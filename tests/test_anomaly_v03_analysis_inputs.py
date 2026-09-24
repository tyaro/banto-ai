"""Compact invented summary fixtures; no observations, scoring or bootstrap."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from banto_ai import anomaly_v03_analysis_inputs as join


def pin(path):
    raw=path.read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def fixture():
    s=join.slices;a=join.arithmetic
    counts={**join.QUIET,'status':'authenticated_dev_smoke_counts','evaluations':720,'by_seed':[],
            'by_role':[],'seed_clusters':[],'zero_denominator_input_metrics':720}
    diagnostics={**join.QUIET,'status':'complete_dev_smoke_descriptive_slices','evaluations':720,'by_seed':[],'by_role':[]}
    identities=join.registry.evaluation_inventory('dev')+join.registry.evaluation_inventory('smoke')
    def table(identity,selected):
        n=len(selected);raw=s.empty_counts();raw['evaluations']=n
        for dim,cells in raw['incident_slices'].items():
            if dim=='class':
                for c in cells.values():c['planned']=10*n
            else:next(iter(cells.values()))['planned']=20*n
        for dim,cells in raw['score_slices'].items():
            if dim=='event-offset':
                for cell in cells.values():cell.update(planned=40*n,observed=30*n,available=30*n,unscored_target=10*n)
            elif dim=='full-target':
                for cell in cells.values():cell.update(planned=1800*n,observed=1800*n,available=1800*n)
            elif dim=='context':
                for k,seconds in {'raw-event':235,'grace':0,'clean':3365}.items():
                    cells[k].update(planned=4*seconds*n,observed=4*seconds*n,available=4*seconds*n)
            else:next(iter(cells.values())).update(planned=14400*n,observed=14400*n,available=14400*n)
        raw['equipment_context']['clean']['planned_seconds']=3365*n
        raw['equipment_context']['raw-event']['planned_seconds']=235*n
        metric={k:[0,d*n] for k,d in {'machine_recall':10,'sensor_recall':10,'precision':0,'clean_rate':3365,'false_alert_burden':20}.items()}
        metric.update({k:[1800*n,1800*n] for k in a.AVAILABILITY})
        old={**identity,'evaluations':n,'counts':metric,'points':{k:a.ratio(*v,k) for k,v in metric.items()},
             'effective_clean_seconds':3300*n,'scheduled_clean_seconds':3365*n,'profile_status':'success',
             'profile_diagnostics':[],'undefined_input_points':[{'evaluation_id':i['evaluation_id'],'metrics':['precision']} for i in selected],
             'ci_status':'not_evaluated','ci_lower':None,'ci_upper':None}
        return old,{**identity,**s.describe(raw)}
    for entry in join.registry.seed_registry()['entries'][:2]:
        role=entry['role']
        for idx,seed in enumerate(entry['seeds']):
            selected=[i for i in identities if i['role']==role and i['seed']==seed]
            cluster={'role':role,'seed':seed,'registered_index':idx,'layouts':list(range(12)),
                     'evaluation_ids':[i['evaluation_id'] for i in selected],'candidates':{}}
            for candidate in a.CANDIDATES:
                cluster['candidates'][candidate]={}
                for layer in a.STRATA:
                    old,new=table({'role':role,'seed':seed,'candidate_id':candidate,'stratum':layer},
                        [i for i in selected if i['candidate_id']==candidate and (layer=='overall' or i['stratum']==layer)])
                    counts['by_seed'].append(old);diagnostics['by_seed'].append(new)
                    if layer!='overall':cluster['candidates'][candidate][layer]={'counts':copy.deepcopy(old['counts']),'profile_status':'calibrated'}
            counts['seed_clusters'].append(cluster)
        for candidate in a.CANDIDATES:
            for layer in a.STRATA:
                old,new=table({'role':role,'candidate_id':candidate,'stratum':layer},
                    [i for i in identities if i['role']==role and i['candidate_id']==candidate and (layer=='overall' or i['stratum']==layer)])
                counts['by_role'].append(old);diagnostics['by_role'].append(new)
    return counts,diagnostics


class AnalysisInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.base=fixture()

    def test_complete_zero_alert_nulls_and_no_mutation(self):
        counts,diagnostics=copy.deepcopy(self.base);before=copy.deepcopy((counts,diagnostics))
        result=join.join_inputs(counts,diagnostics)
        self.assertEqual((counts,diagnostics),before)
        self.assertEqual((len(result['by_seed']),len(result['by_role']),len(result['seed_clusters'])),(90,18,10))
        self.assertEqual(result['zero_denominator_input_metrics'],720)
        self.assertIsNone(result['by_role'][0]['delay_summary']['median'])
        self.assertIsNone(result['by_role'][0]['points']['precision'])
        self.assertEqual(result['seed_clusters'][0]['candidates'][join.arithmetic.CANDIDATES[0]]['core']['effective_clean_seconds'],39600)
        self.assertFalse(result['bootstrap_performed']);self.assertFalse(result['formal_document_emitted'])

    def test_table_order_may_differ_but_registration_cannot(self):
        counts,diagnostics=copy.deepcopy(self.base);diagnostics['by_seed'].reverse()
        self.assertEqual(join.join_inputs(counts,diagnostics)['evaluations'],720)
        counts['seed_clusters'].reverse()
        with self.assertRaisesRegex(ValueError,'registration'):join.join_inputs(counts,diagnostics)

    def test_missing_duplicate_wrong_role_and_scope_rejected(self):
        for mutation in ('missing','duplicate','holdout','formal','ci'):
            counts,diagnostics=copy.deepcopy(self.base)
            if mutation=='missing':diagnostics['by_seed'].pop()
            elif mutation=='duplicate':diagnostics['by_seed'][1]=diagnostics['by_seed'][0]
            elif mutation=='holdout':diagnostics['by_role'][0]['role']='holdout'
            elif mutation=='formal':counts['formal_permission']=True
            else:counts['by_seed'][0]['ci_lower']=0
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):join.join_inputs(counts,diagnostics)

    def test_bad_counts_histograms_omissions_points_and_profile_rejected(self):
        for mutation in ('counts','histogram','fraction','offset','profile','bool'):
            counts,diagnostics=copy.deepcopy(self.base);row=diagnostics['by_seed'][0]
            if mutation=='counts':counts['by_seed'][0]['counts']['machine_recall'][0]=1
            elif mutation=='histogram':row['delay_histogram'][0]=1
            elif mutation=='fraction':row['score_slices'][0]['availability']=.99
            elif mutation=='offset':next(c for c in row['score_slices'] if c['dimension']=='event-offset')['unscored_target']=0
            elif mutation=='profile':counts['by_seed'][0]['profile_status']='inconclusive'
            else:row['score_slices'][0]['available']=True
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):join.join_inputs(counts,diagnostics)

    def test_exposure_and_diagnostic_additivity_rejected(self):
        for mutation in ('seed_overall','role_total','duplicate_diagnostic','undefined_total','cluster_counts'):
            counts,diagnostics=copy.deepcopy(self.base)
            if mutation=='seed_overall':counts['by_seed'][2]['effective_clean_seconds']-=1
            elif mutation=='role_total':counts['by_role'][0]['effective_clean_seconds']-=1
            elif mutation=='duplicate_diagnostic':counts['by_seed'][0]['undefined_input_points'][1]=counts['by_seed'][0]['undefined_input_points'][0]
            elif mutation=='undefined_total':counts['zero_denominator_input_metrics']-=1
            else:next(iter(counts['seed_clusters'][0]['candidates'].values()))['core']['counts']['clean_rate'][0]=1
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):join.join_inputs(counts,diagnostics)

    def test_formal_readiness_covers_every_required_field(self):
        root=Path(__file__).resolve().parents[1]
        schema=json.loads((root/join.SCHEMA).read_text())
        r=join.formal_readiness(schema)
        self.assertEqual([f['field'] for f in r['required_fields']],schema['required'])
        self.assertEqual(r['population']['required_holdout_seeds'],40)
        self.assertEqual(r['population']['required_bootstrap_replicates'],50000)
        self.assertFalse(r['formal_ready']);self.assertFalse(r['population']['holdout_data_read'])

    def test_authenticated_entrypoint_reads_only_compact_inputs(self):
        project=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);seed=root/'seeds';adapter=root/'adapter';slice_root=root/'slices'
            for d in (seed/'verified',adapter,slice_root):d.mkdir(parents=True)
            def write(path,value):path.write_text(json.dumps(value),encoding='utf-8');return pin(path)
            counts,diagnostic=self.base
            cp=write(seed/'verified/authenticated-counts.json',counts);dp=write(slice_root/'slices.json',diagnostic)
            source_names=('src/banto_ai/anomaly_v03_slices.py','src/banto_ai/anomaly_v03.py','src/banto_ai/anomaly_v03_inference_audit.py')
            code={name:pin(project/name) for name in source_names}
            sp=write(seed/'savepoint.json',{'status':'authenticated_seed_aggregation_completed','counts_pin':cp,'code_pins':code})
            ap=write(adapter/'savepoint.json',{'prior_seed_manifest':sp,'code_pins':{join.SCHEMA:pin(project/join.SCHEMA)}})
            manifest={**join.QUIET,'status':'saved_dev_smoke_slices_completed','evaluations':720,'chunks':120,
                      'prior_seed_manifest':sp,'prior_adapter_manifest':ap,'prior_counts':cp,'slices_pin':dp,'artifacts':{'slices.json':dp},'code_pins':code}
            mp=write(slice_root/'savepoint.json',manifest)
            roots={'slices':slice_root/'savepoint.json','seeds':seed/'savepoint.json','adapter':adapter/'savepoint.json'}
            with mock.patch.object(join,'read_pinned',wraps=join.read_pinned) as reader:
                result=join.authenticate_analysis_inputs(roots,mp['sha256'],project/join.SCHEMA)
            self.assertEqual(len(result['authenticated_files']),6)
            self.assertEqual(result['source_payload_bytes_read'],0)
            self.assertEqual(reader.call_count,9)
            self.assertFalse(any('evaluations' in str(c.args[0]) for c in reader.call_args_list))
            with self.assertRaises(ValueError):join.authenticate_analysis_inputs(roots,'0'*64,project/join.SCHEMA)
            (slice_root/'slices.json').write_text('{}')
            with self.assertRaises(ValueError):join.authenticate_analysis_inputs(roots,mp['sha256'],project/join.SCHEMA)


if __name__=='__main__':unittest.main()
