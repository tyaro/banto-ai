# v0.3 Git pipe close／keeper／receipt proof link（2026-10-08）

最新code `5906eed8833d753052194699a355b2fe7f0832ae`、初版code `a1ca9f0b0cea4454335e520b4196ceeb29422b0f`。先行clean文書HEAD `b7a8cd397359bf0177e11c19b5ebb7d7390fb83a` からの小さいopt-in単位。実transport／実executorのpipe receipt publisher／root admission／worker callerは未接続、`ReaderGitParent.create_native` のroot/channel/Job前拒否を維持する。

## 保存した接続

- `ChildGitKeeper.bind_io_close` は同じ原GitPipeClose、output owner、native例外、keeperを明示的に結ぶ。拒否したadapterも診断前に元keeperへ保持し、元例外を再送出する。bindなしではclose event、EOF、released宣言があってもcore closeへ進まない。
- 原close部品が元rawを再読取りし、元writer/readのnative return位置、FileIO close/fd/file identity/raw pin、EOF、元Job/root終了・creation、core/inherited handlesをexact linkへ結ぶ。2番目raw callback失敗でも1番目の元returnを保持。追加IOにlate error/pendingがあればcached close eventから解除しない。
- 原adapter/raw確認後だけkeeperが元coreのnamed closeへ進む。既知Falseのcore closeは既存規則でその残ったhandleだけretryし、native reap／read close／sink closeを反復しない。不明core closeは元UnclosedHandles／未attempt handles／完成済みIO eventを保持して拒否する。marker削除やadapterのmetadata宣言で解除しない。
- 新failed recovery形式 `anomaly-v03-child-git-pipe-recovery-observation-v1` に `io_closed` を必須追加する。元core/IO handlesのalias、creation、exit/empty accounting、named API/return、FileIO fd、全stdout/stderr raw pinを厳密に照合する。failure_raw_verified／lease_completed／parent_ack_authorized／execution_authenticated／formal_permissionはfalseを保持する。
- public receipt verifierは新sidecar形式 `anomaly-v03-preformal-owned-git-pipe-quiescence-v1` を厳密に受け、元receipt/policy/全raw／従来のcore post-close linkを検証してから追加IO linkを検証する。従来receipt JSON、通常のquiescence/recovery形式、追加IOなしのkeeper経路を維持する。
- compact proofのrecovery readerは新形式を元rawへ照合し、failed statusを維持する。既存exact keeper／ordered lease／double raw read／停止prefixの規則を使う。新形式の実archive/worker/ack経路や全budget接続をこの焦点の実証へ読み替えない。

これはfake Win API／Job／process／creation／policyによるprotocol gate。sinkには実exclusive FileIO／fsync／41Bの非空rawと空stderrを使った。receipt verifierの新形式はfake executorが保存した原receiptとpolicyへ接続したが、実exe／Win ABI／pipe／worker／native認証／全経路容量合格ではない。

## 焦点と保存

初版新12件を一回、0.1145777秒、fail0/error0/skip0。explicit opt-in、元IO/core close、cache/no reap反復、bindなし／release metadata／foreign adapter拒否、close後raw改変、unknown core close保全、既知False core retry、raw/schema/alias/return/creation改変拒否、2番目callback失敗時の1番目raw保持、元receipt/policyと追加IO link、compact recovery failed statusを確認。

その後、close後late error/pendingからcached eventでcoreを解除するriskを拒否し、新1件だけ0.0123141秒でpass。cached終了観測後のcore closeも元kernelへ固定し、spawn bindingの後変更に追随しない新1件だけ0.0117701秒でpass。先行13件反復0、distinct14／最終unique14であり、最終source単一14success runへ読み替えない。各38 source/science pin前後不変、変更production2file/test以外35pinは全3run一致、先行close gateの変更production3file以外33pin不変。変更4file target safety、初版clean code-save38working-Git一致。補強code-save-v2は文書draft3件のみdirtyを明記し38working-Git一致、doc push後にclean保存を確認する。

新production module0、選択30source／各phase32要求／予定64Jobの名前は維持。追加IO eventで保存packetのbytesが増えるためfresh source/runtime/profile/policy/request/root inventoryと容量再確認が必要で、古いprofile／容量モデル／pinを読み替えない。既存archive/frame/raw/control/lease上限を緩和しない。全helper終了／critical ownerなし／新native0／追加agent0、旧suite反復0。

raw: `artifacts/preformal-git-pipe-close-link-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 11969 | `ff27f97f5160d324138f6ce66d8679d04eaf0d83e18e55267de4c36064733cf4` |
| focused.log | 2617 | `0dfa247d95e8230fbdc0cf6aa4b7a90e123dc8258dc0abff3109a8893bb2a1f2` |
| supplement.json | 11979 | `1bb5b920e37ae81253161d68c5b03931d244d3aaa576882085079e728e518da2` |
| supplement.log | 323 | `6d3b46376616c37253c71a8526e81231c72ed1096082046eca806f69a2802efe` |
| focused-components-final.json | 6139 | `279c2dda4e51a349e7a17acfd0f73c02c4272e7955ad981457e722e43a17f163` |
| code-save-checkpoint.json | 385 | `2a7769ed240078cbd7a9de1c27ff7a0d4a85fdd10e5b9e955beb3c47bc01be69` |
| kernel-supplement.json | 11986 | `7eb096d861feb715e931d8cc7b2b4a861388f44eb015e92628452b23dfd68316` |
| kernel-supplement.log | 327 | `8ceaef3c6489c52cd634d15d3844bdffd46b7d3d1ee3cdf30d1e7971a2c2944c` |
| focused-components-v2.json | 6343 | `5bd938cc0406d5590da1110ed03eacbc914302a67d84246ee489584c55ae0f85` |
| code-save-checkpoint-v2.json | 527 | `45e1c40ffb4f5a70383f1c5970c8d30eb6d7fb1a5a6f12f57462a91a7cf92b41` |

helper45408/creation134358611881048726/tokene109fbc99048be713b550143698bdcb5a7c4b91315850888bd94b5bbc86ebb62、補強46524/creation134358612886436014/tokend136e8faca09c3781809a395ad48d1159bc43671504c50ce73e9de21a3dff89d、kernel補強42156/creation134358619438515179/tokenc183e9a307e1fb58a41d7576d27c20f8c6ae789834ec1a8832674a0e0aa7fd3fはexit0/CIM残存なし。PIDだけで過去processと同一扱いしない。

## 次の単位

実transportを原spawn/output/reader/close/keeperへ渡す入口を小さく接続する。pipe作成・exclusive空sinkをIO前保持し、exact callの元shared root残余bytes/entriesと失敗raw保存枠をspoolへ結ぶ。output_limit時は元Jobを停止し、未回収／unknown Close/Delete／既存Unclosed／IO・割込みでは原Popen/Job/process/thread/extra handle/Python owner/stream/pending/inflight/partial archiveを保持して後続Git/workerを拒否する。実executorのpipe witness publisherをoriginal return位置から作り、新形式をdeclared metadataで生成しない。

同期Peekのwall／停止保証は未実証。限定caller／元owner保持launcher、最終clean HEADのfresh source/runtime/profile/policy/request/unusedroot、原control/packet/rawのcoupled容量とexclusive準備が完成するまでnative入口を開かない。全7役whole.runを限定reader確認として起動しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理なし。正常readback済み新inflight固定3fileと新directoryだけ整理可能。先行全repository safety30秒timeoutは未確認保全・再試行なし。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。実ロード依存／業務異常子孫／正式5残件／正式採択／最終受入は未完了。
