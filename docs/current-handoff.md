# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**T01〜T12の実装対応・残件・容量時間シナリオを保存。次は通常権限での別process readerと外側状態の接続（T11/T12）。再計算・新試験の実行は今回0。**

- [対応表・容量時間](results/anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)、[入口API](anomaly-v03-engineering-consumer.md)、長い引継書§169。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。調査対象6af1c024be52c063e82f9a43143f2fc5e228258b、OUT artifacts/consumer-coverage-budget-review-2026-09-25。最終文書revision/pinはsavepoint-evidence.json。source変更なし。

## 今回の成果と次の作業

契約案の12群は、engineering接続5（T01/02/03/04/10）、旧証拠再利用3（T05/06/08）、計算部品まで1（T07）、接続残り3（T09/11/12）。正式評価の合格数ではない。20保存file/2,818,781bytes、33 source/契約pin、30 method参照を照合。直近5工程の新規試験計81件は保存済み合格記録の参照で、今回実行0。約0.538秒、peak50.29MiB、最小RAM10.38GiB/commit余裕16.88GiB。

正式40 seed/480区間960datasets/2880評価への単純外挿は59.91GiB/活動178.17時間（7.42日）。元実績は7800file/16,081,676,236bytes/160,357.174秒で失敗・再照合を含む。別工程のscore/ledger監査約80.41分と生成監査約7.57分も参考値。正式推論/最終独立audit予算は未確定。

仮のproducer活動枠240時間/出力96GiB、空き予約32GiB、1コピー開始128GiB/同volume2コピー224GiBの案。設定・運用上限へは適用していない。今回C121.97/D256.05GiBでDが候補。開始前の再確認が必要。system commit余裕52.73MiBの過去標本を確認し、process上限と全体commit停止方針を分ける必要を記録。リークや他作業との因果は未断定。OS実値os-state.json。

**次はT11/T12のconsumer接続：writerを閉じた後、通常権限の別process readerと外側receiptをつなぐ。** 固定入力で応答消失・読取不一致・再封印不整合を確認し、旧保存APIの合格済み試験を重複させない。既存確定payload/markerを修正しない。専用principal/P-U/同時書換え試験、UAC/ACL変更は再開しない。正式40-cluster推論/full document、source/runtime受入、契約採択は別の残りで正式gate/holdoutを起動しない。

前工程のengineering consumerは16試験と実接続済み（実装6567a857455847baf225f552abf5ff9df6644c08、文書6af1c024be52c063e82f9a43143f2fc5e228258b）。7file/7,896,608bytes、約2.055秒。全120区間720評価、18表234主指標5670診断行を保持。chunk119 attempt2、失敗1件、判定不能46指標を保全。観測/score/集計/比率再計算なし。

そのOUTはengineering-consumer-entry-2026-09-25、成功published-success/payload/report.md/html。保存点11477bytes/SHA830d2de2202166c7f3f735603c21b317cb18bb33809530d1f3bf8d8c87403219。marker97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e、receipt11507bytes/SHAe2ac5bb2b36d5121062dd8bdc790556cd767cd22a7168ec0579d5aab6570cf3a。初回tuple比較失敗/HTML末尾LF欠落による未完了publishedとtest-attempt-1/2を保全済み。再使用しない。

新評価・payload読取・再計算・bootstrap・新試験0。旧保存点・実計算c01d1c9・本流clean6f1285d・closed・既存dirty guard不変、banto-24 PAUSED。正式契約案draft、formal/promotion/S6=false、全5まとまりに正式化の残りあり。

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
