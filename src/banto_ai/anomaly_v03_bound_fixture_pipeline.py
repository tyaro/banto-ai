"""Project a pinned invented producer binding into owned analysis and audit.

The caller retains the bound result and reference document pins. No producer
replay, registered observations, publication, or formal permission is added.
"""
from __future__ import annotations
import copy
from pathlib import Path
import subprocess
import sys

from . import anomaly_v03_producer_slice_fixture as producer
from . import anomaly_v03_fixture_worker as analysis
from . import anomaly_v03_fixture_audit_worker as audit

v,io,evidence,budgets = analysis.v,analysis.io,analysis.evidence,analysis.budgets
ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'src/banto_ai/anomaly_v03_bound_fixture_pipeline.py'
BOUND_LIMIT = 16*1024**2
FORMAT = 'anomaly-v03-bound-fixture-pipeline-v1'


def prepare_inputs(raw, *, expected_mode, expected_pin, expected_revision, draws):
    """Project a trusted saved binding without recomputing producer aggregates."""
    v.require(type(expected_mode) is str and expected_mode == 'fixture','only fixture pipeline is open')
    evidence._pin(expected_pin);evidence._digest(expected_revision,40)
    v.require(type(raw) is bytes and 0 < len(raw) <= BOUND_LIMIT,'bound input byte limit')
    evidence._raw(raw,expected_pin,'caller bound result pin');bound = v.strict_json(raw)
    for key,want in {**producer.primary.CLOSED,'format':producer.OUTPUT_FORMAT,'mode':'fixture','invented_only':True,
        'status':'fixture_slices_bound','complete_for_aggregation':True,'scope':'supplied-invented-bytes-only'}.items():
        evidence._same(bound.get(key),want,'bound result '+key)
    main = bound['primary']
    for key,want in {**producer.primary.CLOSED,'format':'anomaly-v03-producer-input-fixture-bound-v1','mode':'fixture',
        'invented_only':True,'status':'fixture_inputs_bound','complete_for_aggregation':True,
        'planned_chunks':480,'planned_evaluations':2880,'producer_state':'complete','producer_failure':None}.items():
        evidence._same(main.get(key),want,'bound primary '+key)
    for pin in (main['manifest_pin'],main['registration_pin'],bound['slice_manifest_pin']):evidence._pin(pin)
    v.require(type(draws) is list and 1 <= len(draws) <= analysis.MAX_DRAWS,'one to eight caller fixture draws')
    fixture = {'format':analysis.wrapper.document.FORMAT,'invented_only':True,'clusters':main['clusters'],
        'diagnostics':main['diagnostics'],'draws':copy.deepcopy(draws),'engineering_ready_assumption':False}
    analysis.wrapper.document._input(fixture)
    analysis.wrapper.document.I._fixture_clusters(fixture['clusters'])
    analysis.wrapper.document.adapter._diagnostics(fixture['clusters'],fixture['diagnostics'])
    coverage = main['wrapper_coverage'];checked = analysis.wrapper._coverage(coverage,fixture)
    v.require(checked['complete'],'complete bound coverage required')
    evidence._same(checked['counts'],main['coverage'],'primary/declared coverage')
    v.require(type(bound['latest_slice_pins']) is dict and len(bound['latest_slice_pins']) == 2880,'latest slice inventory count')
    for pin in bound['latest_slice_pins'].values():evidence._pin(pin)
    source = bound['slice_source'];evidence._keys(source,'format invented_only clusters','bound slice fields')
    evidence._same(source['format'],producer.connection.INPUT_FORMAT,'bound slice format')
    evidence._same(source['invented_only'],True,'invented bound slices')
    v.require(type(source['clusters']) is list and len(source['clusters']) == 40,'forty bound slice clusters')
    for index,(row,cluster,detail) in enumerate(zip(source['clusters'],fixture['clusters'],fixture['diagnostics'])):
        evidence._keys(row,'cluster_id candidates','bound slice cluster')
        evidence._same(row['cluster_id'],cluster['cluster_id'],'ordered bound slice IDs')
        evidence._keys(row['candidates'],' '.join(producer.primary.arithmetic.CANDIDATES),'bound slice candidates')
        for candidate in producer.primary.arithmetic.CANDIDATES:
            layers = row['candidates'][candidate]
            evidence._keys(layers,' '.join(producer.primary.arithmetic.STRATA[:2]),'bound slice strata')
            for layer,cell in layers.items():
                producer.connection._raw_shape(cell,producer.S.empty_counts())
                evidence._same(cell['evaluations'],12,'bound slice layout count')
                producer.connection._primary(cell,cluster['candidates'][candidate][layer]['counts'],described=False)
                evidence._same(cell['profile_inconclusive_evaluations'],coverage['clusters'][index]['candidates'][candidate][layer].count('inconclusive'),'bound slice profile coverage')
                histogram = [0]*5
                for delay in detail['candidates'][candidate][layer]['detected_delays']:
                    v.require(type(delay) is int and 1 <= delay <= 5,'integer fixture delay');histogram[delay-1] += 1
                evidence._same(cell['delay_histogram'],histogram,'bound slice delay')
    values = {'fixture/input.json':fixture,'fixture/slices.json':source,'fixture/coverage.json':coverage,
        'fixture/operation.json':analysis.wrapper.operation_descriptor(expected_revision)}
    files = {n:v.canonical_json(x) for n,x in values.items()}
    v.require(all(len(raw) <= analysis.INPUT_LIMITS[n] for n,raw in files.items()) and
        sum(map(len,files.values())) <= analysis.TOTAL_INPUT_LIMIT,'projected worker input limits')
    binding = {**producer.primary.CLOSED,'format':'anomaly-v03-bound-fixture-projection-v1','mode':'fixture',
        'bound_result_pin':copy.deepcopy(expected_pin),'primary_manifest_pin':copy.deepcopy(main['manifest_pin']),
        'registration_pin':copy.deepcopy(main['registration_pin']),'slice_manifest_pin':copy.deepcopy(bound['slice_manifest_pin']),
        'source_revision':expected_revision,'worker_input_pins':{n:producer.primary.pin(b) for n,b in files.items()},
        'draws':copy.deepcopy(draws),'coverage':copy.deepcopy(main['coverage']),
        'failed_attempt_history':copy.deepcopy(main['failed_attempt_history']),
        'trust_boundary':'caller-pinned previously validated invented binding; raw producer derivation not repeated'}
    return {'files':files,'binding':binding}


