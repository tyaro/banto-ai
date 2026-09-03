# TimesFM 3.0 小規模matrix実測結果

実測日: 2026-09-04

本書は、合成datasetのseed、forecast horizon、context lengthを変えた8 cellについて、TimesFM 3.0と5つの統計baselineを同一のrolling-origin契約で比較した実測結果です。これは研究用の限定評価であり、実設備性能、製品採用、本番効果を示すものではありません。

## 結論

- TimesFM 3.0は`motor_temperature`の4条件すべてでMAEが最良でした。MAEはh1／c6 `0.088840`、h1／c12 `0.047715`、h3／c6 `0.169926`、h3／c12 `0.087544 degC`です。
- `motor_current`ではTimesFM 3.0は4条件すべて6モデル中4位でした。MAEは順に`0.193357`、`0.106948`、`0.161160`、`0.137624 A`です。moving-averageが4条件すべて最良で、h1はcontextによらず`0.076125 A`、h3はcontextによらず`0.074011 A`でした。
- TimesFM 3.0のcontext 12はcontext 6に比べ、MAEが電流h1で`44.69%`、電流h3で`14.60%`、温度h1で`46.29%`、温度h3で`48.48%`低下しました。ただし、2 seed、少数origin、単一の合成generatorに限った傾向であり、contextを長くすれば一般に同程度改善するとは結論できません。
- TimesFM 3.0のweightsはresearch-only／non-commercialです。今回の結果から製品採用はできず、Phase 2も完了扱いにしません。

## 1. 評価条件とprovenance

| 項目 | 実測値 |
| --- | --- |
| matrix ID | `benchmark-matrix-timesfm3-small` |
| code revision | `6ba290a103ae31395573128b406a79ed2bda94c5`、dirty=false |
| axes | seeds `[17, 42]` × horizons `[1, 3]` × context lengths `[6, 12]` |
| cell数 | 8 |
| status | `success` |
| 成功／失敗 | 8／0 |
| targets | `motor_current`（A）、`motor_temperature`（degC） |
| models | last-value、seasonal-naive、moving-average、EWMA、Holt linear、TimesFM 3.0 |
| covariate | `load_proxy`はpast-only、known-futureなし |
| equipment | `conveyor-01`、`motor-01` |
| validation origin | 全cell・各equipmentで`[36, 45]` |
| test origin | 全cell・各equipmentで`[48, 57]` |
| origin設定 | validation／testともstride 3、最大2 origins |

seedはrun metadataだけでなくgeneratorへ反映されています。matrix artifactに記録されたdataset fingerprintと観測ファイル本体のSHA-256は次のとおりで、seed間でいずれも異なります。

| seed | dataset fingerprint | `observations.jsonl` SHA-256 |
| ---: | --- | --- |
| 17 | `9ed9567dff3a597c0254c3a9549bb93773d527e1948d51af086e2100c224043c` | `328bc39dcfcef7c5733bde3e4ee606a21a32de08862a3309cce4b8f819656dbc` |
| 42 | `4f7ee8abaf30576b85536b5c85277570148b560f31f6f01a11196c4a04958b3e` | `c3870dc21750cd16ab808fc1a6b483aed8a310e02739c03101d2e9b41e7022d2` |

各cellでは2 equipment × 2 test originsを評価します。このため、各model-targetのcell内点数はhorizon 1で4点、horizon 3で12点です。以下のseed macroでは2 cell分をまとめるため、horizon 1の`total point count`は8、horizon 3は24です。validationも全cell・各equipmentで2 originsだけです。

### 数値の表示規則

MAE、MASE、WIS、interval widthはartifactの値を小数第6位に丸めます。coverageは百分率へ変換して小数第2位、latencyは小数第1位のms、時間は小数第1位の秒、process peakは10進GBで小数第2位に丸めます。割合の低下率は丸め前のMAEから計算し、小数第2位に丸めます。正確な浮動小数点値はartifactの`result.json`を正とします。

主表はmatrix resultのmodel×target×unit×horizon×context別macro summaryを使います。各値は2 seedのcell metricを同じ重みで平均したcell-macroであり、raw predictionを再集計したpooled metricではありません。単位の異なるAとdegCを混ぜる`aggregate`／`by_model`は優劣判定に使用しません。

## 2. MAE macro比較

### motor_current（A）

| model | h1／c6 | h1／c12 | h3／c6 | h3／c12 |
| --- | ---: | ---: | ---: | ---: |
| last-value | 0.099835 | 0.099835 | 0.089851 | 0.089851 |
| seasonal-naive | 0.090213 | 0.090213 | 0.081829 | 0.081829 |
| moving-average | 0.076125 | 0.076125 | 0.074011 | 0.074011 |
| ewma | 0.604969 | 0.571331 | 0.584211 | 0.583722 |
| holt-linear | 1.822749 | 0.458259 | 3.157124 | 0.748771 |
| timesfm3 | 0.193357 | 0.106948 | 0.161160 | 0.137624 |

moving-averageが全4条件で最良でした。TimesFM 3.0は全条件でmoving-average、seasonal-naive、last-valueに続く4位です。context 12でTimesFM 3.0の差は縮まりましたが、単純なbaselineを上回ってはいません。

### motor_temperature（degC）

