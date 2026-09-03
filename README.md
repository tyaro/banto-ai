# banto-ai

Banto ecosystem における、予測・異常検知・適応型試運転・予知分析のための Industrial AI 研究リポジトリです。

このリポジトリは `banto-industrial` から意図的に分離しています。実験、評価プロトコル、モデル試作、連携契約を扱う研究用ワークスペースです。生産設備の制御動作は、Banto Hub と PLC／制御システムが引き続き担当します。

Savepoint 2では、外部依存ゼロの共通benchmark runnerと統計baselineを実装しています。合成データの結果は実設備性能を示しません。

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
models/
  mini-transformer/            小さく検証しやすい予測ベースライン
  industrial-tsfm/             産業向けモデルの研究
datasets/                      データポリシーとローカル配置
tools/
  smoke.py                    clean checkout用のmanifest／naive smoke
  safety_check.py             repository safety guard
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

Phase 0の実行確認は、外部依存を導入せず `python tools/smoke.py` と `python tools/safety_check.py` で行えます。Phase 1の最小generatorは次で実行できます。

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

Phase 0 research foundation implemented。Phase 1 savepoint 1（seed再現可能synthetic industrial data generator）とSavepoint 2（共通benchmark runner／統計baseline）を実装済みです。外部ML model adapterと本番デプロイ経路は未実装です。

合成データは研究用の制御されたfixtureであり、実設備の挙動を代表すると主張しません。顧客データ、raw設備データ、秘密情報は生成物・設定・Git履歴へ入れません。大量生成データはGit無視領域へ置き、commit対象は小さいconfig／fixtureだけにします。
