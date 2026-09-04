# Chronos-2 MetroPT-3公開実データ評価結果（2026-09-04）

## 結論

固定したMetroPT-3の連続24時間、1設備、3 targetに対して、Chronos-2と5つの統計baselineを比較した。これは公開実データの限定区間におけるforecast-onlyの研究評価であり、実設備一般の性能、異常検知性能、commissioning効果、製品適合性を示さない。Banto用途は引き続き`commercial-evaluation`であり、`product-candidate`へは昇格しない。

native scenarioは、Chronos-2の公式native分位点をそのまま検証する契約である。validationの一つのmulti-target invocationで`quantile crossing detected`が発生したため、runnerは3 target分のfailure recordを作成し、baseline predictionsだけを残した`partial`結果になった。これは3 targetすべてに交差があったことを意味しない。追加のread-only diagnosticでは交差は1セルだけであり、native値の並べ替え、clip、fallbackは行っていない。

point-calibrated scenarioは、Chronos-2の公式point-only予測にvalidation residual by leadの校正を加える明示的な別scenarioである。native分位点の修正や代替ではない。このscenarioでは全モデル・全targetのtest predictionが生成され、crossing／nonfiniteなしで完了した。

## 共通評価契約

| 項目 | 設定・結果 |
| --- | --- |
| dataset | MetroPT-3、`2020-02-21`固定24時間、`metropt3-apu-01` 1台 |
| dataset fingerprint | `e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0` |
| targets | `tp3`、`oil_temperature`、`motor_current` |
| context / horizon | 120分 / 15分 |
| validation / test origins | 16 / 16 |
| covariates | past-only 11、known-future 0 |
| quantiles | `0.1` / `0.5` / `0.9` |
| split | train / validation / test = 864 / 288 / 288（60秒bin） |
| scope | forecastのみ、公開データ限定評価 |

5 baselineは、LastValue、SeasonalNaive（season length 60）、MovingAverage（window 15）、EWMA（alpha 0.3）、Holt linear（alpha 0.8、beta 0.2）であり、既存baseline設定と同一である。A、bar、ºCを混合するaggregateで優劣を主張せず、target別metricsを主に読む。

## Scenario 1: native

| 項目 | 値 |
| --- | --- |
| artifact | `artifacts/benchmark/benchmark-metropt3-chronos2` |
| code revision | `9c042538abe293e1bba4c009a65d9c6158c9ab86` |
| dirty | `false` |
| diff | empty（変更なし） |
| status | `partial` |
| prediction count | 3,600（baselineのみ） |
| failure records | 3 |
| predictions SHA-256 | `6894ecd0a24c057f13afcf505baa30a96b04a3d4203c6e24a964691d2c4520d0` |
| result SHA-256 | `c962f3ebfbea53030c00f5904a9b9e7331899be5d9be05dd136ca3fcb8d68fca` |

失敗したvalidation originはindex `1029`、timestamp `2020-02-21T17:10:00Z`である。対象は`metropt3-apu-01.motor_current`のlead 2で、native値は次のとおりだった。

| 値 | 数値 |
| --- | ---: |
| p10 | 0.14037322998046875 |
| p50 | 0.13484132289886475 |
| p90 | 0.5813533663749695 |
| p10 - p50 | 0.005531907081604004 A |

同じoriginで公式point-only `predict`とnative `predict_quantiles`を比較したところ、3 targets×15 horizonのp50／point最大絶対差は0.0だった。したがって、失敗原因はpointとp50の不一致ではなく、native分位点の交差である。

## Scenario 2: point-calibrated

| 項目 | 値 |
| --- | --- |
| artifact | `artifacts/benchmark/benchmark-metropt3-chronos2-point-calibrated` |
| code revision | `1195c12865541ea4de8020558d7d763d778ac449` |
| dirty | `false` |
| diff SHA-256 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| status | `success` |
| prediction count | 4,320 = 6 models × 3 targets × 16 origins × 15 leads |
| Chronos-2 prediction count | 720 = 3 targets × 16 origins × 15 leads |
| failure records | 0 |
| quantile crossing / nonfinite | 0 / 0 |
| predictions SHA-256 | `2ee3780f7634dc2bf7ca803a13a13c0ec8bf11f52f498ac1035a4c8f813338cf` |
| result SHA-256 | `134171092cf37465afb809416257ffe1cf973ee4d85b59d7c21705425cbe2431` |

