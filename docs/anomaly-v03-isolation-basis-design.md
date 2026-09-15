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

## 取得部品の実装状況

7f93322で[単一呼出し取得部品](anomaly-v03-directory-acquisition-design.md)を追加した。
[fake APIを含む221件pass、独立残件0](results/anomaly-multiseed-v0.3-s4-b2-directory-acquisition-2026-09-14.md)。実機試行の追加なし。
原handle先行記録、同handleのID/実権限/SD、単回close/free、返却不明時のdescriptor保持を扱う。
3a71934でcallerの祖先guard・保存・終了と[局所driver/監視](anomaly-v03-directory-driver-design.md)を接続した。
[240件pass、新規max1の実機取得pass/0.540秒](results/anomaly-multiseed-v0.3-s4-b2-directory-driver-2026-09-14.md)、独立残件0、worker終了確認、枠閉鎖。
上記は原handleでの取得/観測/保存/終了だけの結果。
13ad057で[同一token peer取得](anomaly-v03-directory-peer-design.md)を実装し、[259件passと実機4ケース](results/anomaly-multiseed-v0.3-s4-b2-directory-peer-2026-09-14.md)を確認した。
ADD_FILE/ADD_SUBDIRECTORYは共有違反、DELETE_CHILDは取得可。元rootのshare READだけで全変更用handleの取得は排除できない。
独立process/tokenと実際の子変更は未検証。次は子DELETE権限/DELETE共有、親DELETE_CHILD、path APIと保持parentを使う操作の違いを具体化する。
上記peer/外側parent/consumerの未解決条件は維持する。

## 2026-09-14 削除条件の限定確認

26bc403で[新規空ファイル4条件](anomaly-v03-delete-matrix-design.md)を実装し、[283件pass・実機完了](results/anomaly-multiseed-v0.3-s4-b2-delete-matrix-2026-09-14.md)を確認した。
子DELETE拒否でも親DELETE_CHILD許可・子share7ならDeleteFileW受理/保持childのDeletePending=true。
子share3ではWinError32、親と子の両権限拒否ではWinError5。各case親はshare READで保持していた。
この親の共有条件だけでは子削除を防げない。子のDELETE共有拒否の効果は保持中の局所結果で、公開後/close後まで一般化しない。
close後の名前消滅、保持parent handleの権限使用、独立process/token/競合は検証していない。
次はsealed-file保持と公開順序modelに、子handleの全期間保持・移管/closeの間隙・consumer共通観測期間を接続する。
max1枠は閉鎖しcaseを再利用しない。上記隔離条件とB2/S4未完了、全許可flags=falseは維持する。

## 2026-09-14 保持期間とconsumer model

1c03cfeの[保持期間仕様](anomaly-v03-retention-window-design.md)と[306件passの結果](results/anomaly-multiseed-v0.3-s4-b2-retention-window-2026-09-14.md)で、公開期間とconsumer全fileの共通期間を別々に追跡した。
同ID/bytesの再取得でも途中のclose/reopen欠落を消さず、他境界unresolvedのまま照合済みbytesを返さない。余分なslotを含む不明open/closeも完了/返却を止める。
marker sealerの既存DELETEと新reader/share1の衝突は双方向共有仕様からの予測で、追加実機の結果ではない。share5なら両立しても旧guardのclose後に削除拒否を維持できない。
次は元root/全sealed fileのborrow中に有界読取を完了し、照合したbytesだけを返す部品。既存native publisherの開始条件は変更しない。
親/祖先namespace・inventory・descriptor・保持者の権限行使/移管は別条件として未解決。test仮定によるcommon_interval_model_onlyは隔離認定や受入許可を与えない。
新規実機枠/fixture/checkoutを追加せず、旧caseへ操作なし。B2/S4未完了、全許可flags=falseを維持する。

## 2026-09-14 保持handle内のconsumer読取

8c35fceの[有界読取部品](anomaly-v03-held-consumer-design.md)と[331件passの結果](results/anomaly-multiseed-v0.3-s4-b2-held-consumer-2026-09-14.md)で、全sealed fileを保持したcontinuation中に同handleの実readを接続した。
全子のmetadata/実権限を先に照合し、各file単回read後に全子/元rootを再照合する。最後の子close/guard/上位停止確認まで成功しなければ取得候補を破棄する。
正常returnしたguardが残した停止と、journal snapshotの二次障害が一次例外を隠す問題を修正。独立P2計2件を是正し残件0。
actual bytesはprivate証拠にとどめ、consumer_payloadは常にisolation_unresolvedで拒否する。前回modelのtest仮定による返却switchを実adapterへ導入していない。
同じhandleと前後一致は全期間不変性/親・祖先・全inventoryの一貫性を証明しない。既存native publisherの開始条件は変更しない。
次は元root/祖先保持と子close不明時のworker終了を含む有界driverのfake故障確認。その後の新規限定native仕様は別途固定する。
今回新規実機0回、旧caseへ操作なし。B2/S4未完了、全許可flags=falseを維持する。

