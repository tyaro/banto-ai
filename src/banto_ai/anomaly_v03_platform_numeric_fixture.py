"""Unadopted 26H2 scope for bounded, invented numerical fixture children.

Analysis and its independent audit retain their existing request and result
schemas.  Call each entry in a dedicated orchestrator process: the temporary
module bindings below are not a concurrent public API.  Neither entry accepts
registered observations or grants formal campaign permission.
"""
from __future__ import annotations

from contextlib import contextmanager
import threading
from types import SimpleNamespace

from . import anomaly_v03_fixture_worker as analysis
from . import anomaly_v03_fixture_audit_worker as audit
from . import anomaly_v03_platform_fixture_runtime as runtime


POLICY_ID = 'anomaly-v03-numeric-platform-fixture-v1'
ADDITIONAL_SOURCES = (
    'src/banto_ai/anomaly_v03_platform_numeric_fixture.py',
    'src/banto_ai/anomaly_v03_platform_fixture_runtime.py',
)
EXTRA_SOURCES = tuple(sorted(set((*analysis.EXTRA_SOURCES, *audit.EXTRA_SOURCES,
                                  *ADDITIONAL_SOURCES))))
SOURCE_FILES = tuple(sorted(set((*analysis.observed.SOURCE_FILES, *EXTRA_SOURCES))))
BOOTSTRAP_ANALYSIS = (
    'import sys;sys.path.insert(0,sys.argv.pop(1));'
    'from banto_ai.anomaly_v03_platform_numeric_fixture import worker_main;'
    'raise SystemExit(worker_main("analysis",sys.argv[1:]))'
)
BOOTSTRAP_AUDIT = (
    'import sys;sys.path.insert(0,sys.argv.pop(1));'
    'from banto_ai.anomaly_v03_platform_numeric_fixture import worker_main;'
    'raise SystemExit(worker_main("audit",sys.argv[1:]))'
)
_LOCK = threading.RLock()


@contextmanager
def _numeric_scope(role):
    """Bind one role and the exact candidate runtime within this process."""
    if role not in ('analysis', 'audit'):
        raise ValueError('unknown numeric fixture role')
    with _LOCK:
        worker = analysis if role == 'analysis' else audit
        old = (worker.EXTRA_SOURCES, worker.SOURCE_FILES, worker.BOOTSTRAP,
               worker.supervisor.resources.probe_runtime, worker.supervisor.policy)
        try:
            worker.EXTRA_SOURCES = EXTRA_SOURCES
            worker.SOURCE_FILES = SOURCE_FILES
            worker.BOOTSTRAP = BOOTSTRAP_ANALYSIS if role == 'analysis' else BOOTSTRAP_AUDIT
            worker.supervisor.resources.probe_runtime = runtime.probe_runtime
            worker.supervisor.policy = SimpleNamespace(validate_runtime=runtime.validate_runtime)
            yield
        finally:
            (worker.EXTRA_SOURCES, worker.SOURCE_FILES, worker.BOOTSTRAP,
             worker.supervisor.resources.probe_runtime, worker.supervisor.policy) = old


def worker_main(role, argv):
    """Child entry selected by its fixed, role-specific bootstrap string."""
    with _numeric_scope(role):
        if role == 'analysis':
            return analysis.worker_main(argv)
        return audit.worker_main(argv)


def calculate_fixture(request, *, expected_revision, receipt_parent, receipt_name,
                      budget_limits=None, resource_budget=None,
                      dependency_profile_raw=None,
                      expected_dependency_profile_pin=None):
    """Run the existing bounded invented analysis under the candidate runtime."""
    with _numeric_scope('analysis'):
        return analysis.calculate_with_evidence(
            request, expected_revision=expected_revision, receipt_parent=receipt_parent,
            receipt_name=receipt_name, budget_limits=budget_limits,
            resource_budget=resource_budget,
            dependency_profile_raw=dependency_profile_raw,
            expected_dependency_profile_pin=expected_dependency_profile_pin)


def audit_fixture(request, *, expected_revision, receipt_parent, receipt_name,
                  budget_limits=None, resource_budget=None,
                  dependency_profile_raw=None,
                  expected_dependency_profile_pin=None):
    """Run the existing independent invented audit under the candidate runtime."""
    with _numeric_scope('audit'):
        return audit.audit_with_evidence(
            request, expected_revision=expected_revision, receipt_parent=receipt_parent,
            receipt_name=receipt_name, budget_limits=budget_limits,
            resource_budget=resource_budget,
            dependency_profile_raw=dependency_profile_raw,
            expected_dependency_profile_pin=expected_dependency_profile_pin)
