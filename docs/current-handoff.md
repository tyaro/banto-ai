# 次のタスク用の短い引継ぎ

更新: 2026-09-26 JST。**既存dev/smoke記述レポートの解析証拠→通常公開→別readerまで成功。次は正式受入の残件整理。**

- [今回の結果](results/anomaly-multiseed-v0.3-saved-report-publication-2026-09-26.md)、[API](anomaly-v03-analysis-publication.md)、[source/runtime計画](anomaly-v03-consumer-source-runtime-plan.md)、長い引継書§182。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。OUT artifacts/saved-report-publication-2026-09-26。文書保存revision/pinは最上位savepoint-evidence.json。

## 今回の成果と次の作業

既存dev/smokeの保存済み記述レポートに、profile付きanalysis→通常公開→別observed readerを適用して成功。実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48のpc01と前工程の依存候補を再利用し、source変更・新checkout・新reference起動・試験suite再実行は0。前回43試験の合格記録はcode pin不変を確認して再利用した。

認証した原本7file/7,896,608bytesから4payload/2,755,533bytesを出力。旧published-successの4payloadと2marker、計6fileのbytes/pinが新公開と一致し、原本7fileと旧公開6fileも実行前後で不変。過去の120区間/720評価の記述結果を保存したもので、新評価/数値再計算は0。

analysis PID14244、writer PID22020、reader PID21668。両子ともexit0/reaped、観測error0。全体26.528秒、子の監視はanalysis 2.072秒、reader 2.077秒。analysisの依存234fileは保持候補と前後一致、readerの依存232fileは終了後disk/Git照合。全処理harnessのpeak private 69.38MiB、analysis子 54.05MiB、reader子 52.51MiB。保存準備時は空きRAM 10.81GiB、commit余裕 19.30GiB、C/D空き 133.19/345.92GiB。最終値はsave-checks.json。

前工程manifest29435bytes/SHAe25092c42073f9129615bdb8188789a0eb07933d70dc9faa2f97469b7fb71dd3。公開marker 97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e。chain result 1709bytes/SHAea8b5c8b1185d06de8ae93a2e620191e742214be123fc630b7cc73edc8fc0f0c。保存先profiled-analysis/、published/、chain/。元の7入力も旧公開も残っているので削除しない。失敗attemptのcleanup/再利用なし。

旧62code/18data・pc01/旧候補・実計算c01d1c9/本流6f1285d/closed・既存dirty文書/CRLF差は保全、banto-24 PAUSED。今回の通常公開はengineering記述結果だけ。formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。

**次は受入残件表を現在の実装・保存結果に合わせて更新し、正式consumer/本文provenance、独立数値audit、writer実行証拠、完全資源予算の未充足を具体化する。既存720評価は再実行しない。** 独立数値検算、writer全実行観測、正式source/runtime受入と総予算は未完了。正式gate/holdout/freeze、principal/UAC/ACL、push/mergeを開始しない。

## 直前の公開接続実装と架空試験

実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48、文書f93396977642ed09c32522e516969f95dc9e4b53。OUT analysis-publication-chain-2026-09-26。新14＋既存29の43pass。外部analysis result pinから4payloadを通常公開し、writer終了後のobserved readerへ接続。公開と解析を別のpublication-bindingで結ぶ。部分書込み/応答喪失はunconfirmed、公開後reader失敗でも公開物を保全し、未終了ownerも保持する。pc01と前工程profileを今回再利用した。

## 直前のanalysis事前依存候補

実装140e91de93e2cc43c45fab9efb9a7cbc6ece43c7、文書5e584b4c2fab65ef3d22c32f3376a0ac574835ca。OUT analysis-dependency-profile-2026-09-26、ap01保全。新20＋既存23の43pass。source13/Python2file/10入力、全234file/179modules/48imagesを事前保持し、別analysis processで前後一致を確認。候補はcandidate-not-accepted、正式固定ではない。

## 直前のanalysis実観測

実装2db441e44a65857f288f800a104ba436339358b9、文書edd34cdf00d98b72527232b380ffd1ee4f0f24a7。OUT analysis-observed-evidence-2026-09-25、observed-example/。新15＋既存32の47pass。7保存入力から4payloadの準備をowned childへ分離。source12/Python2file/9入力を親保持期待へ結合。補助source29/全233fileは終了後照合。今回の候補対応がこの次工程。ao01の元候補は保全。

## 直前のreader事前依存候補

実装0b2da336d90bcc60e97798d83d17d9f6f7421a34、文書a114416aea2e87e64a6184e7c1a633f57a35b785。OUT reader-dependency-profile-2026-09-25、成功final/。新規16pass＋不変26種類を再利用。prepare_profileで別readerから候補を作り、後続readerへ232files/177modules/48imagesを事前保持して比較。profile110646bytes/SHAa682eb680def9a61227696de7f76c6d6259d99705403cb150e41933ebb66a0ab。reader専用、16入力目に候補を結ぶ。rp01はclean上記実装で保全。OS更新を記録して別候補の再作成は許容、旧候補自動更新/旧formal pin変更なし。

## 直前の依存採取拡張

実装0b03b91a59c7359e4eb05e3585242b88aa8c8cab、文書49c37f3afc52b8a7c5b807b7624d361a2664dddb。OUT reader-dependency-observation-2026-09-25、成功attempt-2。source28/stdlib79/cache候補77/extension8/その他native40、計232file。外部nativeは親にもloadした同一pathに限定（ESETを含む）。新規13pass＋不変29種類を再利用。disk bytesはmemory codeを証明せず、cache候補は実使用bytecodeとは断定しない。Git helper/一時unloadも未完了。

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
