"""Render authenticated dev/smoke summaries; never emit a formal analysis.

Each cohort has nine candidate tables and four separately named slice series.
Only frozen schema components are validated, using actual cohort denominators.
Score-reference omissions and incident delay histograms live in sidecars.
"""
from __future__ import annotations

import copy
from html import escape
from pathlib import Path

from . import anomaly_v03 as contract
from . import anomaly_v03_analysis_inputs as inputs
from . import anomaly_v03_inference_audit as arithmetic
from .anomaly_v03_observation_audit import read_pinned, paths, scores

QUIET={**inputs.QUIET,'formal_document_emitted':False,'formal_schema_validated':False,'decision':'not_evaluated'}
SERIES={'incident-recall':'detected','score-availability':'available',
        'score-threshold-exceedance':'threshold_exceeded','score-signal-onset':'signal_onsets'}
MAPPING={'planned_count':'planned incidents or event-relative references',
         'actual_count':'numerator of this named series',
         'score_denominator':'scheduled in-test scored origins, including unavailable origins',
         'incident_denominator':'all planned positive incidents',
         'zero_incident_or_score_denominator':'null and not_applicable',
         'zero_primary_denominator':'null; CI not_evaluated; original diagnostics retained',
         'event_offset_partition':False,'class_precision':'not_applicable',
         'formal_mapping_accepted':False}


def metric(n,d,kind='ratio',*,primary=False):
    inputs.integer(n);inputs.integer(d)
    if kind not in ('clean_rate','false_alert_burden'):inputs.need(n<=d,'ratio count bounds')
    return {'numerator':n,'denominator':d,'value':arithmetic.ratio(n,d,kind),
            'ci_status':'not_evaluated' if d or primary else 'not_applicable',
            'ci_lower':None,'ci_upper':None,'null_replicates':0}


def _source_tables(source):
    inputs.fields(source,{**inputs.QUIET,'status':'authenticated_dev_smoke_analysis_inputs',
                  'evaluations':720,'formal_document_emitted':False},'descriptive source')
    keys=[(r,c,s) for r in ('dev','smoke') for c in arithmetic.CANDIDATES for s in arithmetic.STRATA]
    tables=inputs.index(source['by_role'],('role','candidate_id','stratum'),keys)
    for (role,_,layer),t in tables.items():
        n=(96 if role=='dev' else 24)*(2 if layer=='overall' else 1)
        inputs.exact(t['seeds'],8 if role=='dev' else 2,'cohort seed count')
        inputs._join_table(t,t,n)
    return tables


def _mapped_slice(t,cell,series):
    incident=series=='incident-recall';n=cell[SERIES[series]];d=cell['planned'] if incident else cell['observed']
    return {'candidate_id':t['candidate_id'],'stratum':t['stratum'],'dimension':cell['dimension'],'key':cell['key'],
        'metric':metric(n,d),'planned_count':cell['planned'],'actual_count':n,
        'delay_summary':copy.deepcopy(cell['delay_summary']) if incident else None}


def build_report(source,schema):
    """Pure mapper; callers must authenticate input bytes separately."""
    tables=_source_tables(source);cohorts=[]
    for role in ('dev','smoke'):
        cohort={'role':role,'seed_count':8 if role=='dev' else 2,'evaluations':576 if role=='dev' else 144,
                'candidate_tables':[],'diagnostic_series':{k:[] for k in SERIES},'diagnostic_details':[]}
        for candidate in arithmetic.CANDIDATES:
            for layer in arithmetic.STRATA:
                t=tables[role,candidate,layer]
                measures={k:metric(*t['counts'][k],k,primary=True) for k in arithmetic.METRICS[:5]}
                measures['availability']=[{'full_target':target,'metric':metric(*t['counts']['availability:'+target],primary=True)}
                                          for target in arithmetic.TARGETS]
                measures.update({k:copy.deepcopy(t[k]) for k in ('scheduled_clean_seconds','effective_clean_seconds','effective_clean_rate','delay_summary')})
                cohort['candidate_tables'].append({'candidate_id':candidate,'stratum':layer,
                    'profile_status':'calibrated' if t['profile_status']=='success' else 'inconclusive',
                    'metrics':measures,'gates':[],'qualified':False})
                for series in SERIES:
                    cells=t['incident_slices'] if series=='incident-recall' else t['score_slices']
                    cohort['diagnostic_series'][series].extend(_mapped_slice(t,cell,series) for cell in cells)
                cohort['diagnostic_details'].append({'candidate_id':candidate,'stratum':layer,
                    **{k:copy.deepcopy(t[k]) for k in ('delay_histogram','profile_diagnostics','undefined_input_points','equipment_context')},
                    'incident_histograms':[{k:copy.deepcopy(c[k]) for k in ('dimension','key','delay_histogram')} for c in t['incident_slices']],
                    'score_reference_coverage':[{k:c[k] for k in ('dimension','key','planned','observed','unscored_target','outside_test')} for c in t['score_slices']]})
        cohorts.append(cohort)
    report={**QUIET,'format':'anomaly-v03-dev-smoke-descriptive-report-v1','scope':'saved-dev-smoke-descriptive-only',
        'cohorts':cohorts,'column_mapping':copy.deepcopy(MAPPING),'bootstrap_replicates':0,
        'limitations':['descriptive historical saved results; no present raw-payload attestation',
                       'schema component checks only; no formal population/source/runtime/CI/gate acceptance'],
        'formal_readiness':copy.deepcopy(source['readiness'])}
    validate_report(report,source,schema)
    return report


