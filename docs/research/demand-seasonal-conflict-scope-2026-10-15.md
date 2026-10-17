# 共通係数と四季制約の干渉：診断の事前範囲

2026-10-15 JST。人の依頼は2015停止のままAstraと原因分析・季節別学習方法の検討、統計分析の有用性の確認。今回は保存済み4問題/証明の記述診断と設計まで。季節別の新fit・係数最適化・候補予測・2014再評価・2015内容decode/再評価は行わない。

## 成績を見る前に定める診断

各cutoffの保存problemを使う。Q内の適格行重みをw_q=4*w_global=1/(10*nE_qs)として和1にし、L_q=Σw_q(r−xβ)²+||β||²、r=(Y−B)/unitと定義する。原点でg_q=−2Σw_q*x*r。元共通目的の原点勾配は(1/4)Σg_qで、λ1罰則の勾配は原点0。

調べる方向は各qについてd_q=−g_qの計4本だけ。別方向の探索・方向最適化・制約除去後のsolveをしない。各target Qの元数量risk重みv=1/(10*nI_qs)で、e=B−Y、z=unit*x*d（入力不支持/B0はz0）のunder/over右方向微分をexactに計算する。e=0はunder=max(−z,0)、over=max(z,0)を保持。B0でz<0なら非負違反とする。

g_q≠0、自Qの両側微分≤0かつ非負方向を満たし、他Qの側の微分>0があれば「この固定方向についての季節間制約干渉witness」とする。自Qで違反する場合は自Q内でもこの方向が止まる、とだけ結論し、別の可行方向がないとは言わない。

自Qで通る方向には、有限個のhinge符号が変わらない正stepと非負を保つ正stepが存在することを有理数の上限で確認する。L_q(td)−L_q(0)=t*g_q·d+t²A、A=Σw_q(x*d)²+||d||²。0<t<−g_q·d/A、t<|e/z|（e,z非0）、t<B/(−z)（z<0,B>0）の各上限の半分と1を用いた保守的正上限を保存する。実際のモデル係数t*dや予測・成績は生成しない。

既存certificateの正dual/active側は補助的な構造情報。複数Qが現れたことだけを原因の証明にしない。原点stationarityのベクトル恒等式は保存証明から照合する。Q別gradientの内積符号/cosineは記述値で、異質性の有意検定ではない。

## 統計的な支持・寄与の記述

各Qのcomplete/eligible窓、異なる発行日/年度、店別窓数、正規化残差の平均/絶対平均、店/発行日ごとの残差・勾配寄与を保存する。絶対残差寄与の最大店/最大発行日比率は集中度の記述で独立Nではない。学習に使うcurrent Qの年度/発行日数を別表示する。同発行日10店や重なる過去contextを独立標本としない。

p値・ANOVA・独立t検定・bootstrap・block長探索・係数選択は起動しない。統計的区間や再標本化の設計は別途固定する。既読2014の適応的再利用は独立検証に戻らない。現行候補=Bのpaired差0をbootstrapしても新たな改善証拠にはしない。

## 保存・終了

既存source/state/失敗/closed rootsを上書き削除せず、fresh EvidenceStoreへ全stdio/exit/source/旧state pin/closure/記述結果を保存。親900/子870秒、Mac sampled footprint/peak RSS各2GiB、旧EvidenceStore16MiB/512files/part256KiB/failure2MiB16files。新model artifactなし。方向微分等の有理数にもbit8192を確認。

witnessの有無にかかわらず診断を終了し、季節別学習の第一設計と統計計画を保存する。同休業mean28/raw0-null-unknown/休業相当01-01・12-25/観測のみと欠測0仮定の評価分離/欠測0学習0を維持。Windowsnative・OS依存包括suiteは対象外、heartbeat PAUSED。2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/push/採用なし。
