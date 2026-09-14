# S4-B2 隔離の成立条件と次の検証境界

2026-09-14、基準1f70faa。検討結果であり、方式採用・実機試行開始・S4受入の決定ではない。
[残存権限model](anomaly-v03-publication-order-model-design.md)のunresolvedを実際の根拠で解消するため、
生成時の取得競合、別actorの既取得権限、consumerの観測を分けて扱う。

## 結論と選ぶ調査経路

次に具体化するのは、CreateDirectory2Wによる「新規directoryの作成と最初のhandle取得を1回の呼出しで行う」限定部品。
現行CreateDirectoryW→別openの間隙を減らす候補として選ぶ。これをnamespace全体の隔離成立とは扱わない。
このPCには既に必要なSDK宣言とAPI exportがあるため、この候補の調査に新account・service・runtimeの導入は不要。
API存在だけでは呼出し成功・競合拒否・frozen下の子作成/rename成功を証明しない。

別actorがrootのADD/DELETE_CHILD等を取得できる期間が残るなら、前回modelのwrite拒否を維持する。
新APIへ置換するだけでassume_isolated_for_testを実隔離の証拠へ昇格させない。
既知peer0、UUID名、非公開path、最終inventoryの一致、同じ結果の反復は、権限を持つpeerが存在しない根拠にしない。

## 現行実装から確定した不足

`src/banto_ai/_anomaly_v03_windows.py::_dacl`のprivateはuser/SYSTEM/Administratorsへfull allowを与える。
`tests/fixtures/anomaly_v03_private_sink.py::connect`はprivate rootをCreateDirectoryWで作った後、別openで保持する。
directory rename用rootの初回shareはREAD+WRITE、DELETE共有なし。rootを開いたことは、別actorのADD/DELETE_CHILD取得禁止を示さない。