def validate_report(report,source,schema):
    """Check each emitted cell against its authenticated source and schema."""
    inputs.fields(report,QUIET,'report boundary')
    inputs.exact(report['scope'],'saved-dev-smoke-descriptive-only','report scope')
    inputs.exact(report['bootstrap_replicates'],0,'no bootstrap execution')
    inputs.exact(report['column_mapping'],MAPPING,'explicit column meanings')
    inputs.exact(report['formal_readiness'],source['readiness'],'readiness preserved')
    inputs.exact([c['role'] for c in report['cohorts']],['dev','smoke'],'cohort inventory')
    tables=_source_tables(source);primary_count=0;slice_count=0
    for cohort in report['cohorts']:
        role=cohort['role'];inputs.exact(cohort['seed_count'],8 if role=='dev' else 2,'report seed count')
        inputs.exact(cohort['evaluations'],576 if role=='dev' else 144,'report evaluation count')
        expected=[(c,s) for c in arithmetic.CANDIDATES for s in arithmetic.STRATA]
        shaped={**schema['properties']['candidate_tables'],'$defs':schema['$defs']}
        contract._shape(cohort['candidate_tables'],shaped)
        mapped=inputs.index(cohort['candidate_tables'],('candidate_id','stratum'),expected)
        details=inputs.index(cohort['diagnostic_details'],('candidate_id','stratum'),expected)
        for key in ('candidate_tables','diagnostic_details'):
            inputs.exact([[r['candidate_id'],r['stratum']] for r in cohort[key]],[list(k) for k in expected],'ordered candidate tables')
        inputs.exact(sorted(cohort['diagnostic_series']),sorted(SERIES),'named diagnostic families')
        for series,rows in cohort['diagnostic_series'].items():
            contract._shape(rows,{**schema['properties']['slices'],'$defs':schema['$defs']})
            contract._reported_slices(rows,uncomputed_ci=True)
            field='incident_slices' if series=='incident-recall' else 'score_slices'
            expected_keys=[(c,s,cell['dimension'],cell['key']) for c,s in expected for cell in tables[role,c,s][field]]
            indexed=inputs.index(rows,('candidate_id','stratum','dimension','key'),expected_keys)
            inputs.exact([[r[k] for k in ('candidate_id','stratum','dimension','key')] for r in rows],
                         [list(k) for k in expected_keys],'ordered diagnostic cells')
            for c,s in expected:
                for cell in tables[role,c,s][field]:
                    row=indexed[c,s,cell['dimension'],cell['key']]
                    n=cell[SERIES[series]];d=cell['planned'] if series=='incident-recall' else cell['observed']
                    inputs.exact([row['planned_count'],row['actual_count']],[cell['planned'],n],'mapped planned/actual')
                    inputs.exact(row['metric'],metric(n,d),'mapped ratio/denominator')
                    inputs.exact(row['delay_summary'],cell['delay_summary'] if series=='incident-recall' else None,'mapped incident delay')
            slice_count+=len(rows)
        for candidate,layer in expected:
            t=tables[role,candidate,layer];mapped_table=mapped[candidate,layer];m=mapped_table['metrics'];detail=details[candidate,layer]
            contract._reported_metrics(m,datasets=t['evaluations'])
            inputs.exact(mapped_table['profile_status'],'calibrated' if t['profile_status']=='success' else 'inconclusive','profile state')
            inputs.exact(mapped_table['gates'],[],'no gates');inputs.exact(mapped_table['qualified'],False,'no qualification')
            for k in arithmetic.METRICS:
                mapped_metric=next(a['metric'] for a in m['availability'] if a['full_target']==k.split(':',1)[1]) if k.startswith('availability:') else m[k]
                inputs.exact(mapped_metric,metric(*t['counts'][k],k,primary=True),'mapped primary count and units')
                primary_count+=1
            for k in ('scheduled_clean_seconds','effective_clean_seconds','effective_clean_rate','delay_summary'):
                inputs.exact(m[k],t[k],'mapped diagnostic')
            for k in ('delay_histogram','profile_diagnostics','undefined_input_points','equipment_context'):
                inputs.exact(detail[k],t[k],'retained sidecar diagnostic')
            inputs.exact(detail['incident_histograms'],[{k:cell[k] for k in ('dimension','key','delay_histogram')} for cell in t['incident_slices']],'retained incident histogram')
            inputs.exact(detail['score_reference_coverage'],[{k:cell[k] for k in ('dimension','key','planned','observed','unscored_target','outside_test')} for cell in t['score_slices']],'retained offset omissions')
    return {'status':'descriptive_report_cells_verified','cohorts':2,'candidate_tables':18,
            'primary_metrics':primary_count,'diagnostic_rows':slice_count,'schema_components_validated':True,
            'formal_schema_validated':False,'performance_status':'not_evaluated'}


