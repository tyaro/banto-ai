# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**engineering consumer入口の接続が完了。16試験pass、実保存7ファイルから記述結果を出力・読み戻し済み。次は契約案との対応と残件・容量時間予算の整理。**

- [API/CLI](anomaly-v03-engineering-consumer.md)、[結果](results/anomaly-multiseed-v0.3-engineering-consumer-entry-2026-09-25.md)。長い引継書§168。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装6567a857455847baf225f552abf5ff9df6644c08。OUT artifacts/engineering-consumer-entry-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。

## 今回の成果と次の作業

anomaly_v03_engineering_consumerのprepare_engineering_result/run_engineering_consumerとCLI mainを追加。外部保持した結合・記述保存点の2pinと明示analysis-inputs.jsonから、固定7file/7,896,608bytesを認証。元レポートの同じanalysis anchor/input pin/campaignを確認し、LocalPublicationで4payloadを新規保存、writer終了後にreaderで全出力を照合した。

16新規試験pass（failure/error/skip0、0.560秒）。実接続は同一processのCLI mainで約2.055秒。120区間/720評価、18表・234主指標・5,670診断行を保持。最終chunk119 attempt2、過去失敗1件、判定不能46指標を保持。集計入力はhash照合のみで解析・コピーなし。JSONはcanonical化して値は完全一致、MD raw一致、HTML末尾LFだけ追加。観測/score読取、集計/比率/score再計算、追加評価/bootstrap0。

成功保存published-successのmarker hash97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e、receipt11507bytes/SHAe2ac5bb2b36d5121062dd8bdc790556cd767cd22a7168ec0579d5aab6570cf3a。閲覧はpayload/report.md/html。初回tuple比較の単体試験失敗と、その後のHTML末尾LF欠落による未完了publishedをtest-attempt-1/2とともに保全。成功した最終出力と区別する。

現在のanalysis/report bytesは認証。旧公開metadata・集計・診断・cell/schema検証は再利用し、全payload/source-runtime正式受入/trust/analysis/execution/formal/promotion/S6/controllerプロセス終了はfalse。local_verifiedは通常権限の新しい結果保存の確認に限る。契約案はdraft、正式gate/holdoutを開いていない。

外部結合保存点7032bytes/SHA3d7d53fc00ad90de695d44e128d29c45467318da58e11b8ab3bf9d0571521305（consumer-analysis-binding-2026-09-25）。外部記述保存点7932bytes/SHA79364b641f8f7a047298ca73d46fcdc49b1931c23394a043cb8802255392af39（descriptive-report-2026-09-25）。旧OUT不変。

peak37.25MiB、最小RAM12.53GiB/commit余裕19.81GiB、C/D122.78/268.83GiB。OS実値os-state.json。banto-24 PAUSED、旧保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変。

**次は契約案T01〜T12へ実装済みの入口を対応付け、未接続項目と容量・所要時間の見積もりを整理する。** 重い評価・観測/score検算を繰り返さず、正式採択/freezeの判断に必要な残件を具体化する。保留principal/P-U試験は再開しない。

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
