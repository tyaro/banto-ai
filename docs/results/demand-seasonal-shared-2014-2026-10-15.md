# 季節内10店共有：4解と260予測を保存、採点は桁数上限で未完了

2026-10-15 JST。[事前契約](../research/demand-seasonal-shared-2014-contract-2026-10-15.md)を固定し、許可10店・2014以前だけから季節別3係数を推定した。2015再評価は停止を維持した。

**全4季節で非ゼロの厳密最適解を得て260窓の予測を凍結したが、2014評価の有理数集計が8192bit上限に達した。性能改善・悪化・四季条件通過は未判定。停止規則に従い21件の削除感度fitは起動していない。**

[Astra実装・結果確認](../research/demand-seasonal-shared-astra-result-review-2026-10-15.md)と[決定表](../research/demand-seasonal-shared-decisions-2026-10-15.json)を保存した。モデル不成立や少数窓への実測不安定性という結論に置き換えない。

## 固定した適用条件

発行Qの開始cutoffより前に完結・利用可能な同Qだけをfresh payloadとし、10店で3係数を共有する。3特徴/λ1、目的w=1/(10nE)、risk v=1/(10nI)。当Q内の平均過小量・過大量≤同休業仮定のmean28と学習非負を直接制約する。各店の適格支持≥1は構造要件で統計的十分性ではない。QMSE hard追加/後alpha/総量固定/探索/結果後のB差替えなし。発行Q係数を14日全体へ使用する。

01-01・12-25休業相当、営業unknown、raw0/nullの区別を継承した。欠測0仮定は休業相当位置だけ別評価とし学習には使わない。2014全260/通常250/元日10/四季all-normal/年末と2modeの比較を事前固定したが、今回はmetricsを確定できていない。前回の共通係数beta0の2014数値を新候補の成績として転記しない。

## 確定できた学習・予測

| Q開始 | 過去適格窓 | 発行日 | β切片・水準差・週変化（表示） | rounds/pivots/cuts |
|---|---:|---:|---|---|
| 2014-01-01 | 30 | 3 | (6.6554658e-05, 0.00258502099, 0.000693329825) | 4/12/3 |
| 2014-04-01 | 60 | 6 | (-0.000120706423, 0.00218349191, 0.00335555763) | 2/5/1 |
| 2014-07-01 | 70 | 7 | (-8.81544714e-05, 0.00251419824, 0.00351321454) | 2/5/1 |
| 2014-10-01 | 50 | 5 | (-1.70553986e-05, 0.000457334571, 0.000495922719) | 4/11/3 |

全4stateは元hinge・非負・全cut・KKT/gap0を独立照合した。係数のexact値・problem・certificateはstateに保存した。各自Qで非ゼロ可行/最適解が存在することは確認できたが、2014予測性能の保証ではない。係数共有解除だけでなく目的データと制約対応も変えているので単独の因果効果とは呼ばない。

4stateとQ別予測、全260予測・pinを保存してから2014labelを読んだ。独立readerで260予測の入力支持・canonical総量・日次比例配分/fallback端数例外を照合した。観測rawnull10、休業相当位置への欠測0仮定10、元日真0が10店を確認した。元日を含む2014予測は保存済みだが、元日成績も未判定である。

## 停止箇所と証跡の限界

`stage=2014-label-scoring`、`NumericFailure: bit_length_limit`。`score_group`が店別指標を店平均macroへ集計した後、5指標を一括検査する箇所で停止した。どの指標/候補対照が閾値に達したかはtraceに残っていない。異なる有理数分母の合算で表現桁数が増える機構であり、値の発散や不安定係数を示すものではない。

evaluation.json/summary.jsonは生成されず、四季平均の過小量・過大量非増加、総量MSE非増加、年間厳密改善はすべて未判定。部分集計を採否に流用せず、8192bitの緩和/float EPS/候補再fit/再採点による救済を行っていない。primaryとexecution記録はfailedのままimmutable閉鎖し、readbackのpassと区別する。

