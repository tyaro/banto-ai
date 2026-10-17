# v0.3 bounded Git pipe transport／元stop-close owner接続（2026-10-08）

code `690af4900da6fc198ca7f389db2a61fe1374f602`。clean文書HEAD `ee4b20dc1dc32016e0393365ffd0c6cd3c2dda70`からの小さいopt-in単位。

## 接続した単位

- `GitPipeTransport`は元admission/bootstrap、kernel/stdin/child、外部policy/repository/clock/stopを検証・copy・policy IO前に保持。同じrevision/private Job policyとexact callからargvを導出し、元shared checkpoint／caller started_atの10秒枠を使う。追加clock/samplerを作らない。元exclusive sink→CreatePipe→同じSpawnIOOwner／suspended spawn→parent writer close→同じbounded readerを接続し、元returnをpost IO前に保持する。
- `step`は最大4096／保存残余／枠内sentinelの元readerへ渡し、全raw readback後だけ進む。stop/10秒/output_limit/nonzero exitでは元ChildGitKeeperをledger/Terminate/wait前に保持して原Job停止・empty/root exit/creationへ結ぶ。API/clock/IO割込みも原例外と元buffer/pending/raw/secondary ownerを保持して停止へ渡す。未確認reapをclose_readyへ読み替えず、失敗後のread/close/restartとstop再呼出しのnative反復を拒否する。
- 明示closeは同じ元GitPipeClose／admission／keeperへbindし、named read/FileIO close、元raw、core closeとstrict pipe recoveryを照合する。core close成功後のkeeper freezeはmetadataだけで解除せず、元completion/closed_handles/initial_handles／IO linkと全rawを再照合してclosed sink容量checkpointへ結ぶ。cached closeはnative/read/reapを反復しない。

本unitは一つのcallを停止・回収して観測を保存するtransport部品。ChildGitKeeperはno-new-work latchとfailed recovery形式を維持し、返すresultのlease_completed／parent_ack_authorized／execution_authenticatedはfalse。正常64callの継続／通常成功receipt publisherを完成したと宣言しない。正常call終端とfailed terminalの区別・lease継続は実workerへの接続前に別単位で固定する。元stdinはcaller所有として保持し、本transportからcloseしない。

fake Win API/Job/process/creation/policyと実exclusive小FileIO/fsync/3B rawのprotocol gate。実Win ABI/exe/pipe/worker/native認証／全経路wall・容量合格ではない。同期Peekのblock可能性とcaller駆動step間のwall／停止保証は未実証。実receipt publisher／actor-worker-terminal受渡し／限定caller-launcher／parallel reservation・coupled容量は未接続。ReaderGitParent.create_nativeはroot/channel/Job前拒否を維持。

## 原失敗と焦点

初回12件は4pass/1fail/7error、0.2015818秒。fake policy fixtureのempty environmentが既存spawn検証でJob作成前に拒否された原結果を保全し、fixtureだけ訂正して8失敗件のみ再確認した。8件は7pass/1error、0.3960072秒。残る1件で成功core close後のkeeper freezeをclosed-sink checkpointが未回収として拒否する実接続不一致を検出し、元completion/named close/raw linkへ修正、その1件だけ0.1480644秒pass。さらにcompletionのhandlesを元named closeへ固定し、改変拒否の新1件だけ0.1621684秒pass。pass済み11件・旧suiteの再実行0。

13 distinct／最終unique13。最終source単一13success runへ読み替えない。各36 source/science pin前後不変、変更production/test以外34pinは全4component一致、先行close/admissionとの共通34pin不変。変更2file target safety／clean code-save36working-Git一致。新production module0、名前30source／各phase32要求／予定64Jobは完全runtime閉包ではなくfresh source pin/profile/policy/request/unusedroot未準備。

