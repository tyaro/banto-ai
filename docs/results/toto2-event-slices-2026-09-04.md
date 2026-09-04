# Toto 2.0 4M event slice post-hoc解析

日付: 2026-09-04

## 結論

既存のToto 2.0 4M小規模matrix予測に対して、再推論なしでdatasetのground-truth eventを事後付与し、forecast timestampとcontext windowの露出別に再集計しました。statusは`success`、8/8 cells analyzed、excluded 0、predictionは8,640件です。

これは研究・探索専用のpost-hoc解析です。予測値の欠損・stale耐性、異常検知性能、実設備一般化、統計的有意性、製品昇格を示しません。Toto 2.0 4Mの利用区分は従来どおり`commercial-evaluation`で、Banto Hub／PLCへのwrite pathはありません。Phase 2は未完了です。

## 正本と再現情報

| 項目 | 値 |
| --- | --- |
| source matrix | `artifacts/toto2/matrix/benchmark-matrix-toto2-small/result.json` |
| matrix report | [`docs/results/toto2-matrix-2026-09-04.md`](toto2-matrix-2026-09-04.md) |
| source matrix SHA-256 | `3de9b683df25a871bcc1000f6a75ba21a301f55dad316cc15bc3675441959784` |
| event slice result | `artifacts/toto2/event-slices/benchmark-matrix-toto2-small/result.json` |
| event result SHA-256 | `832b9e088fccf5711eb31205b4848473111d38310953901842331023dcfd8e70` |
| generated summary | `artifacts/toto2/event-slices/benchmark-matrix-toto2-small/summary.md` |
| generated summary SHA-256 | `973154dee1ca1b37a53cadf035d4e752b4ddbe09be125c7f06a1a4fe3027d826` |
| matrix code revision | `1c42926903bf3235ef8b86badf0491a5575b4060` |
| analyzer code revision | `221e3bd7d5385f0446f7c32bb406baf876a87066` |
| matrix axes | seed `[17, 42]` × horizon `[15, 30]` × context `[64, 120]` |
| cells | 8/8 analyzed、excluded 0 |
| predictions | 8,640 |

解析器は既存の`predictions.jsonl`を読み、forecast timestampおよび`[origin-context_length*sampling_interval, origin)`のcontext windowと、eventの`[start,end)`を照合しました。seedはpoolせず、cell metricのmacro summaryを使っています。

## 露出集計

全8 cellのprediction rowsを対象とした集計です。event exposureは同じprediction rowをforecastとcontextで別々に分類します。

| dimension | category | prediction rows |
| --- | --- | ---: |
| forecast | `clean` | 6,048 |
| forecast | `other_signal_event` | 2,088 |
| forecast | `target_event` | 504 |
| context | `context_clean` | 1,080 |
| context | `context_target_event` | 1,440 |
| context | `context_covariate_event` | 3,060 |
| context | `context_other_signal_event` | 3,060 |

分類は同一timestamp／windowで同時に複数eventが重なっても、forecastはtarget優先、contextはtarget、covariate、otherの順に1カテゴリへ分類します。一方、event coverageのcountはmodel／target row単位なので、同じeventが重複カウントされます。たとえばoverheat eventは1 cellあたり60/192 prediction rowsでcoverされますが、`target_event`分類は30/96 rowsです。分類カテゴリとevent coverage countは同じ意味ではありません。

## Toto target-eventのcell-macro

以下はtarget-event forecast sliceの2-seed cell-macroです。`points`はcell内のprediction row数であり、raw predictionをpoolした値ではありません。

| horizon | context | points | MAE | RMSE | WIS | coverage | interval width |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 15 | 64 | 10 | 0.41415010607910185 | 0.4861204730542228 | 0.23458896053059908 | 1.0 | 1.4480838775634766 |
| 15 | 120 | 10 | 0.6752031117675781 | 0.8066231182605325 | 0.32857936105550145 | 0.8 | 1.4139863967895507 |
| 30 | 64 | 32 | 2.615565466388703 | 3.203644755407434 | 1.9790756186141971 | 0.3125 | 3.828602373600006 |
| 30 | 120 | 32 | 3.4872136562347413 | 4.080344173064958 | 2.5833244569740295 | 0.25 | 5.113024294376373 |

この限定sliceでは、horizon 15のMAEはHolt linearが最良、Totoが2位でした。horizon 30はMoving Averageが最良で、Totoは6モデル中5位（Holt linearのみTotoより悪い）です。Totoはhorizon 15の方が30より、context 64の方が120より良い傾向ですが、点数・event位置・origin構成が小さく、モデルや設備の一般性能へ外挿できません。

## event別の評価範囲

- forecastの`target_event`として実際に評価されたのは、`conveyor-01.motor_temperature`のoverheatだけです。Toto点数はseed合計でhorizon 15の各contextが10、horizon 30の各contextが32（各seedでは5/16）です。
- `motor-01-slip-test`は`motor_current`のtarget eventですが、全8 cellでforecast timestampのcoverは0です。contextにはhorizon 15で1 cellあたり180、horizon 30で360 prediction rows入ります。したがってmotor_currentのfault性能は未評価です。
- `conveyor drift`はhorizon 15でforecast未cover、horizon 30で1 cellあたり72 rowsです。
- `motor dropout`／`motor spike`は`vibration_feature`のother roleであり、targetまたはcovariate入力のeventではありません。これらはmissing／stale robustness testではありません。

## 限界と次gate

この解析は成功した既存予測へのpost-hoc event label付与であり、再推論を行っていません。`[start,end)`の境界、選択済みorigin、event coverageの重複count、seed cell-macroであることを記録しています。次のgateは以下です。

1. seedを最低5へ増やし、origin、event位置、設備、運転modeを拡大する。
2. fault targetを実際のforecast windowへ配置する専用generator／scenarioを追加する。
3. missing／staleはtarget／covariate入力を欠損させ、mask／skip／fail-closedを別評価する。
4. event単位bootstrap／confidence intervalなど、不確実性を記録する。
5. その後に22Mや他モデル比較を行う。製品昇格は行わない。

本artifactから、anomaly detection性能、missing／stale robustness、実設備一般化、統計的有意性、product-candidate昇格、Banto Hub／PLC writeを推論してはいけません。Toto 2.0 4Mは`commercial-evaluation`を維持し、Phase 2未完了です。

matrix本体の正本と評価範囲は[`docs/results/toto2-matrix-2026-09-04.md`](toto2-matrix-2026-09-04.md)を参照してください。
