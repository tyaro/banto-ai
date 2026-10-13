# 小型独自モデルの一回探索と研究上の結論（2026-10-14）

## 研究目的に対する到達点

TimesFM3の関連公開構造を参考にした、独立初期化の小型多変量モデルを実装し、独自recipeで学習・checkpoint選択・予測まで完走できた。
これは「独自の小型実装・独自学習は可能か」への具体的な前進。TimesFM3の公式構造全体、公式の事前学習、汎用zero-shot、同等性能の再現成功ではない。元重み・教師出力は使っていない。
[設計](timesfm3-small-model-design-2026-10-13.md)、[実装確認](timesfm3-small-model-implementation-2026-10-13.md)、[学習前準備と元失敗](timesfm3-small-model-preparation-2026-10-14.md)。

今回の探索を完了して自走を停止する。人の「進めなくなった場合止める」に従い、次の実用性研究に必要な対象信号・先読み時間・予測で変える判断が未確定な地点を保存する。一般heartbeatだけで学習延長・grid・別seedを始めない。既存automation設定はPAUSEDであることを読取り確認し、変更していない。
別期間の機構確認という研究経路も可能だが、今回のtestを見た調整や用途の決め打ちには進まない。

## 実行と選択

計算checkout9490b5c4f0c32f9db5dc377dda441b1f891369b2、開始時clean。3target/C128/H32/P32/D64/L2/Q3、CPUfloat32。各109024登録parameter、同じ初期state/共通128×8 train origin列。
同stepでfullとdiagonal self-onlyを進め、各128optimizer stepを完了。既存モデル評価・10構造確認・準備確認・CIの反復0。
step32/64/96/128でvalidationし、固定train-only尺度のpinball最小を個別選択。その後探索testは各一回。選択checkpointを保存SHAへ照合し、自己生成stateをweights_onlyで読んだ。

| 構成 | 選択step | validation固定尺度pinball | test固定尺度pinball |
|---|---:|---:|---:|
| full | 128 | 0.2463354667 | 0.2267646790 |
| self-only | 64 | 0.2503388193 | 0.2326977849 |

fullはtest集約が約2.55%低い。ただし同じ探索予算から個別選択した構成の比較で、同一選択stepや同一実効自由度とはしない。
1seed/同設備1日、test9origin×32lead。labelは重ならないがcontextと運転は依存し、9区間/288点を独立した設備試行と数えない。bootstrap/有意差/勝者/方式採択0。

## 点予測の比較

MAEを原単位ごとに示す。異なる単位のMAEを平均しない。点baselineは同じ新C128/H32/originで計算した。

| target（単位） | full | self-only | last-value | moving-average15 |
|---|---:|---:|---:|---:|
| tp3（bar） | 0.412516 | 0.434678 | 0.680031 | 0.551116 |
| oil_temperature（ºC） | 1.645048 | 1.631667 | 1.856444 | 1.383669 |
| motor_current（A） | 1.418997 | 1.449702 | 1.523530 | 1.721394 |

圧力と電流ではfullが小さい。油温のMAEはself-onlyが僅かに小さく、移動平均15が両モデルより良い。
系列間経路の追加価値がある可能性は見えたが、全targetでの優位性・大規模化の必要性は示していない。
旧TimesFM3のC120/H15/11共変量結果とは条件が異なり、今回の数値を直接並べて同等性能/優劣を出さない。TimesFM3自体の実用性への新しい直接評価ではない。

## 分位点と外れ方向

WISはQ3における中央値＋80%区間の定義（2×mean pinball）。区間幅・coverageは校正済みの認証ではない。

| target | full WIS | self WIS | full coverage80 | self coverage80 | full幅 / self幅 |
|---|---:|---:|---:|---:|---:|
| tp3 | 0.261773 | 0.274513 | 76.39% | 72.57% | 1.314800 / 1.218274 bar |
| oil_temperature | 1.114436 | 1.124579 | 57.99% | 53.82% | 3.794245 / 3.505930 ºC |
| motor_current | 0.875181 | 0.889077 | 81.25% | 73.61% | 4.545221 / 4.196002 A |

油温ではfullのpinball/WISが少し小さく、幅も広い一方、名目80%coverageを下回る。
288点のうちfullは下限未満113/上限超過8、selfは下限未満122/上限超過11。外れは実測が予測下限より低い側へ偏っている。
今回のtestを使った再校正・recipe変更・再学習はしていない。点予測と確率予測の結論を分ける。

## 保存済み予測だけによる9originの内訳

Astraの読取り批評を反映し、保存済み予測から27origin-target行を一度抽出した。model forward/学習/新test評価/観測本文再読取りは0。
fullのMAEが小さいoriginはtp3で8/9、油温4/9、電流6/9。改善が全target/全windowに一様とはしない。
以下は保存float32出力をPython floatで集計した記述値。CIや母集団推定ではない。

