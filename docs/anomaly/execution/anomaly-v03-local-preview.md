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

## 保存済み候補の比較

同じ入力で作った異なる2〜3候補を、保存先と各receiptのmarker hashで指定する。

```text
python tools/evaluator/preview_anomaly_v03.py compare --result artifacts/local-results/c0 <C0のmarker hash> --result artifacts/local-results/c1 <C1のmarker hash>
```

各結果を順番に再計算検証し、候補別・target別の利用可能/不能・瞬間的な閾値超過件数と、候補ペアの判定一致/不一致をMarkdownで標準出力へ表示する。`--format json` で同じ集計をJSON出力できる。3候補なら `--result` をもう1つ追加する。候補はC0/C1/C2の順に表示する。
比較コマンドはファイルを作成・変更しない。各候補の実行を先に完了させ、同じ保存先への書込みと比較を同時に行わない。

入力bytesのSHA256・行数・サイズが違う結果、同じ候補の重複、未完成・内容不一致の結果は比較を拒否する。各候補の保存済み観測から再計算するため、比較にも計算時間がかかる。
判定一致/不一致は**両候補で利用可能な同じtarget・sampleの行だけ**を数える。片側だけ利用可能、両側とも不能な行は別欄に表示する。利用不能を「異常なし」に含めない。
全候補がcomputedの場合だけcomparisonもcomputedになり、部分入力などはinconclusiveを維持する。入力不足の理由と除外タグも表示する。
候補ごとにスコアの定義・閾値が異なるため、生スコアの大小による順位や勝者は出さない。判定差の確認用であり、正解ラベルに基づく検出性能の比較ではない。

### 判定差の詳細

比較表には、判定または利用可否が分かれた **sample/targetの組**を既定で最大20組表示する。
各組にUTC時刻と差の種類を付け、候補ごとのスコア・残差・phase・mode/recipe・除外理由を並べる。
判定は `threshold_exceeded` / `below_or_at_threshold` / `unavailable` の3種類。利用不能のスコア・残差はMarkdownでは `n/a`、JSONでは `null` とし、「異常なし」と区別する。
数値は保存済み値を保持し、候補間のスコア差を計算したり順位付けしたりしない。

```text
python tools/evaluator/preview_anomaly_v03.py compare --result artifacts/local-results/c0 <C0のmarker hash> --result artifacts/local-results/c1 <C1のmarker hash> --details-limit 20 --details-offset 20
```

`--details-limit` は0〜100（既定20）、`--details-offset` は先頭から省略する組数（既定0）。上の例は21組目から最大20組を表示する。sample順、同じsampleではtarget名順に並べ、全体の差の組数・表示数・前後の省略数も出す。
0件表示や範囲外のoffsetでも、全体の差の件数と候補別/ペア別集計は保持する。全候補が利用不能の行は詳細対象に含めず、除外理由の集計で確認する。
同じ組が複数ペアで異なることがあるため、詳細の組数はペア別の不一致件数の合計とは限らない。
`--format json` の `details` に同じ詳細とページ情報を追加する。以前のdetailsなし比較JSONもMarkdown表示できる。
上限は表示量の制限であり、入力読取りや再計算を一部に限定するものではない。

各詳細には、同じ設備の **直前1秒・当該時点・直後1秒** の保存済み観測も併記する。
4つの計算対象信号について値・単位・品質とmode/recipeを表示し、C2が参照する他信号の変化も確認できる。load_proxyは計算対象外のため含めない。
正確な時点の観測がない場合は `present=false` / `observation absent` として残し、離れた時点の値や別設備の値で埋めない。観測行はあるが信号値が欠ける場合の `null` とも区別する。
直後の観測は **計算終了後の閲覧専用** であり、表示済みスコア・残差・判定の計算には使わない。
観測は完了結果の検証済みsnapshotから取り出すため、元の入力ファイルを変更しても表示は変わらない。
同一入力は1候補分だけ保持し、追加で保持する展開済み観測は表示対象の時点に限定する。詳細が0件なら観測表示用の解析を省く。
JSONでは各詳細行の `observations` に追加する。既存のobservationsなし詳細JSONも引き続き描画できる。

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