raw: `artifacts/preformal-git-pipe-transport-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 11263 | `8e2cb1be7146e1d03726a9816f93970f84ec65e6368a38899e887afed784f450` |
| focused.log | 27462 | `25b55bd2c1ca69503454972c1081327ee537e06ed187539f50c3387b35ded750` |
| focused-v2.json | 11260 | `05a20db53c0d84f947cf776ca0b8f2308f2fdcb9d7d6d1e695a1eec549fad904` |
| focused-v2.log | 4711 | `3649905910a9db8c8bd29a512e3a208e378292647b38e261be90575ae550666f` |
| focused-v3.json | 11259 | `8af43c5d6504e481383ceafe22f47c6e0ec5e3deaead7c170db898938198a265` |
| focused-v3.log | 314 | `05b6dbacaf708bcf1f25a71856cb178df3e85b3d135bba7a43513d7ff11fb35b` |
| focused-v4.json | 11262 | `00efb30e9d5737dbffd85ca7988cd65a2a3738b397c202ecb6fb796b00157ba5` |
| focused-v4.log | 306 | `56490b049e252ecc12d66f12e7e894c7825ac28c57cf5937f2c9627d86307fad` |
| focused-components-final.json | 2658 | `2b24e095adee9a3795e2772b713c329179c8943a8e474c5e1697eebdad4f9163` |
| code-save-checkpoint.json | 5535 | `0f623f75fa607ff6f30f12457589a4a63e2290fa4fd5b2f7e31d1641dd30f0b1` |

元helperのcreation/tokenは各live/executionへ保持、PID単独で同一扱いしない。
- initial: PID44536／creation134358706403412148／tokenaeea0afe7a56703d4dad1c706c83e774a35b9d43b09a3d4a82118bd05825af05。failed／CIM残存なし。
- fixture: PID43636／creation134358706694649744／token5035da9aef26e5ae76ca9d5dfd1f96ea9e617dedcb310dbb5221842a8c9caf98。failed／CIM残存なし。
- completed_close: PID45808／creation134358707112618222／token3dab85218f951b695ebd27d53583904458d7c9dd61b5b3c154bf151d7b5c4f96。passed／CIM残存なし。
- original_handles: PID42264／creation134358707479777221／token1018b913062f172908538c6e7c127e785193c4af7c04e0c77b5f2e3183246f24。passed／CIM残存なし。

全helper終了／critical ownerなし／新native0／追加agent0。正式gate=s4_acceptance_not_frozen、formal_permission=false、credit0、登録holdout観測未読を維持。

## 次の単位

新transportの原return／全raw／post-close observationからpipe receipt publisherへ結び、通常成功callをno-new-work terminalへ落とさない範囲とfailed/recovery prefixを区別する。元critical owner／bootstrap／追加IOを実actor/terminal catch/keeperへ渡す経路も実worker前に固定する。unknown Close/Delete／既存Unclosed／未回収／診断・IO・割込みでは原Python ownerとPopen/Job/process/thread/extra handles/streams/buffers/pending/inflight/partial archiveを保持し、blind retry／後続Git-workerを拒否する。

実source/runtime inventory/profile／policy/request/unusedroot、元control-packet-raw容量／並行予約とcaller駆動wall、限定caller/元owner保持launcherのexclusive準備前にnative入口を開かない。全7役whole.runを限定readerとして起動しない。旧HEAD/profile/pin/14sourceやproducer pre26/post24を親111/111へ流用しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理なし。正常readback後の新inflight固定3fileと新directoryだけ整理可能。

未保存CI37660790390（full30d38f4485040d649fcdc7c052c06f3fa6ea642b／各minor3468予定）は開始時3.14success/3.12in_progress・run未終端。新CI37666095841（本full690af4900da6fc198ca7f389db2a61fe1374f602／3481予定）はin_progress。各終端を実fullHEAD/workflow/run/attempt/jobsへ固定して一度保存、doc-only新CI追跡なし。完成CI/部品焦点を反復しない。
