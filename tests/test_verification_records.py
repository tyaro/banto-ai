"""Diagnostic record failures; no old evaluation/test/CI is rerun."""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from verification_records import EvidenceStore, RecordLimits, RecordLimitError, OutputLimitError, verify_record


class VerificationRecordTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "artifacts")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "record"

    def item_bytes(self, record, label):
        return b"".join((self.root / p["path"]).read_bytes() for p in record["items"][label]["parts"])

    def small_limits(self, **kwargs):
        values = dict(total_bytes=256 * 1024, total_files=48, part_bytes=8192,
                      failure_bytes=128 * 1024, failure_files=16)
        values.update(kwargs)
        return RecordLimits(**values)

    def test_binary_and_large_json_split_without_byte_or_unicode_loss(self):
        binary = bytes(range(256)) * 2200  # Above the former512KiB root limit.
        value = {"message": "日本語🙂" * 40000, "seed": 2486912926863618161}
        with EvidenceStore(self.root) as store:
            store.write_bytes("stdout", binary)
            store.write_json("metadata", value)
        record = verify_record(self.root)
        self.assertEqual(self.item_bytes(record, "stdout"), binary)
        self.assertEqual(json.loads(self.item_bytes(record, "metadata")), value)
        self.assertGreater(len(record["items"]["stdout"]["parts"]), 1)
        self.assertTrue(all(p.stat().st_size <= 256 * 1024 for p in self.root.iterdir()))

    def test_more_than_32_files_and_closed_root_cannot_be_appended_or_reused(self):
        with EvidenceStore(self.root) as store:
            for i in range(40):
                store.write_json(f"part-{i}", {"i": i})
        marker = store.close()
        self.assertEqual(marker["status"], "complete")
        with self.assertRaises(RecordLimitError):
            store.write_bytes("late", b"no")
        with self.assertRaises(FileExistsError):
            EvidenceStore(self.root)
        self.assertEqual(len(verify_record(self.root)["items"]), 41)

    def test_normal_byte_quota_preserves_partial_prefix_exception_and_closure(self):
        original = None
        with self.assertRaises(RecordLimitError) as raised:
            with EvidenceStore(self.root, self.small_limits()) as store:
                with store.operation("large"):
                    try:
                        store.write_bytes("large-log", b"x" * 160000)
                    except RecordLimitError as error:
                        original = error
                        raise
        self.assertIs(raised.exception, original)
        record = verify_record(self.root)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["items"]["large-log"]["status"], "partial")
        self.assertGreater(record["items"]["large-log"]["saved_bytes"], 0)
        self.assertEqual(record["operations"]["large"]["error"]["type"], "RecordLimitError")
        self.assertLessEqual(sum(p.stat().st_size for p in self.root.iterdir()), 256 * 1024)

    def test_file_quota_leaves_failure_and_closure_slots(self):
        with self.assertRaises(RecordLimitError):
            with EvidenceStore(self.root, self.small_limits(total_files=24)) as store:
                with store.operation("many"):
                    for i in range(24):
                        store.write_json(f"item-{i}", {"i": i})
        record = verify_record(self.root)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["operations"]["many"]["status"], "failed")
        self.assertLessEqual(len(list(self.root.iterdir())), 24)

    def test_failed_exit_and_both_streams_survive_normal_storage_exhaustion(self):
        result = subprocess.CompletedProcess(["already-returned"], 7, b"out" * 12000, b"err" * 3000)
        with self.assertRaises(subprocess.CalledProcessError) as raised:
            with EvidenceStore(self.root, self.small_limits()) as store:
                store.write_bytes("earlier", b"a" * 110000)
                with store.operation("command") as operation:
                    operation.capture_process(result)
        self.assertEqual(raised.exception.returncode, 7)
        record = verify_record(self.root)
        self.assertEqual(record["operations"]["command"]["returncode"], 7)
        self.assertEqual(self.item_bytes(record, "command.failure-stdout"), result.stdout)
        self.assertEqual(self.item_bytes(record, "command.failure-stderr"), result.stderr)

    def test_output_bound_is_unchanged_despite_larger_record_capacity(self):
        result = subprocess.CompletedProcess(["already-returned"], 0, b"a" * (1024**2 + 1), b"")
        with self.assertRaises(OutputLimitError):
            with EvidenceStore(self.root) as store:
                with store.operation("command") as operation:
                    operation.capture_process(result)
        record = verify_record(self.root)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(self.item_bytes(record, "command.stdout"), result.stdout)
        self.assertEqual(record["operations"]["command"]["returncode"], 0)

    def test_swallowed_command_error_still_cannot_become_success(self):
        with self.assertRaises(subprocess.CalledProcessError):
            with EvidenceStore(self.root) as store:
                with store.operation("command") as operation:
                    try:
                        operation.capture_process(subprocess.CompletedProcess(["fixture"], 8, b"", b"failed"))
                    except subprocess.CalledProcessError:
                        pass
        self.assertEqual(verify_record(self.root)["operations"]["command"]["status"], "failed")

    def test_timeout_observed_streams_are_saved_as_partial_and_original_is_retained(self):
        original = subprocess.TimeoutExpired(["fixture"], 30, output=b"prefix", stderr=b"interrupted")
        with self.assertRaises(subprocess.TimeoutExpired) as raised:
            with EvidenceStore(self.root) as store:
                with store.operation("command"):
                    raise original
        self.assertIs(raised.exception, original)
        record = verify_record(self.root)
        item = record["items"]["command.failure-stdout"]
        self.assertFalse(item["source_complete"])
        self.assertEqual(self.item_bytes(record, "command.failure-stdout"), b"prefix")
        self.assertIsNone(record["operations"]["command"]["returncode"])

    def test_filesystem_failure_does_not_mask_original_body_exception(self):
        original = ValueError("original failure")
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            with self.assertRaises(ValueError) as raised:
                with EvidenceStore(self.root) as store:
                    with store.operation("work"):
                        store._write = lambda *a, **kw: (_ for _ in ()).throw(OSError("disk unavailable"))
                        raise original
            self.assertIs(raised.exception, original)
            self.assertIn("evidence could not be saved", stderr.getvalue())
        self.assertFalse((self.root / "root-closed.json").exists())

    def test_interrupt_outside_operation_preserves_failure_record(self):
        original = KeyboardInterrupt("stop")
        with self.assertRaises(KeyboardInterrupt) as raised:
            with EvidenceStore(self.root):
                raise original
        self.assertIs(raised.exception, original)
        record = verify_record(self.root)
        self.assertEqual(record["operations"]["store"]["error"]["type"], "KeyboardInterrupt")

    def test_modified_missing_and_extra_parts_are_rejected(self):
        with EvidenceStore(self.root) as store:
            store.write_bytes("stdout", b"original")
        part = self.root / "stdout.000001.part"
        part.write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            verify_record(self.root)
        part.write_bytes(b"original")
        extra = self.root / "extra"
        extra.write_bytes(b"unexpected")
        with self.assertRaises(ValueError):
            verify_record(self.root)
        extra.unlink()  # This is this test's disposable fixture only.
        part.unlink()
        with self.assertRaises(ValueError):
            verify_record(self.root)

    def test_large_failure_trace_cannot_spend_closure_reserve(self):
        original = ValueError("original")
        with patch("traceback.format_exception", return_value=["trace" * 80000]), patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(ValueError) as raised:
                with EvidenceStore(self.root, self.small_limits()) as store:
                    with store.operation("work"):
                        raise original
        self.assertIs(raised.exception, original)
        record = verify_record(self.root)
        self.assertEqual(record["operations"]["work"]["error"]["type"], "ValueError")
        self.assertEqual(record["items"]["work.traceback"]["status"], "partial")

    def test_closing_before_operation_finishes_is_incomplete_and_cannot_be_retried(self):
        store = EvidenceStore(self.root)
        operation = store.operation("work")
        operation.__enter__()
        marker = store.close()
        self.assertEqual(marker["status"], "incomplete")
        with patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(RecordLimitError):
            operation.__exit__(None, None, None)
        self.assertIs(store.close(), marker)
        record = verify_record(self.root)
        self.assertEqual(record["operations"]["work"]["status"], "running")

    def test_partial_file_from_failed_write_is_retained_without_a_complete_stream_claim(self):
        store = EvidenceStore(self.root)
        original_write = store._write
        def partial(name, raw, emergency=False, closing=False):
            if name.startswith("work.stdout."):
                with (self.root / name).open("xb") as stream:
                    stream.write(raw[:3])
                raise OSError("partial filesystem write")
            return original_write(name, raw, emergency, closing)
        result = subprocess.CompletedProcess(["fixture"], 6, b"original stdout", b"stderr")
        with self.assertRaises(subprocess.CalledProcessError):
            with store:
                with store.operation("work") as operation:
                    store._write = partial
                    operation.capture_process(result)
        record = verify_record(self.root)
        self.assertEqual((self.root / "work.stdout.000001.part").read_bytes(), b"ori")
        self.assertEqual(record["items"]["work.stdout"]["status"], "partial")
        self.assertEqual(record["items"]["work.stdout"]["saved_bytes"], 0)
        self.assertEqual(self.item_bytes(record, "work.failure-stdout"), result.stdout)

    def test_terminal_write_failure_never_replaces_original_exception(self):
        original = ValueError("original body error")
        with patch("sys.stderr", new_callable=io.StringIO), self.assertRaises(ValueError) as raised:
            with EvidenceStore(self.root) as store:
                write = store._write
                def fail_terminal(name, raw, emergency=False, closing=False):
                    if name.startswith("helper-end."):
                        raise OSError("terminal storage failed")
                    return write(name, raw, emergency, closing)
                store._write = fail_terminal
                try:
                    with store.operation("work"):
                        raise original
                finally:
                    self.assertIsNone(store.write_terminal("helper-end", {"status": "failed"}))
        self.assertIs(raised.exception, original)
        self.assertEqual(verify_record(self.root)["operations"]["work"]["error"]["type"], "ValueError")

    def test_terminal_write_failure_after_success_is_a_recording_failure(self):
        with patch("sys.stderr", new_callable=io.StringIO), self.assertRaisesRegex(OSError, "terminal storage failed"):
            with EvidenceStore(self.root) as store:
                with store.operation("work"):
                    pass
                write = store._write
                def fail_terminal(name, raw, emergency=False, closing=False):
                    if name.startswith("helper-end."):
                        raise OSError("terminal storage failed")
                    return write(name, raw, emergency, closing)
                store._write = fail_terminal
                self.assertIsNone(store.write_terminal("helper-end", {"status": "passed"}))
        record = verify_record(self.root)
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["operations"]["work"]["status"], "passed")

    def test_long_exception_summary_marks_truncation_and_retains_full_trace(self):
        message = "original-message-" * 400
        original = ValueError(message)
        with self.assertRaises(ValueError) as raised:
            with EvidenceStore(self.root) as store:
                with store.operation("work"):
                    raise original
        self.assertIs(raised.exception, original)
        record = verify_record(self.root)
        error = record["operations"]["work"]["error"]
        self.assertTrue(error["message_truncated"])
        self.assertEqual(error["message"], message[:2048])
        self.assertIn(message.encode(), self.item_bytes(record, "work.traceback"))


if __name__ == "__main__":
    unittest.main()
