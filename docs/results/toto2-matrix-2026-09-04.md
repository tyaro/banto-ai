# Toto 2.0 4M 小規模matrix実測結果

実測日: 2026-09-04

本書は、合成motor／conveyor datasetのseed、forecast horizon、context lengthを変えた8 cellについて、Toto 2.0 4Mと5つの統計baselineを同一のrolling-origin契約で比較した実測結果である。これは2 seed、2 equipment、CPUのみの限定評価であり、実設備性能、製品採用、Banto Hub／PLC writeを示すものではない。

## 結論

- matrixは`success`、8/8 cell success、partial 0、failed 0で完了した。Toto 2.0のforecast failureは0件である。
- `motor_current`のMAE順位は、h15／c64が3/6、h15／c120が4/6、h30／c64が3/6、h30／c120が1/6だった。h30／c120のMAEはTotoが最良である。電流のWIS順位は2/6、2/6、3/6、2/6で、最良WISは各条件でlast-value（h30／c64を含む）だった。
- `motor_temperature`のMAE順位はh15／c64が4/6、h15／c120が4/6、h30／c64が1/6、h30／c120が1/6だった。WISは4条件すべて1/6である。ただし、短い合成系列の2 seedに限った結果であり、実設備一般化や安定したinterval校正を意味しない。
- context=64から120へのMAE変化は、current h15が`+11.50%`、current h30が`-35.44%`、temperature h15が`-12.08%`、temperature h30が`-24.31%`だった。WISは4条件すべて低下したが、context=120はpatch_size=32のためeffective input length=128となり、先頭8点の未観測paddingを含む。単純な観測長の効果だけとは解釈しない。
- この結果でTotoを`product-candidate`へ昇格せず、Phase 2完了とも扱わない。利用区分は引き続き`commercial-evaluation`である。

## 1. 正本とprovenance

正本はGit管理対象外の次のmatrix resultである。cell resultは正本の`cells[].result_path`が参照する、同じmain workspaceのartifactを用いた。

| 項目 | 実測値 |
| --- | --- |
| matrix ID | `benchmark-matrix-toto2-small` |
| 正本 | `artifacts/toto2/matrix/benchmark-matrix-toto2-small/result.json` |
| 正本 SHA-256 | `3de9b683df25a871bcc1000f6a75ba21a301f55dad316cc15bc3675441959784` |
| 正本 size | `78,629 bytes` |
| status | `success` |
| cells | 8 total、8 successful、0 partial、0 failed |
| code revision | `1c42926903bf3235ef8b86badf0491a5575b4060` |
| worktree | `dirty=false` |
| empty diff hash | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| artifactのGit状態 | Git管理対象外 |

packageは`toto-2==2.0.0`、`toto-models==1.0.0`、checkpointは`Datadog/Toto-2.0-4m@8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9`に固定した。code／weightsはApache-2.0で、今回の利用区分は`commercial-evaluation`である。実行はCPU、batch=1、offline、local-only、固定外部cacheで行った。

## 2. 評価条件

| 項目 | 実測条件 |
| --- | --- |
| axes | seeds `[17, 42]` × horizons `[15, 30]` × context lengths `[64, 120]` |
| equipment | `motor-01`、`conveyor-01`の2設備 |
| dataset | 各seed 480 samples／equipment、960 records |
| split | train 288、validation 96、test 96 samples／equipment |
| validation origin | h15: `[288, 363]`、h30: `[288, 348]` |
| test origin | h15: `[384, 459]`、h30: `[384, 444]` |
| targets | `motor_current`（A）、`motor_temperature`（degC） |
| covariate | `load_proxy`はpast-only、known-futureなし |
| models | 5 baselines + Toto 2.0 = 6 models |
| quantile | Toto native p10／p50／p90、nominal coverage 80% |

各originの選択値は各equipmentで同じである。各cellのToto test forecast callは4回（2 equipment × 2 test origins）、8 cell合計32回だった。全6 modelのpredictionは8,640件、Toto分は1,440件、failureは0件である。

