# 独立算術から解析結果表への接続（2026-09-24）

手計算用clusterから計算した指標・信頼区間・候補比較を、凍結済みanalysis schemaの9候補表へ変換する処理を実装した。関連59試験通過、7手例の各9表/180判定を保存した。**今回接続したのは結果表の部分形式であり、正式analysis文書全体ではない。** 実dev/smokeのCIや正式holdout/gateは起動していない。

## 接続内容

`src/banto_ai/anomaly_v03_analysis_adapter.py`の`compute_fixture_packet(clusters, draws, diagnostics, schema, engineering_ready=...)`が、独立算術の出力を次の形に変換する。

- candidate×core/quality-stress/overallの固定9表、8 targetsのordered availability、13種類の指標を欠落なく対応づける。
- 分子/分母、点、CI上下限、null replicate数、profile状態、absolute/paired gateを丸めず保持する。元のflat availabilityをschemaの配列へ移す。
- `effective_clean_seconds`と検出された全delayをcluster/候補/層ごとに必須入力にする。省略した値を0や推測で補わない。
- delayのcountを検出件数と照合し、1秒以上6秒未満の有限値を要求する。median/mean/min/maxは全delayの結合から計算し直す。区間や層の中央値を平均しない。
- 警報0の適合率はnull/inconclusive、検出0のdelay統計もnull、有効時間0の診断率もnullを維持する。
- 自候補またはC0のprofileが判定不能なら対応する判定と選択へ伝える。engineering_readyは手例の仮定で、実受入証拠にはしない。

`validate_fixture_packet`は、凍結JSON schemaのcandidate_tables/selected_candidate/decision部分と既存S1の件数・露出・delay検査を使う。手例の12 layouts単位の予定母数、overall加算、判定の順序と内容、C1優先選択も照合する。算術とgate閾値は検証済みの独立算術moduleを共用しており、新しい別実装によるCI再監査と称しない。

## 手例と正式出力の区別

すべて**架空2 clusters、4 replicates**の手例である。正式schema全体は40 clusters/50,000 replicatesの宣言とsource/provenanceを必要とするため、小手例をそれに見せかけるmetadataは作らない。

出力は`scope=hand-fixture-analysis-tables-only`。表・仮の候補採択は`fixture_candidate_tables` / `fixture_selected_candidate` / `fixture_decision`に置き、実際の`selected_candidate=null`、`performance_status=not_evaluated`、`formal_document_emitted=false`、formal/promotion/S6=falseを固定する。正式result validatorへこのpacketを渡すと拒否されることも試験した。表のshape合格から正式文書の有効性・実行証拠・独立監査完了を推定しない。

保存した7例は、両候補合格、C1だけ合格、C2だけ合格、両候補不合格、engineering未受入、C0警報0、C0 profile判定不能。各例で9表と180判定を確認した。手例の両候補合格時はC1、C2だけ合格時はC2、判定不能時は選択なしになる。

## 試験・実データの準備状況

新adapter11試験、独立算術21試験、既存S1報告契約27試験の計59試験が通過。欠落/重複/順序違い、誤った母数、delay件数/範囲/NaN、有効時間、CI/判定の改変、profile状態、誤選択、実aggregateの形を手例に渡す誤用を拒否した。入力不変と変換前後の値の完全一致も確認した。

前工程の認証済みcounts（533126bytes/SHA256 e6f3012a0a6fe622b5fc7d6365a7a1f2afadec16517f1bbe2cc423253ae68b2e）は準備状況の確認だけに読んだ。算術には渡していない。dev8 seedは1層96 datasets、smoke2 seedは24 datasetsであり、正式40 seedの480 datasetsとは異なる。

件数・identity/coverage・profile診断・scheduled/effective露出は揃っている。一方、全体の中央値に必要な全検出delay、必要なsliceの独立導出、正式holdout/固定bootstrapの実行証拠、provenance/runtime受入の接続は残る。`readiness.json`に区別して保存した。

## 保存・資源

実装`9b18626703c40801a164f61eb01dab3acbb36eae`。OUT `artifacts/independent-analysis-adapter-2026-09-24`。`fixture-*.json`に入力と結果、`checkpoint-fixtures.json`に中間保存、`test-results.json`に59試験、`readiness.json`に不足項目、`summary.json`に要約を保存。最終文書revisionと全pinは`savepoint-evidence.json`。

前工程の保存点7935bytes/SHA256 `3d03cdef2852e8432b7d1ca9de7cab25ff9b994fefa9819cb290263145426bb5`を外部起点にした。前々工程のregistry pinへ接続し、analysis schemaのraw hashも凍結registryと一致を確認。schema/config/旧算術/旧seed集計の変更はない。

保存検証は2.516秒、peak private 27.36MiB。最小空きRAM 15.09GiB / commit余裕 21.12GiB、終了時C/D空き 128.43/298.74GiB。追加成果物は約1.3MB。旧保存点・実計算source・本流・既存dirty guardを保全し、banto-24 PAUSED維持。観測生成、score再計算、実データCI、新評価、正式文書出力は0。

## 次の作業

次は保存済み実データの**検出遅延と条件別sliceの独立集計**。必要な入力列と証拠pinを確認し、メモリ上限を守る読取りで、全検出delayからの集計とslice母数・重複/欠落を検証する。既存score再計算・新評価は不要。既存の区間別delay中央値から全体中央値を推測しない。

正式40 holdout/実CI/gate、正式analysis文書全体のprovenance/runtime接続、単一writer受入、完全S6は残る。保留した専用principal試験は再開しない。Phase 2/3全体を完了扱いしない。
