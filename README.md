# banto-ai

Banto ecosystem における、予測・異常検知・適応型試運転・予知分析のための Industrial AI 研究リポジトリです。

このリポジトリは `banto-industrial` から意図的に分離しています。実験、評価プロトコル、モデル試作、連携契約を扱う研究用ワークスペースです。生産設備の制御動作は、Banto Hub と PLC／制御システムが引き続き担当します。

現在の研究基盤には、外部依存ゼロの共通benchmark runner、統計baseline、モデル別の隔離実行環境があります。TimesFM 3.0は研究比較専用、Chronos-2は`commercial-evaluation`として、専用環境でCPU smokeと小規模rolling-origin benchmarkを実行済みです。core runtimeへML依存は混入させていません。今回の合成データ結果は実設備性能を示しません。

## 研究テーマ

| テーマ | 最初に検証する問い |
| --- | --- |
| 時系列 foundation model 評価 | TimesFM-3、Chronos-2、Toto、Granite TTMなどは、産業設備に近い信号で単純なbaselineを上回るか？ |
| 自前の時系列 Transformer | 内部を理解・検証できる最小限の多変量予測モデルは何か？ |
| 多変量・分位点予測 | 点予測だけでなく、校正された予測範囲を出せるか？ |
| 異常検知 | 予測残差や正常エンベロープで、誤警報を抑えつつドリフトを早期検知できるか？ |
| Continual learning | 異常データが「正常」を汚染することなくモデルを適応させられるか？ |
| Commissioning auto-tuning | 構造化された試運転レシピから、安全でレビュー可能な設備プロファイルを作れるか？ |
| 合成産業データ | 顧客データがない段階でも、現実的でラベル付きの信号を生成できるか？ |
| Banto Hub 連携 | 本番導入に必要な read-only、shadow、承認済み引き渡しの境界は何か？ |

## 基本方針

- 顧客データはこのリポジトリにコミットしません。合成データまたは再配布が明確に許可された公開データだけを使います。
- 研究成果はレビューと明示的な昇格が完了するまで、助言情報として扱います。
- PLC の安全ロジック、インターロック、非常停止、ハード保護上限は、AI レイヤーの外側で常に優先されます。
- 本番中の適応処理はデフォルトで無効にします。試運転モードと shadow モードは明示的な状態として扱います。
- すべての結果に、データの出所、設定、コードリビジョン、評価指標、既知の制約を記録します。

## ライセンス

このリポジトリのソースコードと文書は [MIT License](LICENSE) です。

研究対象モデルのコードライセンスと学習済み重みのライセンスは別物として管理します。TimesFM 3.0の重みは `research-only` として扱い、MITのリポジトリライセンスによって利用条件が緩和されることはありません。

## リポジトリ構成

```text
docs/
  architecture.md                 Banto Hubとの責務境界と成果物フロー
  time-series-model-survey.md     時系列モデル候補、ライセンス、実現可能性の調査
  research-implementation-plan.md 段階的な研究・実装計画と判断gate
  research-roadmap.md             長期的な研究フェーズと完了条件
  timesfm-notes.md                TimesFM 3.0評価プロトコル
  chronos2-notes.md               Chronos-2の隔離・評価契約
  results/                        実測結果（合成／研究専用）
  adr-0003-timesfm3-isolation.md  TimesFM 3.0の依存・実行隔離
  adr-0004-chronos2-isolation.md  Chronos-2の依存・実行隔離
  commissioning-learning.md       試運転・校正・昇格の設計
  initial-issues.md                最初に作成するIssue 5件の案
schemas/                       manifestを検証するJSON Schema
examples/                     安全な合成fixtureとsample manifest
src/banto_ai/                  外部依存なしのPhase 0共通runtime
tests/                         Python標準unittest
experiments/
  timesfm3/                    foundation model のベンチマーク
  synthetic-data/              産業設備に近いデータの再現可能な生成
  online-learning/             適応とドリフトの実験
environments/
  timesfm3/                    専用venv向け入力とpackage／checkpoint来歴
  chronos2/                    Python 3.14 CPU専用lockと固定証跡
models/
  mini-transformer/            小さく検証しやすい予測ベースライン
  industrial-tsfm/             産業向けモデルの研究
datasets/                      データポリシーとローカル配置
tools/
  smoke.py                    clean checkout用のmanifest／naive smoke
  safety_check.py             repository safety guard
  timesfm3/                   TimesFM 3のpreflight／準備／offline CPU smoke
  chronos2/                   Chronos-2のpreflight／準備／smoke／benchmark
  data-generator/              データ生成ユーティリティ
  evaluator/                   共通の評価指標とレポート
```

