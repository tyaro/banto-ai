"""Small generated fixtures and real publication; no registered observations."""
import io
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_chunk_contract as chunk
from banto_ai import anomaly_v03_chunk_producer as producer
from banto_ai import anomaly_v03_checkpoints as checkpoints
from banto_ai import anomaly_v03_engineering as engine
from banto_ai import anomaly_v03_materializer as materializer
from banto_ai import _anomaly_v03_io as storage
from banto_ai import _anomaly_v03_engineering_runtime as resources
from tests.test_anomaly_v03_engineering import fixture_context, fixture_pair, fixture_compute, fixture_verify


class ChunkProducerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="banto-chunk-producer-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.checkout, self.runtime = fixture_context()
        self.plan = checkpoints.fixed_plan("a" * 40, "b" * 40)
        self.enterContext(redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(materializer, "normal_stream", side_effect=AssertionError("registered generation forbidden")))
        self.generate = self.enterContext(patch.object(materializer, "materialize_pair", side_effect=fixture_pair))
        self.compute = self.enterContext(patch.object(engine.runner, "compute_evaluation", side_effect=fixture_compute))
        self.replay = self.enterContext(patch.object(engine.runner, "verify_evaluation", side_effect=fixture_verify))

    def execute(self, index=96, attempt=1, *, memory=None, boundary=lambda: None):
        parent = self.root / str(index) / str(attempt)
        parent.mkdir(parents=True, exist_ok=True)
        with storage.LocalPublication(parent, "result") as owned:
            return producer.execute_chunk(owned, self.checkout, self.runtime, self.plan, index, attempt, time.monotonic(),
                boundary=boundary, sample_memory=memory or (lambda: {"peak_private_bytes": 1000000}))

    def test_boundaries_produce_correct_six_and_replay_after_writer_closes(self):
        for index in (0, 95, 96, 119):
            result = self.execute(index, 2)
            self.assertEqual([s["identity"] for s in result["manifest"]["slots"]], self.plan["chunks"][index]["identities"])
            self.assertEqual(result["manifest"]["coverage"]["inconclusive"], 2)
            storage.verify_local_publication(Path(result["receipt"]["output_path"]),
                expected_marker_sha256=result["receipt"]["marker_raw_sha256"],
                verify_semantics=lambda files: producer.verify_payloads(files, self.checkout, self.runtime, self.plan, index, 2))
        self.assertEqual((self.compute.call_count, self.replay.call_count), (24, 48))

    def test_failure_retains_prefix_and_new_attempt_does_not_overwrite(self):
        count = 0
        def fail(identity, files, checkout):
            nonlocal count
            count += 1
            if count == 3:
                raise ValueError("injected compute failure")
            return fixture_compute(identity, files, checkout)
        self.compute.side_effect = fail
        with self.assertRaises(ValueError):
            self.execute()
        path = self.root / "96/1/result/failure.json"
        raw = path.read_bytes()
        manifest = v.strict_json(raw)["result"]
        self.assertEqual(chunk.validate_manifest(manifest, self.plan, 96, 1)["coverage"],
                         {"not_started": 3, "success": 2, "inconclusive": 0, "failed": 1})
        with self.assertRaises(FileExistsError):
            self.execute()
        self.compute.side_effect = fixture_compute
        self.execute(attempt=2)
        self.assertEqual(path.read_bytes(), raw)
        self.assertFalse((path.parent / ".complete").exists())

    def test_memory_stop_precedes_generation(self):
        with self.assertRaisesRegex(resources.ResourceStop, "memory_limit"):
            self.execute(memory=lambda: {"peak_private_bytes": 2 * 1024**3 + 1})
        self.generate.assert_not_called()

    def test_wrong_source_rejected_before_any_payload_write(self):
        self.plan = checkpoints.fixed_plan("c" * 40, "b" * 40)
        with self.assertRaisesRegex(ValueError, "producer revision"):
            self.execute()
        self.assertFalse((self.root / "96/1/result/stage/planned.json").exists())
        self.generate.assert_not_called()

    def test_replay_and_boundary_failure_never_publish(self):
        self.replay.side_effect = ValueError("replay mismatch")
        with self.assertRaisesRegex(ValueError, "replay mismatch"):
            self.execute()
        self.replay.side_effect = fixture_verify
        def stop():
            raise ValueError("changed source or runtime")
        with self.assertRaisesRegex(ValueError, "changed source"):
            self.execute(attempt=2, boundary=stop)
        self.assertFalse((self.root / "96/1/result/.complete").exists())
        self.assertFalse((self.root / "96/2/result/.complete").exists())

    def test_saved_wrong_attempt_and_tampered_pair_rejected(self):
        result = self.execute()
        files = storage.read_tree(Path(result["receipt"]["output_path"]) / "payload")
        with self.assertRaises(ValueError):
            producer.verify_payloads(files, self.checkout, self.runtime, self.plan, 96, 2)
        path = result["manifest"]["datasets"][0]["files"][0]["path"]
        files[path] = b'{}\n'
        with self.assertRaisesRegex(ValueError, "registered pair replay"):
            producer.verify_payloads(files, self.checkout, self.runtime, self.plan, 96, 1)


if __name__ == "__main__":
    unittest.main()
