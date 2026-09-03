# TimesFM 3 rolling-origin benchmark 実測結果（2026-09-04）

## 要約

`synthetic-motor-small` に対する小規模な chronological rolling-origin benchmark を、LastValue baseline と TimesFM 3.0で実施しました。この限定条件では、TimesFM 3.0は LastValue より point forecast の MAE、RMSE、MASE、および WIS が良好でした。一方、TimesFM 3.0の p10-p90 interval は baseline より広く、nominal 80% coverage に対して 70.833% でした。

この結果は、24 prediction points、2 equipment、各 equipment 2 validation origins／2 test origins、単一の合成データgenerator、context 12、horizon 3という小さな比較です。したがって、一般性能、実設備性能、製品採否、商用利用可否、または Phase 2 完了を示すものではありません。

## 評価条件

| 項目 | 条件 |
| --- | --- |
| dataset | `synthetic-motor-small` |
| seed | `42` |
| dataset fingerprint | `6427bd2da97958f04b8c34e3a09a101d8bc3fc85eced003aaf022e81567312b6` |
| equipment | 2台 |
| targets | `motor_current`、`motor_temperature` |
| context / horizon | 12 / 3 |
| covariate | `load_proxy` は past-only |
| known-future covariate | なし |
| validation origins | 各 equipment `[36, 45]` |
| test origins | 各 equipment `[48, 57]` |
| prediction points | modelごと24点 |
| test forecast call | modelごと4回 |
| LastValue quantile policy | `validation-residual-by-lead` |
| TimesFM 3 quantile policy | `native` |
| runtime | CPU、offline、Windows OS process peak測定 |

同じ equipment／origin／targetを両modelへ適用しました。1つの origin の全targetを同じ ForecastRequest にまとめ、結果はtarget IDで対応付けています。

## model別結果

下表の「表示値」は比較しやすいように小数点以下6桁へ丸めています。正確なraw値は後の表に併記します。

| 指標 | LastValue | TimesFM 3.0 |
| --- | ---: | ---: |
| count | 24 | 24 |
| MAE | 0.219726 | 0.124178 |
| RMSE | 0.298245 | 0.162091 |
| MASE | 1.159370 | 0.626709 |
| WIS | 0.359569 | 0.173315 |
| p10-p90 coverage | 16.666667% | 70.833333% |
| p10-p90 interval width | 0.389116 | 1.758446 |

### raw値

```text
LastValue
  count: 24
  MAE: 0.21972637499999967
  RMSE: 0.29824453099910303
  MASE: 1.1593699689336212
  WIS: 0.3595693283333335
  coverage: 0.16666666666666666
  interval_width: 0.3891164666666668

TimesFM 3.0
  count: 24
  MAE: 0.12417778491274506
  RMSE: 0.16209104322293902
  MASE: 0.6267093063605986
  WIS: 0.17331521854803297
  coverage: 0.7083333333333334
  interval_width: 1.758446176846822
```

### LastValueに対する相対改善

TimesFM 3.0の相対改善率は、`(LastValue - TimesFM 3.0) / LastValue` で計算しました。

| 指標 | 相対改善率（表示値） | raw値（%） |
| --- | ---: | ---: |
| MAE | 43.4853% | 43.4852621071343% |
| RMSE | 45.6516% | 45.6516293257942% |
| MASE | 45.9440% | 45.9439761979482% |
| WIS | 51.7992% | 51.7992206533913% |

TimesFM 3.0の interval width は baseline の `4.51907417825414`倍（表示値 `4.519074`倍）でした。TimesFM 3.0の p10-p90 coverage は `70.833333%`で、nominal target `80%`を満たしていません。point forecast の改善と interval calibration は別の評価軸として扱う必要があります。

## 再現性と実行時情報

2回のrunで、次が完全一致しました。

- predictions SHA-256: run1、run2ともに `15d233ebccae8e180262dac9b2bb606c4597f58427bd827157e7917aba2244b3`
- metrics: exact equal
- origins: exact equal

| 項目 | run1 | run2 |
| --- | ---: | ---: |
| total runtime | 16.759137400018517秒 | 18.367833299998892秒 |
| peak memory | 2966384640 bytes | 2966917120 bytes |
| TimesFM p50 latency | 321.71039999229833 ms | 379.159449992585 ms |
| TimesFM p95 latency | 327.93352001172025 ms | 437.6459800012526 ms |

peak memory のsourceは、両runとも Windows OS process `PeakWorkingSetSize` です。latencyは各test forecast callの測定値で、model loadは含みません。total runtimeはmodel load、validation、test、output生成を含みます。

実行時の来歴は次のとおりです。

- Git HEAD: `f0a06d225b0cef1f5959cf7196ac8ad2c28c3173`
- dirty diff SHA-256: `0075ff72e3dcf352a46874b63a9ac7035affd86c21adadf512eef1ccbd2042e6`
- TimesFM package: `3.0.0`
- checkpoint revision: `43046b85ec22d584a13f8098c2ed39c889e129c2`
- device: CPU
- network: offline
- weights usage: research-only / non-commercial

## 解釈と限界

このsynthetic testの範囲では、TimesFM 3.0は LastValue に対して point forecast と WIS で優位でした。ただし、次の理由から採用判断には使いません。

- prediction pointsはmodelごと24点に限られる。
- 各 equipment の validation／test originは各2個だけである。
- データは単一generatorによる合成データで、実設備の挙動を代表しない。
- 比較baselineは LastValue だけであり、baselineとして弱い可能性がある。
- TimesFM 3.0のnative intervalは baseline より大幅に広く、coverageも80%未達である。
- 1つの短いcontext／horizon条件であり、長期予測、regime変更、欠損、fault条件を評価していない。
- TimesFM 3.0のpretrained weightsは research-only / non-commercial であり、Banto product候補へ昇格できない。

生成したdataset、checkpoint、benchmark artifactはGit管理対象外です。この結果文書には顧客データやcheckpoint本体を含めません。

## 次の計画

Phase 2は未完了のままです。次は、同じorigin選択規則と結果schemaを維持して、次を追加します。

1. seasonal-naive、EWMA、moving-average、Holt、ETS、linear-regression-covariatesを同一originで比較する。
2. validation／test origin数を増やし、複数seed、複数horizon、複数contextを評価する。
3. startup、nominal、high-load、regime change、欠損、stale、fault-like eventごとにslice結果を出す。
4. TimesFM 3.0のnative quantileについて、coverage不足と過大なinterval widthをcalibration実験で検証する。
5. Chronos-2、Toto 2.0、Granite TTMなど、利用条件の異なる候補を同じdataset／window／metric／hardware記録で比較する。
6. 公開データで再現可能性を補強し、合成データでの結果と分けて報告する。

次の比較結果が揃うまで、実設備評価、製品採否、Banto Hub／PLC write経路、commissioning profileへの自動昇格は行いません。
