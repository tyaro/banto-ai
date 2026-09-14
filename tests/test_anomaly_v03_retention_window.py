"""Synthetic overlap/gap counterexamples and existing fixture contract bindings."""
from dataclasses import replace
import hashlib
import unittest

from tests.fixtures import anomaly_v03_retention_window as retention
from tests.fixtures import anomaly_v03_publication_order_model as order
from tests.fixtures import anomaly_v03_sealed_files as sealed
from tests import test_anomaly_v03_sealed_files as sealing_tests
from tests import test_anomaly_v03_publication_order_model as order_tests

PINS = (retention.FilePin("payload.bin", 7, b"p" * 16, b"checked payload", b"payload sd"),
        retention.FilePin("marker.json", 7, b"m" * 16, b"complete marker", b"marker sd"))


def opened(model, slot, index, *, access=retention.READER, share=1):
    pin = PINS[index]
    model.begin_open(slot, pin.name, access=access, share=share)
    model.confirm_open(slot, volume=pin.volume, file_id=pin.file_id, granted_access=access)


def ready(*, assumed=False, shares=(1, 1)):
    model = retention.RetentionWindow(PINS, marker_name="marker.json", assume_other_boundaries_stable_for_test=assumed)
    for index, share in enumerate(shares):
        opened(model, index + 1, index, share=share)
    model.start_publication_interval()
    return model


def read(model, slot, index):
    pin = PINS[index]
    model.observe(slot, volume=pin.volume, file_id=pin.file_id, raw=pin.raw, descriptor=pin.descriptor)


def close(model, slot):
    model.begin_close(slot)
    model.confirm_close(slot)


def observe_all(model):
    model.begin_observation()
    read(model, 1, 0)
    read(model, 2, 1)
    return model.finish_observation()


class SharingContractTests(unittest.TestCase):
    def test_payload_sealer_can_overlap_read_guard_but_delete_bearing_marker_cannot(self):
        self.assertTrue(retention.share_compatible(sealed.FILE_SEAL_ACCESS, 1, retention.READER, 1))
        self.assertFalse(retention.share_compatible(sealed.MARKER_SEAL_ACCESS, 1, retention.READER, 1))
        self.assertTrue(retention.share_compatible(sealed.MARKER_SEAL_ACCESS, 1, retention.READER, 5))

    def test_sharing_is_bilateral_and_does_not_treat_write_dac_as_data_write(self):
        for first, share1, second, share2, expected in (
            (retention.READER, 1, retention.WRITER, 7, False),
            (retention.READER, 3, retention.WRITER, 7, True),
            (retention.READER, 1, sealed.FILE_SEAL_ACCESS, 1, True),
            (sealed.MARKER_SEAL_ACCESS, 1, retention.READER, 0, False)):
            self.assertEqual(retention.share_compatible(first, share1, second, share2), expected)
            self.assertEqual(retention.share_compatible(second, share2, first, share1), expected)
        for value in (True, -1, 8, None):
            with self.assertRaises(order.OrderError):
                retention.share_compatible(retention.READER, value, retention.READER, 1)

    def test_marker_reader_allowing_delete_does_not_continue_old_delete_guard(self):
        model = retention.RetentionWindow(PINS, marker_name="marker.json", assume_other_boundaries_stable_for_test=True)
        opened(model, 1, 0)
        opened(model, 2, 1, access=sealed.MARKER_SEAL_ACCESS)
        model.start_publication_interval()
        model.begin_observation()
        opened(model, 3, 1, share=5)
        close(model, 2)
        read(model, 1, 0); read(model, 3, 1)
        self.assertEqual(model.finish_observation(), "observations_match_only")
        self.assertIn(("marker.json", "delete"), model.snapshot()["observation_gaps"])

    def test_incompatible_second_open_cannot_be_acknowledged_as_held(self):
        model = retention.RetentionWindow(PINS, marker_name="marker.json")
        opened(model, 1, 1, access=sealed.MARKER_SEAL_ACCESS)
        model.begin_open(2, "marker.json")
        with self.assertRaises(order.OrderError):
            model.confirm_open(2, volume=7, file_id=PINS[1].file_id, granted_access=retention.READER)
        self.assertTrue(model.snapshot()["unresolved_open_or_close"])
        self.assertEqual(model.snapshot()["slots"][1]["state"], "opening")


