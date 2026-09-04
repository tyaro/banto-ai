# banto-ai 研究・実装計画書

策定日: 2026-09-04

## 1. 計画の目的

Banto ecosystem向けの時系列AIについて、次の価値を再現可能な実験で確認し、安全なBanto Hub連携へ段階的に進めます。

- 設備tagの短期・中期forecast
- 分位点予測によるmode別normal envelope
- 予測残差と専用modelによるanomaly detection
- commissioning中の設備固有calibration
- driftを検知し、rollback可能なprofile候補を作る適応処理
- read-only／shadow境界を守るBanto Hub連携

本計画はモデル採用を先に決めるものではありません。TimesFM 3.0とChronos-2のMetroPT-3同一契約評価を完了し、共通のデータ、評価、interfaceによる比較記録を残しました。Chronos-2は商用候補として、TimesFM 3.0はresearch-onlyの基準として同じ条件で継続比較します。

## 2. 前提と決定事項

### 2.1 決定事項

- 研究コードは `banto-industrial` から分離し、`banto-ai`で管理する。
- `banto-ai`のソースコードと文書はMIT Licenseで公開する。ただし、外部modelのcode／weights licenseは個別に管理する。
- core runtimeの外部依存はゼロとし、現時点ではdependency lockを作成しない。最初の外部依存導入時に、model environmentごとのversion pin／lockを必須にする。
- formatter／linterはPhase 0では導入せず、標準ライブラリの`compileall`を使う。最初のdevelopment dependency導入時にformatter／linterをversion pinし、lockへ固定する。
- ドキュメントは日本語を基本とし、API名、model名、schema fieldは英語を使う。
- Gitで管理するのは、source manifest、transform config、schema、code、tests、docs、結果要約などの再現情報とし、生成されたobservations、split／dataset manifest、quality report、fingerprintはGit管理外とする。
- 公開データは、公式URL／DOI／licenseの確認、利用条件の受入れ、取得サイズ／SHA-256／archive member hashの固定を通ったものだけを研究入力候補とする。第一候補はUCI MetroPT-3、次候補はUCI hydraulic systemsとし、raw archiveはrepository外のexternal cache、標準化dataset本体はgitignoredな`artifacts/public-datasets/<dataset-id>/`へ置く。MetroPT-3はsource pin、変換、Public-only quality gate、5 baseline、Chronos-2、TimesFM 3.0の公開実データ評価まで完了した。詳細な境界は[`docs/public-dataset-survey.md`](public-dataset-survey.md)と[`docs/adr-0005-public-dataset-boundary.md`](adr-0005-public-dataset-boundary.md)へ記録する。
- MetroPT-3取込はone compressor、14 signals（`Caudal_impulses`除外）、60秒 `[start,end)`、output timestamp=bin end、analog mean／digital last、補間なしfail closed、`mode=unknown`、864/288/288 chronological splitを契約とする。Public-only quality gateは既存synthetic gateと分離する。
- 最初のruntimeはPython sidecarとし、Banto Hubとはoffline exportから接続する。
- forecastとanomaly detectionは共通interfaceの背後でmodelを交換できるようにする。
- TimesFM 3.0は現行weight licenseにより研究比較専用とし、製品artifactへ昇格しない。
- TimesFM 3.0のoptional backendは専用venvへ隔離し、coreの標準ライブラリのみという境界を維持する。package／checkpoint来歴を固定し、weightsはGit外、`local_files_only=True`を既定とする。
- Chronos-2は`chronos-forecasting==2.3.1`とcheckpoint `amazon/chronos-2@29ec3766d36d6f73f0696f85560a422f50e8498c`を専用venv／外部cacheへ隔離する。package、code、weightsはApache-2.0として記録するが、現段階の用途は`commercial-evaluation`に限定し、実性能・運用検証前の`product-candidate`昇格は禁止する。
- Chronos-2のnative pointは公式APIの名称にかかわらずp50／median契約とする。missing、stale、不規則timestamp、長さ不一致は初期adapterで補間せずfail closedとする。
- commissioningではbase modelを無制限に書き換えず、正規化、bias、interval、threshold、adapter等をversioned profileとして調整する。
- AIはPLC値、interlock、emergency stop、hard limit、PIDを直接変更しない。

### 2.2 現時点の非対象

