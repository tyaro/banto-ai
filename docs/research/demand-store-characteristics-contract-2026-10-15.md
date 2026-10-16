# 発行前10店特性と保存Q1悪化集中：記述診断の事前契約

2026-10-15 JST。人の依頼に基づき、2015停止のまま、10店特性表と保存2014Q1悪化の集中を記述する。[保存260予測採点](../results/demand-bounded-scoring-2014-2026-10-15.md)の候補/B・四季条件・mode分離は変更しない。新fit/新予測/削除fit/候補比較/分類/閾値探索/2015内容decode・fit・予測・再評価なし。

## 境界と先行保存

許可店6,7,10,13,15,17,19,23,26,27のみ。baseline profileはasof2014-01-01、selected-internal.csvからstore/date metadataで2013のみ選別後にquantityをdecodeする。365calendar日×10店を照合し、除外店/2014以後の数量をprofileへ渡さない。日付の翌日に利用可能という既存仮定を継承し、実到着時刻は未確認。

Q1の保存済みinput70件（7発行日×10店）から、origin前56暦日のdate/value/available_atだけを新しい具体payloadへ写す。対象日・asof範囲、next-day available≤origin、重複なし、必ずdate<originを検査する。profile関数は過去payloadだけを取り、path/reader/label/予測誤差を受け取らない。baselineとsnapshotと入力pinsを保存・freezeしてから今回の診断labelを読む。既読Q1悪化後の設計なので盲検ではない。

## 特性定義（全て記述、分類閾値なし）

raw0/nullと営業unknownを維持。01-01/12-25は固定の休業相当仮定として需要特性から除き、raw観測数/真0/null/休業相当内外の各数を別保存。営業相当日の真0は残す。欠測0補完なし。以下は休業相当を除く観測値のみ。

* 水準：平均、母標準偏差/元平均によるCV。平均0・空支持は未定義の理由を保存。
* 曜日：曜日別件数/平均、Σn_w(μ_w−μ)^2/Σ(y−μ)^2によるin-sample曜日説明分散比、週末平均/平日平均比。曜日調整後の相対的ばらつきはsqrt(Σ(y−μ_weekday)^2/n)/元平均（残差平均では割らない）。定数系列等は理由を保存。
* 暦日lag7：date−7の双方が営業相当・観測のペアだけで相関、ペア件数も保存。観測行の7個前を使わない。分散0/ペア不足は未定義。
* 月/Q：暦月別/Q別の件数・平均・全体平均比、月平均最大最小差/全体平均、最大最小月リスト。これは単一年内の水準差でtrend/外れ値/曜日構成も混ざり、安定した年周期の強さとは呼ばない。baseline年反復は1、年季節性はunknown_single_year。
* 直近変化：直近28暦日とその前28暦日の営業相当観測平均比−1、両期間の件数。総量比や曜日補正済み比ではない。前期間平均0は未定義。

baseline10店の全特性を保存し、snapshot70件には同定義とbaseline水準との比を保存。snapshotの月差等は56日だけの記述で年季節性とはしない。長い系列ほど有利な閾値/特性選択・p値/相関検定・クラスタ・店舗型の固定なし。

## Q1寄与分解

保存候補/Bの日次exact配分とcanonical総量、保存2014labelを使用。Q1all70/normal60（元日以外）、observed/assumed_missing_zeroを別々に扱う。modeはrawnull保持と休業相当位置だけの欠測0仮定。元日真0を維持する。

総量MSE/under/over/dailyMSE/quantityMSEについて、元の店内指標支持n_sと10店等重みで、各atomの差/(10n_s)を作る。日次指標を窓平均・窓等重みへ変えない。窓の寄与δはその窓の重み付きatom和。個々のexact値・積・和は8192bit以内、固定p192区間集計を継承する。各窓exactδの符号でgross＋=Σmax(δ,0)、gross−=Σmax(−δ,0)、net=Σδを、店別/発行日別/全体で集計する。grossの単位は元指標への寄与で、独自群平均ではない。

原atomごとのp192集計を旧Q1paired macroと照合する。窓内exact和を先に取るnet区間は旧atom区間に包含されることを確認。各storeのnetは旧per-store mean/10に対応するが、区間の丸め単位は異なる。窓・店・発行日とall/normal/modeは重複切り口で独立追試ではない。

top1/top3 shareは店舗別gross＋を全店舗gross＋で割る。同様に発行日別も出す。net比を集中率にせず、正負/netも併記する。分母0なら該当なし。分母下限>0の場合だけ区間比を計算し、順位は整数区間が分離する場合だけ確定（同値/重なりは未確定）。topはこの保存結果の悪化寄与であり将来の危険店舗順位ではない。net悪化店の順位とは別である。

窓別にcanonical B/Y/P、delta、feature支持、5指標寄与を保存。総量MSEの恒等式Δloss=(2e_BΔ+Δ²)/(14u)²を照合し、悪化時はe_BΔ≥0なら同方向へ誤差拡大、<0なら行き過ぎと記述する。over増加も既存過大の拡大/過小から過大への跨ぎを区別する。これらは保存予測の代数的説明で、店舗特性による因果説明ではない。

## 確認と終了

Astra方法/進め方read-only確認→新入口人工fixture→profile/snapshot凍結→記述分解→別readerで時点/特性/重み/区間/正負net/top境界/原指標照合→Astra結果確認→報告・引継ぎclosure。人工確認はfuture数量非参照、未来日/availability拒否、null/0/closure分離、暦日lag7、CV0/比率0/定数、曜日件数重み、支持が異なる日次寄与、gross0/相殺/順位重なりを含む。

特性と悪化の対応は探索的候補であり原因・安定店舗型・修正ルールを認定しない。四季平均の過小量・過大量非増加、同休業mean28比較、観測/仮定mode分離、2014以前だけの調整を維持。Q1事後B差替え/新候補/新評価へ接続しない。少数発行日削除fitは未実施のまま。

各準備/診断/readback/文書工程は親900/子870秒、Mac sampled physical footprint/peakRSS各2GiB。通常artifact24files768MiB、総32files1GiB/単一32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files。stdio/exit/source/state入力pins/部分結果/失敗/resource/closureをfresh rootsへ保存。既存変更・失敗・closed roots保持、heartbeat PAUSED。

2016–17/予約31–54/販促/正式holdout/Windowsnative/CARE/課金API/新取得/外部研究データ送信/commit/push/削除/依存lock/Xcode変更/PSI採用なし。共通Mac計算とWindows固有/OS依存suiteを別報告。今回依頼の記述分析まで完了し、分類/モデル変更へ自動接続しない。
