# 保存済み監査からのseed集計（2026-09-24）

全120区間・720評価の検算済み報告を認証し、開発用8 seedと動作確認用2 seedを別々に集計した。登録順、各seedの12 layouts×2層×3候補、profile状態、整数の分子・分母を確認し、独立算術のratio-of-sumsへ接続した。関連33試験通過。実データの信頼区間、正式gate、候補採択は未実施。

## 完了した範囲

実装は`src/banto_ai/anomaly_v03_seed_aggregate.py`。既存のplan・identity・path/hash検査を共用し、数値計算には前工程の`anomaly_v03_inference_audit.py`のcounts/ratioを使用する。観測生成・profile/score再計算・bootstrapは呼ばない。

- 10 seedを登録順で保持。dev8/smoke2を混合した推論母集団は作らない。
- 1 seedの12 layouts、core/quality-stress、C0/C1/C2がすべて揃うことを720 identityの固定順で検査。欠落・重複・順序違い・別roleは拒否する。
- seed別90表、role別18表、候補−C0の記述的な差12表を保存した。overallは両層の件数を合算し、各率は分子合計÷分母合計から計算する。12個の率の単純平均にはしない。
- recall各10件、burden20件、scheduled clean 3365秒、availability各target1800行という1評価の母数、検出/誤警報の分割、全8 targets、profile48件とscore14400行の監査状態を確認した。
- profileが判定不能の行もcountsと理由を保持し、seed/role/候補差へ状態を伝える。今回の保存結果にprofile判定不能は0件。
- 警報0件で適合率の分母が0になる46評価は、nullの意味を保持した。`undefined_input_points`にevaluation IDを残し、recallや予定稼働時間の分母から当該区間を除外しない。
- 区間119はverified attempt2だけを採用し、失敗attempt1の記録を保全した。

raw countsのcluster cellは`counts`と`profile_status=calibrated/inconclusive`を持ち、前工程の算術と対応する。実データclusterを手例用の`compute_fixture_tables`へ渡してはいない。正式40 holdout seedを現dev8/smoke2で代用しない。

## 認証と過去の結果との照合

外部起点は前工程のmanifest SHA-256 `54a50e867f8a93a4100d537c4313964b5a8bb3e7df8aba9487336b07858e3ac9`（5956bytes）。そこから生成検算→全score検算・最初の接続検算・完走保存点へhashを連結し、固定plan、120生成報告、120score/ledger報告を読む。算術sourceとfreeze registryのpinも確認した。

各報告のrun root、chunk/attempt、最終verified journal、6 slots、入力pin、生成検算とscore検算が参照した保存入力の一致を確認した。旧観測・score payloadは読み直していない。この認証は**保存時点の監査結果の連結**であり、今日の全payload bytesを再検査したとの主張ではない。過去のruntime/publication検査も継承で、今回再実行していない。

監査報告・manifest・plan等248 JSON、9,337,887bytesを読み、終了時にも同じ小ファイルの不変を確認した。既存の記述集計を別保存点から認証し、seed90表＋role18表の計1404組の分子/分母は完全一致、点推定と12差分表の144点は1e-12 relative/absolute以内で一致した。点の照合許容差だけであり、整数countsや閾値を丸めていない。

## 検証と修正履歴

初回実装`5c8c4f8`では、保存済みCI状態をすべて`not_evaluated`と期待したため、分母0の適合率が持つ正しい`inconclusive`に対して停止した。結果データの不整合ではなく入口の対応漏れだった。初回のclaim/start/runnerと`initial-failure.json`を保全している。

修正後は分母0に限って`inconclusive/value=null/CI両端null/null_replicates=0`を要求する。分母正の場合は`not_evaluated`を要求する。全区間が警報0の場合と、一部の区間だけが警報0の場合の試験を追加し、分母・露出を落とさず合算することを確認した。

最終実装 `d48ecb4ac2a1d6c7c72d3cd16966b84600e165c5`。新規12試験と算術21試験の計33試験通過。pin改変、欠落報告、正しいhashで封じ直された誤attempt/入力/identity/状態も拒否する。手作りの報告treeだけで試験し、raw datasetファイルが存在しなくても処理でき、treeが変更されないことを確認した。

## 保存・資源

OUT: `artifacts/independent-seed-aggregation-2026-09-24`。成功結果は`verified/`。`authenticated-counts.json`にraw counts、点推定、profile/null診断、入力pin、attempt一覧を保存した。`checkpoint-counts.json`は認証・集計直後の保存、`comparison.json`は旧集計との照合、`summary.json`は結果要約。最終revisionと全pinはOUT直下の`savepoint-evidence.json`。

実データ適用・旧集計照合は1.289秒、process peak private 39.27MiB。最小空きRAM 15.63GiB / commit余裕 21.22GiB、終了時C/D空き 130.22/297.07GiB。追加成果物は約0.6MBの小規模な保存。継続的なリークの有無をこの短い処理だけで断定しない。

旧保存点、実計算source、本流、既存dirty guardは不変。banto-24 PAUSED維持。新規観測・評価・score再計算・実CI算出はすべて0。formal_permission/promotion_allowed/independent_s6_complete=false、performance_status=not_evaluated、selected_candidate=null。

## 次の作業

次は独立analysis出力のschema接続に進む。今回の認証済みcountsと算術の間で必要な入力・出力を整理し、手例によるschema/gate/選択の接続を検証する。dev/smoke記述集計と正式40 holdout解析の資格を区別し、実CIやholdoutを自動起動しない。

slice/delayの監査、runtime/単一writer受入、正式holdout/gate、完全S6は残る。Phase 2のforecast比較やPhase 3全体を今回で完了扱いしない。