class RetentionWindowTests(unittest.TestCase):
    def test_default_all_matches_still_has_unresolved_namespace_and_security(self):
        model = ready()
        self.assertEqual(observe_all(model), "observations_match_only")
        self.assertEqual(model.snapshot()["observation_gaps"], [])
        self.assertEqual(model.snapshot()["other_boundaries_basis"], "unresolved")
        with self.assertRaises(order.OrderError):
            model.checked_payload()

    def test_common_interval_returns_same_checked_bytes_without_future_protection(self):
        model = ready(assumed=True)
        model.begin_observation()
        raw = bytes(bytearray(PINS[0].raw))
        model.observe(1, volume=7, file_id=PINS[0].file_id, raw=raw, descriptor=PINS[0].descriptor)
        read(model, 2, 1)
        self.assertEqual(model.finish_observation(), "common_interval_model_only")
        close(model, 2); close(model, 1)
        payload = model.checked_payload()
        self.assertIs(payload[0][1], raw)
        row = model.snapshot()
        self.assertEqual(row["publication_gaps"], [])  # Interval ended before close.
        self.assertEqual(len(row["currently_uncovered"]), 4)
        for flag in ("isolation_certified", "protected_commit_allowed", "future_immutability_proven",
                     "native_publication_performed", "formal_permission", "execution_authenticated"):
            self.assertIs(row[flag], False)

    def test_confirmed_overlap_on_same_identity_keeps_common_interval(self):
        model = ready(assumed=True)
        model.begin_observation()
        opened(model, 3, 0)
        close(model, 1)
        read(model, 3, 0); read(model, 2, 1)
        self.assertEqual(model.finish_observation(), "common_interval_model_only")
        self.assertEqual(model.snapshot()["publication_gaps"], [])

    def test_open_intent_is_not_overlap_and_reopen_cannot_erase_gap(self):
        model = ready(assumed=True)
        model.begin_observation()
        model.begin_open(3, "payload.bin")
        close(model, 1)
        model.confirm_open(3, volume=7, file_id=PINS[0].file_id, granted_access=retention.READER)
        read(model, 3, 0); read(model, 2, 1)
        self.assertEqual(model.finish_observation(), "observations_match_only")
        self.assertIn(("payload.bin", "delete"), model.snapshot()["observation_gaps"])

    def test_sequential_read_close_and_reopen_has_no_common_interval_even_for_same_bytes(self):
        model = ready(assumed=True)
        model.begin_observation(); read(model, 1, 0)
        close(model, 1)
        opened(model, 3, 0)
        read(model, 2, 1)
        self.assertEqual(model.finish_observation(), "observations_match_only")
        with self.assertRaises(order.OrderError):
            model.checked_payload()

    def test_old_publication_gap_does_not_poison_new_consumer_interval_or_disappear(self):
        model = ready(assumed=True)
        close(model, 1); opened(model, 3, 0)
        model.begin_observation(); read(model, 3, 0); read(model, 2, 1)
        self.assertEqual(model.finish_observation(), "common_interval_model_only")
        self.assertTrue(model.snapshot()["publication_gaps"])
        self.assertEqual(model.snapshot()["observation_gaps"], [])
        self.assertFalse(model.snapshot()["protected_commit_allowed"])

    def test_missing_guard_at_window_start_remains_a_gap_after_acquisition(self):
        model = retention.RetentionWindow(PINS, marker_name="marker.json", assume_other_boundaries_stable_for_test=True)
        opened(model, 1, 0)
        model.start_publication_interval(); model.begin_observation()
        opened(model, 2, 1)
        read(model, 1, 0); read(model, 2, 1)
        self.assertEqual(model.finish_observation(), "observations_match_only")

    def test_delete_only_guard_does_not_protect_data_and_data_only_does_not_protect_delete(self):
        for share, missing in ((3, "data_write"), (5, "delete"), (7, "delete")):
            model = ready(assumed=True, shares=(share, 1))
            self.assertEqual(observe_all(model), "observations_match_only")
            self.assertIn(("payload.bin", missing), model.snapshot()["observation_gaps"])

    def test_close_intent_and_lost_reply_never_count_as_a_live_guard(self):
        model = ready(assumed=True)
        model.begin_observation(); read(model, 1, 0)
        model.begin_close(1); model.stop()
        row = model.snapshot()
        self.assertTrue(row["unresolved_open_or_close"])
        self.assertTrue(row["observation_gaps"])
        with self.assertRaises(order.OrderError):
            model.finish_observation()

    def test_unresolved_extra_open_or_close_blocks_completion_despite_continuous_guards(self):
        for kind in ("open", "close"):
            model = ready(assumed=True)
            if kind == "open":
                model.begin_open(3, "payload.bin")
            else:
                opened(model, 3, 0)
                model.begin_close(3)
            model.begin_observation(); read(model, 1, 0); read(model, 2, 1)
            self.assertEqual(model.snapshot()["observation_gaps"], [])
            with self.assertRaises(order.OrderError) as caught:
                model.finish_observation()
            self.assertEqual(caught.exception.reason, "retention_operation_unresolved")
            self.assertIsNone(model.snapshot()["consumer_observation"])
            with self.assertRaises(order.OrderError):
                model.checked_payload()

    def test_operation_started_after_observation_still_blocks_delivery_until_confirmed(self):
        for kind in ("open", "close"):
            model = ready(assumed=True); observe_all(model)
            if kind == "open":
                model.begin_open(3, "payload.bin")
            else:
                model.begin_close(1)
            with self.assertRaises(order.OrderError) as caught:
                model.checked_payload()
            self.assertEqual(caught.exception.reason, "retention_operation_unresolved")
            self.assertEqual(model.snapshot()["consumer_observation"], "common_interval_model_only")

    def test_duplicate_slot_close_or_observation_stops_and_never_reuses_a_generation(self):
        for mode in ("slot", "close", "read"):
            model = ready(assumed=True)
            model.begin_observation()
            with self.assertRaises(order.OrderError):
                if mode == "slot":
                    close(model, 1); opened(model, 1, 0)
                elif mode == "close":
                    close(model, 1); close(model, 1)
                else:
                    read(model, 1, 0); read(model, 1, 0)
            self.assertTrue(model.snapshot()["stopped"])

    def test_identity_rights_type_and_read_changes_are_not_rebound_to_new_pins(self):
        for field, value in (("volume", True), ("file_id", b"z"*16), ("raw", b"other"),
                             ("raw", bytearray(PINS[0].raw)), ("descriptor", b"other")):
            model = ready(assumed=True); model.begin_observation()
            args = dict(volume=7, file_id=PINS[0].file_id, raw=PINS[0].raw, descriptor=PINS[0].descriptor)
            args[field] = value
            with self.assertRaises(order.OrderError):
                model.observe(1, **args)
        model = retention.RetentionWindow(PINS, marker_name="marker.json")
        model.begin_open(1, "payload.bin")
        with self.assertRaises(order.OrderError):
            model.confirm_open(1, volume=7, file_id=PINS[0].file_id, granted_access=sealed.FILE_SEAL_ACCESS)

    def test_partial_reads_or_skipped_start_never_finish(self):
        model = ready(assumed=True)
        with self.assertRaises(order.OrderError):
            model.finish_observation()
        model = ready(assumed=True); model.begin_observation(); read(model, 1, 0)
        with self.assertRaises(order.OrderError):
            model.finish_observation()

    def test_first_failure_resource_escalation_and_close_after_stop(self):
        model = ready()
        with self.assertRaises(order.OrderError) as first:
            model.finish_observation()
        model.stop(resource=True)
        close(model, 1); close(model, 2)
        with self.assertRaises(order.OrderError) as later:
            model.begin_observation()
        self.assertIs(first.exception, later.exception)
        self.assertTrue(model.snapshot()["resource_stop"])
        self.assertFalse(model.snapshot()["unresolved_open_or_close"])

    def test_external_change_after_complete_or_stop_preserves_history_and_invalidates_delivery(self):
        model = ready(assumed=True); observe_all(model)
        model.record_external_change()
        self.assertEqual(model.snapshot()["consumer_observation"], "common_interval_model_only")
        self.assertTrue(model.snapshot()["external_change_observed"])
        with self.assertRaises(order.OrderError):
            model.checked_payload()

    def test_plan_bounds_aliases_and_snapshot_detachment(self):
        for pins in ((PINS[0], PINS[0]), (PINS[0], replace(PINS[1], file_id=PINS[0].file_id)),
                     (replace(PINS[0], raw=b"x"*(retention.MAX_FILE_BYTES+1)), PINS[1])):
            with self.assertRaises(order.OrderError):
                retention.RetentionWindow(pins, marker_name="marker.json")
        model = ready()
        view = model.snapshot(); view["slots"][0]["share"] = 7
        self.assertEqual(model.snapshot()["currently_uncovered"], [])
        for _ in range(retention.MAX_EVENTS-model._events):
            model.record_external_change()
        with self.assertRaises(order.OrderError):
            model.record_external_change()
        self.assertEqual(model.snapshot()["events"], retention.MAX_EVENTS)
        self.assertTrue(model.snapshot()["resource_stop"])


