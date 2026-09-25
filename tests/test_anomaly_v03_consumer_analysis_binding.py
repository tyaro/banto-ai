"""Invented historical provenance; no dataset, score or aggregate computation."""
import copy
from contextlib import ExitStack
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from banto_ai import anomaly_v03 as v
from banto_ai import anomaly_v03_consumer_checkpoints as adapter
from banto_ai import anomaly_v03_consumer_analysis_binding as binding
from tests import test_anomaly_v03_consumer_checkpoints as fixtures


def pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def raw(value):return v.canonical_json(value)+b'\n'


class AnalysisBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ConsumerCheckpointTests.setUpClass()
        f,entries=copy.deepcopy(fixtures.ConsumerCheckpointTests.baseline)
        adapted=adapter.adapt_completed_journal(f.plan,f.records,entries,expected_mode=adapter.MODE,
            expected_plan_sha256=f.plan_hash,expected_record_count=len(f.records),expected_head_sha256=f.head,
            expected_manifests_sha256=v.canonical_sha256(entries))
        evidence={'status':'completed','full_120_chunks_completed':True,'cumulative_verified_chunks':120,
            'next_unverified_chunk':None,'formal_permission':False,'journal_state':f.reduce(),'files':{}}
        closed={'bytes':10,'sha256':fixtures.digest('closed')};reports=[];adapted_digest=v.canonical_sha256(adapted)
        for chunk in adapted['chunks']:
            i=chunk['chunk_index'];attempt=chunk['attempts'][-1];n=attempt['attempt'];seq=attempt['record_sequences'][-1]
            stem=f'attempts/chunks/{i:03d}/attempt-{n:04d}/'
            names=['control/000010/closed.json',f'metadata/journal/{seq:06d}.json',stem+f'descriptors/{seq:06d}.json']
            names += [stem+x for x in ('result/.complete','result/marker-pending.json','result/payload/manifest.json',
                                       'producer-control/supervision.json','audit/supervision.json')]
            files={name:{'bytes':10,'sha256':fixtures.digest(name)} for name in names}
            files[names[0]]=closed
            files[names[1]]['sha256']=attempt['terminal_record_sha256']
            files[stem+'result/.complete']['sha256']=attempt['evidence']['marker_sha256']
            files[stem+'result/marker-pending.json']['sha256']=attempt['evidence']['marker_sha256']
            files[stem+'producer-control/supervision.json']['sha256']=attempt['evidence']['supervision_sha256']
            evidence['files'].update({'run/'+name:copy.deepcopy(p) for name,p in files.items()})
            for row in attempt['evaluations']:
                ident=row['identity']
                for key,filename in binding.INPUT_NAMES.items():
                    evidence['files']['run/'+stem+'result/payload/datasets/'+ident['dataset_id']+'/'+filename]={'bytes':1,'sha256':row['input_hashes'][key]}
                evidence['files']['run/'+stem+'result/payload/evaluations/'+ident['evaluation_id']+'.json']={'bytes':1,'sha256':row['evaluation_sha256']}
            reports.append({'format':'anomaly-v03-consumer-publication-metadata-check-v1','mode':adapter.MODE,
                'status':'publication_metadata_verified','chunk_index':i,'attempt':n,'evaluations':6,
                'adapter_sha256':adapted_digest,'closed_sha256':closed['sha256'],'files_read':files,
                **dict.fromkeys(('publication_metadata_verified','manifest_bytes_verified','worker_exit_records_verified',
                                 'controller_closure_record_verified'),True),
                **dict.fromkeys(('controller_process_exit_verified','full_payload_bytes_verified','audit_report_bytes_verified',
                    'publication_verified','source_runtime_accepted','result_trusted','execution_authorized','analysis_authorized',
                    'formal_permission','promotion_allowed','independent_s6_complete'),False),
                'performance_status':'not_evaluated','selected_candidate':None})
        quiet={**dict.fromkeys(binding.FALSE_FIELDS,False),'performance_status':'not_evaluated','selected_candidate':None,'evaluations':720}
        counts={**quiet,'format':'anomaly-v03-dev-smoke-seed-counts-v1','status':'authenticated_dev_smoke_counts','attempts_used':[
            {'chunk_index':c['chunk_index'],'attempt':c['selected_attempt'],'prior_attempts_not_credited':len(c['attempts'])-1}
            for c in adapted['chunks']], 'zero_denominator_input_metrics':46,'by_seed':[],'by_role':[],'seed_clusters':[]}
        identities=v.evaluation_inventory('dev')+v.evaluation_inventory('smoke')
        for name,seed in (('by_seed',True),('by_role',False)):
            seen=set()
            for ident in identities:
                for layer in (ident['stratum'],'overall'):
                    row={k:ident[k] for k in ('role','candidate_id')};row['stratum']=layer
                    if seed:row['seed']=ident['seed']
                    key=binding._table_key(row,seed)
                    if key in seen:continue
                    seen.add(key);counts[name].append({**row,'counts':{'precision':[0,0]},'ci_lower':None,'ci_upper':None,'ci_status':'not_evaluated'})
        for registered in v.seed_registry()['entries'][:2]:
            for i,seed in enumerate(registered['seeds']):
                ids=[x for x in identities if (x['role'],x['seed'])==(registered['role'],seed)]
                candidates={x['candidate_id']:{layer:{'counts':{'precision':[0,0]},'profile_status':'inconclusive'}
                            for layer in ('core','quality-stress')} for x in ids}
                counts['seed_clusters'].append({'role':registered['role'],'seed':seed,'registered_index':i,'layouts':list(range(12)),
                    'evaluation_ids':[x['evaluation_id'] for x in ids],'candidates':candidates})
        analysis={**copy.deepcopy(counts),'format':'anomaly-v03-descriptive-analysis-inputs-v1','status':'authenticated_dev_smoke_analysis_inputs'}
        del analysis['attempts_used']
        cls.base=(adapted,evidence,reports,counts,analysis,closed)

    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix='banto-analysis-binding-');self.addCleanup(t.cleanup);self.root=Path(t.name)
        self.adapted,self.evidence,self.reports,self.counts,self.analysis,self.closed=copy.deepcopy(self.base)
        self.roots={k:self.root/k/'savepoint-evidence.json' for k in binding.ROOTS}
        self.persist()

    def save(self,path,value):
        data=raw(value);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return pin(data)

    def persist(self):
        evidence_pin=self.save(self.root/'completed/evidence.json',self.evidence)
        completed_pin=self.save(self.roots['completed'],{'artifacts':{'evidence.json':evidence_pin}})
        self.counts['authenticated_files']={str(self.roots['completed']):completed_pin,str(self.root/'completed/evidence.json'):evidence_pin}
        counts_pin=self.save(self.root/'seeds/verified/authenticated-counts.json',self.counts)
        seeds_pin=self.save(self.roots['seeds'],{'artifacts':{'verified/authenticated-counts.json':counts_pin}})
        self.analysis['authenticated_files']={str(self.roots['seeds']):seeds_pin,
            str(self.root/'seeds/verified/authenticated-counts.json'):counts_pin}
        analysis_pin=self.save(self.root/'analysis/analysis-inputs.json',self.analysis)
        self.analysis_anchor=self.save(self.roots['analysis'],{'status':'authenticated_analysis_inputs_completed',
            'evaluations':720,'formal_permission':False,'formal_ready':False,'boundaries':{'closed':self.closed},
            'analysis_inputs_pin':analysis_pin,'artifacts':{'analysis-inputs.json':analysis_pin}})
        adapted_pin=self.save(self.root/'adapter/adapted-metadata.json',self.adapted)
        adapter_pin=self.save(self.roots['adapter'],{'status':'consumer_checkpoint_metadata_adapter_completed',
            'formal_permission':False,'artifacts':{'adapted-metadata.json':adapted_pin}})
        adapted_digest=v.canonical_sha256(self.adapted)
        for report in self.reports:report['adapter_sha256']=adapted_digest
        reports_pin=self.save(self.root/'publication/all-publication-checks.json',self.reports)
        self.publication_anchor=self.save(self.roots['publication'],{'status':'consumer_publication_metadata_reader_completed',
            'engineering_chunks':120,'engineering_evaluations':720,'publication_metadata_verified':True,
            'worker_exit_records_verified':True,'formal_permission':False,'analysis_authorized':False,
            'boundaries':{'closed':self.closed},'prior_savepoint':adapter_pin,'artifacts':{'all-publication-checks.json':reports_pin}})

    def call(self,**kwargs):
        args={'expected_mode':adapter.MODE,'expected_publication_pin':self.publication_anchor,'expected_analysis_pin':self.analysis_anchor}|kwargs
        return binding.authenticate_analysis_binding(self.roots,**args)

    def test_complete_binding_reads_only_ten_artifacts_and_preserves_limits(self):
        allowed=set(self.roots.values())|{self.root/n for n in ('completed/evidence.json','seeds/verified/authenticated-counts.json',
            'analysis/analysis-inputs.json','adapter/adapted-metadata.json','publication/all-publication-checks.json')}
        original=Path.open;opened=[]
        def guard(path,*args,**kwargs):
            self.assertIn(path,allowed);self.assertEqual(args,('rb',));opened.append(path);return original(path,*args,**kwargs)
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path,'open',guard))
            for target in ('subprocess.Popen','banto_ai.anomaly_v03_analysis_inputs.join_inputs',
                           'banto_ai.anomaly_v03_seed_aggregate.aggregate_evaluations','banto_ai.anomaly_v03_materializer.materialize_pair'):
                stack.enter_context(patch(target,side_effect=AssertionError('recomputation forbidden')))
            report=self.call()
        self.assertEqual(len(opened),10);self.assertEqual(len(set(opened)),10)
        self.assertEqual([report[k] for k in ('chunks','evaluations','publication_reference_checks','input_pin_checks','evaluation_pin_checks')],
                         [120,720,960,4320,720])
        self.assertEqual(report['failed_attempts_retained'],1);self.assertEqual(report['undefined_input_metrics_retained'],46)
        self.assertEqual(report['attempts_used'][-1],{'chunk_index':119,'attempt':2,'prior_attempts_not_credited':1})
        for key in ('result_trusted','formal_permission','analysis_authorized','source_runtime_accepted','full_payload_bytes_verified'):
            self.assertIs(report[key],False)
        self.assertTrue(report['historical_aggregate_authentication_reused'])
        self.assertEqual(report['source_payload_bytes_read'],0)

    def test_formal_fails_before_paths(self):
        with patch.object(binding.paths,'regular_path',side_effect=AssertionError('path touched')):
            for mode in ('formal','fixture',None):
                with self.assertRaises(ValueError):self.call(expected_mode=mode)

    def test_wrong_external_anchor_rejected(self):
        for key in ('expected_publication_pin','expected_analysis_pin'):
            with self.subTest(key=key),self.assertRaises(ValueError):self.call(**{key:{'bytes':1,'sha256':'0'*64}})

    def test_changed_analysis_bytes_rejected_without_recalculating(self):
        path=self.root/'analysis/analysis-inputs.json';path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError):self.call()

    def test_different_closure_or_journal_rejected(self):
        self.evidence['journal_state']['head_sha256']='f'*64;self.persist()
        with self.assertRaisesRegex(ValueError,'journal binding'):self.call()

    def test_missing_duplicate_or_reordered_publication_reports_rejected(self):
        original=copy.deepcopy(self.reports)
        for mutate in (lambda r:r.pop(),lambda r:r.__setitem__(1,copy.deepcopy(r[0])),lambda r:r.reverse()):
            self.reports=copy.deepcopy(original);mutate(self.reports);self.persist()
            with self.assertRaises(ValueError):self.call()

    def test_wrong_publication_pin_cannot_bind_to_old_audit(self):
        name=next(n for n in self.reports[0]['files_read'] if n.endswith('/manifest.json'))
        self.reports[0]['files_read'][name]['sha256']='f'*64;self.persist()
        with self.assertRaisesRegex(ValueError,'file pin differs'):self.call()

    def test_aggregation_cannot_revert_to_failed_first_attempt(self):
        self.counts['attempts_used'][-1]['attempt']=1;self.persist()
        with self.assertRaisesRegex(ValueError,'different attempts'):self.call()

    def test_failed_attempt_history_cannot_be_dropped(self):
        self.adapted['chunks'][-1]['attempts'].pop(0);self.persist()
        with self.assertRaisesRegex(ValueError,'history omitted'):self.call()

    def test_input_and_evaluation_pins_must_match_old_audit(self):
        row=self.adapted['chunks'][0]['attempts'][-1]['evaluations'][0]
        old=copy.deepcopy(row)
        row['input_hashes']['targets']='f'*64;self.persist()
        with self.assertRaisesRegex(ValueError,'input pin differs'):self.call()
        row.clear();row.update(old);row['evaluation_sha256']='f'*64;self.persist()
        with self.assertRaisesRegex(ValueError,'evaluation pin differs'):self.call()

    def test_aggregate_values_and_nulls_cannot_change_at_join(self):
        for field,value in (('counts',{'precision':[1,2]}),('ci_lower',0.0)):
            old=copy.deepcopy(self.analysis['by_seed'][0]);self.analysis['by_seed'][0][field]=value;self.persist()
            with self.assertRaisesRegex(ValueError,'table value changed'):self.call()
            self.analysis['by_seed'][0]=old

    def test_seed_inventory_and_cluster_identity_required(self):
        self.analysis['by_seed'][1]=copy.deepcopy(self.analysis['by_seed'][0]);self.persist()
        with self.assertRaises(ValueError):self.call()
        self.analysis['by_seed']=copy.deepcopy(self.counts['by_seed'])
        self.counts['seed_clusters'][0]['evaluation_ids'].reverse();self.persist()
        with self.assertRaisesRegex(ValueError,'cluster registration'):self.call()

    def test_undefined_count_and_restricted_status_retained(self):
        self.analysis['zero_denominator_input_metrics']=0;self.persist()
        with self.assertRaisesRegex(ValueError,'undefined metric'):self.call()
        self.analysis['zero_denominator_input_metrics']=46;self.analysis['formal_permission']=True;self.persist()
        with self.assertRaisesRegex(ValueError,'scope'):self.call()

    def test_report_cannot_upgrade_metadata_to_payload_or_trust(self):
        self.reports[0]['full_payload_bytes_verified']=True;self.persist()
        with self.assertRaisesRegex(ValueError,'report binding'):self.call()


if __name__=='__main__':unittest.main()
