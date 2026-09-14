# S4-B2 専用principal環境の準備記録

2026-09-15、engineering限定。ユーザー「はい、それで続けて下さい」により、専用標準accountと保護rootの準備を承認済み。[前回の方式案](anomaly-multiseed-v0.3-s4-b2-principal-boundary-2026-09-15.md)の未承認状態は履歴として保持する。
実装savepoint **e202677e66356e7b3e554d258ed73f73def7ea0f**、[準備仕様](../anomaly-v03-principal-setup-design.md)。

## 実装・確認

専用account BantoS4Publisherを最初からdisabled/standardで作り、root C:\ProgramData\BantoAI-S4B2-principal-20260915をBA owner、SY/BA full、U/P readonly、protected DACLとmedium labelで用意する限定処理を実装した。
祖先handle/実ID・SD保持、linked ordinary Uによる祖先DELETE/DELETE_CHILD/WRITE_DAC/WRITE_OWNERのpreflight、既存同名対象の拒否、NetAPI実SID/disabled/Users所属検査を含む。
資格情報はB内のunmanaged memoryだけで生成し、引数・ログへ保存しない。OS/paging/強制終了時のコピー消去までは保証しない。
phase失敗後はretry/補償/ancestor先行closeをせずprocess終了まで保持。メモリ解放失敗も事前確保stateに反映し、一次例外とexit phase/codeを維持する。
通常側でcompile/hash固定した公開DLL bytesを圧縮引数でBへ渡し、有界展開/hash/同bytesのAssembly.Loadを行う。BはU書換え可能なDLL pathを読まない。

最終build-03で**34件pass**。各phase故障、応答不明、close順、再使用拒否、SDDL/mask、Win64 ABI、secret pointer、解放失敗/二次OOM/終端解放の記録を確認した。
最終通常権限loader検査PID18112/exit0、account/root entry未実行。DLL bytes不一致と262145-byte超過の拒否も確認した。
独立レビューはP2総3件/P3総1件を修正し残0。読取専用、進捗ポーリングなし。
既存401件pass対象を含む前回73 sourceはraw/Git blob不変のため再試験しない。今回4 sourceを加えた77 sourceを固定し、前回manifest/5 artifacts不変、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全してcommit除外。
repository safety/差分/PowerShell構文/通常loaderの確認pass。

build-03 DLL SHA256 **e10c53362b5cf726b0e49605d3f9f83a88be5450a3ec89fafc40e242e3a62168**。
implementation-input.json18733 bytes/hash34e49c942f16123745fd9ac62dabc013d0871d72f66fef35695077091adf06c7、20 artifacts/論理414253 bytes（input自身を除外）。初期buildと修正後buildは上書きせず保持。

## 実機準備

UTC2026-09-14T17:03:09Zの事前確認でaccount/rootとも未存在。17:04:20Zに承認済みmax1の起動を記録し、Windows UACへ進めた。
UTC17:06:23Zにlaunch_failedで戻り、外側System.InvalidOperationException/HRESULT -2146233079をlaunch-result.jsonへ保存した。起動記録から約123.4秒だがUAC/起動前の待ちを含み、helperの実行時間ではない。
この時点の起動処理は内側WinErrorと失敗stage/PIDを保持しておらず、UAC取消・別の起動障害・process取得後の観測失敗を区別できない。helper開始/終了は不明、実機準備成功とはしない。
UTC17:07:18Zの対象SAM読取でaccount不存在。rootは作成結果不明のため再open/存在確認/列挙せず、状態unknownを保持した。account不存在をroot不存在に読み替えない。同じ作成attemptは閉鎖し、再実行していない。

事後の診断改善savepoint **f8495ed64908dded70e9737c9b0615d55f23f044**。次回の失敗時は起動stage、取得済みの場合だけowned PID、最大4段の例外type/HRESULT/native codeを残す。Message/command/InvocationInfoは保存しない。
純粋な記録関数だけを抽出した**6項目の追加確認pass**、追加独立P0〜P3=0。管理者再起動やC# DLL差替えはしていない。この改善から今回の失敗原因を遡及確定しない。
次はWindowsの管理者確認を操作できる状態で、**OS設定を変更しない昇格診断**を先に固定する。今回の不明rootを再訪する診断や閉鎖attemptのretryにしない。

## 資源と残件

UTC16:40:36 RAM16880279552/C125132517376/D37115596800 bytes、16:55:45 RAM16483479552/C125090119680/D28057473024 bytes、17:03:09 RAM16054964224/C125088272384/D27387621376 bytes。
D空きは今回記録中にも減少、原因未特定。この作業の新規code/artifact保存先はCドライブ。他project/processの走査・停止なし。長期リーク不在の主張はしない。
最終UTC17:09:46Z RAM15485636608/C125072465920/D27387604992 bytes。C約116.48GiB/D約25.51GiB、Dは17:03以降ほぼ横ばい。今回の初期記録から約9.06GiB減少した履歴を残す。
最終savepoint-evidence.json **22001 bytes/hash e5acb7c762bac4f91f59c879eebd5e115a5d41e9f97aa58c00e6379efa898e21**。78 sourceを診断改善revisionのGit/rawで照合。native inputとその20 artifactsは不変、最終27 artifacts/論理437818 bytes（最終manifest自身を除外）。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和と正式pin不変を継続する。既存Python3.14.0/.NET compilerのみ使用し、Python3.12の追加なし。
本流889cfc3/clean不変、push/merge/CI/VM/service/task変更なし。旧native source/枠の再open/列挙/hash/copy/deleteなし。

Pログオン・独立P/U worker・protected code配置・process/thread/token/IPC・namespace共通期間・全publisher・frozen/marker契約・正式B2/S4は未完了。
無効accountからの起動には、新secretのB内resetと有界activation/launch/disable/全worker終了を別仕様にする。account無効化を既存token/handle失効としない。account/rootの自動削除はしない。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。
