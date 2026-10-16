"""Save the requested implementation plan and update repository entry points."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'models/mini-transformer'));sys.path.insert(0,str(Path(__file__).parent))
from verification_records import EvidenceStore
from metropt_multiday import Files,digest
from macos_demand_runtime import MacCheckpoint
from care_rust_r0_close import verify_evidence
PLAN='docs/research/banto-ai-rust-implementation-plan-2026-10-16.md'
def main():
    out=Files(ROOT/'artifacts/banto-ai-rust-implementation-plan-20261016');status='failed';check=MacCheckpoint(seconds=870)
    evidence=ROOT/'artifacts/banto-ai-rust-implementation-plan-20261016-evidence'
    try:
        phase={'id':'BANTO-AI-RUST-PLAN-20261016-v1','scope':'plan and entry-point documentation only','user_request':'計画を立ててください','crate_implementation_repository':'tyaro/banto-ai','consumer_repository':'tyaro/banto-industrial','training_forward_compile_install':False}
        out.json('phase.json',phase);out.sources([Path(__file__),ROOT/'tools/verification_records.py',ROOT/'models/mini-transformer/metropt_multiday.py',ROOT/'tools/macos_demand_runtime.py',ROOT/'tools/public-data/care_rust_r0_close.py'])
        config=ROOT/'examples/configs/rust-small-forecaster-r0-20261016-r0.1.json'
        frozen=digest(config);original=digest(ROOT/'examples/configs/rust-small-forecaster-r0-20261016.json')
        changes={}
        h='docs/current-handoff.md'
        changes[h]='## 最新 — banto-aiのRustクレート実装計画を保存（2026-10-16）\n\n人の計画依頼に対応し、[実装計画](research/banto-ai-rust-implementation-plan-2026-10-16.md)を現在の工程順とする。AI本体はbanto-aiの '+chr(96)+'crates/banto-ai'+chr(96)+'、banto-industrialはpinしたcrateを利用する。依存方向は利用側→AI側。前処理/forwardに加え、loss/backward/AdamW/保存再開までAI側の範囲。\n\n順序はR1a CPU build/依存・子孫資源監視→R1b固定2batchの推論比較→R2有限1/8更新と4+4再開→R3 CAREの保存modelと全5fold有限学習比較→R4 adapter/製品job接続→OS/配布検証。各段階の成果物・合格/停止条件を明記し、通過後に同種確認を無目的に増やさない。R3の長期数値条件は実行前に別固定する。業務の先行時間/誤警報許容は製品採用の別条件とし、未定でもcoreは進められる。\n\n今回plan/docsのみ、crate作成/build/依存導入/学習/forward/CARE採点/2015再評価0。R0.1数値条件と旧closed roots不変、需要調整2014以前/同休業mean28/四季両側非増加/観測と欠測0分離、Windows別検証・heartbeat PAUSED維持。次の実装範囲はR1a/R1b。文書前後・source/stdio/exit/closureは '+chr(96)+'artifacts/banto-ai-rust-implementation-plan-20261016-evidence'+chr(96)+' と実行recordsへ保存。以下は旧記録。\n\n---\n\n'+(ROOT/h).read_text()
        for name in ['docs/research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md','docs/research/timesfm-inspired-dual-domain-plan-2026-10-16.md']:
            old=(ROOT/name).read_text();parts=old.split('\n',2)
            changes[name]=parts[0]+'\n\n## Rust実装の現在の計画（2026-10-16）\n\n[AIクレート実装と製品利用の計画](banto-ai-rust-implementation-plan-2026-10-16.md)に従い、banto-ai内のR1a/R1bから学習・保存再開、有限CARE比較、banto-industrial接続へ段階的に進める。各段階の合格/停止条件と責務を固定した。今回実装/学習は開始せず、[R0.1数値契約](rust-small-forecaster-r0-2026-10-16.md)は不変。\n\n'+parts[2]
        name='docs/research/research-roadmap.md'
        changes[name]='## 現在の着手順 — banto-aiのRust実装計画（2026-10-16）\n\n[計画](banto-ai-rust-implementation-plan-2026-10-16.md)を現在の実装順とする。R1a単独CPU build/依存/子孫資源観測、R1b固定forward、R2学習・保存再開、R3 CARE有限移植比較、R4製品接続/OS/配布、用途受入。AI本体はbanto-ai、banto-industrialは利用側。今回は計画のみで新build/学習/予測0。R0数値条件/既読評価/需要停止条件と旧証跡を維持。以下は旧記録。\n\n---\n\n'+(ROOT/name).read_text()
        name='docs/research/README.md'
        changes[name]=(ROOT/name).read_text().replace('## 文書\n','## 文書\n\n- [banto-aiのRustクレート実装と製品利用の計画](banto-ai-rust-implementation-plan-2026-10-16.md) — AI側に学習/推論/再開、利用側にadapter/job host。CPU buildから数値比較・有限CARE・製品/OS受入までの工程と終了条件。\n',1)
        name='docs/research/rust-small-forecaster-r0-2026-10-16.md'
        old=(ROOT/name).read_text();parts=old.split('\n',2)
        changes[name]=parts[0]+'\n\n[現在の実装計画](banto-ai-rust-implementation-plan-2026-10-16.md)を工程順・成果物・終了条件の入口とする。本R0はモデル/数値/配置の契約として継承する。\n\n'+parts[2]
        checked=[]
        text=(ROOT/PLAN).read_text()
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if target.startswith(('http://','https://','#')):continue
            p=(ROOT/PLAN).parent/target.split('#',1)[0];assert p.exists(),target;checked.append(target)
        for word in ['R1a','R1b','R2','R3','R4','banto-industrial → banto-ai','900秒/子870秒','2015再評価は停止']:assert word in text,word
        with EvidenceStore(evidence) as store:
            store.write_bytes('source',Path(__file__).read_bytes());store.write_json('phase',phase)
            store.write_bytes('plan',(ROOT/PLAN).read_bytes());store.write_bytes('inherited-contract',config.read_bytes())
            before=[]
            for i,name in enumerate(changes):
                p=ROOT/name;store.write_bytes(f'before-{i}',p.read_bytes());before.append({'path':name,'sha256':digest(p)})
            store.write_json('before-index',before)
            for name,text in changes.items():(ROOT/name).write_text(text)
            after=[]
            for i,name in enumerate(changes):
                p=ROOT/name;store.write_bytes(f'after-{i}',p.read_bytes());after.append({'path':name,'sha256':digest(p)})
            store.write_json('after-index',after)
            assert digest(config)==frozen and digest(ROOT/'examples/configs/rust-small-forecaster-r0-20261016.json')==original
            assert not (ROOT/'crates/banto-ai').exists()
            summary={'status':'complete','plan':PLAN,'plan_sha256':digest(ROOT/PLAN),'local_links_checked':checked,'inherited_contract_unchanged':True,'new_crate_build_learning_forward':False,'documentation_files_updated':len(changes),'resources':check.check()}
            store.write_json('summary',summary);store.write_terminal('terminal',{'exit':0,'state':'complete','resources':check.check()})
        out.json('evidence-readback.json',verify_evidence(evidence,'complete'))
        out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)
if __name__=='__main__':main()
