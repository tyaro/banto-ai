# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**全120区間/720評価の保存済み検出遅延・条件別集計を完了。関連32試験、seed90表/用途18表と旧countsの照合を通過。**

- [今回の遅延・条件別集計](results/anomaly-multiseed-v0.3-independent-slice-audit-2026-09-25.md)。長い引継書§159。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装`782dcb7957e29dce481f0dea5c136df85a9152f3`。OUT `artifacts/independent-slice-audit-2026-09-25`、最終文書revision/pinは`savepoint-evidence.json`。

## 今回の成果と次の作業

保存済み10,368,000 score行・14,400異常事例から6軸のincident集計と9軸のscore診断を導出した。720評価JSONは過去の独立監査が認証したpinと全bytes一致。既存profile/score/matchingの導出検算を再利用し、score計算は繰り返していない。dev/smokeを分離し、登録順・12 layouts・予定母数・重複欠落・profile状態を保持する。

検出遅延は因果検出時だけの1〜5秒の正確な度数を保存。全体中央値を元の度数合算から求め、未検出0秒補完や区間中央値の平均をしない。event-offsetは40計画eventの指定target参照で、10件のload_proxyをunscored_target、負offsetの試験外をoutside_testとして保持する。qualityは当該target自身、overlapは有効qualityと交差する正例の同じtargetの判定窓全体。正式slice schemaを完成扱いしない。

処理844.159秒、process peak private 145.32MiB、最小空きRAM 9.60GiB/commit余裕 16.49GiB。終了時C/D空き 127.05/298.62GiB。 最初の1区間＋6区間ごとの保存、旧保存点/source/本流/dirty guard不変、banto-24 PAUSED。新観測・新評価・score再計算・実CIは0。

**次は、別々に検算したcounts・遅延・sliceを単一の認証済み解析入力へ統合し、正式schemaで不足するsource/runtime証拠等を整理する。現dev8/smoke2は記述集計に限定し、正式40holdoutの代用にしない。** `slices.json`と前工程`verified/authenticated-counts.json`は今回manifestのpinを信頼起点に再利用できる。新しい情報が不要なら巨大な元payloadを再読取りしない。

前工程analysis adapter（実装9b18626703c40801a164f61eb01dab3acbb36eae、OUT independent-analysis-adapter-2026-09-24）は7手例の9表/180判定、関連59試験まで接続済み。fixture packetであり正式full document・実CIではない。formal/promotion/S6=false、performance=not_evaluated、selected_candidate=nullを維持する。holdout/producer/実CI/正式gateを自動起動しない。正式analysis全体のprovenance/runtime、単一writer受入、完全S6、Phase 2/3全体は未完了。

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
