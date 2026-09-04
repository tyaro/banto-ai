# Chronos-2 初期評価結果（2026-09-04）

## 結論

固定checkpointの検証、公式API direct CPU smoke、Banto tool経由のCPU smoke、past-only／known-futureの小規模rolling-origin benchmarkまで完了しました。Chronos-2は今回の合成データ条件でaggregate MAE／RMSE／MASE／WISが比較model中最良となり、known-future条件ではpast-only条件からさらに改善しました。

一方、これはseed 42、60 samples×2 equipment、context 12、horizon 3、少数originの合成データ評価です。aggregateはAとdegCを同数混合した比較用指標で、物理量として直接解釈できません。known-futureもorigin時点で確定済みの計画値を模したsynthetic条件に限られます。Chronos-2は`commercial-evaluation`を継続しますが、`product-candidate`には昇格させません。

## 固定したmodel証跡

| 項目 | 値 |
| --- | --- |
| package | `chronos-forecasting==2.3.1` |
| checkpoint | `amazon/chronos-2@29ec3766d36d6f73f0696f85560a422f50e8498c` |
| `model.safetensors` size | 477,930,472 bytes |
| `model.safetensors` SHA-256 | `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42` |
| package／code／weights license | Apache-2.0 |
| Bantoでの利用段階 | `commercial-evaluation` |

checkpointは実取得fileのsizeと実計算SHA-256で検証済みです。実行時はrepository外cache、固定revision、`local_files_only=true`を使用しました。

## Smoke結果

### 公式API direct CPU smoke

- Python 3.14専用venvでpackage install／import成功
- 2 targets×prediction horizon 3×3 quantiles
- inference: 1.335秒
- 判定: package、checkpoint、公式API shapeの契約確認に成功

### Banto tool CPU smoke

正本: `artifacts/chronos2/cpu-smoke-provenance-2026-09-04.json`（Git管理対象外）

旧`artifacts/chronos2/cpu-smoke-2026-09-04.json`は初回実行の証跡として残すが、本書の正本には使用しない。

| 項目 | 値 |
| --- | --- |
| status | `pass` |
| target | `motor_current`、`motor_temperature` |
| context／horizon | 24／4 |
| past-only covariate | `speed` |
| known-future covariate | `planned_load` |
| quantiles | p10／p50／p90 |
| snapshot verification | `snapshot_verified=true` |
| provenance verification | `model.provenance.verification_status=verified` |
| checkpoint evidence | 477,930,472 bytes／SHA-256 `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42` |
| package SHA-256 | `d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496` |
| allowed use | `commercial-evaluation` |
| offline | `local_files_only=true` |
| cold elapsed | 12.057009100011783秒（表示値12.057009秒） |

このelapsedにはmodel load等のcold pathを含みます。後述するrolling benchmarkの`latency_by_model.chronos2`は同一process内のwarm test callであり、直接比較しません。

## Rolling-origin benchmark条件

- dataset: `synthetic-motor-small`、seed 42
- dataset fingerprint: `6427bd2da97958f04b8c34e3a09a101d8bc3fc85eced003aaf022e81567312b6`
- 60 samples×2 equipment（合計120 observation records）
- targets: `motor_current`（A）、`motor_temperature`（degC）
- context 12、horizon 3、quantiles p10／p50／p90
- equipmentごとにvalidation 2 origins、test 2 origins
- Chronos-2はnative quantile、baselineはvalidation-residual-by-lead
- failure: 0、両runとも`status=success`

両resultはHEAD `c89c75a5966bfdfb7f624f5b12f010c8a72e6242`、`dirty=true`、diff SHA-256 `6b7547e3c77252c6693e3a2dc5d114999c17deb7e5274836f4a8031fb02d7ed8`を記録しています。比較条件は揃っていますが、clean savepointからの再実行ではないため、最終的な再現性証跡には使用しません。

## Past-only比較

正本: `artifacts/benchmark/benchmark-chronos2-baselines-past-only/result.json`（Git管理対象外）

6 modelsのaggregate結果です。

| Model | MAE | RMSE | MASE | Coverage | Width | WIS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Chronos-2 | 0.20672198138554906 | 0.2844462855283722 | 0.9750591786120048 | 0.8333333333333334 | 1.7209377686182659 | 0.1952207659517925 |
| Last value | 0.21972637499999967 | 0.29824453099910303 | 1.1593699689336212 | 0.16666666666666666 | 0.3891164666666668 | 0.3595693283333335 |
| Moving average | 0.3101050694444441 | 0.453287697012691 | 1.6967632908640093 | 0.25 | 0.5577706888888879 | 0.5105865783333337 |
| Seasonal naive | 0.3107074583333332 | 0.4434217075273362 | 1.7035669285863255 | 0.25 | 0.5731651333333333 | 0.5119552088888892 |
| Holt linear | 0.45165691970112737 | 0.7373507802531213 | 1.6399611426340082 | 0.375 | 0.2791307089797868 | 0.46557067232665755 |
| EWMA | 0.65636388868174 | 0.8492723491278269 | 3.2042095250251426 | 0.4166666666666667 | 1.048117900165642 | 0.8530498828905768 |

