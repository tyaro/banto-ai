# Git追加IO ownerの保持（2026-10-07）

初版code `66d31eee72d25eda0546739053f43cf47f58d976` と入力検証前snapshot補強 `ffbdc2f8c65dc9f155375330c9c194eb0b62b962` はpush済み。owned_git_job、child_git_keeper、新testの3fileを変更。新module追加0でreaderの名前30source／予定64Jobを維持する。新source pin/profile/requestは未準備で、古いものを新codeへ読み替えない。

## 保持した境界

`GitOutputOwner` は元UnreapedJob/UnclosedHandles、追加stdout/stderr read handle、元BoundedGitSpool/streamをIO前に保持する。read handleはcore/inherited handleと重複させず、既存inherited最大3の枠へ読み替えない。入力dictは拒否時もcopyで保持し、caller後変更でhandle/sinkを落とさない。重複bindでは先行IO ownerも保持して拒否する。

read前に元handle/sink/要求量をpendingへ保存し、元shared checkpointを通す。観測blockは検証やconsumer IOの前に保持し、過大read・pending中の再read・IO/割込みを元native例外として再送出する。原例外にIO ownerが残るため、既存terminal/ChildGitKeeperのPython保持対象から普通のIO例外へ脱落させない。無効なnative入力も専用例外へIO入力を保持する。

ChildGitKeeperは追加IO ownerを早期にcacheし、Job停止・元root終了・creation確認まで行う。その後はcore close/completionへ進まず、元core/inheritedと追加IOを保持する。Job exit0、released/EOF宣言、marker削除でも保持を解除しない。再照合ではcached reapを用い、追加Terminate/wait/creationを反復しない。unknown core closeの場合もnative retryをしない。

実pipe作成/read/close、consumerへ原blockを渡す経路、追加IOの回収確認・解除adapterは未接続である。現在の境界は明示的に未回収の保持のみを行い、lease/raw確認/親ackを許可しない。限定 `create_native` も拒否を維持する。通常の追加IOなし経路は互換を保つ。

## 焦点と保存

初版新10件は0.0013628秒、fail0/error0/skip0。その後、拒否したcaller dictのalias保持riskを修正し、新1件だけ0.0002447秒でpass。無効native metadataの場合もsnapshotを検証前へ移す補強後、新1件だけ0.0002021秒でpass。先行11再実行0、distinct12であり、最終sourceの単一12success runではない。

各runの33source/science pinは前後不変。変更間のowned_git_job/test以外31pinは全3run一致。変更3file safety、final module unique12 discoveryを確認。初版66d31eeのcode-saveはHEAD=origin/clean・33working/Git一致。補強ffbdc2fの33working/Git一致時は文書draft3件だけdirtyであり、その状態をcode-save-v2へ明記した。文書保存後にclean HEADで再照合する。fake native owner/Kernel/reap/creation/checkpointによるprotocol gateで、実Win ABI/実Job/実pipe/native認証/容量合格ではない。

rawは `artifacts/preformal-git-output-owner-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 10220 | `d111b66decbe00233b8e47db564a05e16bf030366a7640cff0357d6e52d7cd3a` |
| focused.log | 2051 | `8e57f8600a61d96dfd48ee8486b471c4db73968db18b22cccd03b781b26b8efe` |
| added-one.json | 10218 | `9bbe02322a7114613e5142219980bc799e0001edf2afe1c1cd0ce1b2c40f139d` |
| added-one.log | 316 | `f819b4969df83b5c6112531291a77b26daa60c6bc6ed24b5606f729113ec0447` |
| added-two.json | 10219 | `c3f9ded7c415d6942b7a8a5af2c5d621af1e029e996682d0035fdad5bbd2c493` |
| added-two.log | 320 | `3a4b850bf04b93d6160229d293b8087cce2aeb7c3e44ebe041bc0f953b5c7f46` |
| focused-components-final.json | 5724 | `f376876ee0abf95d055ac57057ca074c7d15c8d8dae9fa46e7f34147be7cec7f` |
| focused-components-v2.json | 5808 | `467ebf35668a1a161ba6a9d0532c5209d0fc13c4bf384082be50f7d12f6590cf` |
| code-save-checkpoint.json | 405 | `e9377155d3a2317f925b9b9cf6759cacda1f0299a9850c1e35d59e8761dd9747` |
| code-save-v2.json | 637 | `5cf987baf6fd03941c6ebb9f6432213e727f2665785c6491e5d61c05424974dc` |

helper5772/creation134358528206917327/tokenafcb0336591830bb0e4d18442a6b569d1d509fd0a28b1e4a972eb6e51213f200、追加46488/134358530168792068/token08d6dbbefecb63c4c17578a39843abc2f655bb9127ac64a8dfedd1685caf273fはexit0/CIM残存なし。PID単独で過去helperと同一扱いしない。全helper終了・critical ownerなし・新native0・追加agent0。

追加34396/creation134358534884190548/token9c0df9644202bf2559d2909843ba1aa61ebcb359cbb53cb5d7a027f70583c5cbもexit0/CIM残存なし。

## 次の接続

元private Jobのspawn/stdio cleanupへ追加pipe/read handle/sinkの保持を渡し、実read adapterをpendingの要求量へ結ぶ。原blockをbounded spoolへ渡す結果とreadbackを照合後だけpendingを進める。停止時は元Job終了確認、元read handleのEOF/close、sink/file/原rawの確認を追加IO解除へ結ぶ。unknown closeや診断・marker IO失敗は元owner/stream/pendingを保持し、blind retryやPython終了へ落とさない。

実read/close witnessをreceipt/post-close/raw verifierへ結び、元rootの残余bytes/entries、検知byteと失敗rawを既存枠内に収める。metadataだけで解除しない。これが完成してから限定caller/launcherと最終clean HEADのfresh profile/policy/request/rootをexclusive準備する。archive512KiB、outer1MiB/32entry/depth2/reserve128KiB、全体321MiB/672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。

先行spool12、他の完成済み焦点/native/CI保存を反復しない。全repository safetyの先行30秒timeoutは未確認として保全。正式gate s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読、正式5残件は保持。
