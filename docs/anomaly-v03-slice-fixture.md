# 架空40clusterの診断内訳を文書へ接続する

`anomaly_v03_slice_fixture`は、[文書草稿](anomaly-v03-document-fixture.md)へincident recallとscore availabilityを接続する純粋関数。[結果](results/anomaly-multiseed-v0.3-consumer-slice-fixture-2026-09-25.md)。[入出力契約案](anomaly-v03-consumer-io-proposal.md)のslice対応を架空入力で検査したもので、正式なmapping採択ではない。

## API

```python
from banto_ai.anomaly_v03_slice_fixture import (
    attach_fixture_slices, validate_connected_document,
)

connected = attach_fixture_slices(
    saved_fixture_document, original_fixture_input, invented_slice_input,
    frozen_analysis_schema,
)
check = validate_connected_document(
    connected, original_fixture_input, invented_slice_input,
    frozen_analysis_schema,
)
```

元の文書と入力のcanonical digestを対応づける。診断入力は`format=anomaly-v03-slice-fixture-input-v1`、`invented_only=true`、`clusters`の3項目だけ。clustersはinvented-00〜39の順に並ぶ。各clusterはcluster_id/candidates、各候補はcore/quality-stress、各cellは既存`slices.empty_counts()`と同じ整数counts・5秒分のdelay度数・設備contextを持つ。1cellは12-layout分。

通常のdev/smoke consumerや正式入口は変更しない。実データの読取・score生成・CI計算・公開・subprocess起動はない。呼出し側のinvented宣言とdigestは、入力の出自や登録runの認証ではない。

## 集計と対応の検査

既存のslice在庫・母数・参照除外・histogramの検査を再利用し、各clusterのincident recall、availability、precision、誤警報、delay全件、profile状態を元の架空入力へ対応づける。class×equipment×modeの結合表は各周辺表へ、signal×modeはtarget別表へ一致することも確認する。全体合計が変わらない行の入替えを検出するためである。

各candidate/stratumは40clusterのcountsと度数を加算し、overallはcore+stressから作る。比率や中央値を平均しない。9個の主指標表との件数・delay・profile対応を確認してから、既存の記述表mapperで行を出力する。主CIと180gateはそのまま保持する。

| 保存先 | 内容 | 行数 |
| --- | --- | ---: |
| document_draft.slices | 異常検出率48行＋信号利用可能率89行、各9表 | 1,233 |
| diagnostic_series | incident-recallと3種のscore系列を名前で分離 | 2,835 |
| diagnostic_details | 元counts・delay度数・profile件数・設備context・参照除外を保持 | 9表 |

本文はcandidate/stratum/dimension/keyが一意。閾値超過率と警報開始率を同じkeyで本文に追加しない。補助記録には4系列を全部保存する。

incidentの分母は予定正例。scoreの分母は予定された試験内のscore対象行で、利用不能行を含む。event-offsetのplanned_countには対象外・試験時間外の参照が含まれるため、分母と一致するとは限らない。この内訳をdiagnostic_detailsに残し、重複するoffset参照をscore全体の分割として足し合わせない。

補助sliceのCIはnot_evaluated、分母0ならnull/not_applicable。検出0のdelay要約はnull。整数秒の1〜5秒度数で処理し、非整数delayを勝手に丸めない。新しいslice gateや多重比較は追加しない。

## 到達範囲

出力identityは`anomaly-v03-document-with-slices-fixture-v1`。元のv1文書・入力や今回の入力は変更しない。slicesだけを接続し、status/provenance/analysis_consumer/bootstrapの4項目はnullを保つ。外側のformal/promotion/S6/trustはfalse、performanceはnot_evaluated、実selectedはnull。正式validatorは草稿を拒否する。

公開validatorは、渡された架空countsから集計と行対応を再確認する。CIは再計算しないが、独立実装による数値監査やraw観測からの診断導出を代替するものではない。

[診断入力](../artifacts/consumer-slice-fixture-2026-09-25/invented-slices.json)と[接続後の文書](../artifacts/consumer-slice-fixture-2026-09-25/document-with-slices.json)を保存している。次は現在のconsumerに必要なsource/runtime依存一覧と固定方法を更新し、正式実行前の残件・判断資料をまとめる。正式freezeやholdout実行は別工程。
