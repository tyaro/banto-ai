"""S1 contract/adversarial tests; no scorer, materializer, or output publication."""

from __future__ import annotations

import copy
import base64
import hashlib
import json
import zlib
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import _anomaly_v03_contract as c
from banto_ai._anomaly_v03_schema import common_defs

ROOT = Path(__file__).resolve().parents[1]


def status(run="not_run", engineering="not_evaluated", performance="not_evaluated"):
    return {"run_status": run, "engineering_status": engineering, "performance_status": performance}


def payload():
    return {"path": "fixture/result.json", "raw_sha256": "a"*64, "canonical_sha256": "b"*64, "row_count": 0}


SOURCE_SNAPSHOTS = {letter*40: {f"src/{role}.py": f"# invented {role} source\n".encode()}
                    for letter, role in (("a", "producer"), ("b", "audit"), ("c", "analysis"))}


def source_descriptor(letter):
    return {"revision": letter*40, "sources": [{"path": path, "raw_sha256": hashlib.sha256(raw).hexdigest(), "byte_count": len(raw)}
                                              for path, raw in SOURCE_SNAPSHOTS[letter*40].items()]}


def provenance():
    return {"science_revision": c.SCIENCE_REVISION, "post_audit_revision": c.STATUS_REVISION,
            "producer_revision": "a"*40, "producer_source": source_descriptor("a"),
            "registry_raw_sha256": v.REGISTRY_RAW_SHA256, "inventory": [payload()]}


def matrix_result(role="smoke"):
    identities = v.evaluation_inventory(role)
    return {"schema_version": "0.3", "result_type": "anomaly-multiseed-v03", "status": status(),
            "provenance": provenance(), "role": role, "planned_counts": c.counts(role),
            "evaluations": [{"identity": i, "status": "not_started", "failure_stage": None,
                             "safe_reason": None, "input_hashes": None, "evidence": []} for i in identities],
            "coverage": {key: len(identities) if key == "not_started" else 0 for key in c.SLOT_STATUS}}


def ledgers():
    """Invented schema rows, deliberately not numerically computed scores."""
    identity = v.evaluation_inventory("dev")[0]
    events = v.event_inventory(identity)
    profile = {"profile_id": "profile-0", "identity": identity, "profile_version": "0.3", "equipment": "motor-01",
               "full_target": "motor-01.motor_current", "mode": "stopped", "recipe": "stop", "status": "calibrated",
               "fit_samples": [], "calibration_samples": [5400+180*r+u for r in range(10) for u in range(1,30)],
               "planned_calibration_points": 290, "minimum_calibration_points": 250, "phase_medians": None,
               "center": 0.0, "scale": 1.0, "c2_state": None, "reason": None}
    scores = []
    for sample in (7201, 7202):
        scores.append({"score_id": f"score-{sample}", "dataset_id": identity["dataset_id"], "candidate_id": identity["candidate_id"],
                       "sample": sample, "timestamp_ms": c.START_MS+sample*1000, "phase": sample%30, "equipment": "motor-01",
                       "full_target": "motor-01.motor_current", "mode": "stopped", "recipe": "stop", "profile_id": "profile-0",
                       "dependencies": [{"full_target": "motor-01.motor_current", "sample": s, "timestamp_ms": c.START_MS+s*1000,
                                         "quality": "ok", "value": 7.0} for s in (sample-1,sample)],
                       "residual": 7.0, "score": 7.0, "available": True, "exclusion_reason": None,
                       "exclusion_tags": [], "threshold_exceeded": True, "streak": sample-7200,
                       "source_episode_id": "source-0" if sample == 7202 else None})
    source = {"episode_id": "source-0", "dataset_id": identity["dataset_id"], "candidate_id": identity["candidate_id"],
              "equipment": "motor-01", "full_target": "motor-01.motor_current", "mode": "stopped", "recipe": "stop",
              "visit_start_sample": 7200, "profile_id": "profile-0", "onset_ms": c.START_MS+7202000,
              "end_ms": c.START_MS+7203000, "support_score_ids": ["score-7201", "score-7202"]}
    episode = {"episode_id": "equipment-0", "dataset_id": identity["dataset_id"], "candidate_id": identity["candidate_id"],
               "equipment": "motor-01", "mode": "stopped", "recipe": "stop", "visit_start_sample": 7200,
               "onset_ms": source["onset_ms"], "end_ms": source["end_ms"], "source_episode_ids": ["source-0"],
               "matched_event_id": None, "context_tags": ["raw-event"]}
    return identity, {"events": events, "profiles": [profile], "scores": scores, "source_episodes": [source],
                      "equipment_episodes": [episode], "incidents": []}


