"""Bound one owned Windows process; no campaign launcher or descendant claim."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import subprocess
import time

from . import anomaly_v03_engineering_contract as policy
from . import _anomaly_v03_engineering_runtime as resources
from . import _anomaly_v03_runtime as rt


class UnreapedWorker(RuntimeError):
    """Keep the original process handle available; caller must reconcile it."""
    def __init__(self, process, report):
        self.process, self.report = process, report
        super().__init__("owned worker exit could not be confirmed")


class UnreconciledWorker(UnreapedWorker):
    """Keep the original worker alive until its caller's stop fence confirms."""
    def __init__(self, process, report, stop_fence, fence_error=None):
        super().__init__(process, report)
        self.stop_fence, self.fence_error = stop_fence, fence_error
        self.args = ("owned worker stop fence could not be confirmed",)


def _stop_ack(stop_fence, process):
    value = stop_fence(process)
    rt.require(type(value) is bool, "worker stop fence must return an explicit bool ack")
    return value


def _retain_guarded(error):
    # A missing ack or a failing diagnostic must never fall through to the
    # ordinary kill/wait keeper. The callable must also latch no-new-work.
    while True:
        try:
            if _stop_ack(error.stop_fence, error.process):
                if error.process.poll() is None:
                    error.process.kill()
                    error.process.wait(timeout=30)
                if error.process.returncode is not None:
                    error.process._handle.Close()
                    return
        except BaseException as failure:
            if error.fence_error is None:
                error.fence_error = failure
        try:
            time.sleep(0.25)
        except BaseException:
            pass


def retain_until_exit(error):
    """Keep the original owner, even if interruption or diagnostic output fails."""
    if isinstance(error, UnreconciledWorker):
        return _retain_guarded(error)
    while error.process.returncode is None:
        try:
            error.process.kill()
        except BaseException:
            pass
        try:
            error.process.wait(timeout=30)
        except BaseException:
            pass
    error.process._handle.Close()


def _limits(value):
    rt.require(type(value) is dict and set(value) == {"wall_seconds", "private_bytes", "output_bytes"}, "process limit fields")
    wall = value["wall_seconds"]
    rt.require(type(wall) in (int, float) and math.isfinite(wall) and wall > 0, "process wall limit")
    for key in ("private_bytes", "output_bytes"):
        rt.require(type(value[key]) is int and value[key] > 0, "process byte limit")


def _file_pin(path, maximum):
    rt.regular_path(path, missing=True)
    if not path.exists():
        return None
    if path.stat().st_size > maximum:
        raise resources.ResourceStop("output_limit")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while raw := stream.read(min(64 * 1024, maximum - size + 1)):
            digest.update(raw)
            size += len(raw)
            if size > maximum:
                raise resources.ResourceStop("output_limit")
    return {"bytes": size, "sha256": digest.hexdigest()}


