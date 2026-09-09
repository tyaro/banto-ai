# S4-B1 image identity/name付き実機診断（2026-09-10）

状態: **承認済み追加診断1回完了 / 起動障害再現 / 原因未特定**。

ユーザーは「前回と同じ資源・停止条件で、DLL名も記録する実機診断を1回だけ実行してよいですか」に
「続けてください」と回答した。この1回の承認として実行し、自動再試行していない。
実行時HEADは43d05f5271e0f53c2fd918ce2c279474e3f42ebd、実装は06f1e638c6f07dd1f733aa7bce0e392536e60bef。
候補worktreeは開始前・実行直後ともclean。新規fixtureとrestricted childを1個ずつ使用した。

## 観測結果

全体の所要時間は3.216秒。child終了codeは **0xC0000142（3221225794）** で、起動障害を再現した。
driver/session/observerはobserved。これは観測手順の完了であり、childの起動成功やnative受入を意味しない。

| slot | event | 借用file handleから確認した名前 |
| --- | --- | --- |
| 0 | CREATE_PROCESS | python.exe |
| 1 | LOAD_DLL | ntdll.dll |
| 2 | LOAD_DLL | kernel32.dll |
| 3 | LOAD_DLL | KernelBase.dll |
| 4 | UNLOAD_DLL | 今回の公開要約では未対応付け |
| 5 | UNLOAD_DLL | 今回の公開要約では未対応付け |
| 6 | EXIT_PROCESS | code 0xC0000142 |

4つのimage rowはすべてconfirmed。各file handleからvolume/file ID、normalized NT path、
再取得したvolume/file IDの一致を確認してから、既存transportでhandleをcloseした。
表はbasenameだけを記載し、full path、file ID、PID/TID、addressはprivate記録へ分離した。
collectorはstate=ready、count=4、primary/secondary=null。

通常eventは7件、Continue確認も7件。breakpoint、first/second-chance exceptionは0件。
今回のevent列にpython314.dllのLOAD_DLLはない。ただし、未観測と実際の未読み込みを同一視せず、
DLL初期化のどの内部処理が失敗したかは断定しない。名前・load順・最後のDLLは原因の証拠ではない。
file identity/nameの取得はloaded bytesのhashや真正性の認証でもない。

前回の別processで確認した匿名module3→2のunloadと、今回の名前を無条件に結合しない。
今回のraw bufferは保存済みだが、この工程では保存後のfile再読込による追加対応付けは行っていない。

## 終了と保存

process_signaled=true、debug_ownership_resolved=true、child token/driver teardown=pass。
TerminateProcessは不要（terminate_state=not_started）、停止drain待機0回。
driver、stop、保存処理にprimary/secondaryはなく、teardown理由も空。
OwnedDebugStopのexit_continued=falseは停止drain側の値であり、通常EXITのContinue確認とは別である。

private保存は104,807 bytes、capture=captured、WriteFile=confirmed、FlushFileBuffers=confirmed。
保存fileはclosed/resolved=true。resource_stop=false。
保存後、同じprocess内に保持していた出力bufferのbytesからSHA-256を算出した。

`001a73ca15f72db9803981878ba6456eb50a576be400fe456c2815cc05634bbf`

これはメモリ内出力bufferのhashであり、保存fileをreadbackしたhashではない。
後日の読取り照合に使えるが、今回のfile内容のreadback検証や耐障害性を保証しない。
fixture_retention=unverified、native_accepted=false、formal_permission=falseを維持した。
旧rootも今回のrootも削除・修復・再利用していない。

## 環境と資源

同runのpreflightで16 source / 192,088 bytesを照合した。
Windows10.0.26200.9445、CPython3.14.0、exe/python314.dll hashは既存固定値と一致。

| 指標 | 実測値 |
| --- | --- |
| memory sampler回数 | 44 |
| 親＋childの記録上のpeak commit合計 | 24,047,616 bytes（約22.93 MiB） |
| 親＋childの記録上のpeak working合計 | 34,504,704 bytes（約32.91 MiB） |
| 最終取得system commit / limit | 35,419,521,024 / 70,493,097,984 bytes |
| 最終取得system available | 8,469,442,560 bytes |

観測予算512 MiB未満でresource stopは発生しなかった。process peakはsamplerの確認値であり、
保存処理を含む実行全体の連続測定やメモリリーク試験ではない。
PC全体の開始前の空きRAM8.14 GiB/C102.25 GiB/D75.36 GiB、終了後RAM7.97 GiB/C102.24 GiB/D75.36 GiB。
別プロジェクトの同時稼働を含む単発値から、変化の原因やリーク有無を判定しない。

mainは実行後も889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64eでclean。
他プロジェクトへの操作、追加child、CDB/WinDbg/GFlags、loader snaps、required E2E、負荷試験は行っていない。
docs追記のための確認のみで、既存artifactの大きな再走査やtest一式の再実行も追加していない。

## 次に扱う点

取得した名前により、例外なしで終了する今回の起動event列を具体化できた。
原因DLL、初期化object、restricted token/default DACL等との因果関係は未特定。
次は保存buffer hashと照合したoffline解析、または必要な追加観測の範囲を具体化する。
追加の実機probeをこの承認のまま繰り返さない。B1 required E2E、Windows3.12、main統合、formal実行は未達。

## 別工程のhash照合とunload対応（2026-09-10）

次の継続指示を受け、保存記録をread-onlyで解析した。temp直下4,096件、専用prefix root32個の上限で、
固定名control/startup-evidence.binのmetadataだけを調べ、104,807 bytesの候補1件を選択した。
既存のheld-handle/reparse/NTFS検査付き有界readerで当該fileだけを読み込んだ。
SHA-256は上記の実行時メモリ内出力buffer hashと一致した。
format、OS build、source16行、event7件も一致し、旧記録への書込み・修復・削除は行っていない。

同じ記録内でevent slotと保存image rowを結び、base一致を用いてslot4はKernelBase.dll、slot5はkernel32.dllの
unloadと対応付けた。前回の別processのbaseやload順から名前を割り当てたものではない。
normal7、drain0、wait/continue inflight=false、confirmed範囲外の保存bytesはzeroだった。
この工程でもchild/driver/debuggerは起動していない。

hash一致は保存bytesが実行時出力bufferと一致することの確認であり、DLL内容の認証や原因DLLの特定ではない。
readerのprovenance_verified=false / native_accepted=falseを維持する。
次の権限観測候補は[process/thread権限観測案](anomaly-multiseed-v0.3-s4-b1-process-security-plan-2026-09-10.md)へ整理した。
