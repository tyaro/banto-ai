# Supervisor module発行FileIO pair・元close/read owner保持（2026-10-11）

## 保存単位と実行範囲

人の明示再開に従いACTIVEを維持。開始HEAD `0c7084771f2111b7a41cc73a5a60c0d7e90b9588` / upstream clean。元34helperのfull creation-start_tokenとsaved live/execution一致・CIM同original不在、5failed/29passed・過去failedを保持。追加agent起動/再活性化0。

production 2path＋新test 1pathを一回commit/push、code `a54961c025fc7c9023c3a53a57993be99626240f`。文書は本書とcurrent-handoffの2pathを一回[skip ci]へ集約。原caps、create_native早期拒否、全7役whole.run限定reader実起動禁止を維持。

## 接続した経路

ReaderGitParent.prepare_supervisor_source_object_output_pairから同supervisor moduleのSourceObjectOutputPairPreparationを同原親private ledgerへ保持。元(parent,index,stdout path,stderr path,opaque receipt,declared exit,partial,read_wall) tupleをgetter/validation/IO前に保存。元preparation getter return/worker getter return/capture callback/FileIO factoryも保持する。

同parent directoryの元絶対stdout.jsonl又はreport.jsonとstderr.jsonへFileIO xb pairを一度発行。原factory/getter/fileno/fstat/lstat/checkpoint/clock/close/captureのinvocationをcallback前、原return又は例外を判定前のprivate operationsへ保存。部分openの原streamを保持し、二回目のopen/close/readを再実行しない。fd/pathのdev/inode、regular/non-reparse/single-linkのPython metadata整合を確認する。ACL/OS排他/stdio HANDLE認証ではない。

元write streamのcloseを一度呼び、literal None returnが観測された2streamだけread入口へ進む。closed flagをunknown close returnの代替にせず、第一errorを保持して第二close/read-open/captureを止める。None以外の返値も原literalを保持したまま拒否する。read FileIO rb returnを判定前に保持し、元write側file identityと独立stdout/stderr raw maximaへ結ぶ。同原read pair/receipt/declared exit/partial/絶対windowを既存SourceObjectOutputCallsite→同原SourceObjectBatchContractPreparation.capture_rawへ渡す。

callsiteに同原issued pairのprivate bindingを追加。read callbackがpair ledger aliasを消してbytesを返しても、原bytes/prefixを保持して次read/stderr/raw登録を止める。callback再入の拒否を飲み込んでFileIOを返す場合も、元FileIO returnと第一errorを保持する。cached writers/close/captureは無clock・無IO。第二prepare/第二初期化/部分read-open後のfailed再入も再発行しない。既存ParentPublicationRetentionへprivate pair tupleを追加し、新keeper/kill-wait/reclose/reap0。成功read ownersも保持しproduction close0。

元caller tuple(clock,started_ns,deadline_ns)を各IOの前後とcaptureへ同一参照で渡し、stdout/stderr/readごとの期限リセット0。clock/checkpointのliteral returnを先に保持し、非int/逆行/期限到達を拒否する。blocking FileIOの中断、callback自身・proof/packing/joinを含む全経路wall保証ではない。

## 未完成の境界

今回発行したのはsupervisor **module内のPython FileIO準備**。実superviseのdefault output with/Popen/on_started/stop_fenceへは接続せず、既存source_object_callsite opt-in入口拒否とactual generateの新keyword未発行を維持する。元worker/receipt/exit/partial/windowはcaller Python工程入力で、実Popen creation/HANDLE/Job/stdio継承/child receipt/native transport又はsupervisor発行の絶対native clock認証ではない。実superviseがpairを使用した証拠は0。

read FileIO pairの同identityと元close returnを確認した局所経路であり、他writerによる同inodeへの書込み排除、OS排他-allwriter atomic、fresh loaded全閉包/profile/private policy/native request/unused exclusive root、全32entry/global coupled peak/RSS/全future ledger・buffer・検出byte・一時join/decoded/native保持を証明しない。128operation上限は局所件数上限だけ。外側callerのwriteはこのunitのbounded writer又は実supervisor stdioとして認証していない。全14call4358432Bの容量拒否の再実行・解除0。

## 新ケースと原観測

