# 最初のIssue案

公開repository `tyaro/banto-ai`で最初に作成する5件のIssue案です。repository licenseはMITに決定済みです。Issue本文へ転記する際はtarget hardwareと各modelのlicense manifestを確認します。

## 1. 研究環境、manifest、license gate、共通interfaceを確立する

**目的:** model固有のnotebookを増やす前に、再現可能な実行環境と、forecast／anomaly modelを交換できる最小契約を作る。

**完了条件:**

- Python 3.12+、`pyproject.toml`、外部依存なしの実行手順を追加する。
- compileall、unit test、manifest smoke、safety guardをlocalとCIで実行できる。
- dataset、run、result、model license manifestのschemaとsampleがある。
- `Forecaster`と`AnomalyDetector`の共通interfaceを定義する。
- code licenseとweight licenseを別々に記録し、`research-only` modelをpromotion対象外にできる。
- 顧客データ、大型checkpoint、credentialをGitへ追加しないguardがある。

**対象外:** model性能比較、production serving、PLC接続。

## 2. seed再現可能なsynthetic industrial data generatorを作る

**目的:** regime、fault、欠損、既知のevent labelを持つ、motor／conveyorに近いmultivariate dataを生成する。

**完了条件:**

- seedとconfigによって生成データが完全に決まる。
- 単位、sampling rate、generator parameterをmanifestへ記録する。
- stopped、startup、nominal、high load、cooldownを含む。
- drift、spike、stuck value、dropout、overheating trend、slip／jam proxyのうち最低3種類を含む。
- ground-truth event intervalを観測値とは別に出力する。
- chronological splitとcross-equipment splitを生成する。
- data本体をcommitせず再生成でき、小さな安全なfixtureだけをtest用に置く。

**対象外:** 合成信号が顧客設備を代表すると主張すること。

## 3. 共通benchmark runnerとnaive／統計baselineを実装する

**目的:** すべてのmodelを同一window、horizon、metric、hardware記録で比較できる評価基盤を作る。

**完了条件:**

- 1 commandがrun manifestを受け取り、machine-readable resultとsummaryを生成する。
- last-value、seasonal-naive、EWMA、linear／Holt系baselineを含む。
- signal、equipment、operating mode、horizon別にmetricを出力する。
- MAE、RMSE、MASEを実装し、quantile inputにはWISとcoverageを計算する。
- p50／p95 latency、peak memory、artifact size、hardwareを記録する。
- timestamp overlap、future leakage、duplicate、unit mismatch、unexpected gapのtestがある。
- `fev`を採用するか、自前runnerとの役割分担をADRとして記録する。

**対象外:** 特定foundation modelの優遇、leaderboard順位だけによる採用決定。

## 4. Forecast model adapterを実装し、候補を同条件で比較する

**目的:** TimesFM 3.0だけに固定せず、商用利用可能候補を含む最初のforecast comparisonを完成させる。

**対象model:**

- Chronos-2
- TimesFM 3.0（research-only）
- Toto 2.0 4m／22m
- Granite TTM R2
- 実行余力があればTimesFM 2.5、N-HiTS／PatchTST

**完了条件:**

- 各modelが共通`Forecaster` interfaceのadapter経由で実行される。
- exact package version、checkpoint、code／weight license、preprocessingを記録する。
- univariate／multivariate、共変量有無、sampling、missing条件のablationがある。
- accuracy、quantile calibration、latency、memoryを同じreportで比較する。
- TimesFM 3.0 resultとartifactに`research-only`を付け、製品候補へexportできないtestがある。
- 少なくとも1つの商用利用可能modelについて、継続／保留／中止の判断と理由を残す。

**対象外:** production deployment、顧客PoC、model outputからの制御書き込み。

## 5. Anomaly、commissioning profile、Banto read-only contractの縦断PoCを作る

**目的:** offline replay上で、観測値からanomaly scoreとcommissioning profile candidateを生成し、Banto Hub向けshadow responseまで一方向に流す。

**完了条件:**

- robust統計、forecast residual、TSPulseの最低2方式をevent単位で比較する。
- recipe stepにentry、exit、data-quality、abort conditionがある。
- 適格windowだけからnormalization、envelope、bias、threshold候補を作る。
- held-out replayでfalse alarm、incident recall、coverageを評価する。
- profile candidateにprovenance、uncertainty、expiry、approval、rollback metadataがある。
- read-only request／responseにmodel version、profile version、quality、degraded stateを含める。
- Production modeでは学習をlockし、PLC値、recipe、interlock、安全上限を書き込むpathがない。

**対象外:** PID tuning、thresholdの自律昇格、production service deployment。

## 分割方針

Issue 5は縦断契約を確認するためのumbrella Issueです。Issue 1～4のinterfaceが固まった時点で、次の3件へ分割します。

1. anomaly detector benchmark
2. commissioning calibration／profile workflow
3. Banto Hub offline export／shadow adapter

詳細な順序と判断gateは [`research-implementation-plan.md`](research-implementation-plan.md) を参照してください。
