# S4-B2 親共有とpath新規作成の比較準備・実機停止

2026-09-15 JST、基準4e9bc81。実装savepoint **2ec193adf8f81bed5685de0ff0cc09276e2741f7**。
[比較仕様](../anomaly-v03-namespace-create-design.md)を実装し、397件pass/0.727秒、独立P0〜P3所見0件を確認後、新規max1を実施した。
**最初のshare3親directoryのCreateDirectory2Wが失敗し、peer openと子file作成には到達していない。比較結果は未取得。**
worker exit81/終了確認、監視stopなし。失敗枠は閉鎖し、存在確認・列挙・再open・hash/copy/delete・再試行を行わない。

## 比較の実装と限定結果

新規root2個をaccess0x1600a7、share3/1、redirect拒否、明示private SD、非継承で取得する設計。
各rootで同一process/tokenのLIST/ADD_FILE/ADD_SUBDIRECTORY/DELETE_CHILD用OPEN_EXISTINGを確認した後、path指定CREATE_NEWで空fileを作る。
peer取得とpath作成を別に記録し、両rootをmetadata保存まで保持する。既知の非作成拒否例外を作成失敗へ流用しない。
既存driver/launcherを利用し、launcherの変更はscope選択だけ。生payload返却は引き続き拒否する。

| 今回の記録 | 結果 |
| --- | --- |
| 最初の親 | directory_create_failed、phase=create_pending、取得応答あり、close=unavailable/unknown、ID/SD/実access観測なし |
| 入力descriptor | freed。親の作成失敗を無作用・不存在とは扱わない |
| 第2親・両peer・両child | 全て未開始 |
| evidence | not_started、保存bytes/hashなし。失敗状態はstdoutにのみ記録 |
| 祖先/evidence root | 11 leaseをready/close未開始でworker終了まで保持。query token1本はclosed |
| worker | PID41196、exit81、retained_for_worker_exit=true、終了確認 |
| 実行時間 | UTC2026-09-14T15:43:06.7531569Z〜15:43:07.4616119Z、監視計測0.689秒 |
| 出力 | stdout10369 bytes、stderr0、監視stop/errorなし |

reportには一次例外のreason/typeがあるが、今回の親作成失敗のWinError数値は出力されていない。具体的原因はこの証拠だけから確定できない。
share3をWindowsが拒否した、ACLが原因だった、名前一覧が保護された、という結論はいずれも出さない。
同じroot/枠へ戻らず、次は親作成エラー数値の記録を追加してから別の新規診断仕様を固定する。

## 回帰・証拠・資源

新規20＋既存377＝397件pass。failure/error/skip/expected failure/unexpected success全て0。
作成拒否/応答不明、親変更、peer不明、単回close/free、再入、一次例外と二次resource、親/祖先保持とdriver接続をfakeで確認した。
独立レビューはread-only/進捗ポーリングなし。PowerShell構文/repository safety/diff検査pass。試験成功は今回のnative作成成功を保証しない。
initial-checks.jsonl287649 bytes/hashd07fbfb2418c5c90c5af157a25393a8cbf1d928fee1e1c8d00365619f8a675a0。

別clean detached C:\Users\TKent\.codex\worktrees\namespace-create-20260915\banto-ai、HEAD2ec193a。
選抜70 sourceと入力109 sourceのunion139をnative raw/Git blob、選抜sourceを候補とも前後照合した。
候補の追加runtime22件は既存CRLFのみの差として記録し、書換えずnative LF bytesをpinへ固定。
input-pin.json17695 bytes/hash82a3fa6e08bfbb6b3ae1fc1bd4c5b4202d2e62d2406681d0986667a84d56ffba。
前回held-launchのmanifest/13 artifactsは不変、65 source中64不変。変更はlauncher scopeの1件。
ignored artifacts/namespace-create-2026-09-15/に13 artifacts/論理443868 bytes（manifest/別checkout複製/実fixture除外）。
savepoint-evidence.json45792 bytes/hashcb146bf4aebab18e24dacd4ea3eb5e222ec6758f270cad4756bce7d924de981a。

内部資源8点、最後0.062秒、private最大21127168/working29368320、OS working peak35872768 bytes。
外側1点/0.594秒、private20918272/working28045312 bytes。40秒/45秒、private256MiB/working384MiB、空きRAM/disk2GiB以内。
UTC15:39:01 RAM14369255424/C125840904192/D48828010496 bytes、15:45:07 RAM16178049024/C125442588672/D48269496320 bytes。
PC全体の空き容量変動は今回の論理記録量とは異なり、原因未特定。長期リーク不在を主張しない。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変、既存Python3.14.0。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3、旧fixture、他process、push/merge/CI、runtime/account/service追加へ操作なし。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。
