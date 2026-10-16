# 総量両側非悪化を保つ日次配分の四季検証

2026-10-15 JST。人の直接委任「過小非増加維持・通常14日総量MSE/過大も非悪化・2014四季・2014以前調整・同休業mean28・観測only/欠測0分離・Astra別agent確認」に従う。[Astraレビュー](demand-total-preserving-astra-review-2026-10-15.md)を保存してから有限比較を実施する。

基準14日総量B、予測P、未知実績Yについて両側誤差非増加は、既知Yならmin(B,Y)<=P<=max(B,Y)。任意の未知Yで保証するにはP=Bが必要。前回の各日p>=bでは過大量も非減少になり、平均過大量の条件追加だけで非自明な改善を保証できない。今回は旧日次上方制約を14日総量等式へ置換し、人の総量過小非増加を維持する。日々の過小非増加は保証しない。総量MSE/過小/過大は同値・厳密改善ではなく、日次配分のMSE改善を検証する。平均予測候補の二乗誤差評価を維持しquantileへ変更しない。

FIT10=(6,7,10,13,15,17,19,23,26,27)、既読2013–2015だけ。01-01/12-25休業相当仮定、営業unknown、raw0/null、真の観測と欠測0の区別を維持。対照は同mask mean28。閉鎖seasonal rootの2014過去raw予測/2013尺度/全27state（最終250窓・last label2014Dec16）及びshortfall rootの2014校正quarter deltaだけを再利用し、新ridge/NN fitなし。旧変更/失敗/closed rootsを修復/削除しない。

候補順matched_mean28 / ridge_shape / weekly_ridge_shape / level_shape。ridge_shapeはraw ridge、weekly_ridge_shapeはraw14予測を未来の同曜日ごとに平均（休業相当日は平均から除外、7日は既定週周期）、level_shapeは旧seasonal_upliftを用いる。各rawを非休業日だけの非負simplex(sum=同mask mean28総量)へEuclidean射影する。均一level加算は射影で消える場合があり、独立方向を偽らない。週平均はlead揺れを抑える事前仮説で、周期/grid探索をしない。baselineは射影なし。

各候補はp=b+alpha_q*(projection−b)。qは発行日の四半期、同じalphaを全14日に適用。alphaは2014奇数k校正130窓の観測済み非休業日だけから、10店等重み・2013尺度の日次数量MSEの解析解clip[0,1](cov/energy)、分母<=1e-24なら0。各店の数量観測日数で割ってから10店平均し、欠測/休業を学習母数へ混ぜない。target日のquarterで係数を変えない。

2014はJan1+14*k/k0..25の260窓。元日を含む偶数側130は、元日10と通常120（各Q30）に分離。奇数130は校正のみ。校正policyを保存後、各quarterの通常30窓で数量MSE非悪化かつ総量MSE/平均過小/平均過大が対照と一致することを観測only/欠測0仮定それぞれ確認する。Q1は元日10にも同じ条件を課し、元日改善が通常Q1悪化を相殺しないようにする。四季ごとに適格候補の通常joint最小を一度選び、tie1e-12/不適格時baseline。baseline常に適格。元日/年末/全選択130/通常120/校正/四季を別表示。

数値許容差は日次数量MSE/総量MSE1e-12、総量・過小/過大量1e-8販売数量単位。射影とblend後は最大の非休業成分を残差で再計算し総量の丸め差を抑える。全保存予測の実際の最大総量差を保存し、許容差内の指標差は改善と数えず同値と報告する。simplexの非負性/閉鎖0/有限性を検査する。数値誤差以上の総量差は失敗扱い。

全quarter係数・選択方式・source stateを2015入力より先に凍結する。2015の同じ260入力にpを生成しlabel前に保存してから原labelを付ける。通常250と元日10は20店日重複のため合算なし。観測only3490日240総量と欠測0仮定3500採点日250総量を分離し、元日140日10総量も別（欠測なし）。全2015でfit/校正/方式差替えなし。2015の四季も同じ固定policyを記述評価する。未改善ならbaseline結果を保存し、製品採用は認定しない。

fresh macos-demand-total-preserving-20261015及びexecution/readback/doc-records。source/fullstate/校正/選択/label前予測/2label/全stdio/exit/closure/失敗prefixを保存。親900/子870秒/Mac sampled physical footprint・peak RSS各2GiB。artifact通常24files768MiB/全32files1GiB/single32MiB/失敗reserve8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/本番採用は禁止。追加agentは人が明示依頼したAstraのread-onlyレビュー1名のみ（旧no-agent範囲に対する今回の直接許可）。heartbeat PAUSED保持。有限検証・文書閉鎖まで実施する。
