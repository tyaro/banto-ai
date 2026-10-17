# 休業ゼロ・営業中の販売ゼロ・欠測を分ける固定2015評価

2026-10-15 JST、人の「設計に変更して既存10店2015評価」「営業予定不明日は祝日だけでゼロにせず欠測区別」が今回の実行委任。heartbeatは人の声かけでPAUSEDのまま、この直接実行を完了する。前の頑健性診断は未開始で、この工程へ置換。

仮説は、販売数量の平均を出す入口で営業予定による確定休業と販売発生確率を別に扱えば、基準との混合による正の下限を休業日に適用せず、営業中の販売ゼロや欠測を混同せずに評価できること。実在の休業日に対する性能改善と、架空の機構確認を区別する。

## データの制約と主評価

許可済み10店6/7/10/13/15/17/19/23/26/27のみ、既読2013–2015/原u/250origin/3490観測日/240完全総量を維持。原300fitの4200targetは全正値、2014time120の1680targetも全正値、固定2015の3490観測targetも全正値で、10targetは欠測。原snapshotの元日0は評価開始2015-01-13より前にあり、学習窓にもない。評価開始・target支持を結果に合わせて拡張しない。

許可済みsnapshotとclosed rootsには、予測発行時点で確認できる店舗の営業予定を伴う実在の営業記録がない。holiday flagsは営業予定ではない。評価のoperating_records=[]は「実在営業予定を利用できない」を示し、全日unknownとする。実0をclosedへ分類せず、欠測を0にせず、架空予定を実データへ混入しない。休業ゼロ/営業ゼロの実測性能は今回の250窓では測定不能と明記する。

新しい入力・合成器を導入し、固定主模型は前unitのrolling_calibrated/inner alpha0.2063357718495031。新NN/ridgefit/alpha選択0。旧primaryをreferenceとして保持し、合成器の適用後に250予測をlabelなし保存してから既存labelを付与、一回再集計する。元source・closed rootsを変更しない。

## 営業予定と状態

営業予定はstore/date/status(open,closed,unknown)/known_at/record_id/version取消を持つ既存as-of入力を使う。known_at<=issue_timeの同ID最新版のみ選び、後日版や時刻不明版のpayloadを読まない。競合記録は拒否。予定の出典・公開時刻の真正性は入力提供者が別途確認する契約であり、この処理だけでは認定しない。

量の観測状態はmissing、closed_zero、open_zero、unknown_zero、open_positive、unknown_positiveを分ける。missingは営業状態にかかわらずmissing。closedで観測正値なら営業表と対象販売チャネルの不整合として停止し、値を切り捨てない。祝日や過去実0から営業状態を捏造しない。

発行時に確定closedなら、対象販売チャネルは休業時に販売0という明示契約のもと0を合成する。これはold blendより後・確率/数量getterより前に適用するため、正の基準の79.4%下限が残らない。元label/観測maskは変更しない。closed_implies_zero契約なしは予測nullと理由を返し、部分総量を完全総量と呼ばない。

openは営業確認済みの観測だけからP(販売>0|open)、unknownは休業確認のない観測からP(販売>0|営業状態不明を含む)を扱う。後者は営業日の販売ゼロ確率や営業確率とは呼ばない。支持はfixed fit300のmetadataでstore/target日<2014-07-01を選択後にだけpayloadを使い、missingとclosedを確率推定の分母から除く。14以上の観測・正値とゼロの両classがある時だけp=positive/nを返す。片classや支持不足では推定p=nullと理由、effective reference fallbackとする。架空値で学習支持を補わない。

支持がある時はp_positive×positive_quantity_meanで平均を合成。数量モデルの学習対象/予測時点/営業scopeの適合は呼出し側の明示契約。今回の原NN/ridge学習targetは全正値だが、確率negative classも営業状態ラベルもないため、実在の二部モデルを十分学習したとは認定しない。pが未推定なら元観測販売平均を保持する。p=1を学習済み確率と表示せず、unknownを「営業すると仮定した値」と誤表示しない。

## 保存・確認

新mechanismの架空境界testを先に実行。営業0/休業0/unknown0/欠測、予定future poison/最新unknown/競合、closed予測0で数量getter不要、closed label正値拒否、祝日unknownでも予測保持、欠測総量null、fit metadata先行/0class不足/pの分母を確認。

fresh macos-demand-sales-state-20261015及びexecution/readback/doc-records。契約/source/config/営業予定空入力の理由/状態/学習支持/固定主・元state closure/全予測前後/label分類/summary/stdout/stderr/exit/closure、失敗prefixを保存。原主の2015MSEと新合成器MSEの差・ゼロ評価の非露出を報告する。暫定2%・日次総量非悪化・支持不変を維持し、製品採用を認定しない。

親900秒/子870秒、Mac sampled physical footprint/peakRSS各2GiB、通常artifact24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。全source/root前後不変を確認。2016–17/予約31–54/販促数量/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/追加agentなし。Mac共通機構とWindows固有・OS依存包括testを分離、formal_permission=false/本番採用0。既読開発の探索的評価で未知性能claim0。
