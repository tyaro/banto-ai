# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**監査済み720評価のseed raw countsを認証・集計。関連33試験と旧集計照合を通過。実データCIは未算出。**

- [今回の認証・seed集計](results/anomaly-multiseed-v0.3-independent-seed-aggregation-2026-09-24.md)、[前工程の独立算術](results/anomaly-multiseed-v0.3-independent-inference-math-2026-09-24.md)。長い引継書§157。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。最終実装`d48ecb4ac2a1d6c7c72d3cd16966b84600e165c5`。OUT `artifacts/independent-seed-aggregation-2026-09-24`、成功は`verified/`。最終文書revision/pinはOUTの`savepoint-evidence.json`。

## 今回の成果と次の作業

`anomaly_v03_seed_aggregate.py`は、前工程manifestを外部SHAで認証し、生成/score/完走保存点と全報告の入力pin・identity・最終attemptを接続する。観測payloadやscoreを再計算せず、保存時点の検算結果を使う。新たな生payloadの完全性証明ではない。

dev8/smoke2を登録順で保持し、各seedの全12 layouts×2層×3候補、profile状態、予定母数を検査した。seed90表・role18表・候補差12表を保存。旧集計の1404組の整数countsと144差分点が一致。整数は完全一致、点だけ1e-12 relative/absoluteで比較。overallは両層の分子/分母の合計。共通算術のcounts/ratioへ接続し、実bootstrap/gateは呼んでいない。

初回は警報0件の適合率46評価の`ci_status=inconclusive`を厳しすぎる入口が拒否した。初回記録を保持し、分母0のnull形式を受け入れる修正を実施。全警報0/一部警報0を含む新規12＋既存21=33試験通過。undefined_input_pointsにIDを残して分母や予定時間から当該区間を落とさない。profile判定不能は今回0件だがfixtureで伝播を確認。

実行1.289秒、peak private 39.27MiB、最小空きRAM 15.63GiB / commit余裕 21.22GiB、終了時C/D空き 130.22/297.07GiB。小さな248 JSONを認証。追加観測/評価/score再計算/実CIは0。旧保存点/source/本流/dirty guard不変、banto-24 PAUSED。

**次は独立analysis出力のschema接続。** 認証済みcountsと算術の入力/出力を整理し、手例でschema/gate/選択の接続を検証する。現dev8/smoke2はrole別の記述集計を維持し、正式40 holdout bootstrapを代用しない。実CI/holdout/producer/正式gateを自動起動しない。

slice/delay、runtime/単一writer受入、正式実データCI/全gate、完全S6は残る。selected_candidate=null、formal/promotion/S6=false、performance=not_evaluated。Phase 2/3全体を完了扱いしない。

## 前工程の到達範囲

全120区間・240datasetsの正常生成/overlay/丸めは4,320,000保存観測行で完全一致。全720評価のprofile/score/ledger検算と入力pinで接続済み。旧C1/C2の記述統計は変わらない。生成検算の実装47dbc165f12fb1ce7608bb57625cb498bc4a4d04、文書31b73008828a52681f2ae9a887d88ddedecb516f、OUT artifacts/independent-generation-audit-2026-09-24、成功はverified/、manifest 29473bytes/SHA256322a7fe20b23febcb4467ba16034ab9bae5c209777590150c61bccbae09c90f8。

生成検算工程は既存10 seedを120 pairs分メモリ内で再構成し、新dataset/新評価は0だった。その次の算術検証は固定bootstrap indexと手例だけを計算した。今回のseed集計は保存済み監査報告を読み、観測seed再構成/score再計算/bootstrapを行っていない。旧観測/score検算は不要に繰り返さない。

## 完走証拠と保全

起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。`artifacts/chunk-119-retry-2026-09-24/savepoint-evidence.json`は8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。前回全件score検算保存点は26529bytes/SHA256 b591663d8026e348b81e427da8a169702625b160a1352cd7e7e2c07c6e43e9c9（文書commit64fa36c）。これら旧OUTは変更禁止。失敗chunk119/attempt1は保全し、verified attempt2だけを使用。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiはclean 889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

control000010は終了済み。journal362、全120区間/720評価、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a。controller/所有worker終了確認済み、banto-24 PAUSED。旧保存点・元payloadを理由なく再計算しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
