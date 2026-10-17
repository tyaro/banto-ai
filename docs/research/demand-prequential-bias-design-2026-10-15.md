# 発行日前に確定した誤差による店舗別bias更新

2026-10-15 JST。人の声かけまで自走する指示により、時間変化に対する更新方法を一件検証する。旧リッジ/旧NNを学習し直さず、新年度/未読holdoutを使わない。

## 固定する方法

参照はmean28と元NN3328。保存済みの各14日予測が完了した後に、その予測−実績をuで正規化した日次誤差を記録する。origin前56日以内で、かつ予測窓全体がorigin前日に終了した記録だけを使用する。欠測日の誤差は追加しない。全窓の完了を確認してから誤差を入れ、current/future labelsを更新器へ渡さない。
完了はcalendar上の14日末日が経過したことを指し、全labelの観測を要求することではない。欠測日は引き続き誤差記録に入れない。同店の記録が14観測日以上あれば、単純平均biasを全14日から引く。なければ補正0で元予測へfallbackする。daily Praw=max(0,Preference−u*bias)。これは自己模型の予測誤差の更新で、baselineのσ/EMA入力を再学習する方式ではない。56日/14観測日の閾値は結果後に変更しない。

2014 time120をstore/origin順に処理する。最初は空履歴で、それ以前のfitの模型誤差を擬造しない。各行で予測を作ってから完了済みの誤差を状態に追加し、次originで完了/56日条件を再判定する。元NNのtime120保存値はautonomous-mean rootのraw_nnを使い、同state/source pinを照合する。旧checkpoint自体は2014 time validationで選択済みなので、内部値を独立盲検とは呼ばない。

mean28更新とNN更新の二候補について、P=Preference+alpha(Praw−Preference)、0<=alpha<=1を2014 time120だけで校正する。前unitと同じC/Eのjoint最小とdaily/total MSE悪化なしの上限を使う。対照の変更先は各候補の自己参照（baselineまたはNN）。
候補選択はmean28/元NN/更新mean28/更新NNの内部joint最小。1e-12 tieはこの順。alpha/state/選択を保存してから2015へ進む。2015を見て方式やalphaを切り替えない。

## 2015の順次評価

内部2014の完了済みraw予測誤差をwarm stateとし、2015Jan13+14*kの原10店250要求を時系列で処理する。各originで、その時点までに完了した過去窓の自己raw誤差から補正を作る。最終更新済みの予測誤差を再帰的に使う方式にはしない。
2015の予測を生成した後にその行の実績を更新用に付与し、次originへの状態に追加する。全250予測のlabelなしfileも別保存し、採点のlabel付与前後の値を照合する。current行の実績が将来履歴へ入ることと、current行の予測へ入らないことを架空future-poison testで検査する。

全10店等重みの日次MSE/u²と完全14日総量MSE/(14u)²の半々、全店/全4quarter/MAE/WAPE/bias/過去支持とfallbackを保存。3490観測日/240完全総量/Christmas nullを保持。暫定2%改善と副条件を固定。前の診断を受けた既読データで、未知性能/PSI採用の主張はしない。

fresh artifact `artifacts/macos-demand-prequential-bias-20261015` と同execution-records。通常24files768MiB/全32files1GiB/single32MiB/失敗reserve8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files、親900秒/子870秒/Mac footprint/peakRSS各2GiB。新fit/NNforward/profile/原ZIP抽出0、保存値だけ。原root/source前後不変・全stdio/exit/失敗・closureを保存する。
本unit完了後はcontinuation/handoffに従い次の有益な工程へ進む。2016/2017/予約31–54/販促/正式holdout/Windows native/CARE/追加agent/外部送信/Git push/削除/課金APIなし。formal_permission=false、製品採用0、元変更保持。
