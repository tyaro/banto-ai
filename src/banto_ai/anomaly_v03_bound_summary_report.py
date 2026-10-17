"""Prepare descriptive report payloads from pinned compact tables, without IO.

Reuse the report mapper; no saved summaries, journal or raw payloads are opened.
Caller-held pins identify trusted historical inputs, not authenticated execution.
"""
from __future__ import annotations
import copy
import hashlib

from . import anomaly_v03_bound_summary_tables as tables
from . import anomaly_v03_descriptive_report as report
from . import anomaly_v03_engineering_consumer as consumer

binding=tables.binding
flow=tables.flow
v=tables.v
FORMAT='anomaly-v03-bound-summary-report-receipt-v1'
PAYLOAD_LIMITS={**consumer.REPORT_LIMITS,'consumer-receipt.json':1024**2}
FORMAL_FIELDS=dict.fromkeys(('status','provenance','analysis_consumer','bootstrap'))
CLOSED={**flow.CLOSED,'formal_document_emitted':False,'formal_schema_validated':False,
        'decision':'not_evaluated','published':False,'independent_numerical_audit_performed':False}


def _pin(raw):return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def _json(value):return v.canonical_json(value)+b'\n'


def _source(value,schema,mode):
    binding._fields(value,{**flow.CLOSED,'format':tables.FORMAT,'mode':mode,
        'status':'complete_dev_smoke_descriptive_tables','evaluations':720,'seed_groups':10,
        'registry_raw_sha256':v.REGISTRY_RAW_SHA256,'current_source_payloads_read':0,
        'numeric_audits_repeated':0,'ledger_audits_repeated':0,'journal_replayed':False,
        'raw_generation_verified':False,'real_performance_intervals_computed':0})
    coverage=value['coverage']
    binding.evidence._keys(coverage,'success inconclusive partial failed not_started','complete table coverage')
    for n in coverage.values():v.require(type(n) is int and n>=0,'coverage integer')
    v.require(coverage['success']+coverage['inconclusive']==720 and
              coverage['partial']==coverage['failed']==coverage['not_started']==0,'all latest slots complete')
    # The legacy mapper's authentication status means caller-pinned input here;
    # this private view is not saved or presented as process/producer evidence.
    source={**report.inputs.QUIET,'status':'authenticated_dev_smoke_analysis_inputs',
        'evaluations':720,'formal_document_emitted':False,'by_role':value['by_role'],
        'readiness':report.inputs.formal_readiness(schema)}
    report._source_tables(source)
    return source


def prepare_bound_report(tables_raw,schema_raw,*,expected_tables_pin,expected_schema_pin,expected_mode):
    """Return four complete UTF-8/LF payloads and their preparation receipt.

    Neither partial payloads nor formal reports are returned. The caller handles
    resource limits and any subsequent publication; paths in inputs are opaque.
    """
    v.require(type(expected_mode) is str and expected_mode in ('fixture','engineering'),'formal/unknown report mode is closed')
    value=binding._load(tables_raw,expected_tables_pin,16*1024**2)
    schema=binding._load(schema_raw,expected_schema_pin,1024**2)
    source=_source(value,schema,expected_mode)
    packet=report.build_report(source,schema)
    # build_report already validates the emitted cells against source + schema.
    # Record the exact fixed inventory without another mapper/audit execution.
    checks={'status':'descriptive_report_cells_verified','cohorts':2,'candidate_tables':18,
        'primary_metrics':234,'diagnostic_rows':5670,'schema_components_validated':True,
        'formal_schema_validated':False,'performance_status':'not_evaluated'}
    v.require(sum(len(c['candidate_tables']) for c in packet['cohorts'])==checks['candidate_tables'],'emitted table count')
    v.require(sum(len(rows) for c in packet['cohorts'] for rows in c['diagnostic_series'].values())==checks['diagnostic_rows'],'emitted diagnostic count')
    lineage={key:copy.deepcopy(value[key]) for key in ('binding_pin','metadata_pin','journal_bindings',
        'completed_savepoint_pin','evidence_pin','source_summaries','coverage','failed_attempt_history','zero_denominator_input_metrics')}
    lineage.update(tables_pin=copy.deepcopy(expected_tables_pin),schema_pin=copy.deepcopy(expected_schema_pin),
        byte_trust='caller-held pins for retained tables and schema; no current raw payload or process attestation')
    packet.update(**{k:val for k,val in CLOSED.items() if k not in packet},mode=expected_mode,
        data_origin='invented-compact-summaries' if expected_mode=='fixture' else 'saved-dev-smoke-compact-summaries',
        formal_fields=copy.deepcopy(FORMAL_FIELDS),source_lineage=lineage)
    markdown=report.summary_markdown(packet);html=report.detailed_html(packet)
    if expected_mode=='fixture':
        # Keep the established layout while ensuring neither view calls invented
        # counts an actual 720-evaluation result. Fail if the legacy intro moves.
        for text in (markdown,html):v.require(text.count('保存済み720評価')==1,'expected descriptive introduction')
        markdown=markdown.replace('保存済み720評価','架空要約720枠')
        markdown=markdown.replace('# Banto AI 開発用・動作確認用の評価結果',
            '# Banto AI 報告書の接続確認（架空データ）\n\n**これは報告機能の試験用データです。実際の検出性能を示す結果ではありません。**',1)
        html=html.replace('保存済み720評価','架空要約720枠').replace('<title>Banto AI 条件別結果</title>',
            '<title>Banto AI 報告書の接続確認（架空データ）</title>',1)
        html=html.replace('<h1>Banto AI 条件別結果</h1>',
            '<h1>Banto AI 報告書の接続確認（架空データ）</h1><p><strong>これは報告機能の試験用データです。実際の検出性能を示す結果ではありません。</strong></p>',1)
    notice=f"判定不能を含む評価は{value['coverage']['inconclusive']}件です。該当項目の診断は全数値JSONに保持しています。"
    markdown=markdown.replace('\n\n','\n\n'+notice+'\n\n',1)
    html=html.replace('</h1>','</h1><p>'+notice+'</p>',1)
    files={'report.json':_json(packet),'report.md':(markdown.rstrip('\n')+'\n').encode('utf-8'),
        'report.html':(html.rstrip('\n')+'\n').encode('utf-8')}
    receipt={**CLOSED,'format':FORMAT,'status':'bound_summary_report_prepared','mode':expected_mode,
        'data_origin':packet['data_origin'],'source_lineage':lineage,'formal_fields':copy.deepcopy(FORMAL_FIELDS),
        'formal_readiness':copy.deepcopy(packet['formal_readiness']),'checks':checks,
        'report_files':{name:_pin(raw) for name,raw in files.items()},'current_source_payloads_read':0,
        'aggregate_recalculations':0,'summary_binding_recalculations':0,'detector_recalculations':0,
        'ledger_recalculations':0,'report_mapping_runs':1,'report_cell_validation_runs':1,
        'limitations':['report/schema cell correspondence only; no independent numerical or process acceptance',
            'dev and smoke remain distinct; formal fields stay unfilled; publication is not performed']}
    files['consumer-receipt.json']=_json(receipt)
    v.require(set(files)==set(PAYLOAD_LIMITS) and sum(map(len,files.values()))<=8*1024**2,'complete bounded report payload set')
    for name,raw in files.items():
        v.require(0<len(raw)<=PAYLOAD_LIMITS[name] and b'\r' not in raw and raw.endswith(b'\n'),'bounded UTF-8/LF report '+name)
        raw.decode('utf-8',errors='strict')
    return files,receipt
