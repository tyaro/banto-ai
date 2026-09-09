# S4-B1 初期化失敗の次の観測方法（2026-09-10）

状態: **比較・準備のみ / 追加実機診断未承認・未実行**。

3回の限定診断で同じ0xC0000142、通常7 events、例外・breakpointなしを観測した。
名前・ACL・token所属の保存解析だけでは、失敗したobject/operation/要求権限を特定できていない。
次はその情報が得られる観測方法を選び、同じevent列を取得するだけの再実行は行わない。

## 追加起動なしで確認した既存記録

専用root32件・temp直下4096項目以内で107403 bytesの証跡候補が一意であることを確認し、
最終書込み時刻2026-09-09 16:51:30.531269 UTC（2026-09-10 01:51:30.531269 JST）を取得した。
これはファイルmetadataの時刻であり、厳密なchild開始・終了時刻ではない。
前後15秒に限定しApplication logのevent ID1000/1001を最大33件（許容32件）で照会した結果、0件だった。
ログ全体の走査・他eventの本文読取り・ログ設定変更・消去はない。
指定window/IDに記録がないという観測であり、全Windowsログに障害記録がないとの結論ではない。

## 候補の比較

| 方法 | 得られる可能性がある情報 | 残る限界・実行前に詰める条件 |
| --- | --- | --- |
| 既存debug eventとdescriptor再取得 | module/exit/ACL | 既に取得済み。失敗operationを追加で得られない |
| Process Monitor | file/registry/process/thread操作、結果、stack | 全kernel objectのアクセス失敗を網羅するとは限らない。収集範囲と上限の実効性が未検証 |
| loader snaps | loader内部のDLL load/unload詳細 | 今回の許可範囲外の設定変更を伴う。出力量、対象分離、停止手順の設計が必要 |
| 特定APIへのdebugger breakpoint | 特定call/戻り値 | 失敗前に設置できるか未確認。現在の全breakpoint停止条件と両立せず、別設計が必要 |