class SourceObjectOutputCallsite:
    """Retain a caller's original worker/streams; never authorize supervision.

    The worker and receipt are Python inputs, without native authentication.
    Borrowed streams stay with their original owner on success or failure.
    """
    def _retain(self, incoming):
        if hasattr(self,'_SourceObjectOutputCallsite__inputs'):
            self.rejected_initialization_inputs = incoming
            self._failed(ValueError("supervisor original callsite initializes once"))
        self.__inputs = self.__inputs_anchor = self.original_inputs = incoming
        self.__binding = self.__binding_anchor = self.original_binding = None
        self.__preparation = None
        self.__callback = self.capture_callback = None
        self.__error = self.error = None
        self.__running = False
        self.__returned = self.capture_return = None
        self.__observed = self.capture_return_observed = False
        self.__rejected = self.rejected_inputs = None
        self.__supervision = self.supervision_inputs = None
        self.pending = incoming

    def _failed(self, error):
        if self.__error is None:self.__error = error
        self.error = self.__error
        self.__error.source_object_supervisor_callsite = self
        self.__error.reader_git_parent = self.__inputs_anchor[0]
        if self.__preparation is not None:
            try:self.__preparation._failed(self.__error)
            except BaseException as first:
                self.__error = self.error = first
                first.source_object_supervisor_callsite = self
                raise
        raise self.__error

    def bind_originals(self, preparation, worker):
        if self.__binding_anchor is not None:
            self.rejected_original_binding = (preparation,worker)
            self._failed(ValueError("supervisor original worker binding cannot be replaced"))
        self.__binding = self.__binding_anchor = self.original_binding = (preparation, worker)
        try:
            from . import _anomaly_v03_reader_dependencies as dependencies
            rt.require(type(preparation) is dependencies.SourceObjectBatchContractPreparation,
                       "supervisor original source object preparation")
            self.__preparation = preparation
            self.__callback = self.capture_callback = preparation.capture_raw
            preparation.bind_supervisor_callsite(self)
        except BaseException as error:self._failed(error)

    def _bindings(self):
        if self.__error is not None:raise self.__error
        parent = self.__inputs[0]
        preparation, worker = self.__binding
        rows = parent._ReaderGitParent__source_object_supervisor_callsites
        rt.require(self.__inputs is self.__inputs_anchor and self.__binding is self.__binding_anchor and
                   self.original_inputs is self.__inputs and self.original_binding is self.__binding and
                   self.capture_callback is self.__callback and self.capture_return is self.__returned and
                   self.capture_return_observed is self.__observed and self.rejected_inputs is self.__rejected and
                   self.supervision_inputs is self.__supervision and
                   parent.source_object_supervisor_callsites is rows and any(row is self for row in rows) and
                   parent._ReaderGitParent__source_object_batch_owner is preparation and
                   preparation._SourceObjectBatchContractPreparation__inputs[0] is parent and
                   worker is not None and parent.worker is worker,
                   "supervisor same original parent worker streams and private bindings")

    def capture(self, incoming):
        if self.__error is not None:raise self.__error
        try:
            if len(incoming) != len(self.__inputs) or not all(a is b for a,b in zip(incoming,self.__inputs)):
                self.__rejected = self.rejected_inputs = incoming
                raise ValueError("supervisor original capture inputs cannot be replaced")
            self._bindings()
            preparation = self.__binding[0]
            preparation._fixed()
            if self.__observed:return self.__returned
            rt.require(not self.__running, "supervisor original capture cannot reenter")
            self.__running = True
            _, index, stdout, stderr, receipt, code, partial, wall = self.__inputs
            rt.require(type(wall) is tuple and len(wall) == 3,
                       "supervisor original absolute read window required")
            self.pending = self.__inputs
            returned = self.__callback(index,stdout,stderr,receipt,exit_code=code,partial=partial,read_wall=wall)
            self.__returned = returned  # Save the literal return before checking callback changes.
            self.__observed = True
            if self.capture_return is None:self.capture_return = returned
            if self.capture_return_observed is False:self.capture_return_observed = True
            self._bindings();preparation._fixed()
            self.pending = None
            return returned
        except BaseException as error:self._failed(error)

    def refuse_supervision(self, incoming):
        # The actual supervisor entrance retains its original arguments before
        # clock, path, runtime probe, output FileIO or process creation.
        if self.__supervision is None:self.__supervision = self.supervision_inputs = incoming
        else:self.rejected_supervision_inputs = incoming
        self._failed(ValueError("source object supervisor callsite remains preparation only"))


