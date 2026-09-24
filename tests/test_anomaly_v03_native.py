"""Native Windows checks touch only fresh, dedicated system-temp fixtures."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from banto_ai import _anomaly_v03_io as publication
from banto_ai import anomaly_v03_native as native


@unittest.skipUnless(os.name == "nt", "Windows native acceptance only")
class NativeFixtureTests(unittest.TestCase):
    def test_two_processes_cannot_claim_or_replace_same_publication(self):
        with tempfile.TemporaryDirectory(prefix="banto-v03-native-race-") as temporary:
            parent = Path(temporary)
            gate = parent/"start"
            code = ("import pathlib,sys,time; "
                    "from banto_ai import _anomaly_v03_io as p; "
                    "parent=pathlib.Path(sys.argv[1]); gate=parent/'start'; "
                    "\nwhile not gate.exists(): time.sleep(.001)\n"
                    "try:\n"
                    " with p.FixturePublication(parent,'race') as store:\n"
                    "  store.write('facts.json',b'{\"count\":20}\\n'); "
                    "store.publish(lambda files: None,lambda: None)\n"
                    " print('won')\n"
                    "except FileExistsError: print('lost')\n")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1]/"src")
            children = [subprocess.Popen([sys.executable, "-P", "-c", code, str(parent)],
                                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        for _ in range(2)]
            try:
                gate.write_bytes(b"go")
                results = [child.communicate(timeout=10) for child in children]
                self.assertEqual([child.returncode for child in children], [0, 0], results)
                self.assertEqual(sorted(stdout.strip() for stdout, _ in results), ["lost", "won"], results)
                root = parent/"race"
                marker = publication.read_regular(root/".complete", links=2)
                publication.verify_fixture_publication(
                    root, expected_marker_sha256=publication.sha(marker),
                    verify_semantics=lambda files: self.assertEqual(files["facts.json"], b'{"count":20}\n'))
            finally:
                for child in children:
                    if child.poll() is None:
                        child.kill()
                        child.wait(timeout=5)

    def test_protected_dacl_and_restricted_child_access_check(self):
        temporary = tempfile.TemporaryDirectory(prefix="banto-v03-native-")
        root = None
        protection_started = False
        try:
            parent = Path(temporary.name)
            with publication.FixturePublication(parent, "attempt") as store:
                store.write("nested/facts.json", b'{"count":20}\n')
                receipt = store.publish(lambda files: self.assertEqual(files["nested/facts.json"], b'{"count":20}\n'),
                                        lambda: None)
                root = store.root
            publication.verify_fixture_publication(root, expected_marker_sha256=receipt["marker_raw_sha256"],
                                                    verify_semantics=lambda files: self.assertEqual(files["nested/facts.json"], b'{"count":20}\n'))
            protection_started = True
            installed = native.protect_fixture_publication(root)
            checked = native.check_protected_fixture(root)
            publication.verify_fixture_publication(
                root, expected_marker_sha256=receipt["marker_raw_sha256"],
                verify_semantics=lambda files: self.assertEqual(files["nested/facts.json"], b'{"count":20}\n'))
            self.assertEqual(installed["objects"], checked["objects_checked"])
            self.assertEqual(installed["acl_scope"], "system-temp-fixture")
            self.assertEqual(checked["native_acceptance"], "not_completed")
            self.assertNotEqual(checked["child_pid"], os.getpid())
            self.assertTrue(all(row["protected_dacl"] for row in checked["checks"]))
            probe = ("from pathlib import Path; import sys; "
                     "root=Path(sys.argv[1]); target=root/'payload'/'nested'/'facts.json'; "
                     "assert target.read_bytes()==b'{\"count\":20}\\n'; "
                     "\nfor action in (lambda: target.write_bytes(b'overwrite'), "
                     "lambda: (root/'payload'/'new.json').write_bytes(b'{}'), "
                     "lambda: (root/'payload'/'new-dir').mkdir(), "
                     "lambda: target.unlink()):\n"
                     " try: action()\n"
                     " except PermissionError: pass\n"
                     " else: raise AssertionError('write/delete unexpectedly allowed')\n")
            child = subprocess.run([sys.executable, "-I", "-c", probe, str(root)],
                                   capture_output=True, text=True, timeout=10,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(child.returncode, 0, child.stderr)
        finally:
            # Teardown is limited to the new fixture created by this test.
            if root is not None and protection_started:
                for path in sorted(native._published_paths(root), key=lambda p: len(p.parts), reverse=True):
                    native._set_dacl(path, "D:P(A;;FA;;;WD)")
            temporary.cleanup()


if __name__ == "__main__":
    unittest.main()
