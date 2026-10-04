"""Invented, supplied-byte probes of the unadopted research-v2 wrapper."""
from __future__ import annotations

import copy
import hashlib
import unittest

from banto_ai import anomaly_v03 as science
from banto_ai import anomaly_v03_formal_research_v2_candidate as candidate
from banto_ai import anomaly_v03_slices as slices
from tests.test_anomaly_v03_audit_repair import reported_analysis


REVISION = "a" * 40
ATTEMPT = "invented-attempt-01"
ROLE_SNAPSHOTS = {
    role: {"sources": {f"src/{role}.py": ("# invented " + role + " source\n").encode()},
           "runtime": {f"runtime/{role}.dll": ("invented " + role + " runtime").encode()}}
    for role in candidate.ROLES}


def pin(raw):
    return {"byte_count": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def metric(n, d):
    return {"numerator": n, "denominator": d, "value": n / d if d else None,
            "ci_status": "not_evaluated" if d else "not_applicable",
            "ci_lower": None, "ci_upper": None, "null_replicates": 0}


def delay_histogram(n):
    half = n // 2
    return [half, n % 2, half, 0, 0]


def row(candidate_id, stratum, dimension, key, n=0, d=0, *, incident=False):
    return {"candidate_id": candidate_id, "stratum": stratum,
            "dimension": dimension, "key": key, "metric": metric(n, d),
            "planned_count": d, "actual_count": n,
            "delay_summary": slices.delay_summary(delay_histogram(n)) if incident else None}


def make_bundle():
    identities = science.evaluation_inventory("holdout")
    roles = {}
    for role in candidate.ROLES:
        roles[role] = {"revision": REVISION,
                       "sources": [{"path": path, "raw_sha256": pin(raw)["sha256"],
                                    "byte_count": len(raw)}
                                   for path, raw in ROLE_SNAPSHOTS[role]["sources"].items()],
                       "runtime": [{"path": path, "raw_sha256": pin(raw)["sha256"],
                                    "byte_count": len(raw)}
                                   for path, raw in ROLE_SNAPSHOTS[role]["runtime"].items()]}
    inputs = {"registered/input.json": {"byte_count": 11, "sha256": "3" * 64}}
    receipts = {name: {"byte_count": 7, "sha256": str(i) * 64}
                for i, name in enumerate(("audit", "writer", "reader"), 4)}
    analysis = reported_analysis()
    analysis["provenance"]["producer_revision"] = REVISION
    analysis["provenance"]["producer_source"] = {"revision": REVISION,
                                                  "sources": roles["producer"]["sources"]}
    analysis["analysis_consumer"] = {"revision": REVISION,
                                     "sources": roles["analysis"]["sources"]}
    for table in analysis["candidate_tables"]:
        table["metrics"]["delay_summary"].update(min=1, max=3)
    series = {name: [] for name in candidate.SERIES}
    for table in analysis["candidate_tables"]:
        model, stratum = table["candidate_id"], table["stratum"]
        recall = {name: table["metrics"][name + "_recall"]
                  for name in ("machine", "sensor")}
        incident_n = sum(m["numerator"] for m in recall.values())
        incident_d = sum(m["denominator"] for m in recall.values())
        for dimension, keys in slices.INCIDENT_KEYS.items():
            for key in keys:
                primary = recall.get(key) if dimension == "class" else None
                if dimension == "class-equipment-mode":
                    primary = next((metric for name, metric in recall.items()
                                    if key == name + ".motor-01.stopped"), None)
                n, d = ((primary["numerator"], primary["denominator"])
                        if primary else ((incident_n, incident_d) if key == keys[0]
                                         and dimension not in ("class", "class-equipment-mode")
                                         else (0, 0)))
                series["incident-recall"].append(row(model, stratum, dimension, key,
                                                      n, d, incident=True))
        availability = {item["full_target"]: item["metric"]
                        for item in table["metrics"]["availability"]}
        score_n = sum(metric["numerator"] for metric in availability.values())
        score_d = sum(metric["denominator"] for metric in availability.values())
        for dimension, keys in slices.SCORE_KEYS.items():
            for key in keys:
                primary = availability.get(key) if dimension == "full-target" else None
                if dimension == "signal-mode":
                    primary = next((metric for target, metric in availability.items()
                                    if key == target + ".stopped"), None)
                n, d = ((primary["numerator"], primary["denominator"])
                        if primary else ((score_n, score_d) if key == keys[0]
                                         and dimension not in ("full-target", "signal-mode",
                                                               "event-offset") else (0, 0)))
                score_row = row(model, stratum, dimension, key, n, d)
                if dimension == "event-offset":
                    score_row["planned_count"] = 40 * (960 if stratum == "overall" else 480)
                series["score-availability"].append(score_row)
                for name in candidate.SERIES[2:]:
                    extra_row = row(model, stratum, dimension, key, 0, d)
                    extra_row["planned_count"] = score_row["planned_count"]
                    series[name].append(extra_row)
    analysis["slices"] = [*series["incident-recall"], *series["score-availability"]]
    science.validate_result_contract(
        analysis, source_snapshots={REVISION: {
            **ROLE_SNAPSHOTS["producer"]["sources"],
            **ROLE_SNAPSHOTS["analysis"]["sources"]}})
    execution = {"format": candidate.FORMAT, "policy_id": candidate.POLICY,
                 "attempt_id": ATTEMPT, "root": candidate.ROOT,
                 "plan_raw_sha256": "6" * 64,
                 "registry_raw_sha256": science.REGISTRY_RAW_SHA256,
                 "planned_identities": identities, "roles": roles,
                 "external_inputs": inputs,
                 "stages": {role: {"status": "success", "failure": None}
                            for role in candidate.ROLES}}
    coverage = {"format": candidate.FORMAT, "attempt_id": ATTEMPT,
                "planned": {"chunks": 480, "datasets": 960, "evaluations": 2880},
                "chunks": [{"pair_id": identity["pair_id"], "seed": identity["seed"],
                            "layout": identity["layout"], "latest_attempt": ATTEMPT,
                            "status": "success"} for identity in identities[::6]],
                "evaluations": [{"identity": identity, "latest_attempt": ATTEMPT,
                                 "status": "success", "failure": None}
                                for identity in identities]}
    diagnostics = {"format": candidate.FORMAT, "attempt_id": ATTEMPT,
                   "series": series}
    values = {"execution.json": execution, "coverage.json": coverage,
              "analysis.json": analysis, "diagnostics.json": diagnostics}
    raw = {name: science.canonical_json(value) for name, value in values.items()}
    expected = {"attempt_id": ATTEMPT, "revision": REVISION,
                "plan_raw_sha256": "6" * 64,
                "registry_raw_sha256": science.REGISTRY_RAW_SHA256,
                "role_pins": roles, "input_pins": inputs, "receipt_pins": receipts}
    verification = {"format": candidate.FORMAT, "attempt_id": ATTEMPT,
                    "reader": {"separate_process": True, "exit_code": 0, "reaped": True},
                    "receipt_pins": receipts,
                    "payload_pins": {name: pin(raw[name]) for name in candidate.PAYLOADS[:-1]},
                    "semantic_checks": {"science_contract": "pass", "slice_inventory": "pass",
                                        "coverage": "pass", "saved_raw": "pass",
                                        "independent_audit": "pass"},
                    "unverified": ["source/runtime and process evidence externally unverified"]}
    values["verification.json"] = verification
    raw["verification.json"] = science.canonical_json(verification)
    expected["payload_pins"] = {name: pin(raw[name]) for name in candidate.PAYLOADS}
    marker = {"format": candidate.FORMAT, "attempt_id": ATTEMPT,
              "payloads": [{"path": name, **expected["payload_pins"][name]}
                           for name in candidate.PAYLOADS]}
    marker_raw = science.canonical_json(marker)
    expected["marker_pin"] = pin(marker_raw)
    return values, raw, marker_raw, expected


def check(raw, marker, expected, role_snapshots=ROLE_SNAPSHOTS):
    return candidate.validate_candidate_bundle(raw, marker, expected=expected,
                                               role_snapshots=role_snapshots)


def reseal(values, raw, expected, name):
    raw[name] = science.canonical_json(values[name])
    if name != "verification.json":
        values["verification.json"]["payload_pins"][name] = pin(raw[name])
        raw["verification.json"] = science.canonical_json(values["verification.json"])
    expected["payload_pins"] = {path: pin(raw[path]) for path in candidate.PAYLOADS}
    marker = {"format": candidate.FORMAT, "attempt_id": ATTEMPT,
              "payloads": [{"path": path, **expected["payload_pins"][path]}
                           for path in candidate.PAYLOADS]}
    marker_raw = science.canonical_json(marker)
    expected["marker_pin"] = pin(marker_raw)
    return marker_raw


class CandidateV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values, cls.raw, cls.marker, cls.expected = make_bundle()

    def bundle(self):
        return (copy.deepcopy(self.values), dict(self.raw), self.marker,
                copy.deepcopy(self.expected))

    def test_invented_five_payloads_have_exact_inventory_without_formal_credit(self):
        result = check(self.raw, self.marker, self.expected)
        self.assertEqual((result["planned_evaluations"], result["main_slice_rows"],
                          result["diagnostic_rows"]), (2880, 1233, 2835))
        self.assertFalse(result["formal_permission"])
        self.assertFalse(result["S4_ACCEPTED"])
        self.assertEqual(result["campaign_evaluations_credited"], 0)
        self.assertEqual(result["event_offset_exclusion_ledger"], "not_supplied")
        self.assertEqual(result["quality_current_previous_dependency_ledger"],
                         "not_supplied")
        self.assertEqual(result["primary_delay_median_from_slice_rows"],
                         "not_derivable")

    def test_external_raw_pin_rejects_changed_payload_and_marker(self):
        values, raw, marker, expected = self.bundle()
        raw["execution.json"] += b" "
        with self.assertRaises(science.V03ValidationError):
            check(raw, marker, expected)
        _, raw, marker, expected = self.bundle()
        with self.assertRaises(science.V03ValidationError):
            check(raw, marker + b" ", expected)

    def test_resealed_coverage_gap_duplicate_and_wrong_attempt_rejected(self):
        for change in (lambda v: v["evaluations"].pop(),
                       lambda v: v["evaluations"].__setitem__(1,
                                  copy.deepcopy(v["evaluations"][0])),
                       lambda v: v["chunks"][0].update(latest_attempt="later"),
                       lambda v: v["evaluations"][0].update(status="failed",
                                                                failure="unverified")):
            values, raw, _, expected = self.bundle()
            change(values["coverage.json"])
            marker = reseal(values, raw, expected, "coverage.json")
            with self.subTest(change=change), self.assertRaises(science.V03ValidationError):
                check(raw, marker, expected)

    def test_resealed_main_and_sidecar_slice_tamper_rejected(self):
        for change in (lambda v: v["series"]["incident-recall"].pop(),
                       lambda v: v["series"]["score-availability"].__setitem__(
                           1, copy.deepcopy(v["series"]["score-availability"][0])),
                       lambda v: v["series"]["score-signal-onset"][0]
                           ["metric"].update(ci_status="complete"),
                       lambda v: v["series"]["score-threshold-exceedance"][0]
                           ["metric"].update(denominator=1)):
            values, raw, _, expected = self.bundle()
            change(values["diagnostics.json"])
            marker = reseal(values, raw, expected, "diagnostics.json")
            with self.subTest(change=change), self.assertRaises(science.V03ValidationError):
                check(raw, marker, expected)

    def test_resealed_science_and_source_claims_rejected(self):
        for change in (lambda v: v["analysis.json"]["provenance"].update(
                           producer_revision="b" * 40),
                       lambda v: v["analysis.json"]["candidate_tables"][0]
                           ["metrics"]["machine_recall"].update(numerator=0),
                       lambda v: v["analysis.json"]["slices"].pop()):
            values, raw, _, expected = self.bundle()
            change(values)
            marker = reseal(values, raw, expected, "analysis.json")
            with self.subTest(change=change), self.assertRaises(science.V03ValidationError):
                check(raw, marker, expected)

    def test_resealed_claims_of_reader_or_five_role_completion_rejected(self):
        values, raw, _, expected = self.bundle()
        values["verification.json"]["reader"]["reaped"] = False
        marker = reseal(values, raw, expected, "verification.json")
        with self.assertRaises(science.V03ValidationError):
            check(raw, marker, expected)
        values, raw, _, expected = self.bundle()
        values["execution.json"]["stages"]["audit"] = {
            "status": "failed", "failure": "invented failure"}
        marker = reseal(values, raw, expected, "execution.json")
        with self.assertRaises(science.V03ValidationError):
            check(raw, marker, expected)

    def test_duplicate_key_rejected_even_when_external_pin_is_resealed(self):
        _, raw, _, expected = self.bundle()
        marker = self.marker.replace(b'"format":', b'"format":"other","format":', 1)
        expected["marker_pin"] = pin(marker)
        with self.assertRaises(science.V03ValidationError):
            check(raw, marker, expected)

    def test_resealed_cross_role_source_and_runtime_path_conflict_rejected(self):
        for kind in ("sources", "runtime"):
            values, raw, _, expected = self.bundle()
            snapshots = copy.deepcopy(ROLE_SNAPSHOTS)
            producer_path = next(iter(snapshots["producer"][kind]))
            fake = b"different bytes for same full revision and logical path"
            audit_entry = values["execution.json"]["roles"]["audit"][kind][0]
            audit_entry.update(path=producer_path.upper(), raw_sha256=pin(fake)["sha256"],
                               byte_count=len(fake))
            snapshots["audit"][kind] = {producer_path.upper(): fake}
            expected["role_pins"] = copy.deepcopy(values["execution.json"]["roles"])
            marker = reseal(values, raw, expected, "execution.json")
            with self.subTest(kind=kind), self.assertRaisesRegex(
                    science.V03ValidationError, "cross-role revision/path byte conflict"):
                check(raw, marker, expected, snapshots)

    def test_resealed_incident_dimension_count_and_delay_marginal_rejected(self):
        for kind in ("count", "delay"):
            values, raw, _, expected = self.bundle()
            incident = values["diagnostics.json"]["series"]["incident-recall"]
            main = values["analysis.json"]["slices"]
            core, stress, overall = incident[2], incident[48 + 2], incident[96 + 2]
            if kind == "count":
                for diagnostic_row in (core, overall):
                    diagnostic_row["actual_count"] += 1
                    diagnostic_row["metric"] = metric(diagnostic_row["actual_count"],
                                                       diagnostic_row["planned_count"])
                    diagnostic_row["delay_summary"] = slices.delay_summary(
                        delay_histogram(diagnostic_row["actual_count"]))
            else:
                core["delay_summary"] = slices.delay_summary(
                    [0, 0, core["actual_count"], 0, 0])
                stress_hist = delay_histogram(stress["actual_count"])
                stress_hist[2] += core["actual_count"]
                overall["delay_summary"] = slices.delay_summary(stress_hist)
            main[2].update(copy.deepcopy(core))
            main[96 + 2].update(copy.deepcopy(overall))
            reseal(values, raw, expected, "diagnostics.json")
            marker = reseal(values, raw, expected, "analysis.json")
            with self.subTest(kind=kind), self.assertRaisesRegex(
                    science.V03ValidationError, "incident dimension count/delay marginal"):
                check(raw, marker, expected)

    def test_resealed_exclusive_score_availability_and_threshold_marginal_rejected(self):
        for name in ("score-availability", "score-threshold-exceedance"):
            values, raw, _, expected = self.bundle()
            sidecar = values["diagnostics.json"]["series"][name]
            for diagnostic_row in (sidecar[56], sidecar[2 * 89 + 56]):
                diagnostic_row["actual_count"] += 1
                diagnostic_row["metric"] = metric(diagnostic_row["actual_count"],
                                                   diagnostic_row["metric"]["denominator"])
            if name == "score-availability":
                main = values["analysis.json"]["slices"]
                main[432 + 56].update(copy.deepcopy(sidecar[56]))
                main[432 + 2 * 89 + 56].update(copy.deepcopy(sidecar[2 * 89 + 56]))
            reseal(values, raw, expected, "diagnostics.json")
            marker = (reseal(values, raw, expected, "analysis.json")
                      if name == "score-availability" else
                      reseal(values, raw, expected, "verification.json"))
            with self.subTest(name=name), self.assertRaisesRegex(
                    science.V03ValidationError, "exclusive score dimension marginal"):
                check(raw, marker, expected)

    def test_resealed_primary_pooled_delay_mean_drift_rejected(self):
        values, raw, _, expected = self.bundle()
        values["analysis.json"]["candidate_tables"][0]["metrics"]["delay_summary"][
            "mean"] = 2.1  # still within reported min/max, but disagrees with sidecar
        marker = reseal(values, raw, expected, "analysis.json")
        with self.assertRaisesRegex(
                science.V03ValidationError, "incident sidecar/primary pooled delay"):
            check(raw, marker, expected)

    def test_resealed_overall_equipment_key_shift_keeps_totals_but_is_rejected(self):
        values, raw, _, expected = self.bundle()
        incident = values["diagnostics.json"]["series"]["incident-recall"]
        main = values["analysis.json"]["slices"]
        first, second = incident[96 + 2], incident[96 + 3]
        before = (sum(r["planned_count"] for r in (first, second)),
                  sum(r["actual_count"] for r in (first, second)))
        for cell, delta in ((first, -1), (second, 1)):
            cell["planned_count"] += delta
            cell["actual_count"] += delta
            cell["metric"] = metric(cell["actual_count"], cell["planned_count"])
            cell["delay_summary"] = slices.delay_summary(
                delay_histogram(cell["actual_count"]))
        self.assertEqual(before,
                         (sum(r["planned_count"] for r in (first, second)),
                          sum(r["actual_count"] for r in (first, second))))
        main[96 + 2].update(copy.deepcopy(first))
        main[96 + 3].update(copy.deepcopy(second))
        reseal(values, raw, expected, "diagnostics.json")
        marker = reseal(values, raw, expected, "analysis.json")
        with self.assertRaisesRegex(
                science.V03ValidationError, "per-key overall incident-recall"):
            check(raw, marker, expected)


if __name__ == "__main__":
    unittest.main()
