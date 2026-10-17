# 期待数量と総量分位点を分ける次候補の設計（2026-10-14）

## 出力の意味を固定する

[平均・中央値の診断](../results/store-sales-quantity-objectives-2026-10-14.md)を受け、次の公開数量研究では期待値と分位点を明示的に分ける。まだ実装・学習はしていない。

| field | 統計的な対象 | 役割 |
| --- | --- | --- |
| daily_mean[14] | 起点情報に条件付けた各日の期待販売数量 | 日次の平均見込、総量へ加算 |
| total_mean | 同じ情報に条件付けた14日期待数量 | 数量/能力の基準見込。sum(daily_mean)と整合 |
| total_quantiles[Q10,Q50,Q90] | 14日販売量の周辺分位点 | Q50は代表値、上下は確率予測の記述 |
| decision_quantity | 在庫・入庫・納期・ロット・期限・費用から別に決める量 | 現データでは未確定。mean/Q50/Q90から暗黙に埋めない |

meanをQ10–Q90内へclipしたり、mean>=Q50と強制したりしない。分布の歪み次第で関係は変わる。Q50やQ10/Q90を平均してmeanとして返さない。

## 最小接続案

独自の水準/相対変動・暦12要素候補を別namespaceで再利用する。C56/P7/H14/V3/D64/L2、入力契約とas-of境界を保持。

既存総量quantile head64→3とは独立に、mean倍率用64→1 headを加える。mean_total=s*softplus(a)、s=max(mean28総量,0.01*14*固定train平均)。新head weight0、bias=inverse-softplus(1)。名目parameter数120805（現120740+65）の予定で、実装時に確認する。

共有配分headから得るsoftmax配分をmean_totalへ掛けdaily_meanを作る。quantile headのQ50はmeanの日次配分へ使わない。日次Q50は出力しない。この正の配分構造は日次が完全0の境界を有限parameterで正確に表す制約があり、休業を学習済みとしない。数量が0に近い場合の動作は新機構確認へ含める。

原候補の中央値pointや分位点の意味は変更せず、原weights/source/完成学習は反復しない。新候補は独立初期化し、旧候補の性能は保存原結果を参照する。

## meanの学習目的

uを店舗別固定train平均、A_dを実績、A_T=sum(A_d)とする。

`Lmean = 0.5*mean_d(((daily_mean_d-A_d)/u)^2) + 0.5*((total_mean-A_T)/(14*u))^2`

`Lquantile = mean_q(pinball_q(total_quantiles_q,A_T))/(14*u)`

`Ltrain = Lmean + 0.25*Lquantile`

meanの同じ出力にMAEやpinballを重ねず、期待数量の対象を二乗誤差に合わせる。quantileは別出力として補助目的を固定する。重み0.25は本案の事前選択で、testを見た調整や最適値の主張ではない。

自由な日次vectorなら、日次二乗誤差とその和の二乗誤差は、同じ情報に条件付けた期待vectorを最小にする。日間の独立性は不要。ただし有限model・正配分/補正範囲の制約・共通backbone・学習不足では、その最適値へ到達できるとは限らない。平均Bias0も保証しない。

log量にMSEをかけて逆変換した値をmeanとは呼ばない。Huberや実績依存重み・極端値除去もmeanの対象を変える可能性があるので、この案では導入しない。異なる尺度を混ぜる場合のuはtrain固定で、実現したlabelごとの重みを作らない。

## 選択・評価

新実装と少数機構確認後、元991/25/16 origin、保存256×8日付列、AdamW予算・seed等を再固定し、一候補だけの実行へ進む。今回の目的整理では学習しない。

checkpoint選択の主指標はvalidation Lmean。mean評価は日次/14日RMSEとBiasを主に、MAE/WAPEを補助にする。quantileのpinball/coverage/幅/interval scoreは別欄。MAEやWAPEだけでmean headを選ばない。既存候補のQ50とmeanの順位は異なる対象を比べることを明記する。

2017は既に見た回顧期間であり、mean改善を未見確認やメーカー精度にしない。mean headができるまでは、原モデルにmean fieldを作らずnull/未提供として扱う。モデルを替えずにtestのBiasを足してmeanと呼ぶ処理もしない。

実際の発注/生産数量を決める際には、販売実績が潜在需要を表すか、在庫/入庫、リードタイム、ロット、能力、賞味期限と不足/余剰費用を別契約で確認する。公開データだけの研究は、その待ち時間にも継続できる。

実行/記録の既存上限、閉鎖root不変、追加agent0、正式gate不変、automation PAUSED/直接研究ACTIVEを保持。新学習前の実装・機構確認は次unit。ここで採択・正式許可・PSI最適化完了を補わない。
