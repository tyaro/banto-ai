# 保存済み需要予測の補正誤差分解 — 実行前契約（2026-10-14）

人の「改善案に沿って進めましょうか」を受け、[Astraレビューの最初の診断](demand-evaluation-methodology-astra-review-2026-10-14.md)だけを実施する。主問は、学習していない店舗へのsales平均予測において、mean28からの補正量と実績に向かう整合のどちらが悪化に寄与したか。PSI採択・潜在需要推定・未見性能確認とは別の事後診断である。

## 読取りと固定対象

閉鎖済み `artifacts/representative-demand-selected-series-20261014` の以下4ファイルだけをclosure内のpin及び保存済み期待pinへ照合して読む。

- `predictions-before-labels.json` — 119404 B / SHA256 `85b15801b16d8a0c0413ed7b54f1b3fc0f36aced3b0555dd96e31b267b7127b7`
- `predictions-and-labels.json` — 144565 B / `c786aead907fc3df519ca2f2e30d22d71030b98ffde8d86933860f8df79d2acb`
- `preperiod-scales-before-targets.json` — 707 B / `8e85a1a8089157dce088f52fa2af447076b6e65e7d61e96b88774254be5d2f7b`
- `summary.json` — 15402 B / `b8d012bc5de7c33631b3e2fb7e69f26eb56455fbed528d813db755af2649b08a`

closureを読むことは外部の完全な認証を再構成する主張ではない。元rootへの書込みはしない。原quantity CSV/profile/weights、追加抽出、forward、fit、完成した評価・試験・CIの反復は0。

元6店舗4/8/16/20/24/28、2015-01-13 + 14*k（k=0..24）、計150要求を保つ。正尺度5店4/8/16/24/28を等重み主比較、店20はzero-scale baseline-onlyの25要求として別保持。保存された入力可用性、14日labelのnullと実0を保ち、欠測日の補完・欠測窓の除去・店舗や起点の置換はしない。label前の予測とlabel付き予測の対応を全150行確認する。

## 二項の分解

基準B、候補P、実績Y、既存の前期尺度uを用いる。日次は `d=(P-B)/u, r=(Y-B)/u`、完全14日総量は `d=(ΣP-ΣB)/(14u), r=(ΣY-ΣB)/(14u)`。

`候補誤差² − 基準誤差² = d² − 2dr`

補正二乗量E[d²]、整合項2E[dr]、その差を日次・総量別に表示。正の整合項は実績方向への寄与、負なら補正が基準の誤差を増す寄与を持つ。正でも補正二乗量を上回らなければ悪化する。各観測の恒等式差及び集約差を原summaryのMSE差と照合するが、元評価を再発行しない。

- 日次は観測labelだけを使う。総量は14日全観測窓だけで、13日和への置換はしない。
- まず店内で対象件数平均し、固定5店を等重みmacroにする。jointは日次と総量を.5ずつ。異なる支持なのでjointを一つの完全窓分散へ読み替えない。
- 入力なし/ありをともにmean28と比較。補助に入力あり対なしの同じ恒等式を表示し、統計入力差と基準を置き換える能力を分離する。
- 全体、全5店舗、起点所属の固定4四半期、全20店舗×四半期を保存。原単位の予測や尺度はGitへ送信しない。
- 補正ゼロ、必要補正ゼロ、同方向/逆方向、`|d|>2|r|`の件数も事前固定の記述とする。件数を二乗誤差の寄与や独立試験数へ置き換えない。
- 店20は尺度0のまま、両模型欄がbaselineと完全一致すること・正値/実0/欠測支持だけを確認。架空の正尺度を作らない。

補正率の最適化・縮小後の仮想成績、u再計算、外れ店舗除去、良い四半期だけの採択、seed/LR/尺度/期間探索はしない。過学習、尺度移行、営業状態などの原因はこの恒等式だけでは同定できない。

## 保存と区切り

新しいpure calculatorの数式・欠測・等店舗重み・尺度0拒否・入力対応を架空fixtureで一回確認。その後、新しい専用EvidenceStoreへsource/契約/原4ファイル/入力binding/全集約診断/原summary差照合/全child stdio・exit・失敗を保存する。元root・新閉鎖rootへ追記しない。記録の原予測・尺度はlocalだけ、Gitは独自calculator/fixture/集約文書・索引・引継ぎだけ。

900秒/private2GiB/output1GiB/single32MiB/32files（normal24file768MiB/failure8file256MiB）、記録16MiB512files/part256KiB/reserve2MiB16files、prep128KiB16files、Git各batch512KiB16path/stdout1MiB/累積30秒を維持。各新書込み前に容量と件数を確認する。原失敗・原全stdioを保全、容量/停止でPAUSED、重複再試行なし。

この診断を一つの報告で終了し、direct PAUSEDで区切る。Astra案Bの店舗分離学習、暫定2%基準、新2017/予約31–54はここで実行・解除しない。automation PAUSED、追加agent0/CARE手動待ち、formal_permission=false/credit0/native7役禁止/登録holdout未読/正式受入未完了を維持する。