[Process Monitor公式説明](https://learn.microsoft.com/en-us/sysinternals/downloads/procmon)はfile system、registry、
process/thread activityとstackの記録、非破壊filterを説明している。
したがってPID等を表示filterで絞るだけで非対象eventを収集しない、あるいはメモリ使用量が制限されると仮定しない。
公式説明の大規模ログ対応も、小さい固定容量で停止する保証ではない。
このPCでは別プロジェクトが連続稼働中なので、実機導入・起動より先に収集除外と容量停止の方法を検証する。
今回Procmonをdownload/install/runしたことはない。

[Show loader snaps](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/show-loader-snaps)は
FLG_SHOW_LDR_SNAPS=0x2とsystem/kernel/image設定を説明する。
特にpython.exe共通のimage設定は、同名の別起動へ影響し得るため今回の共有PCへそのまま適用する案にしない。
GFlags、registry、PEB、codeの変更やCDB attachは行っていない。既存の禁止条件を自動解除しない。

## 次の準備の優先順位

まずProcess Monitorについて、導入せず参照できる公式資料で収集時の除外・固定記録上限・停止方法を確認する。
条件を示せなければ、この共有PCでの低負荷診断としては準備未完了とする。
別環境での再現案は実際のWindows/Python/token条件差を明示する必要があり、勝手に別環境へ移行しない。
失敗候補のACCESS DENIED等が得られても、通常の探索・fallback中の失敗と原因を区別する。
実行提案は対象、時間、全関係processの資源上限、記録上限、既存child停止との協調を具体化した後に行う。
今回はその実行承認を求める段階ではない。

## 前回の表示エラーへの対策

tests/fixtures/anomaly_v03_debug_report.pyに明示呼出し専用write_summaryを追加した。
最終driver値をwhitelistでJSON1行にしてflushした後、image等の任意詳細を別行にする。
Noneの未使用image枠を除外し、詳細構築失敗は型名だけを出す。raw例外、path全体、SID/profile/file IDは出さない。
resource停止時は詳細を参照せず省略する。出力の部分write/flush失敗は再試行せず呼出し元へ返す。
各行16 KiB以下。証跡hashは正常capture済みの所有bufferからのみ取得し、保存fileのreadbackとは区別する。

今後の明示実行時は、driver.runから戻った直後にwrite_summary(driver, sys.stdout)を呼ぶ。
診断driverへの自動接続、launcher/CLI、追加native query、path lookupはない。
post-run helperは実行後にimportする運用であり、現行preflightの17 sourceには追加していない。
実行前importや診断経路へ接続する変更を行う場合は、その時点でsource範囲を再検討する。

pure4/4 pass。独立レビュー新規P0〜P3=0、指定pure4/4 pass（0.001秒）。
repository safety PASS、diff-check pass。codeはpost-run helperとその試験のみ。
この対策で過去runの不明な最終保存状態・memory peakを復元したとは扱わない。

## Process Monitorの収集除外・容量・停止の一次資料確認（2026-09-10）

結論: 機能の存在は確認できたが、この共有PCで従来の資源・証跡保持条件を満たす実行案は未完成。
ツールのdownload/install/run、driver/service操作、追加childは行っていない。
Microsoft Q&Aも検索に現れたが、利用者の回答を製品の動作保証として採用していない。

| 項目 | 一次資料から確認できたこと | この診断で残る確認 |
| --- | --- | --- |
| 対象外イベント | Drop Filtered Eventsを使った収集例がある | 収集開始前の設定適用、PID対象分離、非対象process情報や収集処理の負荷 |
| 記録量・履歴時間 | v3.70でデータ量/分数に応じて古いeventを破棄する機能を追加 | byte上限到達時の全体停止とは異なる。最初の失敗eventを失わない条件 |
| backing file | fileへの記録と最大file size設定に言及 | 最小設定値、PMLと補助fileの合計上限、flush中の増加量 |
| 終了 | -terminate -quietによる停止・保存の公式例あり | 特定所有instanceだけを選択できるか、終了期限・保存失敗・既存収集との干渉 |
| メモリ | 今回参照した一次資料に全関連process/driverの固定commit上限保証はない | 既存の親＋child512 MiB監視だけでは追加ツールの資源を管理できない |

[Microsoft AskPerfの実例](https://techcommunity.microsoft.com/blog/askperf/the-case-of-the-randomly-launching-internet-explorer-processes/374702/)は
backing file、Drop Filtered Events、process/operation filterを併用している。
これは対象外eventを破棄する設定の実例であり、監視処理自体が対象PID以外へ全く作用しないという保証ではない。

[Sysinternals v3.70リリース記録](https://techcommunity.microsoft.com/blog/sysinternals-blog/procmon-v3-70-sysmon-v13-10-autoruns-v13-99-tcpview-v4-01-and-winobj-v3-03/2280263)は
履歴の分数/データ量による制限と、必要に応じた古いeventの破棄を説明する。
同じ記録にはDrop Filtered Eventsが常に尊重されなかった不具合の修正もある。
従って古い設定例を現行版へ無検証で移さず、使用版と実際の設定適用を確認する必要がある。
この履歴制限を全process commitや全disk writeの厳密な上限に読み替えない。

[Windows Clientの公式診断手順](https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/troubleshoot-apps-start-failure-use-process-monitor)は
file-backed記録、最大file size設定、終了保存の例を示し、上限なしの長期記録によるdisk/virtual memory枯渇に言及する。
終了例には対象PID指定が示されていない。既存の他作業の収集があれば一括終了してよいとは扱わない。
資料中のPsExec/SYSTEM実行例やACL修正例は、本作業への実施指示・承認ではない。
今回は終了コマンドや関連ツールを実行していない。

## 実行案へ進むための具体的な不足

1. 対象版の公式付属help等で、履歴容量・収集時除外・設定の読込み完了・停止の正確な仕様を確認する。
   公開ページの例だけから未確認のCLI flagやconfig binaryを作らない。
2. 既存収集を利用/停止せず、今回の収集だけを識別・終了できることを確かめる。
   instanceの識別が不明なまま-terminateを発行しない。
3. child PIDは作成後に確定するため、suspended作成→PID照合/filter適用→収集準備確認→Resumeの順序を設計する。
   現行driverにはその待合せ処理がなく、追加接続には停止・資源・失敗時所有を含む試験が必要。
   この順序ではCreateProcess以前のeventが取得できない可能性も明示し、観測対象を混同しない。
4. 初期eventの上書きや欠落が起きたtraceを完全な原因解析記録と判定しない。
   データ上限到達・停止期限超過・drop不明を明示する結果項目が必要。
5. 親＋childに加え収集toolと関連driverの負荷を評価する。単なる定期メモリ照会は瞬間的超過を防ぐ上限ではない。

準備の次工程は付属helpを実行せず読める形で確認すること。資料の取得と実行は区別する。
それでも資源・所有・証跡条件を満たす案を示せなければ、共有PC上の収集は提案せず、
別環境や別方式に必要な条件を具体化して判断を求める。未完成のまま同じ限定probeを再実行しない。

今回は文書変更のみで、test再実行や独立レビューの再委譲は省略した。
開始時の空きRAM8.22 GiB/C102.24 GiB/D75.36 GiB。PC全体の単発値からリーク有無を判定しない。

## 現行公式配布物の非実行調査（2026-09-10）

[公式配布ページ](https://learn.microsoft.com/en-us/sysinternals/downloads/procmon)が案内する
https://download.sysinternals.com/files/ProcessMonitor.zip をHTTPSで取得し、redirect先不変・各取得4 MiB以下を確認した。
実ZIPは3,191,035 bytes。取得時SHA-256:

`4ff309fe52c56599377896b7863cb77b6c601d9f2522e52da7a182eac593e8e1`

ZIP内の4項目はProcmon.exe（4,247,832 bytes）、Procmon64.exe（2,232,136 bytes）、
Procmon64a.exe（2,316,576 bytes）、Eula.txt（7,490 bytes）。CHM/HTMLの独立helpは同梱されていなかった。
最初のCHM存在検査で想定との差を検出し、取得を2回追加して目録と静的文字列を確認した。
合計転送は9,573,105 bytes。後の取得は上記hash一致を確認した。ZIP自体やexeはdiskへ保存していない。

Procmon64.exeをメモリ内のbytesとして読み、UTF-16LEの印字可能文字列から関連説明のみ抽出した。
PEをload/executeせず、DLLロード・アプリ起動・help UI起動・driver/service/registry操作もない。
調べたexe bytesのSHA-256:

`78d7148ef5e1472bbcec02cfd655f5aa789006b65d9990862dd8546ecf6c9af1`

公式ページはv4.1表記だが、exeのversion resourceや署名はこの調査では別途検証していない。
取得元とhashによる記録であり、署名検証済みや実動作確認済みとは表現しない。

### 静的説明で新たに確認できた点

- /Terminateの説明は「Terminate all instances of ProcMon and exit」。対象所有instanceだけの停止ではない。
- /Runtimeは指定秒数後に終了する説明。入力エラー用文字列には1〜3600秒の範囲が示されている。
- /WaitForIdle、/LoadConfig、/BackingFileの名称と関連説明が含まれる。
- History Depth、Drop Filtered EventsのUI文字列があり、履歴の総event数を制限する説明も含まれる。

これらは埋込みテキストの存在確認であり、実際のCLI構文・config適用・終了対象・時間精度・資源動作を試験したものではない。
特に/Runtimeをhard deadlineとしたり、/WaitForIdleを対象PID filter適用完了の保証としたりしない。
古いevent数ベースの説明と前節のsize/time機能を、同じ意味の厳密なbyte上限とみなさない。

ローカル保存は隔離worktreeのartifacts/procmon-help-2026-09-10内に限定し、
acquisition.json（500 bytes）、embedded-text.json（1,774 bytes）、Eula.txt（7,490 bytes）の合計9,764 bytes。
artifactsはGit対象外。EULAを保存したことはアプリ上のaccept操作を行ったことを意味しない。
配布物中のファイル名をそのまま任意pathへ展開せず、root直下の小さい文書だけに限定した。

## この調査を受けた判断

前節の「停止対象が不明」は、少なくとも/Terminateの文書化された対象が全instanceだと判明した。
したがって、他作業の収集を停止しないという条件の下で、単純な/Terminateを自動停止処理へ組み込まない。
これは現在他のProcmonが稼働しているという認定ではない。今回はprocess一覧や他作業の収集状態を調べていない。

本PCでのProcmon案には、使用中instanceとの排他・起動後の所有・自動終了の対象範囲・全体資源・
初期event保持の実動作確認が依然必要。付属CHMを探すだけの調査はここで完了し、同じ配布物を再取得しない。
次の準備では、既存debugger方式の停止条件を維持できる追加観測と、条件変更が必要な方式を比較する。
実動作検証が必要になった時点で、その具体的範囲を提示する。未確認のCLI/configで共有PCの収集を始めない。

今回の変更は文書だけでtest再実行・レビュー再委譲なし。追加child・Procmon実行・設定変更はない。
開始時空きRAM8.34 GiB、終了付近8.22 GiB。C102.24 GiB/D75.36 GiBは同値。
短命の資料取得processは終了済み。単発のPC全体値でリーク有無を判定しない。

## 次工程の選択（2026-09-10）

[最初のunload通知中の実行状態取得案](anomaly-multiseed-v0.3-s4-b1-unload-context-plan-2026-09-10.md)を
次の実装準備対象に選んだ。通常debug通知ですでに停止している初期threadからcontextと最大2 KiBのstackを
各1回取得し、既存の全breakpoint拒否とowned stopを維持する設計である。
別の監視processやsystem-wide収集を追加せず、source/evidence/resource管理を既存adapterへ接続できる。
ただし新しいchildメモリ読取りを含むため、実行は実装・試験・レビュー後の別判断とする。
独立設計レビューは新規P0〜P3=0。collectorは未実装。得られるのは通知時点の状態で、失敗APIやcall stackの確定ではない。
Procmonは現在の自動実行案には採用せず、既存の調査結果を保持する。

## 実装準備の完了

unload時context/stack collectorはc4fe99eで接続済み。pure/fake243件、独立実装レビュー、18 sourceの実read-only preflightを通過した。
追加private枠は8 KiB、全体64 KiBを維持。次の判断対象は[unload観測計画末尾](anomaly-multiseed-v0.3-s4-b1-unload-context-plan-2026-09-10.md)の実機診断1回。
追加実機診断は未承認・未実行。以前の未実装という記述は当時の履歴として保持する。
