# 研究計画と調査

研究roadmap、時系列モデルと公開データの調査。

[文書の入口](../README.md) · [最新の引継ぎ](../current-handoff.md)

## 固定パスの関連文書

- [banto-ai 研究・実装計画書](../research-implementation-plan.md)

## 文書

- [2026-10-17の研究整理](../results/research-consolidation-2026-10-17.md) — 現役coreと履歴を分離し、小型Rust学習部品へ進む。

- [R2P lock案・人工Python参照と次工程](../results/rust-r2p-lock-and-python-reference-2026-10-16.md) — 凍結参照を使う小型Rust実装へ。

- [Rust現実装棚卸しと人工学習の固定条件](rust-r2p-synthetic-training-contract-2026-10-16.md) — 小型loss/gradient/AdamW/保存再開、manifest/lock未整合を保持。
- [CARE holdout不合格後の方針](care-next-direction-2026-10-18.md) — 残差scoreに異常と正常を見分ける力がほぼない（AUC中央値0.50）。CAREでの合格主張をやめ、自asset校正の残差監視としてbantoへ組み込み、次の判定はbanto実データの前向き評価で行う。2026-10-18承認。
- [CARE Farm B・Cの1回限りholdout契約](care-holdout-bc-contract-2026-10-18.md) — 開封前に信号（Cの温度1は主軸受温度で代替）・split（B 9fold、C 22fold）・Farm Aと同じ学習と警報・B＋C合算の合格条件を固定。B・Cの新規学習はR0.2の例外として2026-10-18承認。
- [CARE保全の判定基準](care-maintenance-criteria-2026-10-18.md) — 必要な先行時間は72時間（副24時間）、誤警報は上限asset・30日1.0件／目標0.25件。Farm Aは比較だけ、合否はFarm B・Cの1回限りのholdoutで判定する。2026-10-18承認。
- [保全の実用性評価と基盤モデル比較の契約](care-maintenance-practical-contract-2026-10-17.md) — 先行時間0/24/72/168時間別の検知と誤警報の換算を報告し、TimesFM 3・Chronos-2・Toto 2をzero-shotで同じ警報規則に載せる。CARE testは開発材料として扱う。
- [正式R2の固定条件（CARE fold0）](rust-r2-formal-contract-2026-10-17.md) — 保存state＋新AdamWの1更新・8更新、保存再開、成熟state import、floorのtie。R0.2の比較で1回だけ実行する。
- [R0.2: 全モデル更新比較の基準とR1の扱い](rust-r0.2-comparison-amendment-2026-10-17.md) — parameter更新はclip後|勾配|≥10·epsの要素で比較、正式R2の入口はR1最終出力と同一入力局所比較385件。2026-10-17承認。
- [R2P工程4: SmallForecaster全体の人工学習接続の固定条件](rust-r2p-full-model-contract-2026-10-17.md) — lossと全59 tensorの勾配。全モデル1更新の比較はR0.1で成り立たないため除外。

- [実用性検証とRust学習へ戻る改訂2](banto-ai-practical-training-return-plan-2026-10-16.md) — pointer追跡停止、残1点の対応上限、人工R2Pと正式R2を分離。












- [linfaとsmartcoreの将来研究候補とAstraレビュー](rust-classical-ml-linfa-smartcore-note-2026-10-16.md) — 古典MLの比較基準、保全先行の有限比較、保存再開・版・OSの確認。

- [Rust R1全層診断と固定条件](../results/banto-ai-rust-r1-all-layer-audit-2026-10-16.md) — 385比較、各161anchor厳密再現、局所と累積の差を分離。




- Rust R1の現状と再開条件 — Xcode確認通過。R1 CPU buildがcache+target合計768MiB上限で停止、テスト/数値比較未確認。

- banto-ai Rust R1の準備と再開手順 — crateソース/lock/154有効依存と7参照forwardを保存。Xcode規約未同意でbuild/テスト/数値一致は待機、R1未完。

- [denroku-psi-demoの需要AIとPSI接続の現状](denroku-psi-ai-integration-2026-10-16.md) — Python LightGBM学習/Rust推論/静的PSIと、未実装のC API再学習計画。AI crate共通化の境界を整理。

- [banto-aiのRustクレート実装と製品利用の計画](banto-ai-rust-implementation-plan-2026-10-16.md) — AI側に学習/推論/再開、利用側にadapter/job host。CPU buildから数値比較・有限CARE・製品/OS受入までの工程と終了条件。

- [Rust R0配置の訂正](rust-small-forecaster-r0-2026-10-16.md) — AIの学習・推論クレートはbanto-ai、banto-industrialは利用adapter。依存方向を固定、数値条件は不変。

