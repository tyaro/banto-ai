# 保存済み工程から続ける単一の報告実行入口

`src/banto_ai/anomaly_v03_saved_report_pipeline.py` の `run_pipeline` は、呼出し側が指定した保存済み工程から残りだけを進める。元の観測・score・ledgerの再計算、新評価、正式gateを起動しない。

```python
result = run_pipeline(request, output_parent=existing_parent, output_name="new-attempt")
```

requestの共通キーは `format="anomaly-v03-saved-report-pipeline-request-v1"`、`mode`、`start_from`、`inputs`。modeはfixtureまたはengineeringに限定する。入力のpinは信頼する過去の保存点から別途渡す。入力そのものから採ったhashを真正性の根拠にしない。

| start_from | inputs | 新たに実行する工程 |
| --- | --- | --- |
| summaries | binding、順番通り120個のsummaries、schema | 記述集計→報告準備→保存・読取り |
| tables | tables、schema | 報告準備→保存・読取り |
| report | directory、payload_pins（正確な4件） | 保存・読取り |
| publication | directory、result_pin | 過去の完了記録と現在の保存bytesの照合だけ。process起動0 |

binding/tables/schemaと各summaryは `{path: absolute_path, pin: {bytes, sha256}}`。reportのdirectoryには固定4payload、publicationのdirectoryには既存のresult.jsonとpublished/が必要。保存記録中のsource_lineage内のパスは開かない。各stageのinputs集合は厳密に固定し、複数の開始位置や足りないsummaryを黙って補わない。

## 集計・報告・保存

120要約からは既存のaggregate_bound_summariesを1回呼ぶ。bindingと全summaryの外部pin、区間順序、最新attempt、登録ID、全720枠を既存validatorで確認する。dev8seedとsmoke2seedを分離し、null・判定不能・旧失敗履歴を保持する。

集計表からはprepare_bound_reportを1回呼び、JSON/Markdown/HTML/receiptを準備する。新たに作ったpayloadのpinを既存publish_and_checkへ渡す。writer終了後readerを起動し、共有する全体budgetの停止も子監視へ伝える。今回既存publication moduleへの変更は任意のresource_budget引数とupstream引渡しの2行のみ。

publicationから始める場合、外部pin付きの成功記録についてmode、閉じた正式権限、資源pass、writer/reader終了記録、marker/payload/出典の対応を確認する。その後、現在保存されている4payloadとmarkerを既存reader関数で照合する。所有processは起動しない。過去のworker記録の再利用と今回のbytes照合を区別し、過去のPIDへアクセスしない。これは元評価やsource/runtime全依存の認証ではない。

## 保存点と失敗

毎回新しい出力ディレクトリを使用する。原本/sourceとの重複や包含、既存の試行先を拒否する。request.jsonとresult.json、resource-budget.jsonを保存し、完了した工程では次の開始位置を記した新しいrequestを残す。

- tables-checkpoint.json：作成済みtables.jsonと元schemaのpinを使う。
- report-checkpoint.json：作成済み4payloadのdirectoryとpinを使う。
- publication-checkpoint.json：完了したpublicationのdirectoryとresult pinを使う。

保存点のbytes/hashも結果に含む。失敗しても前の保存点を上書き・削除しない。呼出し側が保存点を明示して別名の試行を開始する。最後の工程まで既に終わっていれば、照合だけで完了する。

`aggregation_runs/report_runs/publication_runs` はそれぞれ既存入口の呼出回数で、worker実起動数や元評価件数ではない。失敗時の実起動はsupervisionで確認する。未回収workerは元の所有者を保持した例外で返し、unreaped.jsonを残す。資源停止では自動再試行・上限引上げを行わない。

## 資源と実行方法

全体120秒/親private512MiB/新規領域32MiB/256entries、RAMとcommit余裕各2GiB、disk余裕5GiB。入力はsummary群とbindingの合計32MiB以内、tables16MiB、schema1MiB、request128KiB。既存writer/readerは各30秒/512MiB/stdout等64KiB。純粋関数は段階ごとのcheckpointで制限を検知する方式であり、OSの強制quotaではない。

コマンド入口は `python -B -m banto_ai.anomaly_v03_saved_report_pipeline --request <absolute-json-path> --bytes <retained-size> --sha256 <retained-hash> --output-parent <existing-parent> --output-name <new-name>`。CLIもrequestの外部pinを必須とし、失敗時は終了コード2を返す。

架空の試験データを本物の検出性能として表示しない。正式欄null/formal_ready=false、正式許可・昇格・独立S6・trust・全source/runtime認証は従来どおり未完了。[今回の検証記録](results/anomaly-multiseed-v0.3-saved-report-pipeline-2026-10-03.md)。
