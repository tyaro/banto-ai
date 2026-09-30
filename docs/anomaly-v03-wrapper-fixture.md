# 架空入力による5出力と実行記録の結合

`anomaly_v03_wrapper_fixture` は、既存の文書/slice草稿と供給された架空のanalysis記録を、予定5payloadへ対応付ける純粋関数である。ファイルを開かず、process・観測生成・推論・公開を起動しない。[実装](../src/banto_ai/anomaly_v03_wrapper_fixture.py)、[試験](../tests/test_anomaly_v03_wrapper_fixture.py)、[保存結果](results/anomaly-multiseed-v0.3-wrapper-fixture-2026-09-30.md)。

## 入力と保持すべき期待値

`assemble_fixture_wrapper(request, schema, *, expected_mode, expected_revision, expected_input_pins, analysis_record=None, expected_analysis=None, source_snapshots=None, runtime_snapshots=None)` を使う。

requestはformat・mode・invented_only・fixture_input・slice_input・coverage・documentを持つ。modeはfixtureだけを受け付け、engineering-dev-smoke/正式modeは入力へアクセスする前に拒否する。schemaは既存の固定analysis schema、documentは `attach_fixture_slices` の草稿かNone。登録データをfixtureと呼び替えて利用する入口ではない。

- expected_input_pinsは `fixture/input.json`、`fixture/slices.json`、`fixture/coverage.json`、`fixture/operation.json` のcanonical bytesを、呼出し側が別に保持したpin。operationは `operation_descriptor(expected_revision)` が返すfixture専用の `assemble-invented-document-v1`。
- analysis_recordは供給された証拠のraw bytes。expected_analysisは別に保持したevidence_pinとinvocationを持つ。invocationは既存のconsumer evidence validatorと同じprocess/source/runtime/input/output記録。供給証拠から期待値を自動抽出しない。
- source_snapshotsはrevisionに対応するbytesのMapping、runtime_snapshotsも供給bytesのMapping。記載pathをこの部品がopen/statすることはない。
- analysisのrole=analysis、mode=fixture、revision、4入力の完全一致を要求する。出力は `fixture/document.json` のcanonical bytesのみ。保存済み記述結果準備のoperation/inputやreader/audit役割を、この数値文書fixtureの証拠へ流用しない。

期待値の由来と独立保持は呼出し側の責任である。架空の証拠と架空の期待値が一致しても、実際の起動・実行認証・完全な依存固定・数値的独立性は証明しない。今回の供給記録は全て手作りで、記載したPID/pathでの実行はない。

## coverageと段階状態

coverageは40個の `invented-00`〜`invented-39`、3候補、core/quality-stress、12個のordered layout_idsを持つ。各候補/層の12枠はsuccess/inconclusive/partial/failed/not_startedのいずれか。計2,880枠の予定を保持し、失敗枠を削除しない。全枠が処理済みなら、各cluster/candidate/層のprofile状態とも対応を検査する。これは架空の宣言であり、正式producerの全slotを認証するadapterではない。

JSON objectのメンバー順は意味を持たない。従来のslice検査へ渡す診断count辞書は、この新adapterで固定template順へ整える。値・配列の順序・canonical input pinは変えず、保存後にキー順が変わっても同じ5payloadになる。

| 条件 | analysis段階 | 出力 |
| --- | --- | --- |
| 全枠success/inconclusive、文書と期待値/証拠が一致 | supplied_evidence_bound | 草稿と診断表、供給bytesの結合記録 |
| 全枠処理済みでも文書なし | not_supplied | coverageを保持、解析/診断の値はNone |
| partial/failed/not_startedを含む、文書なし | blocked_by_coverage | 全予定枠・失敗を保持、解析/診断の値はNone |
| 不完全coverageに完成文書を付ける | 拒否 | 完成結果を作らない |
| 文書なしでanalysis証拠だけを付ける | 拒否 | 未作成の解析を実行済みにしない |

inconclusiveは処理済みの科学的判定不能として残す。全枠処理済みでも性能合格・昇格へ変換しない。producerはfixture_declarations_only、writer/reader/auditはnot_runのまま。これらの役割の実記録は今回接続していない。

## 5payloadの対応

| 名前 | 内容 |
| --- | --- |
| execution.json | fixture operation、外部入力pin、analysis結合記録、役割別の段階状態 |
| coverage.json | 2,880枠の元宣言、状態別件数、完全性の集計 |
| analysis.json | 文書草稿、fixture draw/packet、fixture入力digest |
| diagnostics.json | 4系列の補助表と詳細9表、slice入力digest |
| verification.json | 検査範囲、不足欄、正式ready=false |

全payloadと外側にfixture専用format・mode・閉じた受入フラグを持つ。本文のstatus/provenance/analysis_consumer/bootstrapはNoneを維持する。文書そのものがない場合は10欄全てを不足として示す。fixture内の候補選択は草稿/packet内の練習用の値で、外側のselected_candidateはNone。

戻り値のpayload_pinsは全5payloadのcanonical bytesから作り、payloadの外へ保持する。markerや公開receiptは生成せず、verificationに自分のhashを埋める循環参照も作らない。テストharnessが保存したファイルは検証例であり、通常公開や正式結果ではない。

`validate_fixture_wrapper(value, request, schema, **expected)` は保持入力から同じ対応を組み立て、全payload/pinと比較する。改変後のpayloadだけを再封印しても一致しない。文書/sliceの既存validatorで対応を再検査するが、CIを再計算しない。

## 次の接続

この部品はT09/T10の架空の結合確認まで。次は、小さい架空入力を実際に数値計算する所有workerと、呼出し側が起動前に保持する期待値を接続する。保存済み結果準備用のanalysis operationとは区別し、全50,000反復へ拡張しない。その後、独立した数値auditの入口と全体の資源停止条件を揃える。正式契約・実holdout・freeze・S4/S6完了は引き続き対象外。
