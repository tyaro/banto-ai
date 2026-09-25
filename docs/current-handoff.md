# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**実際のreader観測を証拠validatorへ接続。新規13＋既存回帰27種類pass。次は依存source/runtimeの採取範囲の拡張。**

- [API](anomaly-v03-reader-evidence.md)、[結果](results/anomaly-multiseed-v0.3-reader-observed-evidence-2026-09-25.md)、[計画](anomaly-v03-consumer-source-runtime-plan.md)、長い引継書§176。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装0ee336e72ca52849e6725415a3d7f8e4ff75aeeb。OUT artifacts/reader-observed-evidence-2026-09-25、成功attempt-3/。最終文書revision/pinは最上位savepoint-evidence.json。

## 今回の成果と次の作業

anomaly_v03_reader_evidence.check_with_evidenceを追加。親が指定HEADのselected source10本をGit/raw比較し、外部anchorから期待report・入力15fileを保持。supervisorに任意on_started hookを追加して元handleからPID/生成FILETIMEを取得。子はself handle/起動flags/path/OS/CPU/Python executableとloaded DLL/sourceを前後観測。元ownerの記録・保存launch/expectedファイル・子report/証拠を、親のメモリ保持値で検証する。

最終13新規試験pass、failure/error/skip0、15.385秒。同工程初回のsupervisor13＋通常reader14passを、その後source不変確認のうえ再利用（unique40、最後に全40を再実行したわけではない）。初回7failure/1errorはGit hardlink2の扱い。Gitだけ実リンク数とhashを記録・前後照合するよう修正。attempt-2は12pass、記録のメモリ保持を加えたattempt-3で13pass。失敗・中間OUTは保全。

保存例は実child PID 38824、exit0/reaped、監視0.809秒。15入力/19773bytes→reader report 1317bytes。子のOS26200.9457/CPython3.14.0/no_site=1/hook0が親の起動前期待値と一致。fixture原本は一時directory終了で片付け、保存例のexpected/evidence/report/monitorは保持。実データ評価ではない。

今回processの最大private 50.43MiB、保存例の子は36.34MiB。観測時の最小空きRAM 10.21GiB / commit余裕 17.88GiB、保存例後C/D空き 124.38/365.97GiB。 旧境界・dirty guard・closed・banto-24 PAUSED維持。前工程49code/18dataから意図的に変えたのはsupervisor1本、新規adapter/tests2本。以前のraw pinを更新しない。前工程manifest16683bytes/SHAaa64a001a17ea0a4cb54778c1d5d775323e7cb32619c8f7ed108aaecf3f26e1d。

**次：readerの依存sourceとstdlib/extension/loaded DLLの記録範囲を広げる。既知のCRLF差を現在の作業コピーで修正せず、必要なら指定revisionの一時的な候補checkoutでraw一致を確認する。正式freezeとしては扱わない。** 現adapterはsource10本/Python2fileの部分記録。既存inspection collectorはproducer/workflow前提なので直接正式受入へ転用しない。Git helper/DLL、stdlib内部/extension/OS DLL、全project依存は未完了。現在のvalidatorは前後profileの一致を要求するので、import準備と実処理のどこを前観測とするかも明示する必要がある。

新APIは通常権限・単一writer終了後・新規確認directoryに限る。30秒/512MiB/64KiBは子の監視枠で、親のpreflightを含む正式全体予算ではない。1file16MiB/入力合計32MiB、各Git10秒を上限とする。所有worker未終了はUnreapedWorkerをそのまま返し、記録保存失敗でもownerを保持する。principal/UAC/ACL/同時書換え保証は追加していない。

既存document_draft.analysis_consumer=nullとformal/promotion/S6/trust/full closure=falseは維持。source/runtime受入・正式consumer/最終audit・全体予算は残る。正式契約/予算を判断できる実装・証拠を先に用意する。240h/96GiB案は未適用。正式freeze/gate/holdout・50,000実データdraw・新評価と保留principal/UAC/ACLは起動しない。旧formal OS pin9168不変、Windows3.12必須化なし。Phase2/3全体は未完了。

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
