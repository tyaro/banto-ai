# 準備済み報告書のローカル保存と終了後の読取り

`src/banto_ai/anomaly_v03_bound_report_publication.py` の `publish_and_check` は、信頼する前回保存点から受け取った4ファイルの外部pinで、準備済み報告書を保存する。一つのwriterを起動・回収してから一つのreaderを起動する。報告書の作成・集計・評価は実行しない。

```python
result = publish_and_check(
    source_directory,
    expected_mode="fixture",
    expected_payload_pins=retained_pins,
    output_parent=existing_parent,
    output_name="new-attempt",
)
```

呼出側は信頼する過去の保存点から `{bytes, sha256}` を渡す。入力自身から採ったpinを認証根拠にしない。`report.json`、`report.md`、`report.html`、`consumer-receipt.json` の正確な4件が必要。元ディレクトリ内の他ファイルやsource_lineageの参照先は開かない。

## 処理と保持する情報

1. `fixture` / `engineering` と4件のpin形状をIO前に確認する。正式mode、boolサイズ、上限超過を拒否する。
2. 新しい出力ディレクトリを排他的に作成する。既存・途中失敗のディレクトリは再利用しない。原本や実装srcとの包含・重複を拒否する。
3. writerが固定4ファイルをpin/上限付きで読み、receiptと報告JSONのmode・出典・正式欄・未充足状態の一致を確認して保存する。既存のLocalPublicationを使い、完了markerを最後に作る。
4. writerのexit0・終了確認・監視エラーなしを確認する。監視失敗や応答喪失ならreaderを開始しない。
5. readerは保存済み4ファイルと2個のmarkerだけを確認する。外部payload pinとwriterから得たmarker pinを用い、出典とfixture表示を保持する。原本・元評価・mapperは読まない/起動しない。
6. readerの終了とwriter/readerの出典pin一致を確認し、結果・監視記録を保存する。

`published/payload/` に元と同一の4ファイルを保存し、writer/readerのrequest、stdout、supervision、結果は隣接する別ディレクトリへ残す。旧receiptのpublished=falseは「準備段階で未公開だった」履歴であり書き換えない。今回の保存状態は外側のpublication_statusで表す。

| 状態 | 意味 |
| --- | --- |
| publication_status=completed | writerの完了応答と終了を確認 |
| publication_status=unconfirmed | writer起動以降に確認失敗。marker有無を推定しない |
| reader_status=not_started | writer未確認等によりreaderを未起動 |
| reader_status=unconfirmed | 読取り開始後に確認失敗 |
| status=verified | 直列writer/readerと資源確認が成功 |

失敗しても保存済みファイル・markerを削除しない。workerを回収できなければ元の所有ハンドルを持つUnreapedWorkerを呼出側へ返し、unreaped.jsonを保全する。再試行は新しい試行名と、別途保持した外部pinが必要。

各worker30秒/512MiB/出力64KiB、全体120秒/parent512MiB/新規領域32MiB、commit/RAM余裕各2GiB、disk余裕5GiBを監視。サンプリング上限でありOSの強制quotaではない。自分が起動したprocessのみを管理する。

今回は通常の単一writerと終了後reader。別principal・同時改変耐性・数値の独立監査・全source/runtime依存の認証は主張しない。小さい試験fixtureは保存契約の確認用で、数値の妥当性はこのAPIの検査範囲外。

[今回の試験と保存例](results/anomaly-multiseed-v0.3-bound-report-publication-2026-10-03.md)。
