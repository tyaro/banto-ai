# S4-B2 公開処理と通常peerの権限境界案

2026-09-15 JST、基準1185287。方式選択用の設計。account作成・設定変更・native開始・正式契約変更は未実施。
[親share READ下でもpath追加成功](results/anomaly-multiseed-v0.3-s4-b2-namespace-readonly-2026-09-15.md)を受け、通常peerが取得前から変更権限を持たない条件を具体化する。

## 推奨する次の一歩と判断対象

このPCに検証専用の標準local account **BantoS4Publisher** を1個用意し、公開側Pと現在の通常user側Uを異なるuser SIDに分ける案を推奨する。
これは検証環境の候補であり、別SIDであることだけを隔離成立の根拠にしない。共通group ACE、外側親、process/thread/token、取得済みhandleも検査する。
候補rootは **C:\ProgramData\BantoAI-S4B2-principal-20260915**。現在userのworktree/source/旧fixtureを新accountへ開放しない。
UTC2026-09-14T16:09:00Zの読取確認では候補account/rootは存在せず、C:\ProgramDataと既存C:\Python314\python.exeは存在した。作成時には再確認が必要。

判断してほしい範囲は「このPCに専用標準accountと新規検証rootを設け、その方式のbootstrap・限定試験を実装する」こと。
管理者承認と検証用資格情報の扱いが必要になる。Windows設定へ永続的な追加があるため、通常のrepository編集から分けて判断対象とする。
既存userのパスワードを会話・ソース・ログへ入力する方式は採用しない。新accountの資格情報もWindows側の対話/保護された入力経路で扱い、実行引数や成果物に保存しない。
初回は常駐service・定期task・新Python・VM・ネットワーク共有を追加しない。試験専用accountの有効化、資格情報/ログオン、終了後無効化を管理者側の限定手順へまとめる。
無効化だけで既存token/process/handleを失効できたとは扱わず、開始した全processの終了と所有台帳を別途確認する。
既存account/同名rootが見つかった場合は流用・ACL上書き・削除をせず停止する。

## 方式の比較

