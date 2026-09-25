# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**readerの依存記録を232fileへ拡張。新規13試験pass＋不変な既存回帰29種類を再利用。次は役割別の独立した期待profile。**

- [API](anomaly-v03-reader-evidence.md)、[結果](results/anomaly-multiseed-v0.3-reader-dependency-observation-2026-09-25.md)、[計画](anomaly-v03-consumer-source-runtime-plan.md)、長い引継書§177。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装0b03b91a59c7359e4eb05e3585242b88aa8c8cab。OUT artifacts/reader-dependency-observation-2026-09-25、成功attempt-2/。文書保存revision/pinは最上位savepoint-evidence.json。

## 今回の成果と次の作業

`check_with_evidence(..., observe_dependencies=True)` を追加。前後のsys.modules/実file origin/既存pyc候補/EnumProcessModulesExのloaded imageを採取。request解読とcollector import後が前観測の境界。parentは終了・stdout pin・元handle観測を確認してから、依存sourceは指定Git、runtime等はdisk内容/identityへ照合する。外部nativeは親にもloadされた同一絶対pathのみ許可。

成功例はsource28、stdlib79、cache候補77、extension8、その他native40の232file/47,574,229bytes。177modules、native48images。検査中の追加/消失/変更0。ESET eamsi.dll/ebehmoni.dllを含む。dependencies.jsonとdependency-crosscheck.jsonは補助記録。**既存validatorのsource10/Python2file bindingと区別し、child由来の一覧を独立した事前期待値や完全closureとは扱わない。** cache候補を実使用済みbytecodeとは断定しない。

新規13pass、failure/error/skip0、10.825秒。初回41件中、新規live2件がESET範囲外でfail、他39件pass。修正はnew collector/testのみなので、初回の既存reader13＋pure evidence16を再利用（unique42、最終全42再実行ではない）。前段unit10件中2errorだったWindows lstat/fstatのctime差も記録、device/inode/links/size/mtimeとhashへ統一。失敗記録を保持。

候補checkout C:/Users/TKent/.codex/worktrees/rd01/banto-ai はclean 0b03b91a59c7359e4eb05e3585242b88aa8c8cab。743tracked files/8,430,967bytesをGit blobへ比較済み。候補を保全し、元70b0のgenerator.py/manifest.pyのCRLF差は維持。正式freezeではない。sample child20520 exit0/reaped、1.566秒、peak private36.30MiB、stdout240,485bytes。架空入力原本はtemp cleanup済み、観測/期待値/monitor/reportは保存。

資源は資料生成後RAM11.08GiB/commit余裕19.47GiB、C124.35/D365.94GiB。最終値はsave-checks.json。依存採取512file/1file64MiB/合計256MiB、1MiB buffer。opt-in時のみoutput枠1MiB、既定64KiBと30秒/512MiBは維持。親preflight含む正式総予算ではない。試験harness全期間peakは未採取。

**次：reader用の依存一覧を実行結果とは別に保持する期待profileへ落とし込み、import準備の境界と照合手順を定義する。今回の観測一覧をそのまま正式な期待値やfreezeとして採択しない。** まず通常権限readerの小さな架空入力に限定し、別に保持した候補profileと本番読取の実観測を照合する境界を設計・実装する。analysis/audit役割、動的にunloadされたimage/Git helper、全体資源予算は残る。

前工程manifest23326bytes/SHA661238bb87e0d8f03bcab795d470a174e4806b4d746775bf6fee483c37bf06ca。旧52code/18dataの意図的変更はadapter1本、新collector/test2本追加。旧境界/dirty guard/closed/PAUSED維持。document_draft.analysis_consumer=null、formal/promotion/S6/trust/execution_authenticated/full closure=false。新評価/登録データ/実bootstrap0。正式gate/holdout/正式freeze/保留principal/UAC/ACLは開始しない。

## 直前の実reader接続

実装0ee336e72ca52849e6725415a3d7f8e4ff75aeeb、文書fa5d9f5f1ebcfb274828c26e1203a4f45549bd54。OUT reader-observed-evidence-2026-09-25、成功attempt-3。selected source10/Python2file、元Popen handleと子selfのPID/生成FILETIME、入出力15fileを外部期待値に結合。新規13pass＋不変な既存27種類を再利用。記録は親memory保持値と比較し、未終了ownerは保存失敗時も保持。通常権限・single writer終了後、新しい確認directoryに限定。

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
