# caller-held append control planのreader経路への受渡し

2026-10-08 JST。code `3a910b596c079deabc1ebcfe2fedf7b3abbeee22` はoriginへpush済み。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## 保存した接続

外部descriptor `{path,expected_pin}` の新形式 `anomaly-v03-preformal-initial-reader-git-append-plan-v3` は、既存pipe raw allocationとcallerの `append_control_limits` を必須にする。完成・pending各7、計14固定control名のpositive int（bool拒否、各既存32KiB以内）をclosed schemaで確認。v1/v2のfieldsを拡張して旧pinへ読み替えない。同じ外部pin/revision/profile/policy/source/rootを元shared clock開始後に再読取りし、既存linked producer budgetとresolved copyをgenerate_and_readへ渡す。

generate_and_readはroot/profile/runtime IO前のplan copyを保持し、両supervisor前にcontrol/raw allocationを確認してParent.createへ渡す。Parentは同じcaller controlsをshared/source IO前にcopy。元request pin・exact64call inventory pin・revision・outer root identityに結んだclosed append context `{value,pin}` を、新reader entry形式 `anomaly-v03-preformal-reader-git-append-entry-v2` に置く。context自体も32KiB以内。defaultは既存5field entryと追加keywordなしの経路を維持。

ReaderGitWorkerはborrowed kernel/stdinとentryをchannel/clock IO前に保持・copy。新entryで借用pipe IOがない場合、context pin不一致の場合はChildChannel前に拒否。同じ元request/inventory/root identityのcontextを再確認し、WorkerGitActorへ渡す。actorは同じcheckpoint/root/revision/inventory pin/control maximaのArchiveAppendAdmissionを発行し、同じ原writer/verifierへbindする。後変更した入力dictへ追随しない。native資源はJSONへ入れず、stdinの所有権を移さない。

通常pipe receipt→原raw/archive full readback→exact leaseの既存順に、新append storage gateを結んだ。storage完成記録のatomic/ack/authはfalseのまま。原recovery partial rawは新archive frameの別量として扱う。全control publisherの上限強制、親identity将来失敗raw、atomic並行予約/global/memory/実coupled peakの接続は本単位では完成していない。ReaderGitParent.create_nativeはroot/channel/clock/Job前拒否を維持する。

新production module0、選択名前30source/各phase32要求・予定64Git Jobを維持。完全source/runtime閉包ではなく、最新clean revisionのfresh profile/private policy/request/unusedroot、実control-packet-raw容量と元owner保持限定launcherは未準備。同期Peek/caller step間のwall・停止も未実証。

## 新しい焦点11件

一回の最終source run、11件、fail0/error0/skip0、2.918329900014214秒。対象はv3と旧形式のclosed fields、外部pin改変の入口前拒否、元clock内再読取り、実generate callerのIO前copyとforward、invalid controlの両supervisor前拒否、ParentのIO前copyと64call context、Readerのchannel IO前copyと同じwriter/checkpointへのbind、借用pipe/context pin必須、foreign request/inventory/root/formal flag拒否、Parentのroot/clock前拒否、通常pipe receipt/raw/archive後のexact lease。参照fixtureはfake setup/helperのみを使い、旧test本体の実行/discovery重複登録はない。

46source/science pinはrun前後不変。先行append unitとの変更箇所以外の共通31pin不変、変更5production＋新testの6file safety所見0、最終unique11。clean code-save時の46working/Git blob一致とHEAD=originを確認。fake Win API/Job/creation/policy/memory/executableと小さい実FileIO/channel/archiveのprotocol gateであり、実Win ABI/exe/pipe/worker/native認証/容量合格ではない。旧焦点/native/profile再観測/追加agentは0。

専用raw root: `artifacts/preformal-reader-git-append-forwarding-20261008-prep/`。

| 保存物 | bytes / SHA-256 |
| --- | --- |
| focused.json | 14319 / 82782cc4861c5640aa0a143691a36f6a601a2d312c1c8f764de9910fbafcdb74 |
| focused.log | 2809 / 15560a18586772fc2fdf3b80644d771fd2c2ca890d590f596dd70fcbe2dfdfdb |
| focused-components-final.json | 1054 / 58714a5a3985e4483eb3fdf90087deb8eb77cd9b61859921247989a5eff4f982 |
| code-save-checkpoint.json | 7853 / 8398a2286d1c61c505409a299484009fa4dee7e419418597c7e9af30a36cde2c |

helper PID29872/creation134358820718151482/tokenf1a18a2bd306713043ae29822f8c68deee73ce42066c9448d4a6b087eaabb60eはlive/execution原rawへ保存しexit0/CIM残存なし。PIDだけで他processと同一扱いしない。新code CI37689828218（実fullHEAD3a910b596c079deabc1ebcfe2fedf7b3abbeee22/各minor3556予定）はin_progress。先行37685672435/37686697633は3.12success・3.14in_progress、run終端未確認。完成CI保存やrawを反復しない。

## 次の保存単位

全control publisherが同じrequest/root/保持control maximaへ参加する境界を、小さく対象sourceから確認する。request/binding/stop/inventory/manifest/proof/ackとpending、親identity任意失敗raw、原partialと新frame growthの保持順・将来枠を別量で計上。snapshotやcontext pinをatomic予約/native許可にしない。新entry/contextの実保存bytesも後続coupled計算に含め、上限を緩めず、未測定rootへreceiptを移さず、旧raw/rootを整理しない。

unknown Close/Delete/Unclosed/未回収/診断・IO・割込みでは元Popen/Job/process/thread/extra handles/Python owner/stream/buffer/pending/inflight/partial archiveを保全し、blind retry・原Python終了・後続Git/workerを拒否する。bootstrap/0-job/途中成功prefix/未登録owner/poison archive、metadata/root exit/EOF/worker kill-wait/途中capacity checkpointをlease/ackへ読み替えない。archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を保持する。
