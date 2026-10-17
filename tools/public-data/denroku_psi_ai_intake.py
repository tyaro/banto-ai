"""Pin existing PSI source read-only and amend the local integration plan."""
import hashlib,io,json,re,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(Path(__file__).parent))
from metropt_multiday import Files,digest
from verification_records import EvidenceStore
from macos_demand_runtime import MacCheckpoint
from care_rust_r0_close import verify_evidence
NOTE='docs/research/denroku-psi-ai-integration-2026-10-16.md'
PLAN='docs/research/banto-ai-rust-implementation-plan-2026-10-16.md'
def main():
    out=Files(ROOT/'artifacts/denroku-psi-ai-intake2-20261016');check=MacCheckpoint(seconds=870);status='failed'
    evidence=ROOT/'artifacts/denroku-psi-ai-intake2-20261016-evidence'
    try:
        payload=json.loads(Path('/private/tmp/denroku-psi-readonly-20261016.json').read_bytes())
        assert payload['commit']=='816fbdaec722008193b3945db7f4599d1a8a64b7'
        out.json('phase.json',{'scope':'read-only source inspection and integration plan amendment','repository':payload['repository'],'visibility':'private','commit':payload['commit'],'no_customer_data_model_or_prediction_payload':True,'repository_changes_training_forward_build':False})
        out.sources([Path(__file__),ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/verification_records.py',ROOT/'tools/macos_demand_runtime.py',ROOT/'tools/public-data/care_rust_r0_close.py'])
        blobs={x['path']:x for x in payload['tree']['tree'] if x['type']=='blob'}
        bundle=io.BytesIO();pins=[]
        with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
            for f in payload['files']:
                path=f['path'];raw=f['content'].encode()
                assert path.endswith(('.py','.rs','.toml','.md','.ts')) or path.endswith('/feature-definition.json')
                gitsha=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                assert gitsha==blobs[path]['sha'] and len(raw)==blobs[path]['size']
                z.writestr(path,raw);pins.append({'path':path,'bytes':len(raw),'git_blob_sha':gitsha,'sha256':hashlib.sha256(raw).hexdigest(),'url':'https://github.com/tyaro/denroku-psi-demo/blob/'+payload['commit']+'/'+path})
        assert len(pins)==13
        out.write('private-source.zip',bundle.getvalue());out.json('source-pins.json',pins)
        out.json('tree.json',payload['tree'])
        configs=['examples/configs/rust-small-forecaster-r0-20261016.json','examples/configs/rust-small-forecaster-r0-20261016-r0.1.json','examples/configs/care-a-maintenance-20261016-r1.json']
        cfgpins={p:digest(ROOT/p) for p in configs}
        section='## 需要とPSIの既存実装を接続例に加える（2026-10-16）\n\n[denroku-psi-demoの現状と引継ぎ](denroku-psi-ai-integration-2026-10-16.md)を確認した。現状はPython LightGBM学習→Rust推論/照合→静的JSON→画面/PSIで、Python不要の再学習は公式C APIを使う別の未実装計画がある。共通AIの配置はbanto-ai、利用側は産業のbanto-industrialと需要・PSIアプリ。各利用側→banto-aiの依存方向を守る。\n\nR1/R2は自作SmallForecasterを先行する。既存LightGBMの特徴量・木推論・Python不要学習を同一engineへ押し込まず、共通化はmodel版/来歴/数量の意味/進捗・保存等の境界から行う。需要26週の出荷点予測と産業32stepの分位点を区別し、PSI/受注採用判断は利用側へ残す。R0.1の数値契約は不変。需要側のfixture利用・LightGBM移行・平均モデル比較は別工程で仕様と範囲を固定する。\n\n'
        changes={}
        changes[NOTE]=(ROOT/NOTE).read_text().replace('artifacts/denroku-psi-ai-intake-20261016','artifacts/denroku-psi-ai-intake2-20261016')+'\n保存処理の初回はsource許可拡張子にTypeScriptを含め忘れて停止した。失敗root/stdio/exit/sourceを保持し、source種別だけを修正してfresh rootへ保存した。相手のsourceや実行条件は変更していない。\n'
        p=ROOT/PLAN;text=p.read_text()
        text=text.replace('AI本体の実装は **tyaro/banto-ai** に置く。**tyaro/banto-industrial** はその利用側とし、依存方向を **banto-industrial → banto-ai** に固定する。','AI本体の実装は **tyaro/banto-ai** に置く。産業側は **tyaro/banto-industrial**、需要・PSI側は既存の **denroku-psi-demo** を接続例とする。各利用側がbanto-aiへ依存し、共通AI側はアプリへ逆依存しない。現時点で両アプリから共通crateを利用済みという意味ではない。')
        text=text.replace('## 現在ある成果を使う\n',section+'## 現在ある成果を使う\n',1)
        text=text.replace('| 5 | R4a 製品adapter |','| 5 | R4a 産業/需要の製品adapter |')
        text=text.replace('banto-industrialはversion/tag/commitを固定してbanto-ai crateを利用する。','利用側はversion/tag/commitを固定してbanto-ai crateを利用する。産業側はbanto-industrial、需要・PSI側はdenroku-psi-demoの既存Python学習/Rust推論経路を接続例とする。需要側では現行予測JSONとの互換を先に固定し、LightGBMから自作モデルへの置換やPython不要学習は別の有限工程として扱う。')
        changes[PLAN]=text
        for name in ['docs/research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md','docs/research/timesfm-inspired-dual-domain-plan-2026-10-16.md']:
            parts=(ROOT/name).read_text().split('\n',2);changes[name]=parts[0]+'\n\n'+section+parts[2]
        name='docs/research/research-roadmap.md'
        changes[name]=section+'---\n\n'+(ROOT/name).read_text()
        name='docs/research/README.md'
        changes[name]=(ROOT/name).read_text().replace('## 文書\n','## 文書\n\n- [denroku-psi-demoの需要AIとPSI接続の現状](denroku-psi-ai-integration-2026-10-16.md) — Python LightGBM学習/Rust推論/静的PSIと、未実装のC API再学習計画。AI crate共通化の境界を整理。\n',1)
        name='docs/current-handoff.md'
        changes[name]='## 最新 — 需要・PSI側の既存AI実装を計画へ反映（2026-10-16）\n\n人のdenroku-psi-demoの実装紹介に対応し、[現状確認と引継ぎ](research/denroku-psi-ai-integration-2026-10-16.md)・[実装計画](research/banto-ai-rust-implementation-plan-2026-10-16.md)へ反映。private repo main816fbdaec722008193b3945db7f4599d1a8a64b7の13 source/仕様をGit blob照合。PythonでLightGBM学習、Rust probeで木JSON推論/特徴量/再帰/丸めを照合し、一致後に静的画面JSONを出す既存経路。アプリ内学習や定期再学習は未実装、LightGBM C APIを使う別計画がある。\n\nAI本体はbanto-ai、利用側はbanto-industrialと需要/PSIアプリ。R1/R2は自作SmallForecasterを先に進め、LightGBMとの共通化はmodel版/来歴/進捗/数量意味等の境界から。18列の木モデルと3系列tensorモデル、需要26週/産業32step、点予測/平均/分位点を混同しない。PSIと受注採用判断は利用側へ残し、現行モデルを自動置換しない。\n\n今回はsource/仕様読取りと計画更新だけ。source原文/tree/hashはgitignore対象の artifacts/denroku-psi-ai-intake-20261016 にのみ保存し、データ/学習済みmodel/予測値payloadは取得なし。相手repo変更、build/依存追加/学習/forward/2015再評価0。旧R0.1/CARE契約・成果、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離、OS分離・heartbeat PAUSED維持。全source/stdio/exit/phase/closureと文書前後は同名records/EvidenceStoreへ保存。次は既定のR1a/R1b。以下は旧記録。\n\n---\n\n'+(ROOT/name).read_text()
        note=(ROOT/NOTE).read_text()
        for name in re.findall(r'\]\(([^)]+)\)',note):
            if name.startswith(('https://','http://','#')):continue
            assert ((ROOT/NOTE).parent/name).exists()
        with EvidenceStore(evidence) as store:
            store.write_bytes('source',Path(__file__).read_bytes());store.write_bytes('private-source',bundle.getvalue());store.write_json('source-pins',pins);store.write_json('phase',json.loads((out.root/'phase.json').read_bytes()))
            store.write_bytes('integration-note',(ROOT/NOTE).read_bytes())
            before=[]
            for i,name in enumerate(changes):
                p=ROOT/name;store.write_bytes(f'before-{i}',p.read_bytes());before.append({'path':name,'sha256':digest(p)})
            store.write_json('before-index',before)
            for name,text in changes.items():(ROOT/name).write_text(text)
            after=[]
            for i,name in enumerate(changes):
                p=ROOT/name;store.write_bytes(f'after-{i}',p.read_bytes());after.append({'path':name,'sha256':digest(p)})
            store.write_json('after-index',after)
            assert {p:digest(ROOT/p) for p in configs}==cfgpins
            assert 'denroku-psi-ai-integration-2026-10-16.md' in (ROOT/PLAN).read_text()
            summary={'status':'complete','source_files_verified':13,'source_repository_changed':False,'data_model_prediction_payloads_read':0,'source_code_executed':False,'new_model_or_training_runs':0,'numerical_configs_unchanged':True,'plan_updated':PLAN,'resources':check.check()}
            store.write_json('summary',summary);store.write_terminal('terminal',{'exit':0,'state':'complete','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'));out.json('summary.json',summary)
        print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
