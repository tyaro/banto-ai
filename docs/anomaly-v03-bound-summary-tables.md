# 結合済み要約からdev/smokeの比較表を作る

2026-10-03。[実装](../src/banto_ai/anomaly_v03_bound_summary_tables.py)、[試験](../tests/test_anomaly_v03_bound_summary_tables.py)、[結果](results/anomaly-multiseed-v0.3-bound-summary-tables-2026-10-03.md)。

`aggregate_bound_summaries(binding_raw, summaries, *, expected_binding_pin, expected_mode)` は、前工程の全件結合記録と120区間の小さい要約bytesから、記述集計を作る純粋関数。ファイルpathを開かず、過去のjournal結合・観測からのscore検算・ledger検算を繰り返さない。

## 入力と確認

binding_rawは[前工程](anomaly-v03-summary-coverage.md)のcomplete_summary_binding出力bytes。expected_binding_pinは呼出し側が別途保持した期待値であり、読み込んだ文書から自動採用しない。要約の期待pinはこの固定済み結合記録に由来する。summariesは厳密な整数0〜119をキーとしたdictで全120区間が必要。

fixture/engineeringのみを受け付け、modeは過去の生成元を認証する証拠とはしない。固定dev/smoke登録、区間/評価ID順序、最新attempt、共通保存点、供給要約のbytesとpin、全件coverageを照合する。全要約のhash一致を確かめた後にcount処理を始める。部分結合、欠落、重複、異なるattemptや入力bytes、formal/未知modeは例外となり、全体の集計表を返さない。

結合記録4MiB以下、要約1区間512KiB以下、入力合計32MiB以下。時間・メモリ・出力容量は呼出し側で管理する。

## 集計の内容

固定された要約を1区間ずつデコードし、主countを保存監査のcountと照合する。条件別countの形・分割・主countとの対応、判定不能profile、分母ゼロ、遅延度数も確認する。既存の主集計とSliceAccumulatorを再利用し、整数の分子/分母や度数を合算してから割合・遅延統計を計算する。評価ごとの割合や中央値の平均ではない。

| 単位 | 出力 |
| --- | --- |
| dev 8seed、smoke 2seed | 10seed群。roleを混合しない |
| seed × 3候補 × core/quality-stress/overall | 90表。各条件12評価、overall24評価 |
| role × 3候補 × 3条件 | 18表。devは96/192評価、smokeは24/48評価 |
| role × 2候補対c0 × 3条件 | 12件の記述的な差。信頼区間や採択判定を付けない |

主countと条件別内訳を表のキーで結び、予定分母、precisionと検出/episode数、availability、有効時間、判定不能診断を既存の結合検査で照合する。遅延は検出済みincidentに限定した度数から計算し、未検出に遅延を埋めない。分母ゼロはnullのままで、元の不明な指標一覧も残す。

戻り値anomaly-v03-bound-summary-tables-v1はby_seed/by_roleに主指標・条件別内訳・遅延をまとめ、seed_clusters、paired_descriptive、coverageを保持する。元binding/metadata/journal/保存点/evidenceのpinと各区間のsummary参照、旧失敗terminal recordも残す。元の要約や失敗履歴を変更しない。

## 完了範囲

外部pinで固定した過去の記録を信頼して集計する境界であり、署名、現在の元payloadの認証、生成導出やproducerの実行証明ではない。正式40seedへ読み替えず、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=false、performance_status=not_evaluatedを維持する。

新しい観測生成、既存720評価のraw payload再読取り、detector/ledger再計算、bootstrap、信頼区間、正式gate、候補採択は行わない。今回の保存例は前回の架空要約をそのまま使い、集計接続を確認したもの。

次は得られた記述集計表を既存の報告文書・保存payloadの準備へ接続する。元の結合記録への参照と正式欄の未充足を保持し、同じ集計や評価を反復しない。