context=64はeffective input length=64、padding 0。context=120はpatch_size=32に合わせてeffective input length=128、先頭8点が未観測padding、mask=falseである。paddingに実測値を使っていない。入力のmissing／stale／irregular／nonfiniteを許容する検証ではない。test dropoutは未使用の`vibration_feature`へ置いており、今回のmatrixは欠損耐性評価ではない。

seedごとのdataset fingerprintと`observations.jsonl` SHA-256は次のとおりで、2 seedの観測内容は異なる。

| seed | dataset fingerprint | `observations.jsonl` SHA-256 |
| ---: | --- | --- |
| 17 | `d683ff6ccc6d760ac7d1f5b09b0c7b648368cc15e5c8bb60cad1e7d0c5c62d21` | `0bcdbf65e99f4b5ef62f309ebf517f0f59267ac0174ffa39e6d931a4eb896740` |
| 42 | `ce464d618f923c10d9ed543e2f5ee54738b1f235088e9551733087532993eb16` | `5ed5ca824e3fe21522c2f91e41ca1c037d1166de102dd887d5b8ff33f443a439` |

## 3. Toto 2.0 target metrics

次表はmatrix resultの`model=toto2`、`target_signal_key`、horizon、context別macro summaryである。各値は2 seedのcell metricを同じ重みで平均したcell-macroで、raw predictionをpoolして再計算した値ではない。MAE、RMSE、MASE、WIS、interval widthの単位はtargetに依存し、coverageは比率である。

| target | horizon | context | MAE | RMSE | MASE | coverage | width | WIS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| motor_current (A) | 15 | 64 | 0.06990157314809163 | 0.08018017911881262 | 0.49768233897228986 | 0.8833333333333333 | 2.396187496185303 | 0.18535192643958195 |
| motor_current (A) | 15 | 120 | 0.0779369160120646 | 0.09281069372027143 | 0.5419405221518427 | 0.9833333333333333 | 1.1201981743176779 | 0.10094391392881608 |
| motor_current (A) | 30 | 64 | 1.0048316278832754 | 1.443115509968757 | 6.0543462052338235 | 0.6416666666666666 | 4.992005721728007 | 0.936344406264623 |
| motor_current (A) | 30 | 120 | 0.6487267033140818 | 0.8610191531326556 | 4.044124295566806 | 0.9541666666666666 | 3.291176343957583 | 0.44842882010885865 |
| motor_temperature (degC) | 15 | 64 | 1.278612267920939 | 2.7920903272626623 | 24.489602533642845 | 0.7583333333333333 | 1.8399276892344156 | 0.9612175404391818 |
| motor_temperature (degC) | 15 | 120 | 1.1241167561157226 | 2.431124567087817 | 21.514418266536445 | 0.7250000000000001 | 1.4874085108439128 | 0.8556565824598527 |
| motor_temperature (degC) | 30 | 64 | 0.9427341044728598 | 1.4096782659192586 | 14.805398990571849 | 0.7208333333333333 | 3.0861760775248213 | 0.6729737582448325 |
| motor_temperature (degC) | 30 | 120 | 0.7135191171000164 | 1.542191804910232 | 12.61369121192968 | 0.8458333333333334 | 3.600066335995992 | 0.6237563177244398 |

同一target、horizon、context内での6 models中順位と最良baselineは次のとおり。

| target | horizon | context | Toto MAE順位 | MAE最良 | Toto WIS順位 | WIS最良 |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| motor_current | 15 | 64 | 3/6 | moving-average `0.05433319666666664` | 2/6 | last-value `0.08810488288888886` |
| motor_current | 15 | 120 | 4/6 | moving-average `0.05433319666666664` | 2/6 | last-value `0.08810488288888886` |
| motor_current | 30 | 64 | 3/6 | EWMA `0.7097483595317416` | 3/6 | last-value `0.4038088923333335` |
| motor_current | 30 | 120 | 1/6 | Toto `0.6487267033140818` | 2/6 | last-value `0.4038088923333335` |
| motor_temperature | 15 | 64 | 4/6 | EWMA `1.0154068622037942` | 1/6 | Toto `0.9612175404391818` |
| motor_temperature | 15 | 120 | 4/6 | EWMA `1.015406862211621` | 1/6 | Toto `0.8556565824598527` |
| motor_temperature | 30 | 64 | 1/6 | Toto `0.9427341044728598` | 1/6 | Toto `0.6729737582448325` |
| motor_temperature | 30 | 120 | 1/6 | Toto `0.7135191171000164` | 1/6 | Toto `0.6237563177244398` |

