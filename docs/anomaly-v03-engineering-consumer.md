# 保存済み記述結果のengineering consumer

2026-09-25追記：[別process readerと外側receipt](anomaly-v03-consumer-reader.md)を接続済み。writer終了後、独立に保持したmarker/保存点pinで確認し、不一致や応答消失を別directoryへ記録する。本APIの既存inline readerはそのまま保持する。

2026-09-25追記：[契約案への対応・残件と容量時間見積り](results/anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)を保存。次はwriter終了後の別process readerと外側の確認receiptを通常権限で接続する。現APIのlocal_verifiedは同一processの読取確認である。

`anomaly_v03_engineering_consumer` は、認証済みの[集計入力結合receipt](anomaly-v03-consumer-analysis-binding.md)から、同じ入力で作られた記述レポートを選び、新しい保存先へ出力する。既存の数値検証を再利用し、集計・比率・観測・スコアを再計算しない。[実接続結果](results/anomaly-multiseed-v0.3-engineering-consumer-entry-2026-09-25.md)。

## APIとCLI

```python
from banto_ai.anomaly_v03_engineering_consumer import run_engineering_consumer

result = run_engineering_consumer(
    binding_savepoint, report_savepoint, analysis_input,
    expected_mode="engineering-dev-smoke",
    expected_binding_pin=retained_binding_pin,
    expected_report_pin=retained_report_pin,
    output_parent=existing_output_parent,
    output_name="new-descriptive-result",
)
```

両pinは外部で保持した `{bytes, sha256}`。入力は結合保存点、記述レポート保存点、元analysis-inputs.jsonの3つを明示指定する。`prepare_engineering_result` は同じ認証を行い、保存前の4payloadとreceiptを返す。

PowerShellでは作業checkoutで `PYTHONPATH=src` を設定し、下記の1コマンドを実行できる。placeholderは保持したpath/pinへ置き換える。output-parentは既存directory、output-nameは未使用の名前が必要。

```powershell
$env:PYTHONPATH='src'
C:/Python314/python.exe -B -m banto_ai.anomaly_v03_engineering_consumer --mode engineering-dev-smoke --binding-savepoint BINDING_SAVEPOINT --binding-bytes BINDING_BYTES --binding-sha256 BINDING_SHA256 --report-savepoint REPORT_SAVEPOINT --report-bytes REPORT_BYTES --report-sha256 REPORT_SHA256 --analysis-input ANALYSIS_INPUT --output-parent EXISTING_PARENT --output-name NEW_NAME
```

成功時はstdoutに保存先、外部保持用marker hash、receipt pin、読み戻し確認結果をJSONで返す。入口での拒否はexit 2。formal/未知modeはファイル参照前に拒否する。

## 読取りと対応検査

2保存点・結合receipt・明示集計入力・report.json/md/htmlの7ファイルだけを各1回認証する。ファイル別の上限合計は18MiB。保存済み記録内のpathは比較専用で、そこから別ファイルを開かない。schemaやcampaign payloadへもアクセスしない。

同じcampaign closed pin、同じanalysis保存点pin、同じanalysis-inputs.jsonのraw pin、dev8/smoke2・576/144評価の対応を確認する。別入力の報告、改変、認証範囲の格上げを拒否する。元analysisの大きなJSONはhash照合のみで、解析もコピーもしない。

元レポートのcell/schema検証は保存点から再利用する。JSONは既存writerのcanonical UTF-8/LF形式に直すが、decoded値を変えない。Markdown/HTMLはUTF-8/LF本文を保持し、末尾LFだけ不足時に補う。元ファイルpinと出力pinの両方をreceiptに残す。

## 保存と読取り

既存LocalPublicationを使い、通常権限の単一writerで専用directoryへ保存する。`payload/`にはreport.json、report.md、report.html、consumer-receipt.json。完全なinventory照合後に`.complete`を作り、writerを閉じてから既存readerでmarker・inventory・全出力bytesを照合する。保存点を更新する用途や再開機能はなく、既存directoryを上書きしない。途中失敗はそのまま保全し、別の未使用名で再実行する。

`local_verified=true` はこの結果保存の読み戻し確認。過去の公開・集計・診断・cell検証は `historical_*_reused=true`。現在の全payload、controllerプロセス終了、source/runtime受入、trust、analysis/execution/formal/promotion/S6へ格上げしない。bootstrapなし、performance/decision未実施、selected_candidate=null。readinessは元レポート作成時点の文脈を保持する。

正式運用契約はdraft。新規評価・正式gate・holdout・source/runtime freezeはこの入口に含まれない。
