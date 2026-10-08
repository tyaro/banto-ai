# Publication storage allocationの外部発行・bootstrap・Reader/Actor接続

2026-10-08 JST。formal gate=`s4_acceptance_not_frozen`、formal_permission=false、正式credit0、登録holdout観測未読。実データは保存済み合成dev8/smoke2のengineering読取り・記述報告のみ。新production module0、追加agent0、実worker/Job/pipe/exe/native起動0、runtime/profile再観測0。

## 一つの経路として保存した範囲

code `fa82cf720df6a428ad0c4b344b0fe100e0bd05a0`を下記の実fullSHAで一回commit/push。6productionと新testの7fileを対象に、初回request以前のallocation保持から、実request/inventory発行、entry、Reader、Actorのarchive作成前までをまとめた。途中の失敗rawは原source/runとともに保持した。

- 新external `anomaly-v03-preformal-initial-reader-git-storage-plan-v4` は独立allocationのclosed `value/pin`、pipe_raw_limits、14名append_control_limitsを必須とする。既存32KiB canonical descriptor/pinを元shared clock内で再読取りし、generateのroot/profile/runtime IO前copyからParentへ同じpinでforward。旧v1/v2/v3のfieldsを増やさず、形式変更・allocation欠落・pin不一致を拒否する。
- PublicationStoragePreparationは原root/revision/shared budget/clock/checkpoint/owner/source/call maxima/private policy/profile pin/allocationをcopy・検証・IO前に保持する。実outer root lstatの原return/identity、実snapshot32entry/depth2、14将来control枠＋最大call failure raw＋独立archive追加枠＋carrier失敗枠＋親failure枠＋reserve128KiB/診断2entry＋未作成channelを保守的に照合する。観測済みcontrolを差し引かず、元root上の保持rawを削除して通さない。
- 初回requestの元FileIO/close/rename/rawと形成endpointが返った後に独立inventoryを発行し、actual raw/pin/64call/root identity/同clockへ元storage gateを結ぶ。初回request以前にrequest pinやinventory pinを生成しない。初回unknown IO/creation/clock/getter/copy失敗は元input tuple/Python ownerへlatchし、通常診断・返却前の既存ParentPublicationRetentionへ渡す。
- 新reader entry `anomaly-v03-preformal-reader-git-storage-entry-v3` のstorage contextはrequest/inventory/root identity/revision/clockと元allocation value/pinをclosed canonical JSON/pinで固定する。旧entry v2/request/ack/proof JSONへ追加fieldを入れず、借用kernel/stdinをJSONへ入れない。Readerはchannel IO前にcopy/pin確認し、Actor前に実requestと照合する。
- Actorとwriterは元objectをconstructor IO前から保持する。Actorの同checkpoint/control gateへstorageを発行し、archive/sink作成前に予算を照合。初回worker-git.binのexclusive FileIO原stream/fd/fstat/path identity/flush/fsync/close return/全空raw readbackを保持し、unknown closeをclosed metadataや空disk一致で解除しない。FileIO.closeはPython所有fdの原returnであり、Win HANDLE CloseHandle returnやnative回収の宣言ではない。
- Actor constructor失敗をReaderの元actor/error/storage/control/writer/streamへ結び、reader_worker_mainは通常print/return前に原ReaderInitializationRetentionでPythonを保持する。新keeper生成/kill/wait/close/publish/read/reap replayなし。callback後の元issuance context pin改変、Parent準備sidecar消去、metadata復元も同じ最初の例外で拒否する。既存default bootstrap入力tupleは10fieldを維持し、storage opt-in時だけ元allocationを末尾へ保持する。

## 焦点確認と原失敗

新22distinct/最終AST unique22、body呼出し34。最終source単一22success runではない。完成済みfocus/旧suite/native反復0。

| component | body | pass | fail | error | 秒 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 初回 | 20 | 10 | 2 | 8 | 4.302648499957286 |
| 失敗10のみ訂正後 | 10 | 10 | 0 | 0 | 16.991994599986356 |
| 新risk 2のみ | 2 | 1 | 1 | 0 | 3.4302946999669075 |
| 残るrisk 1のみ | 1 | 0 | 1 | 0 | 1.365336099988781 |
| 残るrisk 1のみ再補強 | 1 | 1 | 0 | 0 | 1.0789830000139773 |

初回8errorは準備clockが既存requestのimplementationを保持しなかった接続不一致。元clock情報のreturnを保持して一致を固定。fail2は等しいPathのobject identity期待と、保持root entriesを過大に想定した試験期待。Path equalityへ訂正し、実保持file2名を独立に追加した占有root拒否へ訂正した。元log40400B/d33af5f6457d82207d27f0e3b39f38fc21e8978fb41e4a6d0432e24ce44f2512を保全し、pass済み10は反復しない。

新riskはcallback後issuance allocation pin改変と準備sidecar消去。後者は拒否はできたが準備ownerのfirst error保持、さらにParent後続のgeneric ValueErrorへの置換が残ったため、同じ元例外を準備/storage/Parentへlatch・再送出するよう補強した。補強のhelper-v4はprior focused filenameを誤って置換しFileNotFoundErrorで本体0、exception/live/executionを保全。そのhelperを成功runにしない。試験のretention loopは専用_pause Escapeで抜けるだけで、本番owner解放/native回収を示さない。

各5componentの53source/science pin前後不変、他49は全component一致、先行storage scope共通44不変、変更7file safety0。最後のdefault tuple metadata互換差分は低影響の1行保存で焦点を反復せず、最終source pinはcode-saveでworking/Git一致を独立確認した。science2は既定pin一致のhash読取りだけでholdout観測未読。

