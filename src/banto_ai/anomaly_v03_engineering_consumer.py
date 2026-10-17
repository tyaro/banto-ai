"""Publish a saved descriptive report bound to an explicit engineering input.

The two retained savepoint pins are the trust anchors. Historical numeric and
publication checks are reused, not replayed. No raw campaign payload is opened.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from . import anomaly_v03 as v
from . import _anomaly_v03_io as io
from . import anomaly_v03_observation_audit as pinned
from .anomaly_v03_consumer_analysis_binding import _fields
from .anomaly_v03_consumer_input import _same

MODE = 'engineering-dev-smoke'
MIB = 1024**2
REPORT_LIMITS = {'report.json':4*MIB, 'report.md':MIB, 'report.html':2*MIB}
QUIET = {**dict.fromkeys(('bootstrap_performed','formal_permission','promotion_allowed',
    'independent_s6_complete','formal_document_emitted','formal_schema_validated'),False),
    'performance_status':'not_evaluated','selected_candidate':None,'decision':'not_evaluated'}
BOUNDARY = dict.fromkeys(('full_payload_bytes_verified','controller_process_exit_verified',
    'source_runtime_accepted','result_trusted','execution_authorized','analysis_authorized'),False)


def _pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def prepare_engineering_result(binding_savepoint, report_savepoint, analysis_input, *,
                               expected_mode, expected_binding_pin, expected_report_pin):
    """Authenticate seven bounded files and prepare four publication payloads.

    Only explicit paths and fixed sibling filenames are read. The saved report
    JSON is normalized for LocalPublication; all values and text are preserved
    (a missing final LF is added). The analysis file is not copied.
    """
    v.require(type(expected_mode) is str and expected_mode==MODE,'formal/unknown consumer mode is closed')
    roots=[io.regular_path(Path(p)) for p in (binding_savepoint,report_savepoint,analysis_input)]
    bound_path, report_path, analysis_path = roots
    v.require(len(set(roots))==3,'consumer inputs must be distinct')
    used={}

    def read(path,pin,maximum=MIB):
        v.require(str(path) not in used,'duplicate consumer artifact')
        raw=pinned.read_pinned(path,pin,maximum)
        used[str(path)]=dict(pin)
        return raw

    bound_save=v.strict_json(read(bound_path,expected_binding_pin))
    report_save=v.strict_json(read(report_path,expected_report_pin))
    _fields(bound_save,{'format':'anomaly-v03-consumer-analysis-binding-savepoint-v1',
        'status':'consumer_analysis_provenance_binding_completed','mode':MODE,
        'engineering_chunks':120,'engineering_evaluations':720,'formal_permission':False},'binding savepoint scope')
    _fields(report_save,{**QUIET,'format':'anomaly-v03-descriptive-report-savepoint-v1',
        'status':'descriptive_reports_completed','evaluations':720,'cohorts':2,'candidate_tables':18,
        'primary_metrics_verified':234,'diagnostic_rows_verified':5670},'descriptive savepoint scope')
    bound=v.strict_json(read(bound_path.parent/'analysis-binding.json',bound_save['artifacts']['analysis-binding.json']))
    _fields(bound,{**BOUNDARY,**{k:QUIET[k] for k in ('bootstrap_performed','formal_permission',
        'promotion_allowed','independent_s6_complete','performance_status','selected_candidate')},
        'format':'anomaly-v03-consumer-analysis-binding-v1','status':'historical_analysis_inputs_bound',
        'mode':MODE,'chunks':120,'evaluations':720,'analysis_input_bytes_verified':True,
        'publication_metadata_binding_verified':True,'historical_aggregate_authentication_reused':True,
        'historical_diagnostic_join_reused':True,'source_payload_bytes_read':0,'new_evaluations':0,
        'score_recalculations':0,'aggregate_recalculations':0},'binding receipt scope')
    for save in (bound_save,report_save):
        _same(save['boundaries']['closed'],bound['closed_pin'],'different campaign closure')
    reference=bound['analysis_input_reference']
    # Compare saved path spelling without resolving or accessing that path.
    v.require(Path(reference['path'])==analysis_path,'explicit analysis input differs from binding')
    analysis_pin={k:reference[k] for k in ('bytes','sha256')}
    _same(bound['authenticated_files'][str(analysis_path)],analysis_pin,'bound input pin differs')
    _same(report_save['prior_input_manifest'],bound['external_anchors']['analysis'],'different historical analysis anchor')
    read(analysis_path,analysis_pin,8*MIB)  # Authenticate bytes, no parse or math.
    files={name:read(report_path.parent/name,report_save['artifacts'][name],limit)
           for name,limit in REPORT_LIMITS.items()}
    _same({n:used[str(report_path.parent/n)] for n in REPORT_LIMITS},report_save['report_files'],'report file pin binding')
    _same(report_save['report_pin'],report_save['report_files']['report.json'],'report JSON pin binding')
    report=v.strict_json(files['report.json'])
    _fields(report,{**QUIET,'format':'anomaly-v03-dev-smoke-descriptive-report-v1',
        'scope':'saved-dev-smoke-descriptive-only','bootstrap_replicates':0},'descriptive report boundary')
    auth=report['authentication'];anchor=auth['trust_anchor']
    expected_analysis_save=analysis_path.parent/'savepoint-evidence.json'
    v.require(Path(anchor['path'])==expected_analysis_save,'historical analysis savepoint path')
    _same({k:anchor[k] for k in ('bytes','sha256')},bound['external_anchors']['analysis'],'report analysis anchor')
    _same(auth['files'][str(expected_analysis_save)],bound['external_anchors']['analysis'],'report savepoint pin')
    _same(auth['files'][str(analysis_path)],analysis_pin,'report input differs from selected analysis')
    _same(auth['source_payload_bytes_read'],0,'report raw payload boundary')
    _same([[c['role'],c['seed_count'],c['evaluations'],len(c['candidate_tables'])] for c in report['cohorts']],
          [['dev',8,576,9],['smoke',2,144,9]],'descriptive cohort inventory')
    # Reuse historical cell validation; never call the mapper/aggregate routines.
    files['report.json']=io.json_bytes(report)
    for name in ('report.md','report.html'):
        files[name].decode('utf-8',errors='strict')
        v.require(b'\r' not in files[name],'report text requires LF line endings')
        if not files[name].endswith(b'\n'):files[name]+=b'\n'
    receipt={**QUIET,**BOUNDARY,'format':'anomaly-v03-engineering-consumer-v1',
        'status':'saved_descriptive_result_selected','mode':MODE,'chunks':120,'evaluations':720,
        'external_anchors':{'binding':dict(expected_binding_pin),'report':dict(expected_report_pin)},
        'authenticated_files':used,'analysis_input_reference':dict(reference),'closed_pin':bound['closed_pin'],
        'attempts_used':bound['attempts_used'],'failed_attempts_retained':bound['failed_attempts_retained'],
        'undefined_input_metrics_retained':bound['undefined_input_metrics_retained'],
        'cohorts':2,'candidate_tables':18,'primary_metrics':234,'diagnostic_rows':5670,
        'analysis_input_bytes_verified':True,'saved_report_bytes_verified':True,
        'historical_publication_binding_reused':True,'historical_aggregate_authentication_reused':True,
        'historical_diagnostic_join_reused':True,'historical_report_cell_validation_reused':True,
        'source_payload_bytes_read':0,'new_evaluations':0,'score_recalculations':0,'aggregate_recalculations':0,
        'report_value_recalculations':0,'report_files':{n:_pin(raw) for n,raw in files.items()},
        'report_json_encoding':'canonical UTF-8/LF; decoded values preserved',
        'report_text_encoding':'original UTF-8/LF bytes; missing final LF appended',
        'limitations':['historical numerical and publication validation reused; current checks authenticate saved bytes',
            'single writer followed by reader; no native acceptance, runtime freeze, formal gate or holdout']}
    files['consumer-receipt.json']=io.json_bytes(receipt)
    return files,receipt


def run_engineering_consumer(binding_savepoint, report_savepoint, analysis_input, *,
                             expected_mode, expected_binding_pin, expected_report_pin,
                             output_parent, output_name):
    """Publish only fully authenticated input, without overwriting any attempt."""
    files,receipt=prepare_engineering_result(binding_savepoint,report_savepoint,analysis_input,
        expected_mode=expected_mode,expected_binding_pin=expected_binding_pin,expected_report_pin=expected_report_pin)

    def verify(saved):
        _same(sorted(saved),sorted(files),'consumer output inventory')
        for name,raw in files.items():
            v.require(saved[name]==raw,'consumer output bytes differ: '+name)

    published=io.publish_local_result(Path(output_parent),output_name,files,verify_semantics=verify)
    # Read after the writer closes. Retain the returned marker pin externally.
    checked=io.verify_local_publication(Path(published['output_path']),
        expected_marker_sha256=published['marker_raw_sha256'],verify_semantics=verify)
    return {**published,**checked,'status':'engineering_descriptive_result_published',
        'consumer_receipt_pin':_pin(files['consumer-receipt.json']),
        'authenticated_artifacts':len(receipt['authenticated_files']),
        'authenticated_bytes':sum(p['bytes'] for p in receipt['authenticated_files'].values()),
        'formal_permission':False,'performance_status':'not_evaluated'}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Publish authenticated saved dev/smoke descriptive results only.')
    parser.add_argument('--mode',required=True,choices=(MODE,))
    for name in ('binding-savepoint','report-savepoint','analysis-input','output-parent','output-name'):
        parser.add_argument('--'+name,required=True)
    for name in ('binding','report'):
        parser.add_argument('--'+name+'-bytes',required=True,type=int)
        parser.add_argument('--'+name+'-sha256',required=True)
    args=parser.parse_args(argv)
    try:
        result=run_engineering_consumer(args.binding_savepoint,args.report_savepoint,args.analysis_input,
            expected_mode=args.mode,expected_binding_pin={'bytes':args.binding_bytes,'sha256':args.binding_sha256},
            expected_report_pin={'bytes':args.report_bytes,'sha256':args.report_sha256},
            output_parent=args.output_parent,output_name=args.output_name)
    except (ValueError,OSError,KeyError,TypeError) as error:
        parser.exit(2,f'consumer stopped: {error}\n')
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
