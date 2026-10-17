# 検証記録の容量・自動分割・失敗保存の改善（2026-10-12）

人の「実行側の制限は維持し、検証記録の容量制限を見直して、ログの自動分割と失敗時の証拠保存を改善」に従った工程です。
モデル評価、完成済み試験/CIの再実行、追加agent、固定root追記はありません。

## 変更

共通保存API tools/verification_records.pyと読取りCLI tools/check_verification_record.pyを追加。
新規検証rootを16MiB/512files、part256KiBへ変更。総量のうち2MiB/16filesを失敗保存用、さらに512KiB/4filesを終了manifest用に残します。
raw/JSONをbyte単位で自動分割し、順序・part/stream SHA256・complete/partialを保持します。
元の例外、未観測return null、返った終了コード、stdout/stderr、traceback、部分fileを保存。長いmessageの省略も明示します。
finallyにはwrite_terminalを使い、終了記録の保存失敗が元例外を隠すことを防ぎます。保存だけが失敗した正常処理も記録全体ではfailedです。
読取り検査の成功と元作業の成功を分け、failed/incompleteをそのまま表示します。

実行側900秒/2GiB/評価出力1GiB/評価file32MiB/files32、Git30秒/batch16entry・512KiB/stdout1MiB・stderr128KiBは不変。
計算・科学仕様の既存117pinsと固定v0.3計画bytesは不変。追加3sourceは検証記録専用で、declared calculator16の変更はありません。
固定archive/transport/schema/native gateには接続せず、formal_permission=false/credit0/holdout未読、正式5残件・最終受入未完了を維持します。

## 確認

新17distinct test methods、実body18。初回12件は11pass/error1。欠落fileを検査した時のfixture期待OSErrorに対し、実際はinventory不一致のValueErrorで早期拒否した。
原source・unittest log/summary・failed helper記録を最初の閉鎖rootへ保持し、実装の拒否を変更せずfixture期待だけ訂正した。
その失敗1件と新しい具体的risk2件を別source/runで確認し3pass。finally終了記録失敗の新risk2だけ2pass、長い例外messageの省略表示の新risk1だけ1pass。
完成11件や既存suiteは反復していない。複数source/runの結果であり、最終source単一17success runとは主張しない。

- 旧512KiB/32filesを超えるraw/JSONを分割し、binary・日本語/emoji・seed整数のbyte/値を保持。
- bytes/files枠の到達後も元例外・失敗終了コード・終了manifestを予備枠に保存。
- 保存障害・部分write・タイムアウトprefix・KeyboardInterrupt・元例外を飲み込んだ呼出しの誤successを確認。
- stdout1MiB超過は従来の実行制限違反としてfailed。記録枠が増えても解除しない。
- 途中closureはincomplete、閉鎖済みrootの追記・再利用拒否、part改変/欠落/追加の拒否を確認。
- 巨大tracebackが終了manifest枠を消費しないことを確認。

実CLIを別processで二件だけ起動。初回failed記録はrecord_integrity=passedかつrecorded_status=failed、最新記録はrecorded_status=completeを保持した。
stdout/stderr/returnは新共通APIで判定前に保存し、累積30秒と既存output上限を維持。元tests/model/CIの再実行ではない。

## 原記録

新formatのroot-closed.jsonとmanifest partsを参照。原source・script・creation identity・選択unittest log/summaryを保持します。process全stdioを捕捉した記録とはしません。

| root（artifacts/配下） | 原状態 |
| --- | --- |
| verification-recording-policy-20261012-tests | 初回12件・fixture期待error1を保持、failed |
| verification-recording-policy-20261012-tests-continuation | 失敗1＋新risk2だけ、passed |
| verification-recording-policy-20261012-terminal-tests | 新risk2だけ、passed |
| verification-recording-policy-20261012-message-test | 新risk1だけ、passed |
| verification-recording-policy-20261012-cli | 新reader CLI二件・原failed状態保持、passed |

今回のGit・最終確認はverification-recording-policy-20261012-saveとverification-recording-policy-20261012-finalを参照。
初回のerrorと全過去のfailed/unknown原証拠を後日のpassへ書き換えません。

## 次の使用

新しいengineering helperの検証記録はこの共通APIへ移行し、原実行制限とowner保持処理を継続します。既存閉鎖root内のscriptは変更しません。
次の未実施モデルunitは同保存layout6 quality C0の1cell。入力pin照合・新ID・fresh計算は従来どおりで、既存CLIと元datasetを変更しません。
仕様・使い方・保存保証の範囲は 検証記録の保存 を参照。