- production servingのSLA保証
- AIによる制御commandの発行
- 顧客raw dataの公開repositoryへの保存
- benchmark完了前のmodel一本化
- production中の自動再学習と無審査promotion
- raw振動／音響波形を汎用TSFMへ常時直接入力する構成

## 3. 成果物

最初の研究cycleで次を作成します。

1. version固定可能なPython project metadataと最小CI
2. dataset manifest、run manifest、result manifest、model license manifestのschema
3. seed再現可能なmotor／conveyor合成データfixture／generator
4. 共通 `Forecaster`／`AnomalyDetector` interface
5. naive／統計／学習型baselineを含むbenchmark runner
6. Chronos-2、TimesFM 3.0、Toto 2.0、Granite TTMのadapter
7. 予測残差、robust統計、TSPulseの異常検知比較
8. commissioning profile candidateとshadow replay
9. Banto Hub offline export contractとread-only sidecar PoC
10. model選定、制約、計算量、licenseをまとめた評価報告書

## 4. 全体フェーズ

期間は専任1名が小さな合成datasetから開始する場合の目安です。hardware準備、model download、実データ承認は含みません。各phaseは日付ではなく判断gateで終了します。

| Phase | 目安 | 主な作業 | 完了条件 |
| --- | ---: | --- | --- |
| 0. 研究基盤 | 2～4日 | package、CI、manifest、license inventory、共通型 | synthetic fixtureで検証commandが再現し、非商用modelを識別できる |
| 1. データとbaseline | 4～7日 | generator、split、quality check、naive／統計baseline | 同じseedで同じdataset／metricを再生成でき、leakage testが通る |
| 2. Forecast候補比較 | 1～2週 | Chronos-2、TimesFM 3.0、Toto 4m／22m、TTM sensitivity | 同一契約比較と、TTMのcontext=512／target-only別集計を混同せず記録できる |
| 3. 異常検知 | 1～2週 | residual、robust rule、TSPulse、drift | event単位のprecision／recall、誤警報、lead timeを比較できる |
| 4. Commissioning | 1～2週 | recipe、window選別、calibration、profile、rollback | held-out／shadow replayでcandidateをapprove／reject／inconclusive判定できる |
| 5. Banto連携PoC | 1週 | offline export、read-only sidecar、degraded state | live制御なしでend-to-end replayし、入力欠落／timeoutを安全に処理できる |
| 6. Shadow pilot準備 | 別途判断 | target hardware、監視、認可、audit | 商用利用可能modelだけでpilot review packageが完成する |

Phase 0～5の初回cycleは、並行作業を含めて約6～10週を想定します。これは約束された納期ではなく、Issue分割と優先順位付けのための規模感です。

## 5. Phase別の実施内容

### Phase 0: 研究基盤

#### 実装

- Python 3.12+を対象に`pyproject.toml`を追加する。Phase 0のcore runtimeは標準ライブラリのみとする。
- `src/banto_ai`のpackage、Python標準`unittest`、compileall、安全検査を追加する。
- model dependencyはPhase 0では定義せず、CIとsmoke testではinstallしない。adapter実装時にmodel environmentごとへ分離する。
- dataset、run、result、model license manifestのJSON Schemaと標準ライブラリ検証器を定義する。
- 共通interfaceと、timestamp、signal metadata、quantile、quality status、model／profile versionの型を定義する。
- `tools/smoke.py`でsample manifest検証とlast-value MAE評価を1 commandにまとめる。
- `tools/safety_check.py`で顧客data、credential、大型checkpoint等のpath／extensionを検査する。

```python
class Forecaster:
    def forecast(self, request: ForecastRequest) -> ForecastResult: ...

class AnomalyDetector:
    def score(self, request: AnomalyRequest) -> AnomalyResult: ...
```

`ForecastRequest`は複数の過去context、target signal ID、任意のknown-future covariateを持ち、結果はtargetごとのforecastを返します。`AnomalyRequest`／`AnomalyResult`も複数seriesを扱います。各型にはtimestamp、signal metadata、quantile level、quality status、model version、profile versionを含めます。

#### Gate 0

- clean checkoutで外部dependency installなしにcompileall、unittest、smoke、safetyを実行できる。
- 1つのsynthetic fixtureに対するnaive forecastを`python tools/smoke.py`で再現できる。
- modelごとにcode license、weight license、許可用途をmachine-readableに記録できる。
- customer dataらしい拡張子やlocal pathがGitへ追加されないtestを用意する。

