"""Correct repository ownership only; preserve frozen R0 and numerical evidence."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(Path(__file__).parent))
from metropt_multiday import Files,digest
from verification_records import EvidenceStore
from macos_demand_runtime import MacCheckpoint
from care_rust_r0_close import verify_evidence
OLD='examples/configs/rust-small-forecaster-r0-20261016.json'
NEW='examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
DOC='docs/research/rust-small-forecaster-r0-2026-10-16.md'
NOTE='AI本体のRustクレートは tyaro/banto-ai 側に置き、tyaro/banto-industrial は利用・接続先とする。前回の「移植先」は接続先の意味であり、AI実装の配置先に読み替えない。'
def main():
    out=Files(ROOT/'artifacts/rust-crate-ownership-correction-20261016');check=MacCheckpoint(seconds=870);status='failed'
    evidence=ROOT/'artifacts/rust-crate-ownership-correction-20261016-evidence'
    try:
        out.json('phase.json',{'scope':'repository ownership documentation correction only','human_correction':NOTE,'old_frozen_config_preserved':True,'training_forward_build_install':False})
        out.sources([Path(__file__),ROOT/'tools/verification_records.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/public-data/care_rust_r0_close.py',ROOT/'tools/macos_demand_runtime.py'])
        frozen=load_old=json.loads((ROOT/OLD).read_bytes());oldsha=digest(ROOT/OLD)
        cfg=json.loads(json.dumps(frozen));cfg['id']='RUST-SF-20261016-r0.1'
        cfg['supersedes']={'id':frozen['id'],'path':OLD,'sha256':oldsha,'change':'repository ownership and dependency direction only; scientific/numerical contract unchanged'}
        cfg['implementation']={'repository':'tyaro/banto-ai','local_checkout':str(ROOT),'crate_path_proposed':'crates/banto-ai','crate_status':'planned; not yet created','responsibility':['preprocessing and portable input validation','model and quantile heads','loss/backward/AdamW training','model and optimizer checkpoint/resume','portable library API and reference CLI'],'forbidden_dependencies':['banto-industrial workspace or application DTOs','banto-tagclient','banto-tsquery','Tauri','Windows service or PLC APIs'],'boundary':'application converts its types to portable AI input; core must not import application types'}
        cfg['target']['role']='downstream consumer/integration target; not AI crate implementation repository'
        cfg['dependency_direction']='tyaro/banto-industrial -> version/commit-pinned Rust crate from tyaro/banto-ai; never reverse'
        cfg['adapter']['ownership']='application DTO conversion, acquisition/history and job hosting/activation policy belong to banto-industrial; portable AI training/inference/checkpoint belong to banto-ai'
        cfg['backend']['production_toolchain']='AI crate toolchain and MSRV declared in banto-ai; downstream integration additionally verifies banto-industrial pinned 1.98.1'
        cfg['gates'][0]['scope']=cfg['gates'][0]['scope'].replace('isolated research crate','crate at tyaro/banto-ai:crates/banto-ai (isolated build first)')
        cfg['gates'][3]['scope']='banto-industrial consumes pinned banto-ai crate; adapter and job/model integration compile with downstream pinned toolchain; Windows OS-specific checks separately'
        paragraph='## 実装の所属と依存方向 — 人の訂正（2026-10-16）\n\n'+NOTE+'\n\n- **banto-ai**: 前処理、モデル、学習/loss/backward/AdamW、推論、モデル・optimizer checkpointと再開、共通Rust API/参照CLIを持つ。R1で作成するクレートの配置案はこのrepositoryの '+chr(96)+'crates/banto-ai'+chr(96)+'。当面一つのクレート内でmoduleを分け、必要が生じた段階で分割する。今回はクレート未作成。\n- **banto-industrial**: タグ・履歴の取得と型変換、quality/time/unit policyの適用、学習jobのhost、UI、モデルの利用/切替を持つ。AI本体の実装をここへ移さない。\n- **依存方向**: banto-industrial → banto-ai。利用時のversion/tag/commitを固定し、共通AI crateは製品DTO、banto-tagclient/tsquery、Tauri/PLC/Windows機能へ依存させない。実機固有の対応はadapterで処理する。\n\n[現行機械設定r0.1](../../'+NEW+')。旧r0 JSONと閉鎖artifactは不変の履歴として残す。数値・モデル・optimizer・参照pin・許容差・評価条件は変更しない。banto-industrial 1.98.1の確認は下流統合の条件であり、AIクレートを同repository内に置く理由ではない。\n\n'
        changes={}
        p=ROOT/DOC;s=p.read_text().replace('[機械設定](../../'+OLD+')','[機械設定r0.1](../../'+NEW+')')
        s=s.replace('人が移植先として **banto-industrial** を指定した。','人が**利用・接続先として banto-industrial** を指定した。AI本体はbanto-ai側のRustクレートとする（下記訂正を優先）。')
        s=s.replace('## 目的と今回の境界\n',paragraph+'## 目的と今回の境界\n',1)
        s=s.replace('研究repo内の孤立crateでexact dependency','banto-ai内の '+chr(96)+'crates/banto-ai'+chr(96)+' を最初は単独buildし、exact dependency')
        changes[DOC]=s
        shared='## 配置方針の訂正 — AIクレートはbanto-ai（2026-10-16）\n\n'+NOTE+' 共通AI crateの配置案は '+chr(96)+'crates/banto-ai'+chr(96)+'、製品型/取得処理/jobのhost/UIはbanto-industrial側のadapterに置く。依存方向はbanto-industrial → banto-ai。学習・保存再開もAI側の範囲であり、推論だけに縮小しない。[現行R0契約](rust-small-forecaster-r0-2026-10-16.md)と[機械設定r0.1](../../'+NEW+')へ反映。数値/評価条件は不変、Rust実装・buildはまだ開始していない。以下の移植先という旧表現は接続先を指す履歴として読む。\n\n'
        for name in ['docs/research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md','docs/research/timesfm-inspired-dual-domain-plan-2026-10-16.md']:
            parts=(ROOT/name).read_text().split('\n',2);changes[name]=parts[0]+'\n\n'+shared+parts[2]
        roadmap='docs/research/research-roadmap.md';changes[roadmap]=shared+'---\n\n'+(ROOT/roadmap).read_text()
        handoff='docs/current-handoff.md'
        changes[handoff]='## 最新 — AIクレートはbanto-ai、banto-industrialは利用側（2026-10-16・人の訂正）\n\n'+NOTE+' 前の回答で配置先と接続先を混同したため訂正。[R0契約](research/rust-small-forecaster-r0-2026-10-16.md)と[現行設定r0.1](../'+NEW+')を優先する。\n\nbanto-aiに前処理/model/forward/loss/backward/AdamW/学習・保存再開/共通Rust APIを置く。R1作成予定はこのcheckoutの '+chr(96)+'crates/banto-ai'+chr(96)+'。banto-industrialは製品DTO・履歴/タグ取得adapterとjobのhost/UI/利用切替を持ち、pinしたbanto-ai crateを使う。共通AI側を製品repo/Tauri/PLCへ逆依存させない。両repoにAI本体を重複実装しない。\n\n今回は配置/責務/依存方向だけを文書と派生設定へ反映。旧r0/closed roots/数値/参照/許容差/CARE結果は不変。新crate/build/fit/forward/2015再評価0。既存の次工程R1と資源/OS/需要条件、heartbeat PAUSED維持。文書前後と変更理由を '+chr(96)+'artifacts/rust-crate-ownership-correction-20261016-evidence'+chr(96)+' に保存。以下は旧記録で、旧「移植先」の表現より本訂正を優先する。\n\n---\n\n'+(ROOT/handoff).read_text()
        report='docs/results/care-saved-diagnostics-rust-r0-2026-10-16.md'
        parts=(ROOT/report).read_text().split('\n',2)
        changes[report]=parts[0]+'\n\n配置の追補（人の訂正）: AI本体のRustクレートはbanto-ai側、banto-industrialは利用・接続先。以下の「移植先」は接続先を指す。[現行R0契約](../research/rust-small-forecaster-r0-2026-10-16.md)を優先する。CARE結果・数値条件は不変。\n\n'+parts[2]
        index='docs/research/README.md';changes[index]=(ROOT/index).read_text().replace('## 文書\n','## 文書\n\n- [Rust R0配置の訂正](rust-small-forecaster-r0-2026-10-16.md) — AIの学習・推論クレートはbanto-ai、banto-industrialは利用adapter。依存方向を固定、数値条件は不変。\n',1)
        with EvidenceStore(evidence) as store:
            store.write_bytes('source',Path(__file__).read_bytes());store.write_bytes('old-config', (ROOT/OLD).read_bytes())
            store.write_json('phase',json.loads((out.root/'phase.json').read_bytes()))
            before=[]
            for i,name in enumerate(changes):
                p=ROOT/name;store.write_bytes(f'before-{i}',p.read_bytes());before.append({'path':name,'sha256':digest(p)})
            store.write_json('before-index',before)
            with (ROOT/NEW).open('x') as f:json.dump(cfg,f,ensure_ascii=False,indent=2);f.write('\n')
            for name,text in changes.items():(ROOT/name).write_text(text)
            after=[]
            for i,name in enumerate([*changes,NEW]):
                p=ROOT/name;store.write_bytes(f'after-{i}',p.read_bytes());after.append({'path':name,'sha256':digest(p)})
            store.write_json('after-index',after)
            actual=json.loads((ROOT/NEW).read_bytes())
            assert actual['implementation']['repository']=='tyaro/banto-ai'
            assert actual['target']['repository']=='tyaro/banto-industrial'
            assert digest(ROOT/OLD)==oldsha
            for key in ['model','references','optimizer','tolerance','execution_limits']:
                assert actual[key]==frozen[key],key
            assert not (ROOT/'crates/banto-ai').exists()
            assert NEW in (ROOT/DOC).read_text() and NEW in (ROOT/handoff).read_text()
            summary={'status':'complete','ai_crate_repository':'tyaro/banto-ai','consumer_repository':'tyaro/banto-industrial','dependency_direction':'banto-industrial -> banto-ai','old_r0_sha256_unchanged':oldsha,'numerical_contract_unchanged':True,'crate_created':False,'build_training_forward_runs':0,'resources':check.check()}
            store.write_json('summary',summary);store.write_terminal('terminal',{'exit':0,'state':'complete','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'))
        out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
