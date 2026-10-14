# σ・EMA・等重み予測の併用：新確認と回顧比較（2026-10-14）

## 結論

[固定設計](../research/demand-statistical-overlay-design-2026-10-14.md)で、曜日を除いた過去誤差のEMA/σを作り、保存mean28とEMA補正予測を等重みで併用した。新6確認は一回passed。**固定した等重み候補は基準よりjoint MSE約5.041%悪化、改善3/15店で条件未達。採用せずこの仮説を区切る。** 半減期・窓幅・重みgrid、新NN追加、旧モデルの再学習/forwardは行わない。

時系列統計を併用できることと予測精度が上がることは別。σの計算部品は成立したが、σによって今回のpointを調整していない。将来の確率区間や発注安全量として校正されたものでもない。

## 三つの役割を分けた

|量|意味|今回の使い方|
|---|---|---|
|過去誤差の平均/EMA7|最近の上振れ・下振れ|基準日次BにEMA7を加え非負にした成分|
|EMA7−EMA28|短期と長期のずれ|記述metadata、point切替なし|
|sample σ|過去一歩先誤差の中心化した散らばり|不確実性の診断、未来σや95%区間にしない|

指数平滑と予測平均は需要を含む一般的な時系列の方法で、株価の売買ルールを数量へ移したものではない。[FPP3 指数平滑](https://otexts.com/fpp3/exponential-smoothing.html)、[予測の組合せ](https://otexts.com/fpp3/practical.html#forecast-combinations)。正規分布等を仮定した予測区間にはh歩先の誤差stdが必要で、過去のstdそのものではない。[FPP3 予測区間](https://otexts.com/fpp3/toolbox.html)。

一歩先誤差e_tは各tより前28日の同曜日平均b_tと実観測y_tの差。最新28日分だけ作り、そのための入力は起点前56日のみ。実0を残し、欠測/同曜日支持不足を残差0にしない。n20以上を固定し、sample σは平均μで中心化してn−1分母、RMSEは平方平均。μとσを混ぜず、一定Bias10ならσ0でもRMSE10を代表確認で確認した。

EMAの半減期7日/28日は事前の一案で、最適値ではない。日付gapをretentionへ反映し、欠測日に0を挿入しない。最古有効eで初期化し、最後の誤差日と古さも保持する。外れ値除去0。future getterへのアクセスは新fixtureで拒否した。

`Pema=max(0,B+EMA7)`、`Pblend=.5*B+.5*Pema`。日次pointが全て数値なら総量は和。sample σをmeanへ足して方向を決める処理なし。σ0も将来が確実とは認定しない。日次σをsqrt(14)倍/足し合わせて総量σにせず、日間誤差の共分散を未確認のまま区間へ変換しない。

## 新6確認

|新確認|結果|
|---|---|
|純曜日patternの誤差0・σ0でも確率保証なし|passed|
|一定Biasとσ/RMSEの違い・未来誤差拒否|passed|
|水準変化に対する短期/長期EMAの差|passed|
|future数量getter・実0/missing/支持不足fallback|passed|
|数量単位の変換とEMA/σの対応|passed|
|非負point/日次総量整合・null/NaN拒否|passed|

fixtureは機構の確認で、金融/需要の予測精度を実証していない。旧暦入力6確認、模型3確認、旧NN/区間/CIは反復0。

## 新しいpointだけを比較

直前の閉鎖calendar-pairが保存した2015selection CSV、450prediction ledger、summaryを原closure pinへ照合して再利用した。原archive/旧fit/NNforwardは0。baselineは保存point、baseline指標は保存summaryから再利用し、旧採点を再計算しない。新しく計算したのは過去e/EMA/σと900本の成分/等重みpoint vector、及びその指標。

18店25起点を維持。positive15の元fit uで尺度化し、zero-fit-scale3店はraw-unit統計として計算して別欄に保持。他店の尺度/floorを借りない。今回の450窓は全て残差n20以上、fallback0/point不能0。日次は観測だけ、総量は14日label完備時のみ採点。

主指標は15店macro joint MSE=.5*日次尺度化MSE+.5*14日総量尺度化MSE。

|方式|主joint MSE|日次macro MSE|総量macro MSE|
|---|---:|---:|---:|
|mean28・原保存|0.071036585129|0.118398085511|0.023675084746|
|EMA7補正成分|0.085032004286|0.132088904734|0.037975103837|
|等重み併用|0.074617738151|0.121877777751|0.027357698551|

新等重みが基準より小さい店は3/15（18, 26, 30）。主指標の改善と10/15条件の両方に未達。EMA成分も全体では悪化。店別/日次/総量/raw RMSE/MAE/WAPE/Biasと尺度0群を原summaryへ保持。σの支持とrangeはdiagnosticで、外れ確率や新prediction intervalを採点したものではない。

2015は既知の回顧開発、学習群と不確実性の構造を前の模型と変えた比較であり未見/一般性能ではない。どんな統計併用も無効とは結論しないが、この定義のrecent error levelを固定持続させる一案は置換の根拠を得ていない。

## 次と保存

直接研究はPAUSED/今回の自走を区切る。次の判断はσを使った未来h別/総量誤差の校正、又は長期/短期変化を予測へ入れる別の根拠から。現在のσを±2σの95%帯へ名前だけ替えたり、既知2015に合わせて重みを動かしたりしない。旧休日NN条件未達や元日/Christmas支持不足も変えない。

計算0.818092秒/OS peak private26480640B、新helper失敗0、child全stdio/exit0を判定前保存。新rootにsource/固定設計/input pins/新残差/point/指標を閉鎖保存。本文representative-demand-statistical-overlay-records、post-doc-records/Git後overlay-git-records post-save優先。Webは著者資料URL/参照metadataで、全raw revision保存ではない。

automation PAUSED/CARE手動待ち・自動確認0/追加agent0、全実行/記録/prep上限維持、formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。Git独自code/架空確認/集約docsのみ、原quantity/ledger/尺度/予測送信0。
