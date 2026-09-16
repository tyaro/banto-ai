"""Small metadata/scheduler fixtures only; never generate registered observations."""
from __future__ import annotations

import copy
import io
import tempfile
import time
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from banto_ai import _anomaly_v03_contract as c
from banto_ai import _anomaly_v03_io as storage
from banto_ai import _anomaly_v03_runtime as rt
from banto_ai import _anomaly_v03_engineering_runtime as resource
from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_engineering as engine
from banto_ai import anomaly_v03_engineering_contract as p
from banto_ai import anomaly_v03_materializer as m


def fixture_context():
    checkout = rt.Checkout(Path("fixture"), "a" * 40, (("src/fixture.py", b"# fixture\n"),))
    observed = c.formal_runtime() | {"os_ubr": 9445}
    return checkout, observed


def fixture_pair(identity):
    return tuple(m.DatasetBytes(v.canonical_json(m.identity_for(identity, layer)), tuple(
        (name, m.json_bytes({"fixture": layer, "file": name})) for name in m.DATASET_FILES)) for layer in c.STRATA)


def fixture_compute(identity, files, checkout):
    return {"identity": identity, "input": m.sha(files["observations.jsonl"]),
            "profiles": [{"status": "inconclusive" if identity["candidate_id"] == c.CANDIDATES[2] else "calibrated"}]}


def fixture_verify(result, identity, files, checkout):
    rt.require(result == fixture_compute(identity, files, checkout), "fixture replay differs")


def complete_fixture():
    result = p.new_manifest("attempt")
    checkout, result["runtime"] = fixture_context()
    result["source"] = checkout.source_descriptor()
    for row, dataset in zip(result["datasets"], fixture_pair(result["plan"]["identities"][0])):
        row["files"] = [p.file_record("datasets/" + row["identity"]["dataset_id"] + "/" + name, raw) for name, raw in dataset.entries]
    for slot in result["slots"]:
        files = fixture_pair(slot["identity"])[c.STRATA.index(slot["identity"]["stratum"])].files()
        slot.update(status="success", input_hashes={key: m.sha(files[name]) for key, name in m.INPUT_FILES.items()},
            evaluation=p.file_record("evaluations/" + slot["identity"]["evaluation_id"] + ".json", b"{}\n"))
    result["state"] = "complete"
    result["resources"]["payload_bytes"] = sum(e["bytes"] for row in result["datasets"] for e in row["files"]) + 18
    p.refresh_coverage(result)
    return result


