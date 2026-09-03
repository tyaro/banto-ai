# 研究ロードマップ

## 最終的な目標

産業 AI が、予測・異常検知・試運転支援に有効であることを、再現可能な根拠として示します。同時に、可観測で、元に戻せて、安全重要な制御から分離されていることを満たします。

## フェーズ

| Phase | 焦点 | 完了時の根拠 |
| --- | --- | --- |
| 0 | 研究の衛生管理と契約 | リポジトリ scaffold、データ方針、experiment manifest、artifact 命名、連携境界 |
| 1 | TimesFM-3 benchmark | 再現可能な runner、naive／古典的ベースライン、信号・運転モード別の指標 |
| 2 | 合成産業データ | 運転状態、fault、欠損、label を持つパラメータ化 generator と seed 再現性 |
| 3 | 自前ベースライン | 点予測・分位点予測を備えた小型の多変量 Transformer と ablation レポート |
| 4 | 異常とドリフト | 残差・エンベロープ検知、誤警報分析、データ品質・out-of-distribution 対応 |
| 5 | Continual learning | 本番モード固定、rollback、汚染テストを含む安全な適応実験 |
| 6 | Commissioning auto-tuning | レシピ駆動の profile candidate、shadow 評価、人手承認ゲート |
| 7 | Banto Hub pilot 境界 | read-only export／adapter の試作と、制御を変更しない end-to-end デモ |

## 推奨する優先順

1. benchmark と data manifest を確立する。
2. モーター・コンベアに近い合成信号を生成する。
3. TimesFM-3、seasonal-naive、単純な統計ベースラインを測定する。
4. benchmark が安定してから mini-Transformer を実装する。
5. 残差スコアと運転モード別の正常エンベロープを追加する。
6. 試運転校正を offline と shadow mode で検証する。
7. 承認済み結果を利用できる、最小限の Banto Hub adapter を定義する。

## 実験の必須記録

すべての実験に、次を記録します。

- 目的と仮説
- dataset identifier、出所、license
- 時系列 split と leakage 対策
- サンプリング、resampling、欠損値方針
- feature と context window の設定
- random seed と software／model version
- ベースラインと主要指標
- 運転モード・fault／regime ごとの結果
- 必要に応じて計算環境と実行時間
- 制約、失敗した実行、次の判断

## 判断ゲート

### Gate A: データの妥当性

timestamp、単位、欠損、split 境界を検証するまでモデルを比較しません。合成データには generator の seed と既知の ground truth を記録します。

### Gate B: ベースラインに対する価値

複雑なモデルへ進むのは、合意した指標が改善するか、校正済み interval、早期検知、計算コストなどの運用上の明確な利点がある場合だけにします。

### Gate C: 運用安全性

online または commissioning 実験へ進む前に、mode、rollback、stale data の挙動と、AI が制御できない範囲を明示します。

### Gate D: handoff 準備

再現性、versioning、データ品質、失敗モードの確認に合格した artifact だけを Banto Hub の shadow 利用候補にします。shadow の成功だけで制御権限を自動付与してはいけません。

## 追って具体化する成功指標

- Forecast: MAE、RMSE、妥当な場合の sMAPE、interval の WIS／coverage、horizon 別の劣化。
- Anomaly: incident 別 precision／recall、運転時間あたりの誤警報、検知リードタイム、alert の持続性。
- Adaptation: regime 変更後の回復、汚染下の性能、rollback の正しさ、固定中の安定性。
- Commissioning: profile coverage、校正誤差、却下・判定不能な step、オペレーターのレビュー時間、shadow 誤警報率。
- System: p95 inference latency、リソース使用量、欠損耐性、実行間の再現性。
