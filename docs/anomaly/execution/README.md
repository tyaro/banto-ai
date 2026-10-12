# 実行・入力・保存の設計

consumer、reader、入力対応、実行記録、報告保存とcampaign。

[文書の入口](../../README.md) · [最新の引継ぎ](../../current-handoff.md)

## 文書

- [検証記録の自動分割と失敗時の証拠保存](verification-records.md)
- [保存済み記述結果を準備するanalysis役割の実観測](anomaly-v03-analysis-evidence.md)
- [解析の保存出力を通常公開し、別readerで確認する](anomaly-v03-analysis-publication.md)
- [準備済み報告書のローカル保存と終了後の読取り](anomaly-v03-bound-report-publication.md)
- [監査済み集計入力と公開記録の結合](anomaly-v03-consumer-analysis-binding.md)
- [保存済みcheckpointからconsumerへのmetadata変換](anomaly-v03-consumer-checkpoints.md)
- [consumerの実行証拠と入出力bytesを結ぶ検証部品](anomaly-v03-consumer-evidence.md)
- [consumer入力宣言の検査](anomaly-v03-consumer-input.md)
- [単一writer方針での解析consumer入出力契約案](anomaly-v03-consumer-io-proposal.md)
- [consumerの公開・終了記録reader](anomaly-v03-consumer-publication.md)
- [engineering結果の別process readerと外側の確認記録](anomaly-v03-consumer-reader.md)
- [consumerのsource/runtime固定対象と実行前の残件](anomaly-v03-consumer-source-runtime-plan.md)
- [保存済み記述結果のengineering consumer](anomaly-v03-engineering-consumer.md)
- [保存済み観測データのローカルスコア計算](anomaly-v03-local-preview.md)
- [通常権限での結果保存](anomaly-v03-local-publication.md)
- [架空480区間のproducer/campaign由来anchor案 v1（未採択）](anomaly-v03-preformal-campaign-anchor-proposal-v1.md)
- [架空campaign controllerの次の実装契約案 v1（未採択）](anomaly-v03-preformal-campaign-controller-next-v1.md)
- [実際の別process readerと証拠validatorの接続](anomaly-v03-reader-evidence.md)
- [readerの事前保持候補profile](anomaly-v03-reader-profile.md)
- [保存済み工程から続ける単一の報告実行入口](anomaly-v03-saved-report-pipeline.md)
