# 固定control公開の原stream・返値・readback保全gate

2026-10-08 JST。code `11c7a9929d1d13a755756b8d2e4ac47e8c1520ea` はoriginへpush済み。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## 小さい保存単位

既存worker_git_archiveへ `ControlPublicationAdmission`、既存channel._writeへ明示opt-in keywordを追加した。新production module0、選択名前30source/各phase32要求・予定64Git Jobを維持するが、source/runtime閉包ではない。追加gateなしの既存_write本文・metadata形式はそのまま。

gateは既存の原endpoint/request/request pin/inventory pin/outer root identity/callerの14完成-pending control maxima/元checkpoint/保持Python ownerを保存・copy。checkpoint/file IO前に原ownerへsidecarで保持し、後のrebindは先行gateと拒否gateを両方保持して原gateにも原例外をlatchする。constructorの無効入力も元例外にgateを保持する。native例外や元Job回収を生成する機能ではない。

固定completed名と同じchannel rootだけに、canonical dictの実bytesが完成・pendingの両caller maximaに入る場合だけ進む。原request/inventory pin・manifest inventory link・binding/stop/ack request linkを照合する。semantic proof/lease/ack判定は既存の実publisher/readerが別途行うもので、この保存gateはmetadataからackを許可しない。

元shared checkpointの後に保持plan/原endpoint/request/owner/clockの同一性を確認し、実_directory_snapshot（outer32entry/depth2/元identity）と全control現サイズを計上する。snapshot後のstatで将来枠を割り引かず、14枠全最大bytes・14entry＋reserve128KiB/診断2entryを保守的に加える。現在保存済み分も二重計上した拒否を維持する。同期観測による拒否と保存後照合であり、並行atomic予約/global/memory/親identity将来失敗rawの保証ではない。

exclusive空pending FileIOを返った位置から保持し、原fd/path identity・countを記録。原payloadを保持したままexact write返値→flush/fsync/fstat→全staging raw/pin→同じ残余照合→原Python FileIO.close返値/owned fd観測→closed raw→上書き禁止renameの原返値→published raw/同じfile identity→同じ残余を確認する。close返値は実return位置で観測した場合だけ記録し、stream.closedや完全なdisk rawだけでunknown closeを解決しない。FileIO.closeはPython fd所有streamの観測で、Win sink HANDLEのCloseHandle返値宣言ではない。

partial write/close/renameの非None返値、sync/clock/IO・割込み、原raw改変、公開後の別writer増加では元error/raw/stream/fd/pending/完成名も保持し、全後続公開・reopen/rewrite/reclose/rename反復を拒否する。元errorにもgateを保持し、伝播で原Python所有物を失わない。保存結果のatomic/native_owner_recovered/parent_ack_authorized/execution_authenticatedはfalse。

本unitは既存endpointへの明示gate。初回request bootstrap、Reader/Parent/Actorへの全publisher gate発行・forward、原native keeper/terminalとの未解決IO linkは未接続。初回requestには既存endpointがまだないため、このconstructorで保護済みとはしない。ReaderGitParent.create_nativeはroot/channel/clock/Job前拒否のまま。最新clean revisionのfresh source/runtime/profile/private policy/request/unusedroot/元owner保持限定launcher、実control-packet-raw coupled容量と同期Peek/caller間wall・停止は未完成または未実証。

## 新14distinctの焦点

最初の12件は一回0.7593420000048354秒pass。仕様照合後、rename非None返値拒否の新1件だけ0.10887240001466125秒pass。rebind拒否が原gateを再armしない補強の新1件だけ0.04519820003770292秒pass。先行13/旧suite反復0、最終source単一14success runには読み替えない。

対象は正常raw/stream/返値/同一性、実raw capと固定pathの入口前拒否、既存失敗raw・entryと将来14枠/診断reserve、callback後原endpointの保持、partial write/同期割込み、closed metadataを伴うunknown close、close後raw改変、rename後外部writer増加、owner rebind/元error停止、非None rename返値。fake channel identity/owner＋小さい実FileIO/fsync/rootの部品gateで、実Job/pipe/workerを起動しない。実Win ABI/exe/native認証/全経路wall・容量合格ではない。

各35source/science pin前後不変、変更archive/test以外33pinは全3component一致。先行append-forwarding共通32pin不変、変更3file safety所見0、最終unique14、clean code-save35working/Git blob一致。native/profile再観測/追加agent/完成焦点反復は0。

専用raw root: `artifacts/preformal-control-publication-admission-20261008-prep/`。

| 保存物 | bytes / SHA-256 |
| --- | --- |
| focused.json / focused.log | 10946/aba9367b2e0ffa40ee6d5372ef9ca60fcbd49bb99f70457f2a492e773c3a4211 / 3115/770f21da9d33c0467c34249edcf35f9d7e77bd498de08f9bcedd421152ffa21e |
| focused-v2.json / log | 10945/7e6d2ca0e47964ea6cb84f473f8842f9215222b75bd77f8016d86f2a79497381 / 374/8aa6192e631a6a9a7079dfe7eb5702391436add8d05bcb49374221a5a0502cf9 |
| focused-v3.json / log | 10945/4011843e0de8a03ca6aa9faec1f9762eed48de26084c607c1f2e1433a2e102e7 / 370/a5cb56b127e1f01170b8adab816b036309686e59274c672ccb7f7e8a6e901a4e |
| focused-components-final.json | 1533/f19cf86baf8ee309f86b5e4b746635a70ec42a4083c5403cfa84939bc005073a |
| code-save-checkpoint.json | 6696/706fab4e3d2c43f4c4593aa32bad02b8edee2fa77c07fd2b000c06e2f1daac4c |

原helper47464/creation134358830588993259/tokenb33ae0cea4781077e0fd9fb32b2b543d6578d4057d32bcf770d5dcc7f4619e36、48432/134358831866538792/tokenfa0c3d1510464eb732e9d5fcbec821d5ed70a6be64f6c297f40931a80a2220ff、9408/134358832753607013/tokenc2399749f63839e80a8acc5d5a538aae49e564f32a35016932126b5860ba33ddは各live/execution原rawへ保存しexit0/CIM残存なし。PIDだけで過去processと同一扱いしない。

## 次と上限

inventory/manifest/proof/ackの実publisherへ、同じ原request/inventory/control contextと原owner/keeperを保持してgateを渡す小さい境界が次。親binding/stopと初回request bootstrap、全publisher/親将来失敗rawの同request/root予約は別単位で接続する。gateのpending stream/errorをcached keeper completionから隠さず、元Pythonを終了で落とさない。旧width/model/profile/source bytesを新cap/request/proof/容量合格にしない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。unknown Close/Delete/既存Unclosed/未回収/diagnostic・IO・割込みでは原Popen/Job/process/thread/extra handles/Python owner/stream/buffer/pending/inflight/partial archiveを保全し、blind retry/原Python終了/後続Git-workerを拒否する。bootstrap/0-job/途中成功prefix/未登録owner/poison archive、EOF/root exit/metadata/worker kill-wait/途中capacity checkpointを回収True/lease/ackにしない。未測定rootへreceiptを移さず、旧raw/rootを整理せず、正常readback済みの新actor固定inflight3file/new directoryだけが整理対象。