class ExistingBoundaryTests(unittest.TestCase):
    def test_matching_lifetime_model_never_opens_existing_publisher_gate_or_clears_unknown(self):
        model = ready(assumed=True); observe_all(model)
        producer = order_tests.verified()
        with self.assertRaises(order.OrderError):
            producer.begin_marker_write()
        producer = order_tests.verified(assumed=True)
        producer.begin_marker_write(); producer.stop()
        self.assertEqual(producer.snapshot()["marker_commit_observation"], "unknown")
        self.assertEqual(model.checked_payload(), (("payload.bin", PINS[0].raw),))

    def test_existing_sealed_continuation_closes_all_file_guards_before_return(self):
        table, leases, group, backend, files = sealing_tests.setup()
        seen = []
        def continuation(pins):
            self.assertEqual(set(table.live), {101, 404, 505})
            for observation in pins.observations:
                self.assertEqual(hashlib.sha256(backend.views[observation.pin.handle].raw).hexdigest(),
                                 observation.pin.content_sha256)
            seen.extend(observation.pin.handle for observation in pins.observations)
        files.seal_and_use(continuation)
        self.assertEqual(seen, [404, 505])
        self.assertEqual(set(table.live), {101})
        self.assertTrue(all(row.close_state == "closed" for row in files._leases))
        group.finish()


if __name__ == "__main__":
    unittest.main()