## 進め方

1. 非公開データや顧客データはリポジトリ外に置き、ローカルのデータ識別子だけを参照します。
2. 新しいベンチマーク結果を追加する前に、小さな experiment manifest を作成します。
3. 改善を主張する前に、単純なベースラインと比較します。
4. モデル成果物には、設定と評価レポートを必ず添付します。
5. 実験を PLC に直接接続したり、制御パラメータを自動書き込みしたりしません。

## 次の一歩

最初の実装マイルストーンは、合成産業データ上で naive／古典的 baseline と複数の時系列モデルを同条件で比較できる、再現可能なベンチマークです。

現時点では TimesFM 3.0 の学習済み重みは非商用・非本番用途に限定されるため、研究比較専用とします。商用利用可能候補として Chronos-2、Toto 2.0、Granite TTM／TSPulseなどを同時に評価します。

### Chronos-2初期評価

Chronos-2は固定checkpointのsize／SHA-256検証、公式API direct CPU smoke、Banto tool smoke、past-only／known-futureの初期rolling benchmarkまで完了しました。provenance拡張後のBanto tool smoke正本は`artifacts/chronos2/cpu-smoke-provenance-2026-09-04.json`で、`verification_status=verified`、cold elapsed `12.057009100011783`秒です。known-future 7 modelsではaggregate MAE `0.1691488806622826`、WIS `0.15937026919725228`で1位でしたが、単一seed・少数origin・合成データの結果です。known-futureはorigin時点で確定済みの計画値を模した条件に限り、実績値の先読みを認めません。詳細は[`docs/results/chronos2-initial-evaluation-2026-09-04.md`](docs/results/chronos2-initial-evaluation-2026-09-04.md)を参照してください。

Python 3.14専用venvとrepository外cacheで再現します。各runは既存出力を上書きしないため、cleanなartifact pathで実行してください。

```powershell
py -3.14 -m venv ..\.venv-banto-ai-chronos2
$chronosPython = '..\.venv-banto-ai-chronos2\Scripts\python.exe'
& $chronosPython -m pip install -r environments\chronos2\requirements-windows-cpu-py314.lock
& $chronosPython tools\chronos2\preflight.py --cache-dir C:\banto-cache\chronos2 --format both
& $chronosPython tools\chronos2\prepare_checkpoint.py --cache-dir C:\banto-cache\chronos2 --accept-apache-2.0
& $chronosPython tools\chronos2\run_smoke.py --cache-dir C:\banto-cache\chronos2 --output artifacts\chronos2\cpu-smoke-provenance-2026-09-04.json
& $chronosPython tools\data-generator\generate.py --config examples\configs\synthetic-motor-small.json --output artifacts\generated\synthetic-motor-small
& $chronosPython tools\chronos2\run_benchmark.py --config examples\configs\benchmark-chronos2-baselines-past-only.json --cache-dir C:\banto-cache\chronos2
& $chronosPython tools\chronos2\run_benchmark.py --config examples\configs\benchmark-chronos2-known-load.json --cache-dir C:\banto-cache\chronos2
& $chronosPython tools\chronos2\run_matrix.py --config examples/configs/benchmark-matrix-chronos2-small.json --cache-dir C:\banto-cache\chronos2
```

Chronos-2 matrix設定はseeds `[17, 42]`×horizons `[1, 3]`×context lengths `[6, 12]`の8 cellsです。base benchmarkのmodel parameter `context_length=12`はChronos backendに渡す入力上限で、matrix axisのcontext lengthは各cellの実入力長です。6と12はいずれも上限内です。Chronos専用のdataset／benchmark／matrix出力を使い、既存出力は上書きしません。

Chronos-2はApache-2.0ですが、実modelによるseed×horizon×context matrix（8 cells）、欠損・regime・fault評価、clean savepoint再実行、実設備の計画値契約は未実施です。`commercial-evaluation`を継続し、まだ`product-candidate`へ昇格しません。

