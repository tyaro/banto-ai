# v0.3 pipe receipt publisher／close前観測と追加IO owner保全（2026-10-08）

code `869b27a58c91b119d7328550efc86f017ca62045`。clean文書HEAD `f0076d4dc471f1ce235d849948f835c19d1a8b55`からの小さいopt-in単位。

## 保存した境界

- `GitPipeTransport`は元spawn tupleとResumeThread returnをpost IO前に保持し、元executable-beforeをcopyで固定する。`capture_receipt_inputs`は同じ原normal keeper/native/return/creation/assignment・未closeを照合し、元Job HANDLEがopenの間だけmemoryを照会。元memory/after executable/full stdout-stderr/reaped returnを検証や後続IO前に保持し、全disk count/digestと元shared checkpointを確認する。closed handleへの後付け照会を拒否する。
- `publish_receipt`は原close completion/core handles/IO witness/捕捉rawと外部policy/expected source-output pinを結び、既存JOB_FORMAT／PIPE_QUIESCENCEの厳密verifierを公開前後に使う。元clockでelapsedを保存し、executable変更／stderr／dirty HEAD/status／blob pin不一致など既知semantic failureはfailed receiptとしてnew work停止を維持する。正常receiptもactive leaseを完了せず、formal/runtime/source closure・execution authenticationの各flagはfalse。
- 固定inflight/receipt.jsonのexclusive空FileIOを返った位置から保持。fd/file identity/count、exact write/flush/fsync、原close returnと全disk readbackを確認する。原full payload／stream／pending／changed raw／例外を保持し、partial/unknown write・close／IO・割込みでは再write/reopen/blind closeを拒否する。cached公開はraw/witnessを再照合し、native/read/memory/新fileを反復しない。
- publisher entryより前に原nativeへpending receipt ownerを保持する。coreがclose済みでもpublisher IO/raw未解決ではChildGitKeeperのcached completionを返さず、lease/ackへ読み替えない。元FileIO.closed／fully written canonical rawなどmetadataだけで不明closeを解除しない。元ownerは完全readback/verifier確認後だけ外す。

fake Win API/Job/process/creation/private policy／memory／executable observationと実exclusive小FileIO/fsync/3B raw、partial/unknown IO wrapperのprotocol gate。実Win ABI/exe/pipe/worker/native認証／wall・容量合格ではない。native_start_identity_authenticatedは原process HANDLEのcreation観測に結ぶ既存receipt整合性fieldで、このfake gate自体の実native認証ではない。

## 焦点と保存

新13件を一回の最終source runで1.8147055秒、fail0/error0/skip0。strict normal receipt/pipe witness／memoryのclose前位置／cached無native再実行、pre-close inputs不足/declared成功拒否、closed handle照会拒否、memory割込み、failed blob/executable、elapsed超過、partial write、unknown FileIO.close、root IO、cached receipt raw改変、IO witness改変を確認。参照fixtureはmodule/setupだけで旧TestCaseをdiscovery/実行しない。

36 source/science pin前後不変、先行normal completionとの共通33pin不変、変更3file target safety／最終unique13／clean code-save36working-Git一致。先行normal10/transport13/旧suite反復0。新production module0／名前30source・各phase32要求・予定64Jobは未閉包、fresh source pin/runtime profile/policy/request/unusedroot未準備。

raw: `artifacts/preformal-git-pipe-receipt-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 11364 | `0ec5ae3317c070fc49f2a15199e904db9d221a28128bc7757ac5f109f0174a96` |
| focused.log | 3057 | `98ee91bf1157753a5d25c50734e88b19f47a23fee138cd1b48a36cd0aa0aec5a` |
| code-save-checkpoint.json | 5691 | `5a2bd4efea75a64e3b48e73b42eaa4eb32ea222b62753a2cb41ee2c860148e52` |

helper PID28116／creation134358726632007058／token7cd4b8b4bfb9dbc920ed8c6f26b240b18b9e871465a7a884d05c34fd84aaf595はexit0/CIM残存なし。元live/execution保持、PID単独で過去helperと同一扱いしない。

全helper終了／critical ownerなし／native0／追加agent0。正式gate=s4_acceptance_not_frozen／formal_permission=false／credit0／登録holdout観測未読を維持。

## 次の単位

実WorkerGitActorの原run_owned境界へopt-in pipe transport/receiptのreturn/witnessを渡す。actorのcaller-held inventory/policy/request/root/callと保存raw・archive readbackを照合後だけexact leaseへ進み、正常receipt／failed receipt prefix／recovery／bootstrap／未解決publisher IO ownerを区別する。元keeperを再生成して原cached observationやpending IOを失わず、terminal catchが元Python ownerを通常終了で落とさない経路を先に固定する。

現在の通常worker／file-directed executorは従来のまま、新publisherはactor/worker入口未接続。同期Peek／caller step間wallと停止、parent-child並行予約／coupled容量、fresh source/runtime/profile/policy/request/unusedroot、限定caller/原owner保持launcherは未実証／未準備。create_nativeはroot/channel/Job前拒否維持。exclusive準備完成前にnativeを開始せず、全7役whole.runを限定readerとして起動しない。

元Popen/Job/process/thread/extra handles/Python owner/streams/buffers/pending/inflight/partial archiveを保持し、unknown Close/Delete／既存Unclosed／未回収／診断・IO・割込みでblind retry/後続Git-workerを拒否。metadata/marker不在/root exit/EOF/worker kill-wait/途中capacity checkpointを回収True/lease/ackへ読み替えない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry・元wall/memory/output・cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理禁止、正常readback後の新inflight固定3fileとnew directoryだけ整理可能。旧HEAD/profile/pin/14sourceやproducer pre26/post24を親111/111へ流用しない。

未保存CI37666095841（full690af4900da6fc198ca7f389db2a61fe1374f602／3481予定）と37667626735（full289cbbcb18fd4919db4f697c1a93cfc55f8e4c89／3491予定）は開始時in_progress、新37670193576（本full869b27a58c91b119d7328550efc86f017ca62045／3504予定）もin_progress。各終端を実fullHEAD/workflow/run/attempt/jobsへ固定して一度保存、doc-only新CI追跡なし。完成CI・部品焦点を反復しない。
