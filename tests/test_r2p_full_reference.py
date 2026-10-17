"""The committed R2P step 4 full-model reference is intact and bound to its inputs."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import r2p_full_model_reference as generator  # stdlib only at import time
REF = ROOT/'crates/banto-ai/tests/fixtures/r2p-full'


def load(name): return json.loads((REF/name).read_bytes())
def sha256(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class R2PFullReferenceTests(unittest.TestCase):
    def test_binary_matches_layout_and_summary(self):
        raw = (REF/'reference.f32').read_bytes(); layout = load('reference-layout.json'); summary = load('summary.json')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), summary['reference_sha256'])
        self.assertEqual((len(layout), len(raw)//4), (summary['saved_tensors'], summary['float32_values']))
        offset = 0
        for item in layout:
            self.assertEqual(item['offset'], offset, item['name'])
            chunk = raw[offset:offset+item['bytes']]
            self.assertEqual(hashlib.sha256(chunk).hexdigest(), item['sha256'], item['name'])
            offset += item['bytes']
        self.assertEqual(offset, len(raw))

    def test_every_trainable_tensor_has_gradients_and_all_checks_passed(self):
        names = {x['name'] for x in load('reference-layout.json')}
        trainable = load('initial-parameters-sha256.json')
        self.assertEqual(len(trainable), 59)
        for n in trainable:
            self.assertIn(f'gradient/{n}', names)
            self.assertIn(f'clipped-gradient/{n}', names)
        checks = load('independent-checks.json')
        self.assertEqual(len(checks), load('summary.json')['checks'])
        self.assertTrue(all(c['pass'] and c['element_failures'] == 0 for c in checks))

    def test_initial_parameters_follow_the_fixture_rules(self):
        shapes = {x['name'][len('gradient/'):]: x['shape'] for x in load('reference-layout.json')
                  if x['name'].startswith('gradient/')}
        expected = load('initial-parameters-sha256.json')
        self.assertEqual(set(shapes), set(expected))
        for name, shape in shapes.items():
            values = generator.initial(name, shape)
            packed = struct.pack('<'+'f'*len(values), *values)
            self.assertEqual(struct.unpack('<'+'f'*len(values), packed), tuple(values), f'{name} not float32-exact')
            self.assertEqual(hashlib.sha256(packed).hexdigest(), expected[name], name)

    def test_reference_is_bound_to_current_inputs(self):
        runtime = load('runtime.json')
        for key, path in [('fixtures_sha256', 'examples/configs/rust-r2p-full-model-fixtures-20261017.json'),
                          ('recipe_fixtures_sha256', 'examples/configs/rust-r2p-synthetic-fixtures-20261016.json'),
                          ('tolerance_sha256', 'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'),
                          ('model_source_sha256', 'models/mini-transformer/small_model.py')]:
            self.assertEqual(sha256(ROOT/path), runtime[key], path)


if __name__ == '__main__':
    unittest.main()
