"""Residual capabilities, write/flush/close faults and consumer observations."""
import unittest

from tests.fixtures import anomaly_v03_publication_order_model as order

MARKER = b'{"fixture":"order-model","complete":true}\n'


def sealed(*, assumed=False):
    state = order.PublicationOrder(MARKER, assume_isolated_for_test=assumed)
    state.prepare()
    state.seal_payload()
    state.begin_rename()
    state.confirm_rename()
    state.seal_parent()
    return state


def verified(*, assumed=False):
    state = sealed(assumed=assumed)
    verify(state)
    return state


def verify(state):
    state.verify_final(inventory_matches=True, identities_match=True, bytes_match=True, descriptors_match=True)


def release(state):
    state.begin_marker_write()
    state.acknowledge_write(MARKER[:7])
    state.acknowledge_write(MARKER[7:])
    state.begin_flush()
    state.confirm_flush()
    state.begin_close()
    state.confirm_close()


class PublicationOrderTests(unittest.TestCase):
    def test_unknown_isolation_blocks_write_even_after_matching_final_observation(self):
        state = verified()
        self.assertTrue(state.snapshot()["final_observation_current"])
        with self.assertRaises(order.OrderError) as caught:
            state.begin_marker_write()
        self.assertEqual(caught.exception.reason, "isolation_unresolved")
        self.assertEqual(state.snapshot()["marker_commit_observation"], "not_started")

    def test_hypothetical_success_never_grants_acceptance_or_protection(self):
        state = verified(assumed=True)
        release(state)
        row = state.snapshot()
        self.assertEqual(row["phase"], "released")
        self.assertEqual(row["marker_commit_observation"], "confirmed_model_only")
        self.assertEqual(row["isolation_basis"], "test_assumption_only")
        self.assertFalse(row["protected_commit_allowed"])
        self.assertFalse(row["future_immutability_proven"])
        self.assertEqual(row["acceptance_status"], "not_completed")

    def test_sealing_does_not_revoke_preexisting_parent_rights(self):
        for right in order.RIGHTS:
            state = order.PublicationOrder(MARKER, assume_isolated_for_test=True)
            state.prepare()
            state.record_preexisting_peer(1, frozenset((right,)))
            before = state.snapshot()["peer_handles"]
            state.seal_payload(); state.begin_rename(); state.confirm_rename(); state.seal_parent()
            self.assertEqual(state.snapshot()["peer_handles"], before)
            verify(state)  # Current namespace equality does not revoke access.
            with self.assertRaises(order.OrderError):
                state.begin_marker_write()

    def test_peer_change_before_final_observation_cannot_be_overruled_by_true_flags(self):
        state = sealed()
        state.record_preexisting_peer(1, order.RIGHTS)
        state.peer_mutation(1, "add_child")
        with self.assertRaises(order.OrderError) as caught:
            verify(state)
        self.assertEqual(caught.exception.reason, "final_observation_mismatch")

    def test_late_peer_discovery_invalidates_the_verified_epoch(self):
        state = verified(assumed=True)
        observed = state.snapshot()
        state.record_preexisting_peer(1, frozenset(("delete_child",)))
        self.assertTrue(observed["final_observation_current"])
        self.assertFalse(state.snapshot()["final_observation_current"])
        with self.assertRaises(order.OrderError):
            state.begin_marker_write()
        state.peer_mutation(1, "delete_child")
        self.assertTrue(state.snapshot()["namespace_changed"])

    def test_peer_change_after_model_release_preserves_history_not_future_protection(self):
        state = verified(assumed=True)
        release(state)
        state.record_preexisting_peer(1, order.RIGHTS)
        state.peer_mutation(1, "add_child")
        row = state.snapshot()
        self.assertEqual(row["marker_commit_observation"], "confirmed_model_only")
        self.assertFalse(row["final_observation_current"])
        self.assertFalse(row["protected_commit_allowed"])
        self.assertTrue(row["stopped"])

    def test_rename_reply_loss_cannot_continue_to_seal_or_marker(self):
        state = order.PublicationOrder(MARKER)
        state.prepare(); state.seal_payload(); state.begin_rename(); state.stop()
        self.assertEqual(state.snapshot()["rename_observation"], "unknown")
        for resume in (state.confirm_rename, state.seal_parent, state.begin_marker_write):
            with self.assertRaises(order.OrderError): resume()
        self.assertEqual(state.snapshot()["marker_commit_observation"], "not_started")

    def test_faults_during_partial_full_flush_and_close_are_unknown(self):
        for stop_at in ("intent", "partial", "written", "flush_pending", "flushed", "close_pending"):
            state = verified(assumed=True)
            state.begin_marker_write()
            if stop_at != "intent": state.acknowledge_write(MARKER[:4])
            if stop_at not in ("intent", "partial"): state.acknowledge_write(MARKER[4:])
            if stop_at in ("flush_pending", "flushed", "close_pending"): state.begin_flush()
            if stop_at in ("flushed", "close_pending"): state.confirm_flush()
            if stop_at == "close_pending": state.begin_close()
            state.stop(resource=True)
            self.assertEqual(state.snapshot()["marker_commit_observation"], "unknown")
            self.assertTrue(state.snapshot()["resource_stop"])
            with self.assertRaises(order.OrderError): state.confirm_close()

    def test_failure_before_write_is_not_started_and_late_failure_keeps_close_history(self):
        state = verified(assumed=True)
        state.stop()
        self.assertEqual(state.snapshot()["marker_commit_observation"], "not_started")
        state = verified(assumed=True)
        release(state)
        state.stop(resource=True)
        self.assertEqual(state.snapshot()["marker_commit_observation"], "confirmed_model_only")
        self.assertTrue(state.snapshot()["resource_stop"])

    def test_partial_wrong_empty_or_overlong_writes_never_confirm(self):
        for raw in (b"", b"wrong", MARKER + b"x", bytearray(MARKER)):
            state = verified(assumed=True)
            state.begin_marker_write()
            with self.assertRaises(order.OrderError): state.acknowledge_write(raw)
            self.assertEqual(state.snapshot()["marker_commit_observation"], "unknown")
        state = verified(assumed=True)
        state.begin_marker_write(); state.acknowledge_write(MARKER[:3])
        with self.assertRaises(order.OrderError): state.begin_flush()

    def test_skips_repeats_and_close_before_flush_latch_stop(self):
        for action in ("seal_parent", "confirm_rename", "confirm_flush", "confirm_close", "begin_marker_write"):
            state = order.PublicationOrder(MARKER)
            with self.assertRaises(order.OrderError): getattr(state, action)()
            with self.assertRaises(order.OrderError): state.prepare()
        state = verified(assumed=True)
        state.begin_marker_write(); state.acknowledge_write(MARKER)
        with self.assertRaises(order.OrderError): state.begin_close()
        state = order.PublicationOrder(MARKER)
        state.prepare()
        with self.assertRaises(order.OrderError): state.prepare()

    def test_first_failure_is_preserved_and_resource_stop_escalates(self):
        state = verified()
        with self.assertRaises(order.OrderError) as first: state.begin_marker_write()
        state.stop(resource=True)
        with self.assertRaises(order.OrderError) as later: state.seal_parent()
        self.assertIs(first.exception, later.exception)
        self.assertEqual(state.snapshot()["failure_reason"], "isolation_unresolved")
        self.assertTrue(state.snapshot()["resource_stop"])

    def test_all_final_checks_require_exact_true(self):
        for field in ("inventory_matches", "identities_match", "bytes_match", "descriptors_match"):
            for value in (False, None, 1):
                state = sealed(assumed=True)
                args = dict(inventory_matches=True, identities_match=True, bytes_match=True, descriptors_match=True)
                args[field] = value
                with self.assertRaises(order.OrderError): state.verify_final(**args)

    def test_peer_shape_duplicates_rights_and_budget_are_bounded(self):
        for handle, rights in ((True, order.RIGHTS), (0, order.RIGHTS), (9, order.RIGHTS), (1, set(order.RIGHTS)),
                               (1, frozenset()), (1, frozenset(("write_anywhere",)))):
            state = order.PublicationOrder(MARKER)
            with self.assertRaises(order.OrderError): state.record_preexisting_peer(handle, rights)
        state = order.PublicationOrder(MARKER)
        state.record_preexisting_peer(1, order.RIGHTS)
        with self.assertRaises(order.OrderError): state.record_preexisting_peer(1, order.RIGHTS)
        for _ in range(order.MAX_PEER_EVENTS - 1): state.peer_mutation(1, "add_child")
        with self.assertRaises(order.OrderError): state.peer_mutation(1, "add_child")
        self.assertEqual(state.snapshot()["peer_events"], order.MAX_PEER_EVENTS)
        self.assertTrue(state.snapshot()["resource_stop"])

    def test_snapshots_do_not_mutate_live_peer_rights(self):
        state = sealed()
        state.record_preexisting_peer(1, order.RIGHTS)
        row = state.snapshot(); row["peer_handles"][0]["rights"].clear()
        self.assertEqual(len(state.snapshot()["peer_handles"][0]["rights"]), 2)


