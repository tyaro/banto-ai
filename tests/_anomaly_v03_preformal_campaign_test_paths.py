"""Exercise campaign storage with native temporary paths on POSIX CI.

The production campaign contract intentionally accepts Windows paths only.
These test-local adapters let filesystem and journal tests exercise the same
state transitions on a POSIX runner; the unpatched path contract is covered by
the pure metadata and preflight tests.
"""
from __future__ import annotations

from contextlib import ExitStack
import os
from pathlib import PurePosixPath
import sys
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_consumer_evidence as evidence
from banto_ai import anomaly_v03_preformal_campaign_metadata as metadata
from banto_ai import anomaly_v03_preformal_campaign_preflight as preflight


_WINDOWS_ABSOLUTE = evidence._absolute


def _fixture_absolute(value):
    if not (isinstance(value, str) and value.startswith('/')):
        return _WINDOWS_ABSOLUTE(value)
    parts = value.split('/')
    v.require(PurePosixPath(value).is_absolute() and
              str(PurePosixPath(value)) == value and
              all(part not in ('', '.', '..') for part in parts[1:]),
              'canonical local POSIX fixture path required')
    return value.casefold()


def _fixture_python_path(value):
    v.require(value == sys.executable and PurePosixPath(value).is_absolute(),
              'current POSIX test Python required')
    return value


class PortableCampaignPaths(unittest.TestCase):
    """Scope platform adaptation to one test, including setup and cleanup."""

    def run(self, result=None):
        if os.name == 'nt':
            return super().run(result)
        with ExitStack() as patches:
            patches.enter_context(patch.object(metadata, 'PureWindowsPath',
                                               PurePosixPath))
            patches.enter_context(patch.object(preflight, 'PureWindowsPath',
                                               PurePosixPath))
            patches.enter_context(patch.object(evidence, '_absolute',
                                               _fixture_absolute))
            patches.enter_context(patch.object(preflight, '_python_path',
                                               _fixture_python_path))
            return super().run(result)
