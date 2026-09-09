import io
import json
import unittest
from types import SimpleNamespace as NS

from tests.fixtures.anomaly_v03_debug_report import write_summary


def owner():
    return NS(result={"status": "observed", "evidence_flush_state": "confirmed",
                      "evidence_file_closed": True, "private_secret": "hidden"},
              resource_stop=False, images=NS(rows=[None] * 16),
              security=NS(rows=[]), memory=None, observer=None,
              evidence=NS(capture_state="not_started"))


class ReportTests(unittest.TestCase):
    def test_unused_image_slots_and_private_fields(self):
        value = owner()
        value.images.rows[0] = {"event_slot": 0, "status": "confirmed",
                                "name": "C:\\private\\python.exe", "file_id": "secret"}
        stream = io.StringIO()
        write_summary(value, stream)
        first, second = map(json.loads, stream.getvalue().splitlines())
        self.assertTrue(first["driver"]["evidence_file_closed"])
        self.assertEqual(second["images"][0]["basename"], "python.exe")
        self.assertNotIn("private", stream.getvalue())
        self.assertNotIn("secret", stream.getvalue())

    def test_final_is_flushed_before_detail_failure(self):
        value = owner()
        stream = io.StringIO()
        class Broken:
            @property
            def rows(self):
                self_test.assertIn('"phase":"final"', stream.getvalue())
                raise ValueError("private failure text")
        self_test = self
        value.images = Broken()
        write_summary(value, stream)
        first, second = map(json.loads, stream.getvalue().splitlines())
        self.assertEqual(first["driver"]["status"], "observed")
        self.assertEqual(second["status"], "failed")
        self.assertNotIn("private failure", stream.getvalue())

    def test_resource_stop_skips_all_details(self):
        value = owner()
        value.resource_stop = True
        del value.images, value.security, value.memory, value.evidence
        stream = io.StringIO()
        write_summary(value, stream)
        self.assertEqual(json.loads(stream.getvalue().splitlines()[1])["status"], "resource_skipped")

    def test_output_failure_is_not_retried(self):
        class BrokenStream:
            calls = 0
            def write(self, text):
                self.calls += 1
                return len(text) - 1
            def flush(self):
                raise AssertionError("must not flush partial write")
        stream = BrokenStream()
        with self.assertRaises(OSError):
            write_summary(owner(), stream)
        self.assertEqual(stream.calls, 1)


if __name__ == "__main__":
    unittest.main()
