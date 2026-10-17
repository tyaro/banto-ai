"""Unadopted 26H2 platform fixture, isolated from formal and 25H2 entrances.

Reuses the bounded five-payload publisher only inside this process's explicitly
scoped runtime/source adapter.  Call this entry in its own orchestrator process;
its temporary module bindings are not a concurrent public API.  All observations
remain fixture-only and cannot grant S4/S5/S6 permission.
"""
from __future__ import annotations

from contextlib import contextmanager
import threading
from types import SimpleNamespace

from . import anomaly_v03_fixture_publication as publication
from . import anomaly_v03_platform_fixture_runtime as runtime


ROOT = publication.ROOT
POLICY_ID = runtime.POLICY_ID
OUTPUT_PARENT = ROOT / 'artifacts' / 'anomaly-v03-engineering-platform-v2'
FORMAT = 'anomaly-v03-platform-fixture-check-v2'
ADDITIONAL_SOURCES = (
    'src/banto_ai/anomaly_v03_platform_fixture.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
)
EXTRA_SOURCES = tuple(sorted((*publication.EXTRA_SOURCES, *ADDITIONAL_SOURCES)))
SOURCE_FILES = tuple(sorted((*publication.observed.SOURCE_FILES, *EXTRA_SOURCES)))
BOOTSTRAP = (
    'import sys;sys.path.insert(0,sys.argv.pop(1));'
    'from banto_ai.anomaly_v03_platform_fixture import worker_main;'
    'raise SystemExit(worker_main(sys.argv[1:]))'
)
_LOCK = threading.RLock()


@contextmanager
def _platform_scope():
    """Apply candidate observation only to a dedicated platform-fixture call."""
    with _LOCK:
        previous = (publication.EXTRA_SOURCES, publication.SOURCE_FILES,
                    publication.BOOTSTRAP,
                    publication.supervisor.resources.probe_runtime,
                    publication.supervisor.policy)
        try:
            publication.EXTRA_SOURCES = EXTRA_SOURCES
            publication.SOURCE_FILES = SOURCE_FILES
            publication.BOOTSTRAP = BOOTSTRAP
            publication.supervisor.resources.probe_runtime = runtime.probe_runtime
            publication.supervisor.policy = SimpleNamespace(validate_runtime=runtime.validate_runtime)
            yield
        finally:
            (publication.EXTRA_SOURCES, publication.SOURCE_FILES,
             publication.BOOTSTRAP,
             publication.supervisor.resources.probe_runtime,
             publication.supervisor.policy) = previous


def worker_main(argv):
    """Child entry.  The old publication worker retains its fixture-only schema."""
    with _platform_scope():
        return publication.worker_main(argv)


def _target(receipt_name):
    publication.v.safe_relative_path(receipt_name)
    publication.v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),
                          'platform fixture receipt name')
    parent = publication.io.regular_path(ROOT / 'artifacts', directory=True)
    publication.v.require(OUTPUT_PARENT == parent / 'anomaly-v03-engineering-platform-v2',
                          'platform fixture root changed')
    publication.io.regular_path(OUTPUT_PARENT, directory=True, missing=True)
    OUTPUT_PARENT.mkdir(exist_ok=True)
    target = publication.io.regular_path(OUTPUT_PARENT / receipt_name, directory=True, missing=True)
    return target


def _save_platform_receipt(target, value):
    raw = publication.io.json_bytes(value)
    publication.io._exclusive(target / 'platform-result.json', raw)
    publication.evidence._raw(publication.observed._file(target / 'platform-result.json', 64 * 1024),
                              publication.observed._pin(raw), 'platform fixture receipt changed')
    return {**value, 'platform_result_pin': publication.observed._pin(raw),
            'check_directory': str(target)}


def publish_fixture(request, *, expected_revision, receipt_name, budget_limits=None):
    """Candidate exact-runtime fixture only; never accepts a formal input mode."""
    publication._request(request)
    publication.evidence._digest(expected_revision, 40)
    target = _target(receipt_name)
    value = {**publication.CLOSED, 'format': FORMAT, 'policy_id': POLICY_ID,
             'status': 'failed', 'mode': 'fixture', 'scope': 'invented-platform-fixture-only',
             'source_revision': expected_revision, 'platform_contract_status': 'proposal-not-accepted',
             'registered_data_read': False, 'new_evaluations': 0,
             'preflight_runtime': None, 'postflight_runtime': None,
             'publication_result_pin': None, 'publication_status': 'not_started',
             'reader_status': 'not_started'}
    try:
        value['preflight_runtime'] = runtime.probe_runtime(ROOT)
        with _platform_scope():
            result = publication.publish_with_evidence(
                request, expected_revision=expected_revision,
                receipt_parent=OUTPUT_PARENT, receipt_name=receipt_name,
                budget_limits=budget_limits)
        value['publication_result_pin'] = result['result_pin']
        value['publication_status'] = result['publication_status']
        value['reader_status'] = result['reader_status']
        if result['status'] != 'verified':
            value['reason'] = result.get('reason', 'publication_failed')
            value['detail'] = result.get('detail', '')
        else:
            value['postflight_runtime'] = runtime.probe_runtime(ROOT)
            publication.evidence._same(value['postflight_runtime'], value['preflight_runtime'],
                                       'platform fixture runtime changed')
            value['status'] = 'verified'
    except publication.supervisor.UnreapedWorker:
        # Retain the supervisor's owned process object; a failed sidecar write
        # must never silently discard ownership of a live child.
        raise
    except (ValueError, OSError, KeyError, TypeError) as error:
        value['reason'] = 'platform_fixture_rejected'
        value['detail'] = str(error)
    if not target.exists():
        target.mkdir()
    return _save_platform_receipt(target, value)
