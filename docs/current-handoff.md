# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**consumer実行証拠validatorを追加、16架空試験pass。次は通常権限readerの実起動観測と結合。**

- [API](anomaly-v03-consumer-evidence.md)、[結果](results/anomaly-multiseed-v0.3-consumer-execution-evidence-2026-09-25.md)、[固定計画](anomaly-v03-consumer-source-runtime-plan.md)、長い引継書§175。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装c79fc9e5db7d486a22c2ed4b5f5e75ca0027f7a0、OUT artifacts/consumer-execution-evidence-2026-09-25。最終文書revision/pinはsavepoint-evidence.json。

## 今回の成果と次の作業

anomaly_v03_consumer_evidence.validate_execution_evidenceを追加。fixture/engineering-dev-smokeのanalysis/audit/readerを対象に、外部に保持した期待値とraw証拠pin、前後source/runtime、process identity/command、全source/runtime/input/output bytesを対応づける。新規16試験pass、failure/error/skip0、0.081秒。期待値まで偽造された場合の実行真正性は保証せず、execution_authenticated/full closure/formal等falseを返す。

source descriptorは既存形式。Windows/AMD64・CPython3.14.0・-I -S -Bが初期profile。OS更新はinvocationごとに実値記録を許し、同一実行内の変化を拒否。formal/inspection自己申告pass・役割違い・PID再利用/token違い・欠けたsource・bytes差・未終了を拒否。成功返り値が持つinput/output pinは全供給byte照合済みだが、実process採取へはまだ未接続。既存document_draftのanalysis_consumer=nullは維持。

試験processの最大private 27.20MiB、試験前後の最小空きRAM 11.20GiB / commit余裕 19.57GiB、試験後C/D空き 124.34/365.97GiB。 新たなruntime collector/子process/登録データ/評価/bootstrapは0。前工程47code/18data pinは不変、新規module/test2本を追加。旧boundary・dirty guard・closedを保全、banto-24 PAUSED。資源snapshotは今回の監視値で、保存例のOS/CPU/PID/file内容は架空。

**次の作業：通常権限readerの実際の起動観測と外側で保持した期待値を、このvalidatorへ接続する。最初は既存の小さな架空公開結果で確認し、親の観測値を子の値として流用しない。** 呼出し側が保持するinvocation_id/start_token・実PID/commandと、別process側の起動観測、指定revisionのsource bytes、保存済み結果のbytesを対応づける。証拠から期待値を自己採用しない。新APIの期待値/Mappingは信頼した呼出し側の責務で、今後その採取adapterが必要。最初の接続は通常権限・単一writer終了後・新しい確認directoryに限る。

前工程readerは実装863af36c74aad1bc63ff42bd5b2b469c748882df/保存86fc575480da0549e2f6e9ecaf0c2b3cce87b181、OUT consumer-reader-no-site-2026-09-25。manifest16722bytes/SHA64b3e6010c59b2123ebcf519c97d95ec3f5f86524d47a182f2deff70c38a133e。14試験passと-S除去の対照検出済み。未終了owner保持、公開結果保全、既存失敗directory非再利用を維持。今回はこのsuiteを再実行していない。

静的41source/18data候補はe9826bd時点のレビュー。reader6file pinは25静的候補のclosureではなく、inspection collectorはproducer/workflow必須のinspection scope。generator.py/manifest.pyの既知raw CRLF/LF差は保全し、候補確定時に別clean checkoutで確認する。source/runtime full closure、正式consumer・最終audit・資源予算は未完了。旧CIを現候補の全回帰と扱わず、Windows3.12必須化もしない。

正式契約/予算を判断できる実装・証拠を先に仕上げる。240h/96GiB案は未適用、実freeze・正式gate/holdout・50,000実データdraw・新評価と保留principal/UAC/ACL/同時書換え試験は起動しない。旧formal OS pin9168不変。Phase2/3全体は未完了。

## 直前のslice接続

実装52a032bf8bb22a1eee301ba0cb6d4bbb77a35bed、文書e9826bd0245cf26cf540e1ff470528c001f3cd5f、OUT consumer-slice-fixture-2026-09-25。manifest9528bytes/SHAd369b8c848d9137f9a95279eff84746cf06ef9854cf5bd830f5fd645d64d4fe0。13試験pass、本文1233行/補助2835行/詳細9表。文書の未充足はstatus/provenance/analysis_consumer/bootstrap。slicesの接続は架空入力のmapping確認で、正式採択やraw観測導出の受入ではない。

## 直前の別process reader

別process readerの実装35842261a90b1efe475056dc9ef962c56773f1f1、文書fecea3614e0e818d5e4004fa4672ada06f77021a、OUT consumer-separate-reader-2026-09-25。manifest10053bytes/SHA8e2a647c5539901ce1aa7c5b0924fc98e6b5ed435f1a8a0c9e7fe875d5d92b53を今回の外部起点にした。13試験と実公開物4payload/2,755,533bytesの別process確認済み。T11/T12 engineering部分のみ接続。独立数値auditは実施していない。

writer終了後の通常権限reader、外部markerと2保存点pin、別確認directoryを維持。確認側失敗は元publicationを変更しない。UnreapedWorkerはowner保持、CLI retain_until_exit。旧未完了published/test-attempt等を再利用/清掃しない。

旧保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変、banto-24 PAUSED。principal/UAC/ACL/同時書換え作業は保留。Phase2/3全体は未完了。

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