def supervise(argv, cwd, control_root, limits, *, stdout_name="report.json", runtime_probe=None, boundary=lambda: None,
              on_started=None, resource_probe=None, stop_fence=None, source_object_callsite=None):
    """Return observations after reaping the owned process; caller saves the report.

    control_root is newly claimed and every output is exclusive. The caller owns
    command/source authorization and budget selection. Only this process is
    supervised; descendants require a separate ownership contract. An optional
    on_started callback may observe the original owned handle before polling.
    Its failure follows the same stop/reap path; it must not transfer ownership.
    resource_probe optionally returns a latched cooperative stop reason at each
    budget sample. Its errors also stop/reap the owned child.
    A stop_fence opts into a caller-held no-new-work/owned-Job ack. Only an
    explicit True permits kill/wait/handle close. False or any fence error
    preserves the original worker owner, without reading logs or final context.
    This callback contract is not an authenticated Job or descendant report.
    """
    if source_object_callsite is not None:
        rt.require(type(source_object_callsite) is SourceObjectOutputCallsite,
                   "supervisor exact original source object callsite")
        source_object_callsite.refuse_supervision((argv,cwd,control_root,limits,stdout_name,runtime_probe,
                                                boundary,on_started,resource_probe,stop_fence))
    _limits(limits)
    rt.require(stop_fence is None or callable(stop_fence), "worker stop fence must be callable")
    rt.require(type(argv) is list and argv and all(type(x) is str and x for x in argv), "process argv")
    rt.require(stdout_name in ("report.json", "stdout.jsonl"), "process stdout name")
    cwd = rt.regular_path(Path(cwd), directory=True)
    control = Path(control_root).absolute()
    rt.regular_path(control.parent, directory=True)
    rt.regular_path(control, directory=True, missing=True)
    control.mkdir()  # A previous partial directory is evidence, never reused.
    stdout_path, stderr_path = control / stdout_name, control / "stderr.json"
    probe = runtime_probe or (lambda: resources.probe_runtime(cwd))
    process, before, after, free_before, free_after = None, None, None, None, None
    errors, peak, reason = [], 0, None
    observation_failed = False
    started = time.monotonic()

    def error(stage, value):
        nonlocal observation_failed
        observation_failed = True
        try:
            errors.append({"stage": stage, "error_type": type(value).__name__})
        except BaseException:
            pass

    def observe_memory():
        nonlocal peak
        peak = max(peak, resources.memory_bytes(process._handle)["peak_private_bytes"])

    def fenced_report(confirmed):
        return {"format": "anomaly-v03-owned-process-monitor-v1", "argv": list(argv), "limits": dict(limits),
            "status": "failed", "exit_code": process.returncode,
            "worker_pid": process.pid, "worker_started": True,
            "worker_exit_confirmed": process.returncode is not None, "stop_reason": reason,
            "elapsed_seconds": time.monotonic() - started, "peak_worker_private_bytes": peak,
            "observation_errors": errors, "output": None, "stderr": None,
            "runtime_before": before, "runtime_after": after, "free_before": free_before, "free_after": free_after,
            "worker_stop_fence_confirmed": confirmed,
            "formal_permission": False, "performance_status": "not_evaluated"}

    def budget():
        if resource_probe is not None:
            reason = resource_probe()
            rt.require(reason is None or (type(reason) is str and bool(reason)), "resource stop reason")
            if reason is not None:
                return reason
        if time.monotonic() - started > limits["wall_seconds"]:
            return "time_limit"
        if peak > limits["private_bytes"]:
            return "memory_limit"
        total = sum(path.stat().st_size for path in (stdout_path, stderr_path) if path.exists())
        return "output_limit" if total > limits["output_bytes"] else None

    try:
        before = probe()
        policy.validate_runtime(before)
        free_before = resources.require_start_resources(cwd)
        boundary()
        reason = budget()
        if reason is None:
            with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
                process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                if on_started is not None:
                    on_started(process)
                while process.poll() is None:
                    observe_memory()
                    reason = budget()
                    if reason is not None:
                        break
                    time.sleep(0.25)
    except resources.ResourceStop as value:
        reason = value.reason
    except KeyboardInterrupt:
        reason = "interrupted"
    except Exception as value:
        error("supervision", value)
        reason = reason or "observation_error"
    finally:
        if process is not None:
            if stop_fence is not None:
                fence_error = None
                try:
                    acknowledged = _stop_ack(stop_fence, process)
                except BaseException as value:
                    acknowledged, fence_error = False, value
                    error("worker_stop_fence", value)
                if not acknowledged:
                    reason = reason or "worker_stop_fence_unconfirmed"
                    raise UnreconciledWorker(process, fenced_report(False), stop_fence, fence_error)
            try:
                running = process.poll() is None
            except BaseException as value:
                error("worker_state", value)
                running = True
            if running:
                try:
                    process.kill()
                except BaseException as value:
                    error("worker_stop", value)
            try:
                process.wait(timeout=30)
            except BaseException as value:
                error("worker_reap", value)
            try:
                observe_memory()
            except BaseException as value:
                error("final_worker_memory", value)
            try:
                process.poll()
            except BaseException as value:
                error("final_worker_state", value)
        try:
            after = probe()
            policy.validate_runtime(after)
            if before is not None and before != after:
                reason = "runtime_changed"
            free_after = resources.free_resources(cwd)
            boundary()
        except resources.ResourceStop as value:
            reason = reason or value.reason
        except BaseException as value:
            error("final_context", value)
            reason = reason or "observation_error"
    output, stderr = None, None
    exit_code = process.returncode if process is not None else None
    # A live/unconfirmed worker may still be appending. Return ownership without
    # scanning its logs, and bound reads even after a confirmed exit.
    if process is None or exit_code is not None:
        try:
            limit_reason = budget()
            reason = reason or limit_reason
            if limit_reason != "output_limit":
                output = _file_pin(stdout_path, limits["output_bytes"])
                remaining = limits["output_bytes"] - (output["bytes"] if output else 0)
                stderr = _file_pin(stderr_path, remaining)
        except resources.ResourceStop as value:
            reason = value.reason
        except BaseException as value:
            error("output_observation", value)
    if process is not None and exit_code is not None:
        # CPython's Windows Popen retains this handle after wait(). Close only
        # after the final memory sample; no later process observation is needed.
        try:
            process._handle.Close()
        except BaseException as value:
            error("worker_handle_close", value)
            if stop_fence is not None:
                reason = reason or "worker_handle_close"
                raise UnreconciledWorker(process, fenced_report(True), stop_fence, value)
    complete = exit_code == 0 and reason is None and not observation_failed and before is not None and after == before
    report = {"format": "anomaly-v03-owned-process-monitor-v1", "argv": list(argv), "limits": dict(limits),
        "status": "complete" if complete else "failed", "exit_code": exit_code,
        "worker_pid": process.pid if process is not None else None, "worker_started": process is not None,
        "worker_exit_confirmed": exit_code is not None, "stop_reason": reason,
        "elapsed_seconds": time.monotonic() - started, "peak_worker_private_bytes": peak,
        "observation_errors": errors, "output": output, "stderr": stderr,
        "runtime_before": before, "runtime_after": after, "free_before": free_before, "free_after": free_after,
        "formal_permission": False, "performance_status": "not_evaluated"}
    if process is not None and exit_code is None:
        if stop_fence is not None:
            report["worker_stop_fence_confirmed"] = True
            raise UnreconciledWorker(process, report, stop_fence)
        raise UnreapedWorker(process, report)
    return report
