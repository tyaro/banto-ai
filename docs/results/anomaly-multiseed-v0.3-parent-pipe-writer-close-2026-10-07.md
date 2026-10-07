# v0.3 parent pipe writer close／同じ原nativeへの接続（2026-10-07）

保存追補は2026-10-08 JST。既存のexclusive raw rootと記録名は維持する。

code `c78dbfe34827ae7a9bb7cb979da422cf0ceef1d1`、先行clean文書HEAD `960e4404d43c35cfe42137356b41e6434fcdfa61` からの小さいopt-in単位。実pipe作成・read handle/sink close・追加IO解除・receipt/witness・元root admission・実worker callerは未接続。`ReaderGitParent.create_native` のroot/channel/Job前拒否を維持する。

## 保存した境界

- `NativePipeWriter` はraw HANDLEを保持し、fd変換やdestructorによる自動closeをしない。SpawnIOOwnerは元writer handleをentry時に固定し、read/write/core/inheritedとのaliasを拒否する。raw writerは元DuplicateHandleへ直接渡す。stdinと追加IOなしの既定stream経路は従来のfd経路を使う。
- `close_parent_writers` は元kernel、checkpoint、writer、handleと元returnをIO前に保持し、実CloseHandleの非zero returnを観測した位置からだけ名前別eventを保存する。既知False、不明return、native/clock IO・割込みは元UnreapedJob/stream/handle/元例外へlatchし、次writer／同writerのcloseを増やさない。最初のclose後のcheckpoint失敗でも元成功eventと未attempt writerを保持する。
- 正常結果のcache copyはnative closeを反復しない。stream.closed/released宣言やlegacy fd wrapperからraw closeを許可しない。結果はio_released=false／parent_ack_authorized=false／execution_authenticated=falseを保持する。
- `GitOutputOwner.from_spawn` は同じ原SpawnIOOwner.native、read handles、exact sink streamを結ぶ。異なるsinkでは元nativeへ双方の資源を保持して拒否。parent write closeと観測EOFが揃ってもread handle/sink/core/lease/ackは保持する。

parent write側とchildが継承したwrite側の扱いは [Microsoftのredirected pipe例](https://learn.microsoft.com/en-us/windows/win32/procthread/creating-a-child-process-with-redirected-input-and-output)、APIの参照先は [CloseHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle)。本単位のAPI returnはstubであり、実Win ABI/pipe/Job/native認証/容量合格ではない。

## 焦点と保存

新11件を一回の最終source run、0.0108042秒、fail0/error0/skip0。raw writer duplicate、close/cache、knownFalse/unknown第二close、close後clock割込み、metadata／handle改変拒否、原sink/core接続とforeign sink保全、keeper core保持、close→broken-pipe EOFの保持を確認。先行fixtureはfake setupだけ参照し、旧suiteを実行・discoveryへ重複登録しない。

35 source/science pin前後不変（30production+参照fixture2+新test+science2）、先行変更production2file以外32pin不変、変更3file target safety、unique11 discovery、clean code-save35working/Git一致。新production module0で名前30source/各phase32要求/予定64Jobを維持。完全runtime閉包ではなく、fresh raw pin/profile/policy/request/unusedrootは未準備。旧HEAD/pinを読み替えない。旧read13/spawn13/他完成suite/native反復0、新native0、追加agent0。

raw: `artifacts/preformal-parent-pipe-writer-close-20261007-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 11002 | `a765b2d117ffc0e36b42b40139272f2000a3c2aab7c0309a316ff67c01080e09` |
| focused.log | 2627 | `4ffab8c9eb06efba6d802536aa033f962b89d19869f2f7d68639ddacc752b732` |
| code-save-checkpoint.json | 580 | `123b20422b2f177af7a1868907b24985ede6ddf5bf5f2e9883d42d52c02ae09b` |

helper30208/creation134358581522043999/token1b6fd5e2cf255050cadb5f29e9b520fbcd717d1e3ff82aedeefdc4e3a592906cはexit0/CIM残存なし。全helper終了・critical ownerなし。

## 次の単位

元read handleとsinkのnamed close、元EOF/readback/native returnをcached Job/root終了・creationへ結び、追加IO解除とreceipt/post-close verifierへ渡す。原kernel/stream/handle/buffer/pending/inflight/partial archiveをIO前に保持し、unknown Close/Delete・既存Unclosed・未回収・IO/割込みでは原Python ownerを保持して後続Git/worker拒否。実CreatePipe／exclusive空sink／exact callの元root残余bytes/entries／output_limit停止を実callerへ接続する。同期Peekのwall/停止保証も未実証のままで、接続・拒否/停止保全とfresh exclusive準備が完成するまでnativeを開始しない。

archive512KiB、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和・未測定rootへのreceipt移動・旧raw/root整理なし。先行全repository safety30秒timeoutは未確認保全。正式gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読、正式5残件/採択/最終受入は未完了。