| model | h1／c6 | h1／c12 | h3／c6 | h3／c12 |
| --- | ---: | ---: | ---: | ---: |
| last-value | 0.161790 | 0.161790 | 0.322599 | 0.322599 |
| seasonal-naive | 0.573662 | 0.573662 | 0.526109 | 0.526109 |
| moving-average | 0.365300 | 0.365300 | 0.526109 | 0.526109 |
| ewma | 0.625443 | 0.559340 | 0.786252 | 0.709965 |
| holt-linear | 0.145179 | 0.088973 | 0.265714 | 0.142604 |
| timesfm3 | 0.088840 | 0.047715 | 0.169926 | 0.087544 |

TimesFM 3.0が全4条件で最良でした。次点は全条件でHolt linearです。ただし、この結果は短い合成温度系列に限られ、regime、fault、欠損、実設備ノイズに対する優位性は未確認です。

## 3. TimesFM 3.0のinterval指標

TimesFM 3.0はnative quantileを使用します。次表も2 seedのcell-macroです。

| target | unit | horizon | context | n | MASE | WIS | nominal 80% coverage | interval width |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| motor_current | A | 1 | 6 | 8 | 0.829213 | 0.236508 | 75.00% | 2.339297 |
| motor_current | A | 1 | 12 | 8 | 0.419429 | 0.097643 | 75.00% | 0.834372 |
| motor_current | A | 3 | 6 | 24 | 0.657541 | 0.262260 | 83.33% | 3.008079 |
| motor_current | A | 3 | 12 | 24 | 0.546544 | 0.207267 | 62.50% | 2.065490 |
| motor_temperature | degC | 1 | 6 | 8 | 0.526353 | 0.049387 | 50.00% | 0.175226 |
| motor_temperature | degC | 1 | 12 | 8 | 0.288766 | 0.052676 | 87.50% | 0.544913 |
| motor_temperature | degC | 3 | 6 | 24 | 1.026342 | 0.114156 | 25.00% | 0.274287 |
| motor_temperature | degC | 3 | 12 | 24 | 0.535065 | 0.119253 | 79.17% | 1.253449 |

validation originは各equipmentで2つだけです。test点数もhorizon 1でseed macro合計8点、horizon 3で24点に限られます。coverageとWISは暫定値であり、nominal 80%へ安定して適合しているとは主張しません。context変更に伴ってinterval widthとcoverageが同じ方向へ動いていない条件もあるため、点予測MAEの改善とinterval校正を分けて検証する必要があります。

## 4. latency、memory、実行時間

| 指標 | 実測値 |
| --- | ---: |
| TimesFM 3.0 test-call p50のcell間範囲 | 428.1～1020.1 ms |
| TimesFM 3.0 test-call p95のcell間範囲 | 573.0～1403.0 ms |
| test forecast call数 | 各cell 4 calls |
| 8 cellの`total_seconds`合計 | 65.0 s |
| process peak working set | 約2.97 GB |

latency分位点は各cellわずか4 callsから算出されており、SLAや安定した分布の推定には使えません。matrixではTimesFM adapterを共有しています。展開順の最初のcell（seed 17、horizon 1、context 6）はvalidation処理にmodel cold startを含み、後続cellは同一processのwarm instanceを使います。そのため、cell間latencyや`total_seconds`は独立したcold run同士の比較ではありません。

process peak `2,967,158,784 bytes`は全cellで同じOS processのhigh-water markです。TimesFMモデル単独のmemoryでも、cellごとの追加memoryでもありません。`total_seconds`合計約65.0秒も、同一process、今回のPC、今回のsmall matrixに限定された値です。

## 5. 限界と採用判断

- datasetは単一generatorの2 seedsだけで、実設備を代表しません。
- originはvalidation／testとも各equipment 2つで、interval校正、seed分散、regime差を評価するには不足しています。
- contextは6／12、horizonは1／3だけで、長期予測や異なるsampling cadenceは未評価です。
- fault、欠損、stale data、regime別slice、cross-equipment一般化は未評価です。
- macroは2 seedのcell metricを同重みで平均した値であり、pooled metricではありません。
- AとdegCを混ぜる`aggregate`／`by_model`の値はモデル判断に使っていません。
- cold／warm latencyとモデル単独memoryが分離されていません。

TimesFM 3.0のweightsはresearch-only／non-commercialです。MITで公開する`banto-ai`のコード／文書ライセンスはweightsの制限を緩和しません。温度で有望な傾向は得られましたが、電流では単純なmoving-averageに劣り、評価規模と利用条件の両面から製品採用はできません。Phase 2の完了条件も満たしていません。

## 6. 次工程

1. seedsを最低5以上へ増やし、seed間のばらつきと信頼区間を確認する。
2. validation／test originsを増やし、horizonとcontext lengthの候補も追加する。
3. cold process、共有warm instance、batch条件を分離し、モデル単独memoryとlatencyを測定する。
4. 欠損、stale、regime、fault別sliceを追加し、target／equipment-target別に評価する。
5. Chronos-2などライセンス適合候補を、同じdataset、origin、result契約、単位別metricで比較する。
6. 実設備評価へ進む場合は、データ取得、計画値、単位、sampling、欠損の契約を先に検証する。