### Phase 1: 合成データとbaseline（savepoint 1 実装済み）

#### 対象信号

savepoint 1では、外部依存なしのseed再現可能generatorと最小quality checkerを実装済みです。生成物はGit無視領域へ出力し、既存出力の上書きを拒否します。観測値、ground-truth event、generator config、dataset／split manifest、fingerprint、summaryを分離して出力し、chronological splitとcross-equipment splitを同時に作成します。quality checkerはcatalog sampling intervalを正として全deltaを検査し、観測・split・event構造、split完全被覆・record_count、unit／quality、generator configとのtimestamp／regime／event／summaryのsemantic consistency、SHA-256 fingerprint（manifest／summaryとの一致を含む）を検査します。

これは合成データ生成の最小Gateであり、物理モデルの妥当性・実設備代表性を保証しません。合成データは実設備を代表すると主張せず、顧客データは入力・commitしません。

- motor current
- motor temperature
- conveyor speed
- load proxy
- vibration feature
- operating mode／recipe step

#### 含めるregimeとevent

- stopped、startup、low speed、nominal、high load、cooldown
- load step、sensor drift、bias、spike、stuck value、dropout
- overheating trend、bearing degradation proxy、slip／jam proxy
- maintenance window、alarm window、quality degradation

#### Baseline

- last value
- seasonal-naive
- moving average／EWMA
- linear regression with covariates
- Holt linear trend baseline

#### Gate 1

- seedとconfigからデータを完全再生成できる。
- ground truth eventを観測値とは別fileに出力する。
- chronological splitとcross-equipment splitを用意する。
- future leakage、unit mismatch、duplicate timestamp、unexpected gapをtestで検出する。
- baseline resultにdataset fingerprint、runtime、hardwareが残る。

### Phase 2: Forecast候補比較（TimesFM 3.0／Chronos-2 MetroPT評価済み）

AutoETSは未実装であり、現行benchmarkのmodel registry／schemaには含めません。将来の候補評価ではstatsforecast等を隔離環境へ置き、optional依存を通常CIへ持ち込まない方針です。Holt linear trendは別のbaselineであり、ETSとは称しません。

現在、TimesFM 3.0の共通`Forecaster` adapter、official API境界、license／provenance検証、fake backend tests、専用Windows CPU環境での2回の実モデルsmokeを実施済みです。さらに、LastValueとの初期benchmarkと統計baselineを含むpast-only／known-loadの小規模rolling-origin比較を実施しました。target別metrics、再現性、CPU latency／process peakを[`docs/results/timesfm3-baselines-comparison-2026-09-04.md`](results/timesfm3-baselines-comparison-2026-09-04.md)へ記録しています。MAE、RMSE、WIS、interval widthはAとdegCを混合するaggregateだけで優劣を決めず、result schema `0.2`のtarget別およびequipment-target別集計を主に使用します。known-loadは計画値をorigin時点で取得できるsynthetic oracle-styleの別scenarioであり、実績先読みや本番効果を示しません。

複数seed／horizon／context lengthを反復するmatrix runnerを実装し、seedごとのdataset再生成・一回のquality gate、観測file SHA-256によるseed差確認、既存単一runの再利用、cell失敗隔離、単位別`by_model_target` cell-macro summaryを固定しました。base configは読込raw bytes hash、codeは開始revisionを記録し、cellとpublish直前の不変性をfail-closedで検証します。TimesFM専用入口は既存のlicense／cache／offline preflightを再利用し、adapterをmatrix全体で共有します。2 seeds×2 horizons×2 context lengthsの実TimesFM matrixは8 cellsすべて成功し、結果を[`docs/results/timesfm3-matrix-2026-09-04.md`](results/timesfm3-matrix-2026-09-04.md)へ記録しました。TimesFM 3は温度で4条件すべてMAE最良、電流では4条件とも6モデル中4位です。2 seeds・少数originのcell-macroであり、seedを最低5以上、origin／条件追加、欠損・regime・fault slice、cold／warmとモデル単独resourceの分離、ライセンス適合候補比較、実設備評価が未実施なのでPhase 2完了条件を満たしません。

Chronos-2は依存環境を分離し、外部cacheの固定revision、`model.safetensors` 477,930,472 bytes／SHA-256 `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42`を検証しました。公式API direct CPU smokeと、multivariate target、past-only／known-future covariate、native p10／p50／p90を通すBanto adapter／tool smokeは完了しています。

