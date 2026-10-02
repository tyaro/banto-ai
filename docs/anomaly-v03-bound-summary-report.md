# 結合済み記述集計表から報告payloadを準備するAPI

`src/banto_ai/anomaly_v03_bound_summary_report.py` の `prepare_bound_report` は、外部pinで固定した集計表とschemaのbytesから4ファイルのbytesと準備receiptを返す。ファイルを開く処理や公開処理は含まない。

```python
files, receipt = prepare_bound_report(
    tables_raw, schema_raw,
    expected_tables_pin=tables_pin,
    expected_schema_pin=schema_pin,
    expected_mode="fixture",
)
```

呼出側は信頼する保存点から `{bytes, sha256}` の期待pinを別途渡す。入力自身からpinを採って真正性を主張してはならない。`fixture` と `engineering` のみを扱い、正式modeはdecode前に拒否する。集計表は16MiB以下、schemaは1MiB以下。全120区間/720枠を覆う既存の完了集計表が前提で、今回の数値検算や元payload認証を代行しない。

## 出力と表示

| ファイル | 内容 | 最大サイズ |
| --- | --- | --- |
| report.json | 2cohort、18候補表、234主指標、5,670診断項目、出典・判定不能・失敗履歴 | 4MiB |
| report.md | 主指標の概要、定義、詳細へのリンク | 1MiB |
| report.html | 条件別の折り畳み表示、18details/54tables | 2MiB |
| consumer-receipt.json | 入力pin、出典、前3ファイルのpin、変換の記録 | 1MiB |

合計8MiB以下、UTF-8/LF、末尾改行あり。出力ファイル集合は固定で、途中失敗やサイズ超過時は部分payloadを返さない。receipt自身のpinは呼出側の保存点に記録する。

既存の報告書mapperを1回呼び、mapper内の数値とschema部品の対応検査を1回行う。再集計・再結合・detector再計算・ledger再計算は0。dev8seedとsmoke2seedは分離し、0/0と空の遅延中央値はnullを維持する。条件別診断を独立標本や追加評価として数えない。

`fixture` ではMarkdown/HTMLの表題に「架空データ」を付け、架空要約720枠であり実際の検出性能ではないことを明記する。`engineering` の表示経路も試験したが、今回実データを接続したことにはならない。どちらも判定不能を含む評価件数を表示する。

`source_lineage` に表/schemaの外部pin、binding、metadata、journal、completed savepoint、evidence、全120要約の参照、coverage、旧失敗履歴、分母ゼロ件数を保存する。参照先は不透明な履歴として扱い、現在のファイルを開かない。旧mapper向けの内部形式は保存・公開せず、実行認証の証拠にはしない。

正式の `status/provenance/analysis_consumer/bootstrap` はnull、ready=false、decision=not_evaluated。公開・独立数値監査・正式schema検証はfalse。既存dev/smoke報告formatに出典とmodeを追加し、新receiptは `anomaly-v03-bound-summary-report-receipt-v1` を使う。

## 今回の確認と次工程

[試験・保存例の記録](results/anomaly-multiseed-v0.3-bound-summary-report-2026-10-03.md)。通常のローカル保存への接続は次工程。呼出側が資源上限と保存を管理し、writer終了後にreaderを実行する。今回の4payloadを再生成せず再利用し、新しい出典・mode・未充足の正式欄を保持する。
