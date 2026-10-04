"""Read-only regression gate for the two saved Ubuntu unittest journals.

This checks a selected common-test inventory. It is not an S4 acceptance
receipt and does not authenticate the runner image, Windows, or dev/smoke.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import ci_compare_fixtures as comparison
from tools import ci_test_report as ci
from tools.ci_windows_native_skip_ids import WINDOWS_ONLY_IDS


# The shared fixture owners cover Q1-Q5, M1-M9, profiles/scores, seed and
# bootstrap golden, and accounting. These additional IDs cover common
# validator, runner, and independent consumer paths outside that inventory.
REQUIRED_TEST_IDS = frozenset({
    "tests.test_anomaly_v03.V03ContractTests.test_seed_registry_independent_recalculation",
    "tests.test_anomaly_v03.V03ContractTests.test_full_bootstrap_independent_hash_and_golden",
    "tests.test_anomaly_v03_episodes.AccountingTests.test_zero_alert_precision_null_all_planned_incidents_and_origins",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M1_first_pre_event_support_no_retry",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M2_minimum_causal_delay_one_second",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M3_ended_pre_event_episode_not_a_candidate",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M4_right_endpoint_is_outside_half_open_window",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M5_first_other_target_does_not_retry",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M6_late_target_in_merge_never_moves_group_onset",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M7_mode_entry_minimum_delay_two_seconds",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M8_equality_does_not_exceed",
    "tests.test_anomaly_v03_episodes.MatchingGoldenTests.test_M9_forged_unavailable_support_stops_before_selection",
    "tests.test_anomaly_v03_scoring.ProfileAndScoreTests.test_all_48_profiles_fit20_calibrate290_and_frozen",
    "tests.test_anomaly_v03_scoring.ProfileAndScoreTests.test_hand_C0_C1_residual_and_no_profile_or_score_quantization",
    "tests.test_anomaly_v03_scoring.QuantizationAndCaptureTests.test_Q1_overlay_before_rounding",
    "tests.test_anomaly_v03_scoring.QuantizationAndCaptureTests.test_Q2_finalizer_does_not_round_or_replace_normal_latent_state",
    "tests.test_anomaly_v03_scoring.QuantizationAndCaptureTests.test_Q3_final_quality_null_is_not_imputed",
    "tests.test_anomaly_v03_scoring.QuantizationAndCaptureTests.test_Q4_binary64_ties",
    "tests.test_anomaly_v03_scoring.QuantizationAndCaptureTests.test_Q5_signed_zero_numeric_and_saved_JSON_bytes",
    "tests.test_anomaly_v03.V03ContractTests.test_complete_bundle_positive_and_no_run_status",
    "tests.test_anomaly_v03.V03ContractTests.test_matrix_counts_inventory_duplicate_pairing_and_unknown_status",
    "tests.test_anomaly_v03_acceptance.AcceptanceContractTests.test_both_linux_minors_remain_compatibility_only_and_unaccepted",
    "tests.test_anomaly_v03_scoring.ProfileAndScoreTests.test_test_future_values_do_not_change_fit_or_earlier_scores",
    "tests.test_anomaly_v03_scoring.ProfileAndScoreTests.test_GT_not_accepted_and_pure_no_IO_environment_network",
    "tests.test_anomaly_v03_generation_audit.GenerationCaptureTests.test_full_nonregistered_pair_passes_without_producer_helpers",
    "tests.test_anomaly_v03_chunk_audit.ChunkAuditTests.test_dev_smoke_boundaries_and_retry_bind_real_files_without_generation",
    "tests.test_anomaly_v03_consumer_reader.ConsumerReaderTests.test_wrong_sized_output_rejected_before_opening_payload",
    "tests.test_anomaly_v03_engineering_consumer.EngineeringConsumerTests.test_binding_cannot_upgrade_acceptance",
})


# Exact unittest class IDs and skip reasons. The separate WINDOWS_ONLY_IDS
# inventory lists every permitted fully qualified method ID; a newly added
# method in one of these classes is rejected until explicitly reviewed.
WINDOWS_ONLY_CLASSES = {
    "tests.test_anomaly_failure_diagnostics_publish.DiagnosticsPublisherTests":
        "D2-B publication is Windows-only; non-Windows rejection is tested separately",
    "tests.test_anomaly_v03_analysis_evidence.AnalysisEvidenceTests": "owned Windows analysis preparation",
    "tests.test_anomaly_v03_analysis_profile.LiveProfile": "owned Windows analysis profile checks",
    "tests.test_anomaly_v03_analysis_publication.PublicationChainTests": "owned Windows publication chain",
    "tests.test_anomaly_v03_bound_report_publication.BoundReportPublicationTests": "ordinary Windows local storage",
    "tests.test_anomaly_v03_fixture_audit_worker.AuditWorkerTests": "Windows CPython 3.14 observation",
    "tests.test_anomaly_v03_fixture_budget.BudgetIntegrationTests": "Windows fixture worker",
    "tests.test_anomaly_v03_fixture_publication.FixturePublicationTests": "Windows CPython 3.14 observation",
    "tests.test_anomaly_v03_fixture_worker.FixtureWorkerTests": "Windows CPython 3.14 observation",
    "tests.test_anomaly_v03_platform_fixture.NativePlatformFixtureTests": "explicit 26H2 native fixture run",
    "tests.test_anomaly_v03_preformal_bound_slice_publication.SavedSlicePublicationTests":
        "retained invented slice artifacts and Windows CPython 3.14 required",
    "tests.test_anomaly_v03_preformal_job_tree_owner.NativeJobOwnerTests": "explicit 26H2 native Job fixture run",
    "tests.test_anomaly_v03_reader_dependencies.LiveDependencies": "Windows loaded image observations",
    "tests.test_anomaly_v03_reader_evidence.ReaderEvidenceTests":
        "observed reader uses owned Windows process handles",
    "tests.test_anomaly_v03_reader_profile.LiveProfile": "owned Windows reader profile checks",
    "tests.test_anomaly_v03_replace_trace.NativeReplacementTraceTests":
        "Windows-only small same-parent trace test",
    "tests.test_anomaly_v03_saved_report_pipeline.SavedReportPipelineTests":
        "owned local Windows writer/reader",
    "tests.test_anomaly_v03_windows.NativeWindowsControls":
        "Windows-only native control; NOT acceptance on Linux",
}

WINDOWS_ONLY_TESTS = {
    "tests.test_anomaly_v03_consumer_reader.ConsumerReaderTests.test_child_startup_excludes_site_and_environment_paths":
        "owned reader child requires Windows runtime and process supervision",
    "tests.test_anomaly_v03_consumer_reader.ConsumerReaderTests.test_lost_reader_reply_is_not_promoted_to_verified":
        "owned reader child requires Windows runtime and process supervision",
    "tests.test_anomaly_v03_consumer_reader.ConsumerReaderTests.test_lost_writer_reply_recovered_only_with_retained_marker":
        "owned reader child requires Windows runtime and process supervision",
    "tests.test_anomaly_v03_consumer_reader.ConsumerReaderTests.test_resealed_changed_value_rejected_against_original_source":
        "owned reader child requires Windows runtime and process supervision",
    "tests.test_anomaly_v03_consumer_reader.ConsumerReaderTests.test_separate_process_verified_and_check_root_never_reused":
        "owned reader child requires Windows runtime and process supervision",
    "tests.test_anomaly_v03_consumer_reader.ConsumerReaderTests.test_wrong_retained_anchor_is_failed_outside_unchanged_publication":
        "owned reader child requires Windows runtime and process supervision",
    "tests.test_anomaly_matrix_runner.AnomalyMatrixRunnerTests.test_repository_containment_rejects_real_ntfs_junction":
        "NTFS junction test requires Windows",
    "tests.test_anomaly_v03_fixture_budget.FixtureBudgetTests.test_real_child_is_reaped_after_small_directory_burst":
        "owned Windows child",
    "tests.test_anomaly_v03_fixture_budget.FixtureBudgetTests.test_real_child_reaped_for_injected_commit_pressure_without_allocating_ram":
        "owned Windows child",
    "tests.test_anomaly_v03_process_supervisor.ProcessSupervisorTests.test_tiny_real_windows_child_exits_and_output_is_hashed":
        "real child uses Windows process observation",
    "tests.test_anomaly_v03_preformal_five_role_job_owner.FiveRoleJobNativeProbeTests.test_six_job_members_complete_and_owner_accepts":
        "Windows native Job probe",
    "tests.test_anomaly_v03_preformal_five_role_job_owner.FiveRoleJobNativeProbeTests.test_root_failure_stops_five_children_and_owner_rejects":
        "Windows native Job probe",
}


# These source-checkout tests depend on retained local artifacts or an optional
# analysis extra. Their skips are allowed only for the exact reviewed methods;
# none is a required S4 common-contract test or evidence of native acceptance.
OPTIONAL_SKIP_CLASSES = {
    "tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests":
        "optional offline-analysis extra is not installed; not native acceptance",
    "tests.test_anomaly_v03_preformal_bound_document_bridge.SavedDocumentBridgeTests":
        "retained invented arithmetic fixture absent",
    "tests.test_anomaly_v03_preformal_bound_slice_bridge.SavedSliceBridgeTests":
        "retained invented document/slice fixture absent",
}

OPTIONAL_SKIP_TESTS = {
    "tests.test_anomaly_v03_preformal_owned_saved_attempt.OwnedSavedAttemptMaterializerTests.test_native_owned_materializer_then_registered_saved_reader":
        "native owned materializer is an explicit post-commit run",
    "tests.test_toto2_docs.Toto2DocumentationTests.test_controlled_artifacts_are_verified_when_available":
        "controlled Toto artifact unavailable",
    "tests.test_toto2_docs.Toto2DocumentationTests.test_event_slice_local_artifacts_are_checked_when_present":
        "local Toto event-slice artifacts unavailable",
}

OPTIONAL_SKIP_IDS = frozenset("""
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_instruction_operands_are_not_published
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_two_callers_verified_and_private_values_omitted
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_recovered_registers_are_private_snapshots_of_accepted_frames
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_call_target_mismatch_does_not_accept_candidate
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_chain_and_unhandled_opcodes_stop
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_chained_saves_use_primary_entry_and_fixed_stack_base
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_chained_bare_ret_does_not_unwind_body_again
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_chain_cycle_and_non_table_parent_are_rejected
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_chain_rejects_stack_changes_bad_slots_and_saved_window_escape
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_chain_depth_is_bounded
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_handler_metadata_does_not_change_context_unwind
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_invalid_or_truncated_handler_rva_stops_before_accepting
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_large_allocation_cannot_leave_saved_window
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_potential_epilogue_and_mid_instruction_stop
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_non_stack_arithmetic_is_body_but_stack_aliases_still_stop
tests.test_anomaly_v03_offline_unwind.OfflineUnwindTests.test_pe_range_and_stack_shape_are_checked
tests.test_anomaly_v03_preformal_bound_document_bridge.SavedDocumentBridgeTests.test_saved_pins_and_draft_are_bound_without_arithmetic_replay
tests.test_anomaly_v03_preformal_bound_document_bridge.SavedDocumentBridgeTests.test_wrong_external_top_pin_rejects_before_new_root
tests.test_anomaly_v03_preformal_bound_document_bridge.SavedDocumentBridgeTests.test_run_selects_formal_schema_but_retains_fixture_draft
tests.test_anomaly_v03_preformal_bound_slice_bridge.SavedSliceBridgeTests.test_external_document_and_slice_pins_reject_before_creating_trial
tests.test_anomaly_v03_preformal_bound_slice_bridge.SavedSliceBridgeTests.test_slice_draft_preserves_primary_tables_and_formal_closure
""".split())


def _source_from_first_record(path: Path) -> dict:
    """Get the run identity through a bounded read; full parsing follows."""
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        comparison.require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= ci.MAX_REPORT_BYTES,
                           "report_file_size")
        raw = stream.readline(comparison.MAX_LINE_BYTES + 1)
    comparison.require(0 < len(raw) <= comparison.MAX_LINE_BYTES and raw.endswith(b"\n"),
                       "first_record_size_or_partial_line")
    row = comparison.strict_json(raw)
    comparison.require(type(row) is dict and row.get("event") == "run_started", "missing_run_start")
    source = row.get("source")
    comparison.source_identity(source)
    return source


def _allowed_skip(test_id: str) -> tuple[str, str] | None:
    if test_id in WINDOWS_ONLY_TESTS:
        return "windows_native", WINDOWS_ONLY_TESTS[test_id]
    if test_id in WINDOWS_ONLY_IDS:
        class_id, _, _ = test_id.rpartition(".")
        reason = WINDOWS_ONLY_CLASSES.get(class_id)
        return ("windows_native", reason) if reason is not None else None
    if test_id in OPTIONAL_SKIP_TESTS:
        return "non_s4_optional", OPTIONAL_SKIP_TESTS[test_id]
    if test_id in OPTIONAL_SKIP_IDS:
        class_id, _, _ = test_id.rpartition(".")
        reason = OPTIONAL_SKIP_CLASSES.get(class_id)
        return ("non_s4_optional", reason) if reason is not None else None
    return None


def verify(paths: dict[str, Path], expected_head: str, expected_workflow_sha256: str,
           expected_run_id: str, expected_run_attempt: str) -> dict:
    comparison.require(type(expected_head) is str and re.fullmatch(r"[a-f0-9]{40}", expected_head) is not None,
                       "expected_head_format")
    comparison.require(type(expected_workflow_sha256) is str and
                       re.fullmatch(r"[a-f0-9]{64}", expected_workflow_sha256) is not None,
                       "expected_workflow_pin_format")
    comparison.require(all(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,19}", value) is not None
                           for value in (expected_run_id, expected_run_attempt)),
                       "expected_run_identity_format")
    comparison.require(set(paths) == set(comparison.MINORS), "required_python_matrix")
    source = _source_from_first_record(paths["3.12"])
    comparison.require(source["revision"] == expected_head and
                       source["workflow_sha256"] == expected_workflow_sha256 and
                       source["github_run_id"] == expected_run_id and
                       source["github_run_attempt"] == expected_run_attempt,
                       "external_source_pin_mismatch")

    # Existing parser checks every record, run completion, source/run identity,
    # and exact/numeric shared fixtures. Its comparison is never an acceptance
    # receipt. Re-read to examine test IDs and skip reasons; require the bytes
    # to match the comparison's raw pins so both passes saw the same journals.
    compared = comparison.compare_reports(paths, source)
    checked = {}
    for minor in comparison.MINORS:
        report = comparison.read_report(paths[minor], minor, source)
        comparison.require(report["sha256"] == compared["reports"][minor]["sha256"] and
                           report["bytes"] == compared["reports"][minor]["bytes"],
                           "journal_changed_during_verification")
        planned, finished = set(report["planned"]), report["finished"]
        comparison.require(REQUIRED_TEST_IDS <= planned, "required_test_missing")
        comparison.require(all(finished.get(test_id) == ["pass"] for test_id in REQUIRED_TEST_IDS),
                           "required_test_not_passed")
        windows_skips, optional_skips = [], []
        for skip in report["skips"]:
            test_id = skip.get("test_id")
            policy = _allowed_skip(test_id) if type(test_id) is str else None
            comparison.require(policy is not None and skip.get("reason") == policy[1] and
                               skip.get("subtest") is False and finished.get(test_id) == ["skip"],
                               "unexpected_linux_skip")
            (windows_skips if policy[0] == "windows_native" else optional_skips).append(test_id)
        checked[minor] = {"journal_sha256": report["sha256"], "required_tests_passed": len(REQUIRED_TEST_IDS),
                          "windows_native_skips": sorted(windows_skips),
                          "non_s4_optional_skips": sorted(optional_skips),
                          "runner_image_version": report["runtime"]["runner_image_version"]}

    return {"verification_status": "passed", "source": source, "jobs": checked,
            "shared_fixture_comparison": compared["comparison_status"],
            "runner_image_digest_status": "not_collected",
            "external_runner_image_log_status": compared["external_runner_image_log_status"],
            "external_runner_image_manifest_status": compared["external_runner_image_manifest_status"],
            "scope": "saved Ubuntu unittest journals only; final CI jobs and S4 acceptance are not authenticated",
            "execution_authenticated": False, "acceptance_status": "not_completed", "formal_permission": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python312", required=True, type=Path, help="saved Python 3.12 unittest.jsonl")
    parser.add_argument("--python314", required=True, type=Path, help="saved Python 3.14 unittest.jsonl")
    parser.add_argument("--expected-head", required=True, help="externally pinned full Git SHA")
    parser.add_argument("--expected-workflow-sha256", required=True, help="externally pinned raw workflow SHA-256")
    parser.add_argument("--expected-run-id", required=True, help="externally pinned GitHub run ID")
    parser.add_argument("--expected-run-attempt", required=True, help="externally pinned GitHub run attempt")
    args = parser.parse_args(argv)
    try:
        result = verify({"3.12": args.python312, "3.14": args.python314},
                        args.expected_head, args.expected_workflow_sha256,
                        args.expected_run_id, args.expected_run_attempt)
    except (comparison.EvidenceError, OSError, ValueError, TypeError, KeyError, RecursionError) as error:
        reason = str(error) if isinstance(error, comparison.EvidenceError) else "invalid_journal"
        print("CI regression journals failed: " + reason, file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
