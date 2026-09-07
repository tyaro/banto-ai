"""Source/runtime preflight tests using only in-memory reads and fake APIs."""

from contextlib import ExitStack
import json
import unittest
from unittest.mock import Mock, patch

from tests.fixtures import anomaly_v03_startup_preflight as p


class StartupPreflightTests(unittest.TestCase):
    def setup_preflight(self, stack, *, clock=lambda: 0):
        api = Mock()
        api.resources.return_value = {"peak_pagefile_bytes": 100}
        stack.enter_context(patch.object(p.w, "_api", return_value=api))
        runtime = stack.enter_context(patch.object(p.w, "_runtime", return_value={"build": "pinned"}))
        source = stack.enter_context(patch.object(p.w, "_source_bytes", return_value=b"pinned"))
        index = stack.enter_context(patch.object(p.w, "_index_bytes", return_value=b"pinned"))
        return p.StartupPreflight(clock=clock), api, runtime, source, index

    def test_fixed_complete_inputs_match_index_without_launch_authorization(self):
        with ExitStack() as stack:
            preflight, api, runtime, source, index = self.setup_preflight(stack)
            result = preflight.run()
            self.assertEqual(result["status"], "verified")
            self.assertEqual(preflight.count, len(p.SOURCES))
            self.assertEqual([row["path"] for row in result["sources"]], list(p.SOURCES))
            self.assertIs(result.private_owner, preflight)
            self.assertFalse(result["launch_authorized"])
            self.assertFalse(result["execution_authenticated"])
            for call in index.call_args_list:
                self.assertEqual(call.args[2]["GIT_OPTIONAL_LOCKS"], "0")
                self.assertEqual(call.args[2]["GIT_NO_LAZY_FETCH"], "1")
            api.a.CreateProcessAsUserW.assert_not_called()
            with self.assertRaises(p.w._Failure):
                preflight.run()
            self.assertEqual(source.call_count, len(p.SOURCES))

    def test_mismatch_keeps_partial_hash_rows_and_stops_next_read(self):
        with ExitStack() as stack:
            preflight, api, runtime, source, index = self.setup_preflight(stack)
            index.side_effect = [b"pinned", b"mismatch"]
            result = preflight.run()
            self.assertEqual(result["status"], "failed")
            self.assertEqual(preflight.count, 1)
            self.assertIsNotNone(preflight.rows[1])
            self.assertIsNone(preflight.rows[2])
            self.assertEqual(source.call_count, 2)
            self.assertEqual(preflight.primary.reason, "source_index_bytes")

    def test_runtime_failure_prevents_source_reads(self):
        with ExitStack() as stack:
            preflight, api, runtime, source, index = self.setup_preflight(stack)
            runtime.side_effect = p.w._Failure("runtime_pin")
            result = preflight.run()
            self.assertEqual(result["status"], "failed")
            source.assert_not_called()
            index.assert_not_called()

    def test_resource_failure_has_no_diagnostic_rereads(self):
        for phase in ("runtime", "source", "index"):
            with ExitStack() as stack, self.subTest(phase=phase):
                preflight, api, runtime, source, index = self.setup_preflight(stack)
                original = MemoryError("DUMMY_PRIVATE")
                {"runtime": runtime, "source": source, "index": index}[phase].side_effect = original
                result = preflight.run()
                self.assertIs(preflight.primary, original)
                self.assertTrue(result["resource_stop"])
                self.assertLessEqual(source.call_count, 1)
                self.assertLessEqual(index.call_count, 1)
                self.assertNotIn("DUMMY", json.dumps(result) + repr(preflight))

    def test_memory_limit_prevents_runtime_and_source_reads(self):
        with ExitStack() as stack:
            preflight, api, runtime, source, index = self.setup_preflight(stack)
            api.resources.return_value = {"peak_pagefile_bytes": p.w._MEMORY_LIMIT}
            result = preflight.run()
            self.assertTrue(result["resource_stop"])
            runtime.assert_not_called()
            source.assert_not_called()

    def test_total_source_limit_prevents_index_read_for_excess(self):
        with ExitStack() as stack:
            preflight, api, runtime, source, index = self.setup_preflight(stack)
            source.return_value = b"x" * (p.w._LIMIT // 2 + 1)
            index.return_value = source.return_value
            result = preflight.run()
            self.assertTrue(result["resource_stop"])
            self.assertEqual(source.call_count, 2)
            index.assert_called_once()

    def test_clock_and_reporting_failure_retain_owner_and_fail_closed(self):
        with ExitStack() as stack:
            preflight, api, runtime, source, index = self.setup_preflight(stack, clock=Mock(side_effect=[0, 30]))
            result = preflight.run()
            self.assertEqual(result["status"], "failed")
            runtime.assert_not_called()
        with ExitStack() as stack:
            preflight, api, runtime, source, index = self.setup_preflight(stack)
            stack.enter_context(patch.object(preflight.result, "update", side_effect=MemoryError()))
            result = preflight.run()
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["resource_stop"])
            self.assertIs(result.private_owner, preflight)


if __name__ == "__main__":
    unittest.main()
