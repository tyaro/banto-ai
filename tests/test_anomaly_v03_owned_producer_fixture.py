"""Focused invented-archive and preflight rejection checks for the owned join."""
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from banto_ai import anomaly_v03_owned_producer_fixture as owned


def archive(entries):
    stream = BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as saved:
        for name, raw in entries:
            saved.writestr(name, raw)
    return stream.getvalue()


class OwnedProducerFixtureTests(unittest.TestCase):
    def setUp(self):
        self.manifest = owned.primary.v.canonical_json({
            'registration_pin': {'bytes': 1, 'sha256': '0' * 64}})
        self.entries = [
            ('primary/manifest.json', self.manifest),
            ('slices/manifest.json', b'{}'),
            ('primary/files/registration.json', b'{}'),
            ('slices/files/slices/invented.json', b'{}'),
        ]

    def test_decodes_names_without_extracting_or_granting_a_role(self):
        case = owned._decode_archive(archive(self.entries), (1, 1))
        self.assertEqual(case['expected_mode'], 'fixture')
        self.assertEqual(case['primary_input']['expected_mode'], 'fixture')
        self.assertEqual(set(case['primary_input']['snapshots']), {'registration.json'})
        self.assertEqual(set(case['snapshots']), {'slices/invented.json'})

    def test_rejects_case_alias_and_parent_traversal(self):
        altered = self.entries + [('primary/files/REGISTRATION.json', b'{}')]
        with self.assertRaisesRegex(ValueError, 'duplicate invented archive entry'):
            owned._decode_archive(archive(altered), (2, 1))
        altered = self.entries[:-1] + [('slices/files/../escaped.json', b'{}')]
        with self.assertRaises(ValueError):
            owned._decode_archive(archive(altered), (1, 1))

    def test_expansion_cap_is_checked_before_member_read(self):
        with patch.object(owned, 'UNCOMPRESSED_MAX', 20):
            with self.assertRaisesRegex(ValueError, 'expanded byte limit'):
                owned._decode_archive(archive(self.entries), (1, 1))

    def test_external_pin_failure_creates_no_worker_or_receipt(self):
        with tempfile.TemporaryDirectory(dir=owned.ROOT / 'artifacts') as temporary:
            parent = Path(temporary)
            (parent / 'input').mkdir()
            source = parent / 'input' / 'invented.zip'
            source.write_bytes(archive(self.entries))
            wrong = {'bytes': source.stat().st_size, 'sha256': '0' * 64}
            with self.assertRaisesRegex(ValueError, 'external invented archive pin'):
                owned.join_with_evidence(
                    source, wrong, expected_revision='a' * 40,
                    receipt_parent=parent, receipt_name='producer-attempt')
            self.assertFalse((parent / 'producer-attempt').exists())


if __name__ == '__main__':
    unittest.main()
