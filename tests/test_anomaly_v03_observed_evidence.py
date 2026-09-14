"""Fault tests for acquisition adoption and native-shaped evidence observations."""
from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
import warnings
from unittest.mock import patch

from banto_ai import _anomaly_v03_windows as win
from tests.fixtures import anomaly_v03_observed_evidence as bridge
from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_prepublication as prep
from tests.fixtures import anomaly_v03_publication_model as model
from tests.fixtures.anomaly_v03_tracked_open import TrackedOpen
from tests import test_anomaly_v03_handle_owner as owner_tests
from tests import test_anomaly_v03_prepublication as prep_tests

USER = "S-1-5-21-1-2-3-1001"
FILES = {"facts.json": b'{"count":2}\n'}
MARKER = model.marker_bytes("a" * 40, FILES)


def setup(adopt=True):
    table = owner_tests.ClosingTable((101, 202, 303))
    leases = []
    for index, raw in enumerate((None, FILES["facts.json"], MARKER)):
        handle = (index + 1) * 101
        identity = {"directory": raw is None, "volume": 7, "file_id": bytes([index + 1] * 16).hex()}
        sd = {"protected": True, "owner": USER, "group": USER,
              "aces": win._dacl(USER, "private", raw is None)[1],
              "integrity": "S-1-16-8192", "mandatory_policy": 1}
        view = SimpleNamespace(handle=handle, identity=identity, raw=raw, sd=sd)
        def check(view=view):
            table.calls.append(("check", view.handle))
            return dict(view.identity)
        def read(view=view):
            table.calls.append(("read", view.handle))
            return view.raw
        def security(handle, view=view):
            table.calls.append(("sd", handle))
            return dict(view.sd)
        view.check, view.read, view.api = check, read, SimpleNamespace(security=security)
        lease = TrackedOpen(table)
        lease.acquire(lambda cell, handle=handle: setattr(cell, "handle", handle), lambda h, view=view: view)
        leases.append(lease)
    observations = tuple(bridge.inspect_native(lease, expected=raw, private_user=USER)
                         for lease, raw in zip(leases, (None, FILES["facts.json"], MARKER)))
    journal = model.PublicationJournal(hashlib.sha256(MARKER).hexdigest())
    group = bridge.AcquiredOwner()
    if adopt:
        group.adopt(leases=tuple(leases), journal=journal, observations=observations, parents=(None, 0, 0))
    table.calls.clear()
    return table, tuple(leases), observations, journal, group


def record(group, **changes):
    args = dict(source_revision="a" * 40, files=FILES, marker=MARKER,
                bindings=((1, "facts.json"), (2, None)), private_indices=(0, 1, 2), user=USER)
    args.update(changes)
    return bridge.capture_record(group, "prepare", **args)


