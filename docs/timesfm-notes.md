# TimesFM-3 評価ノート

## 対象範囲

この文書は評価プロトコルを定義します。実験 manifest で評価対象の実装を固定するまでは、特定の package 構成、checkpoint URL、hardware target、feature 対応を前提にしません。

最初に答える問いは実務的なものです。複数の horizon と運転状態において、TimesFM-3 は単純なベースラインと比べて産業設備に近い信号を有用に予測できるでしょうか。

## 評価マトリクス

| 観点 | 初期値 |
| --- | --- |
| 信号 | motor current、motor temperature、vibration proxy、conveyor speed、load proxy |
| 運転状態 | stopped、low speed、nominal speed、high load、startup、cooldown |
| Horizon | サンプリング間隔に対して short、medium、long |
| タスク | まず point forecasting。対応していれば、または校正 wrapper を使い probabilistic／quantile output も評価 |
| Context | 文書化した window の直近履歴。既知 covariate は別 ablation として評価 |
| Baseline | last value、seasonal-naive、moving average、小型 learned baseline |
| Split | 時系列順の train／validation／test。regime と fault 期間は明示的に分離 |

## プロトコル

1. 正確な model release、checkpoint、tokenizer／preprocessing の挙動（該当する場合）、runtime 環境を固定します。
2. 各 split の training 部分から得られる統計量だけで normalization します。
3. 信号を明示的に resample し、不規則な timestamp を model call の中に隠しません。
4. 集約する前に、信号ごと・horizon ごとに評価します。
5. 運転状態、欠損条件、forecast horizon 別に結果を報告します。
6. 同一 window 上で baseline と比較します。
7. runtime が許せば固定 seed で繰り返し、hardware と runtime を記録します。
8. prediction と metric は、リポジトリで安全な合成データから生成したものを除き、Git の外に保存します。

## 指標

point forecast では MAE と RMSE から始めます。zero-heavy な信号で意味が薄くなる場合は sMAPE を使いません。interval では empirical coverage と interval width を報告し、実装が対応していれば weighted interval score などの proper interval score も報告します。

産業用途では、全体平均だけでなく次の運用スライスを必ず含めます。

- startup と shutdown の遷移
- nominal の定常運転
- high-load 運転
- 欠損または遅延した観測
- regime change
- fault-like な合成イベント

## 答えるべき問い

- 対象 horizon で seasonal-naive baseline を上回るか？
- 設備個体間で性能を移せるか、それとも校正が必要か？
- sampling rate、欠損、mode 変更にどの程度敏感か？
- forecast interval は normal envelope を作れる程度に校正されているか？
- context が不足した場合に、性能は段階的に劣化するか？
- Banto Hub の shadow service に必要な最小 runtime footprint はどの程度か？

## 再現性の記録

各 run に、次のような小さな manifest を持たせます。

```yaml
run_id: <timestamp-or-uuid>
model:
  name: timesfm3
  release: <pinned-release>
  checkpoint: <immutable-reference>
data:
  dataset_id: <synthetic-or-public-id>
  split: <manifest-reference>
preprocessing:
  frequency: <duration>
  context_length: <integer>
  missing_policy: <description>
evaluation:
  horizons: [<integer>]
  metrics: [mae, rmse]
runtime:
  device: <cpu-or-accelerator>
  seed: <integer>
```

## 現時点での非対象

- benchmark 前に production checkpoint を選ぶこと。
- zero-shot の結果を commissioning profile とみなすこと。
- model output から threshold、recipe、control parameter を書き込むこと。
- 公開実験で顧客データを使うこと。
