# S4-B1 限定startup診断の実行記録（2026-09-10）

状態: **実診断1回完了 / 起動障害再現 / native受入なし**。

ユーザーは「観測上限30秒、親子合計512 MiB未満、未識別ブレークポイントで停止する実機診断を1回だけ」
という確認に「続けてください」と回答した。これを当該1回の実行承認として扱った。
実行時HEADは963a77a840f3c092baa05ffb0649a8cdc3c003ee、実装commitはb916de9。
開始前の候補worktreeはclean。通常CLI/importでは起動しないDebugDriverを明示的に1回だけ呼び出した。
再試行・別child・CDB/WinDbg/GFlags・loader snaps・required E2Eは実行していない。

## 結果

診断全体は2.346秒で戻り、restricted childの終了codeは **0xC0000142（3221225794）**。
以前の起動障害が現在のWindows更新状態でも再現した。
driver/session/observerのobservedは観測手順の完了を表し、childの起動成功を意味しない。

| 項目 | 実測結果 |
| --- | --- |
| driver status / resource stop | observed / false |
| restricted child作成 | created、suspended、ownership transferred |
| 実child検証後のResume | resumed |
| 観測event / Continue確認 | 7 / 7 |
| breakpoint / exception event | ともに0件 |
| child終了code | 0xC0000142 |
| process signaled / debug ownership resolved | true / true |
| TerminateProcess | 不要。terminate_state=not_started |
| 停止drain待機 | 0回 |
| child token teardown / driver teardown | pass / pass |
| primary / secondary / teardown reasons | null / null / 空 |
| native accepted / formal permission | false / false |

取得順序はCREATE_PROCESS、LOAD_DLL×3、UNLOAD_DLL×2、EXIT_PROCESS。
first/second-chance exceptionは観測されず、未識別breakpoint停止の分岐には入らなかった。
この記録だけで「初期breakpointより前に障害が起きた」と断定したり、DLL名・障害DLL・原因を特定したりしない。
DLL load順序や最後のDLLは原因の証拠ではない。debug条件によるタイミング差も残る。

OwnedDebugStopのexit_continued=falseは停止drain側の値である。
通常観測側では7 eventすべてのContinueが確認され、その後process signaledも確認された。
停止drainを使わず通常のEXITを処理した今回の結果と矛盾しない。

## 保存と環境

新規専用fixtureを1個作成し、private記録103,859 bytesを起動前から保持したfile handleへ書き込んだ。
capture=captured、write=confirmed、flush=confirmed、evidence file close=closed/resolved=true。
保存側のprimary/secondaryもnull。保存後のパス再探索・readback・source/temp/remote memory再読込みはしていない。
fixture_retentionはunverifiedのまま。既存rootも今回のrootも削除・ACL修復・再利用していない。
公開記録にはPID/TID、address、SID、private path、raw bufferを含めない。
保存formatと読み取り上の制約は[初回probe計画](anomaly-multiseed-v0.3-s4-b1-startup-probe-plan-2026-09-07.md)を参照。

同じ実行内のpreflightは15 source / 186,269 bytesを照合し、Windows10.0.26200.9445、Python3.14.0を記録した。
exe/python314.dll SHA-256は既存固定値と一致した。

| メモリ指標 | 実測値 |
| --- | --- |
| sampler回数 | 28 |
| 親＋childの記録上のpeak commit合計 | 23,977,984 bytes（約22.87 MiB） |
| 親＋childの記録上のpeak working合計 | 34,152,448 bytes（約32.57 MiB） |
| 最終取得system commit / limit | 35,719,258,112 / 70,493,097,984 bytes |
| 最終取得system available | 8,128,995,328 bytes |

process peakはsamplerが確認した各processの値を保持した指標であり、保存処理を含む実行全体の
連続測定やメモリリーク検査ではない。観測予算512 MiB未満でresource stopは発生しなかった。

PC全体の開始前の空きRAMは6.82 GiB、C103.09 GiB、D75.36 GiB。
終了後はRAM7.68 GiB、C103.09 GiB、D75.36 GiB（ディスク値は小数2桁丸め）。
別プロジェクトを含む値の変動からリーク有無を判断しない。他プロジェクトのprocess・設定・fileは操作していない。

実行後もmainは889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64eでclean。
候補も実行による追跡fileの変更はなく、その後に本記録を追記した。
大きな再走査や負荷試験、通常test一式の再実行は追加していない。

## 残る点

現在OSでも障害が再現し、今回のdebug event列には原因を直接示す例外がなかった。
障害DLL・初期化object・権限条件との因果関係は未特定。
追加の実機probeは自動実行しない。保存済み証拠の解析範囲や次の観測手段を具体化してから扱う。
B1 required E2E、Windows3.12、main統合、formal campaignは引き続き未達。
