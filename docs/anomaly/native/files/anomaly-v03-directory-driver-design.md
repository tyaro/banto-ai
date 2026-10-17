# S4-B2 局所directory取得driver

2026-09-14、基準982c1318。[取得部品](anomaly-v03-directory-acquisition-design.md)を、独立した新規rootだけの試験へ接続する。
実装/fault試験・独立レビュー後のclean savepointと監視scriptを固定し、新規枠directory-driver-2026-09-14のattempt-1を最大1回実行する。
ユーザーの自走・savepoint作成許可の範囲。旧batch/失敗sourceは再開・再観測しない。native publisherや正式受入へ接続しない。

## 固定する範囲

| 対象 | 仕様 |
| --- | --- |
| runtime | 既存C:\Python314\python.exe、Windows x64、Python3.14.0 exact。追加installなし |
| source | 新規attempt-1/source-fixtureをCreateDirectory2Wの単一呼出しで取得。子・payload・markerを作らずrenameしない |
| evidence | siblingのprivate-evidence/prepare.jsonへ取得履歴を1回保存。最大16KiB、原handleを保持中にflush/readback/close |
| ancestors | private sinkが先に保持するdriveからattemptまでの全leaseをsourceのparentsとexact照合。最大16個、ID重複拒否 |
| source観測 | 原handleのID/実権限/SDを検証。evidence保存後に同じhandleを再観測し一致を要求 |
| 終了 | source CloseHandle→入力descriptor LocalFree→evidence/祖先の逆順close。各所有部品は再終了しても再closeしない |
| 不明所有 | source取得/close/input free、祖先SD取得/freeが不明なら祖先を保持し、専用workerの終了で打ち切る |

既存private sinkのbootstrapは旧CreateDirectoryW+openを使う。その既知のcreate/bind・owner/admin等の信頼制約を継承する。
このevidence領域を保護publisherの隔離根拠へ昇格しない。既存private sinkは変更しない。
既存APIのdescriptor返却はctypes.c_void_p cellだったため、取得部品では元cellを保持したままアドレスを検証する。
fake APIも同じ返却型に合わせ、前回の整数だけの模擬試験との差を修正した。

## 祖先の読取り

祖先の各retained handleについて元ID/type/pathをobserveし、所有者/group/DACL/mandatory labelのdescriptorを取得して再度IDをobserveする。
保護DACL/非継承ACEを要求する新規root専用security()は既存祖先へ適用しない。既存ACLの変更や追加権限の要求はない。
GetSecurityInfo(handle, SE_FILE_OBJECT=1, 0x17)の自己相対SDを最大8192 bytesで比較する。GetSecurityDescriptorControlで自己相対形式を要求する。
1回のSD出力cellをcaller保持し、成功が返った既知pointerだけLocalFreeを1回試す。応答不明なら再query/freeせずworker終了が必要。
複写例外を最初の例外として保持し、free中のMemoryError等を資源停止へ昇格する。bufferは成功したqueryごとに解放する。
元ID/SDの初回snapshotは最大16個。guardは取得前後・観測境界・保存前後で全祖先を比較する。
比較は時点間の差を検出するもので、ABA不在・同時snapshot・peerのADD/DELETE_CHILD不在を証明しない。
既存祖先への明示的path再openはprivate sink内に残る。新規sourceは同handleのobserveだけとし、失敗/衝突後・close後に開き直さない。

API根拠: [GetSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo)、
[GetSecurityDescriptorLength](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getsecuritydescriptorlength)。
上限はこの試験の制限でありWindows一般仕様の上限ではない。別threadによるSD変更との競合をAPI自体が解消するとの主張はしない。

## 記録・停止・資源

driver/contextは接続前からcallerが保持する。同期callbackの再入や不正な応答を最初の例外としてラッチする。
失敗時は最初の例外を維持し、後発resource stopを昇格する。通常報告は終了後のstdoutだけへ出し、最大64KiB。
resource stop後は通常snapshot/JSON組立てを避け、固定ASCII通知とexit80。固定通知自体の成功も無制限OOM下では保証しない。
通常失敗exit1、不明所有でworker終了が必要な場合exit81、正常終了exit0。報告値だけで終了を推定せず、監視側が実process終了を確認する。
driverは最大64資源点、40秒、private256MiB/working384MiB、空きRAM/disk各2GiBを上限/下限とする。
外側監視は開始前の空きRAM/diskを確認し、専用workerを1秒単位・45秒/private256MiB/working384MiBで制限する。
外側停止は作成したworkerのprocess objectだけを対象とする。終了を最大5秒で確認し、他processへ干渉しない。
stdout/stderr合計128KiB超も失敗。監視記録・出力は新規名だけで、上書きや削除をしない。
1秒間隔の観測は瞬間peak全体を保証しない。native DLL内の未観測割当ても含む完全なリーク不在を主張しない。

## 実行前と終了後

pure/faultと既存回帰を実行し、実装/入口/監視/設計を独立レビューする。source bytes/hashとclean exact HEADを固定する。
既存の無関係な親policy結果書の差分を保護するため、native用に小さなdetached checkoutを1個作る。
そこに試行planを保存し、全sourceと監視scriptが固定revisionのGit blobと一致したことを照合してから1回だけ開始する。
成功/失敗のどちらでも枠を閉じる。同条件の2回目・代替API・旧sourceの検査/再利用/cleanupはない。
成功なら既知のprepare.jsonと監視stdoutを照合できるが、sourceのclose後読取りや子inventory確認は追加しない。
取得成功は局所API/観測/保存/終了の結果に限る。子がないというpostclose検査やnamespace隔離の証拠にはしない。
全isolation/protected commit/native publication/formal permission/execution authenticated flagsはfalse、acceptance_status=not_completed。
次工程の親全保護・root private期間のpeer経路・handle移管・consumer整合性は依然未解決である。
