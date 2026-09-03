# TimesFM 3.0／統計baseline比較結果

実測日: 2026-09-04

本書は、同一の合成データ、rolling-origin、target、context、horizonで実行した2つのscenarioを記録します。これは研究用の限定評価であり、実設備性能、製品採用、本番効果を示すものではありません。

## 結論

- `past-only`では、TimesFM 3.0の`motor_temperature`のMAEが`0.07884 degC`で対象model中最良でした。一方、`motor_current`のMAEは`0.16951 A`で、moving-averageの`0.08237 A`などに劣りました。
- `known-load`では、TimesFM 3.0のMAEは`motor_temperature`が`0.08582 degC`、`motor_current`が`0.19488 A`でした。linear regressionは`motor_current`が`0.12950 A`、`motor_temperature`が`0.82574 degC`であり、両targetに対して一貫して優位ではありません。
- この小標本では、known-loadを与えたTimesFM 3.0の点予測MAEはpast-onlyから改善しませんでした。WISはこのrunでは両targetで数値上低下しましたが、対象、origin、データ生成条件が限定されるため一般化できません。
- TimesFM 3.0は本比較に含める研究referenceですが、weightsはresearch-only／non-commercialです。採用判断は行わず、Phase 2も完了扱いにしません。

## 1. 評価条件とprovenance

| 項目 | past-only | known-load |
| --- | --- | --- |
| config | `benchmark-timesfm3-baselines-past-only.json` | `benchmark-timesfm3-known-load.json` |
| run ID | `benchmark-timesfm3-baselines-past-only` | `benchmark-timesfm3-known-load` |
| dataset | `synthetic-motor-small` | `synthetic-motor-small` |
| dataset fingerprint | `6427bd2da97958f04b8c34e3a09a101d8bc3fc85eced003aaf022e81567312b6` | 同左 |
| seed | `42` | `42` |
| context／horizon | `12`／`3` | `12`／`3` |
| validation origin | 各equipment `[36, 45]` | 各equipment `[36, 45]` |
| test origin | 各equipment `[48, 57]` | 各equipment `[48, 57]` |
| origin選択 | stride `3`、最大 `2` | stride `3`、最大 `2` |
| status／failures | `success`／`0` | `success`／`0` |
| prediction count | `144` | `168` |
| code revision | `4e4473898e86589aae58aa8852816834bc5d9057`、dirty=false | 同左 |

両scenarioとも、各equipmentのvalidationは2 origins、testは2 originsです。各test originからhorizon 3点を予測するため、各equipment-targetのtest点数は6、各model-targetの集計点数は12です。known-loadでは、origin時点で将来の`load_proxy`を計画値として確実に取得できるという、syntheticなoracle-style／planned-load仮定を置きます。これは実績値の先読みではなく、本番で効果が得られることを意味しません。past-onlyとknown-loadは別scenarioとして扱い、結果を混同しません。

past-onlyの`load_proxy`はpast-only入力で、known-futureはありません。known-loadでは`load_proxy`をknown-futureとしてcontext+horizonちょうど渡し、split／test範囲外へは越えません。known-loadの全modelには同じknown-future seriesを渡しています。統計baselineはvalidation residual quantile、TimesFM 3.0はnative quantile、linear regressionはcovariate付き設定です。

### 数値の表示規則

以下の主表はartifactの`metrics.by_model_target`を使用しています。MAE、RMSE、MASE、WIS、interval widthは小数第5位まで、`nominal_interval_coverage`は割合をパーセント表示して小数第2位までに丸めています。TimesFM 3.0と統計baselineのlatencyは小数第1位のms、linear regressionのlatencyは小数第2位のms、process peakは10進GBで小数第2位に丸めています。`result.json`には元の浮動小数点値が保存されています。

単位の異なる`motor_current`（A）と`motor_temperature`（degC）を混ぜる`by_model`／`aggregate`は、優劣判定に使用しません。以下ではmodel×targetを分けて比較します。`by_model_equipment_target`についても、equipmentごとの所属と単位を保った結果が生成されています。

## 2. past-onlyの結果

`load_proxy`の将来値を使用しない標準scenarioです。

| model | target | unit | n | MAE | RMSE | MASE | WIS | nominal interval coverage | interval width |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| last-value | motor_current | A | 12 | 0.11361 | 0.12539 | 0.45204 | 0.11364 | 8.33% | 0.06669 |
| last-value | motor_temperature | degC | 12 | 0.32584 | 0.40271 | 1.86670 | 0.60550 | 25.00% | 0.71154 |
| seasonal-naive | motor_current | A | 12 | 0.08358 | 0.09856 | 0.31306 | 0.07872 | 25.00% | 0.07279 |
| seasonal-naive | motor_temperature | degC | 12 | 0.53784 | 0.61930 | 3.09408 | 0.94519 | 25.00% | 1.07354 |
| moving-average | motor_current | A | 12 | 0.08237 | 0.09989 | 0.29945 | 0.07648 | 25.00% | 0.04200 |
| moving-average | motor_temperature | degC | 12 | 0.53784 | 0.63321 | 3.09408 | 0.94469 | 25.00% | 1.07354 |
| ewma | motor_current | A | 12 | 0.58882 | 0.80022 | 2.07237 | 0.62383 | 33.33% | 0.26077 |
| ewma | motor_temperature | degC | 12 | 0.72391 | 0.89564 | 4.33605 | 1.08227 | 50.00% | 1.83547 |
| holt-linear | motor_current | A | 12 | 0.75417 | 1.01971 | 2.55784 | 0.69540 | 25.00% | 0.34438 |
| holt-linear | motor_temperature | degC | 12 | 0.14914 | 0.21807 | 0.72208 | 0.23574 | 50.00% | 0.21388 |
| timesfm3 | motor_current | A | 12 | 0.16951 | 0.20696 | 0.70005 | 0.22808 | 66.67% | 2.21392 |
| timesfm3 | motor_temperature | degC | 12 | 0.07884 | 0.09856 | 0.55336 | 0.11855 | 75.00% | 1.30297 |

