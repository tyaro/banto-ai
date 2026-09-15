# 通常権限での結果保存

2026-09-16。[ユーザーの運用方針](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)に合わせ、同じ出力先は一度に1処理だけが書き込む。
`_anomaly_v03_io` の既存保存エンジンを共用する `LocalPublication` と、簡単な保存・読取りAPIを追加した。
管理者権限、専用Windowsアカウント、ACL設定は不要。自動再開や既存結果の上書きはしない。

## 保存と読取り

呼出し側が既存の親フォルダーと新しい実行名を指定する。各ファイルはUTF-8/LF、JSONは既存のcanonical形式を使う。
小さな計算済み結果の例:

```python
from pathlib import Path
from banto_ai._anomaly_v03_io import publish_local_result, verify_local_publication
from banto_ai.anomaly_v03_materializer import json_bytes

parent = Path("artifacts/local-results")
parent.mkdir(parents=True, exist_ok=True)
files = {"result.json": json_bytes({"count": 2}), "summary.md": b"2 saved records\n"}

def verify_result(saved):
    if dict(saved) != files:
        raise ValueError("result content mismatch")

receipt = publish_local_result(parent, "example-01", files, verify_semantics=verify_result)
report = verify_local_publication(
    Path(receipt["output_path"]),
    expected_marker_sha256=receipt["marker_raw_sha256"],
    verify_semantics=verify_result,
)
```

`example-01` が既にあれば、完了・未完了を問わず拒否する。再実行時は別の実行名を選ぶ。
`verify_semantics` には呼出し側の件数・内容・集計整合性などの検査を渡す。例は2ファイルの既知bytesを比較しているだけで、評価データの生成はしない。
大量の入力を一括メモリへ持たない場合は `LocalPublication` の `write` で順次保存する。

## 維持する保存条件

| 条件 | 処理 |
| --- | --- |
| 同じ保存先の二重使用 | 新規rootを排他的に作成し、2つ目のwriterを拒否 |
| 既存結果の上書き | ファイルを排他的に作成。payloadの名前確定と完了印も既存先を置換しない |
| 保存失敗・途中終了 | 完了前なら完了印なしで残す。失敗したwriterやclose後のwriterは再使用を拒否 |
| 完成した結果だけ読む | receiptのmarker hash、全payload inventory/hash、内容検査を通した結果だけを採用 |

完了点は全payloadを保存・再読取り・検査した後の `.complete` 作成。同じ実行の `stage/` や `payload/` が見えるだけでは完了としない。
途中で処理が終了した場合は自動修復・削除せず、新しい実行名でやり直す。
完了印作成後に応答を失うとwriterは失敗状態でも有効な結果が残ることがある。同じwriterで再試行したり、失敗記録を追記して完成済みの構成を変えたりしない。既知のreceipt情報があれば、新しい読取り検査で確認できる。
完了前の失敗記録 `preserve_failure` は既知のrootに一度だけ保存できる。記録後は成功へ進めない。

## 今回の範囲

新markerは `anomaly-v03-local-complete`。従来のtemp用fixture markerと相互に混同しない。
通常ファイルI/Oを使い、Windowsでは既存の非上書きrename/hardlink経路を共用する。書込みflush/fsyncは行うが、停電後の全ディレクトリ構成の永続性まで保証する変更ではない。
同じ保存オブジェクトを複数threadから操作せず、作業中の出力を他の処理で書き換えない運用を前提にする。
意図的な別プロセスからの改ざん耐性・専用principalの分離は保留中。既知の正式v0.x出力名を通常保存先に使わない。
科学的評価条件、正式v0.3 campaign entry、runtime/受入gateは変更しない。`local_verified=true` は今回の保存検査だけを示し、`native_acceptance=not_completed` を維持する。