初期rolling benchmarkも、60 samples×2 equipment、context 12、horizon 3、各equipment validation／test各2 originsで完走しました。past-only 6 modelsのChronos-2はaggregate MAE `0.20672198138554906`、WIS `0.1952207659517925`、known-future 7 modelsではMAE `0.1691488806622826`、WIS `0.15937026919725228`で1位でした。known-futureはorigin時点で本当に確定していた計画値を模したsynthetic scenarioであり、評価対象の実績値をoracleとして渡していません。target別には電流MAEでmoving-average、温度MAEでHolt linearが優位です。詳細は[`docs/results/chronos2-initial-evaluation-2026-09-04.md`](results/chronos2-initial-evaluation-2026-09-04.md)に記録します。

Chronos-2のseed `[17, 42]`×horizon `[1, 3]`×context `[6, 12]`の実model matrixは、固定clean HEADから8/8 cells success／0 failureで完了しました。currentは4条件すべてmoving-averageがMAE首位、temperatureはWIS 4条件すべてChronos-2が首位でした。coverage／width、各cellの相対順位、warm latency、peak memoryは[`docs/results/chronos2-matrix-2026-09-04.md`](results/chronos2-matrix-2026-09-04.md)に記録しています。

Toto 2.0 4Mは、`toto-2==2.0.0`／`toto-models==1.0.0`、固定HF revision、外部cache、offline／CPU／batch=1／`decode_block_size=None`の専用境界へ追加し、CPU smokeとMetroPT-3数値benchmarkを実行済みです。MetroPT-3の既存context=120を変えず、patch_size=32のためadapter内で8点の未観測paddingを追加しeffective input length=128とします。全11 past-only covariatesをtargetと同時入力し、known-future／exogenousを拒否します。status=`success`、4,320 predictions、failure 0のtarget別metrics、provenance、runtimeは[`docs/results/toto2-metropt3-evaluation-2026-09-04.md`](results/toto2-metropt3-evaluation-2026-09-04.md)に記録しました。22M、seed拡大、fault slice、実設備一般化は次工程です。

Toto 2.0 4Mの小規模matrixは、seed `[17, 42]` × horizon `[15, 30]` × context `[64, 120]`の8 cellsを実行し、8/8 success、partial 0、failed 0となりました。2 equipment、各seed 480 samples／equipment、past-only `load_proxy`、known-futureなし、native p10／p50／p90の契約です。正本のhash、exact origin、target別cell-macro metrics、padding、runtime、memoryは[`docs/results/toto2-matrix-2026-09-04.md`](results/toto2-matrix-2026-09-04.md)に記録しました。2 seed・少数origin・単一synthetic generatorのため、seed／origin拡大、missing／stale／fault／regime slice、model-only resource、22M、公開／実設備一般化を次gateとします。

Toto 2.0 4M matrixの既存predictionに対するevent slice post-hoc解析を完了しました。8/8 cells analyzed、excluded 0、8,640 predictionsを再推論なしで`[start,end)`分類し、target-event forecastは`conveyor-01.motor_temperature`のoverheatのみ、`motor-01-slip-test`の`motor_current` faultはforecast未coverでした。詳細、正本hash、2-seed cell-macro値、未評価event、次gateは[`docs/results/toto2-event-slices-2026-09-04.md`](results/toto2-event-slices-2026-09-04.md)に記録しています。これはanomaly detection、missing／stale robustness、実設備一般化、製品昇格を示さず、Totoの`commercial-evaluation`とPhase 2未完了を維持します。evidence-completenessの受入条件は、intended target fault eventの全seed × horizon × context forecast coverage、target／covariate missing／stale実入力のexerciseと構造化記録、paired event-level bootstrap 95% CIの報告後に限る優劣主張、性能／製品昇格閾値の次実験前事前登録です。今回のrunでは昇格閾値を定義せず、条件を満たすまで`commercial-evaluation`を維持します。

controlled 4-track acceptance analyzerのsource/config/schema/testを追加しました。real controlled resultsは未実行で、実行順は4 matrix → analyzerです。結果が生成された場合も、analyzerはcross-model rankingを許可せず、control→degradedの同一group paired deltaだけを比較します。

#### 公開データ source pin と次保存点