def authenticate_report(input_savepoint,root_sha256,schema_path):
    """Read only a pinned input bundle and frozen schema, never raw evaluations."""
    manifest_path=paths.regular_path(input_savepoint);used={}
    def read(path,pin,maximum=1024**2):
        raw=read_pinned(path,pin,maximum);used[str(path)]=dict(pin);return scores.strict_json(raw)
    pin={'bytes':manifest_path.stat().st_size,'sha256':root_sha256}
    manifest=read(manifest_path,pin)
    inputs.fields(manifest,{'status':'authenticated_analysis_inputs_completed','evaluations':720,
        'formal_permission':False,'promotion_allowed':False,'selected_candidate':None,'formal_document_emitted':False},'input savepoint')
    inputs.exact(manifest['analysis_inputs_pin'],manifest['artifacts']['analysis-inputs.json'],'bundle pin binding')
    source=read(manifest_path.parent/'analysis-inputs.json',manifest['analysis_inputs_pin'],16*1024**2)
    schema=read(paths.regular_path(schema_path),manifest['code_pins'][inputs.SCHEMA])
    project=Path(__file__).resolve().parents[2]
    for name in ('anomaly_v03_analysis_inputs.py','anomaly_v03_slices.py','anomaly_v03.py','anomaly_v03_inference_audit.py'):
        relative='src/banto_ai/'+name;read_pinned(project/relative,manifest['code_pins'][relative],1024**2)
    result=build_report(source,schema)
    result['authentication']={'trust_anchor':{'path':str(manifest_path),**pin},'files':used,'source_payload_bytes_read':0}
    return result,validate_report(result,source,schema)


def display(value,*,percent=False):
    return '—' if value is None else (f'{100*value:.2f}%' if percent else f'{value:.3f}')