class AcquiredOwnerTests(unittest.TestCase):
    def test_adopt_borrow_and_finish_share_one_raw_close_authority(self):
        table, leases, _, journal, group = setup()
        self.assertEqual(group.owner.borrowed((1,), lambda pins: pins[0].handle), 202)
        group.finish()
        self.assertEqual([r for r in table.calls if r[0] == "close"], [("close", n) for n in (303, 202, 101)])
        self.assertTrue(group.owner.snapshot()["all_closes_confirmed"])
        self.assertTrue(all(lease.close_state == "closed" for lease in leases))
        self.assertEqual(journal.snapshot()["commit_observation"], "not_started")

    def test_graph_or_allocation_failure_leaves_sources_caller_owned(self):
        for failure in ("graph", "allocation"):
            with self.subTest(failure=failure):
                table, leases, observations, journal, group = setup(False)
                parents = (None, 2, 0) if failure == "graph" else (None, 0, 0)
                manager = patch.object(owned, "HandleOwner", side_effect=MemoryError()) if failure == "allocation" else patch.object(owned, "MAX_HANDLES", 32)
                with manager, self.assertRaises((MemoryError, owned.OwnershipError)):
                    group.adopt(leases=leases, journal=journal, observations=observations, parents=parents)
                self.assertFalse(group.active)
                self.assertFalse(table.calls)
                for lease in reversed(leases):
                    lease.close()
                self.assertFalse(table.live)

    def test_partial_attachment_failure_before_or_after_assignment_keeps_caller_authority(self):
        for after in (False, True):
            table, leases, observations, journal, group = setup(False)
            def assign(cell, name, value):
                if name == "_custodian" and cell is leases[1]:
                    if after:
                        object.__setattr__(cell, name, value)
                    raise MemoryError()
                object.__setattr__(cell, name, value)
            with patch.object(TrackedOpen, "__setattr__", assign), self.assertRaises(MemoryError):
                group.adopt(leases=leases, journal=journal, observations=observations, parents=(None, 0, 0))
            self.assertFalse(group.active)
            for lease in reversed(leases):
                lease.close()
            self.assertFalse(table.live)
            self.assertEqual(sum(r[0] == "close" for r in table.calls), 3)

    def test_lost_adoption_reply_leaves_receiver_reachable(self):
        table, leases, observations, journal, group = setup(False)
        try:
            group.adopt(leases=leases, journal=journal, observations=observations, parents=(None, 0, 0))
            raise MemoryError()
        except MemoryError as primary:
            with self.assertRaises(MemoryError) as caught:
                group.finish(primary=primary)
            self.assertIs(caught.exception, primary)
        self.assertFalse(table.live)

    def test_direct_close_and_reacquire_after_transfer_stop_even_if_swallowed(self):
        for action in ("close", "acquire"):
            table, leases, _, journal, group = setup()
            try:
                if action == "close":
                    leases[1].close()
                else:
                    leases[1].acquire(lambda cell: None, lambda h: None)
            except owned.OwnershipError:
                pass
            self.assertFalse(table.calls)
            with self.assertRaises(owned.OwnershipError):
                group.owner.borrowed((0,), lambda pins: None)
            with self.assertRaises(owned.OwnershipError):
                group.finish()
            self.assertFalse(table.live)
            self.assertEqual(journal.snapshot()["model_status"], "stopped")

    def test_unknown_close_and_reused_number_are_never_closed_twice(self):
        table, leases, _, journal, group = setup()
        def lost():
            table.live[303] = "new-object"
            raise MemoryError()
        table.hooks[303] = lost
        with self.assertRaises(MemoryError):
            group.finish()
        with self.assertRaises(owned.OwnershipError):
            group.finish()
        self.assertEqual(sum(row == ("close", 303) for row in table.calls), 1)
        self.assertEqual(table.live, {303: "new-object"})
        self.assertTrue(group.owner.snapshot()["resource_stop"])

    def test_swallowed_second_adoption_stops_receiver_without_raw_close(self):
        table, leases, observations, journal, group = setup()
        with self.assertRaises(owned.OwnershipError):
            group.adopt(leases=leases, journal=journal, observations=observations, parents=(None, 0, 0))
        self.assertFalse(table.calls)
        self.assertEqual(journal.snapshot()["model_status"], "stopped")
        with self.assertRaises(owned.OwnershipError):
            group.owner.borrowed((0,), lambda pins: None)
        with self.assertRaises(owned.OwnershipError):
            group.finish()
        self.assertFalse(table.live)

    def test_unavailable_or_mismatched_acquisition_rejected_before_transfer(self):
        for corrupt in ("closed", "pin", "duplicate", "prior_error"):
            table, leases, observations, journal, group = setup(False)
            if corrupt == "closed":
                leases[1].close()
            elif corrupt == "pin":
                observations = (observations[0], replace(observations[1], pin=replace(observations[1].pin, handle=999)), observations[2])
            elif corrupt == "duplicate":
                leases, observations = (leases[0], leases[1], leases[1]), (observations[0], observations[1], observations[1])
            else:
                leases[1]._record(ValueError())
            with self.assertRaises((owned.OwnershipError, ValueError)):
                group.adopt(leases=leases, journal=journal, observations=observations, parents=(None, 0, 0))
            self.assertFalse(group.active)