公開実データの第一候補をUCI MetroPT-3に固定します。source pin tool実装と実archive検証は完了し、正本manifestは[`datasets/manifests/metropt3-source.json`](../datasets/manifests/metropt3-source.json)、手順は[`tools/public-data/README.md`](../tools/public-data/README.md)です。アーカイブは218,381,995 bytes、SHA-256と2つのmember hashを固定しています。公式ページ内のsampling記載は1 Hz／0.1 Hzで競合し、source timezoneも未指定なので、UTCや固定周期を仮定せずraw timestampのdelta／gapを保存します。NASA C-MAPSSは公式licenseが`License not specified`のため採用しません。

検証済みの標準化datasetに対するrolling benchmarkも実施しました。取込は標準ライブラリのstreaming importerで`2020-02-21`の連続24時間候補を研究上UTCとして解釈し、60秒 `[start,end)` bin（analog mean／digital last、output timestamp=bin end）、one compressorの14 signals、`Caudal_impulses`除外、`mode=unknown`、864/288/288 chronological split、7つのdeterministic filesを固定済みです。未来actual、failure report、RULをknown-futureへ渡していません。統計baseline、Chronos-2 native、point-calibrated、TimesFM 3.0 nativeの結果は[`docs/results/metropt3-baseline-evaluation-2026-09-04.md`](results/metropt3-baseline-evaluation-2026-09-04.md)、[`docs/results/chronos2-metropt3-evaluation-2026-09-04.md`](results/chronos2-metropt3-evaluation-2026-09-04.md)、[`docs/results/timesfm3-metropt3-evaluation-2026-09-04.md`](results/timesfm3-metropt3-evaluation-2026-09-04.md)に記録します。

残る課題はorigin／日／設備拡大、Chronos再実行の再現性、missing／stale／regime／fault slice、known-future計画値対past-onlyの追加比較、coverage calibration改善、cold／warmとmodel-only resourceの分離、Toto／Granite TTMなど商用候補との比較です。今回のMetroPT-3評価は24時間・1設備・16 test origins・単一CPU・1 runに限られ、Phase 2完了または`product-candidate`昇格の根拠にはしません。Chronos-2は`commercial-evaluation`、TimesFM 3.0は`research-only`を継続します。

#### 優先順位

| 優先度 | 候補 | 目的 |
| --- | --- | --- |
| P0 | seasonal-naive、EWMA、moving-average、Holt linear | 複雑modelを採用する最低条件 |
| P0 | Chronos-2 | TimesFM 3.0評価後のcommercial-evaluation候補 |
| P0 | TimesFM 3.0 | 最新research reference。非商用・非本番に限定 |
| P0 | Toto 2.0 4m／22m | 軽量multivariate／telemetry候補 |
| P0 | Granite TTM R2 | CPU／fine-tuning／設備別候補 |
| P1 | TimesFM 2.5 | Apache-2.0のTimesFM fallback |
| P1 | N-HiTS／PatchTST／TFT | 対象データ学習型baseline |
| P2 | MOMENT／Moirai | 一次候補で結論が出ない場合の研究比較 |

#### Ablation

- univariate対multivariate
- target historyのみ対operating mode／load共変量あり
- 1秒、5秒、10秒、1分resampling
- short／medium／long horizon
- normal steady state対startup／shutdown／high load
- complete data対missing／stale／irregular data
- zero-shot対設備別calibration／fine-tuning

#### Gate 2

- 同一のevaluation windowとmetricでmodel間比較ができる。
- aggregateだけでなくtarget、equipment-target、signal、mode、horizon別結果がある（target／equipment-target別集計はresult schema `0.2`で提供）。
- accuracy、calibration、latency、peak memory、artifact sizeを同時に報告する。
- TimesFM 3.0の結果に `research-only` が明示され、promotion対象から除外される。
- 少なくとも1つの商用利用可能候補について、継続／保留／中止の判断ができる。
- Chronos-2について、固定package／checkpoint revision／hash、license、cache境界、native p50、missing fail-closedの証跡がある。
- Chronos-2を`product-candidate`へ昇格する場合、精度だけでなくtarget slice、coverage／WIS、CPU p95／memory、再現性、運用失敗時のdegraded stateを満たす。未達ならcommercial-evaluationで停止または撤退する。

### Phase 3: 異常検知

#### 比較方式

1. robust z-score、EWMA、change-point等の統計方式
2. forecast residual + mode別threshold
3. TSPulse anomaly detection
4. Riverによるdrift detection
5. 必要な場合だけmini-Transformer autoencoder等の自前方式

