"""In-memory handle lifetime/fault tests; never open or close OS handles."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from tests.fixtures import anomaly_v03_handle_owner as owned
from tests.fixtures import anomaly_v03_publication_model as model
from tests.fixtures import anomaly_v03_rename_adapter as rename
from tests import test_anomaly_v03_rename_adapter as rename_tests


def slots():
    root = rename.ObjectPin(101, 7, b"R" * 16, True)
    child = rename.ObjectPin(202, 7, b"D" * 16, True)
    leaf = rename.ObjectPin(303, 7, b"F" * 16, False, "a" * 64)
    marker = rename.ObjectPin(404, 7, b"M" * 16, False, "b" * 64)
    return (owned.OwnedSlot(root, None), owned.OwnedSlot(child, 0),
            owned.OwnedSlot(leaf, 1), owned.OwnedSlot(marker, 0))


def ready_journal():
    journal = model.PublicationJournal("b" * 64)
    for step in model.STEPS:
        journal.begin(step)
        journal.succeed(step)
    return journal


class ClosingTable:
    def __init__(self, handles):
        self.live = {handle: "original" for handle in handles}
        self.calls, self.results, self.hooks = [], {}, {}
        self.error = 5

    def close_handle(self, handle):
        self.calls.append(("close", handle))
        if handle in self.hooks:
            self.hooks[handle]()
        if handle in self.results:
            return self.results[handle]
        if self.live.pop(handle, None) != "original":
            raise AssertionError("stale_or_double_close")
        return 1

    def get_last_error(self):
        self.calls.append(("error",))
        if "error" in self.hooks:
            self.hooks["error"]()
        return self.error


def setup(journal=None):
    entries = slots()
    backend = ClosingTable(row.pin.handle for row in entries)
    journal = ready_journal() if journal is None else journal
    owner = owned.HandleOwner(backend, journal=journal, slots=entries)
    return backend, owner, journal


def raising(error):
    def fail():
        raise error
    return fail


class HandleOwnerTests(unittest.TestCase):
    def assert_states(self, owner, expected):
        state = owner.snapshot()
        self.assertEqual([row["state"] for row in state["handles"]], expected)
        for flag in ("retry_permitted", "path_cleanup_permitted", "formal_permission", "execution_authenticated"):
            self.assertIs(state[flag], False)
        self.assertEqual(state["acceptance_status"], "not_completed")

    def test_constructor_rejects_invalid_graph_without_taking_ownership(self):
        entries = slots()
        variants = [(), list(entries), entries * 9, (None,), (entries[0], entries[0]),
                    (replace(entries[0], parent=0),),
                    (entries[0], replace(entries[1], parent=True)),
                    (entries[0], replace(entries[1], parent=3)),
                    (entries[0], replace(entries[1], parent=-1)),
                    (entries[0], replace(entries[1], pin=replace(entries[1].pin, volume=8))),
                    (entries[0], replace(entries[1], pin=replace(entries[1].pin, handle=101))),
                    (entries[0], replace(entries[1], pin=replace(entries[1].pin, file_id=b"R" * 16))),
                    (replace(entries[2], parent=None),),
                    (entries[0], replace(entries[2], parent=0), replace(entries[3], parent=1))]
        for rows in variants:
            with self.subTest(rows=rows):
                backend = ClosingTable(row.pin.handle for row in entries)
                with self.assertRaises(ValueError):
                    owned.HandleOwner(backend, journal=ready_journal(), slots=rows)
                self.assertEqual(backend.calls, [])
                self.assertEqual(len(backend.live), 4)
        for journal in (None, object()):
            with self.assertRaises(owned.OwnershipError):
                owned.HandleOwner(backend, journal=journal, slots=entries)
        journal = ready_journal()
        journal.finish_teardown(success=True)
        with self.assertRaises(owned.OwnershipError):
            owned.HandleOwner(backend, journal=journal, slots=entries)
        self.assertEqual(backend.calls, [])

    def test_exact_capacity_closes_each_handle_once(self):
        entries = [slots()[0]]
        for index in range(1, 32):
            pin = rename.ObjectPin(1000 + index, 7, index.to_bytes(16, "little"), False, "c" * 64)
            entries.append(owned.OwnedSlot(pin, 0))
        backend = ClosingTable(row.pin.handle for row in entries)
        owner = owned.HandleOwner(backend, journal=ready_journal(), slots=tuple(entries))
        owner.finish()
        self.assertEqual(len(backend.calls), 32)
        self.assertEqual(backend.live, {})
        self.assertTrue(owner.snapshot()["all_closes_confirmed"])

    def test_reverse_acquisition_order_closes_descendants_before_ancestors(self):
        backend, owner, journal = setup()
        owner.finish()
        self.assertEqual(backend.calls, [("close", handle) for handle in (404, 303, 202, 101)])
        self.assertEqual(backend.live, {})
        self.assert_states(owner, ["closed"] * 4)
        self.assertEqual(owner.snapshot()["owner_status"], "finished")
        self.assertEqual(journal.snapshot()["model_status"], "complete")

    def test_failure_at_each_close_still_attempts_remaining_distinct_handles(self):
        for handle in (404, 303, 202, 101):
            with self.subTest(handle=handle):
                backend, owner, journal = setup()
                error = ValueError("private-path")
                backend.hooks[handle] = raising(error)
                with self.assertRaises(ValueError) as caught:
                    owner.finish()
                self.assertIs(caught.exception, error)
                expected = ["unknown" if row.pin.handle == handle else "closed" for row in slots()]
                self.assert_states(owner, expected)
                self.assertEqual(backend.live, {handle: "original"})
                self.assertEqual(backend.calls, [("close", value) for value in (404, 303, 202, 101)])
                self.assertEqual(journal.snapshot()["teardown"], "failed")
                self.assertEqual(journal.snapshot()["commit_observation"], "confirmed")
                self.assertEqual(journal.snapshot()["model_status"], "stopped")

    def test_close_response_loss_never_retries_reused_handle_number(self):
        backend, owner, journal = setup()
        def lost_reply():
            del backend.live[404]
            backend.live[404] = "unrelated-new-handle"
            raise MemoryError()
        backend.hooks[404] = lost_reply
        with self.assertRaises(MemoryError):
            owner.finish()
        before = backend.calls[:]
        with self.assertRaises(owned.OwnershipError):
            owner.finish()
        self.assertEqual(backend.calls, before)
        self.assertEqual(backend.live, {404: "unrelated-new-handle"})
        self.assert_states(owner, ["closed", "closed", "closed", "unknown"])
        self.assertTrue(owner.snapshot()["resource_stop"])
        self.assertTrue(journal.snapshot()["resource_stop"])

    def test_false_close_reads_error_before_next_handle(self):
        for code in (5, 6, 8, 14, 39, 112, 1450, 1451, 1452, 1453, 1454, 1455, 1816):
            with self.subTest(code=code):
                backend, owner, journal = setup()
                backend.results[404], backend.error = 0, code
                with self.assertRaises(owned.OwnershipError) as caught:
                    owner.finish()
                self.assertEqual(caught.exception.winerror, code)
                self.assertEqual(backend.calls[:3], [("close", 404), ("error",), ("close", 303)])
                self.assertEqual(owner.snapshot()["handles"][3]["winerror"], code)
                self.assertEqual(journal.snapshot()["resource_stop"], code not in (5, 6))
                self.assert_states(owner, ["closed", "closed", "closed", "unknown"])

    def test_bad_native_return_or_unavailable_error_cannot_confirm_close(self):
        for result in (True, False, None, "1", 1 << 31, -(1 << 31) - 1):
            with self.subTest(result=result):
                backend, owner, journal = setup()
                backend.results[404] = result
                with self.assertRaises(owned.OwnershipError):
                    owner.finish()
                self.assertNotIn(("error",), backend.calls)
                self.assert_states(owner, ["closed", "closed", "closed", "unknown"])
        for code in (0, True, None, "5", -1, 1 << 32):
            with self.subTest(code=code):
                backend, owner, journal = setup()
                backend.results[404], backend.error = 0, code
                with self.assertRaises(owned.OwnershipError):
                    owner.finish()
                self.assertEqual(len(backend.calls), 5)
                self.assert_states(owner, ["closed", "closed", "closed", "unknown"])

    def test_last_error_exception_does_not_abandon_other_handles(self):
        backend, owner, journal = setup()
        backend.results[404] = 0
        backend.hooks["error"] = raising(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            owner.finish()
        self.assertEqual(backend.calls[-3:], [("close", 303), ("close", 202), ("close", 101)])
        self.assert_states(owner, ["closed", "closed", "closed", "unknown"])

    def test_primary_failure_wins_while_later_resource_failure_escalates(self):
        backend, owner, journal = setup()
        primary = ValueError("original-operation")
        backend.hooks[404] = raising(RuntimeError("close"))
        backend.hooks[303] = raising(MemoryError())
        with self.assertRaises(ValueError) as caught:
            owner.finish(primary=primary)
        self.assertIs(caught.exception, primary)
        self.assertTrue(journal.snapshot()["resource_stop"])
        self.assertEqual(journal.snapshot()["failure_reason"], "operation_error")
        self.assert_states(owner, ["closed", "closed", "unknown", "unknown"])

    def test_early_abort_stops_pending_publication_before_closing(self):
        journal = model.PublicationJournal("b" * 64)
        journal.begin("prepare")
        backend, owner, journal = setup(journal)
        def observe_stop():
            self.assertEqual(journal.snapshot()["model_status"], "stopped")
            self.assertEqual(journal.snapshot()["steps"][0]["state"], "unknown")
        backend.hooks[404] = observe_stop
        owner.finish()
        self.assertEqual(journal.snapshot()["teardown"], "succeeded")
        self.assertEqual(journal.snapshot()["model_status"], "stopped")
        self.assertEqual(journal.snapshot()["commit_observation"], "not_started")
        self.assert_states(owner, ["closed"] * 4)

    def test_existing_failure_is_not_cleared_by_successful_releases(self):
        journal = ready_journal()
        journal.stop(resource=True)
        backend, owner, journal = setup(journal)
        owner.finish()
        self.assertEqual(journal.snapshot()["failure_reason"], "resource_stop")
        self.assertTrue(journal.snapshot()["resource_stop"])
        self.assertEqual(journal.snapshot()["model_status"], "stopped")
        self.assertTrue(owner.snapshot()["all_closes_confirmed"])
        self.assertTrue(owner.snapshot()["resource_stop"])

    def test_swallowed_reentry_does_not_double_close_or_report_publication_success(self):
        backend, owner, journal = setup()
        def reenter():
            try:
                owner.finish()
            except owned.OwnershipError:
                pass
        backend.hooks[404] = reenter
        with self.assertRaises(owned.OwnershipError):
            owner.finish()
        self.assertEqual(len(backend.calls), 4)
        self.assert_states(owner, ["closed"] * 4)
        self.assertEqual(journal.snapshot()["model_status"], "stopped")
        self.assertEqual(journal.snapshot()["teardown"], "succeeded")

    def test_nested_resource_failure_and_classifier_failure_are_conservative(self):
        nested = RuntimeError("outer")
        nested.__cause__ = owned.OwnershipError("close_failed", 1453)
        for error in (nested, ExceptionGroup("group", [nested]), rename.BudgetStop()):
            with self.subTest(error=type(error).__name__):
                backend, owner, journal = setup()
                backend.hooks[404] = raising(error)
                with self.assertRaises(type(error)):
                    owner.finish()
                self.assertTrue(journal.snapshot()["resource_stop"])
                self.assertEqual(len(backend.calls), 4)
        backend, owner, journal = setup()
        backend.hooks[404] = raising(ValueError())
        with patch.object(rename, "_resource", side_effect=RuntimeError("classifier")):
            with self.assertRaises(ValueError):
                owner.finish()
        self.assertTrue(journal.snapshot()["resource_stop"])
        self.assertEqual(len(backend.calls), 4)

    def test_journal_snapshot_failure_still_closes_every_handle(self):
        backend, owner, journal = setup()
        with patch.object(model.PublicationJournal, "snapshot", side_effect=MemoryError()):
            with self.assertRaises(MemoryError):
                owner.finish()
        self.assertEqual(backend.live, {})
        self.assertEqual(journal.snapshot()["model_status"], "stopped")
        self.assertTrue(journal.snapshot()["resource_stop"])

    def test_teardown_record_failure_before_and_after_update_preserves_confirmed_commit(self):
        original = model.PublicationJournal.finish_teardown
        for after in (False, True):
            with self.subTest(after=after):
                backend, owner, journal = setup()
                def fail_record(current, *, success):
                    if after:
                        original(current, success=success)
                    raise MemoryError()
                with patch.object(model.PublicationJournal, "finish_teardown", fail_record):
                    with self.assertRaises(MemoryError):
                        owner.finish()
                self.assertEqual(backend.live, {})
                state = journal.snapshot()
                self.assertEqual(state["commit_observation"], "confirmed")
                self.assertEqual(state["model_status"], "stopped")
                self.assertEqual(state["teardown"], "succeeded" if after else "not_started")
                self.assertTrue(state["resource_stop"])

    def test_secondary_journal_stop_failure_preserves_original_and_marks_unknown(self):
        original_finish = model.PublicationJournal.finish_teardown
        original_stop = model.PublicationJournal.stop
        for has_primary in (False, True):
            for after in (False, True):
                with self.subTest(has_primary=has_primary, after=after):
                    backend, owner, journal = setup()
                    primary = ValueError("original") if has_primary else None
                    report_error = RuntimeError("report")
                    calls = []
                    def fail_finish(current, *, success):
                        calls.append("finish")
                        if after:
                            original_finish(current, success=success)
                        raise report_error
                    def fail_last_stop(current, *, resource=False):
                        calls.append("stop")
                        if "finish" in calls:
                            raise MemoryError()
                        original_stop(current, resource=resource)
                    with patch.object(model.PublicationJournal, "finish_teardown", fail_finish), \
                         patch.object(model.PublicationJournal, "stop", fail_last_stop):
                        with self.assertRaises(ValueError if has_primary else RuntimeError) as caught:
                            owner.finish(primary=primary)
                    self.assertIs(caught.exception, primary if has_primary else report_error)
                    self.assertEqual(backend.live, {})
                    self.assertEqual(calls, ["stop", "stop", "finish", "stop"] if has_primary else ["finish", "stop"])
                    self.assertEqual(owner.snapshot()["journal_finalization"], "unknown")
                    self.assertTrue(owner.snapshot()["resource_stop"])
                    self.assertTrue(owner.snapshot()["all_closes_confirmed"])
                    # If recording itself is broken, the raw journal may still
                    # say complete. The exception + unknown owner record forbids
                    # interpreting that stale/partly updated journal as success.
                    if after and not has_primary:
                        self.assertEqual(journal.snapshot()["model_status"], "complete")

    def test_snapshot_is_detached_and_has_no_handle_values_paths_or_exception_text(self):
        backend, owner, journal = setup()
        backend.hooks[404] = raising(ValueError("private/path"))
        with self.assertRaises(ValueError):
            owner.finish()
        state = owner.snapshot()
        self.assertNotIn("private/path", str(state))
        self.assertNotIn("404", str(state))
        self.assertEqual(set(state["handles"][0]), {"slot", "parent", "state", "winerror"})
        state["handles"][0]["state"] = "forged"
        self.assertEqual(owner.snapshot()["handles"][0]["state"], "closed")

    def test_real_adapter_protocol_integrates_success_and_lost_commit_reply_with_owner(self):
        for lost in (False, True):
            with self.subTest(lost=lost):
                backend, operation, journal = rename_tests.setup()
                close_calls = []
                def close_handle(handle):
                    close_calls.append(handle)
                    del backend.handles[handle]
                    return 1
                backend.close_handle = close_handle
                owner = owned.HandleOwner(backend, journal=journal, slots=(
                    owned.OwnedSlot(rename_tests.PARENT, None), owned.OwnedSlot(backend.source, 0)))
                if lost:
                    backend.hooks["after_effect"] = raising(MemoryError())
                    try:
                        operation.run(journal)
                    except MemoryError as primary:
                        with self.assertRaises(MemoryError) as caught:
                            owner.finish(primary=primary)
                        self.assertIs(caught.exception, primary)
                else:
                    operation.run(journal)
                    owner.finish()
                self.assertEqual(close_calls, [backend.source.handle, rename_tests.PARENT.handle])
                self.assertEqual(backend.handles, {})
                self.assertEqual(backend.names[(rename_tests.PARENT.file_id, ".complete")], backend.source.file_id)
                self.assertEqual(journal.snapshot()["commit_observation"], "unknown" if lost else "confirmed")
                self.assertEqual(journal.snapshot()["model_status"], "stopped" if lost else "complete")
                self.assertEqual(journal.snapshot()["teardown"], "succeeded")


if __name__ == "__main__":
    unittest.main()
