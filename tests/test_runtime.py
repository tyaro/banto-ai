import sys
import types
import unittest
from unittest.mock import patch

from banto_ai.runtime import process_peak_memory_bytes


class RuntimeMemoryTests(unittest.TestCase):
    def test_linux_ru_maxrss_is_converted_from_kibibytes(self):
        fake_resource = types.SimpleNamespace(
            RUSAGE_SELF=0,
            getrusage=lambda _kind: types.SimpleNamespace(ru_maxrss=4096),
        )
        with patch.dict(sys.modules, {"resource": fake_resource}), patch(
            "banto_ai.runtime.os.name", "posix"
        ), patch("banto_ai.runtime.sys.platform", "linux"):
            value, source = process_peak_memory_bytes()
        self.assertEqual(value, 4096 * 1024)
        self.assertEqual(source, "os.resource.ru_maxrss")

    def test_macos_ru_maxrss_is_already_bytes(self):
        fake_resource = types.SimpleNamespace(
            RUSAGE_SELF=0,
            getrusage=lambda _kind: types.SimpleNamespace(ru_maxrss=4096),
        )
        with patch.dict(sys.modules, {"resource": fake_resource}), patch(
            "banto_ai.runtime.os.name", "posix"
        ), patch("banto_ai.runtime.sys.platform", "darwin"):
            value, source = process_peak_memory_bytes()
        self.assertEqual(value, 4096)
        self.assertEqual(source, "os.resource.ru_maxrss")


if __name__ == "__main__":
    unittest.main()