def summary_markdown(report):
    rows=['# Banto AI 開発用・動作確認用の評価結果','',
          '保存済み720評価の記述集計です。信頼区間・正式性能判定・候補採択は未実施です。',
          'C0＝差分基準、C1＝運転段階別正常値、C2＝運転段階別の条件付き正常値。',
          'core＝基本条件、quality-stress＝品質劣化を重ねた条件、overall＝両条件の合計。','']
    for cohort in report['cohorts']:
        rows += [f"## {'開発用' if cohort['role']=='dev' else '動作確認用'}：{cohort['seed_count']} seed・{cohort['evaluations']}評価",'',
                 '| 候補 | 条件 | 機械検出率 | センサー検出率 | 警報正解率 | 正常時警報/8設備時間 | 誤警報/予定異常100件 | 検出数 | 遅延中央値 秒 |',
                 '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for t in cohort['candidate_tables']:
            m=t['metrics'];d=m['delay_summary']
            rows.append(f"| {t['candidate_id'][:2].upper()} | {t['stratum']} | "+' | '.join(display(m[k]['value'],percent=True) for k in ('machine_recall','sensor_recall','precision'))+
                        f" | {display(m['clean_rate']['value'])} | {display(m['false_alert_burden']['value'])} | {d['count']} | {display(d['median'])} |")
        rows+=['']
    rows += ['遅延は検出できた事例だけの値です。「—」は分母0または検出0で値が定まらない項目で、0ではありません。',
             'overallは両条件の合計で、追加評価ではありません。比率や中央値は元の件数・度数から計算しています。','',
             '[全条件別表を開く](report.html)／[全数値JSON](report.json)','',
             'JSONは用途ごとに9結果表と4種類の診断表を保存します。検出率・利用可能率・閾値超過率・信号警報開始率を区別し、対象外/試験外参照、遅延度数、品質・profile診断も保持しています。','']
    return '\n'.join(rows)


def detailed_html(report):
    """Dependency-free, escaped static HTML with native collapsible tables."""
    def table(headers,rows):
        return '<table><thead><tr>'+''.join('<th>'+escape(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join(
            '<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table>'
    output=['<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>Banto AI 条件別結果</title><style>body{font:16px system-ui;max-width:1440px;margin:32px auto;padding:0 16px;color:#172536;background:#fafcff}h1,h2{color:#123d62}details{background:white;border:1px solid #cad7e1;border-radius:6px;padding:12px;margin:14px 0}summary{font-weight:650;cursor:pointer}table{border-collapse:collapse;font-size:13px;width:100%;margin:14px 0}td,th{border:1px solid #dce4eb;padding:7px;text-align:right}th{background:#eaf2f8}td:first-child,th:first-child{text-align:left}.scroll{overflow:auto}p{line-height:1.65}caption{text-align:left}</style>',
        '<h1>Banto AI 条件別結果</h1><p>保存済み720評価の記述集計。信頼区間・正式性能判定・候補採択は未実施です。用途・候補・条件ごとに表を展開できます。</p>',
        '<p>core＝基本条件、quality-stress＝品質劣化を重ねた条件、overall＝両条件の合計。「—」は値が定まりません。遅延は検出できた事例のみ。</p>',
        '<p>発生前後の参照は同じscoreが重複する場合があります。score対象外と試験時間外を分け、残る試験内の予定行を各率の分母にします。閾値超過は時刻数、警報開始は連続条件が成立した回数です。</p>']
    for cohort in report['cohorts']:
        output.append(f"<h2>{'開発用' if cohort['role']=='dev' else '動作確認用'} — {cohort['seed_count']} seed / {cohort['evaluations']}評価</h2>")
        for t,sidecar in zip(cohort['candidate_tables'],cohort['diagnostic_details']):
            candidate,layer=t['candidate_id'],t['stratum'];m=t['metrics']
            output.append('<details><summary>'+escape(candidate+' / '+layer)+'</summary><div class="scroll">')
            output.append(table(['指標','分子','分母','値'],[[k,m[k]['numerator'],m[k]['denominator'],display(m[k]['value'],percent=k not in ('clean_rate','false_alert_burden'))] for k in arithmetic.METRICS[:5]]))
            output.append('<p>clean_rateの単位は8設備時間当たり、false_alert_burdenは予定異常100件当たり。</p>')
            select=lambda name:[r for r in cohort['diagnostic_series'][name] if (r['candidate_id'],r['stratum'])==(candidate,layer)]
            output.append('<h3>異常事例の条件別検出率</h3>')
            output.append(table(['分類','条件','検出','予定','検出率','遅延中央値 秒','遅延平均 秒'],
                [[r['dimension'],r['key'],r['actual_count'],r['planned_count'],display(r['metric']['value'],percent=True),display(r['delay_summary']['median']),display(r['delay_summary']['mean'])] for r in select('incident-recall')]))
            groups=[select(name) for name in list(SERIES)[1:]]
            output.append('<h3>scoreの品質・時刻・運転条件別診断</h3>')
            output.append(table(['分類','条件','予定参照','試験内行','対象外','試験外','利用可能','利用可能率','超過時刻','超過率','警報開始','開始率'],
                [[a['dimension'],a['key'],ref['planned'],ref['observed'],ref['unscored_target'],ref['outside_test'],
                  a['actual_count'],display(a['metric']['value'],percent=True),b['actual_count'],display(b['metric']['value'],percent=True),
                  c['actual_count'],display(c['metric']['value'],percent=True)] for a,b,c,ref in zip(*groups,sidecar['score_reference_coverage'])]))
            output.append('<p>qualityは当該target自身の依存観測品質。overlapは同じtargetの有効quality区間と交差する正例の判定窓全体です。contextは設備全体の計画event区間によります。</p></div></details>')
    output.append('<p>全数値・分母・診断記録は同じフォルダーのreport.jsonに保存しています。正式40 holdoutの解析やsource/runtime受入を完了した報告ではありません。</p></html>')
    return '\n'.join(output)
