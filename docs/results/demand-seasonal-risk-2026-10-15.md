# 四季平均の両側制約付き総量補正・改善支持なし

2026-10-15 JST。[事前契約](../research/demand-seasonal-risk-design-2026-10-15.md)と[Astraレビュー](../research/demand-seasonal-risk-astra-review-2026-10-15.md)に従い、総量固定を外した有限比較を完了。2014各季節の平均過小量・平均過大量を増やさず総量MSEを下げる条件を、事前固定3候補で検証したが、主として選べる補正は残らず全四季mean28となった。2015の主は観測only/欠測0仮定とも同じ休業仮定mean28と一致し、総量MSE改善0。これは総量を構造的に固定した結果ではなく、符号付き総量補正が校正又は選択条件で棄却された結果。負の結果も保存し、2015による係数縮小・候補追加・方式再選択を行わない。

## Astra確認・今回の条件

今回も人の明示依頼でgpt-6-astraの既存read-only agent /root/astra_method_reviewに設計確認した。mean28基点のsigned rawと直近14日候補、凸区間とMSE解析解、通常四季別選択/元日別報告、欠測感度、停止条件に賛成。旧選択済みshapeには既に選択側labelを使っているため新基点へ組み込まないという助言も採用した。編集/実験/追加agentはさせていない。

旧全窓保証を、人が今回明示した「2014通常四季の平均条件」へ変更。各窓予測p=(1−alpha)*mean28+alpha*rawで総量差は正負を許す。両端の非負/休業0は維持。平均条件では同季節内の窓・店で相殺が起き、個別窓/各店/元日/2015/将来の非悪化保証はない。量の平均予測候補を総量二乗損失で調整し、quantileへ変更しない。

固定FIT10店/既読2013–2015のみ、01-01/12-25休業相当、営業unknown、raw0/nullを維持。rawは旧2014過去26fitと最終2015Jan1前250窓/last label2014Dec16のstateから保存済み値を再利用。新ridge/NN fit0。recent14は発行日前14日だけの非休業・観測曜日平均で最低2件、足りない曜日はmean28へfallback。真の非休業0は保持し欠測と区別。14日は既定予測長で期間gridなし、曜日支持は最大2日。

## 係数校正と四季選択

2014Jan1+14*k/k0..25の260窓。奇数130は校正だけ、完全な真の14labelで総量係数をfit。Q1/Q2/Q3/Q4の支持は30/30/40/20窓（各店3/3/4/2）。店等重みの平均過小/過大を基準以下とするalpha0..1の凸適格区間を折点走査で求め、総量MSE解析解を一回clipした。初期傾き・折点・制約上限・標本・energy/covarianceを保存。係数は発行日のquarterで全14日共通。欠測0仮定をfitへ混ぜない。内部尺度は2013観測平均、2015採点尺度は旧u。

偶数130は通常120（各Q30）と元日10を分ける。各Qで観測only/欠測0仮定それぞれ総量MSE/平均過小/平均過大の非悪化をgate。適格候補の総量MSE最小、tieはbaseline、不適格ならQごとmean28へ戻す。選択側で係数を縮め直さない。選択群に欠測はなく両scenarioが同値で、独立な頑健性証拠ではない。元日10は報告のみで係数/選択へ使わず、元日改善で通常Q1の悪化を隠さない。

| 校正Q | 候補 | 制約なし最適alpha | 両側制約上限 | 固定alpha | 完全実観測窓 |
|---|---|---:|---:|---:|---:|
| Q1 | signed_raw_blend | 0.273513340185 | 0.000000000000 | 0.000000000000 | 30 |
| Q1 | signed_recent14_blend | 0.564405552058 | 0.977003275369 | 0.564405552058 | 30 |
| Q2 | signed_raw_blend | 0.924280921097 | 1.000000000000 | 0.924280921097 | 30 |
| Q2 | signed_recent14_blend | 1.197778685935 | 0.585329220951 | 0.585329220951 | 30 |
| Q3 | signed_raw_blend | 2.168041829620 | 0.000000000000 | 0.000000000000 | 40 |
| Q3 | signed_recent14_blend | -1.801685278378 | 0.000000000000 | 0.000000000000 | 40 |
| Q4 | signed_raw_blend | 0.843932137239 | 1.000000000000 | 0.843932137239 | 20 |
| Q4 | signed_recent14_blend | 0.954066867297 | 1.000000000000 | 0.954066867297 | 20 |

