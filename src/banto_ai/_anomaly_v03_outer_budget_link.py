"""Relay a stage's local limits and receipts to a live cooperative outer clock.

The local sampler keeps its original directory/time caps and is closed by its
stage. The outer sampler is owned and closed only by the composing caller.
"""
from __future__ import annotations


class LinkedBudget:
    def __init__(self, inner, outer, *, stage, role_map=None):
        outer.require_stage(stage, inner.root)
        self.inner = inner
        self.outer = outer
        self.stage = stage
        self.role_map = dict(role_map or {})

    def __getattr__(self, name):
        return getattr(self.inner, name)

    def start(self):
        self.outer.checkpoint(self.stage)
        self.inner.start()
        return self

    def probe(self):
        return self.inner.probe() or self.outer.probe()

    def checkpoint(self, *args):
        self.inner.checkpoint(*args)
        self.outer.checkpoint(self.stage)

    def record_role(self, role, status, pin=None, pid=None, exit_confirmed=None):
        self.inner.record_role(role, status, pin, pid, exit_confirmed)
        self.outer.record_role(self.role_map.get(role, role), status, pin, pid,
                               exit_confirmed)

    def record_output(self, name, pin):
        self.inner.record_output(name, pin)
        self.outer.record_output(name, pin)

    def close(self):
        report = self.inner.close()
        reason = self.outer.probe()
        report['coordinated_outer_root'] = str(self.outer.root)
        report['coordinated_outer_stage'] = self.stage
        report['outer_sampler_closed_by_this_stage'] = False
        if reason is not None:
            report.update(passed=False, stop_reason=report['stop_reason'] or reason)
        return report
