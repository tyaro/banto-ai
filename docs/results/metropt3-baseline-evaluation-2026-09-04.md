# MetroPT-3 統計baseline評価結果（2026-09-04）

## 結論

固定したMetroPT-3の連続24時間窓、1設備、3 targetに対して、5つの統計baselineによる限定的なrolling-origin研究評価を完了した。これは公開実データの限定区間における研究結果であり、実設備一般の性能、製品適合性、異常検知性能を示さない。今回の評価はforecastのみで、故障・異常検知の判定は実施していない。

dataset fingerprintは`e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0`、run statusは`success`、failure countは0、test prediction countは3,600である。入力データのsource pin、標準化、Public-only quality gateは別途 [`metropt3-import-2026-09-04.md`](metropt3-import-2026-09-04.md) に記録している。

## 評価契約

| 項目 | 設定・結果 |
| --- | --- |
| dataset | MetroPT-3、`2020-02-21`固定24時間、`metropt3-apu-01` 1台 |
| targets | `tp3`、`oil_temperature`、`motor_current` |
| context / horizon | 120分 / 15分 |
| split | train / validation / test = 864 / 288 / 288（60秒bin） |
| origin stride | validation / test = 15 / 15 |
| origin上限 | validation / test = 16 / 16 |
| validation origins | 16件、indices=`[864, 879, 894, 924, 939, 954, 969, 984, 1014, 1029, 1044, 1059, 1074, 1104, 1119, 1134]` |
| test origins | 16件、indices=`[1152, 1167, 1182, 1212, 1227, 1242, 1257, 1272, 1302, 1317, 1332, 1347, 1362, 1392, 1407, 1422]` |
| covariates | past-only 11、known-future 0 |
| quantiles | `0.1` / `0.5` / `0.9` |
| calibration | 全5モデルとも`validation-residual-by-lead` |
| models | LastValue、SeasonalNaive（season length 60）、MovingAverage（window 15）、EWMA（alpha 0.3）、Holt linear（alpha 0.8、beta 0.2） |

validationはquantile calibration用で、`predictions.jsonl`に保存されるpredictionはtest splitだけである。test prediction countは`5 × 3 × 16 × 15 = 3,600`で、各modelは720件、各model-targetは240件となる。

## Testのmodel別metrics

値は`result.json`の原値を記載している。coverageは`nominal_interval_coverage`、intervalは`interval_width`である。

| model | count | MAE | RMSE | WIS | coverage | interval width | MASE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| last-value | 720 | 1.294350148809524 | 1.9380980487284603 | 1.1644673115079345 | 0.5736111111111111 | 2.8770251322751346 | 5.218733053219234 |
| seasonal-naive | 720 | 1.3433741071428569 | 2.063254310107907 | 1.0041477612433831 | 0.7097222222222223 | 4.050979894179895 | 5.52314531175878 |
| moving-average | 720 | 1.4288551995149907 | 1.8078673505333487 | 0.9945355257201621 | 0.6625 | 3.5418749823633155 | 5.830914915899948 |
| ewma | 720 | 1.3381698410660763 | 1.847498238380298 | 1.0295770274501177 | 0.6277777777777778 | 3.508734540787118 | 5.384128400714303 |
| holt-linear | 720 | 2.2455100006180406 | 3.6226751315810777 | 2.107689300309201 | 0.5291666666666667 | 3.9620198588926168 | 9.019913888702773 |

この限定条件では、全targetを混ぜた単一値からモデルの一般的な優劣は結論しない。MAE・RMSE・WIS・coverageは異なる性質を持ち、targetごとに単位も異なるため、以下のtarget別結果を分けて読む。

## Testのmodel-target別metrics

