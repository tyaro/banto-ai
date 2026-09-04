# Toto 2.0 4M controlled evaluation 実測報告

実施日: 2026-09-05  
対象: Toto 2.0 4M、synthetic controlled acceptance 4-track
正本artifact（Git外）: `D:\develop\banto-ai\artifacts\toto2\ctl`

## 結論

固定したcontrolled acceptance契約に対して、4 matrixとcross-matrix analyzerが完了しました。acceptance statusは`pass`、4 tracks、80/80 cells、1,920/1,920 groups complete、1,440/1,440 paired deltas paired、availability deltaは全件0、`cross_model_ranking_allowed=false`です。

これは「契約どおりの比較artifactが揃った」ことを示す受入結果であり、実設備性能、異常検知精度、commissioning自動調整、Banto Hub write、production採用の証明ではありません。

## 実行と再現性の証跡

- formal code revision: `336afae6e2e7edf80d8e0c3b0f4834e76a5ff257`
- formal repository state: `git clean`
- CI: [GitHub Actions run 33888043470](https://github.com/tyaro/banto-ai/actions/runs/33888043470)（Python 3.12／3.14 success）
- 実行条件: synthetic、5 seeds（17／29／42／73／101）、horizon 15／30、context 64／120、origin 384をequipmentごとに1点／cell
- matrix構成: 4 track × 20 cells、2 equipment、3 target、5 baselines＋Toto native
- 環境: Python 3.14、CPUのみ、`local_files_only=true`、Toto 4M

初回のold revision `5795ed4`では、同一instantであるdatasetの`2026-01-01T00:06:24.000Z`とpredictionの`2026-01-01T00:06:24Z`を文字列比較したため、最初のpredictionでtimestamp mismatchとなり、結果は公開されませんでした。timestampをtimezone-aware UTC instant比較へ修正した`336afae`後に4 matrixを再実行し、formal acceptance passとなりました。旧artifactはlocal quarantineに残し、正式sourceには含めていません。

## Matrix結果

| matrix | track | cells | success / partial / failed | prediction | result.json SHA-256 |
| --- | --- | ---: | ---: | ---: | --- |
| m-a | control | 20 | 20 / 0 / 0 | 10,800 | `88cd3afdd25178808ddecb4b01c58e00e520bd67ab82dcf4ec6ba5b9856a16ae` |
| m-b | target-fault | 20 | 20 / 0 / 0 | 10,800 | `46d07a04f5b3455a6baf8f0ff95fb835b155aad3056af90013f31aeb300ee573` |
| m-c | target-quality | 20 | 20 / 0 / 0 | 10,800 | `552bd6b58c478f3ff17d59d4b5505d1941df0a9a3c28b4e8a788f25ccdeabe92` |
| m-d | covariate-quality | 20 | 20 / 0 / 0 | 10,800 | `349f8c2187a29339995ae0dddb392f874bd16ce4752238de2ba0fd2bf6f54144` |
| **合計** |  | **80** | **80 / 0 / 0** | **43,200** |  |

各matrixのbenchmark failureは0です。acceptance artifactのSHA-256は次のとおりです。

- `acceptance/result.json`: `dafd58b804d3c7d907a063669cf62a941e87c21e5dc7b80e66e877a8768bc992`
- `acceptance/summary.md`: `040e3d9c39885328b9c833d68fbc772f70b7535889f629000cba653e52372e7f`
- `acceptance/.complete`: `22b88556aa8ef7403828ea57c44179f6e2bba2912569207073908b827ddf5608`

`.complete`はresultとsummaryのhashを含み、markerのhashと実ファイルhashが一致することを確認しました。

## 実行コストの参考値

以下はToto単独の推論時間ではなく、benchmark process全体のcell runtime合計です。

| track | process runtime合計 | track内最大peak memory |
| --- | ---: | ---: |
| control | 137.54 s | 707.64 MiB |
| target-fault | 120.97 s | 707.49 MiB |
| target-quality | 131.71 s | 707.89 MiB |
| covariate-quality | 118.12 s | 707.16 MiB |

## 同一モデル内のpaired MAE delta

deltaは`degraded MAE - control MAE`です。単位が混在するため、target間を性能rankingしません。cross-model順位と採用判定も禁止です。

| track / target | n | mean | range | 内訳 |
| --- | ---: | ---: | ---: | --- |
| target-fault / motor current | 20 | +1.400180354 | +0.897004071 ～ +1.896781267 | 20 worsened |
| target-fault / motor temp | 20 | 0 | 0 ～ 0 | unchanged |
| target-fault / conveyor | 20 | 0 | 0 ～ 0 | unchanged |
| target-quality / motor current | 20 | +0.077163356 | -0.097491551 ～ +0.335682768 | 6 improve / 14 worsen |
| target-quality / motor temp | 20 | +0.041568463 | -0.317049414 ～ +0.152684666 | 3 improve / 17 worsen |
| target-quality / conveyor | 20 | 0 | 0 ～ 0 | unchanged |
| covariate-quality / motor current | 20 | +0.025224948 | -0.193942627 ～ +0.300238456 | 4 improve / 16 worsen |
| covariate-quality / motor temp | 20 | -0.012913400 | -0.077124907 ～ +0.066887581 | 11 improve / 9 worsen |
| covariate-quality / conveyor | 20 | 0 | 0 ～ 0 | unchanged |

target-faultのmotor current差は、fault eventがforecast内でknown futureではないことを確認するためのcontrolled sensitivityであり、異常検知性能の証拠ではありません。5 baselinesはpast-only covariateを消費しないため、covariate-qualityのdeltaは全件0です。これはrobustnessの証明ではなく、入力契約の確認です。

## Toto固定情報

- checkpoint revision: `8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9`
- model file: `model.safetensors`、16,582,848 bytes
- model SHA-256: `316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e`
- package: `toto-2==2.0.0`、`toto-models==1.0.0`
- model identity: Toto-2 4M 2.0.0
- 実行: Python 3.14 CPU、`local_files_only=true`

## 未評価と次ゲート

今回の範囲はsynthetic、5 seeds、horizon 15／30、context 64／120、origin 384、各equipment 1 origin／cell、4M CPUのみです。実設備への一般化、異常検知accuracy、commissioning自動調整、22M、production採用、Banto Hub write、制御系連携は未評価です。

次ゲートは、forecast benchmarkから分離した次の実験を慎重に定義することです。

1. event-aware anomaly scoringを、複数origin／regimeとevent単位のprecision、recall、lead time、誤警報で評価する。
2. commissioning baseline calibrationを、held-out／shadow replayとprofileのapprove／reject／rollback境界で評価する。
3. 再現性を複数origin／regimeで確認し、shadow／read-only Banto Hub境界を定義する。

すべてのartifact、customer data、checkpointはGitへ追加しません。Totoは引き続き`commercial-evaluation`に留め、evidence-completeness条件と事前登録した昇格閾値を満たすまで、cross-model順位や製品昇格を主張しません。