## 2026-09-14 保持consumerの準備・保存・終了driver

fe6f7a8の[接続仕様](anomaly-v03-held-driver-design.md)と[360件passの結果](results/anomaly-multiseed-v0.3-s4-b2-held-driver-2026-09-14.md)で、新規2fileのprepare barrierとconsumer、収集証拠保存、元root/祖先の終了をfake APIで接続した。
子close不明・writer release未確認では元root/祖先を保持し、root/祖先のclose不明でも上位を閉じない。状態query障害も保持側へ倒す。
sourceのbootstrapは既存private sink方式であり、単一呼出しdirectory取得部品の保証を合成しない。初期競合と既存内部割当の制約は継承する。
収集証拠のseal_payload.jsonは保存slot名にとどまり、publication journal工程を進めない。consumer生bytes返却は依然isolation_unresolved。
独立所見0件、新規実機0回。次は専用launcherと外側監視を固定・接続し、新規限定実機の条件を整える。
親/祖先/全inventoryの共通期間と独立token/競合、B2/S4受入は未完了。旧caseへ操作なし、全許可flags=falseを維持する。

## 2026-09-14 専用workerでの保持consumer限定確認

9cc926fの[専用worker仕様](anomaly-v03-held-launch-design.md)と[377件pass・実機結果](results/anomaly-multiseed-v0.3-s4-b2-held-launch-2026-09-14.md)で、新規2fileのprepare/保持中read/証拠保存/全closeを0.860秒で完了した。
worker exit0/終了確認、max1枠閉鎖。28 handle＋2 query token closed、consumer内のpath再openなし。周囲のprepare/sealer/evidence処理とは区別する。
input pin106 sourceと選抜65 sourceのunion134をnative raw/Git blobで照合し、候補側追加22 sourceの既存CRLFだけの差分を記録した。
専用worker化は独立peer/tokenによる干渉検証を意味せず、source rootの既存bootstrap/TOCTOU制約も解消しない。
生bytes返却・namespace共通期間は未解決。次は親保持中のpathによる新規file追加を別fixtureの有界仕様で検証する。
ADD_FILE handleの取得拒否だけで名前一覧が保護されたとは推定しない。今回のsource/枠は再利用せず、B2/S4未完了と全許可flags=falseを維持する。

## 2026-09-15 親共有とpath作成比較の取得段階停止

2ec193aの[比較仕様](anomaly-v03-namespace-create-design.md)と[397件pass・限定実機結果](results/anomaly-multiseed-v0.3-s4-b2-namespace-create-2026-09-15.md)を保存した。
share3の最初のroot作成がdirectory_create_failedとなり、peer/child/第2rootへ未到達。worker81/終了確認、失敗枠閉鎖。
WinError数値がreportにないため原因は未確定。share3の一般的制約、ACL原因、名前一覧の保護・非保護を推定しない。
次は親作成エラーの記録を改善し、新規の有界診断を先に固定する。旧source/枠へ戻らない。
生bytes返却・namespace共通期間・B2/S4受入は未解決、全許可flags=falseを維持する。

## 2026-09-15 share READ保持中でもpathによる新規名前追加は成立

674d119の[単独case仕様](anomaly-v03-namespace-readonly-design.md)と[401件pass・限定実機結果](results/anomaly-multiseed-v0.3-s4-b2-namespace-readonly-2026-09-15.md)で、親ADD_FILE/ADD_SUBDIRECTORY用handleは32で拒否された一方、path CREATE_NEWで空fileを追加できた。
元rootのID/SDを前後照合して保存まで保持、全既知handle close/worker exit0/0.770秒。同じworker/primary tokenの実例であり、独立peer/tokenの干渉試験ではない。
親share READ保持とADD権限open拒否だけをnamespace追加の隔離根拠にする経路は採用しない。親ID/SDの観測一致もinventory不変を示さない。
share3の作成は直前の新規診断で87となり、今回controlを省略した。share3対照比較や具体的不適合原因の確定は未完了。

