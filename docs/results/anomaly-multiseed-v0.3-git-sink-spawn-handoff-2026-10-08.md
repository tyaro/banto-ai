# v0.3 Git sink／pipe／原spawn owner受渡し（2026-10-08）

code `27be314059e8f092b994258ada176dab3c17c717`。clean文書HEAD `d90bb704910f9851a940d6fd7c6191163832d8cf` からの小さいopt-in単位。

## 保存した境界

- `GitSinkAdmission.bind_spawn` は元creatorを検証／root clock IOより前に保持し、元pipe bootstrapへsink admissionを結ぶ。sink bootstrapと各原native binding／先行admissionの参照を保持したうえで、同じ原creator／完成済み空sink／原root残余を確認する。まだspawnを開始しない。
- 原NativeGitPipes.bind_spawnへ同じFileIO streamsを渡し、返った元SpawnIOOwner/nativeをpost checkpoint前に保持する。両bootstrapのsuccessorと元spawn/nativeから同じadmissionへの参照を残す。bind前後のIO/割込みでもpipe outputs/read handles/raw writer/sink stream/pendingが同じ原ownerへ残る。再bindでは元creator/descriptorと拒否したcreatorを保持して拒否し、pipeを再createしない。
- callerの既存spawn後の`bind_output` は原SpawnIOOwner/nativeへ同じ元spool/stream/read handlesをGitOutputOwner.from_spawnで結び、返ったoutput ownerをpost checkpointより前に保持する。spawn前／再output bind／別admissionを拒否して元ownerと先行参照を保持する。
- sinkの`_failed`は原native例外を再送出し、sink_errorと元IO errorを保持する。既にあるnative.original_errorを上書きしない。spawnのattribute/stdio cleanup例外でも原Job/process/thread/inheritedと同じsink admissionが保持される。

これはfake CreatePipe／spawn／Win API／Job/processと実小FileIO/root計測のprotocol gate。実CreatePipe/exe/worker/Win ABI/native認証／容量合格ではない。新methodsの実worker caller/transport/read/stop-reap、output_limit時の元Job停止、pipe receipt publisherは未接続。`ReaderGitParent.create_native`はroot/channel/Job前拒否を維持する。原Python ownerの実terminal catch/keeperへこの新sink境界を渡す処理も必要で、参照保持だけをPython終了保全へ読み替えない。

close後のadmission checkpointはまだ未確認として拒否する。原named read/FileIO closeのreturn／fd/file identity／raw witnessと同じ原keeperへ結び、元closeを反復せず再照合する接続が次の単位。EOF／stream.closed／metadata／marker不在／root exit／worker kill-waitだけを回収済みTrue/lease/ackにしない。並行parent/childのatomic予約・coupled peak、同期Peekのwall/停止保証も未実証。

## 焦点と保存

新11件を一回の最終source run、0.1838095秒、fail0/error0/skip0。両bootstrap→同じ原spawn/sink、既存fake spawn tuple→同じoutput/core/spool、spawn前output拒否、再bind/invalid creator、bind前後clock割込み、原spawn cleanup失敗のcore+stream保持、output生成後checkpoint失敗、先行admission conflict、output再bind拒否を確認した。参照fixtureはmodule参照とfake setupだけで、旧suiteを実行・重複discoveryしない。

35 source/science pin前後不変、先行admissionの共通32pinのうち変更owned_git_job以外31pin不変、変更2file target safety／unique11／clean code-save35working-Git一致。新production module0／名前30source／各phase32要求／予定64Jobを維持するが完全runtime閉包ではなくfresh profile/policy/request/unusedroot未準備。旧HEAD/profile/pinを流用しない。全helper終了／critical ownerなし／実native0／追加agent0、完成suite/native/profile再観測反復0。

raw: `artifacts/preformal-git-sink-spawn-handoff-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 10998 | `53ab6106a2fc4c48b5cdaf08ab52d52175b1232d03fc8acb0e09fc08c7d02d9e` |
| focused.log | 2303 | `0eeca3cab9469cb016b82cce4e18bf08f6b17ec10aed825d63ae2efd0529e259` |
| code-save-checkpoint.json | 374 | `caf289f9f0ae8b5c87a20c176524d6df056f00fd7721acd3121d0ccf44f34c82` |
| initial-ci-status-read-failure.json | 249 | `10bcfb70ba1296a2dad417ea3e6d93ef88c502447c56d0fe105448d6d801c72d` |
| code-push-first-failure.json | 353 | `b6dff6dcfe662948fe800297e50c9d38f4907ea9e53feaf53edf20c8a78057c8` |
| code-push-final.json | 193 | `bebedcd7add90166d82889848959529e18be57d88b384e0c09a93a7f24b7b977` |

helper33520/creation134358659645455818/token506e4a930062c30dc17eaaa789016544522aaee97c9b3035257f2d6548d91f54 はexit0/CIM残存なし。元identity/tokenをlive/executionへ保存し、PID単独で過去processと同一扱いしない。

## 外部保存と次の単位

初回code pushはGitHub Internal Server Errorでremote rejected（Request ID0781:B130:1E8799:2AC644:6AC67AAB／2026-10-07T17:00:29Z）。原失敗を保存し、git ls-remoteで旧d90bb70のままと確認後、同じcommitを一回だけ再pushしてorigin一致を保存した。新native/試験の再実行はしない。初回CI37651176465の状態読取りもwsarecv接続断で失敗し、read failureとして保全、終端へ読み替えず今回再照会0。

未保存CI37651176465（full6a77b8ef764ff97a4ed929ed2616b2ef6bca8c4a/各minor3432予定）は今回の終端未確認、37654425831（full8eba6cfa9dd3fcf633e314908327f7449fe8a9d0/3444予定）は進行中、新37655643970（full27be314059e8f092b994258ada176dab3c17c717/3455予定）はqueued。各終端のrun/attempt/jobs/fullHEAD/workflowを固定して専用rootへ一度保存。成功時だけlocal回帰/runner v2、失敗は小さい原因確認と原raw保存。doc-only新CI追跡なし。

次は原named close/raw witnessをadmission／同じ元keeperへ結ぶ小さい単位。閉じたstreamをmetadataだけで許可せず、不明close/Delete／既存Unclosed／未回収／診断・IO・割込みで原Popen/Job/process/thread/extra handle/Python owner/stream/buffer/pending/inflight/partial archiveを保持して後続Git/worker拒否、blind retry/原Python終了へ落とさない。実transport/stop、元returnからのpipe receipt publisher、元owner保持caller/限定launcher、最新clean HEADのfresh source/runtime/profile/policy/request/unusedroot／coupled容量／exclusive準備はその後の別単位。準備完了までnative入口を開かず、全7役whole.runを限定readerとして起動しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理なし。正常readback済み新inflight固定3fileと新directoryだけ整理可能。旧正常モデル786782B/31entry／generic失敗stdout1MiBのreader1704030B>reserve後917504Bを新cap/requestへ読み替えず、旧14source/pinやproducer pre26/post24を親111/111へ流用しない。

formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。先行全repository safety30秒timeoutは未確認保全・再試行なし。実ロード依存／業務異常子孫／正式5残件／正式採択／最終受入は未完了。