class ContractTests(unittest.TestCase):
    def test_fixed_plan_is_metadata_only_and_matches_registered_first_pair(self):
        with patch.object(m, "normal_stream", side_effect=AssertionError("generation forbidden")):
            plan = p.fixed_plan()
            self.assertEqual(plan["identities"], v.evaluation_inventory("dev")[:6])
            self.assertEqual(plan["planned_counts"]["score_rows"], 86400)
            self.assertEqual({x["role"] for x in plan["identities"]}, {"dev"})
            self.assertEqual({x["layout"] for x in plan["identities"]}, {0})
            self.assertEqual(p.validate_manifest(p.new_manifest("plan"))["state"], "planned")

    def test_builder_returns_independent_copies(self):
        value = p.new_manifest("first")
        value["plan"]["limits"]["wall_seconds"] = 1
        value["slots"][0]["identity"]["seed"] = 1
        self.assertEqual(p.new_manifest("next")["plan"]["limits"]["wall_seconds"], 900)
        self.assertNotEqual(p.new_manifest("next")["slots"][0]["identity"]["seed"], 1)

    def test_attempt_rejects_paths_reserved_names_and_empty_values(self):
        for value in ("", "../escape", "x/y", "X", "anomaly-multiseed-v03-dev", "a" * 65, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                p.new_manifest(value)

    def test_plan_scope_order_seed_limits_and_flags_cannot_be_overridden(self):
        mutations = [lambda x: x["plan"].update(scope="holdout"),
            lambda x: x["plan"]["identities"].reverse(),
            lambda x: x["plan"]["limits"].update(wall_seconds=901),
            lambda x: x["plan"].update(formal_permission=True),
            lambda x: x["plan"]["planned_counts"].update(seeds=True),
            lambda x: x.update(extra="override")]
        for mutate in mutations:
            value = p.new_manifest("plan")
            mutate(value)
            with self.assertRaises(ValueError):
                p.validate_manifest(value)

    def test_runtime_accepts_updated_ubr_but_preserves_python_and_other_pins(self):
        original = c.formal_runtime()
        p.validate_runtime(original | {"os_ubr": 9445})
        for key, bad in (("os_build", True), ("os_ubr", -1), ("python_version", "3.12.0"),
                         ("filesystem", "local-FAT32"), ("python_exe_raw_sha256", "a" * 64)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                p.validate_runtime(original | {key: bad})
        self.assertEqual(c.formal_runtime(), original)
        with self.assertRaisesRegex(rt.IntegrityError, "s4_acceptance_not_frozen"):
            rt.require_campaign_acceptance()

    def test_completion_remains_untrusted_and_inconclusive_is_preserved(self):
        value = complete_fixture()
        value["slots"][1]["status"] = "inconclusive"
        p.refresh_coverage(value)
        report = p.validate_manifest(value)
        self.assertEqual(report["coverage"]["inconclusive"], 1)
        self.assertFalse(report["result_trusted"])
        self.assertFalse(report["formal_permission"])

    def test_complete_requires_six_exact_slots_and_saved_pair(self):
        for mutate in (lambda x: x["slots"].pop(), lambda x: x["datasets"].pop(),
                       lambda x: x["datasets"][1].update(files=None),
                       lambda x: x["slots"].reverse(), lambda x: x.update(source=None)):
            value = complete_fixture()
            mutate(value)
            with self.assertRaises(ValueError):
                p.validate_manifest(value)

    def test_candidate_hashes_paths_and_coverage_must_agree(self):
        for mutate in (lambda x: x["slots"][1]["input_hashes"].update(observations="b" * 64),
                       lambda x: x["slots"][0]["evaluation"].update(path="other.json"),
                       lambda x: x["coverage"].update(success=5),
                       lambda x: x["resources"].update(payload_bytes=0)):
            value = complete_fixture()
            mutate(value)
            with self.assertRaises(ValueError):
                p.validate_manifest(value)

    def test_failed_prefix_retains_success_and_stops_remaining_slots(self):
        value = complete_fixture()
        value["state"] = "failed"
        value["failure"] = {"stage": "evaluation", "reason": "exception"}
        value["slots"][2].update(status="failed", evaluation=None)
        for row in value["slots"][3:]:
            row.update(status="not_started", evaluation=None, input_hashes=None)
        p.refresh_coverage(value)
        self.assertEqual(p.validate_manifest(value)["coverage"]["not_started"], 3)
        value["slots"][4] = complete_fixture()["slots"][4]
        p.refresh_coverage(value)
        with self.assertRaisesRegex(ValueError, "nonsequential"):
            p.validate_manifest(value)

    def test_nonfinite_bool_and_exceeded_completion_resources_are_rejected(self):
        for key, bad in (("elapsed_seconds", float("nan")), ("elapsed_seconds", True),
                         ("elapsed_seconds", 901), ("peak_worker_private_bytes", 2 * 1024**3 + 1),
                         ("payload_bytes", 1024**3 + 1)):
            value = complete_fixture()
            value["resources"][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                p.validate_manifest(value)


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="banto-engineering-tests-")
        self.addCleanup(directory.cleanup)
        self.parent = Path(directory.name)
        self.checkout, self.observed = fixture_context()
        self.stack = self.enterContext(ExitStack())
        self.stack.enter_context(patch.object(m, "normal_stream", side_effect=AssertionError("registered generation forbidden")))
        self.generate = self.stack.enter_context(patch.object(m, "materialize_pair", side_effect=fixture_pair))
        self.compute = self.stack.enter_context(patch.object(engine.runner, "compute_evaluation", side_effect=fixture_compute))
        self.replay = self.stack.enter_context(patch.object(engine.runner, "verify_evaluation", side_effect=fixture_verify))
        self.stack.enter_context(redirect_stdout(io.StringIO()))

    def execute(self, name="attempt", *, memory=None, boundary=lambda: None):
        with storage.LocalPublication(self.parent, name) as store:
            return engine._execute(store, self.checkout, self.observed, name, time.monotonic(),
                boundary=boundary, sample_memory=memory or (lambda: {"peak_private_bytes": 1000000}))

    def test_full_small_run_saves_both_layers_before_sequential_compute_and_replays(self):
        observed = []
        def compute(identity, files, checkout):
            root = self.parent / "attempt/stage/datasets"
            self.assertEqual(len(list(root.iterdir())), 2)
            observed.append((identity, dict(files)))
            return fixture_compute(identity, files, checkout)
        self.compute.side_effect = compute
        result = self.execute()
        self.assertEqual([x[0] for x in observed], p.fixed_plan()["identities"])
        self.assertEqual(observed[0][1], observed[1][1])
        self.assertEqual(observed[3][1], observed[5][1])
        self.assertEqual(result["manifest"]["coverage"], {"not_started": 0, "success": 4, "inconclusive": 2, "failed": 0})
        self.assertEqual(self.compute.call_count, 6)
        self.assertEqual(self.replay.call_count, 6)
        receipt = result["receipt"]
        report = storage.verify_local_publication(Path(receipt["output_path"]),
            expected_marker_sha256=receipt["marker_raw_sha256"],
            verify_semantics=lambda files: engine._verify_payloads(files, self.checkout, self.observed))
        self.assertTrue(report["local_verified"])
        self.assertEqual(self.replay.call_count, 12)

    def test_compute_failure_preserves_prefix_and_no_completion(self):
        calls = []
        def compute(identity, files, checkout):
            calls.append(identity)
            if len(calls) == 3:
                raise ValueError("injected")
            return fixture_compute(identity, files, checkout)
        self.compute.side_effect = compute
        with self.assertRaises(ValueError):
            self.execute()
        failure = v.strict_json((self.parent / "attempt/failure.json").read_bytes())["result"]
        self.assertEqual(p.validate_manifest(failure)["coverage"], {"not_started": 3, "success": 2, "inconclusive": 0, "failed": 1})
        self.assertFalse((self.parent / "attempt/.complete").exists())
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual(len(calls), 3)

    def test_resource_limit_stops_before_data_generation(self):
        with self.assertRaisesRegex(resource.ResourceStop, "memory_limit"):
            self.execute(memory=lambda: {"peak_private_bytes": 2 * 1024**3 + 1})
        self.generate.assert_not_called()
        failure = v.strict_json((self.parent / "attempt/failure.json").read_bytes())["result"]
        self.assertEqual(p.validate_manifest(failure)["coverage"]["not_started"], 6)

    def test_replay_or_source_failure_never_publishes(self):
        self.replay.side_effect = rt.IntegrityError("changed output")
        with self.assertRaisesRegex(ValueError, "changed output"):
            self.execute("bad-replay")
        self.assertFalse((self.parent / "bad-replay/.complete").exists())
        def fail():
            raise rt.IntegrityError("source changed")
        with self.assertRaisesRegex(ValueError, "source changed"):
            self.execute("bad-source", boundary=fail)
        self.assertFalse((self.parent / "bad-source/.complete").exists())

    def test_payload_verifier_rejects_forged_pair_even_with_updated_hashes(self):
        result = self.execute()
        files = storage.read_tree(Path(result["receipt"]["output_path"]) / "payload")
        path = result["manifest"]["datasets"][0]["files"][0]["path"]
        files[path] = b'{"changed":true}\n'
        with self.assertRaisesRegex(ValueError, "registered pair replay"):
            engine._verify_payloads(files, self.checkout, self.observed)

    def test_output_limit_prevents_oversized_first_write(self):
        with patch.object(engine, "CONTROL_RESERVE", 1024**3), self.assertRaisesRegex(resource.ResourceStop, "output_limit"):
            self.execute()
        self.generate.assert_not_called()
        self.assertFalse((self.parent / "attempt/stage/planned.json").exists())


class ResourceTests(unittest.TestCase):
    def test_invalid_measurements_cannot_disable_limits(self):
        for values in ((float("nan"), 0, 0), (-1, 0, 0), (0, True, 0), (0, 0, -1)):
            with self.assertRaises(ValueError):
                resource.check_budget(*values)

    def test_exact_limits_and_each_excess(self):
        resource.check_budget(900, 2 * 1024**3, 1024**3)
        for values, reason in (((901, 0, 0), "time_limit"), ((0, 2 * 1024**3 + 1, 0), "memory_limit"),
                               ((0, 0, 1024**3 + 1), "output_limit")):
            with self.assertRaisesRegex(resource.ResourceStop, reason):
                resource.check_budget(*values)

    def test_low_start_resources_are_rejected(self):
        for observed in ({"free_ram_bytes": 1, "free_disk_bytes": 100 * 1024**3},
                         {"free_ram_bytes": 10 * 1024**3, "free_disk_bytes": 1}):
            with patch.object(resource, "free_resources", return_value=observed), self.assertRaisesRegex(resource.ResourceStop, "insufficient_resources"):
                resource.require_start_resources(Path("fixture"))

    def test_plan_cli_does_not_observe_runtime_or_generate_data(self):
        with patch.object(resource, "probe_runtime", side_effect=AssertionError("runtime probe")), \
             patch.object(m, "normal_stream", side_effect=AssertionError("generation")), redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(engine.main(["plan"]), 0)
        self.assertEqual(v.strict_json(stream.getvalue())["state"], "planned")


class SupervisorTests(unittest.TestCase):
    class Process:
        pid, _handle, returncode = 12345, 456, None
        def __init__(self):
            self.polls, self.kills, self.waits = 0, 0, 0
        def poll(self):
            self.polls += 1
            if self.polls > 1 and self.returncode is None:
                self.returncode = 0
            return self.returncode
        def kill(self):
            self.kills += 1
            self.returncode = -9
        def wait(self, timeout):
            self.waits += 1
            if self.returncode is None:
                self.returncode = 0
            return self.returncode

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="banto-supervisor-tests-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.process = self.Process()
        self.stack = self.enterContext(ExitStack())
        self.stack.enter_context(patch.object(engine, "_root", return_value=self.root))
        self.stack.enter_context(patch.object(resource, "probe_runtime", return_value=fixture_context()[1]))
        self.stack.enter_context(patch.object(resource, "require_start_resources", return_value={"fixture": "free"}))
        self.stack.enter_context(patch.object(rt, "_git", side_effect=lambda root, *args: ("a" * 40).encode() if args[0] == "rev-parse" else b""))
        self.launch = self.stack.enter_context(patch.object(engine.subprocess, "Popen", return_value=self.process))
        self.stack.enter_context(patch.object(engine.subprocess, "CREATE_NO_WINDOW", 0, create=True))
        self.stack.enter_context(patch.object(engine.time, "sleep"))
        self.memory = self.stack.enter_context(patch.object(resource, "memory_bytes", return_value={"peak_private_bytes": 1000}))
        self.free_after = self.stack.enter_context(patch.object(resource, "free_resources", return_value={"fixture": "free"}))

    def test_supervisor_records_whole_worker_and_exit(self):
        result = engine.supervise(self.root, "a" * 40, "attempt")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["observation_errors"], [])
        self.assertTrue(result["worker_exit_confirmed"])
        self.assertEqual(self.process.kills, 0)
        self.assertTrue((self.root / p.OUTPUT_PARENT / "attempt-control/supervision.json").is_file())
        self.assertEqual(self.launch.call_args.kwargs["creationflags"], 0)

    def test_limit_reason_survives_secondary_memory_and_free_resource_failures(self):
        self.memory.side_effect = [{"peak_private_bytes": 2 * 1024**3 + 1}, OSError("final query")]
        self.free_after.side_effect = OSError("free query")
        result = engine.supervise(self.root, "a" * 40, "attempt")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["stop_reason"], "memory_limit")
        self.assertEqual(result["exit_code"], -9)
        self.assertEqual(self.process.kills, 1)
        self.assertEqual(len(result["observation_errors"]), 2)
        saved = v.strict_json((self.root / p.OUTPUT_PARENT / "attempt-control/supervision.json").read_bytes())
        self.assertEqual(saved, result)

    def test_final_memory_failure_is_not_success(self):
        self.memory.side_effect = [{"peak_private_bytes": 1000}, OSError("query")]
        result = engine.supervise(self.root, "a" * 40, "attempt")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["observation_errors"][0]["stage"], "final_worker_memory")

    def test_spawn_failure_still_records_no_worker_started(self):
        self.launch.side_effect = OSError("spawn")
        result = engine.supervise(self.root, "a" * 40, "attempt")
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["worker_pid"])
        self.assertFalse(result["worker_exit_confirmed"])
        self.assertEqual(result["stop_reason"], "supervision_error")

    def test_control_collision_refuses_second_launch(self):
        engine.supervise(self.root, "a" * 40, "attempt")
        with self.assertRaises(FileExistsError):
            engine.supervise(self.root, "a" * 40, "attempt")
        self.assertEqual(self.launch.call_count, 1)


if __name__ == "__main__":
    unittest.main()
