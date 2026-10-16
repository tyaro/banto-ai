"""New setup safeguards on invented files; no historical experiment reruns."""

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import macos_demand_runtime as runtime
import verify_demand_transfer as transfer
import check_demand_macos as connection


class SetupSafeguards(unittest.TestCase):
    def test_connection_refuses_existing_root_before_resource_or_model_work(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory).resolve()
            root = repo / 'artifacts' / 'existing'
            root.mkdir(parents=True)
            (root / 'facts.json').write_bytes(b'preserve')
            with patch.object(connection, 'REPO', repo), \
                    patch.object(connection, 'MacCheckpoint', side_effect=AssertionError('resource work')):
                with self.assertRaises(ValueError):
                    connection.run(root)
            self.assertEqual((root / 'facts.json').read_bytes(), b'preserve')
            self.assertEqual({p.name for p in root.iterdir()}, {'facts.json'})

    def test_checkpoint_stops_on_time_and_memory(self):
        sample = {'phys_footprint_bytes': 10, 'peak_rss_bytes': 10}
        with patch.object(runtime, 'memory_observation', return_value=sample), \
                patch.object(runtime.time, 'monotonic', side_effect=[0, 2]):
            with self.assertRaises(RuntimeError):
                runtime.MacCheckpoint(seconds=1).check()
        with patch.object(runtime, 'memory_observation', return_value=sample):
            with self.assertRaises(RuntimeError):
                runtime.MacCheckpoint(memory_bytes=9).check()

    def test_invalid_limits_and_missing_measurement_fail_closed(self):
        for kwargs in ({'seconds': float('nan')}, {'seconds': 901}, {'seconds': True},
                       {'memory_bytes': 2 * 1024**3 + 1}):
            with self.assertRaises(ValueError):
                runtime.MacCheckpoint(**kwargs)
        with patch.object(runtime, 'memory_observation', side_effect=OSError('unavailable')):
            with self.assertRaises(OSError):
                runtime.MacCheckpoint().check()

    def fixture(self, root):
        raw = b'invented transfer fixture\n'
        (root / 'facts.json').write_bytes(raw)
        closure = {'status': 'complete', 'immutable': True,
                   'files': {'facts.json': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}}
        marker = root / 'root-closed.json'
        marker.write_text(json.dumps(closure))
        return hashlib.sha256(marker.read_bytes()).hexdigest()

    def test_transfer_accepts_exact_files_and_external_source_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            digest = self.fixture(root)
            report = transfer.verify(root, digest)
            self.assertTrue(report['external_source_closure_checked'])
            self.assertFalse(report['evaluation_replayed'])
            self.assertFalse(report['formal_permission'])
            with self.assertRaises(ValueError):
                transfer.verify(root, '0' * 64)

    def test_transfer_rejects_tamper_missing_extra_and_symlink(self):
        for attack in ('tamper', 'missing', 'extra', 'symlink'):
            with self.subTest(attack=attack), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                self.fixture(root)
                if attack == 'tamper': (root / 'facts.json').write_bytes(b'changed\n')
                elif attack == 'missing': (root / 'facts.json').unlink()
                elif attack == 'extra': (root / 'extra.json').write_bytes(b'{}')
                else:
                    (root / 'facts.json').unlink()
                    (root / 'facts.json').symlink_to(root / 'root-closed.json')
                with self.assertRaises(ValueError):
                    transfer.verify(root)


if __name__ == '__main__':
    unittest.main()
