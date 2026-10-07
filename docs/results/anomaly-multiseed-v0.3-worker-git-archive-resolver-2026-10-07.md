# v0.3 worker Git archive／原raw resolver部品（2026-10-07）

code `ba6f82e01eeedb4007a402589cd459f458b4308b`。gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## 保存／再読取り境界

WorkerGitArchiveはcaller-held inventory pinを持つProofVerifierへ結び、原receipt/stdout/stderr・close event、または確認済みrecovery eventとpartial receipt/archive bytesを独立したworker-git.binへ保存する。旧parent source_blob archiveの形式・使用済みrootは変更しない。各leaseのcanonical recordを単一gzip frameにし、全rawの名前/bytes/eventを保存する。stdoutはcallごとに保存し、cache/dedupはこの部品では接続しない。

archive512 KiB、圧縮record128 KiB、展開record1536 KiB、stdout1 MiB以下、manifest32 KiB、64call以下を保持。測定budget leaf内の固定filename/depth2以下・exclusive new fileだけを許可し、phaseはpre→postの順序とする。元receipt/output/policy/close・expected call/evidence pinを確認し、追記後は外部manifest/raw/frame pin・全coverage・全recordを再読取りしたうえで、原rawとも再照合する。failed receipt/recoveryは最後の保存callに限り、後続appendを拒否する。

書込み前にpending packet/evidence pinを保持し、未知write/fsync/close・readback/checkpoint/割込み失敗ではpartial archiveとpendingを保全してwriterをpoisonする。後続appendで元pendingを上書きしない。原rawを削除/移動しない。SavedWorkerGitArchiveはcaller-held manifest/inventory/raw pin、strict canonical fields、frameの順序・coverage、単一gzipの展開上限、原close/recoveryと元creation identityの重複を検証する。readと公開verifierの入口も毎回disk pinを再照合し、cached packetだけで改変を見逃さない。

storage/resolver自体はprocessを起動/回収せず、leaseやackを完成にしない。opt-in VerifiedLeasesへこの原raw resolverを渡すcode経路を試験した。recoveryのlease releaseには元ChildGitKeeperの同じoriginal/lease/cached completionと全handle closeを別に必要とする。unknown attribute/close/既存Unclosed・未回収を回収済み扱いにしない。

## 焦点と保存

新16試験 / 3.203126秒、fail0/error0/skip0、module discovery unique16。正常head/status/source_blob、failed receipt、recovery partial rawと元owner保持、archive raw→lease→ack→独立parent fenceのcode経路、partial writeと無再試行/pending保全、readback割込み、欠落/不正close、disk変更・manifest pin/permission差、frame offset/trailing bytes、gzip膨張、既存file/測定path/広いstdout inventory拒否、shared checkpoint停止、元identity重複の拒否を確認した。

fake Kernel/executable/creation/common-budget checkpointとfixture rawによるprotocol gate。実worker/実exe/実Win ABI/native認証/容量合格ではない。先行proof18/旧parent archive54/keeper13等の既存suiteは実行しない。選択18 source/test/science pin前後不変、変更2file safety pass、code-save HEAD=origin/clean・18 working/Git一致。全helper終了・critical ownerなし・追加agent0・新native0。full repository safetyは先行e4cb30秒timeoutの未確認を保全し再試行しない。

raw: `artifacts/preformal-worker-git-archive-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 7997 | `56211ba751158d77ac8f44fe489431bdc4a632e1d0002d93806386d7e8f9681a` |
| focused.log | 3451 | `e42b49c624ab7ebca456e71251b05efacefa49e2d734cfc8714b1ee69e074c4a` |
| code-save-checkpoint.json | 843 | `80ae6e26b898e16af58a2fec98574d344e94cedd339c87f2064f829366ed7c0f` |

## CIと次の小さい単位

新CI37598762191（HEADba6f82e、各minor3263予定）と修正fixture CI37596406096（HEAD9473523/3247予定）は進行中。先行CI37592838738（HEAD7da5aa9/3247）は終端failure・各minor fail1/error1/skip237/source不変、compare skipped。失敗は前のctypes.get_last_error未stubの同2件で、9473523より前のHEADを再確認した。原7rawは `artifacts/ci-diagnostic-37592838738/` に保全、index2922 B / `acdd87eb92885328635389ef5d8f075bf3d58f3272d8c563dfea739eb9dd524d`。旧失敗をsuccessへ読み替えない。

実actor/shared stop probe/実worker入口/原keeperのPython終端保全・0-job proof/部分ack再照合は未接続。次はこのarchive/resolverに実Git callerのcapture_quiescence・exact lease/原raw/元keeperを渡す小さいactor境界を固定する。metadata旗/root exit/marker不在だけでTrueにせず、0-job/部分ackと元owner終端を入口接続前に扱う。caller checkpointの停止・cleanup時計も既存上限内で結ぶ。実importを含むsource/runtime inventoryと未使用rootを新revisionで準備し、旧14/14やproducer pre26/post24、親111/111を流用しない。

control完成4+pending4、git-proof/pending、caller inventory/manifest、worker-git.bin、inflight/失敗raw/partial archiveを測定rootへ計上する。outer1MiB/32entry/depth2/reserve128KiB・全体321MiB/672entryを保持し、接続/拒否/停止保全とexclusive準備が完成するまでnativeは開始しない。旧親archive520852Bの残余3436Bへ追加/再起動しない。実ロード依存・業務異常子孫と正式5残件は別単位。