次はpublisherが行う追加/renameと通常peerへ与えない権限を、取得前/保持中/公開後と外側親・process handle移管に分けて整理する。
同一SIDの通常tokenと同じDACLだけでは両actorの区別根拠にならず、restricted publisher tokenだけで通常token peerを隔離したことにもならない。
専用principalが必要となる場合はlocal account/隔離VM、資格情報・起動・consumerアクセスの運用差を具体化してからユーザー判断へ出す。現時点でaccount/service作成は行わない。
これまでの旧source/枠は再利用しない。生bytes返却・全期間・B2/S4受入は未解決、全許可flags=falseを維持する。

## 2026-09-15 公開側と通常peerの主体を分ける案

60ac6c4の[権限境界案](anomaly-v03-principal-boundary-design.md)と[保存結果](results/anomaly-multiseed-v0.3-s4-b2-principal-boundary-2026-09-15.md)を追加した。
専用標準local account P、現在userのordinary peer U、管理者側bootstrap B、consumer Rを分ける案。別SIDだけでなく、共通ACE、外側祖先、process/thread/token/移管、初期SD/code/資格情報の窓を含める。
同じuserへの許可を残したままrestricted tokenやAppContainer ACEを加えるだけの案には、通常peer排除の根拠が不足する。AppContainer一般の隔離機能を否定する結論ではない。
初回は新規P作成/U拒否を確認するharnessだけを設計し、起動/SDDL/IPC/複数process所有の実装前残件を明記した。
専用標準account BantoS4Publisherと C:\ProgramData\BantoAI-S4B2-principal-20260915 の追加案をユーザー判断へ出す。名前/場所は読取確認時には未存在だが、まだ作成していない。
独立P0〜P3所見0件。OS変更/native追加/新worker0、前回選抜72 source/13 artifacts不変。
この環境案への同意に、frozen/markerの正式契約変更やB2/S4受入を含めない。生bytes返却・全期間の未解決と全許可flags=falseを維持する。

## 2026-09-15 承認済みprincipal準備の管理者起動停止

ユーザーが環境準備を承認。e202677の[限定準備仕様](anomaly-v03-principal-setup-design.md)と[34件＋診断6項目pass/実機起動結果](results/anomaly-multiseed-v0.3-s4-b2-principal-setup-2026-09-15.md)を保存した。
最初からdisabledの標準account、BA所有/保護DACL/medium labelのroot、U/P readonly、祖先handle/linked U preflight、資格情報をB内memoryに限定する準備を実装した。
管理者起動max1はlaunch_failedで戻り、外側例外だけのため原因/開始/終了を確定できない。accountは対象SAM読取で未存在、rootはunknownを保持して再訪しない。
f8495edで将来の起動stage/内側native error記録を改善したが、閉鎖済みattemptを再起動せず、今回の原因の確定にも使わない。
次はOS設定を変更しない独立の昇格診断。環境準備の許可を再確認する必要はないが、Windowsの管理者確認を操作できる条件が必要。
P/U実process、namespace/共通保持期間、全publisher、frozen/markerの契約、正式B2/S4は未完了。準備実装やaccount方式への許可を隔離認定に読み替えず、全許可flags=falseを維持する。

## 2026-09-15 復帰後の昇格診断と新規準備b

[短い自己照会](results/anomaly-multiseed-v0.3-s4-b2-elevation-diagnostic-2026-09-15.md)は通常/管理者とも終了確認したが、[新規準備b](results/anomaly-multiseed-v0.3-s4-b2-principal-setup-b-2026-09-15.md)はrequest-launchで停止した。account不存在、旧/新rootともunknown・閉鎖を維持し、設定準備を成功としない。
WindowsPowerShellのエラー置換でnative番号が落ちることを実装/host ILから確認した。これは起動失敗原因とは別。[直接Shell診断](results/anomaly-multiseed-v0.3-s4-b2-shell-launch-diagnostic-2026-09-15.md)は15331文字の無害commandを用い、3ケースと通常Controlだけを確認した。
直前の管理者確認画面の表示状況をユーザーへ質問中で、新Run枠は未使用。環境方式の許可は継続する。全期間/全publisher/正式B2-S4は未完了、全許可flags=falseを維持する。

続報：ユーザーから画面表示の回答を得て、直接Shell診断の管理者Runを一度実行した。PID26600/exit40/4256ms、Handle・終了・解放成功。通常Controlと同じ15331文字の無害commandで当該形式の管理者起動を確認した。準備処理の以前の失敗原因は未確定、両rootのunknown/閉鎖と全許可flags=falseを維持する。次は準備Entryを呼ばない管理者側の公開DLL読込みだけを別の診断として具体化する。
