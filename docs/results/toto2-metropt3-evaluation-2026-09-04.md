# Toto 2.0 4M MetroPT-3公開実データ評価結果（2026-09-04）

## 結論

固定したMetroPT-3の24時間、1設備、3 target、16 validation origins／16 test originsで、Toto 2.0 4Mと5つの統計baselineを共通runnerで評価した。結果は`success`、failure 0、prediction 4,320である。Totoは3 targetすべてで5 baselineに対してMAE／WISが最良だった。

これは公開実データの限定区間によるforecast-onlyの研究評価であり、実設備一般の性能、統計的有意差、製品適合性、異常検知、commissioning効果を示さない。`commercial-evaluation`の範囲に留め、`product-candidate`への昇格やBanto Hub／PLC writeは行わない。

## 評価契約と実行provenance

| 項目 | 値 |
| --- | --- |
| benchmark artifact | `artifacts/benchmark/benchmark-metropt3-toto2-4m/result.json`、`summary.md`（Git管理対象外） |
| CPU smoke artifact | `artifacts/toto2/cpu-smoke.json`、status=`pass`、snapshot verification済み（Git管理対象外） |
| dataset | MetroPT-3、2020-02-21固定24時間、`metropt3-apu-01` 1設備 |
| dataset fingerprint | `e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0` |
| code revision | `c696daf5ba58055d92607ccdbd5d47b775e24024`、dirty=`false` |
| targets | `tp3`、`oil_temperature`、`motor_current` |
| context / horizon | 120分 / 15分 |
| Toto effective input | 128点、先頭8点の未観測padding、`patch_size=32` |
| covariates | past-only 11、known-future 0 |
| origins | validation 16、test 16、stride 15 |
| quantiles | native `p10` / `p50` / `p90` |
| prediction count | 4,320 = 6 models × 3 targets × 16 origins × 15 leads |
| status / failures | `success` / 0 |

Totoのpackageは`toto-2==2.0.0`（wheel SHA-256 `5eb922f8162a800d6d31cffb10e3f4c079276b12c41e272129e5b4a930943f71`）、umbrella packageは`toto-models==1.0.0`。checkpointは`Datadog/Toto-2.0-4m@8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9`、`model.safetensors`は16,582,848 bytes、SHA-256は`316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e`である。code／weights licenseはApache-2.0、許可用途は`commercial-evaluation`である。

MetroPT-3のcontext=120は変えていない。adapterはTotoのpatch境界に合わせて先頭8点をzero valueで埋めるが、maskはfalseであり、観測値として学習・評価に使っていない。公式呼出しはCPU、batch=1、`decode_block_size=None`、`local_files_only=True`、`has_missing_values=True`である。

client CLI修正後の`python tools\\toto2\\prepare_checkpoint.py`直接実行経路と、repo外cwdからのabsolute script経路は、download mock／acceptance gateによる副作用なしのsubprocess検証を通過した。

## Toto 2.0 4M target別test metrics

| target | MAE | RMSE | WIS | coverage | p10-p90 width |
| --- | ---: | ---: | ---: | ---: | ---: |
| `tp3` | 0.2838531311307635 | 0.46821120850926456 | 0.18813409077301227 | 0.7708333333333334 | 0.8683372437953949 bar |
| `oil_temperature` | 0.976644075030372 | 1.6187391663937019 | 0.6915168324223271 | 0.8333333333333334 | 3.51393879254659 ºC |
| `motor_current` | 0.8562984656547269 | 1.655146105085328 | 0.6179118725635393 | 0.8541666666666666 | 2.869700863833229 A |

5 baselineはLastValue、SeasonalNaive、MovingAverage、EWMA、Holt linearである。Totoは3 targetすべてで、この5系統それぞれよりMAE／WISが低かった。ただしA、bar、ºCを混ぜたaggregate値や単位の異なるtargetの平均を採用判断には使わない。

## 既存modelとの比較

TimesFM 3.0との比較は同じMetroPT契約だが、TimesFMのweightsはresearch-only／non-commercialであるため、製品候補比較ではない。

| target | Toto MAE / WIS | TimesFM 3.0 MAE / WIS | 読み方 |
| --- | ---: | ---: | --- |
| `tp3` | 0.2838531311307635 / 0.18813409077301227 | 0.30800515920396826 / 0.21338089966546916 | Toto優位 |
| `oil_temperature` | 0.976644075030372 / 0.6915168324223271 | 0.8771395713563943 / 0.600044632866269 | TimesFM優位 |
| `motor_current` | 0.8562984656547269 / 0.6179118725635393 | 0.8559598828544691 / 0.6349674172621401 | MAEはほぼ同等でTimesFM僅差、WISはToto優位 |

Chronos-2はnative quantileでcrossingが発生したため、比較にはvalidation-residualでpointを校正した別scenarioを使う。quantile policyが異なるため、Totoとの直接のnative優越とは解釈しない。

| target | Toto MAE / WIS | Chronos-2 point-calibrated MAE / WIS |
| --- | ---: | ---: |
| `tp3` | 0.2838531311307635 / 0.18813409077301227 | 0.3585292395970178 / 0.28138579459023816 |
| `oil_temperature` | 0.976644075030372 / 0.6915168324223271 | 1.0336034076932876 / 0.8685041867513497 |
| `motor_current` | 0.8562984656547269 / 0.6179118725635393 | 1.0604097130248942 / 0.9982477601140415 |

この限定条件ではTotoが3 targetで低いが、Chronos-2 nativeとは別の失敗・校正契約であり、これだけでmodel選定を確定しない。runtimeもTotoのp50はChronos-2より短い一方、p95はToto `2391.030899991165 ms`、Chronos-2 `1341.8645250130794 ms`でTotoの方が長い。p50だけで優越を主張しない。

## Runtimeと安全境界

| 項目 | Toto 2.0 4M |
| --- | ---: |
| total time | 116.79421359999105 s |
| validation / test time | 78.32724240000243 s / 19.81894050000119 s |
| p50 / p95 latency | 584.8305000108667 ms / 2391.030899991165 ms |
| process peak | 752,611,328 bytes |
| measurement | process-level peak、end-to-end timing |

process peakは共有benchmark process全体であり、Toto model-only memoryではない。cold／warm、model load、CPU thread数、model-only resourceは分離していない。Banto Hub／PLCへのwriteはなく、artifactの`production=false`、`control_write=false`、`network_fallback=false`である。実行中はoffline、telemetry disabled、external cache、固定snapshotを使い、cache miss時のnetwork fallbackはしない。nonfinite、missing／stale／irregular input、quantile crossing、output shape異常は補正せずfail closedにする。

## 限界と次工程

評価は一つの24時間slice、1設備、16 test origins、単一CPU、同日単発の1 runである。統計的有意差、seed robustness、cold／warm差、日・設備・origin拡大、missing／stale／regime／fault slice、coverage calibration、model-only resourceは未実施である。全model混在aggregateも単位が異なるため主判断に使わない。

次工程は、seed・origin・日・設備の拡大、coverage calibration、missing／stale／regime／fault slice、cold／warmとmodel-only resourceの分離、Chronos再実行である。Toto 22M、matrix、fine-tuning、実設備一般化も未実施であり、別の評価として扱う。Phase 2は完了扱いにせず、本番制御やproduct-candidateへの昇格は行わない。
