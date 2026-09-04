# TimesFM 3.0 MetroPT-3公開実データ評価結果（2026-09-04）

## 結論

固定したMetroPT-3の連続24時間、1設備、3 targetに対して、TimesFM 3.0と5つの統計baselineを同一契約で比較した。TimesFM 3.0は3 targetすべてでMAE、RMSE、WISが最良となったが、これは1日・1設備・16 test origins・単一CPU・1回の実行に限るforecast-onlyの研究評価である。実設備一般の性能、異常検知性能、commissioning効果、製品適合性を示さない。

TimesFM 3.0はnative quantileを使用し、分位点のsort、clip、fallbackは行っていない。全4,320 predictionでquantile crossingは0、nonfiniteは0となり、結果は`success`だった。重みは`timesfm-non-commercial-license-v1.0`であり、利用段階は`research-only`／non-productionに固定する。精度差だけで製品採用、顧客PoC、本番shadow、Banto Hub／PLC writeへ進めない。

## 評価契約と再現性

| 項目 | 値 |
| --- | --- |
| artifact | `artifacts/benchmark/benchmark-metropt3-timesfm3`（Git ignored） |
| code revision | `2506a8d54c33558b0f2b793ffd7306fc86b021ac` |
| dirty | `false` |
| diff SHA-256 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| status / failures | `success` / 0 |
| dataset fingerprint | `e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0` |
| window | `2020-02-21`の24時間、`metropt3-apu-01` 1設備 |
| targets | `tp3`、`oil_temperature`、`motor_current` |
| context / horizon | 120分 / 15分 |
| origins | validation 16、test 16 |
| covariates | past-only 11、known-future 0 |
| quantiles | `0.1` / `0.5` / `0.9` |
| prediction count | 4,320 = 6 models × 3 targets × 16 origins × 15 leads |
| TimesFM 3.0 count | 720 = 3 targets × 16 origins × 15 leads、各target 240 |

baseline 3,600 predictionsは既存baseline artifactとbyte単位で完全一致する新artifactの先頭prefixであり、baseline metricsとorigin selectionも完全一致した。TimesFM 3.0のpredictions SHA-256は`bb5e14e5371f97a507f69a3029a09e08c08a624dcbe9bbafa3e5a66d148bd899`、result SHA-256は`b78e7658c10ffa5fbd0fd8aa1139ea9189a4c768c5d335258b0c81d904ceb228`である。

## TimesFM 3.0 target別test metrics

| target | count | MAE | RMSE | MASE | WIS | coverage | p10-p90 width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `tp3` | 240 | 0.30800515920396826 | 0.5227586899562882 | 2.938696449782159 | 0.21338089966546916 | 0.7708333333333334 | 0.9638691862424215 bar |
| `oil_temperature` | 240 | 0.8771395713563943 | 1.409615571344454 | 2.729675275680971 | 0.600044632866269 | 0.8166666666666667 | 3.1866864840189617 ºC |
| `motor_current` | 240 | 0.8559598828544691 | 1.6402796920599785 | 2.5293351310178704 | 0.6349674172621401 | 0.8208333333333333 | 2.70845591314137 A |

nominal 80% intervalに対するcoverageはtargetごとに異なり、aggregateや単位の異なるA／bar／ºCを混ぜた値を主判断には使わない。target別metricsを正本とする。

## baselineとの比較

下表は各target・各metricについて最良baselineと比較した改善率である（lower is better）。

| target | MAE | RMSE | WIS |
| --- | ---: | ---: | ---: |
| `tp3` | 48.28%（last-value） | 29.72%（EWMA） | 49.19%（EWMA） |
| `oil_temperature` | 46.91%（last-value） | 26.99%（moving-average） | 44.50%（moving-average） |
| `motor_current` | 45.27%（seasonal-naive） | 29.92%（moving-average） | 51.22%（seasonal-naive） |

この限定条件ではTimesFM 3.0が3 targetでMAE／RMSE／WISの1位だった。ただし、target数、期間、origin、設備、データ品質sliceを拡大しておらず、結果から一般性能を推定しない。

## Chronos-2 point-calibratedとの比較

比較対象はChronos-2の公式point-only予測へvalidation residual by lead校正を加えた`point-calibrated` scenarioである。Chronos-2 nativeはquantile crossingにより`partial`であり、この数値比較には使用していない。TimesFM 3.0はnative quantileなので、quantile生成方式が異なることにも注意する。

| target | MAE改善率（TimesFM） | RMSE改善率（TimesFM） | WIS改善率（TimesFM） |
| --- | ---: | ---: | ---: |
| `tp3` | 14.09% | 2.87% | 24.17% |
| `oil_temperature` | 15.14% | 13.69% | 30.91% |
| `motor_current` | 19.28% | 14.65% | 36.39% |

3 targetでTimesFM 3.0がMAE／RMSE／WISの1位となったが、同一実行内容ではなく、Chronos-2のpoint-calibratedは別のquantile契約である。したがって、これを単独の製品採用根拠にはしない。

## Runtimeとprovenance

| 項目 | TimesFM 3.0 |
| --- | ---: |
| total_seconds | 124.47128669999074 |
| validation_seconds | 63.46892919999664 |
| test_seconds | 41.07436820000294 |
| test calls | 16 |
| p50 latency | 2118.109999995795 ms |
| p95 latency | 3907.7310250140727 ms |
| process peak | 2,977,607,680 bytes（2.773 GiB） |

Chronos-2 point-calibrated比では、TimesFM 3.0はp50 `2.748x`、p95 `2.912x`、process peak `2.725x`、total `1.092x`だった。ただしprocess peakは共有process全体であり、model-only memoryではない。cold／warm／model-onlyのlatencyとmemoryは分離していないため、個別モデルのリソース値として解釈しない。

環境はPython 3.14、`timesfm==3.0.0`、CPU、`per_core_batch_size=1`、`local_files_only=True`、offlineである。checkpointは`google/timesfm-3.0-pytorch@43046b85ec22d584a13f8098c2ed39c889e129c2`、`model.safetensors`は1,322,898,824 bytes、SHA-256は`a7592b0a8432baee54483254e5647856911ce69e09d09a9bb65904b2d98f17da`である。CI `33851877697`はPython 3.12／3.14ともsuccessだった。

初回のcheckpoint prepareではWindows socket errorによりpartial cacheとなったが、取得済みのmodel、config、READMEを削除せず、`HF_HUB_DISABLE_XET=1`と`max_workers=1`を固定するhardening後に再利用して成功した。LICENSEを含むallow-list、size／hash検証、research-only acceptance、repository外cache境界は維持している。

## 判断境界と限界

TimesFM 3.0のcodeはApache-2.0でも、pretrained weightsは非商用・非本番の`timesfm-non-commercial-license-v1.0`である。今回のartifact、weights、公開データはGit管理対象外とし、結果は`research-only`として扱う。Banto Hub／PLCへのwrite、制御parameter、recipe、commissioning、顧客PoC、本番shadowへの昇格は行わない。評価はforecast-onlyで、異常検知や実設備一般性能を示さない。

今回の限界は、24時間、1設備、16 origins、単一CPU、1 run、日・設備・origin未拡大、missing／stale／regime／fault slice未実施、再現run未実施、cold／warm／model-only resource未分離である。Phase 2は未完了とする。

次はChronos-2の再現run、coverage改善、Toto／Granite TTMなど商用候補との同一契約比較、日・設備・origin拡大、degraded slice、model単独resource分離である。TimesFM 3.0の精度結果だけで利用段階を変更しない。
