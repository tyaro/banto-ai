"""Save pinned report bytes once, then read them after the owned writer exits.

Ordinary trusted local processes only. Pins bind retained bytes; they do not
authenticate numerical provenance, source closure, or independent principals.
"""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import sys

from . import anomaly_v03_bound_summary_report as prepared
from . import anomaly_v03_process_supervisor as supervisor
from . import _anomaly_v03_fixture_budget as budgets

consumer=prepared.consumer;io=consumer.io;v=prepared.v
ROOT=Path(__file__).resolve().parents[2]
FORMAT='anomaly-v03-bound-report-publication-v1'
LIMITS={'wall_seconds':30,'private_bytes':512*1024**2,'output_bytes':64*1024}
CLOSED={**prepared.flow.CLOSED,'independent_numerical_audit_performed':False,
    'current_source_payloads_read':0,'new_evaluations':0,'report_mapping_runs':0,
    'aggregate_recalculations':0,'summary_binding_recalculations':0}


def _contract(mode,pins):
    v.require(type(mode) is str and mode in ('fixture','engineering'),'formal/unknown publication mode is closed')
    v.require(type(pins) is dict and set(pins)==set(prepared.PAYLOAD_LIMITS),'exact four retained payload pins')
    for name,limit in prepared.PAYLOAD_LIMITS.items():
        p=pins[name]
        v.require(type(p) is dict and set(p)=={'bytes','sha256'},'payload pin fields')
        v.require(type(p['bytes']) is int and 0<p['bytes']<=limit,'payload declared size')
        prepared.binding.evidence._digest(p['sha256'])


def _validate(files,pins,mode):
    """Validate historical preparation metadata and bytes, without recomputing cells."""
    _contract(mode,pins)
    v.require(set(files)==set(pins),'report payload inventory')
    for name,raw in files.items():
        v.require(type(raw) is bytes and prepared._pin(raw)==pins[name],'retained report bytes: '+name)
        v.require(b'\r' not in raw and raw.endswith(b'\n'),'report UTF-8/LF')
        raw.decode('utf-8',errors='strict')
    receipt=v.strict_json(files['consumer-receipt.json']);packet=v.strict_json(files['report.json'])
    fields={**prepared.CLOSED,'mode':mode,'formal_fields':prepared.FORMAL_FIELDS,
        'data_origin':'invented-compact-summaries' if mode=='fixture' else 'saved-dev-smoke-compact-summaries'}
    prepared.binding._fields(receipt,{**fields,'format':prepared.FORMAT,'status':'bound_summary_report_prepared',
        'current_source_payloads_read':0,'aggregate_recalculations':0,'summary_binding_recalculations':0,
        'detector_recalculations':0,'ledger_recalculations':0,'report_mapping_runs':1,'report_cell_validation_runs':1})
    prepared.binding._fields(packet,{**fields,'format':'anomaly-v03-dev-smoke-descriptive-report-v1'})
    prepared.tables.same(receipt['report_files'],{n:p for n,p in pins.items() if n!='consumer-receipt.json'},'preparation payload pins')
    prepared.tables.same(receipt['source_lineage'],packet['source_lineage'],'report/receipt lineage')
    prepared.tables.same(receipt['formal_readiness'],packet['formal_readiness'],'report readiness')
    prepared.binding._fields(packet['formal_readiness'],{'formal_ready':False,
        'status':'formal_analysis_not_ready','formal_document_emitted':False})
    if mode=='fixture':
        for name in ('report.md','report.html'):
            text=files[name].decode('utf-8')
            v.require('架空データ' in text and '保存済み720評価' not in text,'fixture label retained')
    return {'source_lineage_pin':prepared._pin(io.json_bytes(receipt['source_lineage'])),
        'consumer_receipt_pin':pins['consumer-receipt.json'],'output_bytes_verified':sum(len(b) for b in files.values())}


def _load(directory,pins):
    root=io.regular_path(Path(directory),directory=True)
    return {n:consumer.pinned.read_pinned(root/n,p,prepared.PAYLOAD_LIMITS[n]) for n,p in pins.items()}


def _read(publication,pins,mode,marker):
    root=io.regular_path(Path(publication),directory=True)
    v.require({p.name for p in root.iterdir()}=={'payload','marker-pending.json','.complete'},'publication control inventory')
    payload=io.regular_path(root/'payload',directory=True)
    v.require({p.name for p in payload.iterdir()}==set(pins),'publication payload inventory')
    for name,p in pins.items():v.require(io.regular_path(payload/name).stat().st_size==p['bytes'],'published payload size')
    for name in ('.complete','marker-pending.json'):
        v.require(io.regular_path(root/name,links=2).stat().st_size<=16*1024,'marker bound')
    metadata={}
    def verify(saved):metadata.update(_validate(dict(saved),pins,mode))
    checked=io.verify_local_publication(root,expected_marker_sha256=marker,verify_semantics=verify)
    return {**checked,**metadata}


def worker_main(argv):
    try:
        path,size,digest=argv
        request_pin={'bytes':int(size),'sha256':digest}
        request=v.strict_json(consumer.pinned.read_pinned(Path(path),request_pin,16*1024))
        role=request['role'];mode=request['mode'];pins=request['payload_pins'];_contract(mode,pins)
        v.require(request['format']==FORMAT and role in ('writer','reader'),'worker request role')
        if role=='writer':
            files=_load(request['source_directory'],pins);metadata=_validate(files,pins,mode)
            root=Path(request['publication_root'])
            result=io.publish_local_result(root.parent,root.name,files,
                verify_semantics=lambda saved:_validate(dict(saved),pins,mode))
            result.update(metadata,status='writer_completed')
        else:
            result=_read(request['publication_root'],pins,mode,request['expected_marker_sha256'])
            result.update(status='reader_verified',marker_raw_sha256=request['expected_marker_sha256'])
        result.update(CLOSED,format=FORMAT,role=role,mode=mode,worker_pid=os.getpid(),
            request_pin=request_pin,payload_pins=pins)
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'rejected','error_type':type(error).__name__,'formal_permission':False}))
        return 2
    print(json.dumps(result,ensure_ascii=False,sort_keys=True));return 0