- [CARE保存予測の未検知分析とRust R0](../results/care-saved-diagnostics-rust-r0-2026-10-16.md) / [Rust R0契約](rust-small-forecaster-r0-2026-10-16.md) — 8件は3連続未達、1件は超過なし。banto-industrial source確認、Burn0.22候補・学習再開/数値比較条件固定。次はR1、製品接続未実施。

- [CARE v6原本・利用条件・sensor/asset確認](../results/care-metadata-contract-2026-10-16.md) / [有限契約r1](care-a-maintenance-contract-2026-10-16.md) / [設定JSON](../../examples/configs/care-a-maintenance-20261016-r1.json) — v6 MD5一致、入力/label分離、Farm A留一5fold/22file/3 Avgを固定。metadata段階の履歴。現在の数値入力は次の結果を参照。
- [CARE数値入力と実consumerの支持確認](../results/care-numeric-consumer-2026-10-16.md) — 22file/3信号変換、全record独立検算、時点/label分離と全固定支持床pass。CARE学習/予測/性能採点は未実施。
- [CARE train尺度とbaseline profile・全学習schedule固定](../results/care-training-preparation-2026-10-16.md) — 全5foldの尺度/MAD/20bin支持pass、全163,840例再現、実batch取得。ニューラル学習/性能採点は次工程。
- [CARE5fold実学習・保全イベント評価](../results/care-macos-learning-evaluation-2026-10-16.md) — 固定4条件通過、検知3/12・9未検知/nativeだけのevent22も保存。全保存値独立照合・学習state neutral参照。

- [MetroPT Mac M1・3seed実学習と評価](../results/metropt-macos-m1-2026-10-16.md) — 全6構成4096更新、全予測freeze後採点。機構pinball2.105%改善、負のseed/圧力pinball/coverage不足も保存。全6学習stateのneutral書出し。
- [CARE保全・点検支援のイベント評価設計](care-maintenance-evaluation-design-2026-10-16.md) — event/誤警報/先行時間、asset分離、残差可用時刻。metadata/r1固定・数値入力準備済み、CARE学習未開始。

- [MetroPT Mac M0実装・数量品質・最小接続の結果](../results/metropt-macos-m0-2026-10-16.md) — 全8,967/123/123窓保持、未学習forward2回/境界10項目/新guard6件/独立読戻しpass。Rust用neutral参照を保存。M1実学習/2015停止、用途第一優先は保全・点検支援。

