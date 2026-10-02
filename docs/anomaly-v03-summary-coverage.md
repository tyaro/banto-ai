# 保存済み要約と登録・試行履歴・全予定枠の結合

2026-10-02。[実装](../src/banto_ai/anomaly_v03_summary_coverage.py)、[試験](../tests/test_anomaly_v03_summary_coverage.py)、[結果](results/anomaly-multiseed-v0.3-summary-coverage-2026-10-02.md)。

`bind_summary_coverage(metadata_raw, summaries, *, expected_mode, expected_metadata_pin, expected_summary_pins, expected_savepoint_pin, expected_evidence_pin)` は、保存済みの小さい要約とcheckpoint adapter出力を結ぶ純粋関数。観測や評価payloadを開かず、以前の検算結果を再利用する。入力bytesの期待pinは、読み込んだ文書自身ではなく呼出し側が別途保持する。

## 入出力

- metadata_rawは、既存のadapt_completed_journalで照合した全120区間の出力bytes。固定dev/smoke登録、最新attempt、過去の失敗、評価/input hash、journalの外部結合を保持する。
- summariesとexpected_summary_pinsは、区間番号の厳密な整数0〜119をキーとする同一集合のdict。それぞれread_chunk_summariesの出力bytesと、その外部pinを渡す。JSONオブジェクトの項目順には依存しない。
- expected_modeはfixtureまたはengineering。fixtureでも登録IDの形式はdev/smokeのまま。modeは生成元を認証する証拠ではなく、正式・未知modeはデコード前に拒否する。
- expected_savepoint_pinとexpected_evidence_pinを全要約の保存点・evidenceへ結合する。各要約のrun_root、保存点path、planファイルpinも同じであることを確認する。path文字列は比較するだけで開かない。

metadataは4MiB以下、要約1区間は512KiB以下、供給bytes全体は32MiB以下。これらは入力サイズ制限で、時間・メモリ・ディスクの実行予算は呼出し側が管理する。

## 確認する内容

固定登録の全720枠、120区間の順序、各区間の最新attempt、履歴中の連番、終端hash、既知の失敗履歴を確認する。候補間・再試行間の既知の入力hashが一致し、最新6評価がsuccessまたはinconclusiveであることも必要。

供給された各要約は、最新attempt、6つの登録identity、評価ファイルhash、6種の入力hash、旧監査hash、保存済み監査の判定と対応させる。主集計の整数分子/分母と有効時間を監査結果から照合し、条件別の分割・joint/marginal・遅延・判定不能・分母ゼロとの整合性も確認する。観測→scoreやepisode→incidentの独立検算を再実行する処理ではない。

## 完了宣言と供給済み要約を分ける

| 入力 | 戻り値 |
| --- | --- |
| 全120区間の完了メタデータ＋要約なし | partial_summary_binding、確認済み0評価、未確認720評価 |
| 同メタデータ＋1区間の要約 | partial_summary_binding、確認済み6評価、未確認714評価、欠落区間119個 |
| 同メタデータ＋120区間の要約 | complete_summary_binding、確認済み720評価、未確認0評価 |
| 区間重複、登録や最新attempt不一致、欠落したpin、異なる入力hash | 例外。部分成功に置き換えない |

欠けた要約をjournalの完了宣言から補わない。declared_coverageとbound_summary_coverageを別に返し、missing_summary_chunks/unverified_summary_evaluationsを残す。全件一致時もcampaign_evaluations_creditedは0で、実campaignの新規認証・正式採択にはしない。

出力はanomaly-v03-summary-coverage-binding-v1。要約pin、各区間の最新attempt/評価ID/coverage、共通anchor、失敗の元terminal record、判定不能件数、分母ゼロ件数を保持する。大きな要約本体を複製せず、集計表や信頼区間はここでは生成しない。失敗時の評価詳細がunreportedなら、その不明状態を保持する。過去attemptのmanifest詳細は元metadataのpinを通じて保持する。

## 信頼の境界と次工程

期待pinは署名ではなく、呼出し側が信頼した過去の記録を固定するためのもの。入力を作り直して期待値も差し替えられる相手の真正性は保証しない。journal自体の再実行・各評価payloadの現時点のbytes確認・生成導出・過去processの認証は行わない。formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持する。

次は結合済みのdev/smoke主count・条件別countを、role/seed/candidate/stratum別の記述集計へ接続する。登録IDを正式40seedや架空40clusterへ変換せず、欠落した要約を含む結果から全体集計を返さない。固定入力で接続を確認し、既存720評価のpayloadを読み直す作業には戻らない。