## 4. CPU runtimeとmemory

Totoのlatencyは各cellの4 test forecast callから計算した。次の`total_seconds`はcell全体、p50／p95はTotoのmodel callであり、単位はそれぞれ秒／msである。

| seed | horizon | context | Toto p50 (ms) | Toto p95 (ms) | cell total (s) | Toto calls |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 17 | 15 | 64 | 254.6400499995798 | 400.1389750032103 | 66.72652649998781 | 4 |
| 17 | 15 | 120 | 268.7723000126425 | 674.4041199810453 | 5.6477517999883275 | 4 |
| 17 | 30 | 64 | 172.4390500166919 | 543.1004050085901 | 4.714425200014375 | 4 |
| 17 | 30 | 120 | 1071.7355999950087 | 1901.820460008457 | 11.563655600009952 | 4 |
| 42 | 15 | 64 | 230.20044999429956 | 770.3912650031268 | 5.258269300014945 | 4 |
| 42 | 15 | 120 | 345.4088500002399 | 661.561145003361 | 5.059567200019956 | 4 |
| 42 | 30 | 64 | 255.5162499920698 | 421.0080600052606 | 5.276834100019187 | 4 |
| 42 | 30 | 120 | 175.0840999884531 | 426.03623999893887 | 4.396137000003364 | 4 |

8 cellの`total_seconds`合計は`108.64316670005792 s`だった。Toto p50は`172.4390500166919`～`1071.7355999950087 ms`、平均`346.72458124987315 ms`、p95は`400.1389750032103`～`1901.820460008457 ms`、平均`724.8075837514988 ms`だった。process peakは全cell共通のOS process high-water markで`741,568,512 bytes`であり、Toto model単独の増分memoryではない。

最初のcell（seed 17／horizon 15／context 64）の`66.72652649998781 s`はvalidationとmodel load／初回処理を含む。cell間は共有instanceを使うため、後続cellのlatencyは独立したcold-start比較ではない。p50／p95は各cell4 callの小標本であり、SLAや安定した分布の推定には使わない。

## 5. 制約、判断、比較境界

- datasetは単一generator、2 seed、2 equipment、各equipment validation／test各2 origins、CPUのみである。合成データは実設備挙動を代表しない。
- Totoはnative p10／p50／p90を使い、coverageのnominalは80%だが、今回の少数originから校正済みとは判断しない。
- context=120は128点へpaddingされるため、context=64との差を観測長だけの効果として解釈しない。
- test dropoutは`vibration_feature`のため、対象target／past-only covariateの欠損耐性を測っていない。missing／stale／fault／regime sliceは別gateで評価する。
- TimesFM／Chronosの既存small matrixはdataset length、horizon、contextが異なるため、今回の数値と直接優劣比較しない。MetroPT-3の同一契約比較も本書とは別reportである。
- Toto 2.0 4Mは`commercial-evaluation`を継続し、product-candidate、Phase 2完了、顧客PoC、本番shadow、Banto Hub／PLC writeへ進めない。

## 6. 次のgate

1. seedを5以上、originを拡大し、seed間分散と信頼区間を確認する。
2. missing／stale／fault／regime sliceを別シナリオとして追加し、今回のclean forecast matrixと混同しない。
3. model-onlyのcold／warm latency、resource、memoryを分離して測定する。
4. Toto 2.0 22Mを同じ安全境界で評価する。
5. これらの結果を確認した後、公開実データ／実設備へ一般化する。planned-load、unit、sampling、欠損契約を先に固定する。

Granite TTMはcontext 512 sensitivityとして別条件で扱い、今回のToto matrixと同一契約の順位には含めない。