fake creation/budget/private policy/Popen＋実小FileIO/root/channel/archiveのprotocol gate。正常composing snapshotと上位stage/supervisorは明示stub、worker/native起動なし。実rootの占有拒否を別ケースで確認したが、stubを実coupled peak/atomic予約/全失敗保存/全経路wallや容量合格に読み替えない。

## 証拠と元helper

raw `artifacts/preformal-publication-storage-forwarding-20261008-prep/`。初回・訂正・補強のraw/scriptを全て保持。

- components.json 12176B/7b2f78f5b9f608c001cfa284800b679fd67c7c13cf94cd2a52cb03de96bffedf
- code-save.json 8203B/9e3acb62e9f9b2b6e625d6cfb6b49b582d83b9f859709ec8e3da98ee1721d10b
- 最終未pass1のfocused-v6.json 16964B/676a9e09155d6ec9801a05dc47e3bfe9686ae99a2ec3f6c471d4a6278586dd1c、log364B/aedbd8e4c2506a45fdc3d7739cba8dcc68662b8a0c70bbe46f746b0b1fdcb3c8

- `49488/creation134358995675895183/token06e960c31efd4451d0f6cd9551bde2a616ba536954dfd01f3a72f997a1d4748e`: failed。元live/execution一致、CIM残存なし。
- `36540/creation134358996236860845/tokenb63ce8377fa4e51a945cf74030119c47f35fe96a3891e98329444529495f98dd`: passed。元live/execution一致、CIM残存なし。
- `31904/creation134358997661544182/tokena00c474066a27637555b7981037d6e37a3f302fdff18f29a82e78bd04e401bbc`: failed。元live/execution一致、CIM残存なし。
- `43888/creation134358997999266953/tokend16a19e55393947c97f1a1f5fa3114952617bfe40195f3fa2c2d22e15a51b3f5`: failed。元live/execution一致、CIM残存なし。
- `46604/creation134358998267683541/token63571a5ee1110575998a8f21466b8b6ba42d709078cf311dee940843ed6bb2ce`: failed。元live/execution一致、CIM残存なし。
- `46204/creation134358998596063962/tokenb1362a407d2e7d8906a0e28e75db8b8176053a23acac661065e8841778c052eb`: passed。元live/execution一致、CIM残存なし。

PID再利用は元creation/tokenで区別し、PIDだけで同一扱いしない。全helper終了/critical ownerなし。専用prepはpost-saveを最後の32fileとして閉じ、512KiB/32entry/reserve128KiBを維持する。このrootへ追加/完成22focus再実行しない。

## CI状態（原raw保存とは別）

今回のgh読取りでrun結論successを確認した未保存CIは37704906810/full e3004745c83962b73ed21cf8415385a1328df4e4、37708333072/full9a83455025918dbe04c8052372fee23cc37da345、37711478075/full112f3cd0cf2973213ca70b1d5337e8c423468246。attempt1/push/Phase 1 CI。jobs/journal/log/local回帰/runner v2の終端証拠保存は今回追加0、既存成功CIや現code/native/容量合格へ読み替えない。37714331936/full0b80bf7d21f42e22a358e895ca160f1142fc6f81は開始時in_progress、新37717924409/fullfa82cf720df6a428ad0c4b344b0fe100e0bd05a0はpush後in_progress。

次のCI保存単位では外部fullHEAD/workflow/run/attempt/jobsを固定し新専用rootへ一度保存、成功時だけ2journal/comparison-regression/3log/local回帰/runner v2、失敗時は小さい原因確認と原raw保全。実fullSHAのみ、空選択をrun/終端にしない。完成CI/旧run failure/fixture/discovery失敗rawを反復・successへ読み替えない。doc-only追補はskip ci。

## 未完了と次の単位

同revisionの名前30source・phase32要求・予定64Git Jobは維持、選択source phase730115B/最大worker_git_archive.py94523B。新production module0。これは完全runtime閉包ではなくfresh latest-clean source/runtime/profile/private policy/request/unusedrootの準備は未完了。古いHEAD/profile/source bytes/model/width placeholderを新pin/cap/receipt/proofへ流用しない。

次は原限定launcherのborrowed kernel/stdin/carrier発行とPopen HANDLE creationへ、同じcaller descriptor/request/root/clock/storage/原Python ownerを保持して接続する準備を一つの単位で確認する。その前に今回success終端を観測した3CIの原rawを別の保存単位で固定する。実child local close/rename ownerのtransport認証、全writer同request/root atomic予約、親identity任意将来失敗raw/diagnostic、原partial rawと新archive growthの別予約、entry/context実bytesと実packet/gzip/frame/receipt/partial coupled peak/global/memory/実loaded source-runtime/業務異常子孫は未完成。

ReaderGitParent.create_nativeはroot/channel/clock/Job前拒否を維持。実carrier/native入口を開かず、全7役whole.runを限定readerとして実起動しない。同期Peek/Read/Write/caller間wall・停止は未実証。storage結果native_launch_authorized/atomic/capacity/parent_ack_authorized/execution_authenticated=false、正式5残件/正式採択/最終受入は未完了。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。unknown IO/Close/Delete/Unclosed/未回収/割込みは元owner/stream/fd/raw/pendingを保持し、blind retry/metadata回収宣言なし。旧raw-root整理/上限緩和/使用済みrootへの追加なし。停止割込みとSol容量エラーでは保全後heartbeat PAUSED、通常はACTIVEを維持する。