TimesFM 3.0の共通`Forecaster` adapter、official APIの遅延import境界、license／provenance検証、fake backend testsは実装済みです。公式backendはadapterごとに初回forecast時だけロードし、以後は安全に再利用します。benchmark coreにはoptional modelを注入するregistry境界があり、通常のbaseline CLI／CIから`timesfm`、`torch`、`numpy`はimportされません。`environments/timesfm3/requirements.in`は`timesfm[torch]==3.0.0`のtop-level exact pinであり、完全なtransitive lockではありません。専用環境でのCPU smokeと、LastValueとの小規模rolling-origin benchmark結果は記録済みです。ただし、単一generator、少数origin、短いcontext／horizon、弱いbaselineによる限定評価であり、一般性能と実設備性能は未評価です。

正式CPU smoke 2回の測定値は [`docs/results/timesfm3-cpu-smoke-2026-09-04.md`](docs/results/timesfm3-cpu-smoke-2026-09-04.md) に記録しています。単一synthetic windowの結果であり、実設備性能や製品採否を示しません。

rolling-origin benchmarkの実測値は [`docs/results/timesfm3-rolling-benchmark-2026-09-04.md`](docs/results/timesfm3-rolling-benchmark-2026-09-04.md) に記録しています。clean savepointから実行したrun3をprimary reproducibility runとし、run1/run2はdirty pre-savepointの再現性確認として残しています。TimesFM 3.0はこの限定条件のcomposite値でpoint forecastとWISがLastValueを上回りましたが、native intervalのcoverageはnominal 80%未達です。AとdegCの異なる単位を混合した値のため、物理量としての直接解釈やtarget構成の異なるrunとの比較は行いません。結果はPhase 2完了や製品採用の根拠ではありません。

統計baselineを含むpast-only／known-loadのtarget別比較は [`docs/results/timesfm3-baselines-comparison-2026-09-04.md`](docs/results/timesfm3-baselines-comparison-2026-09-04.md) に記録しています。known-loadは計画値をorigin時点で取得できるsynthetic oracle-styleの別scenarioであり、実績先読みや本番効果を意味しません。この小標本ではTimesFM 3.0は温度で有力でしたが、電流ではmoving-average等を上回らず、Phase 2完了・採用判断には進みません。次は複数seed／horizon／context／origin、モデル単独resource測定、ライセンス適合候補との同一契約比較です。

複数seed／horizon／contextを反復するmatrix runnerを追加しました。seedはrun metadataだけでなくgenerator configへ反映し、seedごとにdatasetを一度生成・品質確認して各cellで再利用します。dataset fingerprintに加えて`observations.jsonl`自体のSHA-256を記録し、異seedで観測内容が同一なら停止します。出力の主集計は単位を分離した`by_model_target`のseed間cell-macro summaryであり、raw predictionのpooled metricではありません。base configのraw bytes hashと開始code revisionを固定し、cell終了時・matrix publish直前まで不変であることを検証します。これは評価範囲拡大の基盤で、Phase 2完了を意味しません。

2 seeds×2 horizons×2 context lengthsの実TimesFM matrixは8 cellsすべて成功し、結果を [`docs/results/timesfm3-matrix-2026-09-04.md`](docs/results/timesfm3-matrix-2026-09-04.md) に記録しました。TimesFM 3.0は温度の4条件でMAE最良でしたが、電流では4条件ともmoving-average等に劣りました。2 seeds・少数originのcell-macroであり、Phase 2完了や製品採用の根拠にはしません。次はseed／origin／条件の拡大、cold／warmとモデル単独resourceの分離、欠損・regime・fault slice、ライセンス適合候補との同一契約比較です。

Phase 0の実行確認は、外部依存を導入せず `python tools/smoke.py` と `python tools/safety_check.py` で行えます。Phase 1の最小generatorは次で実行できます。

TimesFM 3の実評価は、リポジトリ外のcacheを明示して次の順に実行します。checkpoint準備だけがdownloadを行い、smokeは`local_files_only=True`でcache miss時に停止します。

```powershell
python tools/timesfm3/preflight.py --cache-dir C:\banto-cache\timesfm3 --format both
python tools/timesfm3/prepare_checkpoint.py --cache-dir C:\banto-cache\timesfm3 --accept-research-only-license
python tools/timesfm3/run_smoke.py --cache-dir C:\banto-cache\timesfm3 --output artifacts\timesfm3\cpu-smoke.json
```

