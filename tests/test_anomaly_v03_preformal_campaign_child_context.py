"""Pinned campaign child context rejects a changed or misplaced plan."""
from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from banto_ai import anomaly_v03_preformal_campaign_child_context as child
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from tests.test_anomaly_v03_preformal_campaign_metadata import _plan


class CampaignChildContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        artifacts = Path(self.temporary.name) / 'artifacts'
        artifacts.mkdir()
        self.root = artifacts / 'anomaly-v03-preformal-campaign-aaaaaaaa'
        self.root.mkdir()
        original = _plan()
        self.plan = metadata.fixed_plan(
            original['campaign_id'], str(self.root), original['path_code'],
            original['registry_pin'], original['source'],
            original['runtime_candidate'], original['budget_candidate'])
        self.raw = metadata.encode_plan(self.plan)
        self.path = self.root / 'plan.json'
        self.path.write_bytes(self.raw)
        self.pin = metadata.pin(self.raw)
        self.attempt = metadata.attempt_root(self.plan, 0, 1)
        self.context = {
            'plan_path': str(self.path), 'anchor_pin': self.pin,
            'chunk_index': 0, 'attempt': 1,
        }

    def test_exact_plan_slot_attempt_and_revision(self):
        self.assertEqual(child.verify_context(
            self.context, attempt_root=self.attempt,
            revision=self.plan['source']['revision']), self.context)
        self.assertEqual(child.from_parts(
            self.path, self.pin, 0, 1, attempt_root=self.attempt,
            revision=self.plan['source']['revision']), self.context)
        for change in (
            {'chunk_index': 1}, {'attempt': 2},
            {'anchor_pin': metadata.pin(b'wrong plan')},
            {'plan_path': str(self.root / 'other.json')},
        ):
            wrong = copy.deepcopy(self.context)
            wrong.update(change)
            with self.subTest(change=change), self.assertRaises((ValueError, OSError)):
                child.verify_context(wrong, attempt_root=self.attempt,
                                     revision=self.plan['source']['revision'])
        for attempt_root, revision in (
            (self.attempt + '-other', self.plan['source']['revision']),
            (self.attempt, 'f' * 40),
        ):
            with self.assertRaises(ValueError):
                child.verify_context(self.context, attempt_root=attempt_root,
                                     revision=revision)

    def test_changed_plan_raw_fails_closed(self):
        self.path.write_bytes(self.raw + b' ')
        with self.assertRaises(ValueError):
            child.verify_context(self.context, attempt_root=self.attempt,
                                 revision=self.plan['source']['revision'])


if __name__ == '__main__':
    unittest.main()
