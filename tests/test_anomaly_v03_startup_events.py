"""Offline debugger-event bookkeeping; never launches a child or debugger."""

import json
import unittest

from tests.fixtures.anomaly_v03_startup_events import EventContractError, StartupEvent, StartupEvents


class StartupEventTests(unittest.TestCase):
    def test_preallocation_binding_and_stopped_unbound_recorder(self):
        journal = StartupEvents()
        slots = journal.slots
        with self.assertRaises(EventContractError):
            journal.receive(StartupEvent("create_process", 17, 19), 0)
        for pid in (0, True, -1, 2**32, "17"):
            with self.assertRaises(EventContractError):
                journal.bind(pid)
        journal.bind(17)
        self.assertIs(journal.slots, slots)
        with self.assertRaises(EventContractError):
            journal.bind(17)
        journal.receive(StartupEvent("create_process", 17, 19), 0)
        unbound = StartupEvents()
        unbound.stop(resource=True)
        with self.assertRaises(EventContractError):
            unbound.bind(17)

    def started(self):
        journal = StartupEvents(17)
        journal.receive(StartupEvent("create_process", 17, 19), 0)
        journal.continued()
        return journal

    def test_dll_load_is_not_a_faulting_module_and_exit_needs_continue_and_wait(self):
        journal = self.started()
        journal.receive(StartupEvent("load_dll", 17, 19), 1)
        journal.continued()
        journal.receive(StartupEvent("exit_process", 17, 19, 0xC0000142), 2)
        self.assertEqual(journal.report()["exit_code_observed"], 0xC0000142)
        self.assertEqual(journal.report()["status"], "running")
        with self.assertRaises(EventContractError):
            journal.process_signaled()
        journal.continued()
        self.assertEqual(journal.status, "exit_continued")
        journal.process_signaled()
        self.assertEqual(journal.status, "completed")
        self.assertIsNone(journal.report()["faulting_module"])
        self.assertFalse(journal.report()["native_accepted"])

    def test_stop_keeps_delivered_event_without_claiming_continue_or_retry(self):
        for resource in (False, True):
            journal = self.started()
            event = StartupEvent("exception", 17, 19, 0xC0000005, True)
            journal.receive(event, 1)
            journal.stop(resource=resource)
            self.assertIs(journal.pending, event)
            self.assertIs(journal.slots[1], event)
            self.assertEqual(journal.confirmed, 1)
            for action in (journal.continued, journal.process_signaled,
                           lambda: journal.receive(StartupEvent("load_dll", 17, 19), 2)):
                with self.assertRaises(EventContractError):
                    action()
            journal.stop(resource=False)
            self.assertEqual(journal.resource_stop, resource)

    def test_first_chance_and_second_chance_remain_distinct(self):
        journal = self.started()
        for first in (True, False):
            journal.receive(StartupEvent("exception", 17, 19, 0xC0000005, first), 1)
            journal.continued()
        self.assertTrue(journal.slots[1].first_chance)
        self.assertFalse(journal.slots[2].first_chance)

    def test_count_limit_rejects_before_overwriting_any_slot(self):
        journal = self.started()
        for _ in range(journal.LIMIT - 1):
            journal.receive(StartupEvent("load_dll", 17, 19), 1)
            journal.continued()
        original = tuple(journal.slots)
        with self.assertRaises(EventContractError):
            journal.receive(StartupEvent("load_dll", 17, 19), 2)
        self.assertEqual(tuple(journal.slots), original)
        self.assertIsNone(journal.pending)

    def test_time_boundary_and_backward_clock_are_rejected(self):
        journal = self.started()
        journal.receive(StartupEvent("load_dll", 17, 19), 10)
        journal.continued()
        for elapsed in (9, 30_000, True, 10.0):
            with self.subTest(elapsed=elapsed), self.assertRaises(EventContractError):
                journal.receive(StartupEvent("load_dll", 17, 19), elapsed)
        self.assertEqual(journal.count, 2)

    def test_foreign_pid_bad_fields_and_duplicate_create_are_rejected(self):
        journal = self.started()
        for event in (StartupEvent("load_dll", 18, 19), StartupEvent("load_dll", 17, True),
                      StartupEvent("exception", 17, 19, True), StartupEvent("exception", 17, 19, 1, 1),
                      StartupEvent("load_dll", 17, 19, 1), StartupEvent("create_process", 17, 19),
                      StartupEvent("unknown", 17, 19)):
            with self.subTest(kind=event.kind), self.assertRaises(EventContractError):
                journal.receive(event, 1)
        self.assertEqual(journal.count, 1)

    def test_pending_event_and_terminal_state_cannot_be_overwritten(self):
        journal = StartupEvents(17)
        with self.assertRaises(EventContractError):
            journal.receive(StartupEvent("load_dll", 17, 19), 0)
        journal.receive(StartupEvent("create_process", 17, 19), 0)
        with self.assertRaises(EventContractError):
            journal.receive(StartupEvent("load_dll", 17, 19), 0)
        journal.continued()
        journal.receive(StartupEvent("exit_process", 17, 19), 1)
        journal.continued()
        with self.assertRaises(EventContractError):
            journal.receive(StartupEvent("load_dll", 17, 19), 2)
        journal.process_signaled()
        with self.assertRaises(EventContractError):
            journal.stop()

    def test_public_report_does_not_expose_process_or_thread_ids(self):
        journal = self.started()
        report = journal.report()
        self.assertNotIn("pid", report)
        self.assertNotIn("tid", report)
        self.assertNotIn("17", repr(journal) + repr(journal.slots[0]) + json.dumps(report))