def _role(request,target,budget):
    target.mkdir();raw=io.json_bytes(request);pin=prepared._pin(raw)
    io._exclusive(target/'request.json',raw)
    bootstrap='import sys;sys.path.insert(0,sys.argv.pop(1));from banto_ai.anomaly_v03_bound_report_publication import worker_main;raise SystemExit(worker_main(sys.argv[1:]))'
    argv=[sys.executable,'-I','-S','-B','-c',bootstrap,str(ROOT/'src'),str(target/'request.json'),str(pin['bytes']),pin['sha256']]
    def boundary():
        budget.checkpoint()
        v.require(consumer.pinned.read_pinned(target/'request.json',pin,16*1024)==raw,'worker request changed')
    try:monitor=supervisor.supervise(argv,ROOT,target/'worker',LIMITS,boundary=boundary,resource_probe=budget.probe)
    except supervisor.UnreapedWorker as error:
        io._exclusive(target/'supervision.json',io.json_bytes(error.report));raise
    io._exclusive(target/'supervision.json',io.json_bytes(monitor))
    v.require(monitor['status']=='complete' and monitor['worker_exit_confirmed'] is True and
        monitor['exit_code']==0 and not monitor['observation_errors'],'owned '+request['role']+' failed')
    reply=v.strict_json(consumer.pinned.read_pinned(target/'worker/report.json',monitor['output'],LIMITS['output_bytes']))
    prepared.binding._fields(reply,{**CLOSED,'format':FORMAT,'mode':request['mode'],'role':request['role'],
        'status':'writer_completed' if request['role']=='writer' else 'reader_verified',
        'request_pin':pin,'payload_pins':request['payload_pins'],'worker_pid':monitor['worker_pid']})
    v.require(type(reply['worker_pid']) is int and reply['worker_pid']!=os.getpid(),'owned separate worker')
    reply['supervision_pin']=prepared._pin(io.json_bytes(monitor))
    reply['worker_exit_confirmed']=True
    io._exclusive(target/'result.json',io.json_bytes(reply));return reply


def publish_and_check(source_directory,*,expected_mode,expected_payload_pins,output_parent,output_name,resource_budget=None):
    """One new attempt. No overwrite, restart, remapping, or numerical audit.

    The caller retains payload pins outside the source. Failure preserves all
    files; a lost writer reply is unconfirmed and never starts a reader.
    """
    _contract(expected_mode,expected_payload_pins);pins=copy.deepcopy(expected_payload_pins)
    source=io.regular_path(Path(source_directory).absolute(),directory=True)
    parent=io._local_parent(Path(output_parent).absolute());v.safe_relative_path(output_name)
    v.require('/' not in output_name and not output_name.casefold().startswith('anomaly-multiseed-v0'),'attempt name')
    target=io.regular_path(parent/output_name,directory=True,missing=True)
    for p in (source,ROOT/'src'):
        v.require(not (target==p or target in p.parents or p in target.parents),'attempt overlaps source')
    target.mkdir();publication=target/'published'
    budget=budgets.FixtureBudget(target,upstream=resource_budget,publication_roots=[publication])
    result={**CLOSED,'format':FORMAT,'mode':expected_mode,'status':'failed','payload_pins':pins,
        'publication_status':'not_started','reader_status':'not_started','writer_reaped_before_reader_start':False}
    request={'format':FORMAT,'mode':expected_mode,'payload_pins':pins,'source_directory':str(source),
        'publication_root':str(publication),'role':'writer'}
    try:
        budget.start();result['publication_status']='unconfirmed'
        writer=_role(request,target/'writer',budget)
        marker=writer['marker_raw_sha256'];prepared.binding.evidence._digest(marker)
        result.update(publication_status='completed',writer=writer,marker_raw_sha256=marker)
        budget.checkpoint();result.update(reader_status='unconfirmed',writer_reaped_before_reader_start=True)
        reader=_role({k:val for k,val in request.items() if k!='source_directory'}|
            {'role':'reader','expected_marker_sha256':marker},target/'reader',budget)
        prepared.tables.same(reader['marker_raw_sha256'],marker,'reader marker binding')
        for name in ('source_lineage_pin','consumer_receipt_pin','output_bytes_verified'):
            prepared.tables.same(reader[name],writer[name],'writer/reader '+name)
        v.require(reader['local_verified'] is True and reader['payloads']==4,'reader completion')
        result.update(status='verified',reader_status='completed',reader=reader,payload_files=4,
            payload_bytes=reader['output_bytes_verified'],source_lineage_pin=reader['source_lineage_pin'])
    except supervisor.UnreapedWorker as error:
        result['reason']='worker_exit_unconfirmed'
        try:io._exclusive(target/'unreaped.json',io.json_bytes(result))
        finally:raise error
    except (ValueError,OSError,KeyError,TypeError) as error:
        result.update(reason='publication_or_reader_rejected',error_type=type(error).__name__,detail=str(error))
    finally:budgets.finish(budget,target,result,owner_error=sys.exception())
    budgets.save_result(target,result)
    return {**result,'check_directory':str(target),'result_pin':prepared._pin(io.json_bytes(result))}