Q1 rawは校正で過大量の初期傾きが正となり適格上限0。Q3はraw/recent14とも過小量の初期傾きが正となり上限0（recent14はMSE側の最適方向も負）。Q2/Q4では正の係数が校正で残ったが、次の別選択で棄却された。

| 2014通常選択 | 候補 | 総量MSE | 平均過小量 | 平均過大量 | 適格 |
|---|---|---:|---:|---:|---|
| Q1 | matched_mean28 | 0.004343371819 | 57.160966333 | 125.682632667 | yes |
| Q1 | signed_raw_blend | 0.004343371819 | 57.160966333 | 125.682632667 | yes |
| Q1 | signed_recent14_blend | 0.006528495324 | 54.632498410 | 152.568687244 | no: observed/total_MSE,observed/over,assumed_missing_zero/total_MSE |
| Q2 | matched_mean28 | 0.006851491543 | 184.831098833 | 55.360733333 | yes |
| Q2 | signed_raw_blend | 0.007375436356 | 153.693815775 | 90.277786264 | no: observed/total_MSE,observed/over,assumed_missing_zero/total_MSE |
| Q2 | signed_recent14_blend | 0.007591858504 | 201.376267553 | 57.766846357 | no: observed/total_MSE,observed/under,observed/over |
| Q3 | matched_mean28 | 0.040074978588 | 298.500832333 | 93.699198667 | yes |
| Q3 | signed_raw_blend | 0.040074978588 | 298.500832333 | 93.699198667 | yes |
| Q3 | signed_recent14_blend | 0.040074978588 | 298.500832333 | 93.699198667 | yes |
| Q4 | matched_mean28 | 0.034253483186 | 147.333084000 | 231.673083500 | yes |
| Q4 | signed_raw_blend | 0.025065623662 | 148.484738672 | 192.785160986 | no: observed/under,assumed_missing_zero/under |
| Q4 | signed_recent14_blend | 0.025779522548 | 194.607470433 | 183.745748409 | no: observed/under,assumed_missing_zero/under |

Q2 rawは過小量を減らす一方で過大量55.360733→90.277786、総量MSEも悪化。recent14はQ1で総量MSE/過大量、Q2で3条件とも悪化。Q4 rawは総量MSEを26.823139%改善し過大量も減ったが、平均過小量147.333084→148.484739（+1.151655）で不適格。Q4 recent14も過小量増加で不適格。Q1 raw/Q3両候補はalpha0の同点なのでtie順でmean28。

全通常120をまとめるとrawは総量MSE10.130470%改善・平均過小量7.496407減・平均過大量0.992717減となる。しかしQ2/Q4の条件違反が隠れるので採用しない。四季条件を全体平均に置換せず維持した。

## 2014校正Q4の欠測0感度（係数fit/追加guardには使用しない）

Q4の校正発行日は3つだがChristmas欠測窓を除いた実観測総量は各店2つのみ。欠測0仮定は別の感度評価として以下を保存。真の観測0への昇格はしない。

| Q4校正のlabel条件 | 候補 | 完全総量 | 総量MSE | 平均過小量 | 平均過大量 |
|---|---|---:|---:|---:|---:|
| observed | matched_mean28 | 20 | 0.015366626224 | 80.784226000 | 291.533550750 |
| observed | signed_raw_blend | 20 | 0.011015217366 | 67.519214881 | 193.312318083 |
| observed | signed_recent14_blend | 20 | 0.010364290886 | 37.007377758 | 228.792595890 |
| assumed_missing_zero | matched_mean28 | 30 | 0.028534901831 | 107.480184000 | 368.656102667 |
| assumed_missing_zero | signed_raw_blend | 30 | 0.021754938391 | 89.155501692 | 291.577668487 |
| assumed_missing_zero | signed_recent14_blend | 30 | 0.034245178796 | 72.140670706 | 341.169291460 |

この追加表は閉鎖した予測/labelの記述診断だけであり、係数や選択を変更していない。校正の全Q/全2014/年末/元日も両labelでartifactに保存した。

## 2015凍結主・観測only/欠測0分離

