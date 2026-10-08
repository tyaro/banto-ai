# v0.3 子publication IO観測欠落の親fence拒否（2026-10-08）

## 保存した拒否境界

Code `e3004745c83962b73ed21cf8415385a1328df4e4`。append controls付きParentChannel/ReaderGitParentは、bound ack/proof/rawの整合性とTrue proof verdictだけでは子localの原publication close/rename ownerを観測できない。今回、その観測transportが未接続の間はTrue候補をFalseへ固定する。default追加gateなしのfile-directed形式・明示verdict経路は互換を維持する。

元Popen/controller/endpoint/publication gate/bindingとack/proofの保持slotをIO前に固定する。返った原rawはJSON/pin検証前、verdictは元return位置からbool検証前に保持する。ackの原rawはJSON/pin validation前に保存し、改変rawでも失わない。request/inventory pin/root identity/clock/root/revision/binding pin/worker identityをbounded32KiB canonical contextとして保持する。旧request/entry/ack/proofへfieldを追加して旧pinを読み替えない。新disk publisher/fileは0。

子close/rename ownerの独立観測はNoneのままで、parent_ack_authorized/execution_authenticated/atomic_reservationはfalse。False拒否は最初の原previewへ固定し、cached経路はproof/creation/clock/raw/file/close/reapを再観測しない。foreign Popen/gate/contextやunknown ack/proof IOは原raw/owner/例外を保持し後続拒否。worker exit0/closed/released/success flags/marker不在/完成rawで子IOを回収済みにしない。

実child observerを観測・認証するtransport/launcherは未実装であり、この拒否はpositive ackやnative回収を発行する部品ではない。既存root/channel/clock/Job前のReaderGitParent.create_native拒否は維持する。

## 新焦点一回

新10件を一回の最終source run 18.456017900025472秒、fail0/error0/skip0。44source/science pin前後不変、先行publication retention共通41pin不変、変更3file safety0、unique10、clean code-save44working/Git一致。先行14distinct/旧suite/native/profile再観測/追加agent0。新production module0、選択30source/phase32要求/予定64Git Jobは未閉包。

確認対象は、bound完成ack/proof＋True stub verdictの拒否、ack不在、子の実ack rename完了後の不明返値、exit/closed/success metadata、cached/direct channelの無再観測、foreign Popen恒久保持、callback内inventory pin改変、invalid ackの原changed raw、default経路の互換。

子の不明renameケースは原exclusive小FileIOのwrite/fsync/close後、実no-replace renameが完了した位置で試験KIを注入した。子gateは原pending/stream/raw/errorを保持し、親は完成ackが存在してもFalse。proof verdictは明示True stubであり有効native proofを発行した試験ではない。fake creation/budget/profile/private policy/Popen＋実小FileIO/root/channelのprotocol gate、実worker/Job/pipe/exe起動0、実Win ABI/native認証/全経路wall/容量合格ではない。

## 原raw・終了・保存後照合

専用 `artifacts/preformal-child-publication-fence-denial-20261008-prep/` は512KiB/32file/reserve128KiBを維持。focused13704B/b680d4a2acb241d5c6e7ee3cebef7beb67c5b090be9412fbc82cff0aabf7adb6、log2710B/fea2aea8e0504d7671b38d57558607d2f40c779b9c02d95a092fe0b97c930809、components1225B/d9ac5ec4a5200b0cd63fb2e38f337b61e27ee37219a7d9e67fa090eab62ca813、code-save7719B/71b1de54685c9764b26f192a1d70467c8338076eaf1b763f5d33f253445aabe0。

元focus `30348/creation134358907433726580/token186647828121d6229b39f9f0505598353ea34a904352c051748eb5e38e0edc4c`、CI download `26208/creation134358909390667601/tokenffbeb6cb8a9307a7d0e219f6f25a62651fcd90ff248a06a7e2405886704aa8ae`、verification `37392/creation134358910094096159/token62b6c1577c46a406ead6d39ec150a6a8e81ff949700f3e8069e547d91ce257d4` は元live/executionを保持・exit0/CIM残存なし。全helper終了/critical ownerなし。PIDだけで過去processと同一扱いしない。docpush後44working-Git/science/docs3/focus2raw/新CI14pin/CLI両pin/HEAD=origin/clean/元3helper終了を専用post-save-checkpoint.jsonへ保存する。

## 次の小単位と限界

child local原close/rename/raw witnessを親の原process/creation/control transportに結び、欠落/unknown IOを成功flagsで補わず拒否する実観測transport/原owner保持launcherは未接続。全writer同request/root予約、親identity任意将来失敗raw/diagnostic、原partial rawと新archive frame growthの別計上、entry/context実保存bytes、atomic並行予約/global/memory/coupled peakは未完成。snapshot/cached raw/sidecar/context pinをatomic予約/native許可へ読み替えない。

fresh latest clean source/runtime/profile/private policy/request/unusedroot/実control-packet-raw容量/exclusive準備は未完成。native入口を開かず全7役whole.runを限定readerとして起動しない。旧HEAD/profile/pin/14sourceやproducer pre26/post24を親111/111へ流用しない。元clock/上限/stopと旧raw/root/失敗保全を維持。

formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。実ロード依存/業務異常子孫・正式5残件/正式採択/最終受入は未完了。
