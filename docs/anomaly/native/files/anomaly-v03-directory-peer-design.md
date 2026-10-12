# S4-B2 private期間中のpeer権限取得

2026-09-14、基準8290039。[局所directory取得](anomaly-v03-directory-driver-design.md)の成功後に残る、
private rootを別handleで開く経路を限定して調べる。新規directory-peer-2026-09-14枠のattempt-1を最大1回。
前回のdirectory-driver枠とsourceは再利用しない。実装/fault試験・独立レビュー・clean source/監視固定後に実行する。

## 調べること

専用workerが新規rootをCreateDirectory2Wで取得し、root0x1600a7/share READ=1/private SD/非継承の原handleを保持する。
同じprocessの同じprimary tokenで4個のOPEN_EXISTINGを順に試す。これは別handleの取得試験であり、別processや独立tokenの競合試験ではない。
根拠のない「別actorを完全に再現した」という主張をしない。名前からのpeer openはこの新規fixtureの原root保持中だけに限定する。

| 順序 | 権限 | requested mask | 役割 |
| --- | --- | --- | --- |
| 1 | FILE_LIST_DIRECTORY | 0x120081 | 比較用の読取りcontrol。取得不可なら残りを打切る |
| 2 | FILE_ADD_FILE | 0x120082 | ファイル追加権限の取得結果 |
| 3 | FILE_ADD_SUBDIRECTORY | 0x120084 | サブdirectory追加権限の取得結果 |
| 4 | FILE_DELETE_CHILD | 0x1200c0 | 子の削除権限の取得結果 |

全maskにREAD_ATTRIBUTES/READ_CONTROL/SYNCHRONIZEを含め、同じobjectのID/SDとGrantedAccessを照合できるようにする。
peer share=READ|WRITE|DELETE=7は原handleの既取得権限との互換性を許す指定。原rootのshare READは変更しない。
CreateFileWのdisposition=OPEN_EXISTING=3、flags=BACKUP_SEMANTICS|OPEN_REPARSE_POINT=0x02200000、security attributes=NULL、template=NULL。
CREATE系、DELETE_ON_CLOSE、子作成/列挙、write、SD変更、rename、削除、marker操作は行わない。

API根拠: [CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)、
[File Access Rights Constants](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants)。
権限bitと実際にその権限を使う操作は分ける。全要求が拒否されても、子の内部open・外側parentの既取得権限・別token/移管経路を排除したとはしない。
取得が許可された権限も、子作成/削除が実行できたという観測にはしない。

## 所有と停止

PeerAcquisitionsと4個のTrackedOpenを原root取得後、最初のpeer open前にcallerへ保持する。
返却handleを各slotに保存してからNtQueryObjectと同handleのID/type/path/private SDを確認する。
peer pinは原rootのvolume/file ID/type/descriptorと比較し、peer自身のhandleも返却値に結び付ける。
各peerの既知handleは次のケース前にclose。全部完了してからprepare.jsonを保存し、原rootを再観測してclose/freeし、最後に祖先を閉じる。

CreateFileWの文書化されたINVALID_HANDLE_VALUE（Win64全1または-1）と、直後に得たerror5/32だけをknown denialとする。
この場合は新規作成をしないOPEN_EXISTINGの既知失敗で、返却された所有handleはない。TrackedOpen自体のunavailable履歴は書き換えず、
peer専用台帳のknown_no_handle_denialで区別する。正常な拒否後も次の独立ケースへ進めるが、同じ要求は再試行しない。
control拒否、0/NULL/異常値、他error、error取得失敗、返却/close不明では行列を打切る。
これはCreateDirectory2Wの作成失敗を無作用とする扱いには転用しない。

不明peerが残る場合、PeerDriverは基底driverのroot終了より先に停止し、原root/input descriptor/ancestorもworker終了まで保持する。
既知peerの検査失敗はpeerをcloseしてから原root/祖先を通常終了する。最初の例外objectと後発resource stopを維持する。
callbackのrun/finish再入を握り潰しても後続へ進まない。slot・ケース・所有unknownを再利用/再closeしない。

## tokenと資源の範囲

既存sinkのquery token slotで開始時primary token情報を読み、query handleを1回closeする。
primary type1、非昇格、medium integrity、SeBackup/SeRestoreが有効でないことを要求する。token/account/privilegeの作成・変更やimpersonationはしない。
user/token ID/modified ID/authentication ID/有効privilege等の開始情報を最大4096文字で保存する。
これは開始時のprofileであり、期間中の外部token変更の完全な監査や異なるtokenを使った試験ではない。

peer guardが増えるため新contextの観測点だけ最大96（基底driverの既定64は不変）とする。
40秒/256MiB private/384MiB working/空きRAM・disk各2GiBを維持し、外側監視は45秒/1秒周期/終了待ち5秒。
上限超過/MemoryError等は通常JSONの割当てを避け固定通知/exit80、不明所有はexit81、他失敗exit1、行列/保存/再確認/終了完了だけexit0。
prepare.jsonは16KiB、stdoutは64KiB、stdout+stderrは128KiB以内。常駐・繰返し監視・他process停止なし。
新規clean detached checkoutと固定source/監視/planの照合を済ませてから1回だけ実行し、結果によらず枠を閉じる。

## 解釈と次工程

matrix_completeは4件の観測と終了がそろった意味で、4件全部の拒否や隔離成立という意味ではない。
初期token・原handle保持・各request/error/GrantedAccess・同object照合・終了の根拠を証跡に結ぶ。
保存成功なら既知prepareだけをhash照合できる。sourceは失敗/close後に開き直し・列挙・hash/copy/deleteしない。
既存evidence bootstrapの信頼制約を維持し、isolation_certified/protected_commit_allowed/formal_permission/execution_authenticated=false。
取得できた権限があれば、次はそれを使用する具体操作と呼出し時の追加権限検査を新規fixtureで別途評価する。
取得が全て拒否されても外側parent・子内部open・handle移管・consumer共通観測期間は未解決。native publisher/正式B2/S4受入には進めない。