方式/係数を2015入力より前に保存し、全候補予測をlabel前保存してから評価。主は全Qmean28となった。原250と元日10には20店日重複があり合算しない。元日当日の0、原null、営業unknown、休業相当仮定を保持。欠測0仮定で追加したChristmas10日は数量観測の母数へ加えない。

| cohort / label | 真の観測/採点日 | 完全総量 | 主総量MSE | mean28総量MSE | 平均過小量 | 平均過大量 |
|---|---:|---:|---:|---:|---:|---:|
| original250/observed | 3490/3490 | 240 | 0.020878675703 | 0.020878675703 | 162.484107236 | 166.248529576 |
| original250/assumed_missing_zero | 3490/3500 | 250 | 0.021120844073 | 0.021120844073 | 160.301623947 | 176.761292453 |
| newyear10/observed | 140/140 | 10 | 0.038582955907 | 0.038582955907 | 613.433209000 | 64.906833333 |

元日には欠測がなく欠測0仮定も同値。主は2015の四季それぞれ3指標とも対照同値、総量MSE改善0。通常数量MSE0.134053954571/元日0.283224941162、数量MAE48.845588649/76.159638923も対照同値。今回の総量候補比較がbaselineという結果であり、前回の総量保存shapeによる数量0.556694%改善結果とstateは別成果物として保持している。

| 2015観測条件 | 候補 | 総量MSE | 平均過小量 | 平均過大量 |
|---|---|---:|---:|---:|
| original250 | matched_mean28 | 0.020878675703 | 162.484107236 | 166.248529576 |
| original250 | signed_raw_blend | 0.023335564156 | 202.094406385 | 151.240078862 |
| original250 | signed_recent14_blend | 0.021529637640 | 163.787693345 | 170.683341901 |
| newyear10 | matched_mean28 | 0.038582955907 | 613.433209000 | 64.906833333 |
| newyear10 | signed_raw_blend | 0.038582955907 | 613.433209000 | 64.906833333 |
| newyear10 | signed_recent14_blend | 0.072888643517 | 768.701968796 | 111.781956124 |

事前副候補も保存したが2015後に主へ差し替えない。今回の副も2015で一貫した改善ではなかった。

## 検証・保存・区切り

macos-demand-seasonal-risk-20261015: complete、23files / 9,914,093B。新9fixture pass。独立読戻しは別の等価条件delta_MAE+alpha*abs(mean(D))と90回二分探索で適格上限を照合、scalar MSE係数・店等重み/完全支持30/30/40/20・recent14過去範囲/0/null/fallback・通常120/元日別扱い・四季選択・2015凍結260予測・128群scalar MSE/MAE/bias/数量/under/over/分解恒等式・元27state/失敗/source不変を確認。上限/alphaの最大独立差2.220446049250313e-16、予測差0。

child 7.339277秒、sampled peak physical footprint 214,434,608B、peak RSS 231,047,168B。親900/子870秒/各2GiB/保存上限内。全stdio/stderr/exit0/source/Astraレビュー/state/closureをexecution/readback/doc-recordsへ保存。Mac resourceはOS hard limit/Windows private bytesではない。

共通Mac研究のfixture/評価/読戻しはpass。Windows固有機能/Windows nativeは対象外・未実行。OS依存包括suiteの新実行なし、Mac resource計測のみ。既存変更/失敗/closed roots保持、未commit、2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部送信/Git push/削除/本番採用なし。Astra確認は人の明示依頼によるread-only 1名のみ。heartbeat PAUSED保持。

事前の停止条件を満たしたため、この3候補の工程は文書閉鎖まで完了して終了する。改善を得るためにQ4の小さな過小増を許したり、選択側でalphaを縮め直したり、2015で期間/係数/候補を選ばない。今回支持されなかった理由は、校正方向の両側トレードオフと季節内の時間的再現性不足。これは平均制約下の総量改善一般が不可能という証明ではない。新規仮説/独立した内部検証支持なしに同じ探索を反復しない。

証拠: [model](../../artifacts/macos-demand-seasonal-risk-20261015/summary.json)、[execution](../../artifacts/macos-demand-seasonal-risk-20261015-execution-records/root-closed.json)、[readback](../../artifacts/macos-demand-seasonal-risk-20261015-readback-records/root-closed.json)、[doc-records](../../artifacts/macos-demand-seasonal-risk-20261015-doc-records/root-closed.json)。