新14distinct/body14。初回新12一回 `0.09847760002594441` 秒、12pass/fail0/error0/skip0。reviewの第二初期化・第二read-open失敗の具体的新risk2だけ一回 `0.01494350004941225` 秒、2pass/fail0/error0/skip0。初回testの同一式を簡約し新2を追加した複数source/runで、最終source単一14successではない。完成12/旧15・旧16・旧19/容量訂正1case/旧suite/旧native/collector/probe/37Git/CI/verifier反復0。

小実FileIO/実time.monotonic_ns/注入factory-close-read-clock/opaque Python worker-receipt/ReaderGitParent.__new__/Mock checkpoint/retention Escapeを使用。PopenはAssertionError mockで実Job/HANDLE/ACL/stdio/child/native0。test cleanupはproduction/native回収ではない。selected observationsはoperations/read-prefix件数で全原process stdout-stderrではない。

apply_patchのcallsite binding追補は期待行quote不一致でmutation前に一回拒否。selected tool excerptをtool-patch-miss.jsonへ保持し正しい対象行へ訂正。foreground original creation identity/full process logsはNone、production/CI/native/Sol容量failureへしない。原34helperの5failedを今回の全passedへ読み替えない。

## Source・容量・Git・CI

115source-science各run前後一致。変更production2＋newtest1はcode Git exact、未変更112は verified55c3親tree/prior37/doc-only非交差から継承。科学hash metadataだけ/holdout観測未読/credit0。旧SourceBatch14301B/0903a855f665499d9e3eba5248ceaca09387b948a7051d42704d792db18c0b17とcreate_native437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7c不変。named30source `992758` B、最大archive130691B/e5ab8de3cc7f02f6ccc9f5eb08feeb5e283a64782c2e16bc78ac8f25c6f36337/source cap差381Bはfull runtime/global容量ではない。

code Git batch `163160` B/3entry、実累積 `4.291871100082062` 秒。512KiB16entry/output1MiB/累積30秒維持。大stdoutは取得時全文照合とpin保存でhelper全process logsではない。

先行code55c3の実fullSHA selection一回は38134980431/push/Phase1CI/in_progress。原stdout156B/2ecac7f6b6bab508221d8573f4fab60f5bf2e3fb770ad4fdccca7d4775da4117、stderr0/原gh exit0保存。attempt/jobs/終端/journal/count未固定、待機・反復0。新code `a54961c025fc7c9023c3a53a57993be99626240f` の実fullSHA selection一回は空配列、原stdout3B/37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570/stderr0/原exit0。空をsuccessへしない。doc-only新CI追跡0。完成379634/2d66/4081failure・379685/091916/4097・379656/f9/4081success・379582/fe518/4062failure及び旧CIの再照会/download/verifier0。

## 原保存と次工程

原 `artifacts/preformal-supervisor-output-pair-20261011-prep/` は 15file/103844B、root-closed.json 1750B/fe6474965e33a238e9281c2be481785dbb8c19da2aeeec9817bc3fa1dc978fdfで閉鎖。postは `artifacts/preformal-supervisor-output-pair-post-20261011-prep/`、CI selectionは `artifacts/preformal-ci-supervisor-callsite-current-save-20261011-prep/`。各metadata512KiB32entry/reserve128KiB/single128KiB。最終post-save/owners-after-save/root-closedが最終pins/count/bytesを優先。閉鎖後追加/同保存/完成14/元helper再実行禁止。

次heartbeatは38134980431/full55c3 compact一回と新a54961実fullSHA selection一回。終端だけ未保存rawを新専用rootへ一度保存し、現3.14 journal/独立verifier/2logsをfullHEAD-workflow-run-attempt-jobsへ結び実summary後count固定。空/未終端は反復・待機なしで機能unitへ進む。以前停止した古い部分CIは履歴のまま保持する。

次機能はこのpairを実supervisorの元write stdio/Popen/on_started/元stop fence/原絶対期限に結ぶこと、全future receipt/exit/partialの実transport認証、診断公開/parent_failure原raw/child bootstrap、OS排他-allwriter atomic、fresh loaded全閉包、全32entry/global coupled peak。今回Python close/read identityをnative許可へしない。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/登録holdout観測未読/正式5残件・最終受入未完了。Sol容量エラー/人の停止割込みでは保全後PAUSED・重複再試行なし。追加agent禁止を維持。
