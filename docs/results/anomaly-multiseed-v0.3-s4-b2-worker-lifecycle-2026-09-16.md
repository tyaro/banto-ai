# S4/B2 worker lifecycle model and launch capability observation

2026-09-16 JST「次に進めてください」で、準備済みjの次段階を進めた。
実装savepointは **cbd3df9a61348562019a2c4ae9113e17e122dd96**。
[設計](../anomaly-v03-principal-worker-lifecycle-design.md)の純粋modelと通常Uからの読み取り診断を追加した。
Pのreset/enable/logon、rootアクセス、privilege調整、UAC、実worker起動は行っていない。

## 実装・試験

26操作の通常経路と、有効化応答不明時のDisable→Verify、既知secretのゼロ化/解放、job停止→全process終了→job空確認、内側からのscope解放をモデル化した。
未知の取得handleは推測closeせず、外側のcode/祖先を保持する。stop要求を終了証明にせず、primary障害と後発障害を別に残す。
各scopeは記号であり、実handle台帳、時間/メモリ制限、初期SD、job原子参加を強制するnative backendは未実装。
ModelSucceededは仮定した応答の順序検証だけで、native実行許可にはならない。

独立レビューは既存Maxwell 1体に限定し、進捗pollなし。初回model P2 1件（HashSet割当て失敗で工程が消費される）を、構築時確保のbitset/配列へ修正した。
診断P2 2件（未確定out handleのclose、close例外によるprimary/他方close喪失）は、取得確定leaseと独立した単回解放へ修正した。最終P0〜P3所見0件。

採用 **build-03、65 model＋8 query lease＋15 privilege/parser＝88件pass**。csc x64/optimize+/warnaserror+、repository safety/diff-check pass。
最初の手動cscコマンドは相対path表記でsource解決に失敗し、出力生成前に終了。固定launcherの絶対pathで修正した。
build-01/02はレビュー修正前の中間生成物として保存し、実行採用しない。setup jの既存source107個/public artifact13個は全て不変。

## 通常Uでの読み取り診断

`PrincipalLaunchCapabilityDiagnostic-build-03.exe` は **32768 bytes / SHA256 5f4f4ae2fa623067f7d4f05d3a4b1782f8fbcb7a11980de2ad3a4f54ab731a33**。
通常Windows PowerShellが、有界読取り→hash照合した同一bytesをLoadし固定Mainを一度呼んだ。RunAs/UACなし。
`PrincipalSetup.cs` は既存parserを再使用するため同梱compileするが、診断MainはNativeBackendをインスタンス化しない。
自分のtokenはTOKEN_QUERYだけで開き、固定U SID/elevation0/typeLimitedを確認。linked tokenも同SID/elevation1/typeFull、非継承を確認して固定3特権だけを照会した。

UTC **2026-09-15T16:11:05.2815534Z**、query_complete=true、launcher exit0。
own/linked tokenともCloseHandle成功、取得不明=false、primary/release/両個別release error=null。

| 特権 | linked tokenでの観測 |
| --- | --- |
| SeIncreaseQuotaPrivilege | present=true / enabled=false |
| SeAssignPrimaryTokenPrivilege | present=false / enabled=null |
| SeImpersonatePrivilege | present=true / enabled=true |

`launch-capability.json` **614 bytes / SHA256 9d44ebe97433f9ef71b86f71a6d32618c7dbd0022b3fa9cc2cc094a689ee8cee**。
このlinked tokenの読取りは将来の別UAC tokenやP tokenのassignabilityを証明しない。
SeAssignPrimaryTokenPrivilege不存在だけからCreateProcessAsUserWが必ず失敗すると断定しないが、別user Pへcallerのrestricted-token例外を適用できたとは扱わない。
必要な起動条件が未成立なので、Pを有効化してAPIを試す段階へは進めていない。
診断結果fileはCREATE_NEW guardを兼ねるため同じDiagnoseを再実行しない。

## 証跡・資源・保全

公開証跡は `artifacts/principal-worker-lifecycle-2026-09-16`。
input **19627 bytes / SHA256 d4ccd4546b5fb26d61030de7795b8b8f1d6211ba8381c15b04b628a3d9bb41b2**。
113 source（前回107不変＋新規6）のworkspace bytesとgit blob一致、旧j13公開artifact不変を実行前後に確認。
最終manifest **24645 bytes / SHA256 1cae772d518ca0d62cb91a44deacc87560910ecc2e4b5159dfa3b088c2e0959a**。
manifest自身を除く16 artifacts、論理249764 bytes。全snapshotの各source pinは採用build-03に対応し、中間buildとの一致を主張しない。

終了後UTC16:12:57、空きRAM6608343040、C149446660096、D198224842752 bytes（D約184.61GiB）。
開始時の参考観測RAM6384390144/C149731835904/D198225006592 bytesと、実行直前/直後の保存snapshotを区別する。
PC全体の変動原因や長期リーク不在、診断process全寿命の厳密peakは未確認。
OS26200.9445、boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和を記録し正式pinは不変。

旧9 rootと準備済みjへ一切アクセスしていない。Pの現在SAM再照会もなく、最後の無効/Users確認は前回j終了後の記録に基づく。今回account変更なし。
本流 **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e / clean** を維持。
既存親policy結果書 **8461 bytes / SHA256 443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621** を保全・commit除外。
新runtime/service/task/VM/profile、push/merge/CIなし。

## 次の工程

追加のOS権利を付与せず成立する起動API条件を先に確定する。CreateProcessAsUserWのtoken条件、process/thread/token初期SD、desktop/環境/IPC、作成時job参加の仕様を結び付ける必要がある。
既存privilegeの有効化と、新たな権利付与は区別する。SeAssignPrimaryTokenPrivilegeを勝手に追加したり、SA引数を持たないAPIへ失敗時fallbackしない。
既存権利の範囲で成立しない場合は、必要になる権利/構成変更と影響を具体化した上でユーザーへ判断を求める。
その後に実handle台帳/制限/containment adapterを実装・故障試験・レビューし、suspendedの仕事をしないworkerから段階的に検証する。

environment_preparation_complete=trueは前回jの結果を維持。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。
P-U干渉、全publisher、namespace共通期間、frozen/marker、正式B2/S4は未完了。