Chronos-2はaggregate MAE、RMSE、MASE、WISで最良でした。Last valueに対してMAEは約5.92%、WISは約45.71%小さくなりました。ただしinterval widthは広く、coverage改善と幅のtrade-offを追加条件で確認する必要があります。

### Chronos-2のtarget別結果

| Target | MAE | RMSE | MASE | Coverage | Width | WIS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `motor_current` | 0.11516869389088939 | 0.14802147625752052 | 0.3826615546868966 | 1.0 | 1.9990071455637615 | 0.17165670766788058 |
| `motor_temperature` | 0.2982752688802088 | 0.3740441434755005 | 1.567456802537113 | 0.6666666666666666 | 1.4428683916727703 | 0.21878482423570453 |

電流MAEはmoving-averageの`0.0823739722222222`がChronos-2より優位でした。温度MAEもHolt linearの`0.14914157586799526`が優位です。一方、温度WISはChronos-2の`0.21878482423570453`が6 models中最良でした。aggregateだけで採否を決めず、target別に単純baselineを上回る条件を確認します。

### Runtime

| 項目 | 値 |
| --- | ---: |
| Chronos warm test call count | 4 |
| Chronos warm p50 | 100.6970499875024 ms |
| Chronos warm p95 | 120.42497499205638 ms |
| process peak memory | 1,065,250,816 bytes |
| memory source | `os.process_peak_working_set` |
| total | 40.616660100000445秒 |

peak memoryはprocess全体であり、Chronos-2単独の増分ではありません。

## Known-future比較

正本: `artifacts/benchmark/benchmark-chronos2-known-load/result.json`（Git管理対象外）

7 modelsのaggregate結果です。`load_proxy`はorigin時点で確定済みの計画値を模したsynthetic known-future covariateであり、評価期間の実績値を後から渡すoracle leakageを許可するものではありません。

| Model | MAE | RMSE | MASE | Coverage | Width | WIS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Chronos-2 | 0.1691488806622826 | 0.25764632773710655 | 0.8187799631009623 | 0.8333333333333334 | 1.4527024229367573 | 0.15937026919725228 |
| Last value | 0.21972637499999967 | 0.29824453099910303 | 1.1593699689336212 | 0.16666666666666666 | 0.3891164666666668 | 0.3595693283333335 |
| Moving average | 0.3101050694444441 | 0.453287697012691 | 1.6967632908640093 | 0.25 | 0.5577706888888879 | 0.5105865783333337 |
| Seasonal naive | 0.3107074583333332 | 0.4434217075273362 | 1.7035669285863255 | 0.25 | 0.5731651333333333 | 0.5119552088888892 |
| Holt linear | 0.45165691970112737 | 0.7373507802531213 | 1.6399611426340082 | 0.375 | 0.2791307089797868 | 0.46557067232665755 |
| Linear regression covariates | 0.477616995786591 | 0.6553225886225554 | 2.5229702007731345 | 0.25 | 1.473554065879462 | 0.9331462115873409 |
| EWMA | 0.65636388868174 | 0.8492723491278269 | 3.2042095250251426 | 0.4166666666666667 | 1.048117900165642 | 0.8530498828905768 |

Chronos-2はaggregate MAE、RMSE、MASE、WISで7 models中1位でした。past-onlyに対して、MAEは18.17566785662254%、RMSEは9.421799177824903%、MASEは16.027664672979707%、WISは18.364079548480557%小さくなりました。coverageは同じ`0.8333333333333334`で、widthは15.586580210676278%小さくなりました。

Chronos-2のtarget別MAEは、電流`0.10921215304819736`、温度`0.22908560827636779`です。past-onlyから両targetで改善しましたが、電流はmoving-average `0.0823739722222222`、温度はHolt linear `0.14914157586799526`を上回っていません。今回のaggregate 1位を全targetでの優位と解釈しません。

### Runtime

| 項目 | 値 |
| --- | ---: |
| Chronos warm test call count | 4 |
| Chronos warm p50 | 112.99855000106618 ms |
| Chronos warm p95 | 134.7454250077135 ms |
| process peak memory | 1,063,981,056 bytes |
| memory source | `os.process_peak_working_set` |
| total | 45.12894639998558秒 |

## 判断と次のgate

今回の結果により、Chronos-2の固定snapshot、公式API、Banto adapter／tool smoke、共通rolling-origin runnerへの接続は成立しました。商用利用可能候補として評価を継続します。

次のgateはseed×horizon×context matrixです。最低でもseed数、origin数、horizon、contextを増やし、missing／stale、startup／shutdown、regime、fault sliceを追加します。clean savepointから再実行し、cold／warm、model単独resource、再現性を分離して記録します。実設備でknown-futureを評価する場合は、origin時点の計画値version／as-of証跡を必須にします。

これらが完了するまでは小標本・合成データ上の初期結果であり、Banto Hub shadow pilotや`product-candidate`への昇格根拠にはしません。TimesFM 3.0もweight licenseによりresearch-onlyの比較基準のままです。
