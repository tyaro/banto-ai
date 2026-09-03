# 最初の Issue 案

GitHub の remote が利用できるようになったら、まず次の5件を Issue として作成します。現時点では scaffold に remote を設定しただけで、外部への Issue 作成は暗黙に行わないため、案をローカルに記録しています。

## 1. 再現可能な TimesFM-3 benchmark runner を確立する

**目的:** versioned dataset manifest 上で TimesFM-3 と単純な baseline を実行し、比較可能な metric を出力する。

**完了条件:**

- 1つの command が run manifest を受け取り、machine-readable な結果を生成する。
- 正確な model release／checkpoint と preprocessing を記録する。
- signal、horizon、運転 mode 別に結果を出力する。
- last-value と seasonal-naive baseline を含む。
- 顧客データを使わない小さな synthetic fixture で smoke test が動く。

**対象外:** production serving、PLC 接続、model promotion。

## 2. seed 再現可能な synthetic industrial data generator を作る

**目的:** regime、fault、欠損、既知の event label を持つ、motor／conveyor に近い多変量データを生成する。

**完了条件:**

- seed によって生成データが完全に決まる。
- 単位、sampling rate、generator parameter を記録する。
- startup、steady state、load change、少なくとも3種類の fault-like pattern を含む。
- ground-truth event interval を観測値とは別に出力する。
- 生成データ本体を commit せずに再生成できる。

**対象外:** 合成信号が顧客設備を代表すると主張すること。

## 3. mini 多変量 quantile Transformer baseline を実装する

**目的:** point forecast と interval forecast を検証できる、内部を理解しやすい baseline を作る。

**完了条件:**

- 複数の aligned signal と明示的な mode／context feature を入力できる。
- p10、p50、p90 または同等の interval 表現を出力する。
- chronological split で学習し、calibration metric を報告する。
- univariate、multivariate、mode-aware input の ablation を比較する。
- model size、runtime、failure behavior を記録する。

**対象外:** evaluation harness が安定する前に foundation model を上回ろうとすること。

## 4. commissioning profile の calibration と shadow evaluation を設計する

**目的:** 制御動作を変更せずに、commissioning recipe を versioned profile candidate に変換する。

**完了条件:**

- recipe step に entry、exit、data-quality、abort condition がある。
- 適格な window だけから baseline／envelope を学習する。
- held-out または shadow replay で誤警報と coverage を評価する。
- candidate profile に provenance、uncertainty、expiry、rollback metadata がある。
- Production mode では学習を lock し、PLC 設定を書き込まない。

**対象外:** threshold または PID の自律書き込み。

## 5. Banto Hub read-only adapter contract を定義する

**目的:** observation、forecast、quality、shadow result を扱う、最小限の versioned interface を定める。

**完了条件:**

- model version、profile version、status、quality を含む request／response 例がある。
- missing、stale、out-of-distribution の挙動が明示されている。
- identity、authorization、retention、audit の要件を記載する。
- PLC 値、recipe、interlock、安全上限を書き込む endpoint がない。
- live Banto Hub なしで動く local contract test がある。

**対象外:** production service の deploy または最終 transport protocol の選定。