class ObservedEvidenceTests(unittest.TestCase):
    def test_real_shaped_bytes_identity_and_sd_reach_barrier_before_release(self):
        table, leases, _, journal, group = setup()
        journal.begin("prepare")
        captured = record(group)
        data = json.loads(captured.raw)
        self.assertEqual(len(data["observations"]), 3)
        self.assertFalse(data["native_observations_authenticated"])
        sink = prep_tests.Sink(table.calls)
        gate = prep.EvidenceBarrier(sink, owner=group.owner, protected=(0,))
        gate.save_and_release(captured, (1, 2))
        saved = table.calls.index(("save", "prepare"))
        self.assertTrue(all(i > saved for i, row in enumerate(table.calls) if row[0] == "close"))
        self.assertEqual(gate.snapshot()["steps"][0]["state"], "released")
        group.finish()
        self.assertFalse(table.live)
        self.assertEqual(sink.records["prepare"], captured.raw)

    def test_identity_bytes_descriptor_or_policy_changes_stop_before_save(self):
        for fault in ("identity", "bytes", "policy", "descriptor_budget"):
            table, leases, _, journal, group = setup()
            if fault == "identity":
                leases[1].observed.identity["file_id"] = "ff" * 16
            elif fault == "bytes":
                leases[1].observed.raw = b"changed"
            elif fault == "policy":
                leases[1].observed.sd["owner"] = "S-1-5-18"
            else:
                leases[1].observed.sd["extra"] = "x" * 2048
            with self.assertRaises((owned.OwnershipError, win._Failure)):
                record(group)
            self.assertEqual(journal.snapshot()["model_status"], "stopped")
            self.assertFalse(any(row[0] == "close" for row in table.calls))
            with self.assertRaises((owned.OwnershipError, win._Failure)):
                group.finish()
            self.assertFalse(table.live)

    def test_complete_exact_file_bindings_are_required(self):
        for bindings in ((), ((1, "facts.json"),), ((1, None), (2, None)),
                         ((1, "facts.json"), (1, None)), ((0, "facts.json"), (2, None)),
                         ((True, "facts.json"), (2, None))):
            _, _, _, journal, group = setup()
            with self.assertRaises(owned.OwnershipError):
                record(group, bindings=bindings)
            self.assertEqual(journal.snapshot()["model_status"], "stopped")

    def test_swapped_files_even_with_valid_inventory_fail_native_readback(self):
        _, _, _, journal, group = setup()
        with self.assertRaises(owned.OwnershipError):
            record(group, bindings=((2, "facts.json"), (1, None)))
        self.assertEqual(journal.snapshot()["model_status"], "stopped")

    def test_private_file_omission_and_duplicate_indices_are_rejected(self):
        for indices in ((0,), (0, 1, 1, 2), (0, True, 2), (0, 1, 9)):
            _, _, _, journal, group = setup()
            with self.assertRaises(owned.OwnershipError):
                record(group, private_indices=indices)
            self.assertEqual(journal.snapshot()["model_status"], "stopped")

    def test_swallowed_direct_close_during_observation_cannot_return_record(self):
        table, leases, _, journal, group = setup()
        original = leases[1].observed.read
        def read():
            try:
                leases[1].close()
            except owned.OwnershipError:
                pass
            return original()
        leases[1].observed.read = read
        with self.assertRaises(owned.OwnershipError):
            record(group)
        self.assertEqual(table.calls[-1], ("read", 202))
        self.assertFalse(any(row[0] == "close" for row in table.calls))
        with self.assertRaises(owned.OwnershipError):
            group.finish()
        self.assertFalse(table.live)

    def test_owner_only_resource_stop_aborts_each_observation_boundary(self):
        for boundary in ("check", "read", "sd"):
            table, leases, _, journal, group = setup()
            view = leases[1].observed
            target = view.api if boundary == "sd" else view
            name = "security" if boundary == "sd" else boundary
            original = getattr(target, name)
            def stop(*args):
                result = original(*args)
                journal.stop(resource=True)
                return result
            setattr(target, name, stop)
            with self.assertRaises(MemoryError):
                record(group)
            self.assertEqual(table.calls[-1], (boundary, 202))
            self.assertFalse(any(row[1:] == (303,) for row in table.calls))
            self.assertTrue(group.owner.snapshot()["resource_stop"])
            with self.assertRaises(MemoryError):
                group.finish()
            self.assertFalse(table.live)

    def test_saved_reply_loss_keeps_all_source_handles_until_terminal_release(self):
        table, leases, _, journal, group = setup()
        journal.begin("prepare")
        captured = record(group)
        sink = prep_tests.Sink(table.calls)
        sink.after = owner_tests.raising(MemoryError())
        gate = prep.EvidenceBarrier(sink, owner=group.owner, protected=(0,))
        with self.assertRaises(MemoryError):
            gate.save_and_release(captured, (1, 2))
        self.assertEqual(sink.records["prepare"], captured.raw)
        self.assertFalse(any(row[0] == "close" for row in table.calls))
        self.assertEqual(gate.snapshot()["steps"][0]["state"], "unknown")
        with self.assertRaises(MemoryError):
            group.finish()
        self.assertFalse(table.live)


class ObservedProbeTests(unittest.TestCase):
    def test_resource_stop_in_acquisition_or_teardown_emits_only_fixed_notice(self):
        from tests.fixtures import anomaly_v03_observed_evidence_probe as probe
        for late in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                source = SimpleNamespace(_leases=[], _resource=False)
                source.connect = owner_tests.raising(ValueError() if late else MemoryError())
                # connect accepts the new source path but never opens anything.
                fail = source.connect
                source.connect = lambda path: fail()
                sink = SimpleNamespace(_resource=False)
                sink.finish = lambda **kwargs: (_ for _ in ()).throw(MemoryError()) if late else None
                sink.snapshot = lambda: self.fail("resource stop must not build snapshot")
                with patch.object(probe, "BASE", Path(directory)), \
                     patch.object(probe, "WindowsPrivateSink", side_effect=(source, sink)), \
                     patch.object(probe.subprocess, "check_output", side_effect=("a" * 40, b"")), \
                     patch.object(probe.sys, "argv", ["probe", "--expected-head", "a" * 40, "--attempt", "1"]), \
                     patch.object(probe.os, "write") as notice:
                    self.assertEqual(probe.main(), 80)
                notice.assert_called_once_with(1, b'{"observed_prepare":"resource_stop","resource_stop":true}\n')
                self.assertFalse((Path(directory) / "attempt-1/probe-result.json").exists())

    def test_probe_sources_compile_without_finally_return_warnings(self):
        base = Path(__file__).parent / "fixtures"
        with warnings.catch_warnings():
            warnings.simplefilter("error", SyntaxWarning)
            for name in ("private_sink", "observed_evidence"):
                path = base / ("anomaly_v03_" + name + "_probe.py")
                compile(path.read_text(encoding="utf-8"), str(path), "exec")
