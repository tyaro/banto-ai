# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**集計入力と公開metadataの結合を実装、14試験pass。全120区間/720評価が同じ最終attempt・入力hashへ結び付くことを確認。次はengineering consumerの入口接続。**

- [API](anomaly-v03-consumer-analysis-binding.md)、[結果](results/anomaly-multiseed-v0.3-consumer-analysis-binding-2026-09-25.md)。長い引継書§167。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装c4f04121764c882e1cb885f9fea173e4bc2d6cc3。OUT artifacts/consumer-analysis-binding-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。

## 今回の成果と次の作業

anomaly_v03_consumer_analysis_binding.authenticate_analysis_bindingを追加。明示5保存点（publication/analysis/adapter/seeds/completed）と外部publication/analysis raw pinから10artifactを各1回認証。旧報告内のpathは照合だけで、payloadへアクセスしない。元集計入力を複製せずpath/raw pinと導出関係を小さなreceiptへ保存する。

14新規試験pass（failure/error/skip0、11.189秒）。実保存記録10artifact/9,785,474bytesを0.542秒で結合。120区間720評価、公開管理記録960参照、input hash4,320件、evaluation hash720件が一致。10seed cluster/90seed表/18role表の元集計欄も保持。区間119 attempt2を選択し、過去失敗1件と判定不能46指標を保全。観測/score payload読取・score/集計再計算・新評価・bootstrapは0。

重要: publication_metadata_binding_verified/analysis_input_bytes_verified=true。historical_aggregate_authentication_reused/historical_diagnostic_join_reused=trueであり、旧算術・診断検証を再実行していない。full_payload/source-runtime受入/trust/analysis/execution/formal/promotion/S6/controllerプロセス終了はfalse。前工程の公開metadata/worker終了記録認証と合わせても正式受入へ格上げしない。

外部publication保存点7257bytes/SHA256 00b5e1bb5a668e2636091938604492fc486e78b8c83b3fe3ac1c50da738feaba、analysis保存点7305bytes/SHA256 8527dfe71bcb7544f6276b14eeb8bd853491cd2be87ee4f3e8bec2375b0f876dを使用。結果はanalysis-binding.json/saved-binding-check.json。peak47.41MiB、最小RAM12.38GiB/commit19.72GiB、C/D122.79/268.83GiB。

**次は結合receiptからengineering consumerの入力選択・記述結果までの入口をつなぐ。** 既存の独立監査・集計・記述結果APIを再利用し、重い観測/scoreを再計算しない。旧検証の再利用範囲と、新しく認証したbytesを区別する。正式gate/holdout・追加評価は起動しない。

[契約案](anomaly-v03-consumer-io-proposal.md)はdraft。正式運用候補IDも未採択。保留principal作業は再開せずbanto-24 PAUSED。元科学条件・formal拒否を維持する。旧保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変。

## 前工程の受入残件

[残件表](results/anomaly-multiseed-v0.3-acceptance-gap-review-2026-09-25.md)。freeze前は運用契約、consumer接続、source/runtime固定、公開接続、容量時間予算の5まとまり。今回で全5完了とはしない。11保存点＋3receipt203,543bytesを照合済み、158source等比較中157一致、差分は旧READMEの追記だけ。720評価を再計算しない。

17モジュールの静的候補表にはmanifest.pyのworking CRLF/Git LF差が残る。正規化後同一だがraw不一致なので別clean checkoutでfreeze時に確認。旧Linux CI036ecb4からselected11本が変更/追加、古いpassは最新候補全回帰の代わりにならない。完全runtime/dependency closureは未完了。

本流は別作業でclean6f1285d（旧889cfc3）。temp native/互換試験のmain README記載はGit bytesまで照合し、raw/CI再検証・mergeなし。Windows3.12必須化なし。旧helper.boundariesのmain固定値は古いため、acceptance-gap-review/review.pyのboundary関数を参照。OS直近観測はProfessional25H2/26200/UBR9457、旧engineering9445から更新。formal pin9168と過去runtimeは維持。

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
