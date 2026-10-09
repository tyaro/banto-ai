# 同request/rootのwriter宣言・元owner保持の準備

## 範囲

2026-10-09開始10:08:15Z、HEAD d8cada08527b4ce10045736a400898d779e253f7/origin一致・clean。先行3helperのfull creation/start_token/live-executionとCIM同original不在、repo helper/critical ownerなしを確認。最新CI37913386221/fullb4a0401680b0d938598c71ff890948f208eee2b5はcompact一回でattempt1/push/Phase 1 CI/in_progress、run原11696B/c9d10cc5b73b9890c060c9b028a0c6f1c0ba5f08f06e0a445b49f3acb97a9084とstderr保存。jobs/終端/journal未固定、同状態再照会/待機/download/runnerなし。

## 新しい経路

RequestWriterPreparation/ReaderGitParent.prepare_request_writersを同unitへまとめた。元caller owner/未取得clock/publication/declaration/participantsをgetter前保持→private元親owner→同PartitionedPublicationPreparationの元owner-clock-context bytes→新closed request-writer-preparation-v1/context pin/固定5role→宣言した元Python participantのidentityとcontext一致/role一回claim→親_inventory_ready早期拒否→既存ParentPublicationRetentionへ保持を結ぶ。

roleはparent_control/worker_archive/worker_carrier/parent_failure/diagnostic。これはcallerが宣言したPython objectのrosterで、実writerの参加・Job/HANDLE/child transportを認証したものではない。threading.Lockのnonblocking claimは当該objectへ参加するcaller間だけを扱い、OS root排他/all-writer atomic予約ではない。実PublicationStorageAdmission/WorkerGitArchive/carrier/control/diagnostic IOのclaim hookは未接続。全declared roleのclaim成功でもall_writers_registered/exclusive_root/atomic_reservation/capacity/native/auth/ack/formalはfalse、unresolved=true、executeはIO/API/clock前拒否。

元returnはlocal private pendingへcallback後・判定前保存。public pending/ledger/owner marker消去、両claim snapshot消去、reentry/KI/未知clock return、第二constructor、local lock release例外でも原第一例外・元Lock/participant/context/途中view/拒否incomingを保持。private親bindingを保持し、public owner aliases消去で新ownerへ切り替えない。元lock releaseはPythonの局所同期資源のみでnative HANDLE/stream回収claimではない。cached view/executeはclock/snapshot/native反復なし。

## 確認と原失敗

| run | body | pass | error | 対象 |
|---|---:|---:|---:|---|
| 初回 |20|18|2|新20のみ|
| v2 |4|4|0|失敗2＋new risk2のみ|
| v3 |2|2|0|constructor return/親alias消去のnew risk2のみ|

24distinct/body26/pass body24/原error2。別source/runなので最終source単一24successではない。初回cached view testは保存済みsnapshot callable自体を差替えたため元dependency pinが拒否、retention testはmoduleに存在しない_pauseをpatchしたためAttributeError。testの差替え先をos.scandir/ParentPublicationRetention._pauseへ訂正し失敗2だけ再確認。原focus helper failed/script/log/focused/exceptionを保持、原script再実行なし。完成18/旧focus/旧suite/基本runtime probe/13AST監査/native/追加agent/profile再観測なし。

工程stub context/identity/event、ReaderGitParent.__new__、memory archive準備、opaque caller object、小temp root metadata、Mock clock、局所Lock/fake release-return、retention専用Escapeだけ。実Win ABI/Job/ACL/process/stdin/stdio/HANDLE/child close-rename owner認証/全経路wall/RSS/global coupled peak/容量合格ではない。

## 保存と未完了

- focused.json: 12891B/949a8603a3955581d01f3ac08872190b6bea496c24f93c89701967e8de23eab1、elapsed 0.5499947000062093秒。log 7760B/6f043552ef9ce68240d82c868aeaf19d276c8c0e194c8cef6fba5e42f5cfd471。
- focused-v2.json: 10666B/f926d24c362c59e9aeb245f28411ac3688fca0ac923bfc6ab456d62956bc969e、elapsed 0.3452229999820702秒。log 942B/347b7e20ccb55483fd4cb799eff07089f821970e3e80870e3e497ffdf348289d。
- focused-v3.json: 10401B/3c55adabb4d98b6e09eef29628d619c75c77a5542847948dabf462d8348adaa0、elapsed 0.40556420001666993秒。log 560B/c37a3dc52a7ee1e349ed6728a4b01b411d33424dfd8b820918974121d6032c5c。

components18786B/014fbd3a463f24f3f7276904dea48df9fae89778ed32b09b036aa1ba32095e85。各66source-science working前後pin不変/他64source不変/開始65working-Git exact、科学hash metadataだけ/holdout観測未読。変更3file safety0/new production module0。旧PartitionedPublicationPreparation/GeneratedChainBudget/_directory_snapshotとcreate_native whole-node-linesはGit開始bytesへmetadata照合して不変。create_nativeの既存source segment437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7cも不変（whole-node-lines442Bのpinは別format）。名前30幅879821B/最大src/banto_ai/anomaly_v03_preformal_worker_git_archive.py 123874B/a9b770f61632ad88c9cc0eac12fb324e6b4d274768e34637ff513636b64e9a0c。名前inventoryをruntime closure/profileへしない。

原metadata artifacts/preformal-same-request-writer-preparation-20261009-prep/を既存512KiB32entry/reserve128KiB/single128KiB内で閉鎖。先行resume21file45365B/CI訂正metadata26file47469B/原failureCI12file5360859B不変。5helperはlive-execution full creation-start_token一致/CIM同original不在/repo helperなし、初回focusだけfailedを保持。CIMはmicrosecondのcreation照合、start_tokenは保存live/executionのfull比較、native回収claimなし。

補助source/template path missと不要なforeground importのModuleNotFoundErrorはtool excerptとして保持し、原process全byte log/production/native/Sol容量失敗へ読み替えない。source-before内の補助tool IDは未検証で、componentが非検証を明示。selected unittest logとgh bytesはhelper process全stdout/stderrではない。

次は実IO writerの同request/root参加、同original ownerのnative/exclusive/all-writer原子予約、fresh latest-clean loaded runtime/source closure/profile/private policy/request/unusedrootへの接続が必要。全planned raw32entry/原partialとnew growth/codec-native buffer-object overhead/global coupled peak、実callsite/stdio/child transportは未完了。旧raw/閉鎖rootへ追加・receipt移動・cap緩和なし。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了。create_native早期拒否/全7役whole.run限定reader実起動禁止/元caps・unknown原owner-stop保持。人の明示再開により自走ACTIVE、停止割込みやSol容量エラーでは保全後PAUSED。
