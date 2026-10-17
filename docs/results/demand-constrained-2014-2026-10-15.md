# 2014制約付き共通残差：全季節ゼロ最適、追加改善なし

2026-10-15 JST。人の依頼に基づき、[事前契約v2](../research/demand-constrained-2014-contract-v2-2026-10-15.md)を成績前に固定し、Astraの確認と人工統合fixture後、既読2014への一巡を完了した。2015の新内容参照・学習・予測・再評価は行っていない。

**4cutoffとも制約付き目的の最適beta=(0,0,0)がexactに検証され、全260予測は同休業仮定mean28と同値だった。四季の過小量・過大量非増加は満たしたが、14日総量MSE・営業相当日の数量MSEとも追加改善0。** 学習時に両側条件を組み込んでも、この固定3特徴/重み/λ/制約の組合せでは有効な補正を得られなかった。

[Astra事前確認](../research/demand-constrained-2014-astra-review-2026-10-15.md)、[実装・結果確認](../research/demand-constrained-2014-astra-result-review-2026-10-15.md)。旧source・model/state・失敗・closed rootsは保持した。

## 成績前に固定した条件

許可10店(6,7,10,13,15,17,19,23,26,27)だけ。既存3特徴、全係数罰則λ1、正規化MSE目的、全pastQの平均under/over≤Bと学習row非負、Q別MSE hard制約なし、後段alphaなし。年をまとめた発行Q別の過去完全labelだけを使い、特徴不支持行もrisk分母へ残す。欠測0で学習しない。

2014Q開始4時点以前の許可prefixだけをfresh copyして学習関数へ渡した。全input/label reader/index/sourcepathは渡さない。後Qで確定済みの過去ラベルを使うことは許可するが、同origin未到来targetを使わず、後のstateを前Qへ適用しない。全4state・全260予測とpinをfreeze markerへ保存してから2014labelを別採点した。

QP core/v2数値入口/独立verifierは不変。新統合v1の支持不足停止・途中予測保存についてAstra指摘を反映した統合v2で、人工8fixture pass後に実データ一巡だけを行った。旧統合v1/6fixture準備はcompleteの履歴として保持し、実データv1再実行や結果後救済はない。

## 後段alpha停止から、制約付き目的のゼロ最適へ

| cutoff | 完全prefix / feature適格 | beta | round / pivot / cut | 正dualを持つactive側 | exact gap |
|---|---:|---|---:|---|---:|
| 2014-01-01 | 210 / 210 | (0,0,0) | 3 / 14 / 7 | Q2over, Q1under, Q4under | 0 |
| 2014-04-01 | 270 / 250 | (0,0,0) | 4 / 24 / 8 | Q1under, Q2over, Q4under | 0 |
| 2014-07-01 | 330 / 310 | (0,0,0) | 3 / 9 / 7 | Q1under, Q4under, Q1over | 0 |
| 2014-10-01 | 400 / 380 | (0,0,0) | 4 / 25 / 9 | Q1under, Q2over, Q4under | 0 |

以前はMSEだけで得た非ゼロbetaの方向をalphaで止めていた。今回はbeta自体を制約内で選んだ上で、厳密なprimal feasibility・dual非負・相補性・stationarity・gap0によりbeta0の最適性を確認した。ridge目的は正定値なので、この符号化済み問題の最適betaは一意である。数値failureや支持不足をBへ置換した結果ではない。

active側は保存された一つの最適性証明に現れる制約で、表にないQが無関係という意味でも、唯一の原因分解でもない。全Q制約を共有betaへ同時に課すため季節間の条件の交差が推定を制限し得る。非ゼロ可行点が全くないことは調べておらず、他の特徴・目的・制約一般の不可能性も示していない。

Astraが確認した数学的含意として、L2罰則の勾配はbeta0で0なので、同じcertificateは同じ可行集合の訓練MSEについてもゼロ最適を支持する。λだけを弱めて訓練MSE改善を回復できるという結果ではない。これは保存証明からの含意で、λ変更や再fitを行ったものではない。

入力不支持はJan1/Jan15の20窓。残り240の適格窓も、学習でbeta0が最適になったため変更なし。outer成績を見たB差替えは0。

## 2014観測のみ・欠測0仮定の結果

下表は候補=Bのため共通の値。主総量MSEはcanonical B/Y/P、店等重みで((P−Y)/(14u))²。平均under/overは元数量単位。数量MSEは非休業相当maskかつ観測された日の((p−y)/u)²。

