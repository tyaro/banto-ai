# consumerの実行証拠と入出力bytesを結ぶ検証部品

2026-09-25接続追記：[実観測reader API](anomaly-v03-reader-evidence.md)を追加し、実際の子processと元handleの記録を本validatorへ接続した。期待値は親が起動前/起動時に保持する。以下の純粋関数自体は引き続き採取/起動を行わず、formal/full closureはfalse。[結果](results/anomaly-multiseed-v0.3-reader-observed-evidence-2026-09-25.md)。

2026-09-25、実装 `c79fc9e5db7d486a22c2ed4b5f5e75ca0027f7a0`。[試験結果](results/anomaly-multiseed-v0.3-consumer-execution-evidence-2026-09-25.md)、[source/runtime計画](anomaly-v03-consumer-source-runtime-plan.md)。`anomaly_v03_consumer_evidence.validate_execution_evidence`は、外部に保持した期待値と、渡された証拠・source/runtime・入出力bytesの対応を検査する純粋関数。実process観測の採取や正式受入は行わない。

## APIと信頼する起点

```python
checked = validate_execution_evidence(
    evidence_raw,
    expected_mode="fixture",  # or engineering-dev-smoke
    expected_role="reader",  # analysis, audit, reader
    expected_pin=retained_evidence_pin,
    expected=retained_invocation,
    source_snapshots=revision_scoped_source_bytes,
    runtime_snapshots=runtime_file_bytes,
    input_snapshots=input_file_bytes,
    output_snapshots=output_file_bytes,
)
```

`expected_pin`は外部保持した証拠raw bytesの`{bytes, sha256}`。`expected`は呼出し側の計画・起動記録から保持し、検査対象の証拠から期待値を自動生成しない。full revisionのsource snapshot、processのPID/生成を区別するstart_token、実際のruntime観測も呼出し側が取得する必要がある。期待値まで偽造・差し替えた束の実行真正性を、この関数だけで判定することはできない。

`expected`は次の6欄を厳密に持つ。

| 欄 | 対応する情報 |
| --- | --- |
| invocation_id | 呼出し側が保持する64桁hexの実行識別子 |
| source | full revisionと、並び順・重複なしのpath/raw_sha256/byte_count一覧。既存source descriptor形式 |
| process | pid、parent_pid、start_token、argv、cwd。PID再利用はtokenとの組で区別 |
| runtime | platform、python、startup、files。記録は子の観測として呼出し側で対応づける |
| inputs | logical pathからbytes/SHA256への対応表 |
| outputs | 同じ形式の出力対応表。実際に渡された出力bytesも照合 |

source snapshotは`{revision: {path: bytes}}`。他snapshotはlogical pathからbytesへのMapping。過不足を拒否し、全列挙fileのサイズとSHA256を照合する。lazy Mappingにも対応し、この関数内では1fileずつ参照する。Mapping自体の取得・I/O・真偽は信頼した呼出し側の責務。

## 証拠の形と拒否条件

証拠formatは`anomaly-v03-consumer-execution-evidence-v1`。mode・role・invocation_id・process・inputs・outputsに加え、source_before/source_after、runtime_before/runtime_after、completionを持つ。余分な自己申告pass/正式完了欄や未知欄を受理しない。

前後source/runtimeを同じ外部期待値に照合し、completionはcompleted・exit_code整数0・worker_exit_confirmed真・observation_errors空だけを受理する。未終了、異常終了、監視欠落は拒否。プロセスIDと親IDが同じ場合も拒否する。

この初期profileはWindows/AMD64・CPython3.14.0、`-I -S -B`起動を対象とする。実機の全platformを受入済みという意味ではない。OS build/UBRは外部期待値に実値を保持し、実行間の更新は表現できるが同一実行内の前後差は拒否する。旧formal pinは変更しない。

runtime.startupは6起動flag、明示されたsys_path、site_imported=false、hooks空を持つ。system/user siteの検索先、同一検索pathのcase別名、危険なpath表記を拒否する。runtime.filesはlogical pathごとのphysical_path/category/pinで、python/executableとpython/shared-libraryは必須。stdlib/extension/native/toolも指定分を照合できるが、一覧の完全性を証明するものではない。argvのPython pathとruntimeの実行fileを対応づける。

実fileの解決・リンク・ACL検査は行わず、pathは文字列としてのみ検証。sourceはraw bytesで比較し、CRLF/LFを正規化しない。証拠JSONは重複key/非有限数/不正UTF-8を拒否、parse前に1MiB上限を確認する。これらは構造の上限であり、評価実行の容量・時間予算を変更しない。

## 戻り値と未完了範囲

成功は`status=supplied_consumer_evidence_bound`、scopeはsupplied-bytes-only。外部pin、source descriptor、input/output pinを独立copyとして返す。正式許可・昇格・S6・結果信頼・実行認証・source/runtime閉包はすべてfalse、性能判定はnot_evaluated、selected_candidate=nullを維持する。

既存の正式schemaやdocument_draft.analysis_consumer=nullは変更しない。inspection receiptや通常readerをこの新APIへ自動接続したものでもない。通常権限readerの実際の起動観測と外側で保持した期待値を、このvalidatorへ接続する。最初は既存の小さな架空公開結果で確認し、親の観測値を子の値として流用しない。 完全runtime closure、正式consumer・独立audit・予算採択は別の残件。
