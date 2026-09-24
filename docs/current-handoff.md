# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**既存受入証拠を整理し、freeze前の作業を5まとまりに確定。720評価の再計算・再試験なし。**

- [今回の残件表](results/anomaly-multiseed-v0.3-acceptance-gap-review-2026-09-25.md)。長い引継書§162。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。確認基準ddd0165a45f42e9921e849e150d2cba63714b3a6。OUT artifacts/acceptance-gap-review-2026-09-25、成功結果verified/とsupplement-source-map.json、最終文書revision/pinはsavepoint-evidence.json。

## 今回の成果と次の作業

11保存点manifest＋3小型receipt（203,543 bytes）を外部hashへ照合。旧source等158比較中157一致、差分1件はREADMEへの追記だけ。単一writer保存実装は旧27試験時点と同じ。既存720評価・生成/score/ledger/seed/slice検算・記述表は再実行しない。

freeze前の5まとまりは、(1)正式化する単一writer/OS運用契約、(2)正式consumerの入出力接続、(3)source/runtime受入と版固定、(4)controller/保存/readerの公開接続、(5)容量・時間予算。Phase 2/3全体の残件数や試験数ではない。正式holdout実行と最終独立監査はさらに後。

**次は単一writer方針でconsumerが受け取り・検証・保存するものを具体的な契約案にする。既存10入口と正式schemaの不足を対応づけ、必要な接続試験を指定する。** 案がレビュー可能になる前に正式化の判断を求めない。元の科学式/seed/母数/閾値を変えず、実holdout/CI/gate・新評価は起動しない。保留principalも再開しない。

静的import候補は17モジュール。manifest.pyにworking CRLF / Git LFのraw差あり、正規化後同一だが未修正。最終freezeは別clean checkoutでraw一致確認が必要。完全dependency/runtime closureではない。旧Linux CI036ecb4からselected11モジュールに差があり、古いpassを最新候補の全回帰受入へ読み替えない。正式入口run_campaignは未接続、runtime受入はnot_completedのまま。

本流が別作業で889cfc3からclean 6f1285dへ進んだ（4 commit/5 path）。main docs/READMEにはtemp native fixtureの追加試験pass記録があるが、今回は文書のGit bytesまで照合しraw/CI再検証なし。自動統合せず、Windows3.12の必須化も行わない。旧helperのmain HEAD guardはそのまま再使用すると停止するため、今回review.pyのboundary記録を参照する。

今回OS実測はProfessional25H2/build26200/UBR9457。旧engineering9445からの更新を記録。旧formal pin9168や過去のruntime証拠は変更しない。主確認2.450秒/peak private26.82MiB、最小空きRAM11.49GiB/commit余裕19.98GiB、C/D空き126.24/293.31GiB。新評価/試験/元payload読取0。初回main guard停止とraw差停止をOUT直下に保全した。

## 前工程の記述表

[結果表・診断表](results/anomaly-multiseed-v0.3-descriptive-report-2026-09-25.md)、[閲覧用要約](../artifacts/descriptive-report-2026-09-25/report.md)。実装e0753ba4e1518706002cb3a51f9b5a3c891a4e7c。dev/smoke別18表・234主指標・5,670診断行を元入力とschema部分形式へ照合、27試験pass。manifest7932bytes/SHA25679364b641f8f7a047298ca73d46fcdc49b1931c23394a043cb8802255392af39。gate/CI/採択なし、formal/promotion/S6=false、selected=null、performance=not_evaluated。入力のreadinessは作成時点の文脈として保持。

## 前工程のseed集計

全120区間/720評価を5保存点のhashと全報告のidentity/最終attempt/入力pinで認証済み。seed90表・role18表の1404 counts、候補差12表144点が旧集計と一致。dev8/smoke2は各12layouts×両層×3候補。警報0の適合率46評価はnull診断を保持し、予定母数から除外していない。実装d48ecb4、文書c02e7b0、OUT artifacts/independent-seed-aggregation-2026-09-24、成功verified/。manifest7935bytes/SHA2563d03cdef2852e8432b7d1ca9de7cab25ff9b994fefa9819cb290263145426bb5。counts533126bytes/SHA256e6f3012a0a6fe622b5fc7d6365a7a1f2afadec16517f1bbe2cc423253ae68b2e。保存時点の監査連結であり、今日の全payload再検査ではない。

## 前工程の到達範囲

全120区間・240datasetsの正常生成/overlay/丸めは4,320,000保存観測行で完全一致。全720評価のprofile/score/ledger検算と入力pinで接続済み。旧C1/C2の記述統計は変わらない。生成検算の実装47dbc165f12fb1ce7608bb57625cb498bc4a4d04、文書31b73008828a52681f2ae9a887d88ddedecb516f、OUT artifacts/independent-generation-audit-2026-09-24、成功はverified/、manifest 29473bytes/SHA256322a7fe20b23febcb4467ba16034ab9bae5c209777590150c61bccbae09c90f8。

生成検算工程は既存10 seedを120 pairs分メモリ内で再構成し、新dataset/新評価は0だった。その次の算術検証は固定bootstrap indexと手例だけを計算した。前工程のseed集計は保存済み監査報告を読み、観測seed再構成/score再計算/bootstrapを行っていない。旧観測/score検算は不要に繰り返さない。

## 完走証拠と保全

起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。`artifacts/chunk-119-retry-2026-09-24/savepoint-evidence.json`は8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。前回全件score検算保存点は26529bytes/SHA256 b591663d8026e348b81e427da8a169702625b160a1352cd7e7e2c07c6e43e9c9（文書commit64fa36c）。これら旧OUTは変更禁止。失敗chunk119/attempt1は保全し、verified attempt2だけを使用。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiは別作業でclean 6f1285d28a37edf486ba5c49b8dac3708c7f3067へ更新（旧保存点889cfc3）。今回merge/pushなし。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

control000010は終了済み。journal362、全120区間/720評価、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a。controller/所有worker終了確認済み、banto-24 PAUSED。旧保存点・元payloadを理由なく再計算しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
