# S4-B2 親share READ保持中のpath新規作成

2026-09-15 JST、基準37ec1c9。実装savepoint **674d1193711334fefd21bc56c11ffa8000943e6a**。
[単独case仕様](../anomaly-v03-namespace-readonly-design.md)の新規max1で、**親ADD_FILE/ADD_SUBDIRECTORY用handleは共有違反で拒否された一方、path指定CREATE_NEWで空fileの追加が成功した。**
今回の同一process/token/private DACL条件では、親をshare READで保持するだけでは新しい名前の追加を防げない。
401件pass/2.278秒、独立P0〜P3所見0件。実機0.770秒、証拠保存・全既知handle close・worker exit0/終了確認まで完了。
独立process/tokenの干渉、全namespace・全期間不変、B2/S4受入の完了ではない。生consumer bytes返却は拒否を維持する。

## 新規実機で観測した操作

親をCreateDirectory2W、access0x1600a7 exact、share1、redirect拒否、private SD、非継承で作成・取得した。
原handleのID/SDをpeer前後・child観測後に照合し、結果保存まで保持した。SDを途中で変更していない。
peerは同じprimary tokenからshare7/OPEN_EXISTINGで1回ずつ取得し、成功handleを同ID/SD/実accessで確認してcloseした。

| 操作 | 要求access | 結果 |
| --- | --- | --- |
| LIST_DIRECTORY用peer | 0x120081 | granted/closed |
| ADD_FILE用peer | 0x120082 | denied、WinError32、既知の非作成no-handle拒否 |
| ADD_SUBDIRECTORY用peer | 0x120084 | denied、WinError32、既知の非作成no-handle拒否 |
| DELETE_CHILD用peer | 0x1200c0 | granted/closed。削除操作は行っていない |
| new-empty.binのpath CREATE_NEW | 子0x120081/share7 | accepted。同handleで空/links1/非delete-pending・ID/SD/実access確認後closed |

親ID86690d00000080000000000000000000、子ID0f6b0d00000034000000000000000000。
親を通る新しい子fileの作成と、親そのものをADD権限でopenする要求は、同じ結果にはならなかった。
親ID/SDの観測一致は、子の名前一覧が変化しない根拠にはならない。今回の追加は同じworker/tokenによる意図した操作で、独立peerが操作したとは言わない。
入出力親と子のdescriptorはfreed、親1＋子1＋granted peer2＋sink12＝16 file/directory handleとquery token1がclosed。
peerのnamespace_mutation_performed=falseは4件のOPEN_EXISTING部分だけの状態で、後続child_create=acceptedを否定するものではない。

初期tokenはprimary/非昇格/medium、enabled privilegeはSeChangeNotifyPrivilegeのみ。token生成・impersonation・AccessCheck・移管・全期間監査は実施していない。
source-fixtureは作らず、share-read-write controlも省略した。[前回診断](anomaly-multiseed-v0.3-s4-b2-namespace-diagnostic-2026-09-15.md)のshare3作成87を解消した、またはshare3対照比較を完了したとは扱わない。
payload write/delete/renameなし、空fileはそのまま残した。今回も閉鎖済み枠を再利用しない。

## 保存・起動・資源

新規clean detached checkoutはC:\Users\TKent\.codex\worktrees\namespace-readonly-20260915\banto-ai、HEAD674d119。
UTC2026-09-14T15:56:31.4716823Z〜15:56:32.2623011Z、外側計測0.770秒、PID25500/exit0/終了確認、stop/errorなし。
stdout23949/stderr0 bytes、held_driver/collection=complete、evidence=saved、retained_for_worker_exit=false。
metadata保存はprivate-evidence/prepare.json slotへ4082 bytes/hash6e066529de9207b26f87ed8533ce7ee25958e704ab73152e1fe578321feac59e。
reportのcollection_evidence_bytes/sha256にこの値が入り、未使用prepare barrierのprepare_bytes/sha256はnull。
hashはworkerの保存・読戻し完了報告による。終了後にsource/private-evidenceを再openして独立照合したものではない。

内部79資源点、最後0.189秒、観測private最大21180416/working29548544、OS working peak35905536 bytes。
外側1点/0.577秒、private21184512/working29007872 bytes。40秒/45秒、private256MiB/working384MiB、空きRAM/disk2GiBの全上限内。
UTC15:55:13 RAM15006621696/C125367009280/D45615149056 bytes、15:57:35 RAM15456075776/C125327585280/D45614665728 bytes。
この作業開始時のツール観測UTC15:28:19ではD55098978304 bytesであり、今回末尾までにPC全体のD空きが約8.83GiB減った。原因は未特定で他processへの操作なし。
この3工程の候補側記録はmanifest込み合計1859099 bytes。別checkout複製・Git/worktree・実fixture・PC全体の使用量を含む数字ではない。
長期メモリリーク不在やPC全体の容量減少の原因を証明しない。worker/監視は全て終了している。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。既存Python3.14.0、新account/service/runtimeなし。

## 回帰とsavepoint

新規2＋既存399＝401件pass。選択case、保存までの親保持、終了順、許容matrix形、実contextのcase準備を追加確認。
failure/error/skip/expected failure/unexpected success全て0。独立所見0件/read-only/進捗ポーリングなし、レビュー後code変更なし。
結果文書/引継書と保存ログの独立照合もP0〜P3所見0件。
repository safety/PowerShell構文/diff pass。initial-checks.jsonl290308 bytes/hash36a6664f33b3d8a35a2c57a070372539d00d8212b40b1f774b1e5a27ace6a872。
選抜72 sourceと入力109 sourceのunion141をnative raw/Git blobで前後照合、選抜は候補とも一致。候補の追加22 sourceは既存CRLFのみ、改行正規化で一致を確認して書換えず保全。
input-pin.json17695 bytes/hashf039debbb0b99a2ebebfc398681f7b8912b341b1fa686521614d6f6515f4805e。
前回namespace-diagnosticのmanifest/15 artifactsは不変、71 source中67不変。変更4件はnamespace本体/test/probe/supervisor。
artifacts/namespace-readonly-2026-09-15に13 artifacts/論理462313 bytes（manifest/別checkout複製/実fixture除外）。
savepoint-evidence.json47676 bytes/hash4b26123e10ba815ea10e8f1e809991609e669a2c34e4fa0d7a0920f149317f6c。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommit除外。本流889cfc3不変。
旧source/枠、S3/D2/production、push/merge/CI、他processへの操作なし。

## 次の境界

親share READだけをnamespace隔離の根拠として採用する経路は、この実例により進めない。
次は[権限境界の設計](../anomaly-v03-isolation-basis-design.md)に戻り、publisherに必要な追加/renameと通常peerへ与えない権限を一覧化する。
同じSIDの通常tokenへ同じDACLを適用するだけではpublisher/peerを区別できる根拠にならない。保持handle・取得前の権限、外側親、processからのhandle移管も残る。
専用principalが必要となる場合は、local account/隔離VMの配置、起動・資格情報・consumer読取の運用差を具体化してからユーザー判断へ出す。現時点でaccount/サービス作成を行わない。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。
