"""Saved S1 audit probes. Values are invented reports, never computed runs."""
from __future__ import annotations

import copy
import hashlib
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import _anomaly_v03_contract as c
from banto_ai._anomaly_v03_schema import schemas
from tests.test_anomaly_v03 import SOURCE_SNAPSHOTS, analysis_result, audit_result, evaluator_result, ledgers, status, unprocessed


def delay_summary(count):
    return {"count":count, **{k:2.0 if count else None for k in ("median","mean","min","max")},
            "conditioned_on":"causal-detected-only", "undetected_fill":"forbidden", "unit":"seconds"}


def metric(n, d, *, kind="ratio", width=0.0005):
    if d == 0:
        return {"numerator":n,"denominator":d,"value":None,"ci_status":"inconclusive","ci_lower":None,"ci_upper":None,"null_replicates":50000}
    value = 8*n/(d/3600) if kind == "clean" else (100*n/d if kind == "burden" else n/d)
    return {"numerator": n, "denominator": d, "value": value, "ci_status": "complete",
            "ci_lower": max(0.0, value-width), "ci_upper": min(1.0, value+width) if kind == "ratio" else value+width,
            "null_replicates": 0}


def reported_analysis(*, c1_pass=True, c2_pass=True, control_zero_alerts=False):
    value = analysis_result()
    value["status"] = status("complete", "pass", "pass")
    value["decision"] = "qualified"
    value["selected_candidate"] = c.CANDIDATES[1] if c1_pass else (c.CANDIDATES[2] if c2_pass else None)
    if not c1_pass and not c2_pass:
        value["status"]["performance_status"] = "fail"
        value["decision"] = "no_promotion"
    fixed = c.config_values(c.BOOTSTRAP_HASH, c.GOLDEN_DRAWS)[3]
    by_key = {}
    for table in value["candidate_tables"]:
        candidate, layer = table["candidate_id"], table["stratum"]
        overall = layer == "overall"
        denominator = 9600 if overall else 4800
        passing = {c.CANDIDATES[0]:True,c.CANDIDATES[1]:c1_pass,c.CANDIDATES[2]:c2_pass}[candidate]
        machine = denominator*95//100 if passing else denominator//2
        sensor = 8760 if overall else (4560 if layer == "core" else 4200)
        exposure = 3230400 if overall else 1615200
        false = 20 if overall else 10
        if candidate == c.CANDIDATES[0] and control_zero_alerts:
            machine=sensor=false=0
        matched = machine+sensor
        av = []
        for target in c.FULL_TARGETS:
            stress = 825960 if target.startswith("motor-01.") else 826320
            num = 835200 if layer == "core" else (835200+stress if overall else stress)
            av.append({"full_target":target,"metric":metric(num,1728000 if overall else 864000)})
        table["metrics"] = {"machine_recall":metric(machine,denominator), "sensor_recall":metric(sensor,denominator),
                            "precision":metric(matched,matched+false), "clean_rate":metric(false,exposure,kind="clean",width=0.1),
                            "false_alert_burden":metric(false,2*denominator,kind="burden",width=0.1),
                            "availability":av, "scheduled_clean_seconds":exposure, "effective_clean_seconds":exposure,
                            "effective_clean_rate":8*false/(exposure/3600), "delay_summary":delay_summary(matched)}
        table["profile_status"] = "calibrated"
        table["qualified"] = candidate != c.CANDIDATES[0] and passing
        by_key[candidate,layer] = table
        thresholds = next(r for r in fixed["absolute_gates"] if r["stratum"] == layer)
        for name,target,m in items(table["metrics"],absolute=True):
            rule = thresholds["each_target_availability" if name=="availability" else name]
            passed = m["value"] is not None and (m["value"]<=rule[0] and m["ci_upper"]<=rule[1] if name=="clean_rate" else m["value"]>=rule[0] and m["ci_lower"]>=rule[1])
            table["gates"].append({"name":name,"comparison":"absolute","full_target":target,"point":m["value"],
                                   "lower":m["ci_lower"],"upper":m["ci_upper"],"ci_status":m["ci_status"],"null_replicates":m["null_replicates"],
                                   "status":"inconclusive" if m["ci_status"]!="complete" else ("pass" if passed else "fail")})
        if candidate != c.CANDIDATES[0]:
            control = by_key[c.CANDIDATES[0],layer]["metrics"]
            ctrl = {(name,target):m for name,target,m in items(control,absolute=False)}
            for name,target,m in items(table["metrics"],absolute=False):
                delta = m["value"]-ctrl[name,target]["value"]
                width = 0.0005 if name=="availability" else (0.005 if "recall" in name else 0.1)
                rule = fixed["paired_noninferiority"]["each_target_availability" if name=="availability" else name]
                passed = delta<=rule[0] and delta+width<=rule[1] if name in ("clean_rate","false_alert_burden") else delta>=rule[0] and delta-width>=rule[1]
                table["gates"].append({"name":name,"comparison":"paired-control","full_target":target,"point":delta,
                                       "lower":delta-width,"upper":delta+width,"ci_status":"complete","null_replicates":0,"status":"pass" if passed else "fail"})
    return value