def unprocessed(identity, event):
    return {"dataset_id": identity["dataset_id"], "event_id": event["event_id"], "status": "not_processed",
            "candidate_count": 0, "candidate_episode_ids": [], "selected_candidate_episode_id": None,
            "selected_source_episode_id": None, "support_score_ids": [], "reason": "not_processed",
            "matched_episode_id": None, "causal_detected": None, "delay_seconds": None, "secondary_canonical_detected": None}


def evaluator_result():
    identity = v.evaluation_inventory("dev")[0]
    events = v.event_inventory(identity)
    return {"schema_version": "0.3", "result_type": "event-aware-anomaly-v03", "status": status(),
            "provenance": provenance(), "identity": identity, "input_hashes": {k:"a"*64 for k in common_defs()["input_hashes"]["properties"]},
            "splits": {"warmup":[0,1800], "fit":[1800,5400], "calibration":[5400,7200], "test":[7200,9000]},
            "events": events, "profiles": [], "scores": [], "source_episodes": [], "equipment_episodes": [],
            "incidents": [unprocessed(identity,e) for e in events if e["event_class"] in ("machine","sensor")],
            "metrics": None, "slices": [], "row_counts": {"events":40,"profiles":0,"scores":0,"source_episodes":0,"equipment_episodes":0,"incidents":20}}


def analysis_result():
    return {"schema_version":"0.3", "result_type":"anomaly-multiseed-analysis-v03", "status":status(),
            "analysis_consumer":source_descriptor("c"),
            "provenance":provenance(), "bootstrap":copy.deepcopy(c.config_values(c.BOOTSTRAP_HASH,c.GOLDEN_DRAWS)[3]["bootstrap"]),
            "candidate_tables":[{"candidate_id":a,"stratum":b,"profile_status":"not_evaluated","metrics":None,"gates":[],"qualified":False}
                                for a in c.CANDIDATES for b in (*c.STRATA,"overall")],
            "slices":[], "selected_candidate":None, "decision":"not_evaluated"}


def audit_result():
    names=("inventory","raw-observations","profiles","scores","support","matching","denominators","bootstrap","gates","selection","native-publication")
    return {"schema_version":"0.3", "result_type":"anomaly-multiseed-audit-v03", "status":status(),
            "provenance":provenance(), "consumer_revision":"b"*40,
            "input_analysis":source_descriptor("c"), "audit_consumer":source_descriptor("b"),
            "checks":[{"name":name,"status":"not_evaluated","evidence":[]} for name in names], "result_trusted":False,
            "limitations":["owner-can-change-acl","privileged-writer","no-power-loss-guarantee","synthetic-only"]}