def _record(path,raw):
    io._exclusive(path,raw)
    pin = producer.primary.pin(raw)
    evidence._raw(analysis.observed._file(path,max(len(raw),1)),pin,'pipeline write readback')
    return {'path':str(path),'pin':pin,'links':1}


def run_pipeline(raw, *, expected_mode, expected_pin, expected_revision, draws,
                 expected_document_pin, receipt_parent, receipt_name, resource_budget=None):
    """Run the existing analysis once, then the existing independent audit once.

    An externally retained reference pin is required before either worker starts.
    The pipeline never creates its own expected document or retries a worker.
    """
    v.require(type(expected_mode) is str and expected_mode == 'fixture','only fixture pipeline is open')
    evidence._pin(expected_document_pin);evidence._digest(expected_revision,40)
    v.require(0 < expected_document_pin['bytes'] <= analysis.DOCUMENT_LIMIT,'reference document limit')
    parent = io._local_parent(Path(receipt_parent));v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),'pipeline receipt name')
    target = io.regular_path(parent/receipt_name,directory=True,missing=True)
    v.require(not analysis.observed.reader._overlap(target,ROOT/'src'),'pipeline/source overlap')
    target.mkdir();budget = budgets.FixtureBudget(target,upstream=resource_budget)
    result = {**producer.primary.CLOSED,'format':FORMAT,'mode':'fixture','status':'failed','new_evaluations':0,
        'fixture_inference_performed':False,'fixture_numerical_audit_performed':False,'fixture_slice_audit_performed':False,
        'analysis_runs':0,'audit_runs':0,'bound_result_pin':copy.deepcopy(expected_pin)}
    try:
        budget.start()
        prepared = prepare_inputs(raw,expected_mode=expected_mode,expected_pin=expected_pin,expected_revision=expected_revision,draws=draws)
        budget.checkpoint()
        _,_,git = analysis.observed._git_sources(expected_revision)
        v.require(not git('status','--porcelain').strip(),'pipeline candidate must be clean')
        source = analysis.observed._file(ROOT/SOURCE,1024**2)
        evidence._raw(source,producer.primary.pin(git('show',expected_revision+':'+SOURCE)),'pipeline source/Git bytes')
        analysis.observed._save(target/'parent-source.json',{'revision':expected_revision,'path':SOURCE,'pin':producer.primary.pin(source)})
        inputs = target/'inputs';inputs.mkdir()
        records = {n:_record(inputs/Path(n).name,b) for n,b in prepared['files'].items()}
        projection_raw = io.json_bytes(prepared['binding']);_record(target/'projection.json',projection_raw)
        request = {'format':analysis.FORMAT,'mode':'fixture','role':'analysis','operation':analysis.OPERATION,
            'inputs':records,'expected_document_pin':copy.deepcopy(expected_document_pin)}
        analysis.observed._save(target/'analysis-request.json',request);budget.checkpoint()
        result['analysis_runs'] = 1
        a = analysis.calculate_with_evidence(request,expected_revision=expected_revision,receipt_parent=target,receipt_name='analysis',resource_budget=budget)
        result['analysis'] = a
        v.require(a['status'] == 'verified' and a['resource_budget_passed'],'analysis did not verify')
        result['fixture_inference_performed'] = True
        budget.checkpoint();ap = target/'analysis'
        reference = {'result_pin':a['result_pin'],'evidence_pin':a['evidence_pin'],'source_revision':expected_revision}
        audit_op = _record(inputs/'audit-operation.json',v.canonical_json(audit.operation_descriptor(expected_revision,reference,operation=audit.SLICE_OPERATION)))
        audit_inputs = {n:copy.deepcopy(records[n]) for n in ('fixture/input.json','fixture/slices.json')}
        for n,path,pin in [('fixture/document.json',ap/'payload/document.json',expected_document_pin),
            ('analysis/result.json',ap/'result.json',a['result_pin']),('analysis/evidence.json',ap/'evidence.json',a['evidence_pin'])]:
            audit_inputs[n] = {'path':str(path),'pin':copy.deepcopy(pin),'links':1}
        audit_inputs['fixture/audit-operation.json'] = audit_op
        audit_request = {'format':audit.FORMAT,'mode':'fixture','role':'audit','operation':audit.SLICE_OPERATION,
            'inputs':audit_inputs,'analysis_reference':reference}
        analysis.observed._save(target/'audit-request.json',audit_request);result['audit_runs'] = 1
        b = audit.audit_with_evidence(audit_request,expected_revision=expected_revision,receipt_parent=target,receipt_name='audit',resource_budget=budget)
        result['audit'] = b
        v.require(b['status'] == 'verified' and b['resource_budget_passed'] and b['fixture_slice_audit_performed'],'independent audit did not verify')
        result.update(fixture_numerical_audit_performed=True,fixture_slice_audit_performed=True)
        budget.checkpoint()
        # Link the exact projected inputs to both owned records, after clean exit.
        for role,role_result in (('analysis',a),('audit',b)):
            record = analysis.observed._file(target/role/'evidence.json',64*1024)
            evidence._raw(record,role_result['evidence_pin'],'pipeline role evidence pin')
            record = v.strict_json(record)
            for n in ('fixture/input.json','fixture/slices.json'):
                evidence._same(record['inputs'][n],prepared['binding']['worker_input_pins'][n],'projection/role input binding')
        evidence._raw(analysis.observed._file(target/'projection.json',64*1024),producer.primary.pin(projection_raw),'retained projection changed')
        evidence._raw(analysis.observed._file(ROOT/SOURCE,1024**2),producer.primary.pin(source),'pipeline source changed')
        result.update(status='verified',fixture_inference_performed=True,fixture_numerical_audit_performed=True,
            fixture_slice_audit_performed=True,projection_pin=producer.primary.pin(projection_raw),
            expected_document_pin=copy.deepcopy(expected_document_pin),worker_input_pins=prepared['binding']['worker_input_pins'],
            inherited_failed_attempts=len(prepared['binding']['failed_attempt_history']))
    except analysis.supervisor.UnreapedWorker as error:
        try:analysis.observed._save(target/'unreaped.json',error.report)
        finally:raise error
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError) as error:
        result.update(error_type=type(error).__name__,detail=str(error))
    finally:budgets.finish(budget,target,result,owner_error=sys.exception())
    budgets.save_result(target,result)
    return {**result,'check_directory':str(target),'result_pin':producer.primary.pin(io.json_bytes(result))}