| model | target | unit | count | MAE | RMSE | WIS | coverage | interval width | MASE |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| last-value | tp3 | bar | 240 | 0.5955611111111111 | 0.7713545599662001 | 0.4422919312169307 | 0.4875 | 1.4044365079365073 | 5.682285736296819 |
| last-value | oil_temperature | ºC | 240 | 1.6522346230158738 | 2.0090489907324747 | 1.0848498677248677 | 0.65 | 3.6513690476190557 | 5.141786036509801 |
| last-value | motor_current | A | 240 | 1.6352547123015873 | 2.5763164470055635 | 1.9662601355820095 | 0.5833333333333334 | 3.5752698412698423 | 4.832127386851083 |
| seasonal-naive | tp3 | bar | 240 | 0.6646753968253969 | 0.7910927420182309 | 0.4322537169312171 | 0.6791666666666667 | 1.7773047619047622 | 6.341709450440842 |
| seasonal-naive | oil_temperature | ºC | 240 | 1.8015550595238092 | 2.415516347261486 | 1.2784356812169326 | 0.7333333333333333 | 4.921388888888893 | 5.6064741169475605 |
| seasonal-naive | motor_current | A | 240 | 1.563891865079365 | 2.5120724699289965 | 1.3017538855820117 | 0.7166666666666667 | 5.454246031746032 | 4.621252367887937 |
| moving-average | tp3 | bar | 240 | 0.6914495105820105 | 0.7740496990067898 | 0.44802471869488547 | 0.5791666666666667 | 1.4180510052910054 | 6.597162941044614 |
| moving-average | oil_temperature | ºC | 240 | 1.7327235449735439 | 1.9307682617246207 | 1.081211849647265 | 0.5333333333333333 | 3.5210423280423275 | 5.3922691151540745 |
| moving-average | motor_current | A | 240 | 1.862392542989418 | 2.3405414019747215 | 1.454370008818344 | 0.875 | 5.686531613756614 | 5.503312691501157 |
| ewma | tp3 | bar | 240 | 0.6099596952712995 | 0.7438534093999 | 0.4199398690670948 | 0.65 | 1.5078078730017603 | 5.819663526535114 |
| ewma | oil_temperature | ºC | 240 | 1.7343619206666443 | 2.0280928152029114 | 1.0979206812396418 | 0.625 | 3.6023088213271617 | 5.3973677719331965 |
| ewma | motor_current | A | 240 | 1.670187907260285 | 2.360777596619679 | 1.5708705320436147 | 0.6083333333333333 | 5.416086928032432 | 4.9353539036745975 |
| holt-linear | tp3 | bar | 240 | 1.033247673800527 | 1.5419012737533748 | 0.945704234069152 | 0.44583333333333336 | 1.649702508036041 | 9.858280551503706 |
| holt-linear | oil_temperature | ºC | 240 | 2.2186380545348423 | 3.2980164192651067 | 1.7095205827226614 | 0.7208333333333333 | 5.248795186744131 | 6.904444447516535 |
| holt-linear | motor_current | A | 240 | 3.4846442735187524 | 5.110474878833025 | 3.6678430841358027 | 0.42083333333333334 | 4.987561881897678 | 10.297016667088077 |

要点はtargetごとに異なる。例えばtp3ではEWMAのMAEが`0.6099596952712995`、WISが`0.4199398690670948`であり、seasonal-naiveのcoverageは`0.6791666666666667`だった。oil_temperatureではmoving-averageのRMSEが`1.9307682617246207`、coverageはseasonal-naiveが`0.7333333333333333`だった。motor_currentではseasonal-naiveのMAEが`1.563891865079365`、moving-averageのcoverageが`0.875`だった。一方、Holt linearはこのrunの3 targetでMAE・RMSE・MASEが高く、coverageもtargetにより異なる。これらは16 test originsの限定結果であり、モデルの一般的な順位や実設備への採用判断ではない。

## Quality、provenance、leakage boundary

Public-only quality gateはPASSで、観測recordは1,440件、equipmentは1件である。sourceはUCI MetroPT-3の固定済み公開archiveで、データのlicenseはCC BY 4.0、リポジトリのMIT licenseとは別である。source archive、member hash、transform、timezone assumption、60秒bin、split、no-label leakageの証跡は取込結果とsource manifestに保持する。

splitはtrain `(0, 864)`、validation `(864, 1152)`、test `(1152, 1440)`である。future covariatesは空で、targetのactual valueはtestの評価labelとしてのみ使い、actual futureを入力へ渡していない。known-future contractそのものは今回テストしていない。failure reportやlabelを入力特徴量へ使う評価でもない。

benchmark artifactは`artifacts/benchmark/benchmark-metropt3-baselines/`に生成され、raw／derived public dataと同じくGit管理外のartifact boundaryに置く。

## 再現性・実行証跡

primary runは、detached clean worktreeのcommit `b9b0a678f1ef9ef685dc450824a4705ff9881cf0`から実行した。`result.json`の`code_revision.status`は`git`、`code_revision.dirty`は`false`、`code_revision.diff_sha256`は`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`である。`predictions.jsonl`のSHA-256は`6894ecd0a24c057f13afcf505baa30a96b04a3d4203c6e24a964691d2c4520d0`で、以前の実行とprediction、metrics、provenanceが一致した。

## Runtime

clean commitからの`result.json`のruntimeは次の通りである。秒数、latency、memoryはPython／OS／実行環境に依存する測定値であり、モデルの性能保証や実設備の性能保証ではない。

| 項目 | 値 |
| --- | ---: |
| validation_seconds | 0.8732296999951359 |
| test_seconds | 2.04535770000075 |
| total_seconds | 16.17603400000371 |
| p50_latency_ms | 0.8707499946467578 |
| p95_latency_ms | 2.8196649916935708 |
| peak_memory_bytes | 47255552 |
| memory_source | `os.process_peak_working_set` |
| Python | 3.14.0 |
| OS | Windows 11 |

## 次の工程

次は同じconfig契約、dataset fingerprint、split、target／horizon条件でChronos-2とTimesFM 3.0を追加比較する。ただし、モデル依存のインストール、license、外部cache、CPU負荷は別評価として記録する。今回の統計baselineはモデル比較の共通基準であり、今回の数値だけからモデルの一般的な優劣、製品適合性、異常検知能力を主張しない。