class V03ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshots = {p: (ROOT/p).read_bytes() for p in (*c.CONFIG_PATHS, *c.SCHEMA_PATHS)}
        cls.configs = {p: v.strict_json(cls.snapshots[p]) for p in c.CONFIG_PATHS[:4]}
        # Exact historical documentation bytes, also usable in shallow CI checkouts.
        fixture = json.loads((ROOT/"tests/fixtures/anomaly-v03-plan-snapshots.json").read_bytes())
        assert fixture["science_revision"] == c.SCIENCE_REVISION
        assert fixture["status_revision"] == c.STATUS_REVISION
        cls.science = zlib.decompress(base64.b85decode(fixture["science_zlib_base85"]))
        cls.status_plan = zlib.decompress(base64.b85decode(fixture["status_zlib_base85"]))

    def check_bundle(self, snapshots=None, **kwargs):
        return v.validate_bundle(self.snapshots if snapshots is None else snapshots,
                                 science_plan_raw=kwargs.get("science", self.science),
                                 status_plan_raw=kwargs.get("status_plan", self.status_plan))

    def test_complete_bundle_positive_and_no_run_status(self):
        report = self.check_bundle()
        self.assertEqual(report["validation_status"], "configuration_valid")
        self.assertEqual(report["run_status"], "not_run")
        self.assertEqual(report["engineering_status"], "not_evaluated")
        self.assertEqual(report["performance_status"], "not_evaluated")
        self.assertEqual(report["runtime_io_status"], "not_checked")

    def test_pure_validation_never_reads_files_network_or_environment(self):
        with ExitStack() as stack:
            for name in ("builtins.open", "pathlib.Path.open", "pathlib.Path.stat", "pathlib.Path.resolve",
                         "os.stat", "os.listdir", "os.getenv", "socket.socket", "subprocess.run", "subprocess.Popen"):
                stack.enter_context(patch(name, side_effect=AssertionError("unexpected I/O")))
            self.check_bundle()
            v.validate_decoded_configs(copy.deepcopy(self.configs))
            v.validate_result_contract(matrix_result())

    def test_all_pins_independently_hash_exact_bytes(self):
        registry = json.loads(self.snapshots[c.CONFIG_PATHS[4]])
        self.assertEqual(len(registry["pins"]), 13)
        self.assertNotIn(c.CONFIG_PATHS[4], [p["path"] for p in registry["pins"]])
        for pin in registry["pins"]:
            with self.subTest(path=pin["path"]):
                raw = self.snapshots[pin["path"]]
                canonical = json.dumps(json.loads(raw), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), pin["raw_sha256"])
                self.assertEqual(hashlib.sha256(canonical).hexdigest(), pin["canonical_sha256"])
        self.assertEqual(hashlib.sha256(self.science).hexdigest(), v.PLAN_SCIENCE_RAW_SHA256)
        self.assertEqual(hashlib.sha256(self.status_plan).hexdigest(), v.PLAN_STATUS_RAW_SHA256)

    def test_each_snapshot_raw_and_semantic_tamper_rejected(self):
        for path in self.snapshots:
            with self.subTest(path=path):
                values = dict(self.snapshots)
                values[path] += b" "
                with self.assertRaises(v.V03ValidationError):
                    self.check_bundle(values)

    def test_registry_and_payload_coordinated_hash_tamper_rejected(self):
        snapshots = dict(self.snapshots)
        mutated = copy.deepcopy(self.configs[c.CONFIG_PATHS[0]])
        mutated["sample_count"] = 8999
        snapshots[c.CONFIG_PATHS[0]] = v.canonical_json(mutated)
        registry = v.strict_json(snapshots[c.CONFIG_PATHS[4]])
        registry["pins"][0]["raw_sha256"] = hashlib.sha256(snapshots[c.CONFIG_PATHS[0]]).hexdigest()
        registry["pins"][0]["canonical_sha256"] = v.canonical_sha256(mutated)
        snapshots[c.CONFIG_PATHS[4]] = v.canonical_json(registry)
        with self.assertRaisesRegex(v.V03ValidationError, "external registry"):
            self.check_bundle(snapshots)

    def test_plan_bytes_and_snapshot_inventory_tamper_rejected(self):
        for kwargs in ({"science": self.science+b" "}, {"status_plan": self.status_plan+b" "}):
            with self.subTest(kwargs=list(kwargs)), self.assertRaises(v.V03ValidationError):
                self.check_bundle(**kwargs)
        for extra in (False, True):
            snapshots = dict(self.snapshots)
            if extra:
                snapshots["other.json"] = b"{}"
            else:
                del snapshots[c.SCHEMA_PATHS[0]]
            with self.assertRaises(v.V03ValidationError):
                self.check_bundle(snapshots)

    def test_seed_registry_independent_recalculation(self):
        used = {11,17,23,29,37,42,53,67,79,97}
        output = {}
        for role, n in (("dev",8),("smoke",2),("holdout",40)):
            seeds = []
            for i in range(n):
                j = 0
                while True:
                    digest = hashlib.sha256(f"banto-ai/anomaly-v03/seeds/{role}/{i}/{j}".encode()).hexdigest()
                    number = int(digest[:16],16) & 0x7fffffffffffffff
                    if number >= 1000000 and number not in used:
                        break
                    j += 1
                self.assertEqual(j,0)
                used.add(number)
                seeds.append(number)
            output[role] = seeds
        canonical = json.dumps(output, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), "fa072f5299132fc22cce471c94ca189ddfc0f3acd27c2c5201bc31a2a9287505")
        self.assertEqual([r["seeds"] for r in v.seed_registry()["entries"]],list(output.values()))
        self.assertEqual(len(used),60)
        from tools.ci_shared_fixtures import record
        record("seeds", self.id(), lambda: {"seeds": output, "seed_count": len(used)-10,
                                            "canonical_sha256": hashlib.sha256(canonical).hexdigest()})

    def test_full_bootstrap_independent_hash_and_golden(self):
        # Independent loop, hex conversion and streaming digest, no production draw helper.
        digest = hashlib.sha256()
        golden = {}
        cutoff = 2**256 - 2**256 % 40
        accepted = 0
        for b in range(50000):
            row = []
            for j in range(40):
                counter = 0
                while True:
                    value = int(hashlib.sha256(f"sha256-counter-rejection-v1:2026090603:{b}:{j}:{counter}".encode()).hexdigest(),16)
                    if value < cutoff:
                        break
                    counter += 1
                row.append(value % 40)
            digest.update(bytes(row)); accepted += len(row)
            if b in (0,1,24999,49999):
                golden[b] = row
        self.assertEqual(accepted,2000000)
        self.assertEqual(digest.hexdigest(), "e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5")
        actual = v.bootstrap_indices()
        self.assertEqual(hashlib.sha256(actual).hexdigest(),digest.hexdigest())
        registered = self.configs[c.CONFIG_PATHS[3]]["bootstrap"]
        self.assertEqual(registered["indices_raw_sha256"], digest.hexdigest())
        for draw in registered["golden_draws"]:
            self.assertEqual(draw["indices"],golden[draw["replicate"]])
        from tools.ci_shared_fixtures import record
        record("bootstrap", self.id(), lambda: {"bytes": len(actual), "raw_sha256": hashlib.sha256(actual).hexdigest(),
                                                "golden_draws": [{"replicate": i, "indices": list(actual[i*40:(i+1)*40])} for i in (0,1,24999,49999)]})

    def test_strict_json_rejects_duplicates_nonfinite_and_bad_encoding(self):
        for raw in (b'{"x":1,"x":2}', b'{"nested":{"x":1,"x":2}}', b'NaN', b'Infinity', b'-Infinity', b'1e9999', b'\xff', b'"\\ud800"', b'\xef\xbb\xbf{}'):
            with self.subTest(raw=raw), self.assertRaises(v.V03ValidationError):
                v.strict_json(raw)

    def test_canonical_preserves_signed_zero_and_large_exact_integer(self):
        self.assertEqual(v.canonical_json({"z": -0.0, "seed": 2486912926863618161}), b'{"seed":2486912926863618161,"z":-0.0}')
        for val in (float("nan"),float("inf"), {1:0}, {"x": object()}, (1,2)):
            with self.subTest(value=repr(val)), self.assertRaises(v.V03ValidationError):
                v.canonical_json(val)

    def test_paths_reject_traversal_absolute_unc_drive_and_aliases(self):
        invalid = ("../x", "/x", "//host/share", "\\\\host\\share", "C:x", "C:/x", "C:\\x", "a/../b", "a/./b", "a//b", "a\\b", "a%2f..", "a:x", "a/CON", "a/LPT1.txt", "a/file.", "a/file ", "", True)
        for path in invalid:
            with self.subTest(path=path), self.assertRaises(v.V03ValidationError):
                v.safe_relative_path(path)
        self.assertEqual(v.safe_relative_path("schemas/test.json"), "schemas/test.json")

    def test_all_schemas_recursively_close_objects_and_resolve_refs(self):
        object_count = 0
        for path in c.SCHEMA_PATHS:
            schema = v.strict_json(self.snapshots[path])
            def walk(node):
                nonlocal object_count
                if type(node) is dict:
                    if node.get("type") == "object":
                        object_count += 1
                        self.assertIs(node.get("additionalProperties"),False)
                        self.assertEqual(set(node["required"]),set(node["properties"]))
                    if "$ref" in node:
                        ref = node["$ref"]
                        self.assertTrue(ref.startswith("#/$defs/"))
                        self.assertIn(ref.split("/")[-1],schema["$defs"])
                    for child in node.values(): walk(child)
                elif type(node) is list:
                    for child in node: walk(child)
            walk(schema)
        self.assertGreater(object_count,70)

    def test_nested_additional_property_in_each_config_rejected(self):
        for path in c.CONFIG_PATHS[:4]:
            bad = copy.deepcopy(self.configs)
            bad[path]["unknown"] = 0
            with self.subTest(path=path), self.assertRaises(v.V03ValidationError):
                v.validate_decoded_configs(bad)
        bad = copy.deepcopy(self.configs)
        bad[c.CONFIG_PATHS[0]]["layout"]["unknown"] = 0
        with self.assertRaises(v.V03ValidationError): v.validate_decoded_configs(bad)

    def test_scientific_and_cross_config_changes_rejected(self):
        mutations = ((0,"sample_count",8999),(0,"overlay_order",["sensor","machine","ignored","data_quality"]),
                     (0,"splits",{"warmup":[0,1800],"fit":[1800,5401],"calibration":[5400,7200],"test":[7200,9000]}),
                     (1,"candidate_id","C3"),(2,"candidate_order",list(reversed(c.CANDIDATES))),
                     (2,"stratum_order",["core"]),(2,"roles",["dev","smoke","production"]),
                     (3,"input_root","../old"),(3,"control_promotable",True))
        for index,key,val in mutations:
            bad = copy.deepcopy(self.configs); bad[c.CONFIG_PATHS[index]][key] = val
            with self.subTest(key=key),self.assertRaises(v.V03ValidationError): v.validate_decoded_configs(bad)

    def test_bool_integer_and_nonfinite_config_rejected(self):
        for val in (True,False,9000.0,float("nan"),float("inf")):
            bad = copy.deepcopy(self.configs); bad[c.CONFIG_PATHS[0]]["sample_count"] = val
            with self.subTest(value=val),self.assertRaises(v.V03ValidationError): v.validate_decoded_configs(bad)

    def test_seed_counter_counts_and_golden_config_tamper_rejected(self):
        for kind in ("seed","counter","role","counts","bootstrap","golden"):
            bad = copy.deepcopy(self.configs)
            matrix=bad[c.CONFIG_PATHS[2]]; boot=bad[c.CONFIG_PATHS[3]]["bootstrap"]
            if kind == "seed": matrix["seed_registry"]["entries"][0]["seeds"][0] += 1
            elif kind == "counter": matrix["seed_registry"]["entries"][0]["counters"][0] = True
            elif kind == "role": matrix["seed_registry"]["role_order"].reverse()
            elif kind == "counts": matrix["counts"][2]["positive_incidents"] -= 480
            elif kind == "bootstrap": boot["replicates"] = 49999
            else: boot["golden_draws"][0]["indices"][0] = 0
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): v.validate_decoded_configs(bad)

    def test_independent_counts_and_event_window_inventory(self):
        rows = v.evaluation_inventory("holdout")
        self.assertEqual(len(rows),2880)
        datasets = {r["dataset_id"] for r in rows}
        self.assertEqual(len(datasets),960)
        events = positives = enabled = exposure = 0
        for row in rows[::3]:
            schedule = v.event_inventory(row)
            self.assertEqual(len(schedule),40)
            union = set()
            for e in schedule:
                self.assertLessEqual(e["window_end_sample"],(e["start_sample"]//30+1)*30)
                union.update(range(e["start_sample"],e["window_end_sample"]))
            self.assertEqual(len(union),235)
            events += len(schedule); positives += sum(e["event_class"] in ("machine","sensor") for e in schedule)
            enabled += sum(e["enabled"] for e in schedule); exposure += 3600-len(union)
        self.assertEqual((events,positives,enabled,exposure),(38400,19200,33600,3230400))
        self.assertEqual(len(rows)*1800*8,41472000)
        self.assertEqual(len(rows)*48,138240)
        self.assertEqual(len(datasets)*9000*2,17280000)
        self.assertEqual(len(v.evaluation_inventory("dev")),576)
        self.assertEqual(len(v.evaluation_inventory("smoke")),144)

    def test_identity_unknown_role_seed_candidate_bool_or_pair_rejected(self):
        original = v.evaluation_inventory("holdout")[0]
        for key,val in (("role","test"),("seed",True),("seed",42),("candidate_id","C0"),("layout",False),("layout",12),("stratum","overall"),("pair_id","wrong"),("evaluation_id","wrong")):
            bad=copy.deepcopy(original); bad[key]=val
            with self.subTest(key=key),self.assertRaises(v.V03ValidationError): v.validate_identity(bad)

    def test_matrix_planned_not_run_is_not_engineering_success(self):
        report=v.validate_result_contract(matrix_result())
        self.assertEqual(report["validation_status"],"result_contract_valid")
        self.assertEqual(report["run_status"],"not_run")
        self.assertFalse(report["result_trusted"])

    def test_matrix_counts_inventory_duplicate_pairing_and_unknown_status(self):
        for kind in ("count","missing","duplicate","order","status","role","boolean"):
            value=matrix_result()
            if kind=="count": value["planned_counts"]["datasets"]-=1
            elif kind=="missing": value["evaluations"].pop()
            elif kind=="duplicate": value["evaluations"][1]=copy.deepcopy(value["evaluations"][0])
            elif kind=="order": value["evaluations"].reverse()
            elif kind=="status": value["evaluations"][0]["status"]="valid"
            elif kind=="role": value["role"]="dev"
            else: value["coverage"]["success"]=False
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): v.validate_result_contract(value)

    def test_matrix_paired_input_hash_mismatch_rejected(self):
        value=matrix_result(); value["status"]=status("in_progress")
        for slot in value["evaluations"][:2]:
            slot.update(status="success",evidence=[payload()],input_hashes={k:"a"*64 for k in common_defs()["input_hashes"]["properties"]})
        value["coverage"]["success"]=2; value["coverage"]["not_started"]-=2
        v.validate_result_contract(value)
        value["evaluations"][1]["input_hashes"]["observations"]="b"*64
        with self.assertRaises(v.V03ValidationError): v.validate_result_contract(value)

    def test_producer_never_claims_performance_or_incomplete_acceptance(self):
        for run,eng,perf in (("not_run","pass","not_evaluated"),("complete","pass","not_evaluated"),("complete","pass","pass"),("banana","not_evaluated","not_evaluated")):
            value=matrix_result(); value["status"]=status(run,eng,perf)
            with self.subTest(run=run,eng=eng,perf=perf),self.assertRaises(v.V03ValidationError): v.validate_result_contract(value)

    def test_ledger_shape_positive_does_not_compute_scores(self):
        identity, rows=ledgers()
        self.assertIsNone(v.validate_ledger_rows(identity,**rows))

    def test_layout_overlap_enable_time_and_id_tamper(self):
        for field,val in (("start_sample",7201),("end_sample",7204),("window_end_ms",0),("enabled",False),("event_id","bad"),("magnitude",True)):
            identity,rows=ledgers(); rows["events"][0][field]=val
            with self.subTest(field=field),self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)

    def test_profile_split_fit_calibration_and_identity_tamper(self):
        for field,val in (("fit_samples",[7200]),("calibration_samples",[5400,7200]),("scale",0.0),("identity",v.evaluation_inventory("smoke")[0]),("unknown",1)):
            identity,rows=ledgers(); rows["profiles"][0][field]=val
            with self.subTest(field=field),self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)

    def test_score_support_time_dependencies_unknown_and_bool_tamper(self):
        for field,val in (("sample",True),("timestamp_ms",0),("phase",0),("full_target","conveyor-01.motor_current"),("profile_id","unknown"),("available",False),("score",float("nan"))):
            identity,rows=ledgers(); rows["scores"][0][field]=val
            with self.subTest(field=field),self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)
        identity,rows=ledgers(); rows["scores"][0]["dependencies"][0]["sample"]=7202
        with self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)

    def test_source_support_duplicate_missing_gap_and_merge_tamper(self):
        for field,val in (("support_score_ids",["score-7201","score-7201"]),("support_score_ids",["missing","score-7202"]),("onset_ms",c.START_MS+7203000),("visit_start_sample",7380)):
            identity,rows=ledgers(); rows["source_episodes"][0][field]=val
            with self.subTest(field=field),self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)
        identity,rows=ledgers(); rows["equipment_episodes"][0]["end_ms"]+=1000
        with self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)

    def test_unprocessed_incident_cannot_be_filled_as_miss(self):
        identity,rows=ledgers()
        row={"dataset_id":identity["dataset_id"],"event_id":rows["events"][0]["event_id"],"status":"not_processed",
             "candidate_count":0,"candidate_episode_ids":[],"selected_candidate_episode_id":None,"selected_source_episode_id":None,
             "support_score_ids":[],"reason":"not_processed","matched_episode_id":None,"causal_detected":None,"delay_seconds":None,
             "secondary_canonical_detected":None}
        rows["incidents"]=[row]; v.validate_ledger_rows(identity,**rows)
        row["causal_detected"]=False
        with self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)

    def test_M_Q_are_registered_contract_ids_not_scorer_tests(self):
        fixtures=self.configs[c.CONFIG_PATHS[1]]["fixtures"]
        self.assertEqual(fixtures["matching"],[f"M{i}" for i in range(1,10)])
        self.assertEqual(fixtures["quantization"],[f"Q{i}" for i in range(1,6)])
        self.assertEqual(set(common_defs()["incident"]["properties"]["reason"]["enum"]),set(c.MATCH_REASONS))
        self.assertEqual(self.check_bundle()["s2_semantics_status"],"not_implemented")

    def test_all_four_result_schemas_accept_planned_metadata_only(self):
        for factory in (evaluator_result,matrix_result,analysis_result,audit_result):
            with self.subTest(kind=factory.__name__):
                report=v.validate_result_contract(factory())
                self.assertFalse(report["result_trusted"])
                self.assertEqual(report["independent_recomputation"],"required-not-performed")

    def test_evaluator_incomplete_rows_cannot_claim_complete(self):
        value=evaluator_result(); value["status"]=status("complete","pass")
        with self.assertRaises(v.V03ValidationError): v.validate_result_contract(value)

    def test_result_additional_properties_version_and_path_rejected(self):
        for factory in (evaluator_result,matrix_result,analysis_result,audit_result):
            for kind in ("additional","nested","version","path","hash"):
                value=factory()
                if kind=="additional": value["extra"]=True
                elif kind=="nested": value["provenance"]["inventory"][0]["extra"]=0
                elif kind=="version": value["schema_version"]="0.2"
                elif kind=="path": value["provenance"]["inventory"][0]["path"]="fixture/../escape.json"
                else: value["provenance"]["registry_raw_sha256"]="a"*64
                with self.subTest(factory=factory.__name__,kind=kind),self.assertRaises(v.V03ValidationError):
                    v.validate_result_contract(value)

    def test_analysis_tables_bootstrap_selection_tamper(self):
        for kind in ("tables","bootstrap","selection","qualified","status","control"):
            value=analysis_result()
            if kind=="tables": value["candidate_tables"][1]=copy.deepcopy(value["candidate_tables"][0])
            elif kind=="bootstrap": value["bootstrap"]["clusters"]=39
            elif kind=="selection": value["selected_candidate"]=c.CANDIDATES[1]
            elif kind=="qualified": value["candidate_tables"][3]["qualified"]=True
            elif kind=="status": value["decision"]="no_promotion"
            else: value["candidate_tables"][0]["qualified"]=True
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): v.validate_result_contract(value)

    def test_audit_cannot_claim_trust_or_skip_inventory(self):
        for kind in ("trust","duplicate","limitation","skip","complete"):
            value=audit_result()
            if kind=="trust": value["result_trusted"]=True
            elif kind=="duplicate": value["checks"][1]=copy.deepcopy(value["checks"][0])
            elif kind=="limitation": value["limitations"][1]=value["limitations"][0]
            elif kind=="skip": value["checks"][0]["status"]="skipped"
            else: value["checks"][0]["status"]="pass"
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): v.validate_result_contract(value)

    def test_ledger_duplicate_reversed_scores_and_threshold_claim_rejected(self):
        for kind in ("duplicate","reverse","threshold","streak"):
            identity,rows=ledgers()
            if kind=="duplicate": rows["scores"].append(copy.deepcopy(rows["scores"][0]))
            elif kind=="reverse": rows["scores"].reverse()
            elif kind=="threshold": rows["scores"][0]["score"]=4.0
            else: rows["scores"][1]["streak"]=3
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)

    def test_selected_candidate_cannot_reference_later_id(self):
        identity,rows=ledgers()
        incident=unprocessed(identity,rows["events"][0])
        incident.update(status="processed",candidate_count=1,candidate_episode_ids=["equipment-0"],
                        selected_candidate_episode_id="equipment-0",selected_source_episode_id="source-0",
                        support_score_ids=["score-7201","score-7202"],reason="causal_detected",matched_episode_id="equipment-0",
                        causal_detected=True,delay_seconds=2)
        rows["incidents"]=[incident]; rows["equipment_episodes"][0]["matched_event_id"]=incident["event_id"]
        v.validate_ledger_rows(identity,**rows)
        for field,val in (("selected_candidate_episode_id","later"),("delay_seconds",1),("support_score_ids",["score-7202","score-7201"]),("candidate_count",2)):
            bad=copy.deepcopy(rows); bad["incidents"][0][field]=val
            with self.subTest(field=field),self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**bad)

    def test_frozen_builder_results_are_not_mutable_registry_state(self):
        value=c.config_values(c.BOOTSTRAP_HASH,c.GOLDEN_DRAWS)
        value[3]["bootstrap"]["golden_draws"][0]["indices"][0]=0
        self.assertEqual(c.GOLDEN_DRAWS[0]["indices"][0],28)
        seeds=v.seed_registry(); seeds["entries"][0]["seeds"][0]=0
        self.assertEqual(v.seed_registry()["entries"][0]["seeds"][0],2486912926863618161)

    def test_no_registered_output_roots_exist(self):
        for path in c.OUTPUT_ROOTS:
            with self.subTest(path=path): self.assertFalse((ROOT/path).exists())


if __name__ == "__main__":
    unittest.main()