| 2014群 / label | 観測・採点日 / 完全総量 | 営業相当数量MSE | 14日総量MSE | 平均過小量 | 平均過大量 |
|---|---:|---:|---:|---:|---:|
| all260/observed | 3630 / 250 | 0.094337148064 | 0.023472177931 | 205.258387253 | 132.322898507 |
| all260/assumed_missing_zero | 3640 / 260 | 0.094337148064 | 0.024679842358 | 203.551222359 | 147.345141122 |
| normal250/observed | 3490 / 240 | 0.093001268930 | 0.023185127311 | 189.326543792 | 134.986352611 |
| normal250/assumed_missing_zero | 3500 / 250 | 0.093001268930 | 0.024452580340 | 188.188366040 | 150.502946767 |
| newyear10/observed | 140 / 10 | 0.130200364813 | 0.030361392809 | 587.622630333 | 68.400000000 |
| newyear10/assumed_missing_zero | 140 / 10 | 0.130200364813 | 0.030361392809 | 587.622630333 | 68.400000000 |
| Q1_all/observed | 980 / 70 | 0.109454587999 | 0.012602158510 | 202.486397048 | 97.468387524 |
| Q1_all/assumed_missing_zero | 980 / 70 | 0.109454587999 | 0.012602158510 | 202.486397048 | 97.468387524 |
| Q2_all/observed | 840 / 60 | 0.049764233366 | 0.008466906356 | 163.811141833 | 90.480449833 |
| Q2_all/assumed_missing_zero | 840 / 60 | 0.049764233366 | 0.008466906356 | 163.811141833 | 90.480449833 |
| Q3_all/observed | 980 / 70 | 0.099253641202 | 0.044899171222 | 303.945763857 | 114.974957000 |
| Q3_all/assumed_missing_zero | 980 / 70 | 0.099253641202 | 0.044899171222 | 303.945763857 | 114.974957000 |
| Q4_all/observed | 830 / 50 | 0.115974700272 | 0.026698740401 | 120.713540800 | 255.617270400 |
| Q4_all/assumed_missing_zero | 840 / 60 | 0.115974700272 | 0.031394192508 | 127.406634000 | 300.164593083 |

全12群×2modeの全てで候補/Bのpaired差はexact0。必須に固定したQ別all/normalと元日10の三条件は同値pass。全260/通常250/年末も保存した。全260両modeの厳密MSE減がないのでstrict_total_improvement=false、採用なし。丸め表示の0で判定したのではなく、exactな符号で判定した。

通常250は今回の2014群で、以前の2015の250窓成績とは別。元日10は真観測140日・総量10、元日の販売0全10店を保持。全260 observedは3630日/250総量、欠測0仮定は3640日/260総量。営業相当観測日は両mode3620日、通常は3490日で、欠測0を観測0へ昇格していない。raw0/null/営業unknown、01-01/12-25の休業相当仮定は維持する。

## canonical総量と日次表示

B/Yは既存math.fsumのbinary64値をexact Fractionにした同じ定義。Pも有理数で保存し、主指標は日次float表示を再加算して置換しない。候補/Bで同じ尺度・窓・店重みを用い、旧報告値との差で改善を算出しない。旧float EPSによる判定から今回は厳密符号へ変えることを契約で先に固定した。

Δ0/入力不支持/B0は日次baselineをbitsのままコピーし、canonical BとΣFraction(B_d)の端数差を許す例外として台帳へ保存した。変更時だけexact日次和=Pへ比例配分、P=0<Bは全日0という人工fixtureもpassしたが、今回の実データでは変更窓0なので変更経路の実データ作動はなかった。端数差を改善に数えていない。

## 独立照合と資源・OS結果

新統合8fixture pass（旧6＋支持不足停止/部分保存2）。独立readerはsolverをimportせず、保存prefixから4問題のB/Y/x/目的・制約重みを別に再構築し、4certificateとgap0を再検証した。全260のQ対応、特徴、total、daily配分/copy、mask、ラベル/欠測仮定、2760個の店別/群別scalarとpaired/必須判定を別計算で照合した。exact差0。旧source/state/失敗/closed roots不変も確認。

独立とは実装の別経路でありFractionと既存input/label検証基盤は共通。KKT証明は最適性であり反復/資源履歴の全証明ではない。bit検査は一部累積後、Mac計測はsampled checkpointでOS hard capではない。

| 工程 | child秒 | sampled footprint bytes | peak RSS bytes |
|---|---:|---:|---:|
| 実2014一巡 | 3.235456 | 28,869,064 | 49,152,000 |
| 独立readback | 1.970737 | 28,459,464 | 46,972,928 |

モデルrootは15files/2,475,369B、complete。親900/子870秒・footprint/peak RSS各2GiB・既存artifact/EvidenceStore上限は工程ごとに維持。全工程合計900秒という意味ではない。全stdio/exit/source/4state/260予測/freeze pin/label別metric/closureを保存。

共通Mac/Python3.14.8は人工統合・一巡・独立readback pass。Windows固有/nativeおよびOS依存包括suiteは未実行（Mac資源測定のみ）。依存導入/環境lock変更なし。文書のGit diff検査は同梱Gitを明示し、Xcode同意/設定変更なし。

今回の固定仕様は一巡完了。全Bは安全性・予測力・性能改善の証拠ではなく、既読2014の探索的診断で独立性は回復しない。結果後の特徴/λ/期間/制約/閾値/上限救済、別候補、2015確認は起動しない。新仮説や別評価契約が必要だが今回の結果から自動接続しない。heartbeat PAUSED、PSI製品採用なし。

旧変更/失敗/closed roots保持・未commit/push/削除。2015新内容decode/fit/予測/再評価0、2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/研究データ外部送信/本番採用なし。

証拠：[model](../../artifacts/macos-demand-constrained-2014-20261015/summary.json)、[freeze](../../artifacts/macos-demand-constrained-2014-20261015/freeze-before-scoring.json)、[execution](../../artifacts/macos-demand-constrained-2014-20261015-execution-records/root-closed.json)、[readback](../../artifacts/macos-demand-constrained-2014-20261015-readback-records/root-closed.json)、[準備v1](../../artifacts/macos-demand-constrained-2014-20261015-preparation-records/root-closed.json)、[準備v2](../../artifacts/macos-demand-constrained-2014-20261015-preparation-v2-records/root-closed.json)、[文書](../../artifacts/macos-demand-constrained-2014-20261015-doc-records/root-closed.json)。
