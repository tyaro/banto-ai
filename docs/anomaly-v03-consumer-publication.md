# consumerの公開・終了記録reader

`anomaly_v03_consumer_publication.read_chunk_publication` は、[checkpoint adapter](anomaly-v03-consumer-checkpoints.md)で選択した最終attemptについて、公開印・manifest・終了監視記録を固定hashで照合する。単一writerが書込みを終えた後に使う、読取専用API。[確認結果](results/anomaly-multiseed-v0.3-consumer-publication-reader-2026-09-25.md)。

```python
from banto_ai.anomaly_v03_consumer_publication import read_chunk_publication

report = read_chunk_publication(
    run_root, plan, adapted,
    expected_mode="engineering-dev-smoke",
    expected_adapter_sha256=retained_adapter_canonical_hash,
    chunk_index=119,
    closed_sequence=10,
    expected_closed_sha256=retained_closed_raw_hash,
)
```

`run_root` はcampaignの `run/` ディレクトリ。planとadaptedはdecoded値。adapter hashは検証済み出力を呼出し側が保持したcanonical hash、closed hashは同じcampaignの外部保存点に残したraw hash。読み込んだ値自身を期待値にしても認証にならない。

## 読み取る範囲

formal/未知mode、区間・終了記録番号の不正、adapter hash不一致をファイルアクセス前に拒否。planは既存固定契約とadapterのplan hashへ結合する。各区間で以下の8管理ファイルを1回ずつ読み、合計上限は1,040KiB。

| 管理記録 | 認証する参照 | 上限 |
| --- | --- | --- |
| controllerのclosed.json | 外部raw hash、completed、journalのplan/count/head、全最終descriptorの在庫、metadata root | 64KiB |
| 選択attemptのterminal journal record | adapterが保持したrecord hash、canonical framing、attempt/context/evidence | 16KiB |
| attempt descriptor | closedが保持したhash、既存descriptor契約、固定path/role/identity/outcome | 64KiB |
| .complete | journal/descriptorのhash、local marker形式、inventoryの閉じた欄・順序・hash | 256KiB |
| marker-pending.json | .completeと同じbytes・同じファイルidentity・各link数2 | 256KiB |
| payload/manifest.json | markerのraw/canonical hash・row count、adapterのmanifest hash、既存manifest契約 | 256KiB |
| producer-control/supervision.json | descriptorのhash/bytes、選択binding、正常終了、worker回収、同一runtime、資源上限 | 64KiB |
| audit/supervision.json | descriptorのhash/bytes、正常終了、worker回収、runtime、監査出力pin、stderr・資源上限 | 64KiB |

読取前にサイズと各ancestorを検査し、最大サイズ＋1bytesまで読む。前後のfile identity/size/mtimeと期待hashを確認。通常payloadやcontrolの多重link、symlink/junction/reparse、`..`を拒否する。公開印の2本だけ既存のhardlink方式を許し、同じ内容の別fileへの置換も拒否する。読み込んだ記録内の任意pathは辿らず、固定名を組み立てる。

manifest内のdataset/evaluation参照はmarker inventoryのraw hashと一致させる。adapterの6slotとも照合するが、dataset/evaluation本文は開かない。公開rootの3項目だけ確認し、payload全体の再帰走査やhash再計算はしない。既存publication verifierの全payload再読取りやscore auditは呼ばない。

## 戻り値の範囲

`publication_metadata_verified`、`manifest_bytes_verified`、`worker_exit_records_verified`、`controller_closure_record_verified` がtrueになる。これは各区間の管理記録の認証である。

`full_payload_bytes_verified`、`audit_report_bytes_verified`、全体の `publication_verified` はfalse。controllerのclosedは、終了前に保存される処理完了記録であり、OSプロセスそのものの終了証拠ではないため `controller_process_exit_verified=false`。workerについても過去の終了監視記録を照合した意味で、今回プロセスを起動・監視したわけではない。

source/runtime正式受入、trust、execution/analysis/formal/promotion/S6はfalse、performance未実施、selected_candidate=null。敵対的同時書換えへのprincipal分離保証は追加しない。既存の保留試験やwriterは起動しない。

次は既存の独立監査済み集計入力と、この公開metadataの参照対応を固定する。旧保存点の検証履歴を再利用する場合はその導出関係を明記し、観測/scoreの再計算や、payload全体を新規認証したという扱いを避ける。

2026-09-25追記：[監査済み集計入力との結合](anomaly-v03-consumer-analysis-binding.md)を実装。14新規試験と全120区間の導出対応を確認済み。公開readerのflagsは変更せず、旧算術/診断検証の再利用を別receiptに明示する。
