# 保存済み観測データのローカルスコア計算

通常権限・単一writerで「入力を保存→スコア計算→結果保存→再計算による確認」を行う開発用コマンド。
既存S2のC0/C1/C2の数式・fit/calibration範囲・閾値を共用する。登録seedからのデータ生成、campaign identityの付与、イベント照合、性能評価は行わない。

## 実行

入力JSONLと、既存の出力親フォルダーを用意する。実行名は毎回新しい名前を使う。

```text
python tools/evaluator/preview_anomaly_v03.py run --observations observations.jsonl --output-parent artifacts/local-results --name preview-01 --candidate c0-diff-control
```

候補は `c0-diff-control`（既定）、`c1-phase-level`、`c2-phase-conditional`。一度に1候補だけ計算する。
出力先を最初に排他的に確保するため、重複した実行名は入力読取り・計算の前に拒否する。
標準出力のJSONに保存先・marker hash・計算件数を返す。コマンドが正常終了しても、入力不足の場合は `preview_status=inconclusive` になる。

完了した出力を、標準出力の `receipt.marker_raw_sha256` を指定して確認する。

```text
python tools/evaluator/preview_anomaly_v03.py verify --output artifacts/local-results/preview-01 --marker-sha256 <receiptに表示された64桁のhash>
```

保存済み入力から再計算して、結果JSON・score JSONL・summaryの全bytesを照合する。元の入力ファイルがその後変わっても、保存したsnapshotが再計算の入力になる。

## 入力形式と上限

既存 `decode_saved_observations` と同じcanonical UTF-8/LF JSONLを受け付ける。
対象設備はmotor-01/conveyor-01、4 targetsとload_proxyを持つ既存の観測形式。設備順・時刻順、品質値、6桁精度、固定capture範囲（2026-01-01 UTCの最初の9000秒）など、既存decoderの条件を維持する。
任意の実設備データ形式を自動変換するコマンドではない。

入力は **16MiB・18000行以下**。これは入力上限であり、Python process全体のメモリ上限ではない。
既存の時間分割はwarm-upがsample0〜1799、fitが1800〜5399、calibrationが5400〜7199、scoreが7200〜8999。
部分入力は診断用に受け付け、normal-prefixの不足・不適切な品質・利用不能profileを隠さず記録する。score区間の観測がなければscore件数は0になる。

## 保存内容と結果の意味

`payload/` に次の4ファイルを保存する。保存先の排他・完了印は[通常保存API](anomaly-v03-local-publication.md)を共用する。

- `observations.jsonl`: 計算に使った入力snapshot。
- `preview.json`: 入力hash、候補、48 profileの状態、利用可能/不能件数、瞬間的な閾値超過件数、入力不足の理由。
- `scores.jsonl`: 入力に存在するscore区間の各targetの値・除外理由。campaignのdataset/score/profile IDは付与しない。
- `summary.md`: 候補・件数・target別集計。

閾値超過はその時点のスコア条件であり、確定した異常イベント数ではない。除外理由は重複し得るため、その件数の合計が利用不能行数を超える場合がある。
`computed` は提供された観測の計算ができたという意味。全test区間の網羅や検出性能の成功判定ではない。
`performance_status=not_evaluated` / `formal_permission=false` / `native_acceptance=not_completed` を維持する。

入力エラー・計算失敗・保存失敗では完了印を作らず、その実行名を再使用しない。完了印作成後の応答喪失は通常保存APIと同様に扱う。
元のformal campaign entry、科学的評価条件、受入gateは変更しない。専用principal/追加OS権利/厳密なP-U分離試験も再開しない。