このrunはresearch-only／non-productionであり、Banto Hub／PLCへのwrite pathを持ちません。実測値はartifactと結果文書へ記録し、単一windowの結果を一般性能として扱いません。

TimesFM 3をrolling-origin benchmarkへ接続する場合は、専用venvで次を実行します。`prepare_checkpoint.py`で取得・検証済みの、リポジトリ外cacheだけを指定してください。実行時はlicense acceptance、固定revision、checkpointのサイズ／SHA-256、インストール済み`timesfm==3.0.0`を確認し、ネットワークを禁止します。

```powershell
python tools/data-generator/generate.py --config examples/configs/synthetic-motor-small.json --output artifacts/generated/synthetic-motor-small
python tools/timesfm3/run_benchmark.py --config examples/configs/benchmark-timesfm3-small.json --cache-dir C:\banto-cache\timesfm3 --accept-research-only-license
```

小規模matrixは同じ専用venvとcacheで次のように実行します。sampleはpast-onlyを標準とし、2 seeds×2 horizons×2 context lengthsの8 cellsです。既存のdataset／cell／matrix出力は上書きしません。

```powershell
python tools/timesfm3/run_matrix.py --config examples/configs/benchmark-matrix-timesfm3-small.json --cache-dir C:\banto-cache\timesfm3 --accept-research-only-license
```

`benchmark-timesfm3-small.json`はLastValueとTimesFM 3を同じequipment／origin／targetで比較します。validation／test originは高コスト実モデル向けに決定的なstrideと最大数を設定し、その選択結果は`result.json`のprovenanceへ保存します。TimesFM 3はnative quantile、baselineはvalidation residual by leadを使います。今回のsampleでは将来の`load_proxy`を本番で計画値として確実に知れる前提を置かず、全covariateをpast-onlyにしています。このため既知将来値を使う実験は、計画値であることを別途データ契約に明記したconfigで行います。

```text
python tools/data-generator/generate.py --config examples/configs/synthetic-motor-small.json --output artifacts/generated/synthetic-motor-small
python tools/data-generator/check_quality.py --dataset artifacts/generated/synthetic-motor-small
python tools/evaluator/run_benchmark.py --config examples/configs/benchmark-small.json
```

上記はsrc layoutのclean checkoutから実行する標準手順です。`python -m banto_ai ...` を使う場合は、先に `python -m pip install -e . --no-deps` を実行してください。

出力先の既定値は `artifacts/generated/<dataset_id>` です。既存ディレクトリは上書きせず、観測値、ground-truth event、generator config、dataset／split manifest、fingerprint、summaryを分離して出力します。`[start,end)` のinterval境界、UTC timestamp、equipmentごとのstrictly increasing timestamp、canonical JSON／JSONLの順序とSHA-256計算方法を記録します。quality checkerはcatalogのsampling interval、unit、quality keys、event構造、splitの完全被覆・record_count、generator configとのsemantic consistency、fingerprint整合性、future leakageを検査します。

Windowsを含む開発手順とモデル別のplanned environmentは [`CONTRIBUTING.md`](CONTRIBUTING.md) に記載しています。

調査結果は [`docs/time-series-model-survey.md`](docs/time-series-model-survey.md)、具体的な作業計画は [`docs/research-implementation-plan.md`](docs/research-implementation-plan.md)、Issue案は [`docs/initial-issues.md`](docs/initial-issues.md) を参照してください。

## ステータス

Phase 0 research foundation implemented。Phase 1 savepoint 1（seed再現可能synthetic industrial data generator）とSavepoint 2（共通benchmark runner／統計baseline）を実装済みです。TimesFM 3.0はCPU smoke、小規模rolling-origin benchmark、8-cell matrixを実行済みです。Chronos-2は固定snapshot検証、公式API／Banto tool CPU smoke、past-only 6 models／known-future 7 modelsの初期rolling benchmark、および8-cell matrix設定・専用wrapperを実装済みです。Chronos-2の実model seed×horizon×context matrix実行、origin拡大、model単独resource測定、欠損・regime・fault slice、clean savepoint再実行は未実施であり、Phase 2は完了していません。本番デプロイ経路も未実装です。

合成データは研究用の制御されたfixtureであり、実設備の挙動を代表すると主張しません。顧客データ、raw設備データ、秘密情報は生成物・設定・Git履歴へ入れません。大量生成データはGit無視領域へ置き、commit対象は小さいconfig／fixtureだけにします。
