# S4-B2 親共有とpath新規作成の限定比較

2026-09-15 JST、基準4e9bc81。[保持consumerの限定成功](results/anomaly-multiseed-v0.3-s4-b2-held-launch-2026-09-14.md)の次に、親を保持するだけで名前一覧への追加を防げるかを調べる。
新規namespace-create-2026-09-15 batchの最大1回。旧source・閉鎖済み枠は再利用しない。結果にかかわらず同じcaseへ戻らない。

## 比較対象

新規case directoryを2個、CreateDirectory2Wで単回取得し保持する。いずれもaccess0x1600a7、redirect拒否、非継承、既存private SD。
差分はshare READ|WRITE=3のcontrolとshare READ=1だけ。ACLを取得後に変更せず、保持元rootのID/SD/実accessを確認する。
各rootについて同一process/primary tokenから、既存PeerAcquisitionsの4要求を一度ずつ行う。
LIST control/ADD_FILE/ADD_SUBDIRECTORY/DELETE_CHILDのOPEN_EXISTING、share全許可7、非継承。成功は実権限/同ID/SDを確認してclose、既存openの既知5/32拒否は元部品の契約通り記録する。
peerに不明応答・未終了があれば、後続の新規file作成へ進まない。

次に、その保持root下のnew-empty.binをpath指定CreateFileW/CREATE_NEWで一度だけ作る。
子access0x120081/share7、非継承、OPEN_REPARSE_POINT、既存空file backendの明示SD。payload write/flush/delete/renameは行わない。
成功時は同handleのID/SD/実access、空file/links1/非delete-pendingを確認する。親ID/SDをpeer前後とchild確認後に照合する。
子とpeerは元root保持中にcloseする。両case rootを結果保存まで保持し、子終了確認→root→外側祖先の順で終了する。

親へのADD_FILE handleの取得拒否と、親のpathを経由した別file作成の成否を独立に記録する。
[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)の共有条件だけから親namespace全体の変更拒否を導かず、実際の新規作成応答で確認する。
root取得は[CreateDirectory2W](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createdirectory2w)の保持handleを使うが、childの作成は保持parentを直接指定するAPIではない。

## 失敗と保存

CREATE_NEWのINVALID_HANDLE_VALUEとWinError5/32はdeniedとして応答を記録するが、OPEN_EXISTINGの既知no-handle例外を作成操作へ流用しない。
作成失敗/応答喪失では既存TrackedOpenのunknown/unavailable状態を維持し、root/関連祖先を保持してworker終了へ進む。失敗sourceの存在確認・列挙・再open・hash/copy/deleteは禁止する。
この場合collection未完了/exit81、resourceなら80であり、拒否応答を局所実行全完了へ読み替えない。以降のcaseは開始しない。
成功fileは空のまま残す。parentの不変観測だけで全期間不変、名前一覧全体、既存mapping/祖先/ACL操作を証明したとは扱わない。
状態query故障も親保持側へ倒し、一次例外と後発resourceを維持する。再入はラッチし、close/freeを再試行しない。

NamespaceContextは既存HeldDriverの終了プロトコルを使い、reader位置へ2caseの観測matrixを接続する。生consumer bytesの返却機能はない。
元sinkはProfiledSinkのtoken記録とRetainedSinkの終了保留を組み合わせ、primary/非昇格medium、backup/restore privilege未使用を要求する。
同じworker/tokenでの比較であり、独立peer process/tokenによる干渉試験ではない。token生成・impersonation・AccessCheckは行わない。
両caseの観測完了後だけprivate-evidenceのprepare.jsonへ最大32KiBのmetadataを保存する。保存後のsource列挙・再読込を行わない。
worker reportにはmatrix/各case/各peer/子・root close/初期tokenを含め、isolationと受入flagsはfalse。

## 実行固定と上限

既存held launcherのHEAD/入力pin全体SHA/全py・ps1 inventory照合、module参照保持、stdout単回、80/81維持を再利用する。
launcherの変更は報告scopeを選べる引数だけで、既定動作は維持する。新規probeとsupervisorの出力先は今回batchに固定。
fake故障・独立レビュー・実装savepoint後に別clean detached checkoutへ固定し、入力codeのraw/Git blobを照合する。
候補側の既存CRLF差分は前回同様に正規化だけの一致を記録し、native raw bytesをpinへ固定する。実fixtureへはアクセスしない。
最大2 root/2 child作成/8 peer open、新規attempt1回。内部40秒/1024資源点、外側45秒/500ms観測・96点。
private256MiB/working384MiB、空きRAM/disk各2GiB、通常stdout320KiB/外側出力384KiB。超過時は対象workerだけを止め、5秒以内の終了確認を要求する。
前後の資源観測とOS build/bootを記録し、Windows Updateのengineering緩和は維持する。既存Python3.14.0、runtime/account/service追加なし。
起動前に仕様を固定し、native後はstdout/stderr/監視記録のみ照合する。保存証拠のhashはworker内読戻し報告として扱い、終了後に独立再openしたとは言わない。

結果に応じて、親共有だけで名前追加を防げないなら、この条件をisolation根拠へ明記して次の権限境界候補を絞る。
専用principal等の運用変更が必要なら、具体的なアクセス・運用負担・正式契約変更を判断材料にする。現時点で新accountは作らない。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completedを維持する。