| origin | target | full MAE | self MAE | full下限未満/上限超過 | self下限未満/上限超過 |
|---:|---|---:|---:|---:|---:|
| 1152 | tp3 | 0.434019 | 0.476454 | 7/1 | 8/1 |
| 1184 | tp3 | 0.293439 | 0.327939 | 4/0 | 4/0 |
| 1216 | tp3 | 0.304119 | 0.354656 | 2/3 | 4/4 |
| 1248 | tp3 | 0.468550 | 0.477069 | 1/7 | 2/7 |
| 1280 | tp3 | 0.657577 | 0.632413 | 12/6 | 10/6 |
| 1312 | tp3 | 0.379359 | 0.420913 | 12/0 | 13/0 |
| 1344 | tp3 | 0.291533 | 0.309028 | 0/0 | 0/1 |
| 1376 | tp3 | 0.470902 | 0.487510 | 7/0 | 8/2 |
| 1408 | tp3 | 0.413149 | 0.426124 | 5/1 | 6/3 |
| 1152 | oil_temperature | 2.410050 | 2.460185 | 26/0 | 27/0 |
| 1184 | oil_temperature | 1.592687 | 1.626975 | 11/0 | 11/0 |
| 1216 | oil_temperature | 1.327205 | 1.310560 | 6/0 | 9/0 |
| 1248 | oil_temperature | 1.424895 | 1.377432 | 9/7 | 7/8 |
| 1280 | oil_temperature | 1.342934 | 1.415598 | 12/1 | 12/2 |
| 1312 | oil_temperature | 1.950799 | 1.995806 | 21/0 | 20/0 |
| 1344 | oil_temperature | 1.583137 | 1.549572 | 8/0 | 14/0 |
| 1376 | oil_temperature | 1.718672 | 1.601933 | 11/0 | 13/0 |
| 1408 | oil_temperature | 1.455055 | 1.346938 | 9/0 | 9/1 |
| 1152 | motor_current | 1.407855 | 1.453844 | 2/2 | 5/2 |
| 1184 | motor_current | 1.290791 | 1.372181 | 4/1 | 4/1 |
| 1216 | motor_current | 1.212379 | 1.238510 | 1/2 | 2/2 |
| 1248 | motor_current | 1.849922 | 1.742583 | 3/5 | 6/6 |
| 1280 | motor_current | 1.891280 | 1.676666 | 6/4 | 6/6 |
| 1312 | motor_current | 1.191893 | 1.154487 | 7/0 | 8/0 |
| 1344 | motor_current | 1.087623 | 1.318324 | 0/3 | 3/7 |
| 1376 | motor_current | 1.490540 | 1.566443 | 3/6 | 4/7 |
| 1408 | motor_current | 1.348687 | 1.524281 | 0/5 | 0/7 |

## 資源、失敗、原保存

実CPython3.14.0/WindowsAMD64/Torch2.14.0+cpu。
model process elapsed10.137896秒、親11.307083秒。full学習1.399637秒/validation0.101161秒/test推論0.055764秒、self学習1.385660秒/validation0.111835秒/test推論0.069392秒。短い局所計測で本番throughputへ外挿しない。
OS private998944768B / peak pagefile1033314304B / peak working set318038016B。
output23file4409682B、closure2617B/SHA3f99aa53e7278c899a796918511e5849a877027212d40a5118dd024ed00a98c3。
実行900秒/private2GiB/output1GiB/single32MiB/files32、normal24/failure8とEvidenceStore上限不変。checkpoint測定はblocking/global/native容量証明ではない。

- output: artifacts/representative-small-model-training-20261014（閉鎖、summary candidate-complete＋root-closed complete）
- 実行raw: artifacts/representative-small-model-training-20261014-execution-records（閉鎖）
- 保存予測の内訳: artifacts/representative-small-model-training-20261014-analysis-records（閉鎖）
- 本文保存: artifacts/representative-small-model-training-20261014-doc-records
- Git後: artifacts/representative-small-model-training-20261014-git-records のpost-save/root-closed

各23outputのbytes/SHA、実行source4fileとの一致、原closureと実summaryを照合。モデル工程failure0。
準備の元sandbox失敗と二次cleanup例外は原rawを保持しており、今回成功へ書換えない。closed root追記/完成helper・モデル再実行0。親起動warning/誤ったautomation path読取りはtool観測でモデル/CI失敗にしない。foreground fullcreation/fullstdioは未捕捉と区別する。
Astraはread-onlyで設計・保存経路・結果を批評。新agent・追加モデル実行はしない。

## 次に必要な入力

実用性を主問として進むなら、対象設備/信号、何分先まで、予測を使って何を判断するかを具体化する必要がある。32分は今回の構造探索用で運用要件ではない。
次はその用途に合う未評価の運転区間・基準・許容誤差を固定する計画。現在のtestを見た調整と同じtestへの再評価はしない。
単日探索を根拠にTimesFM3代替/商用権利適合/方式採択/正式受入を宣言しない。
PAUSED / formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / 登録holdout未読 / native reader禁止。
