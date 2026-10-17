"""Final integrity check with absolute paths; preserve the prior caller error."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'models/mini-transformer'),str(ROOT/'tools/public-data')]
from metropt_multiday import Files,digest,verify_closed
from care_rust_r0_close import verify_evidence
from macos_demand_runtime import MacCheckpoint
from rust_r1_publish_preparation import validate_root
from verification_records import EvidenceStore

def main():
    # The prior ad-hoc final caller passed a relative path to a helper whose
    # return value requires a repository-absolute path. No artifacts changed.
    failure_path=ROOT/'artifacts/rust-r1-context-final-caller-failure-20261016'
    if failure_path.exists():
        assert validate_root(failure_path)['status']=='failed'
        return final_check()
    failed=Files(failure_path)
    failed.sources([Path(__file__),ROOT/'tools/public-data/care_rust_r0_close.py'])
    failed.json('phase.json',{'scope':'post-publication read-only integrity caller','scientific_experiments':0,'reason':'relative Path passed to verify_evidence; its root.relative_to(ROOT) return formatting failed after content validation','resource_monitor_was_not_attached_to_original_ad_hoc_caller':True,'original_tool_exit_code':1})
    failed.write('stdout.txt',b'')
    failed.write('stderr.txt',b'''Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/Users/tyaromax/Documents/Codex/2026-10-14/yaro-banto-ai-mac-python-3/outputs/banto-ai-research/tools/public-data/care_rust_r0_close.py", line 30, in verify_evidence
    return {'root':str(root.relative_to(ROOT)),'status':expected,'parts_verified':len(actual),'bytes':sum(p.stat().st_size for p in root.iterdir()),'closure_sha256':digest(root/'root-closed.json')}
                       ~~~~~~~~~~~~~~~~^^^^^^
  File "/Users/tyaromax/Documents/Codex/2026-10-14/yaro-banto-ai-mac-python-3/outputs/python/cpython-3.14.8-macos-aarch64-none/lib/python3.14/pathlib/__init__.py", line 490, in relative_to
    raise ValueError(f"{str(self)!r} is not in the subpath of {str(other)!r}")
ValueError: 'artifacts/rust-r1-context-results-20261016-evidence' is not in the subpath of '/Users/tyaromax/Documents/Codex/2026-10-14/yaro-banto-ai-mac-python-3/outputs/banto-ai-research'
''')
    failed.json('state.json',{'artifact_mutations':False,'experiment_repeated':False,'repair':'Use ROOT / artifacts absolute paths in the new read-only caller.'});failed.close('failed')
    return final_check()

def final_check():
    out=Files(ROOT/'artifacts/rust-r1-context-final-integrity2-20261016');status='failed';check=MacCheckpoint(seconds=870)
    try:
        root=ROOT/'artifacts/rust-r1-context-results-20261016';verify_closed(root);verify_closed(ROOT/'artifacts/rust-r1-context-results-20261016-records');e=verify_evidence(ROOT/'artifacts/rust-r1-context-results-20261016-evidence','complete')
        resources=json.loads((root/'resources.json').read_bytes())
        old=ROOT/'artifacts/rust-r1-layer-comparison-20261016';verify_closed(old)
        # The original optional extraction used an absent family name 'linear'.
        # Preserve that closed empty extraction; select existing semantic groups.
        assert json.loads((root/'prior-linear-diagnosis.json').read_bytes())==[]
        linear=[r for r in json.loads((old/'node-comparisons.json').read_bytes()) if r['family'] in ['patch','attention_projection','attention_output_projection','ff_linear','head']]
        assert len(linear)==154
        failedpins=[validate_root(ROOT/'artifacts'/n) for n in ['rust-r1-context-final-caller-failure-20261016','rust-r1-context-final-integrity-20261016','rust-r1-context-final-integrity-20261016-records']]
        assert all(p['status']=='failed' for p in failedpins)
        summary={'result_records_evidence_verified':True,'model_sha256':digest(ROOT/'crates/banto-ai/src/model.rs'),'resource_maxima':{key:max(v['sampled_group_peak'][key] for v in resources.values()) for key in ['monitor_inclusive_footprint','monitor_inclusive_rss']},'cache_max_bytes':max(v['sampled_cache_bytes'] for v in resources.values()),'saved_linear_nodes':len(linear),'bookkeeping_only_repair':True,'new_scientific_experiments':0,'evidence':e,'resources':check.check()}
        assert summary['model_sha256']=='acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80'
        report=ROOT/'docs/results/banto-ai-rust-r1-context-normalization-2026-10-16.md';before=report.read_bytes()
        note='\n保存補足: 最終読取りcallerの相対pathエラーと、既存層別診断の抽出に存在しないfamily名linearを指定した空抽出を検出して保持した。前者は絶対path、後者は既存patch/attention_projection/attention_output_projection/ff_linear/headの154nodeを抽出する形へ修正し、artifacts/rust-r1-context-final-integrity2-20261016/prior-linear-diagnosis.jsonへ保存。元のclosed空抽出/失敗rootsを変更せず、数値計算・候補・採否は変更0。補足前後は同名-evidenceへ保存した。\n'
        out.sources([Path(__file__),ROOT/'tools/public-data/care_rust_r0_close.py',ROOT/'tools/public-data/rust_r1_context_publish.py']);out.json('prior-linear-diagnosis.json',linear);out.json('failed-root-pins.json',failedpins)
        extra=ROOT/'artifacts/rust-r1-context-final-integrity2-20261016-evidence'
        with EvidenceStore(extra) as store:
            store.write_json('phase',summary);store.write_json('failed-roots',failedpins);store.write_bytes('source',Path(__file__).read_bytes());store.write_bytes('before',before);report.write_text(before.decode()+note);store.write_bytes('after',report.read_bytes());store.write_json('prior-extraction',{'original_empty_sha256':digest(root/'prior-linear-diagnosis.json'),'corrected_sha256':digest(out.root/'prior-linear-diagnosis.json'),'old_node_source_sha256':digest(old/'node-comparisons.json'),'model_or_prediction_changes':False})
        verify_evidence(extra,'complete');out.json('summary.json',summary);print(json.dumps(summary));status='complete'
    finally:out.close(status)

if __name__=='__main__':main()
