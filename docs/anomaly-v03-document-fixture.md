# 40-cluster推論と結果文書の架空入力adapter

`anomaly_v03_document_fixture` は、40個の非登録・架空クラスタを既存の推論/表adapterへ接続し、正式analysis schemaの10項目に対応する文書草稿を作る純粋関数。[試験結果](results/anomaly-multiseed-v0.3-consumer-document-fixture-2026-09-25.md)。ファイル操作・評価起動・公開・実runtime検査は行わない。

## 呼出し

```python
from banto_ai.anomaly_v03_document_fixture import (
    build_fixture_document, validate_fixture_document,
)

result = build_fixture_document(invented_input, frozen_analysis_schema)
check = validate_fixture_document(result, frozen_analysis_schema)
```

入力は次の6項目だけを持つJSON値。既存のengineering consumer、実dev/smoke入力、正式consumer入口は変更していない。

| 項目 | 条件 |
| --- | --- |
| format | anomaly-v03-document-fixture-input-v1 |
| invented_only | true。呼出し側の架空入力宣言で、データ起源の認証ではない |
| clusters | invented-00〜invented-39の順序、40個固定。各候補×core/stress、12-layout相当のcounts/profile |
| diagnostics | 同じcluster/candidate/stratum順、実効clean秒と因果検出された全delay |
| draws | 1〜64行、各40個の整数index（0〜39）。bool/float・欠落・上限超過を拒否 |
| engineering_ready_assumption | bool。架空の試験条件であり、実工程の受入とは別 |

clusterの中身は既存`anomaly_v03_analysis_adapter`と同じ。planned denominator、候補間pairing、precision/incident/false episodeの件数関係、delay件数/範囲を計算前に確認する。role/seed/path等の別入力項目や不正inventoryを受け付けない。渡されたschemaは既存contractが生成する固定schemaと一致する必要がある。

1本のdrawを全候補・core/stressに共通適用する。overallは元countsの和で計算し、候補差の区間推定は同じdrawでの差から求める。既存推論の算術・閾値・C1優先選択は変更していない。50,000回を宣言する正式bootstrap欄を小さい試算で埋めない。

## 文書への対応

出力identityは`anomaly-v03-document-fixture-v1`。入力canonical digest、実際のdraw全行、既存fixture packet、document_draft、10項目のfield_coverageを保持する。入力/schemaは変更せず、出力内のdraftとpacketも別の値を持つ。

| document_draftの項目 | 今回の扱い |
| --- | --- |
| schema_version / result_type | 固定schemaの識別値。草稿内だけに配置 |
| candidate_tables | 架空40clusterから9表・180gateを組立て |
| selected_candidate / decision | 架空試験の選択・判定。実際の採択ではない |
| status | null。正式runとengineering受入の証拠が未提示 |
| provenance | null。正式producerと公開inventoryが未提示 |
| analysis_consumer | null。clean source/runtimeの受入が未提示 |
| bootstrap | null。登録holdoutでの50,000回推論は未実施 |
| slices | null。正式sliceの全inventory・導出接続が未完了 |

未充足の5項目を空配列や架空のhash/revisionで補わない。草稿単体も正式validatorには通らない。外側のselected_candidateは常にnull、performanceはnot_evaluated、formal/promotion/S6/trust等はfalse、計上評価は0。fixture側のqualifiedを実際の採択へ読み替えない。

`validate_fixture_document`は表の既存検証とdraft/packet/各閉鎖flagの対応を確認する。CIを再計算しない。input digestは参照値であり、保存点/登録runの認証や、入力からの独立数値監査ではない。

## 保存例と残り

[架空入力](../artifacts/consumer-document-fixture-2026-09-25/invented-input.json)と[文書草稿を含む出力](../artifacts/consumer-document-fixture-2026-09-25/document-fixture.json)を保存。例は4draw/160indexのみ。入力は前半と後半で検出数が異なり、候補間のpaired CIと集約delayを確認できる。

次は架空の診断入力からincident recall/availabilityの正式slice行を組み立て、草稿のslicesへ接続する。正式source/runtime受入、運用契約採択、予算、正式推論・独立auditと公開は引き続き別の残件。今回の5未充足項目はプロジェクト全体の残件数ではない。
