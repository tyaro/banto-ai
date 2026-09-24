# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**全120区間・240datasetsの正常生成/overlay/丸めが保存bytesと完全一致。前回の全720評価のprofile/score/ledger検算と入力hashを接続した。**

- [今回の正常生成検算](results/anomaly-multiseed-v0.3-independent-generation-audit-2026-09-24.md)、[前回全720評価の検算](results/anomaly-multiseed-v0.3-full-connected-audit-2026-09-24.md)、[比較](results/anomaly-multiseed-v0.3-dev-smoke-comparison-2026-09-24.md)、[上司向け報告](results/banto-ai-anomaly-briefing-2026-09-24.md)。長い引継書§155。
- 候補: C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。生成検算の実装/実行 `47dbc165f12fb1ce7608bb57625cb498bc4a4d04`、score検算本体2505fed。今回OUT `artifacts/independent-generation-audit-2026-09-24`、成功結果は`verified/`。最終文書revision/pinはOUT直下の`savepoint-evidence.json`。

## 今回の成果と次の作業

`anomaly_v03_generation_audit.py`はstdlibだけで正常式、乱数消費順、温度state、event時刻、overlayと丸めを独立に復元する。Random/gauss・binary64・round・JSONは共有する指定primitive。IO/CLIは外部pin付き完走保存点から登録planとverified attemptを選び、8filesを認証して渡す。producerの生成関数や検出器を呼ばない。

全120区間（dev96/smoke24）、240datasets、4,320,000観測行/21,600,000 signal cells、3,600欠損cells、9,600計画events/8,400有効eventsが厳密bytes一致。前回全720評価の検算報告と観測/mask/event-ledgerの720filesのpin、identity、attemptが一致。今回profile/scoreを再計算せず、旧報告を変更していない。

**登録済み10 seedについて120 pairsの正常系列をメモリ内で再構成した**。新規producer/追加attempt/holdout/保存dataset作成は0だが、seed計算0とは書かない。手計算・対照fixture等22試験と実行補助6試験通過。WindowsのUTF-8 decodeと組込みmoduleの実行補助を修正した事前停止2件は保存済みで、両方dataset読取り前。成功分だけを集計する。

所要113.560秒、peak private57.41MiB、最小空きRAM14.57GiB/commit余裕14.84GiB、終了時C/D空き136.81/315.18GiB。pilot保存と6区間ごとの19中間保存、全件最終保存済み。漏れなく一致したのは保存bytesの再現であり、過去内部stateの直接観測や実設備性能の証明ではない。

**次はbootstrap/信頼区間/候補比較の独立実装と手計算fixtureの検算を整理する。** 正式bootstrapは40 holdout seed・50,000 replicates。現10 seedで正式CIを代用しない。生成不要の契約/集計検算から進め、holdoutや長時間producerは起動しない。runtime/単一writer受入、Phase 2 forecastも残る。

今回normal_generation/pre_rounding_overlay/rounding_verifiedは全240datasetsでtrue。前回profile/score/ledger_verifiedは720評価でtrue。independent_s6_complete/formal_permission/promotion_allowed=false、performance_status=not_evaluated、campaign加算0。既存C1/C2の記述統計は変わらない。Phase 2/3全体を完了扱いしない。

## 完走証拠と保全

起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。`artifacts/chunk-119-retry-2026-09-24/savepoint-evidence.json`は8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。前回全件score検算保存点は26529bytes/SHA256 b591663d8026e348b81e427da8a169702625b160a1352cd7e7e2c07c6e43e9c9（文書commit64fa36c）。これら旧OUTは変更禁止。失敗chunk119/attempt1は保全し、verified attempt2だけを使用。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiはclean 889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

control000010は終了済み。journal362、全120区間/720評価、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a。controller/所有worker終了確認済み、banto-24 PAUSED。旧保存点・元payloadを理由なく再計算しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
