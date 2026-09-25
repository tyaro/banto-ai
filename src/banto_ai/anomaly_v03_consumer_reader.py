"""Post-writer engineering reader with separate, immutable check attempts.

Trusted callers supply retained marker/source anchors and serialize writers and
readers. Process separation is not a principal boundary or a numerical audit.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys

from . import anomaly_v03_engineering_consumer as consumer
from . import anomaly_v03_process_supervisor as supervisor

io=consumer.io;v=consumer.v
MIB=1024**2
LIMITS={'wall_seconds':30,'private_bytes':512*MIB,'output_bytes':64*1024}
FORMAT='anomaly-v03-engineering-reader-request-v1'
REQUEST_KEYS={'format','mode','publication_root','expected_marker_sha256','binding_savepoint',
    'report_savepoint','analysis_input','expected_binding_pin','expected_report_pin'}
PROJECT=Path(__file__).resolve().parents[2]


def _digest(value):
    v.require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value),'retained SHA256 required')


def _pin_shape(value):
    v.require(type(value) is dict and set(value)=={'bytes','sha256'},'retained pin fields')
    v.require(type(value['bytes']) is int and 0<value['bytes']<=MIB,'retained savepoint size')
    _digest(value['sha256'])


def _request(value):
    v.require(type(value) is dict and set(value)==REQUEST_KEYS,'reader request fields')
    v.require(value['mode']==consumer.MODE and type(value['mode']) is str,'formal/unknown reader mode is closed')
    v.require(value['format']==FORMAT,'reader request format')
    _digest(value['expected_marker_sha256'])
    for name in ('expected_binding_pin','expected_report_pin'):_pin_shape(value[name])
    for name in ('publication_root','binding_savepoint','report_savepoint','analysis_input'):
        v.require(type(value[name]) is str and Path(value[name]).is_absolute(),'explicit absolute reader path')


def verify_saved_publication(request):
    """Authenticate source bytes and compare the entire published result read-only."""
    _request(request)
    files,receipt=consumer.prepare_engineering_result(request['binding_savepoint'],request['report_savepoint'],
        request['analysis_input'],expected_mode=request['mode'],expected_binding_pin=request['expected_binding_pin'],
        expected_report_pin=request['expected_report_pin'])
    root=io.regular_path(Path(request['publication_root']),directory=True)
    v.require({p.name for p in root.iterdir()}=={'payload','marker-pending.json','.complete'},'reader control inventory')
    payload=io.regular_path(root/'payload',directory=True)
    v.require({p.name for p in payload.iterdir()}==set(files),'reader payload inventory')
    # Bound every saved object before the generic publication reader opens it.
    for name,raw in files.items():
        path=io.regular_path(payload/name)
        v.require(path.stat().st_size==len(raw),'reader payload size differs: '+name)
    for name in ('.complete','marker-pending.json'):
        path=io.regular_path(root/name,links=2)
        v.require(path.stat().st_size<=16*1024,'reader marker size limit')

    def verify(saved):
        consumer._same(sorted(saved),sorted(files),'reader expected output inventory')
        for name,raw in files.items():v.require(saved[name]==raw,'reader source-bound content differs: '+name)

    checked=io.verify_local_publication(root,expected_marker_sha256=request['expected_marker_sha256'],verify_semantics=verify)
    return {**consumer.QUIET,**consumer.BOUNDARY,**checked,
        'format':'anomaly-v03-engineering-reader-report-v1','status':'source_bound_publication_verified',
        'reader_pid':os.getpid(),'publication_root':str(root),'marker_raw_sha256':request['expected_marker_sha256'],
        'consumer_receipt_pin':consumer._pin(files['consumer-receipt.json']),
        'authenticated_artifacts':len(receipt['authenticated_files']),
        'authenticated_bytes':sum(p['bytes'] for p in receipt['authenticated_files'].values()),
        'output_bytes_verified':sum(len(raw) for raw in files.values()),
        'independent_numerical_audit_performed':False,'historical_report_cell_validation_reused':True,
        'source_payload_bytes_read':0,'new_evaluations':0,'score_recalculations':0,'aggregate_recalculations':0}


def worker_main(argv):
    parser=argparse.ArgumentParser(description='Internal bounded, read-only saved-result checker.')
    parser.add_argument('request');parser.add_argument('bytes',type=int);parser.add_argument('sha256')
    args=parser.parse_args(argv);pin={'bytes':args.bytes,'sha256':args.sha256}
    try:
        raw=consumer.pinned.read_pinned(Path(args.request),pin,16*1024)
        result=verify_saved_publication(v.strict_json(raw))
        result['request_pin']=pin
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps({'status':'reader_rejected','reader_pid':os.getpid(),'error_type':type(error).__name__,
            'formal_permission':False},sort_keys=True))
        return 2
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0


def _overlap(left,right):return left==right or left in right.parents or right in left.parents


def check_in_subprocess(publication_root,binding_savepoint,report_savepoint,analysis_input,*,
                        expected_mode,expected_marker_sha256,expected_binding_pin,expected_report_pin,
                        receipt_parent,receipt_name):
    """Check an already closed writer's result; retain each success/failure outside it.

    Does not infer a marker anchor from the publication being checked. A lost
    writer reply is recoverable only with independently retained expected pins.
    UnreapedWorker preserves the original owner for the caller to reap.
    """
    request={'format':FORMAT,'mode':expected_mode,'expected_marker_sha256':expected_marker_sha256,
        'expected_binding_pin':expected_binding_pin,'expected_report_pin':expected_report_pin,
        **{name:str(Path(path).absolute()) for name,path in (
            ('publication_root',publication_root),('binding_savepoint',binding_savepoint),
            ('report_savepoint',report_savepoint),('analysis_input',analysis_input))}}
    _request(request)  # Reject formal/invalid anchors before any filesystem IO.
    parent=io._local_parent(Path(receipt_parent))
    v.safe_relative_path(receipt_name)
    v.require('/' not in receipt_name and not receipt_name.casefold().startswith('anomaly-multiseed-v0'),'reader attempt name')
    target=io.regular_path(parent/receipt_name,directory=True,missing=True)
    sources=[io.regular_path(Path(request[name])) for name in ('binding_savepoint','report_savepoint','analysis_input')]
    publication=io.regular_path(Path(request['publication_root']),directory=True)
    v.require(all(not _overlap(target,p) for p in [publication,*(p.parent for p in sources)]),'reader receipt overlaps saved inputs')
    target.mkdir()  # Exclusive; never reuse a previous check, including failure.
    raw=io.json_bytes(request);request_path=target/'request.json';io._exclusive(request_path,raw)
    request_pin=consumer._pin(raw)
    selected_sources={str(PROJECT/'src/banto_ai'/name):consumer._pin((PROJECT/'src/banto_ai'/name).read_bytes()) for name in
        ('anomaly_v03_consumer_reader.py','anomaly_v03_engineering_consumer.py','anomaly_v03_process_supervisor.py',
         '_anomaly_v03_io.py','_anomaly_v03_runtime.py','_anomaly_v03_engineering_runtime.py')}

    def boundary():
        for path,pin in selected_sources.items():v.require(consumer._pin(Path(path).read_bytes())==pin,'reader entry source changed')
        v.require(consumer._pin(request_path.read_bytes())==request_pin,'reader request changed')

    # -I ignores PYTHONPATH and user site; -S skips site initialization, including
    # system site-packages. Only this explicit source checkout is added. The
    # child invokes no producer, generator, writer, or subprocess.
    bootstrap='import sys;sys.path.insert(0,sys.argv.pop(1));from banto_ai.anomaly_v03_consumer_reader import worker_main;raise SystemExit(worker_main(sys.argv[1:]))'
    argv=[sys.executable,'-I','-S','-B','-c',bootstrap,str(PROJECT/'src'),str(request_path),str(request_pin['bytes']),request_pin['sha256']]
    outer={**consumer.QUIET,**consumer.BOUNDARY,'format':'anomaly-v03-engineering-reader-check-v1',
        'status':'failed','request_pin':request_pin,'publication_root':str(publication),
        'expected_marker_sha256':expected_marker_sha256,'reader_exit_confirmed':False,
        'separate_process_verified':False,'independent_numerical_audit_performed':False,
        'selected_entry_source_pins':selected_sources,'source_closure_complete':False,
        'new_evaluations':0,'source_payload_bytes_read':0,'original_publication_modified':False}
    try:
        monitor=supervisor.supervise(argv,PROJECT,target/'worker',LIMITS,boundary=boundary)
    except supervisor.UnreapedWorker as error:
        io._exclusive(target/'supervision.json',io.json_bytes(error.report))
        io._exclusive(target/'result.json',io.json_bytes({**outer,'reason':'worker_exit_unconfirmed'}))
        raise  # Preserve ownership; never scan a possibly still-written log.
    monitor_raw=io.json_bytes(monitor);io._exclusive(target/'supervision.json',monitor_raw)
    outer.update(supervision_pin=consumer._pin(monitor_raw),reader_pid=monitor['worker_pid'],
        reader_exit_confirmed=monitor['worker_exit_confirmed'],worker_exit_code=monitor['exit_code'],
        reason=monitor['stop_reason'] or 'reader_rejected')
    if monitor['status']=='complete':
        try:
            reply=v.strict_json(consumer.pinned.read_pinned(target/'worker/report.json',monitor['output'],LIMITS['output_bytes']))
            consumer._fields(reply,{**consumer.QUIET,**consumer.BOUNDARY,
                'format':'anomaly-v03-engineering-reader-report-v1','status':'source_bound_publication_verified',
                'local_verified':True,'payloads':4,'native_acceptance':'not_completed',
                'request_pin':request_pin,'publication_root':str(publication),'marker_raw_sha256':expected_marker_sha256,
                'reader_pid':monitor['worker_pid'],'independent_numerical_audit_performed':False,
                'new_evaluations':0,'source_payload_bytes_read':0},'reader response binding')
            v.require(type(reply['reader_pid']) is int and reply['reader_pid']!=os.getpid(),'reader must be a separate process')
            outer.update(status='verified',reason=None,separate_process_verified=True,reader_report_pin=monitor['output'],
                consumer_receipt_pin=reply['consumer_receipt_pin'],authenticated_artifacts=reply['authenticated_artifacts'],
                authenticated_bytes=reply['authenticated_bytes'],output_bytes_verified=reply['output_bytes_verified'])
        except (ValueError,OSError,KeyError,TypeError) as error:
            outer.update(reason='reader_response_invalid',error_type=type(error).__name__)
    result_raw=io.json_bytes(outer);io._exclusive(target/'result.json',result_raw)
    return {**outer,'check_directory':str(target),'result_pin':consumer._pin(result_raw)}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Read an existing engineering result in a bounded separate process.')
    parser.add_argument('--mode',required=True,choices=(consumer.MODE,))
    for name in ('publication-root','marker-sha256','binding-savepoint','report-savepoint','analysis-input','receipt-parent','receipt-name'):
        parser.add_argument('--'+name,required=True)
    for name in ('binding','report'):
        parser.add_argument('--'+name+'-bytes',type=int,required=True);parser.add_argument('--'+name+'-sha256',required=True)
    args=parser.parse_args(argv)
    try:
        result=check_in_subprocess(args.publication_root,args.binding_savepoint,args.report_savepoint,args.analysis_input,
            expected_mode=args.mode,expected_marker_sha256=args.marker_sha256,
            expected_binding_pin={'bytes':args.binding_bytes,'sha256':args.binding_sha256},
            expected_report_pin={'bytes':args.report_bytes,'sha256':args.report_sha256},
            receipt_parent=args.receipt_parent,receipt_name=args.receipt_name)
    except supervisor.UnreapedWorker as error:
        supervisor.retain_until_exit(error)
        parser.exit(2,'reader stopped; original owned process reaped; check remains unconfirmed\n')
    except (ValueError,OSError,KeyError,TypeError) as error:
        parser.exit(2,f'reader stopped: {error}\n')
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0 if result['status']=='verified' else 2


if __name__=='__main__':raise SystemExit(main())
