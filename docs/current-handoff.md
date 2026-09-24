# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**720評価のcounts・遅延・sliceを認証済み解析入力へ統合。関連39試験、108表の対応と48組の加算照合を通過。**

- [今回の解析入力統合](results/anomaly-multiseed-v0.3-analysis-inputs-2026-09-25.md)。長い引継書§160。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装`1db34dc3502552feb0869da2cec68508736f1b8d`。OUT `artifacts/independent-analysis-inputs-2026-09-25`、最終文書revision/pinは`savepoint-evidence.json`。

## 今回の成果と次の作業

`anomaly_v03_analysis_inputs.authenticate_analysis_inputs`は明示したslices/seeds/adapter保存点を外部SHAで認証し、固定名のcompact counts/slicesと凍結schemaを読む。旧source pinも照合する。今回6入力ファイル・5,453,594 bytesを利用し、元payloadは0 bytes。履歴上の監査済み結果の再利用であり、今日の元payload再確認ではない。純関数join_inputsだけを入力認証と呼ばない。

analysis-inputs.jsonにdev8/smoke2の10 clusters、seed90/role18表、counts・有効露出・遅延度数・全診断を統合。overall30組とrole18組の加算を照合し、警報0の未定義適合率46記録を保持。用途を混ぜず、率/中央値は平均せず、未検出0秒補完もしない。readiness.jsonは正式schemaの必須10項目を対応づけるが、full documentではない。

処理3.176秒、process peak private 53.00MiB、前後観測の最小空きRAM 10.68GiB/commit余裕 15.14GiB、終了時C/D空き 126.79/298.91GiB。 旧保存点/source/本流/dirty guard不変、banto-24 PAUSED。新観測・新評価・score再計算・実CIは0。

**次は統合済み入力から、dev/smoke別の記述結果表と診断表を出力する。正式schemaとの列対応を確認し、event-offsetの対象外/試験外参照やavailability・閾値超過・警報開始数を落とさない。** 今回manifestでanalysis-inputs.json/readiness.jsonを認証して再利用できる。巨大な元payloadの再読取りは不要。元slice定義・元報告は[前工程](results/anomaly-multiseed-v0.3-independent-slice-audit-2026-09-25.md)を参照。

前工程analysis adapter（9b18626）は7手例/59試験のfixture packetまで接続済み。正式40holdout/50,000 bootstrap、CI・gate、consumer source/runtime受入・freeze・provenance/publication、完全S6は残る。formal/promotion/S6=false、performance=not_evaluated、selected_candidate=null。これらと保留principalを自動起動しない。Phase 2/3全体は未完了。

## 前工程のseed集計

全120区間/720評価を5保存点のhashと全報告のidentity/最終attempt/入力pinで認証済み。seed90表・role18表の1404 counts、候補差12表144点が旧集計と一致。dev8/smoke2は各12layouts×両層×3候補。警報0の適合率46評価はnull診断を保持し、予定母数から除外していない。実装d48ecb4、文書c02e7b0、OUT artifacts/independent-seed-aggregation-2026-09-24、成功verified/。manifest7935bytes/SHA2563d03cdef2852e8432b7d1ca9de7cab25ff9b994fefa9819cb290263145426bb5。counts533126bytes/SHA256e6f3012a0a6fe622b5fc7d6365a7a1f2afadec16517f1bbe2cc423253ae68b2e。保存時点の監査連結であり、今日の全payload再検査ではない。

## 前工程の到達範囲

全120区間・240datasetsの正常生成/overlay/丸めは4,320,000保存観測行で完全一致。全720評価のprofile/score/ledger検算と入力pinで接続済み。旧C1/C2の記述統計は変わらない。生成検算の実装47dbc165f12fb1ce7608bb57625cb498bc4a4d04、文書31b73008828a52681f2ae9a887d88ddedecb516f、OUT artifacts/independent-generation-audit-2026-09-24、成功はverified/、manifest 29473bytes/SHA256322a7fe20b23febcb4467ba16034ab9bae5c209777590150c61bccbae09c90f8。

生成検算工程は既存10 seedを120 pairs分メモリ内で再構成し、新dataset/新評価は0だった。その次の算術検証は固定bootstrap indexと手例だけを計算した。前工程のseed集計は保存済み監査報告を読み、観測seed再構成/score再計算/bootstrapを行っていない。旧観測/score検算は不要に繰り返さない。

## 完走証拠と保全

起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。`artifacts/chunk-119-retry-2026-09-24/savepoint-evidence.json`は8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。前回全件score検算保存点は26529bytes/SHA256 b591663d8026e348b81e427da8a169702625b160a1352cd7e7e2c07c6e43e9c9（文書commit64fa36c）。これら旧OUTは変更禁止。失敗chunk119/attempt1は保全し、verified attempt2だけを使用。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiはclean 889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

control000010は終了済み。journal362、全120区間/720評価、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a。controller/所有worker終了確認済み、banto-24 PAUSED。旧保存点・元payloadを理由なく再計算しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