#### Gate 3

- point単位ではなくincident／event単位で評価する。
- mode別にfalse alarm、miss、detection delayを確認する。
- missing、stale、sensor faultをmachine faultと区別する。
- thresholdを学習した期間と評価期間を分離する。
- operatorが原因と根拠windowを追跡できる出力を作る。

### Phase 4: Commissioning auto-tuning

#### 最初に調整する値

- signalごとのnormalization
- mode／loadごとのrobust quantile envelope
- forecast biasとinterval calibration
- residual thresholdとpersistence window
- data-quality threshold
- equipment-specific adapter parameter

#### 昇格フロー

```text
commissioning recipe
  -> valid window extraction
  -> candidate calibration
  -> held-out replay
  -> shadow replay
  -> human review
  -> approved / rejected / inconclusive
  -> version lock + rollback target
```

#### Gate 4

- recipe step、使用window、除外理由、sample数、mode coverageを追跡できる。
- maintenance、known fault、alarm、低quality区間をnormal学習から除外する。
- candidateが従来profileより悪い場合に自動昇格しない。
- Production modeで学習処理が無効になるtestがある。
- profileからPLCへのwrite pathが存在しない。

### Phase 5: Banto Hub連携PoC

#### 段階

1. CSV／Parquet bundleによるoffline replay
2. versioned read-only APIまたは既存queryのadapter
3. 1～10秒cadenceの非同期shadow inference
4. evaluation reportとprofile candidateのreviewed handoff

#### Gate 5

- inputにequipment pseudonym、tag、unit、timestamp、frequency、quality、modeがある。
- outputにmodel／profile version、forecast、quantile、anomaly score、quality、statusがある。
- missing、stale、out-of-distribution、timeout、model unavailableを明示的なdegraded stateとして返す。
- inference停止時もBanto Hub／PLCの制御が影響を受けない。
- authentication、authorization、retention、audit要件が文書化される。

## 6. 評価指標と暫定合格基準

以下は研究開始時の比較基準であり、製品SLAではありません。最初の実測後に設備用途ごとに改定します。

### 6.1 Forecast

- MAE、RMSE、MASE、horizon別error
- p10／p50／p90がある場合はWIS、interval width、empirical coverage
- nominal 80% intervalのcoverage errorは原則±5 percentage point以内を目標とする
- 商用利用可能modelが、対象sliceの過半数でseasonal-naiveよりMASEまたはMAEを10%以上改善することを継続検討の目安とする
- 改善が小さくても、校正、欠損耐性、latencyの運用価値が明確なら継続可能とする

### 6.2 Anomaly

- incident precision／recall、PR-AUC
- 設備運転時間あたりのfalse alarm
- detection delay／lead time
- 合成faultの初期目標はincident recall 0.8以上、false alarm 1件／8設備時間以下
- thresholdは設備riskとfault costに依存するため、実データ導入前に固定SLA化しない

### 6.3 Runtime

- p50／p95 inference latency
- peak RAM／VRAM、CPU、artifact size、startup time
- 初期shadow目標は、1 equipment／1 requestでp95 1秒未満、RAM 4 GiB以内
- 1～10秒cadenceに間に合わないmodelはoffline／batch用途へ降格する
- raw 100 ms collectionをmodel response待ちでblockしない

### 6.4 Reproducibilityとsafety

- 同じversion、manifest、seedでmetric差が許容範囲内に収まる
- train／validation／testのtimestamp境界にoverlapがない
- model unavailable時に制御系へ副作用を起こさない
- non-commercial modelから生成したartifactをproduct candidateとしてexportできない

## 7. 実験manifestの最小形

```yaml
run_id: <uuid>
purpose: <hypothesis>
code_revision: <git-sha>
model:
  adapter: <name>
  release: <pinned-version>
  checkpoint: <immutable-reference>
  code_license: <spdx-or-reference>
  weights_license: <spdx-or-reference>
  allowed_use: <research-only|commercial-evaluation|product-candidate>
data:
  dataset_id: <id>
  fingerprint: <hash>
  provenance: <synthetic-or-public-reference>
  split_manifest: <path>
preprocessing:
  frequency: 5s
  context_length: 512
  missing_policy: <policy>
  feature_set: <version>
evaluation:
  horizons: [12, 60, 180]
  quantiles: [0.1, 0.5, 0.9]
  metrics: [mae, rmse, mase, wis, coverage]
runtime:
  os: <value>
  device: <cpu-or-gpu>
  cpu: <value>
  accelerator: <value-or-null>
  memory_gib: <value>
  seed: 42
```