class MarkerConsumerTests(unittest.TestCase):
    def classify(self, **kwargs):
        return order.classify_marker(expected_marker=MARKER, **kwargs)

    def test_unreadable_empty_partial_and_wrong_marker_are_not_a_match(self):
        for status in ("absent", "sharing_violation"):
            self.assertEqual(self.classify(read_status=status)["observation"], "not_ready")
        self.assertEqual(self.classify(read_status="read_error")["observation"], "indeterminate")
        for raw, expected in ((b"", "not_ready"), (MARKER[:4], "incomplete"), (b"other", "invalid"),
                              (MARKER + b"x", "invalid"), (b"x"*(order.previous.MAX_MARKER_BYTES+1), "invalid")):
            row = self.classify(read_status="readable", raw=raw)
            self.assertEqual(row["observation"], expected)
            self.assertFalse(row["snapshot_matches"])

    def test_exact_marker_needs_current_namespace_and_descriptor_observations(self):
        for namespace, descriptor, expected in ((None, True, "indeterminate"), (True, None, "indeterminate"),
                                                (False, True, "invalid"), (True, False, "invalid"), (True, True, "snapshot_matches")):
            row = self.classify(read_status="readable", raw=MARKER, namespace_matches=namespace,
                                identities_match=True, payload_bytes_match=True, descriptors_match=descriptor)
            self.assertEqual(row["observation"], expected)
            self.assertFalse(row["protected_commit_allowed"])
            self.assertFalse(row["future_immutability_proven"])
            self.assertFalse(row["polling_performed"])

    def test_marker_equality_cannot_replace_identity_or_payload_checks(self):
        for identity, payload, expected in ((None, True, "indeterminate"), (True, None, "indeterminate"),
                                           (False, True, "invalid"), (True, False, "invalid")):
            row = self.classify(read_status="readable", raw=MARKER, namespace_matches=True,
                                identities_match=identity, payload_bytes_match=payload, descriptors_match=True)
            self.assertEqual(row["observation"], expected)
            self.assertFalse(row["snapshot_matches"])

    def test_complete_bytes_can_match_after_producer_loses_reply(self):
        state = verified(assumed=True)
        state.begin_marker_write(); state.stop()
        row = self.classify(read_status="readable", raw=MARKER, namespace_matches=True,
                            identities_match=True, payload_bytes_match=True, descriptors_match=True)
        self.assertEqual(state.snapshot()["marker_commit_observation"], "unknown")
        self.assertTrue(row["snapshot_matches"])
        self.assertEqual(row["acceptance_status"], "not_completed")

    def test_reader_shapes_and_marker_pins_are_checked(self):
        for kwargs in (dict(read_status="other"), dict(read_status="readable", raw=None),
                       dict(read_status="absent", raw=MARKER), dict(read_status="sharing_violation", namespace_matches=True),
                       dict(read_status="readable", raw=MARKER, namespace_matches=1)):
            with self.assertRaises(order.OrderError): self.classify(**kwargs)
        for marker in (b"", bytearray(MARKER), b"x"*(order.previous.MAX_MARKER_BYTES+1)):
            with self.assertRaises(order.OrderError): order.PublicationOrder(marker)
        with self.assertRaises(order.OrderError): order.PublicationOrder(MARKER, assume_isolated_for_test=1)
