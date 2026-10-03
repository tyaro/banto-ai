"""One bounded dev/smoke entry starting from a caller-pinned retained stage.

No raw evaluation execution, automatic retries, or formal inference. Checkpoints
are new immutable requests; the caller explicitly selects a later start stage.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import sys

from . import anomaly_v03_bound_report_publication as publication

prepared=publication.prepared;tables=prepared.tables;io=publication.io;v=publication.v
budgets=publication.budgets;reader=publication.consumer.pinned
FORMAT='anomaly-v03-saved-report-pipeline-v1'
REQUEST_FORMAT='anomaly-v03-saved-report-pipeline-request-v1'
STAGES={'summaries':{'binding','summaries','schema'},'tables':{'tables','schema'},
        'report':{'directory','payload_pins'},'publication':{'directory','result_pin'}}
MIB=1024**2


def _pin(value,maximum):
    prepared.binding.evidence._pin(value)
    v.require(type(value['bytes']) is int and 0<value['bytes']<=maximum,'bounded retained pin')


def _path(value):
    v.require(type(value) is str and 0<len(value)<=4096 and Path(value).is_absolute(),'explicit absolute saved path')


def _ref(value,maximum):
    v.require(type(value) is dict and set(value)=={'path','pin'},'saved file reference fields')
    _path(value['path']);_pin(value['pin'],maximum)


def _request(request):
    v.require(type(request) is dict and set(request)=={'format','mode','start_from','inputs'},'pipeline request fields')
    v.require(type(request['mode']) is str and request['mode'] in ('fixture','engineering'),'formal/unknown pipeline mode is closed')
    v.require(request['format']==REQUEST_FORMAT,'pipeline request format')
    stage=request['start_from'];inputs=request['inputs']
    v.require(type(stage) is str and stage in STAGES,'explicit saved start stage')
    v.require(type(inputs) is dict and set(inputs)==STAGES[stage],'exact selected stage inputs')
    if stage in ('summaries','tables'):
        _ref(inputs['schema'],MIB)
        if stage=='summaries':
            _ref(inputs['binding'],tables.MAX_BINDING)
            refs=inputs['summaries'];v.require(type(refs) is list and len(refs)==120,'all ordered compact summaries')
            for ref in refs:_ref(ref,prepared.binding.MAX_SUMMARY)
            v.require(len({r['path'] for r in refs})==120,'distinct summary references')
            v.require(inputs['binding']['pin']['bytes']+sum(r['pin']['bytes'] for r in refs)<=prepared.binding.MAX_TOTAL,'summary input total')
        else:_ref(inputs['tables'],16*MIB)
    else:
        _path(inputs['directory'])
        if stage=='report':publication._contract(request['mode'],inputs['payload_pins'])
        else:_pin(inputs['result_pin'],64*1024)
    v.require(len(io.json_bytes(request))<=128*1024,'pipeline request bound')


def _inputs(request):
    rows=request['inputs'];stage=request['start_from']
    if stage in ('report','publication'):return [Path(rows['directory'])]
    refs=[rows['schema']]
    refs+=([rows['binding']]+rows['summaries']) if stage=='summaries' else [rows['tables']]
    return [Path(r['path']).parent for r in refs]


def _read(ref,maximum):return reader.read_pinned(Path(ref['path']),ref['pin'],maximum)


def _write(path,raw):
    io._exclusive(path,raw);pin=prepared._pin(raw)
    reader.read_pinned(path,pin,len(raw))
    return {'path':str(path),'pin':pin}


def _checkpoint(target,stage,mode,inputs):
    request={'format':REQUEST_FORMAT,'mode':mode,'start_from':stage,'inputs':inputs}
    _request(request)
    return _write(target/(stage+'-checkpoint.json'),io.json_bytes(request))


def _reuse_publication(inputs,mode):
    """Reuse trusted historical completion; verify current bytes, not new process evidence."""
    root=io.regular_path(Path(inputs['directory']),directory=True)
    raw=reader.read_pinned(root/'result.json',inputs['result_pin'],64*1024);value=v.strict_json(raw)
    prepared.binding._fields(value,{**publication.CLOSED,'format':publication.FORMAT,'mode':mode,
        'status':'verified','resource_budget_passed':True,'publication_status':'completed',
        'reader_status':'completed','writer_reaped_before_reader_start':True,'payload_files':4})
    pins=value['payload_pins'];publication._contract(mode,pins)
    marker=value['marker_raw_sha256'];prepared.binding.evidence._digest(marker)
    for role,status in (('writer','writer_completed'),('reader','reader_verified')):
        part=value[role]
        prepared.binding._fields(part,{**publication.CLOSED,'format':publication.FORMAT,'mode':mode,
            'role':role,'status':status,'worker_exit_confirmed':True,'payload_pins':pins,
            'marker_raw_sha256':marker,'source_lineage_pin':value['source_lineage_pin'],
            'consumer_receipt_pin':pins['consumer-receipt.json'],'output_bytes_verified':value['payload_bytes']})
        v.require(type(part['worker_pid']) is int and part['worker_pid']>0,'historical worker PID')
    current=publication._read(root/'published',pins,mode,marker)
    tables.same(current['source_lineage_pin'],value['source_lineage_pin'],'saved publication lineage')
    tables.same(current['output_bytes_verified'],value['payload_bytes'],'saved publication bytes')
    return {'directory':str(root),'result_pin':copy.deepcopy(inputs['result_pin']),
        'marker_raw_sha256':marker,'payload_pins':pins,'source_lineage_pin':current['source_lineage_pin'],
        'historical_worker_evidence_reused':True,'current_worker_execution_verified':False}


def run_pipeline(request,*,output_parent,output_name,resource_limits=None):
    """Advance only missing stages; retain failures and requests for explicit resume.

    All reads use caller-held pins. Reuse of completed publication starts no
    process; ownership evidence is historical, never promoted to authentication.
    """
    _request(request);request=copy.deepcopy(request);limits=budgets.limits(resource_limits)
    parent=io._local_parent(Path(output_parent).absolute());v.safe_relative_path(output_name)
    v.require('/' not in output_name and not output_name.casefold().startswith('anomaly-multiseed-v0'),'pipeline attempt name')
    target=io.regular_path(parent/output_name,directory=True,missing=True)
    for p in [publication.ROOT/'src',*_inputs(request)]:
        v.require(not(target==p or target in p.parents or p in target.parents),'pipeline overlaps saved source')
    target.mkdir();budget=budgets.FixtureBudget(target,limits,publication_roots=[target/'publication/published'])
    result={**prepared.flow.CLOSED,'format':FORMAT,'mode':request['mode'],'status':'failed',
        'start_from':request['start_from'],'aggregation_runs':0,'report_runs':0,'publication_runs':0,
        'current_source_payloads_read':0,'independent_numerical_audit_performed':False,
        'checkpoints':{},'completed_stages_reused':[]}
    stage=request['start_from'];inputs=request['inputs'];mode=request['mode']
    try:
        budget.start();result['request_reference']=_write(target/'request.json',io.json_bytes(request));budget.checkpoint()
        if stage=='summaries':
            bound=_read(inputs['binding'],tables.MAX_BINDING)
            summaries={i:_read(ref,prepared.binding.MAX_SUMMARY) for i,ref in enumerate(inputs['summaries'])}
            budget.checkpoint();result['aggregation_runs']=1
            value=tables.aggregate_bound_summaries(bound,summaries,expected_binding_pin=inputs['binding']['pin'],expected_mode=mode)
            del bound,summaries
            ref=_write(target/'tables.json',io.json_bytes(value));del value
            inputs={'tables':ref,'schema':inputs['schema']};stage='tables'
            result['checkpoints']['tables']=_checkpoint(target,stage,mode,inputs);budget.checkpoint()
        elif stage=='tables':result['completed_stages_reused'].append('tables')
        if stage=='tables':
            raw=_read(inputs['tables'],16*MIB);schema=_read(inputs['schema'],MIB);budget.checkpoint()
            result['report_runs']=1
            files,_=prepared.prepare_bound_report(raw,schema,expected_tables_pin=inputs['tables']['pin'],
                expected_schema_pin=inputs['schema']['pin'],expected_mode=mode)
            del raw,schema
            directory=target/'report';directory.mkdir()
            pins={n:_write(directory/n,b)['pin'] for n,b in files.items()};del files
            inputs={'directory':str(directory),'payload_pins':pins};stage='report'
            result['checkpoints']['report']=_checkpoint(target,stage,mode,inputs);budget.checkpoint()
        elif stage=='report':result['completed_stages_reused'].append('report')
        if stage=='report':
            budget.checkpoint();result['publication_runs']=1
            published=publication.publish_and_check(inputs['directory'],expected_mode=mode,expected_payload_pins=inputs['payload_pins'],
                output_parent=target,output_name='publication',resource_budget=budget)
            result['publication_attempt']={'directory':published['check_directory'],'result_pin':published['result_pin']}
            v.require(published['status']=='verified' and published['resource_budget_passed'],'publication stage failed')
            inputs={'directory':published['check_directory'],'result_pin':published['result_pin']}
            result['checkpoints']['publication']=_checkpoint(target,'publication',mode,inputs)
            result['publication']={**inputs,'marker_raw_sha256':published['marker_raw_sha256'],
                'payload_pins':published['payload_pins'],'source_lineage_pin':published['source_lineage_pin'],
                'historical_worker_evidence_reused':False,'current_worker_execution_verified':True}
        elif stage=='publication':
            result['publication']=_reuse_publication(inputs,mode)
            result['completed_stages_reused'].append('publication')
            result['checkpoints']['publication']=_checkpoint(target,stage,mode,inputs)
        budget.checkpoint();result['status']='verified'
    except publication.supervisor.UnreapedWorker as error:
        try:io._exclusive(target/'unreaped.json',io.json_bytes(result|{'reason':'worker_exit_unconfirmed'}))
        finally:raise error
    except (ValueError,OSError,KeyError,TypeError) as error:
        result.update(reason='pipeline_stage_rejected',error_type=type(error).__name__,detail=str(error))
    finally:budgets.finish(budget,target,result,owner_error=sys.exception())
    budgets.save_result(target,result)
    return {**result,'check_directory':str(target),'result_pin':prepared._pin(io.json_bytes(result))}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Continue pinned saved dev/smoke stages without evaluation replay.')
    for name in ('request','sha256','output-parent','output-name'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--bytes',type=int,required=True);args=parser.parse_args(argv)
    try:
        request=v.strict_json(reader.read_pinned(Path(args.request),{'bytes':args.bytes,'sha256':args.sha256},128*1024))
        result=run_pipeline(request,output_parent=args.output_parent,output_name=args.output_name)
    except publication.supervisor.UnreapedWorker as error:
        publication.supervisor.retain_until_exit(error);parser.exit(2,'worker stopped and reaped; saved attempt remains unconfirmed\n')
    except (ValueError,OSError,KeyError,TypeError):parser.exit(2,'saved pipeline request rejected\n')
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0 if result['status']=='verified' else 2


if __name__=='__main__':raise SystemExit(main())