通常のDACL判定は要求権限とtokenのSID等に依存する。したがって同じ判定材料を持つpublisherとpeerを、
同じallow ACEだけで区別できるという根拠はない。これは下記の公式説明と現行DACLからの設計上の推論である。
[File security and access rights](https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights)。
restricted tokenは制限を追加する仕組みであり、それを作っただけで同一userの通常tokenからpublisher専用権限を隔離したことにはならない。
[Restricted Tokens](https://learn.microsoft.com/en-us/windows/win32/secauthz/restricted-tokens)。

既存B1のowner/adminによる意図的な権限変更、privileged writer、writable mapping等の非目標は維持する。
一方、B2で既に問題にしている通常のADD/DELETE_CHILDと取得済みhandleを「同じuserだから対象外」と取り除かない。
作成前から外側parentを持つpeer、作成後にrootを開こうとするpeer、publisherから漏れたhandleは別の経路である。
非継承設定だけでは明示的なhandle移管やprocessへのアクセスまで証明しない。未知の移管経路があれば隔離はunresolved。

## API資料とローカル確認

[CreateDirectory2W](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createdirectory2w)は
Windows 11 24H2以降を対象とし、HANDLE返却、要求権限・共有mode・security attributesを指定する。
DISALLOW_PATH_REDIRECTS=1はpathのreparse/symlinkによるredirectを拒否するためのflagとして説明されている。
この説明から、既存ancestorの同一性保持や外側parentの既取得権限が不要になったとは推論しない。

公式ページには不整合がある。syntaxは5引数、例は6引数。戻り値の本文は失敗0だが、例はINVALID_HANDLE_VALUEを検査する。
ローカルSDK10.0.26100.0のum/fileapi.hと[Microsoftのheader](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/fileapi.h)はともに5引数のHANDLE宣言。
そのため6引数の例を転写せず、Win64のLPCWSTR/DWORD/DWORD/enum32/LPSECURITY_ATTRIBUTESの5引数を設計基準にする。
返却値0/INVALID_HANDLE_VALUEはどちらも成功にしない。失敗表現の曖昧さを実ディレクトリ作成なしとは読み替えず、再試行・再open・削除へ進まない。
正しい宣言であることと、意図した権限/共有条件で作成できることは別の確認事項である。

2026-09-14に既存C:\Python314\python.exe/Win64でkernel32のexport有無だけ照会し、CreateDirectory2W存在を確認した。
関数本体は呼んでいない。DLL追加・SDK更新・root作成・native publisherは実行していない。
SDK原fileのhash、該当宣言とexport照会結果をignoredの今回記録へ保存する。

NtCreateFileも作成とhandle返却を行い、保持parentからの相対名を指定できる。
ただし今回は並行した別adapterや失敗後fallbackを作らない。
[NtCreateFile](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntcreatefile)。

## 検証すべき取得経路

| 経路 | 必要な根拠 | それだけでは不足する観測 |
| --- | --- | --- |
| root作成前の外側parent | 外側の元ID/SD/実権限と保持の寿命。既取得DELETE_CHILD等でrootを削除・差替えできるかの別評価 | rootの新規作成成功、外側parentのDELETE共有なしだけ |
| root作成直後 | 作成と取得を分けず、原handleを最初に所有台帳へ保存。要求/実権限・ID・type・SD・非継承を照合 | SDK/export有無、作成APIの非zero返却だけ |
| private期間中のroot | ADD_FILE、ADD_SUBDIRECTORY、DELETE_CHILDの各権限をpeerが取得・使用できない根拠 | share READ/0という設定名、rootのDELETE open拒否だけ |
| 子の作成・rename | publisherの操作に必要な内部openが成立し、peerには同じ経路を許さないこと | publisherが既取得ADDを持っていること、過去のprivate rename成功だけ |
| marker writer | 空の新規markerを共有なし・非継承で取得し、他の有効writer/移管がない根拠。元IDとwriter寿命を追跡 | writer1本を自分の台帳で確認したことだけ |
| 固定後・全handle解放後 | 新規mutation拒否に加え、それ以前から使える権限を排除・隔離した根拠 | 新しく開いたreaderで全項目が一致したことだけ |

親の共有制限を子全体のmutexとはみなさない。特にDELETE_CHILDをDELETE bitの共有検査と同一視しない。
CreateDirectory2Wの共有説明だけから、上表の権限別・操作別の拒否結果を補完しない。
固定DACLを作成時に渡す案も、publisherの要求権限が得られ、子作成が通るとは未確認。
後からprivateへ緩めて成功させる処理は、事前取得の窓を復活させるので、この隔離候補の成功条件に含めない。

## consumerが一貫した観測を返すための条件

1. markerの有界readを1回の試行として扱い、空・部分・共有違反・応答不明を成功へ昇格させない。
2. 期待marker、inventory、ID、bytes/SDのpinを試行開始前に固定し、途中で新しいpinへ差替えない。
3. root/各payload/markerの元handleと生存期間を追跡し、別pathの再openを同一観測へ混ぜない。
4. 最終照合を単に2回行うだけでは、その間の変更やABAを排除できない。共通の変更不能期間、または同等の一貫性根拠を必要とする。
5. 読み手へ返すpayload bytesは、照合した同じ有界bytesに結び付ける。照合後のpath再読取りを代用しない。
6. 隔離が未解決なら4つの一致flagが揃ってもsnapshot_matchesまで。将来のnamespace不変性を約束しない。

上記は必要条件の設計であり、実consumer/同時性検証/共有違反の待機処理は未実装。
consumerの正しい時点観測を、publisherのunknownを消す根拠にも使わない。

## 次に実装する部品の範囲

新規directory取得部品をtests/fixturesへ分離し、既存private sink/6工程/productionへは接続しない。
固定する候補要求はroot 0x1600a7、share READ=1、redirect拒否=1、非NULLの既存private SD、非継承。
private SDを選ぶのは現行との取得挙動比較のためであり、この部品の成功で隔離を認定しない。
DLL symbolの解決・ABIと全引数準備・所有slot予約を作成前に終え、返却handleを検査より先にslotへ格納する。
返却前/記録前の割込みは所有unknownとしてworker終了が必要。記録後の検査失敗は記録したhandleのcloseを1回だけ試す。
失敗時は最初の例外を保持し、後発resource stopを昇格する。取得/closeの返却喪失後の再試行・別API・path再open・清掃は不可。

最初にfake backendで、0/-1、衝突、検査失敗、実権限違い、close応答喪失、資源停止、再入を確認し、独立レビューする。
その後の新規限定実機仕様は別途固定する。今回は実機枠を開かず、旧失敗root・旧batchへ操作しない。
将来の局所取得試験に成功しても、上表のpeer経路・外側parent・consumer整合が未確認ならnative publisherは開始しない。

この経路で隔離条件が成立しなければ、専用principalでpublisher/peerを分ける案を、権限・運用負担・正式契約変更とともに判断対象へ出す。
専用principalだけでも生成前からの祖先権限やhandle移管、別account運用を自動解決しない。現時点で追加account等を作る判断は不要。
formal_permission/execution_authenticated/protected_commit_allowed=false、acceptance_status=not_completedを維持する。