## 8. 最初の5 Issue

詳細は [`initial-issues.md`](initial-issues.md) に記載します。作成順は次のとおりです。

1. 研究環境、manifest、license gate、共通interfaceを確立する。
2. seed再現可能なsynthetic industrial data generatorを作る。
3. 共通benchmark runnerとnaive／統計baselineを実装する。
4. Forecast model adapterを実装し、候補を同条件で比較する。
5. Commissioning／anomaly／Banto Hub shadowに必要な契約を試作する。

Issue 5は実装開始時に「異常検知」「commissioning profile」「Banto adapter」へ分割して構いません。最初はinterface間の整合を確認するumbrella Issueとします。

## 9. リスク管理

| リスク | 早期検知 | 対応 |
| --- | --- | --- |
| model download／GPU準備で開始が遅れる | CPU smoke testが動かない | naive、TTM、Toto 4mから開始しmodel environmentを分離 |
| Python dependencyが衝突する | lock解決不能、CUDA version不一致 | model adapterごとにoptional environmentまたはcontainerを分離 |
| 合成データで差が出ない | 全modelが同程度 | startup、mode switch、非線形load、欠損を段階追加しgeneratorを検証 |
| 高精度だが重すぎる | p95／memory不合格 | resampling、batch、smaller checkpoint、offline用途への降格 |
| quantileが未校正 | coverage errorが大きい | conformal／isotonic等の後段校正をholdoutで比較 |
| continual learningが異常を吸収する | fault期間後にthresholdが拡大 | update gate、quarantine、human approval、rollbackを必須化 |
| ライセンス違反 | weight license不明／変更 | run開始前検査、version pin、research-only artifactのpromotion禁止 |

## 10. 判断が必要な事項

実装前またはPhase 0中に、次を決めます。

1. `banto-ai`自体のrepository license。MITを採用する（`LICENSE`に反映済み）。
2. 最初のtarget hardware。最低でも開発PC CPU、利用可能ならNVIDIA GPU、将来のBanto Hub想定PCを記録する。
3. 最初の主要sampling cadence。初期案はraw 100 ms、forecast 1秒／5秒／10秒比較とする。
4. 最初の設備scenario。motor + conveyorを標準scenarioとする。
5. public industrial datasetを初回cycleへ含めるか。含める場合は再配布条件とpretraining overlapを確認する。

## 11. 初回マイルストーンのDefinition of Done

初回マイルストーンは「製品model決定」ではなく、「公平で再現可能な比較基盤の成立」です。次をすべて満たしたら完了とします。

- clean checkoutから環境構築、データ生成、baseline評価を実行できる。
- datasetとrun manifestがschema validationを通る。
- seasonal-naive、Chronos-2、TimesFM 3.0、Toto 4mまたは22mのうち、利用可能な最低3系統を同じdatasetで比較できる。TTMはcontext／covariate契約が異なるため別sensitivity集計とする。
- signal／mode／horizon別のaccuracy、calibration、latency、memory reportが生成される。
- code licenseとweight licenseがreportに残り、TimesFM 3.0はresearch-onlyとして隔離される。
- 顧客データ、credential、大型checkpointがGit履歴に含まれない。
- 次phaseへ進める商用利用可能候補を少なくとも1つ選ぶか、選べない理由を記録する。

技術候補の根拠と詳細は [`time-series-model-survey.md`](time-series-model-survey.md)、Banto Hubとの責務境界は [`architecture.md`](architecture.md) を参照してください。

## Savepoint 2 実装状況

共通runner、last-value／seasonal-naive／moving-average／EWMA／Holt linear trend／covariate付き線形回帰、MAE／RMSE／MASE／標準WIS／coverage／width、rolling-origin、lead別validation-only分位点校正を外部依存ゼロで実装する。split-manifestの`[start,end)`、train-only MASE、raw pointでのRMSE集計、actual timestamp mode、partial／failed／inconclusiveの状態定義を固定する。stateless baselineの決定的なcanonical設定・空state byte数と出力file sizeは別項目で記録し、fevはPhase 2で再評価する。合成データの結果は実設備性能を示さない。
