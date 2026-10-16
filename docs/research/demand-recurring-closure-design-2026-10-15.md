# 過去の繰返しゼロ・欠測による休業相当仮説の2015評価

2026-10-15 JST。人の「0は休業でよいのでは」「欠測も休業扱い」と、その説明に対する「進めてください」を今回の委任とする。過去から休業相当日を推定し、観測だけの評価と推定欠測0の感度評価を分ける。営業予定の確認済み休業へ昇格させず、原実0/欠測/nullを保持する。前契約の欠測0化禁止について、今回の仮定付きside評価だけが人の新委任による変更である。

## 実行前に固定する仮説

許可済みFIT10店・既読2013/2014の全calendarを使用。予測パターンの学習終了は2015-01-01 exclusiveで、2015quantity/maskは学習に渡さない。全365月日を調べ、同月日の2013年と2014年で全10店とも観測0又は欠測であれば、その月日を2015の「休業相当日」と推定する。20店年の行があるが独立な年は2で、10店を独立な20例と呼ばない。一つでも過去正値があればその月日は選ばない。両年の完整calendarと全店支持を要求し、2月29日/支持不足を補わない。閾値/年/店舗/対象月日を2015で調整しない。祝日リストは推定器へ渡さない。

これは反復パターンに基づくhard-mask仮説で、P(休業)=1を統計的に推定したものではない。欠測が休業に由来するという仮定は未証明で、反復データ欠落でも同じパターンが生じ得る。量の履歴/観測maskはそのまま保存し、実在のas-of予定はないのでoperating_status=unknown、別field assumed_closure=trueを用いる。元日/Christmasという名称だけで自動0にしない。

## 予測・対照・二種類のlabel

原尺度/暦/NN・ridge state/alphaは変更せず、新NN/ridgefit/forward/alpha・方式選択0。原sales-state250窓と元日追加10窓の保存済みlabelなし予測を読み、2015入力labelを解釈する前に凍結したパターンで該当日の数量を0へ合成する。主candidate=原主rolling+推定休業mask。raw baseline=原mean28、prior=原主、matched baseline=同じ推定休業maskを適用したmean28も報告し、仮定の改善を回帰模型の改善に混ぜない。どの方式も全期間の予測/支持を保存。

観測評価では原actual/null/complete_labelを保持し、欠測を採点しない。仮定付き評価では、凍結パターン該当日かつ原欠測だけを新scenario_actual=0へ置き、imputed flagを残す。該当しない欠測はnullのまま、原actualは別fieldに残す。推定休業日で実績が正値なら原正値を保持して誤予測を採点し、仮定との矛盾を記録する。仮定付きの追加支持を実測と呼ばない。全14日が揃わない総量を部分和で代替しない。

二cohortを分離：original250（Jan13から原25origin×10店）とnewyear10（Jan1発行Jan1〜14）。原閉鎖summaryは保護し、今回のmask評価を新rootへ保存。20店日の重複を明示し、260窓や全2015の一つの成績に合算しない。newyear観測0の効果と、original250のChristmas欠測0仮定の効果を分ける。

日次MSE/u²・完全14日総量MSE/(14u)²・半々jointを固定10店等重み、MAE/WAPE/bias、店舗別を報告。raw mean28比、同仮定matched mean28比、原主比を併記。ゼロ日だけのWAPEは分母0でnull。日次の改善で総量が悪化する可能性も保存。改善があっても2年間由来の仮説/既読探索的開発に限り、PSI採用・因果・未知性能・統計的有意性を認定しない。

## 確認と保存

新fixture：2015/他店payloadのmetadata先行拒否、2年/全店支持不足、過去正値でmask拒否、過去欠測と観測0の区分、未来label毒化で同pattern/同予測、仮定正値矛盾の保存、原null保持と別imputation、nonpattern欠測の維持/不完全総量、matched baseline同mask、cohort支持とゼロWAPE。

fresh macos-demand-recurring-closure-20261015及びexecution/readback/doc-records。契約/source/config/過去7300calendar ledger/frozen patternと支持/各cohort labelなし予測・推定ledger/原label・scenario label/summary/全stdio/exit/失敗prefix/closure、原source/root前後不変を保存。親900秒/子870秒/Mac sampled footprintとpeakRSS各2GiB、通常24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。

原変更・失敗・closed roots保持、2016–17/予約31–54/販促数量/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/追加agentなし。共通CPU/Mac検査とWindows固有/OS依存包括test未実行を分離。formal_permission=false/製品採用0。heartbeat PAUSEDを保持して今回の直接委任を最後まで完了する。