| 案 | この問題への評価 | 運用差 |
| --- | --- | --- |
| 同一user＋親share | 追加/DELETE_CHILDを排除できない実例があり、この根拠だけの採用はしない | 変更は少ないが不足を解消しない |
| 同一userのrestricted publisher | 通常SID側とrestricting SID側の両判定が必要。publisher制限だけでは通常peerの許可を取り消さない | token生成だけでは今回の境界にならない [資料1](https://learn.microsoft.com/en-us/windows/win32/secauthz/restricted-tokens) |
| AppContainer/Package ACE追加 | user/group側とAppContainer側の積集合。共通user/groupへwrite許可を残したままPackage ACEを追加するだけでは通常peer排除の根拠にならない | AppContainer固有の保護を否定する結論ではないが、この案の成立は未確認 [資料2](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer) |
| 同じaccountで別ログオンSID | logon SIDをACLのtrusteeにできるため別の調査候補。通常user SIDの共通allowやowner権限を区別する必要がある | 新ログオンと資格情報/セッション寿命の管理が必要。今回は既存user資格情報を扱う案を選ばない [資料3](https://learn.microsoft.com/en-us/windows/win32/secauthz/how-dacls-control-access-to-an-object) |
| 専用標準local account | Pだけに作成権限を与え、Uの通常tokenを明示的な試験対象にできる。推奨する次の限定検証 | accountと保護root追加、管理者による準備・起動管理が必要 |
| 別VM内で専用account | ホストへの検証用account追加を避ける代替。VM内でもP/Uの権限分離は必要 | OS/VM digest・準備・disk/RAMの追加負担。VMを作るだけで同一user問題は解決しない |

資料1〜3と既存ACLからの設計上の推論を含む。AppContainer等を追加実行して拒否を観測した結果ではない。

## 主体と信頼範囲

| 主体 | 役割と検査 |
| --- | --- |
| B: bootstrap/監視 | ユーザーが承認した管理者側の準備・起動・終了担当。Pの資格情報/高権限handleをU側の監視processへ渡さない |
| P: publisher | 専用標準accountの単回worker。非昇格medium、想定group/privilegeだけ。別の通常processをこのaccountで動かす構成にしない |
| U: ordinary peer | 現在の非昇格user。これまで問題にしたADD/DELETE_CHILD/子の通常変更を、対象外にせず独立processから試す |
| R: consumer | Uに読み取りだけを許可する経路。将来の独立restricted readerではU側とrestricting SID側の許可を両方検査する |

PとUは実TokenUserのSIDで区別し、名前/UUID/PIDだけを根拠にしない。初期user/group/deny-only属性/logon SID/整合性/有効privilegeを記録する。
SYSTEM/管理者による意図的変更、ownerの意図的DACL変更、privileged writer、writable mapping等の既存非目標は拡張しない。
ownerの暗黙READ_CONTROL/WRITE_DACを直接のADD_FILE/DELETE_CHILDとは混同しない。Uを新sourceのownerにしない案だが、実owner確認前にその効果を主張しない。
[owner判定](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/4f1bbcbb-814a-4c70-a11e-2a5b8779a6f9)。
P以外のwriter/handle移管がないことはaccount名だけでは証明できず、取得経路・起動規則・所有台帳の残件である。

## オブジェクトごとの必要権限と寿命

以下は権限要求の設計表。実SDDL/要求maskは次のadapter仕様で固定し、現行のprivate/frozen verifierを黙って置換しない。
P/U/SYSTEM/Administratorsの実SID、保護DACL、owner、mandatory labelを照合し、Users/Authenticated Users/Everyone等への意図しない変更許可を残さない。
fileのDELETEと親のDELETE_CHILDは代替経路になり得るため、Uへの両方の許可を排除する。[削除の権限](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-deletefilew)。

| 対象・期間 | P/Bに必要な操作 | U/Rに許す操作 | 失ってはいけない根拠 |
| --- | --- | --- | --- |
| 外側祖先・保護された検証root、作成前から終了まで | Bが新rootを保護状態で作成し、必要な親を保持。Pは専用配下への作成に限定 | 必要な読取/traverseだけ。ADD/DELETE_CHILD/DELETE/WRITE_DAC/WRITE_OWNERは許可しない | 既存祖先の権限/既取得handleと新rootの境界。親IDだけの一致では足りない |
| 固定したcode/runtime、P起動前から終了まで | Bが新規codeコピーとhashを固定、Pはread/execute | 必要ならreadだけ | UがPとして実行されるcode/DLL/config/環境/TEMPを差し替えられないこと。source hashだけで全runtime closureを認定しない |
| attempt/root、private準備中 | Pが子作成、名前変更用親権限、SD読取/設定に必要な権限を保持 | 初回toy試験ではLIST/read属性/READ_CONTROL controlだけ。namespace変更は禁止 | 作成時からUの変更許可を与えない。後からACLを閉じるだけの窓を作らない |
| payload writer、書込み中 | PがCREATE_NEW/write/flush、非継承handleを所有 | 初回は空file読取controlだけ。write/append/DELETE/WRITE_DAC等は禁止 | 原ID・実access・write/flush応答と単回close、他writer/移管の不在 |
| payload/stage sealer・rename | Pが必要なWRITE_DACとsource DELETE、destination側の名前操作。現在の要求実績はroot0x1600a7/stage0x1700a1/file sealer0x160081 | 内容readのみ | frozen変更は既取得権限を失効させない。子closeとrename用handle寿命を追跡 |
| marker writer/rename | 採用した方式ごとのwrite/flush/DELETE/親追加権限 | 完了前の存在だけで成功判定しない | 完全bytesを見たconsumerとproducerの不明応答を区別。専用principalだけでmarker方式は確定しない |
| 公開後のroot/payload/marker | 信頼したPの後続変更停止と全handle終了を確認。最終SDの条件は別の契約判断 | 必要なread/traverseのみ | 全inventoryの共通期間、B/P停止、既取得権限・外側祖先を含める |
| evidence/IPC | B/Pだけが既知の出力先へ単回・有界保存 | Uへ必要な結果metadataだけ | reportの自己申告でtoken/実行者を認証しない。IPC対象・process開始・code pinと対応させる |

CreateFileで取得した権限、標準権限、DACL/MICは別の検査事項。[file security](https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights)、[file access constants](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants)。

## processと起動経路も同じ境界に置く

UがPやBにPROCESS_DUP_HANDLEを取得できれば、file ACLの新規open拒否だけでは足りない。
PROCESS_VM_WRITE/VM_OPERATION/CREATE_THREADやthreadのcontext設定、tokenのduplicate/impersonate/assign/adjust、process/threadのWRITE_DAC/WRITE_OWNERも対象へ含める。
必要な待機/限定queryとこれらの権限を分け、実process/thread/token SDとUの要求を確認する。非継承flagだけで明示的な複製経路を消したとは言わない。
[process rights](https://learn.microsoft.com/en-us/windows/win32/procthread/process-security-and-access-rights)、[DuplicateHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle)。

資格情報を必要とする起動APIは設計上の残件。[CreateProcessWithLogonW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithlogonw)は候補だが、現U processでpasswordを保持してPを起動する構成にはしない。
B側で保護された起動を担当し、default process/thread/token DACLがUの危険権限を作成時から許可しない条件を先に固定する。
CREATE_SUSPENDED後に検査できることを、作成直後から検査までのopen/移管窓がない証明にはしない。初期SDの条件を用意できなければPへ仕事を渡さない。
LogonUser/別起動APIへ移る場合も、必要privilege・SA指定・token default DACL・handle継承・profile/環境・返却不明の所有を別仕様としてレビューする。
userへの追加権限付与、service化、別APIへの失敗時fallbackを自動的に行わない。

## 初回に作る限定試験と停止点

判断後も、最初に作るのは新規root1個の権限分離用harness。全publisher/markerへは接続しない。
新codeコピー/SD/複数processの所有と起動失敗をfakeで検証し、独立レビュー・実装savepointの後だけ新規max1へ進む。

1. Bが専用account/root、実SID/初期SD/外側親/code/runtime/初期process・tokenを確認する。P/U tokenの自己申告だけで通さない。
2. Pが新規rootを取得し、元handleでID/SD/実accessを確認。Pのpath CREATE_NEWで空file1個を作り、同handleで確認する。
3. Uの別workerがrootのLIST controlを成功させ、同じID/SDを確認。ADD/DELETE_CHILD等のOPEN_EXISTINGとfile変更用openの成否・errorを記録する。
4. 最後にUが別の新規名をpath CREATE_NEWで1回だけ試す。共有違反とACLの拒否を区別し、意図した権限拒否の有無を記録する。AccessCheckの予測だけで代用しない。
5. 作成失敗/応答不明ではUの所有をunknownとしてworker終了まで保持し、P/B側の親・祖先を先に閉じない。失敗名を存在確認/列挙/再open/hash/copy/deleteしない。Uの作成が成功した場合は境界失敗として停止する。

上記の詳細な要求mask、code配置、親の保持を跨ぐIPC/終了プロトコルは次の実装前仕様で固定する。現在の単一worker HeldDriverをそのまま複数processの所有証明に転用しない。
初回の成功条件は「Pによる追加が成立し、Uの普通の変更経路が拒否され、起動/既取得handle/全終了の条件も揃う」という限定結果。全期間不変・B2/S4受入とは別。
原rootはshare READ実績を出発点とするが、shareだけでUの拒否を説明しない。ADD用openがP/U双方で共有拒否される場合は判定不能として、path作成の差と実SD/tokenを別に扱う。

通常U processを網羅的に走査/停止しない。監視が対象にするのは今回生成したprocess objectだけ。
P/U計2 workerを上限とし、観測したworker合計private256MiB/working384MiB、内側40秒/外側45秒、空きRAM/disk2GiB、通常出力合計384KiBを初回上限案とする。
境界metadata/fileは各64KiB以下、記録合計16MiB以下を案とし、これらの上限を実装した後に使う。account/profile/OS全体のdisk量をこの論理上限に含めたと主張しない。
安全な起動監視が40/45秒枠に収まらなければ理由を記録し、同じ枠で上限を引き上げたり再試行しない。profile loadを省く案でもTEMP/環境/実行依存を先に固定する。

## この方式選択で変更しない契約

現行private/frozen policyはP/User/RCの固定形を持つため、P/Uを使うharnessは別policyとして検証し、既存verifierの期待SIDやdeny maskを差し替えない。
frozen親内のrename拒否は既に別の実機課題であり、新accountだけで解消しない。
[6工程/atomic no-replace marker](anomaly-v03-publication-model-design.md)と[予約した空markerへ最後にwriteする未採用案](anomaly-v03-publication-order-options.md)の選択は、この環境案への同意に含めない。
通常peerの生成前からの権限を排除できた後、名前変更が必要な時点と親最終policy、consumerの共通観測期間を再設計し、正式契約差分を別途判断する。
本流/S3/D2/production/科学schema/正式OS pin・VM digestを変更しない。Windows Update engineering緩和は継続してbuild/bootを記録する。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 不採用・終了時の扱い

今回の検討だけならOS側に新規作成物はない。方式を採用しない場合は文書と軽量な記録だけを残す。
将来の検証を終了する場合、作成したprocessの終了・検証account無効化の記録を先に残す。account/保護root/旧fixtureを自動削除しない。
account削除は残存tokenの失効手段でも、file/ACL/profileの自動除去保証でもない。保全期限と削除対象を明示した別のcleanup判断にする。