- [Rustでの学習・推論とbanto統合の最終目的/R0〜R4](timesfm-inspired-practical-evaluation-plan-2026-10-16.md#7-最終実装--学習も含めたrust移植とbanto統合) — library API/CLI、前処理からoptimizer/保存再開まで、Python参照との比較・有限評価・banto接続を段階化。

- [計画遵守・MetroPT固定詳細仕様r2](metropt-macos-multiday-protocol-2026-10-16.md) / [設定JSON](../../examples/configs/metropt-macos-multiday-20261016.json) — 日時だけで独立13日を固定、候補8,967/123/123窓。M0実装・数量品質は未完、実学習・2015停止。

- [自作モデル実用性の具体計画・Astra確認](timesfm-inspired-practical-evaluation-plan-2026-10-16.md) — MetroPTの有限比較を最初に、油圧/XJTU/CAREと需要の役割・判断・終了を分離。計画のみ、実学習・2015停止。

- [産業3データセットのMac公式取得・入力準備](../results/industrial-data-macos-intake-2026-10-16.md) / [取得契約](industrial-data-macos-intake-contract-2026-10-16.md) — MetroPT・油圧・XJTU全原本を取得、入力準備と独立読戻し。学習・2015停止。

- [元の主目的への復帰・産業/需要の自作モデル実用性計画とAstra確認](timesfm-inspired-dual-domain-plan-2026-10-16.md) — 用途選択を目的の廃止とした解釈を訂正。既存3モデル系統を再利用し、CARE異常予兆候補を追加。実学習・2015停止。
- [CAREローカル原本受領metadata](care-local-archive-metadata-2026-10-16.json) — 原本SHA/中央directory/READMEのみ、未取込・未採点。

- [現在の検証と研究目的のAstra監査](demand-purpose-alignment-astra-review-2026-10-16.md) — 目的の方向は一致、人工境界系列はここで区切る。実学習・2015停止を維持。

- [rank3・週係数非ゼロの厳密ゼロ境界結果](../results/demand-rank3-zero-boundary-artificial-2026-10-16.md) — Q2 rank3人工1解/30予測/90scenario、週項と中央raw0/前後を独立照合。実学習・2015停止。
- [事前契約](demand-rank3-zero-boundary-artificial-contract-2026-10-16.md) / [Astra](demand-rank3-zero-boundary-artificial-astra-review-2026-10-16.md) / [決定表](demand-rank3-zero-boundary-artificial-decisions-2026-10-16.json)

- [rawP厳密ゼロ境界・前後人工接続結果](../results/demand-zero-boundary-artificial-2026-10-16.md) — Q2人工1解/30予測/90scenario、中央raw0とflag/branch差。実学習・2015停止。
- [事前契約](demand-zero-boundary-artificial-contract-2026-10-16.md) / [Astra](demand-zero-boundary-artificial-astra-review-2026-10-16.md) / [決定表](demand-zero-boundary-artificial-decisions-2026-10-16.json)

- [丸め差付き比例配分・floor人工接続結果](../results/demand-roundfloor-pipeline-artificial-2026-10-16.md) — 8active state再利用、新fit/solve0、400予測・152scenario。実学習・2015停止。
- [事前契約](demand-roundfloor-pipeline-artificial-contract-2026-10-16.md) / [Astra](demand-roundfloor-pipeline-artificial-astra-review-2026-10-16.md) / [決定表](demand-roundfloor-pipeline-artificial-decisions-2026-10-16.json)

- [制約が非ゼロ解を変える人工接続結果](../results/demand-active-pipeline-artificial-2026-10-16.md) — 四季正負8active解、640日次・380scenarioの独立照合。実学習・2015停止。
- [事前契約](demand-active-pipeline-artificial-contract-2026-10-16.md) / [Astra](demand-active-pipeline-artificial-astra-review-2026-10-16.md) / [決定表](demand-active-pipeline-artificial-decisions-2026-10-16.json)

- [rank3・週β非ゼロ人工接続結果](../results/demand-rank3-pipeline-artificial-2026-10-16.md) — 8state/640予測/380scenario、週寄与をexact日次まで照合。実学習・2015停止。
- [事前契約](demand-rank3-pipeline-artificial-contract-2026-10-16.md) / [Astra](demand-rank3-pipeline-artificial-astra-review-2026-10-16.md) / [決定表](demand-rank3-pipeline-artificial-decisions-2026-10-16.json)

- [非ゼロ人工prefix→日次接続結果](../results/demand-nonzero-pipeline-artificial-2026-10-16.md) — 8非ゼロstate/240予測/228scenario。実学習・2015停止。
- [事前契約](demand-nonzero-pipeline-artificial-contract-2026-10-16.md) / [Astra](demand-nonzero-pipeline-artificial-astra-review-2026-10-16.md) / [決定表](demand-nonzero-pipeline-artificial-decisions-2026-10-16.json)

- [重み付きsolver人工結果](../results/demand-weighted-solver-artificial-2026-10-16.md) — 41case/43成功API、独立KKT/gap0。実学習・2015停止。
- [solver人工契約](demand-weighted-solver-artificial-contract-2026-10-15.md) / [Astra](demand-weighted-solver-artificial-astra-review-2026-10-16.md) / [決定表](demand-weighted-solver-artificial-decisions-2026-10-16.json)

- [実2013数量prefix・問題生成/β0結果](../results/demand-weighted-numeric-prefix-2026-10-15.md) — 210完全label/25compile、独立54191比較。学習・2015停止。
- [数量prefix事前契約](demand-weighted-numeric-prefix-contract-2026-10-15.md) / [Astra](demand-weighted-numeric-prefix-astra-review-2026-10-15.md) / [決定表](demand-weighted-numeric-prefix-decisions-2026-10-15.json)

- [実prefix条件・時点来歴metadata結果](../results/demand-weighted-prefix-preflight-2026-10-15.md) — 470metadata/25検査、独立15698比較。数量生成・学習・2015停止。
- [prefix事前監査契約/接続AND条件](demand-weighted-prefix-preflight-contract-2026-10-15.md) / [Astra](demand-weighted-prefix-preflight-astra-review-2026-10-15.md) / [決定表](demand-weighted-prefix-preflight-decisions-2026-10-15.json)

- [非ゼロ係数→日次bridge人工結果](../results/demand-weighted-daily-bridge-2026-10-15.md) — 39予測/82人工label、独立4553比較。学習・2015停止。
- [日次bridge事前契約](demand-weighted-daily-bridge-contract-2026-10-15.md) / [fixture修正](demand-weighted-daily-bridge-fixture-amendment-2026-10-15.md) / [Astra](demand-weighted-daily-bridge-astra-review-2026-10-15.md) / [決定表](demand-weighted-daily-bridge-decisions-2026-10-15.json)

- [consumer人工結果・β0再現](../results/demand-weighted-consumer-artificial-2026-10-15.md) — 27問題/5replay、独立28809比較。学習・2015停止。
- [consumer人工事前契約](demand-weighted-consumer-artificial-contract-2026-10-15.md) / [出力復元補記](demand-weighted-consumer-output-recovery-2026-10-15.md) / [Astra](demand-weighted-consumer-artificial-astra-review-2026-10-15.md) / [決定表](demand-weighted-consumer-artificial-decisions-2026-10-15.json)

- [Q4集中・自店信号0と学習開始条件の結果](../results/demand-weight-learning-entry-2026-10-15.md)
- [学習開始条件と将来の有限実験枠](demand-weight-learning-entry-contract-2026-10-15.md)
- [開始条件のAstra確認](demand-weight-learning-entry-astra-review-2026-10-15.md)

- [固定重みの実入力接続・集中/rank監査結果](../results/demand-ordered-weight-input-audit-2026-10-15.md)
- [実入力接続・支持監査の事前契約](demand-ordered-weight-input-audit-contract-2026-10-15.md)
- [実入力監査のAstra確認](demand-ordered-weight-input-audit-astra-review-2026-10-15.md)

- [重みの数値仕様固定と人工統合結果](../results/demand-ordered-weight-numeric-2026-10-15.md)
- [重みの事前数値契約](demand-ordered-weight-numeric-contract-2026-10-15.md)
- [人工検証補強・初版保持](demand-ordered-weight-numeric-test-amendment-2026-10-15.md)
- [Astra数値実装レビュー](demand-ordered-weight-numeric-astra-review-2026-10-15.md)

- [店舗特性×順序付き持続性の第一案・人工確認](../results/demand-ordered-persistence-design-2026-10-15.md)
- [順序付き重みの設計（実行未ready）](demand-ordered-persistence-design-2026-10-15.md)
- [順序/単調性/連続性の説明補記](demand-ordered-persistence-amendment-2026-10-15.md)
- [Astra順序付き案の結果確認](demand-ordered-persistence-astra-result-review-2026-10-15.md)


- [保存260予測の2014採点：年間改善/Q1不適格](../results/demand-bounded-scoring-2014-2026-10-15.md)
- [桁数内の固定精度区間集計契約](demand-bounded-scoring-contract-2026-10-15.md)
- [Astra有界集計の実装/結果確認](demand-bounded-scoring-astra-result-review-2026-10-15.md)





- [制約付き学習の第一設計（新fitなし）](demand-constrained-training-design-2026-10-15.md)
- [Astra方法・進め方監査](demand-constrained-training-astra-review-2026-10-15.md)

- [許可prefixと固定2特徴の監査契約](demand-prefix-adapter-design-2026-10-15.md)

- [入力境界検証のGit環境・初回文書失敗の保存](demand-input-boundary-os-check-2026-10-15.md)

- [入力/ラベル分離と仮定時点契約の検証結果](../results/demand-input-boundary-2026-10-15.md)
- [入力境界の事前実装契約](demand-input-boundary-design-2026-10-15.md)
- [Astra実装前確認](demand-input-boundary-astra-review-2026-10-15.md)
- [Astra loader指摘とv2補強](demand-input-boundary-loader-review-2026-10-15.md)
- [Astra境界契約の結果確認](demand-input-boundary-astra-result-review-2026-10-15.md)









- [四季平均両側制約・総量補正は全Q対照へfallback](../results/demand-seasonal-risk-2026-10-15.md)
- [四季平均制約付きsigned総量補正の事前契約](demand-seasonal-risk-design-2026-10-15.md)
- [Astra確認・凸適格区間と総量MSEの有限比較](demand-seasonal-risk-astra-review-2026-10-15.md)

- [Astra確認・総量両側非悪化と四季別数量配分の結果](../results/demand-total-preserving-2026-10-15.md)
- [総量保存と四季別校正/選択の実行前契約](demand-total-preserving-design-2026-10-15.md)
- [Astra独立レビュー・保証境界と有限比較](demand-total-preserving-astra-review-2026-10-15.md)

- [総量過小非増加・元日数量改善と通常総量MSEの残課題](../results/demand-shortfall-quantity-2026-10-15.md)
- [過小非増加と元日前後数量の実行前契約](demand-shortfall-quantity-design-2026-10-15.md)


- [過去反復の休業相当推定・観測と欠測0仮定の別評価](../results/demand-recurring-closure-2026-10-15.md)
- [2013/2014から推定する休業相当仮説の実行前契約](demand-recurring-closure-design-2026-10-15.md)
- [休業0・営業中販売0・欠測の分離と固定2015評価](../results/demand-sales-state-2026-10-15.md)
- [営業状態/販売発生確率/欠測の分離・実行前契約](demand-sales-state-design-2026-10-15.md)
- [声かけまで継続するMac自走・heartbeatと境界](autonomous-continuation-2026-10-15.md)
- [既存10店2015の一回評価・小幅改善と暫定目安未達](../results/demand-existing-stores-2015-2026-10-15.md)
- [既存10店2015評価の実行契約](demand-existing-store-evaluation-design-2026-10-15.md)
- [主用途は既存店舗の将来予測・PSI／次評価の設計](demand-existing-store-purpose-2026-10-15.md)
- [Mac原本からの新規生成契約](demand-macos-rebuild-design-2026-10-15.md)
- [Macでの入力・profile・模型生成結果](../results/demand-macos-rebuild-2026-10-15.md)
- [現在の保管範囲・旧証拠3.46GBの承認済み削除](workspace-retention-2026-10-14.md)
- [Macへの引継ぎ・Git外の証拠と移植箇所](pc-handoff-2026-10-14.md)
- [店舗分離による終了点選択・一軌跡比較の契約](demand-group-selection-design-2026-10-14.md)
- [時間選択対移行選択の一回結果](../results/demand-group-selection-2026-10-14.md)
- [学習量・固定全件曲線・早期停止の新手順](demand-training-adequacy-design-2026-10-14.md)
- [学習量診断の結果・1664best](../results/demand-training-adequacy-2026-10-14.md)
- [統計8入力の同条件学習比較・小幅改善](../results/demand-statistical-feature-pair-2026-10-14.md)
- [σ・EMAの学習入力への修正設計](demand-statistical-feature-input-design-2026-10-14.md)
- [統計branchの新6接続確認](../results/demand-statistical-features-2026-10-14.md)
- [σ・EMA・予測平均の固定案](demand-statistical-overlay-design-2026-10-14.md)
- [統計併用6確認と回顧結果](../results/demand-statistical-overlay-2026-10-14.md)
- [休日当日対前後の小型模型比較・条件未達で停止](../results/demand-calendar-model-pair-2026-10-14.md)
- [公開暦の共通入力6確認とfit支持](../results/demand-public-calendar-input-2026-10-14.md)
- [公開暦と営業予定を分ける小型模型接続条件](demand-calendar-model-connection-design-2026-10-14.md)
- [休暇区間/休業長の新6確認](../results/demand-event-interval-input-2026-10-14.md)
- [休暇期間のイベント表現・Astraの検討](demand-holiday-duration-design-2026-10-14.md)
- [休業ゼロと休日前後を分ける新入力設計](demand-holiday-event-input-design-2026-10-14.md)
- [休日予定版と前後channelの新6確認](../results/demand-holiday-event-input-2026-10-14.md)
- [8週間の入力境界・新5確認](../results/store-sales-weekly-history-input-2026-10-14.md)
- [8週間の履歴を残す次入力の固定案](store-sales-weekly-history-design-2026-10-14.md)
- [mean出力の実装・一回評価](../results/store-sales-mean-pilot-2026-10-14.md)
- [meanとquantileを分ける次候補設計](demand-mean-and-quantile-model-design-2026-10-14.md)
- [需要モデルの一回探索と判断](../results/store-sales-small-model-2026-10-14.md)
- [研究方針に合わせたデータの保管と整理](data-retention-and-cleanup-2026-10-14.md)
- [公開研究データの取得状況](public-dataset-acquisition-2026-10-14.md)
- [菓子の季節・販促を加味した需要予測とPSIの研究計画](confectionery-demand-psi-research-plan-2026-10-14.md)

- [小型独自モデルの一回探索と研究上の結論](timesfm3-small-model-pilot-2026-10-14.md)
- [小型独自モデルのデータ・学習前準備](timesfm3-small-model-preparation-2026-10-14.md)
- [小型独自モデルの最小実装確認](timesfm3-small-model-implementation-2026-10-13.md)
- [TimesFM構造を参考にした小型独自モデルの設計](timesfm3-small-model-design-2026-10-13.md)
- [TimesFM 3の実用性と公開情報からの独自モデル構築](timesfm3-utility-and-reproduction-2026-10-13.md)
- [公開産業時系列データ調査・選定](public-dataset-survey.md)
- [研究ロードマップ](research-roadmap.md)
- [Banto向け時系列モデル技術調査](time-series-model-survey.md)
