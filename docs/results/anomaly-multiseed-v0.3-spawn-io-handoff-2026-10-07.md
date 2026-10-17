# v0.3 spawn／stdio cleanupの追加IO保持（2026-10-07）

code `1d9d70a20aba3a96646f5a0e1e2ff1a2391cb20c`、先行clean文書HEAD `20778a03c766d890562bb6b9564f868817350a68` からの小さいopt-in単位。新production module0、名前30source/各phase32要求/予定64Git Jobを維持。実worker callerからのspawn_io受渡し・pipe作成・実close/readback witness・元root admissionは未接続で、`ReaderGitParent.create_native` のroot/channel/Job前拒否を維持する。

## 原ownerと追加IO

`SpawnIOOwner` はread2handle、sink2stream、write2streamの元入力を保持し、exact dictは全てcopyしてから検証する。別read2本を既存inherited最大3へ読み替えない。検証失敗も追加IO付きの元UnreapedJobへ保持し、mappingの後変更で原sink/write/read handleを落とさない。

opt-in `_spawn_cli(..., spawn_io=...)` はkernel/stdin/stdout/stderrをimport/environment/Job/stdio/native IO前に保持する。入力write stream不一致・再armを入口で拒否。Job/ProcessInformation/inherited snapshot/pending duplicate/attribute bufferを元holderへ保持し、core/inheritedとread handleのaliasはprocess作成とcleanup closeより前に拒否する。

正常spawnは従来のtupleを返し、元core/追加IOはcaller-held holderに残す。正常stdio duplicate closeの元eventを保持し、確認済みduplicateをactive extra handleへ再登録しない。body/knownFalse cleanupではopt-in原coreをlegacy partial reap/closeへ落とさず、原例外へ保持する。Delete／不明stdio Closeでは元core/attribute buffer/失敗・未attempt duplicate/追加IOを同じnative例外へ保持。`_new_job` が別のUnclosedHandlesを持つ場合も、その原例外と追加IOを相互に保持する。追加IOなしの既定経路は従来innerへ渡し、tuple/cleanup動作を維持する。

ChildGitKeeperは元spawn IO ownerをledger IO前にcacheし、原Job/root empty/creationを確認した後もcore close/completionを拒否する。cached native観測を反復せず、marker除去やreleased宣言でも解除しない。追加IOの実close/recovery proof/lease/ackは本単位では許可しない。

## 焦点と保存

新13件を一回の最終source run、0.0143406秒、fail0/error0/skip0。success tuple/原core保持、Delete／unknown Close、knownFalse、body／pre-Job失敗、別原native例外、duplicate alias、invalid mapping snapshot、再arm、keeper cache、invalid descriptor／write stream不一致を確認。

Win API/Job/process/creation/IO streamsはstub。実Win ABI/実pipe/実worker/native認証/容量合格ではない。先行fixtureはfake setupのみ参照し、旧9件を実行・新module discoveryへ重複登録しない。旧read13/IO owner12/spool12/他の完成suite/native反復0、新native0、追加agent0。

34 source/science pinが試験前後不変（30production、参照fixtureと新test、science2）。先行read gateの変更production2file以外31pinも不変、変更3fileのtarget safety pass、module unique13 discovery、clean code-save34 working/Git blob一致。fresh profile/policy/request/unusedrootは未準備で、旧HEAD/pinを読み替えない。

raw: `artifacts/preformal-spawn-io-handoff-20261007-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 10659 | `9c0f49be235ca3ef5ce321afbc369d28cb1eb15a74b7eda40c5a9a554eb314b1` |
| focused.log | 2710 | `24fae512f3357ea33fe4b9ec34b9c443dba7cba29d855795c8f6b4d543a5d477` |
| code-save-checkpoint.json | 574 | `2555d3aba6d0773fd25d28de79745619891ae747e6dc52c67c175942e13acf03` |

helper41500/creation134358568373857387/tokenb17c97ff72ca8170ceb602a27eae7776b69d03cd87d1d484c66ec77e22468abfはexit0/CIM残存なし。全helper終了・critical ownerなし。

## 次の単位

原parent write streamのcloseからread EOFへ進む順序と、元native return/不明close/原stream・handle保持を実transportへ結ぶ。元ChildGitKeeper.cached Job終了/creation、GitPipeReaderの原EOF/readback、read handle/sink/fileのnamed close/raw witnessを追加IO解除とreceipt/post-close verifierへ渡す。metadata/root exit/marker不在だけで解除せず、unknown Close/Delete/既存Unclosed/未回収/IO・割込みでは原Python ownerを保持して後続Git/worker拒否。実callerへexclusive空sink、exact callの元root残余bytes/entries、output_limit停止を渡す。

接続・拒否/停止保全とfresh exclusive準備完成前にnativeを開始しない。archive512KiB、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和・未測定rootへのreceipt移動・旧raw/root整理はしない。先行全repository safety30秒timeoutは未確認保全。正式gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読、正式5残件/採択/最終受入は未完了。