Primaryの子stdout/stderr/exit1、source、4state、260予測、freeze、2014 scoring-labels、failure/進捗/closureは保存した。失敗時の最終resource snapshotは既存失敗保存経路に含まれず、最終peak footprint/RSSとelapsedの記録が欠ける。ガード呼出しと親900/子870秒設定はあるが、この実行全体の資源遵守は記録から断定しない。将来の新契約では失敗時resourceも保存する。

## 少数発行日への依存：確認できた範囲

| Q | 完全/適格窓 | 異なる発行日（全て2013） | 同日10店を除く元目的質量 | 元risk質量 | 実測削除fit |
|---|---:|---:|---:|---:|---:|
| Q1 | 30/30 | 3 | 1/3 | 1/3 | 0 |
| Q2 | 60/60 | 6 | 1/6 | 1/6 | 0 |
| Q3 | 70/70 | 7 | 1/7 | 1/7 | 0 |
| Q4 | 50/50 | 5 | 1/5 | 1/5 | 0 |

各店で同じ発行日が等重みであり、特徴適格の目的と全completeのriskを別々に再合成して上表を確認した。1発行日が14.3〜33.3%の元重みを占める。削除後は再正規化するため、この割合は予測変化率ではない。10店×30〜70窓を独立Nとせず、発行日も独立とは認めない。

事前固定の21通り（3+6+7+5）はPrimary完成後の別工程であり、今回は開始条件を満たさず未実施。係数差/総量差/RMS/変化窓数などの実測感度は未評価、小さい/大きい/安定/不安定の判定なし。成功foldだけを抽出する処理もしていない。p値/CI/bootstrapは未実施。

## 検証と今後の工程

独立readerはsolver未importで4問題再構成・4証明・260予測・260窓のlabel-scenario・21発行日の元重み質量・旧source/closed roots不変を照合した。再採点scalar0・削除fit0・2015新decode/fit/予測/評価0。

人工fixtureは旧v1準備11件とv2準備11件を保持。Astraによりv2準備のprimary8件がv1入口だったことが判明し、説明を訂正した。実行後の別recordでv2入口primary8件＋influence4件=12件passを確認した。数値仕様や保存予測を変えていない。

独立readbackは1.664560秒、sampled footprint 29,000,136B、peak RSS 52,822,016B。このreaderは各2GiB以内。artifact/EvidenceStoreは従来ファイル・容量上限内に保存し、全既存変更/失敗/closed rootsを保護した。

次は採点の一括通分を避ける別数値契約と人工stress fixtureを先に固定する。Astra第一案はexact項保持＋事前固定精度の上下界でpaired差符号を証明し、0を跨ぐ場合は未判定、完全同値は別証明とするもの。今回未実装/未適用である。新契約後も保存済み260予測だけの別再採点工程とし、元failed rootの書換え/再fit/2015再開をしない。Primary判定が完成するまでは削除診断を起動しない。

共通Mac/Python3.14.8：推定4解/260予測の独立検証と人工12件pass、評価pipelineは上限停止。Windows固有/native：未実行。OS依存包括suite：未実行（Mac資源API測定はreadbackで実施、Windows private bytes相当とはしない）。

heartbeat PAUSED、PSI採用なし。2016–17/予約31–54/販促/正式holdout/CARE/課金API/新データ取得/外部研究データ送信/commit/push/削除なし。依存lock/Xcode変更なし。今回の一巡はfailed保存と独立照合・記述診断で終了し、新方式へ自動接続しない。

証拠：[primary failure](../../artifacts/macos-demand-seasonal-shared-2014-20261015/root-closed.json)、[stdio/exit](../../artifacts/macos-demand-seasonal-shared-2014-20261015-execution-records/root-closed.json)、[readback](../../artifacts/macos-demand-seasonal-shared-2014-20261015-readback-records/root-closed.json)、[人工事後確認](../../artifacts/macos-demand-seasonal-shared-2014-20261015-postrun-fixtures-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-seasonal-shared-2014-20261015-doc-records/root-closed.json)。
