# Source objectとsupervisor callsiteの同原owner保持（2026-10-11）

## 今回のunit

人の明示再開によるACTIVEを維持。開始2026-10-11T11:03:24Z、clean文書HEAD767a90c1c27faf9956ba7ccc1d58b4790058faf1、元production/test0919168683de1bdeafaea73bd5e2b44da77f7459。先行24helperのfull saved creation-start_token/live-execution一致、read-only CIM同original不在、repository helper-critical ownerなし。追加agent起動・再活性化0。

production3＋新test1/4pathを一回commit/push、code HEAD55c3f86e3751b3049529a11f5a122246d624a3e4。文書2pathの追補は一回[skip ci]へ集約。完成379634/2d66/4081failure、379685/091916/4097success、379656/f9/4081success、379582/fe518/4062failureと旧failure/旧2minor/全過去failedは別source/runのまま保存し、照会/download/verifier/完成focus反復0。

## 接続した境界

既存reader capture_supervisor_source_object→同supervisor module SourceObjectOutputCallsite→同原SourceObjectBatchContractPreparation.capture_raw→既存RawCaptureを接続。新production module0、旧SourceBatch class/v1 schemas/create_native早期拒否は不変。

原(parent,index,stdout stream,stderr stream,opaque receipt,declared exit,partial,read_wall)をgetter前にprivate保持し、原preparation/worker getter return、同原worker/preparation/callback/bindingを固定する。元絶対(clock,started_ns,deadline_ns) tupleをそのまま渡し、read/stderr/cachedごとに期限をリセットしない。parent/preparation両private ledgerとanchorを照合し、worker差替え/alias消去/ledger消去/再入/第二初期化-binding/foreign cached inputsは第一errorへ固定する。

read callbackが拒否を飲んでreturnしても元bytes/prefixをRawCaptureへ保持して次read/stderr/raw登録を止める。元capture callback returnも形/owner判定前にprivate保持。cached同inputsは無clock/無read、failed再入はcallsite/read/wall ledger増分0。worker getter割込みでは元inputsとpreparation getter returnを先に保持しstream getter/read0。新private callsite tupleを既存同原ParentPublicationRetentionへ保持し、public alias消去からowner解除へしない。新keeper/close/reclose/reap0、借用stream close0。

実superviseの新opt-in source_object_callsiteは元argv/cwd/control_root/limits/probe/boundary/on_started/resource_probe/stop_fenceを保持して、clock/path/runtime probe/FileIO/Popen前にpreparation-only拒否する。既存default supervisorは新captureを呼ばず、actual generateも新keywordを発行していない。

## 観測の範囲

workerはcallerの同Python object参照で、Popen creation identity/HANDLE/Job owner認証ではない。streams/window/opaque receipt/declared exit/partialもcaller工程入力。superviseが実発行した書込み専用xb pair→読取stream→captureのowner受渡しは未接続。原第一errorを解除してnativeを起動する入口ではない。

blocking read自体の中断/clock-checkpoint callback/metadata-proof-join-packingを含む全経路wall、全future検出byte/一時raw/追加callsite-wall ledger/tuple/decoded/native buffer/all-writer同時保持/全32entry/global coupled peak/RSS/OS排他-all-writer atomicは未証明。原14call4358432B容量拒否の再実行・解除0。fresh loaded source/runtime全閉包-profile-private policy-native request-unused exclusive root未発行。caller EOF/期限内return/原readback/manifest/cached completionをnative認証や容量許可へ補わない。

## 新しい試験

15distinct/body18、複数source/runで最終source単一15successではない。

- 初回新12一回0.02880550001282245秒：10pass/fail1error1skip0。既存captureの(incoming,proof_raw) tupleをdict/record objectと取り違えたtest期待値を原log/JSON/failed helperへ保存。
- 失敗2＋第二初期化/第二worker binding/worker getter割込みの新risk3だけv2一回0.017540000029839575秒：4pass/fail1error0skip0。残failureは値が等しいtupleのidentityを誤って要求したtest期待値。
- その失敗1の期待値だけ訂正しv3一回0.004191000014543533秒：1pass/fail0error0skip0。完成初回10/v2完成4/旧16・19・前19・前16/容量訂正1case/旧suite反復0。

小実FileIO＋実time.monotonic_ns、注入read/clock/Mock checkpoint、opaque Python worker/receipt、ReaderGitParent.__new__、retention試験専用Escapeを使用。supervise入口はPopen/path/clockをAssertionError mockで禁止した拒否試験だけ。実Job/HANDLE/ACL/stdio/child/native0。試験cleanupはproduction/native回収ではない。selected observationsは件数/prefix幅で、全原read bytes literal保存/helper全process stdout-stderrではない。

## 保存・Git・CI

114source-science workingを各run前後/最終metadataで照合。開始113の未変更110はverified091916親tree/先行37Git/doc-only非交差継承、変更production3＋新test1を新code Git bodyへexact固定。safety違反0、科学hash metadataだけ/holdout観測未読/credit0。named30source978466B、最大archive130691B/e5ab8de3cc7f02f6ccc9f5eb08feeb5e283a64782c2e16bc78ac8f25c6f36337/source cap差381Bはfull runtime/global容量ではない。旧SourceBatch14301B/create_native437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7c不変。

components原helperは存在しないreader.SOURCE_NAMES参照でAttributeError/exit1。原script/live-execution/failureを保持し、別continuationで旧named30の名前順だけ継承して現pinと未保存metadataを保存。原helper/試験反復0・failed書換え0。今回focus2failed/components1failedと過去failedを保持し、production/CI/native/Sol容量failureへ読み替えない。rg不存在source2pathと文書builderのfunctions.exec SyntaxErrorはtool excerpt metadataのみ。後者はisolate評価前/tools0/process開始0/tracked mutation0。foreground creation/full process logsNone。

code Git batch221167B4entry/実累積4.267719199997373秒、各batch512KiB16entry/output1MiB/累積30秒。大stdoutは取得時全文照合しpin保存でhelper全process logsではない。新code fullSHA gh run list一回は空配列、原stdout3B/37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570/stderr0/exit0。新run/attempt/jobs/終端/journal/count未固定、空選択をsuccessへしない。待機/反復0/doc-only新CI追跡0。

原root artifacts/preformal-source-object-supervisor-callsite-20261011-prep/ 最終21file158358B/root-closed2415B/4717ba766d3799f0430f28db16849a0785264cb52a1963d2a17a56868c2c7f84閉鎖。post artifacts/preformal-source-object-supervisor-callsite-post-20261011-prep/も保存後閉鎖。両512KiB32entry/reserve128KiB/single128KiB。最終count/bytes/manifest/full helper identitiesはpost-save/owners-after-save/root-closedを優先。追加/同保存/完成15/元failed helper反復禁止。

## 次

次heartbeatは実fullSHA55c3f86e3751b3049529a11f5a122246d624a3e4のCI選択一回。未終端/空なら反復・待機なし、終端のみ新専用rootへ未保存raw一度/実summary後count固定。旧CI/旧focusを反復しない。

次機能は実supervisor発行write/read stdio ownerと元絶対期限の受渡し、receipt/partial実transport、診断専用公開/parent_failure実raw/child bootstrap、OS排他-all-writer atomic、全32entry/global coupled容量。今回caller holder/入口拒否を実write owner認証/正式許可へ補わない。

create_native早期拒否/全7役whole.run限定reader起動禁止/元caps-unknown原owner-stop/追加agent禁止/formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了を維持。Sol容量エラー/人の停止割込みでは保全後PAUSED・重複再試行なし。ACTIVE継続・状態不変通知なし。
