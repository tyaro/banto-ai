"""The committed R2P Torch reference is complete, intact and bound to the current fixtures."""
import hashlib
import json
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT/'crates/banto-ai/tests/fixtures/r2p'


def load(name): return json.loads((REF/name).read_bytes())
def sha256(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class R2PReferenceTests(unittest.TestCase):
    def test_binary_matches_layout_and_summary(self):
        raw = (REF/'reference.f32').read_bytes(); layout = load('reference-layout.json'); summary = load('summary.json')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), summary['reference_sha256'])
        self.assertEqual((len(layout), len(raw)//4), (summary['saved_tensors'], summary['float32_values']))
        offset = 0
        for item in layout:
            self.assertEqual(item['offset'], offset, item['name'])
            chunk = raw[offset:offset+item['bytes']]
            self.assertEqual(hashlib.sha256(chunk).hexdigest(), item['sha256'], item['name'])
            self.assertEqual(list(struct.unpack('<'+'f'*(len(chunk)//4), chunk)), item['values'], item['name'])
            offset += item['bytes']
        self.assertEqual(offset, len(raw))
        self.assertEqual(len({x['name'] for x in layout}), len(layout))

    def test_all_independent_checks_passed(self):
        checks = load('independent-checks.json')
        self.assertEqual(len(checks), load('summary.json')['checks'])
        self.assertTrue(all(c['pass'] and c['element_failures'] == 0 for c in checks))

    def test_reference_is_bound_to_current_fixtures_and_tolerances(self):
        runtime = load('runtime.json')
        for key, path in [('fixtures_sha256', 'examples/configs/rust-r2p-synthetic-fixtures-20261016.json'),
                          ('protocol_sha256', 'examples/configs/rust-r2p-synthetic-protocol-20261016.json'),
                          ('tolerance_sha256', 'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json')]:
            self.assertEqual(sha256(ROOT/path), runtime[key], path)


if __name__ == '__main__':
    unittest.main()