def items(metrics, *, absolute):
    for name in (("machine_recall","sensor_recall","precision","clean_rate") if absolute else ("machine_recall","sensor_recall","clean_rate","false_alert_burden")):
        yield name,None,metrics[name]
    for row in metrics["availability"]:
        yield "availability",row["full_target"],row["metric"]


def validate_report(value):
    revisions = {value["provenance"]["producer_source"]["revision"]}
    for key in ("analysis_consumer","input_analysis","audit_consumer"):
        if key in value: revisions.add(value[key]["revision"])
    return v.validate_result_contract(value, source_snapshots={r:SOURCE_SNAPSHOTS[r] for r in revisions})


class S1AuditProbeTests(unittest.TestCase):
    def test_reported_analysis_positive_both_and_C1_only_qualified(self):
        for c2_pass in (True,False):
            with self.subTest(c2_pass=c2_pass):
                report=validate_report(reported_analysis(c2_pass=c2_pass))
                self.assertFalse(report["result_trusted"])
                self.assertEqual(report["run_status"],"not_run")
                self.assertEqual(report["performance_status"],"not_evaluated")

    def test_reported_analysis_C2_only_and_no_promotion(self):
        for c2_pass in (True,False):
            validate_report(reported_analysis(c1_pass=False,c2_pass=c2_pass))

    def test_C1_preferred_when_both_qualified(self):
        value=reported_analysis(); value["selected_candidate"]=c.CANDIDATES[2]
        with self.assertRaisesRegex(v.V03ValidationError,"C1-first"): validate_report(value)

    def test_gate_inventory_flags_paired_delta_and_profile_claims(self):
        for kind in ("missing","duplicate","flag","delta","paired-bounds","paired-nulls","not-applicable","profile","overall"):
            value=reported_analysis(); table=value["candidate_tables"][3]; gate=table["gates"][-1]
            if kind=="missing": table["gates"].pop()
            elif kind=="duplicate": table["gates"][-1]=copy.deepcopy(table["gates"][0])
            elif kind=="flag": gate["status"]="fail"
            elif kind=="delta": gate["point"]=0.5
            elif kind=="paired-bounds": gate.update(lower=1,upper=-1)
            elif kind=="paired-nulls": gate["null_replicates"]=1
            elif kind=="not-applicable": gate["status"]="not_applicable"
            elif kind=="profile": table["profile_status"]="inconclusive"
            else:
                # Keep this metric's ratio valid, but break stratum additivity.
                m=value["candidate_tables"][5]["metrics"]["availability"][0]["metric"]
                m["numerator"]-=1; m["value"]=m["numerator"]/m["denominator"]
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_required_precision_CI_inconclusive_selects_only_C2(self):
        value=reported_analysis(); table=value["candidate_tables"][3]
        table["metrics"]["precision"].update(ci_status="inconclusive",ci_lower=None,ci_upper=None,null_replicates=1)
        gate=next(g for g in table["gates"] if g["name"]=="precision")
        gate.update(ci_status="inconclusive",lower=None,upper=None,null_replicates=1,status="inconclusive")
        for t in value["candidate_tables"][3:6]: t["qualified"]=False
        value["selected_candidate"]=c.CANDIDATES[2]
        validate_report(value)

    def test_control_profile_inconclusive_forbids_both_candidates(self):
        value=reported_analysis()
        for table in value["candidate_tables"]:
            table["qualified"]=False
            if table["candidate_id"]==c.CANDIDATES[0]:
                table["profile_status"]="inconclusive"
                for gate in table["gates"]: gate["status"]="inconclusive"
            else:
                for gate in table["gates"]:
                    if gate["comparison"]=="paired-control": gate.update(ci_status="inconclusive",lower=None,upper=None,status="inconclusive")
        value.update(selected_candidate=None,decision="inconclusive")
        value["status"]["performance_status"]="inconclusive"
        validate_report(value)

    def test_zero_alert_control_precision_not_imputed_or_used_as_relative_precision(self):
        value=reported_analysis(control_zero_alerts=True)
        # Relative false-alert burden/clean rate genuinely fail here: the
        # zero-alert control is not rescued by replacing its undefined precision.
        for table in value["candidate_tables"]: table["qualified"]=False
        value.update(selected_candidate=None,decision="no_promotion")
        value["status"]["performance_status"]="fail"
        validate_report(value)
        value["candidate_tables"][0]["metrics"]["precision"]["value"]=1.0
        with self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_delay_closed_conditional_counts_ranges_and_zero_nulls(self):
        for mutation in ({"count":0},{"mean":0},{"min":0},{"max":6},{"mean":None},{"median":5},{"undetected_fill":"zero"},{"other":1}):
            value=reported_analysis(); value["candidate_tables"][3]["metrics"]["delay_summary"].update(mutation)
            with self.subTest(mutation=mutation),self.assertRaises(v.V03ValidationError): validate_report(value)
        zero=delay_summary(0); v._delay_summary(zero,0)
        zero["mean"]=0
        with self.assertRaises(v.V03ValidationError): v._delay_summary(zero,0)

    def test_source_bytes_revision_inventory_hash_length_and_no_IO(self):
        value=reported_analysis(); snapshots={r:copy.deepcopy(SOURCE_SNAPSHOTS[r]) for r in ("a"*40,"c"*40)}
        with self.assertRaisesRegex(v.V03ValidationError,"requires caller-supplied"): v.validate_result_contract(value)
        for kind in ("bytes","revision","length","hash","duplicate","missing","free-payload"):
            bad=copy.deepcopy(value); supplied=copy.deepcopy(snapshots)
            source=bad["analysis_consumer"]["sources"][0]
            if kind=="bytes": supplied["c"*40][source["path"]]+=b"tamper"
            elif kind=="revision": bad["analysis_consumer"]["revision"]="d"*40
            elif kind=="length": source["byte_count"]+=1
            elif kind=="hash": source["raw_sha256"]="0"*64
            elif kind=="duplicate": bad["analysis_consumer"]["sources"].append(copy.deepcopy(source))
            elif kind=="missing": del bad["analysis_consumer"]
            else: bad["analysis_consumer"]["inventory"]=[copy.deepcopy(bad["provenance"]["inventory"][0])]
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): v.validate_result_contract(bad,source_snapshots=supplied)
        with patch("builtins.open",side_effect=AssertionError("I/O")),patch("subprocess.run",side_effect=AssertionError("I/O")):
            report=v.validate_result_contract(value,source_snapshots=snapshots)
        self.assertIn("supplied_bytes_verified",report["source_validation"])
        self.assertFalse(report["result_trusted"])
        audit=audit_result(); validate_report(audit)
        for key in ("producer_revision","consumer_revision"):
            bad=copy.deepcopy(audit)
            if key=="producer_revision": bad["provenance"][key]="d"*40
            else: bad[key]="d"*40
            with self.subTest(key=key),self.assertRaises(v.V03ValidationError): validate_report(bad)

    def test_pending_metadata_and_partial_diagnostics_not_acceptance(self):
        value=reported_analysis()
        value["status"]=status("in_progress")
        value.update(selected_candidate=None,decision="not_evaluated")
        for table in value["candidate_tables"]:
            table.update(gates=[],qualified=False)
            for _,_,m in items(table["metrics"],absolute=True): m.update(ci_status="not_evaluated",ci_lower=None,ci_upper=None,null_replicates=0)
            table["metrics"]["false_alert_burden"].update(ci_status="not_evaluated",ci_lower=None,ci_upper=None,null_replicates=0)
        validate_report(value)
        value["status"]=status()
        with self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_full_string_patterns_in_config_registry_source_and_nullable_ID(self):
        config=c.config_values(c.BOOTSTRAP_HASH,c.GOLDEN_DRAWS)
        from banto_ai._anomaly_v03_schema import common_defs
        for key,text in (("digest","a"*64),("identifier","score-1")):
            for suffix in ("\n","\r\n"):
                with self.subTest(key=key,suffix=suffix),self.assertRaises(v.V03ValidationError): v._shape(text+suffix,common_defs()[key])
        for index,key in ((0,"producer_source"),(1,"analysis_consumer"),(2,"audit_consumer"),(3,"input_analysis")):
            value=analysis_result() if index<2 else audit_result()
            descriptor=value["provenance"][key] if index==0 else value[key]
            descriptor["revision"]+="\n"
            with self.subTest(key=key),self.assertRaises(v.V03ValidationError): v.validate_result_contract(value)
        config[3]["bootstrap"]["indices_raw_sha256"]+="\n"
        with self.assertRaises(v.V03ValidationError): v.validate_decoded_configs(dict(zip(c.CONFIG_PATHS[:4],config)))

    def test_reported_source_membership_interior_and_preonset_backlink(self):
        identity,rows=ledgers()
        extra=copy.deepcopy(rows["scores"][1]); extra.update(score_id="score-7203",sample=7203,timestamp_ms=c.START_MS+7203000,phase=3,streak=3)
        for dep in extra["dependencies"]: dep["sample"]+=1; dep["timestamp_ms"]+=1000
        rows["scores"].append(extra)
        rows["source_episodes"][0]["end_ms"]+=1000; rows["equipment_episodes"][0]["end_ms"]+=1000
        v.validate_ledger_rows(identity,**rows)
        for kind in ("interior-none","preonset","interior-other"):
            bad=copy.deepcopy(rows)
            if kind=="interior-none": bad["scores"][2]["source_episode_id"]=None
            elif kind=="preonset": bad["scores"][0]["source_episode_id"]="source-0"
            else: bad["scores"][2]["source_episode_id"]="unknown"
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**bad)

    def test_candidate_half_open_end_and_other_equipment_rejected(self):
        for kind in ("end","other-equipment"):
            identity,rows=ledgers(); event=rows["events"][0]
            if kind=="end":
                offset=(event["window_end_ms"]-rows["source_episodes"][0]["onset_ms"])//1000
                for row in rows["scores"]:
                    row["sample"]+=offset; row["timestamp_ms"]+=offset*1000; row["phase"]=row["sample"]%30
                    for dep in row["dependencies"]: dep["sample"]+=offset; dep["timestamp_ms"]+=offset*1000
                for row in rows["source_episodes"]+rows["equipment_episodes"]:
                    row["onset_ms"]+=offset*1000; row["end_ms"]+=offset*1000
            else:
                for row in rows["profiles"]+rows["scores"]+rows["source_episodes"]+rows["equipment_episodes"]:
                    row["equipment"]="conveyor-01"
                    if "full_target" in row: row["full_target"]="conveyor-01.motor_current"
                    for dep in row.get("dependencies",[]): dep["full_target"]="conveyor-01.motor_current"
            v.validate_ledger_rows(identity,**rows)
            incident=unprocessed(identity,event)
            incident.update(status="processed",candidate_count=1,candidate_episode_ids=["equipment-0"],selected_candidate_episode_id="equipment-0",
                            reason="first_candidate_no_target_onset",causal_detected=False)
            rows["incidents"]=[incident]
            with self.subTest(kind=kind),self.assertRaisesRegex(v.V03ValidationError,"equipment/window"): v.validate_ledger_rows(identity,**rows)

    def test_P2_1_ordered_splits_reverse_and_degenerate(self):
        for key,array in (("fit",[5400,1800]),("test",[7200,7200]),("warmup",[1800,0]),("calibration",[7200,5400])):
            value=evaluator_result(); value["splits"][key]=array
            with self.subTest(key=key),self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_1_ordered_bootstrap_repeat_reverse_and_typed_indices(self):
        for kind in ("repeat-index","duplicate-replicate","reverse-interval","reverse-draws","bool-index"):
            value=analysis_result(); boot=value["bootstrap"]
            if kind=="repeat-index": boot["golden_draws"][0]["indices"]=[28]*40
            elif kind=="duplicate-replicate": boot["golden_draws"]=[copy.deepcopy(boot["golden_draws"][0]) for _ in range(4)]
            elif kind=="reverse-interval": boot["interval"].reverse()
            elif kind=="reverse-draws": boot["golden_draws"].reverse()
            else: boot["golden_draws"][0]["indices"][3]=False
            with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_2_empty_gates_qualified(self):
        value=reported_analysis()
        for t in value["candidate_tables"]: t["gates"]=[]
        with self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_2_C1_only_qualified_cannot_select_C2(self):
        value=reported_analysis(c2_pass=False); value["selected_candidate"]=c.CANDIDATES[2]
        with self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_2_duplicate_availability_target_inventory(self):
        value=reported_analysis(); table=value["candidate_tables"][3]
        table["metrics"]["availability"]=[copy.deepcopy(table["metrics"]["availability"][0]) for _ in range(8)]
        with self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_2_required_CI_inconclusive_cannot_qualify(self):
        value=reported_analysis(); value["candidate_tables"][3]["metrics"]["precision"].update(ci_status="inconclusive",ci_lower=None,ci_upper=None,null_replicates=1)
        with self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_2_not_run_computed_slices(self):
        value=analysis_result()
        value["slices"]=[{"candidate_id":c.CANDIDATES[0],"stratum":"core","dimension":"class","key":"machine", "metric":metric(1,1),"planned_count":1,"actual_count":1,"delay_summary":delay_summary(1)}]
        with self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_2_invalid_denominator_CI_range_and_null_count(self):
        for mutation in ({"denominator":0,"value":9},{"ci_lower":2,"ci_upper":1},{"null_replicates":50001}):
            value=reported_analysis(); value["candidate_tables"][3]["metrics"]["precision"].update(mutation)
            with self.subTest(mutation=mutation),self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_3_delay_and_role_specific_source_descriptors_required(self):
        ss=schemas(c.config_values(c.BOOTSTRAP_HASH,c.GOLDEN_DRAWS))
        self.assertIn("delay_summary",ss[5]["$defs"])
        self.assertIn("delay_summary",ss[7]["$defs"])
        self.assertIn("analysis_consumer",ss[7]["properties"])
        self.assertIn("input_analysis",ss[8]["properties"])
        self.assertIn("audit_consumer",ss[8]["properties"])

    def test_P2_4_digest_revision_and_identifier_trailing_LF(self):
        for kind in ("digest","revision","identifier"):
            if kind=="identifier":
                identity,rows=ledgers(); rows["scores"][0]["score_id"]+="\n"; rows["source_episodes"][0]["support_score_ids"][0]+="\n"
                with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)
            else:
                value=audit_result()
                if kind=="digest": value["provenance"]["inventory"][0]["raw_sha256"]+="\n"
                else: value["consumer_revision"]+="\n"
                with self.subTest(kind=kind),self.assertRaises(v.V03ValidationError): validate_report(value)

    def test_P2_5_out_of_window_equipment_0_in_sensor_candidates(self):
        identity,rows=ledgers(); event=rows["events"][1]
        incident=unprocessed(identity,event)
        incident.update(status="processed",candidate_count=1,candidate_episode_ids=["equipment-0"],selected_candidate_episode_id="equipment-0",
                        reason="first_candidate_no_target_onset",causal_detected=False)
        rows["incidents"]=[incident]
        with self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)

    def test_P2_6_source_onset_backlink_cannot_be_none(self):
        identity,rows=ledgers(); rows["scores"][1]["source_episode_id"]=None
        with self.assertRaises(v.V03ValidationError): v.validate_ledger_rows(identity,**rows)

    def test_P3_1_bootstrap_rejection_threshold_counter_and_position_reset(self):
        sha=hashlib.sha256; limit=(2**256//40)*40; seen=[]
        forced={(0,0,0):limit-1,(0,1,0):limit,(0,1,1):2**256-1,(0,1,2):7}
        class Digest:
            def __init__(self,value): self.value=value
            def digest(self): return self.value.to_bytes(32,"big")
        def fake(raw):
            text=raw.decode()
            if text.startswith("sha256-counter-rejection-v1:"):
                parts=tuple(map(int,text.split(":")[-3:]))
                if parts[0]==0 and parts[1]<3: seen.append(parts)
                if parts in forced: return Digest(forced[parts])
            return sha(raw)
        with patch.object(c.hashlib,"sha256",new=fake): result=c.bootstrap_indices()
        self.assertEqual(len(result),2000000); self.assertEqual(list(result[:2]),[39,7])
        self.assertEqual(seen,[(0,0,0),(0,1,0),(0,1,1),(0,1,2),(0,2,0)])

    def test_P3_1_seed_small_old_and_new_collision_retry(self):
        sha=hashlib.sha256; seen=[]; first=2486912926863618161
        forced={("dev",0,0):999999,("dev",0,1):42,("dev",0,2):first,("dev",1,0):first}
        class Digest:
            def __init__(self,value): self.value=value
            def digest(self): return self.value.to_bytes(8,"big")+bytes(24)
        def fake(raw):
            text=raw.decode()
            if text.startswith("banto-ai/anomaly-v03/seeds/"):
                role,i,j=text.split("/")[-3:]; key=(role,int(i),int(j))
                if role=="dev" and int(i)<3: seen.append(key)
                if key in forced: return Digest(forced[key])
                if key==("dev",1,1): return sha(b"banto-ai/anomaly-v03/seeds/dev/1/0")
            return sha(raw)
        with patch.object(c.hashlib,"sha256",new=fake): result=c.seed_registry()
        self.assertEqual(result["entries"][0]["counters"][:3],[2,1,0])
        self.assertEqual(seen,[("dev",0,0),("dev",0,1),("dev",0,2),("dev",1,0),("dev",1,1),("dev",2,0)])


if __name__=="__main__": unittest.main()