Chronos-2にはvalidation 16 originsからlead別に計算した残差分位点を、point予測へ加算した。test actualやfuture actual、failure report、RULは入力へ渡していない。baselineの3,600 predictionsは既存baseline artifactの全bytesと新artifactの先頭prefixが一致し、baseline model metricsとorigin selectionも一致した。

### Chronos-2 target別test metrics

| target | MAE | RMSE | MASE | WIS | coverage | interval width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `tp3` | 0.3585292395970178 | 0.5381980263190024 | 3.4207498545474975 | 0.28138579459023816 | 0.7833333333333333 | 1.2702918570624457 |
| `oil_temperature` | 1.0336034076932876 | 1.633188453146909 | 3.2165937542607916 | 0.8685041867513497 | 0.6833333333333333 | 3.890819462367463 |
| `motor_current` | 1.0604097130248942 | 1.9218331953057979 | 3.1334780918493825 | 0.9982477601140415 | 0.725 | 4.329250962181697 |

best baseline比の改善率は、targetごと・metricごとの最良baselineとの比較である。

| target | MAE | RMSE | WIS |
| --- | ---: | ---: | ---: |
| `tp3` | -39.80%（last-value） | -27.65%（EWMA） | -32.99%（EWMA） |
| `oil_temperature` | -37.44%（last-value） | -15.41%（moving-average） | -19.67%（moving-average） |
| `motor_current` | -32.19%（seasonal-naive） | -17.89%（moving-average） | -23.32%（seasonal-naive） |

3 targetすべてでChronos-2がMAE／RMSE／WISの1位だった。一方、p10-p90のnominal 80%に対するcoverageは`tp3` 78.33%、`oil_temperature` 68.33%、`motor_current` 72.50%で、特にtemperatureとcurrentにundercoverageがある。これは改善率だけで製品採用を判断できない理由の一つである。

## Runtimeとprovenance

| 項目 | 値 |
| --- | ---: |
| total_seconds | 113.96744499998749 |
| validation_seconds | 75.27639730001101 |
| test_seconds | 17.88285910000559 |
| Chronos-2 test calls | 16 |
| p50 latency | 770.8114499982912 ms |
| p95 latency | 1341.8645250130794 ms |
| process peak | 1,092,546,560 bytes |

process peakは共有プロセス全体の測定値であり、model-only resourceではない。cold／warmとmodel-onlyの個別値は記録していないため推測しない。環境はPython 3.14、`chronos-forecasting==2.3.1`、CPU、`amazon/chronos-2@29ec3766d36d6f73f0696f85560a422f50e8498c`で、`model.safetensors`は477,930,472 bytes、SHA-256は`ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42`である。CI `33849354029`は3.12／3.14ともsuccessだった。

package、repository code、weightsはApache-2.0として記録しているが、Bantoでの許可用途は`commercial-evaluation`に限定する。forecast-onlyの結果であり、異常検知、commissioning、実設備一般性能、Banto Hub／PLCへのwriteを示さない。dataset、weights、実行artifactはGit管理対象外のままである。

## 限界と次の工程

今回の範囲は24時間、1設備、16 test origins、単一CPU、一回のpoint residual校正である。coverage不足、missing／stale／regime／fault slice、複数日・複数設備、再現実行は未評価である。TimesFM 3.0との同じMetroPT条件のresearch-only比較は完了し、結果を[`timesfm3-metropt3-evaluation-2026-09-04.md`](timesfm3-metropt3-evaluation-2026-09-04.md)に記録した。Phase 2は未完了とし、次はChronos再実行の再現性、origin／日／設備拡大、coverage calibration改善、missing／stale／regime／fault評価、cold／warmとmodel-only resourceの分離を行う。
