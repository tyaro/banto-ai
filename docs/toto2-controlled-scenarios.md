# Toto 2.0 controlled evaluation scenarios

これは Toto 2.0 の実データ評価や製品性能の結果ではなく、generator → quality gate → benchmark → Toto adapter の受入契約を固定するための synthetic control plane です。利用区分は `commercial-evaluation` のままであり、PLC write、製品制御、実設備への一般化、Phase 2 の完了を意味しません。

## 目的と比較単位

4本の同一条件データを、control と event 条件の paired comparison として定義します。

| track | 日本語名 | event | event の役割 | ねらい |
| --- | --- | --- | --- | --- |
| A | 無イベント対照 | なし | control | 品質変更・故障なしの基準 |
| B | target fault | `motor-01.motor_current` の `jam_or_slip` `[388,396)` | target の未来実値 | target fault forecast への露出 |
| C | target quality | current dropout `[368,372)`、temperature stale `[372,376)` | target の過去 context | target quality 欠損への頑健性 |
| D | covariate quality | `load_proxy` dropout `[368,372)`、stale `[372,376)` | past-only covariate の過去 context | covariate quality 欠損への頑健性 |

全 track は `sample_count=480`、同じ motor／conveyor、同じ12 regime、1秒間隔です。設定ファイルは次の4 generator config と、共通 benchmark config、4 matrix config です。

- `examples/configs/synthetic-toto2-controlled-control.json`
- `examples/configs/synthetic-toto2-controlled-target-fault.json`
- `examples/configs/synthetic-toto2-controlled-target-quality.json`
- `examples/configs/synthetic-toto2-controlled-covariate-quality.json`
- `examples/configs/benchmark-toto2-controlled.json`
- `examples/configs/benchmark-matrix-toto2-controlled-control.json`
- `examples/configs/benchmark-matrix-toto2-controlled-target-fault.json`
- `examples/configs/benchmark-matrix-toto2-controlled-target-quality.json`
- `examples/configs/benchmark-matrix-toto2-controlled-covariate-quality.json`

頑健性の比較は、各 model の control → degraded の同一 seed／horizon／context paired comparison です。model 間の順位付けをこの設計から導きません。availability／valid denominator（呼び出し可能、予測完備、実測値が評価可能）と accuracy metric は別に集計します。baseline は同じ request を受けますが、non-OK target history を除外して短縮し、past-only covariate は使わないため、Toto の mask 入力とは実装差があります。この差分は denominator として明示し、model ranking には使いません。

## 固定された時刻と half-open window

test origin は `384` の1点だけです。開始時刻が `2026-01-01T00:00:00Z`、sampling interval が1秒なので、origin timestamp は `2026-01-01T00:06:24Z` です。horizon は未来の `[origin, origin+horizon)`、context は origin 直前の `[origin-context_length, origin)` とします。

| horizon | forecast window | context=64 | context=120 |
| --- | --- | --- | --- |
| 15 | `[384,399)` | `[320,384)` | `[264,384)` |
| 30 | `[384,414)` | `[320,384)` | `[264,384)` |

B の fault `[388,396)` は h15／h30 の forecast に含まれ、context には含まれません。C／D の quality intervals `[368,372)` と `[372,376)` は両方の context に含まれ、どちらの forecast にも含まれません。したがって C／D の forecast actual は control と同一 seed で byte-equivalent、finite、quality `ok` であることを静的・実行テストで確認します。

`dropout` は `value=null` かつ `quality=missing`、`stale_value` は有限値を保持した `quality=stale` です。stale は値を hold した品質フラグであり、source age や transport freshness の証拠ではありません。Toto adapter は両方を0-fillし、`target_mask=false` と `has_missing_values=true` を渡します。padding も未観測として扱います。

## 実行面の受入契約

各 matrix は次の直積を持ちます。seed は5個以上、horizon は15／30、context は64／120です。benchmark は targets `motor_current`／`motor_temperature`、past-only `load_proxy`、known-future 空、validation／test は stride 15・max origin 1、5 baselines と pinned Toto native quantiles を固定します。出力先は track ごとに分離し、既存 output を上書きしません。

実行する場合のコマンドは以下です。4 config を定義しただけでは paired 比較の受入完了ではありません。cross-matrix acceptance analyzer source と config/schema/test は追加済みで、pair key、base config hash、event 差分、全 equipment の future actual 同一性、model／equipment／target／origin 別 availability、expected／valid denominator、non-OK input count、no-ranking／truth-unavailable を machine-enforceします。analyzer がない結果は比較採用不可です。この savepoint では real model、matrix、result document、実 controlled artifact は作成していません。

```powershell
& $totoPython tools\toto2\run_matrix.py --config examples\configs\benchmark-matrix-toto2-controlled-control.json --cache-dir C:\banto-cache\toto2
& $totoPython tools\toto2\run_matrix.py --config examples\configs\benchmark-matrix-toto2-controlled-target-fault.json --cache-dir C:\banto-cache\toto2
& $totoPython tools\toto2\run_matrix.py --config examples\configs\benchmark-matrix-toto2-controlled-target-quality.json --cache-dir C:\banto-cache\toto2
& $totoPython tools\toto2\run_matrix.py --config examples\configs\benchmark-matrix-toto2-controlled-covariate-quality.json --cache-dir C:\banto-cache\toto2
& $totoPython tools\toto2\analyze_controlled_acceptance.py --config examples\configs\toto2-controlled-acceptance.json
```

## 除外する解釈

- B は fault forecast の評価であり、anomaly detection 性能の評価ではありません。
- truth が unavailable なセルは、別の inconclusive／no-rank track として扱う予定であり、この4本には混ぜません。
- stale／dropout の availability 差を accuracy 改善と呼びません。
- cross-matrix acceptance analyzer の出力がない結果は比較採用不可です。実行順は4 matrix → analyzerです。
- この仕様は commercial evaluation の受入境界を固定するもので、Phase 2 の production candidate、22M、fine-tuning、実設備データ、製品採用の根拠ではありません。
