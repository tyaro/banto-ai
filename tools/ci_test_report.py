"""Linux CI unittest evidence, streamed to disk; never an S4 acceptance receipt."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import sysconfig
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import ci_shared_fixtures as shared

REPORT = Path("artifacts/ci-tests/unittest.jsonl")
MAX_REPORT_BYTES = 16 * 1024 * 1024


def runtime_metadata():
    # Reject this Windows workstation before discovery can import native tests.
    if sys.platform != "linux":
        raise RuntimeError("Linux CI only")
    distro = platform.freedesktop_os_release()
    if (distro.get("ID"), distro.get("VERSION_ID"), platform.machine()) != ("ubuntu", "24.04", "x86_64"):
        raise RuntimeError("Ubuntu 24.04 x86_64 required")
    if (platform.python_implementation() != "CPython" or sys.version_info[:2] not in ((3, 12), (3, 14))
            or sysconfig.get_config_var("Py_GIL_DISABLED")):
        raise RuntimeError("CPython 3.12/3.14 with GIL required")
    return {"os": "ubuntu", "os_version": "24.04", "kernel": platform.release(), "architecture": platform.machine(),
            "python_version": platform.python_version(), "python_build": sys.version, "compiler": platform.python_compiler(),
            "soabi": sysconfig.get_config_var("SOABI"),
            "runner_image_os": os.environ.get("ImageOS"), "runner_image_version": os.environ.get("ImageVersion"),
            "runner_image_digest": None, "runner_image_digest_status": "not_collected"}


def source_identity(root):
    def git(*args):
        return subprocess.check_output(
            ["git", "-c", "core.fsmonitor=false", "-C", str(root), *args],
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1"}, timeout=30)
    revision = git("rev-parse", "HEAD").decode("ascii").strip()
    if not re.fullmatch("[a-f0-9]{40}", revision) or git("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError("clean source revision required")
    if os.environ.get("GITHUB_SHA", revision) != revision:
        raise RuntimeError("workflow and checkout revisions differ")
    return {"revision": revision, "workflow_sha256": hashlib.sha256((root / ".github/workflows/ci.yml").read_bytes()).hexdigest(),
            "github_run_id": os.environ.get("GITHUB_RUN_ID"), "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}


class Journal:
    def __init__(self, stream):
        self.stream = stream
        self.bytes_written = 0

    def emit(self, event, **fields):
        raw = (json.dumps({"event": event, **fields}, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n").encode()
        if self.bytes_written + len(raw) > MAX_REPORT_BYTES:
            raise RuntimeError("CI evidence byte limit exceeded")
        self.stream.write(raw)
        self.stream.flush()
        self.bytes_written += len(raw)


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, emit, **kwargs):
        super().__init__(*args, **kwargs)
        self.emit = emit
        self.active = None

    def startTest(self, test):
        super().startTest(test)
        self.active, self.outcomes, self.subtests = test, set(), 0
        self.started = time.monotonic()
        self.emit("test_started", test_id=test.id())

    def _outcome(self, test, status, **fields):
        if self.active is not None:
            self.outcomes.add(status)
        self.emit("outcome", test_id=(self.active if self.active is not None else test).id(), status=status, **fields)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._outcome(test, "pass")

    def addError(self, test, err):
        super().addError(test, err)
        self._outcome(test, "error", exception_class=err[0].__name__)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._outcome(test, "failure", exception_class=err[0].__name__)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._outcome(test, "skip", reason=str(reason)[:512], subtest=self.active is not None and test is not self.active)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._outcome(test, "expected_failure", exception_class=err[0].__name__)

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._outcome(test, "unexpected_success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        self.subtests += 1
        if err is not None:
            status = "failure" if issubclass(err[0], test.failureException) else "error"
            # Keep the parent ID and ordinal, not arbitrary subtest parameters.
            self._outcome(test, status, subtest_ordinal=self.subtests, exception_class=err[0].__name__)

    def stopTest(self, test):
        self.emit("test_finished", test_id=test.id(), outcomes=sorted(self.outcomes), elapsed_seconds=time.monotonic() - self.started)
        self.active = None
        super().stopTest(test)


def _cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _cases(item)
        else:
            yield item


def run_suite(suite, emit, stream):
    seen = set()
    for case in _cases(suite):
        name = case.id()
        if name in seen or len(seen) >= 10000:
            raise RuntimeError("duplicate test ID or test count limit exceeded")
        seen.add(name)
        emit("planned_test", test_id=name)
    if not seen:
        raise RuntimeError("no tests discovered")
    count = len(seen)
    del seen
    runner = unittest.TextTestRunner(stream=stream, verbosity=2,
        resultclass=lambda *args, **kwargs: RecordingResult(*args, emit=emit, **kwargs))
    result = runner.run(suite)
    return {"discovered": count, "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
            "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
            "unexpected_successes": len(result.unexpectedSuccesses), "stopped": result.shouldStop,
            "unittest_success": result.wasSuccessful() and result.testsRun > 0 and not result.shouldStop}


def main():
    runtime = runtime_metadata()
    source = source_identity(ROOT)
    path = ROOT / REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        journal = Journal(output)
        journal.emit("run_started", report_version="ci-unittest.2", started_utc=datetime.now(timezone.utc).isoformat(),
                     runtime=runtime, source=source, acceptance_status="not_completed", formal_permission=False)
        # An interruption/discovery failure leaves a partial journal without run_finished.
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
        with shared.capture(journal.emit) as fixtures:
            summary = run_suite(suite, journal.emit, sys.stderr)
        summary.update(shared_fixture_version=shared.VERSION, shared_fixtures=len(fixtures.seen),
                       shared_fixtures_complete=fixtures.complete())
        unchanged = source_identity(ROOT) == source
        journal.emit("run_finished", **summary, source_unchanged=unchanged, acceptance_status="not_completed", formal_permission=False)
        return 0 if summary["unittest_success"] and unchanged and fixtures.complete() else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print("CI test evidence failed: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(2)
