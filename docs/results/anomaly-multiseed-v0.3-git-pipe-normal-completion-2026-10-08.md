# v0.3 Git pipeの通常call完了／critical owner昇格（2026-10-08）

code `289cbbcb18fd4919db4f697c1a93cfc55f8e4c89`。先行transport690af49の停止・回収部品からの小さいopt-in単位。

## 接続した境界

- `GitPipeTransport.normal_completion`と`ChildGitKeeper.normal_completion`を明示boolのopt-inとして追加。既定の停止keeper経路は維持する。元native/child/leaseを保持してから通常active lease・owner不在・未停止・原error不在を検証する。
- 通常modeは原Jobのfresh accounting／原process HANDLEのexit0／creationを照会してemptyを確認し、Terminate/waitやchannel.stopped／hold_ownerを実行しない。同じ原kernel/reader/admission/named read/FileIO/core closeと全raw照合を通し、正常channelをno-new-work terminalへ落とさない。
- 通常観測・creation・close・raw確認が失敗したら、元keeper/nativeを保持したままpromoteのlatchをledger IOより前に立て、child.stoppedと原ownerを結ぶ。ledger割込みでも元error／keeper／停止latchを保持し再登録を増やさない。不明read closeは再closeしない。既知False core closeは原secondary ownerと残ったnamed handleだけを保持する。output_limitは既定の原Job停止keeperへ渡す。

通常modeの終了観測後もactive leaseは未完了、finishedは増やさず、resultはfailed recovery形式／lease_completed・parent_ack_authorized・execution_authenticated=falseを維持。正常64call継続・success receipt／archive／lease接続を完成したとは宣言しない。通常receiptを作る次の単位ではJob memory等の必要な元観測をcore close前に保存し、elapsed/executable-after/source-output検証を実callerへ結ぶ。閉じたJob/process HANDLEを再照会して証拠を補わない。

新10件を一回の最終source runで0.7277483秒、fail0/error0/skip0。fake Win API/Job/process/creation/policy＋実exclusive小FileIO/fsync/3B raw gateであり、実Win ABI/exe/pipe/worker/native認証・容量合格ではない。通常modeのempty/exit0/creation/close・cached無native反復、観測中新active member/creation割込み/ledger割込みの昇格、output_limit停止、unknown read close、knownFalse core保持、同サイズraw改変、非boolの入口前拒否を確認した。

35 source/science pin前後不変・先行共通32pin不変・変更3file target safety・最終unique10／clean code-save35working-Git一致。先行transport13／旧suiteの実試験反復0、新production module0／名前30source・phase32要求・予定64Jobは未閉包。fresh source pin/runtime profile/policy/request/unusedroot未準備、旧pinを流用しない。

raw: `artifacts/preformal-git-pipe-normal-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 11072 | `649fc97eb552fc2f2628526d153d1f2ae6fb11129893ae20d639b0cdcfadf3d3` |
| focused.log | 2429 | `1a056c864742db011edb20abf968f0650455615b0a0282944b0aa3f379ea0ade` |
| code-save-checkpoint.json | 5545 | `abdb5b9b291e60a3cf4b8d2271f517646b64e21a41f5783ee9dac778c75c7ab0` |

helper PID49732／creation134358714991711789／token08b823749077c34b6543f3993491f21d51ea9e41e90656616ccaf008c1d10c26。exit0／CIM残存なし、原live/executionへ保持。全helper終了／critical ownerなし／native0／追加agent0。

## 次の保存単位

正常receipt publisherへ元transport/native return、core close前のJob観測、元executable/policy/source-output pin、全raw/post-close witnessを結ぶ。失敗receipt／recovery prefix／未回収ownerを区別し、archive raw readback後だけexact leaseへ進む。normal/critical/bootstrapを実actor-terminalへ保持して渡す経路、同期Peek／caller step wallと並行容量、限定caller-launcher／新exclusive profile/request/rootは未接続。create_nativeはroot/channel/Job前拒否を維持し、全7役whole.runを限定readerとして起動しない。

元Popen/Job/process/thread/extra handles/Python owner/stream/buffer/pending/inflight/partial archiveをIO前保持。不明Close/Delete／既存Unclosed／未回収／診断・IO・割込みをblind retryや通常Python終了へ落とさず後続Git-workerを拒否する。metadata/marker不在/root exit/EOF/worker kill-wait/途中capacity checkpointを回収True/lease/ackへ読み替えない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry・元wall/memory/output・cleanup30秒/poll0.25秒を維持。上限緩和/未測定rootへのreceipt移動/旧raw-root整理禁止、正常readback後の新inflight固定3fileとnew directoryだけ整理可能。正式gate=s4_acceptance_not_frozen/formal_permission=false/credit0/登録holdout観測未読・実ロード依存／業務異常子孫／正式5残件を維持。
