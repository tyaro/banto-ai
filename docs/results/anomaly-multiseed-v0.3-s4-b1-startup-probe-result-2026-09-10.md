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

## 別工程での保存記録解析（2026-09-10）

上記実行の終了後、ユーザーの継続指示を受け、保存済みprivate記録だけをread-onlyで解析した。
実行時の「観測後にsource/temp/remote memoryを再読込みしない」手順はそのまま保持し、
今回は実行完了済みの記録を対象とする別工程とした。child/driver/debuggerは再起動していない。

temp直下の列挙は4,096件まで、banto-s4-b1-という専用prefixのroot候補は32個までに制限した。
候補rootの固定名control/startup-evidence.binだけを調べ、候補は1ファイルだった。
実行記録の103,859 bytesと照合し、既存のheld-handle/reparse/NTFS検査付き有界readerでその1ファイルを読んだ。
OS build、source15行、通常event7件、終了codeも前回の要約と一致した。
元fileの書込・削除・ACL変更や、他のfailure rootの内容読込は行っていない。

今回読んだbytesのSHA-256:
`45a310ebc2183d4ea90cd02ca150c39699ca79edea41382ac3ecec3ccbf41bba`

このhashは今回のread時点の値。実行時に保存したhashとの比較ではなく、真正性や過去の無変更を認証しない。
readerはformat_valid=true / provenance_verified=false / native_accepted=falseを返す。

| event順 | byte記録の解釈 |
| --- | --- |
| 0 | process image（匿名module0） |
| 1 | DLL load（匿名module1） |
| 2 | DLL load（匿名module2） |
| 3 | DLL load（匿名module3） |
| 4 | module3と同じbaseのunload |
| 5 | module2と同じbaseのunload |
| 6 | exit 0xC0000142 |

normal confirmed7、drain confirmed0、両領域のwait/continue inflight=false。
confirmed範囲外の保存bytesは両領域ともzeroだった。未観測eventの不在をOS全体について保証するものではない。
匿名番号はこのfile内のload順。baseの一致だけを対応付け、例外所在や原因DLLの特定には使わない。
保存rawにあるimage_name等のpointerは追跡しない。プロセスは終了済みであり、DLL名の文字列や
event file handleのfile identity/pathを保存していなかったため、今回の記録からDLL名は復元できない。

新しいbyte-only readerは別テスト部品とし、実診断driverからはimportしない。
当時の15 source pinや保存format、production sourceは変更しない。
長さ/型/重複JSON key、不正count、未確認枠、匿名load/unload、公開redactionのpure5/5 pass。
独立レビューの新規P0〜P3=0、指定pure5/5（0.006秒）。担当は実記録を読んでいない。

次にDLL名を必要とする場合は、LOAD_DLL/CREATE_PROCESS eventのfile handleをcloseする前に
file identityと名前を有界に取得・保持する観測部品が必要になる。
終了後のpointer参照、現在の親processのDLL配置からの推定、load順序だけのDLL名割当ては採用しない。
追加実機probeはこの工程では承認も実行もしていない。