このscenarioでは、温度のMAEだけを見るとTimesFM 3.0が最良です。電流ではmoving-averageが最良であり、TimesFM 3.0を全targetに対する一律の改善とは解釈できません。

## 3. known-loadの結果

`load_proxy`の計画値をorigin時点で確実に取得できる設備を模した、synthetic known-future／oracle-styleの別scenarioです。実設備でこの契約が成立するかは別途検証が必要です。

| model | target | unit | n | MAE | RMSE | MASE | WIS | nominal interval coverage | interval width |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| last-value | motor_current | A | 12 | 0.11361 | 0.12539 | 0.45204 | 0.11364 | 8.33% | 0.06669 |
| last-value | motor_temperature | degC | 12 | 0.32584 | 0.40271 | 1.86670 | 0.60550 | 25.00% | 0.71154 |
| seasonal-naive | motor_current | A | 12 | 0.08358 | 0.09856 | 0.31306 | 0.07872 | 25.00% | 0.07279 |
| seasonal-naive | motor_temperature | degC | 12 | 0.53784 | 0.61930 | 3.09408 | 0.94519 | 25.00% | 1.07354 |
| moving-average | motor_current | A | 12 | 0.08237 | 0.09989 | 0.29945 | 0.07648 | 25.00% | 0.04200 |
| moving-average | motor_temperature | degC | 12 | 0.53784 | 0.63321 | 3.09408 | 0.94469 | 25.00% | 1.07354 |
| ewma | motor_current | A | 12 | 0.58882 | 0.80022 | 2.07237 | 0.62383 | 33.33% | 0.26077 |
| ewma | motor_temperature | degC | 12 | 0.72391 | 0.89564 | 4.33605 | 1.08227 | 50.00% | 1.83547 |
| holt-linear | motor_current | A | 12 | 0.75417 | 1.01971 | 2.55784 | 0.69540 | 25.00% | 0.34438 |
| holt-linear | motor_temperature | degC | 12 | 0.14914 | 0.21807 | 0.72208 | 0.23574 | 50.00% | 0.21388 |
| timesfm3 | motor_current | A | 12 | 0.19488 | 0.22754 | 0.76113 | 0.18463 | 25.00% | 0.75671 |
| timesfm3 | motor_temperature | degC | 12 | 0.08582 | 0.11153 | 0.55558 | 0.05754 | 66.67% | 0.30835 |
| linear-regression-covariates | motor_current | A | 12 | 0.12950 | 0.15568 | 0.50146 | 0.17502 | 50.00% | 0.35691 |
| linear-regression-covariates | motor_temperature | degC | 12 | 0.82574 | 0.91360 | 4.54449 | 1.69128 | 0.00% | 2.59020 |

known-loadでTimesFM 3.0の点予測は、past-only比で電流・温度ともMAEが改善しませんでした。一方、WISは電流`0.22808`から`0.18463`、温度`0.11855`から`0.05754`へ低下しました。これは今回の小標本におけるinterval評価の変化であり、known-futureを与えれば本番性能が改善するという根拠ではありません。linear regressionも電流ではTimesFM 3.0を下回るMAEでしたが、温度では大きく劣り、全targetでの一貫した優位性はありません。

## 4. latencyとmemory

latencyはartifactのmodel別forecast callのp50です。各runのtest origin数が少ないため、性能SLAの根拠にはしません。

| scenario | TimesFM 3.0 p50 | 統計baseline p50の範囲 | linear regression p50 |
| --- | ---: | ---: | ---: |
| past-only | 352.8 ms | 0.7～1.0 ms | — |
| known-load | 312.8 ms | 0.4～0.8 ms | 2.28 ms |

統計baselineは概ね`0.4～1.0 ms`、known-loadのlinear regressionはartifact上`2.283... ms`です。process peakはpast-only `2.76 GB`、known-load `2.97 GB`でした。これはプロセス全体のpeak working setであり、TimesFMモデル単独のmemory使用量ではありません。モデル単独のmemoryとcold／warm latencyは次工程で分離測定します。

## 5. 限界と採用判断

各model-targetのtestは12点、各equipmentは2 origins×horizon 3、validationも各equipment 2 originsです。intervalの校正に使う母数が極めて小さいため、coverageとWISは暫定値です。さらに、データは単一の合成generator、単一seed、短いcontext／horizonに限定されています。`by_model`／`aggregate`は単位混在を含むため、物理量の優劣判定には使いません。

TimesFM 3.0 weightsの利用条件はresearch-only／non-commercialです。リポジトリのMIT licenseはweightsの利用制限を変更しません。この結果だけで採用判断はできず、Phase 2完了とも扱いません。

## 6. 次工程

1. seed、horizon、context length、rolling originを増やし、点予測とinterval校正の不確実性を評価する。
2. model単独のmemory、cold／warm latency、batch条件をプロセスpeakから分離して測定する。
3. Chronos-2など、ライセンス適合性を確認できる候補を同一result契約・同一originで比較する。候補ごとにweights／code licenseをrun単位で記録する。
4. known-loadは、実設備で計画値がorigin時点に利用可能で、実績値と区別されたseries契約を検証してから評価する。契約が成立しない場合はpast-onlyを標準scenarioとする。
5. 複数equipment、regime、欠損、faultを含む評価へ拡張し、target別・equipment-target別の結果を維持する。
