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
