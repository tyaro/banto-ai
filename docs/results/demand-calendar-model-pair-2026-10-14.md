# 休日当日と前後入力の小型モデル比較（2026-10-14）

## 判断

[固定条件](../research/demand-calendar-model-connection-design-2026-10-14.md)で同shape/初期重み/samplerの二件を各256step一回学習し、既知2015の回顧比較を完了。**前後入力候補は小幅改善だが、事前の進捗条件未達。採用せず、この仮説の自走を止める。** 同seed再試行、step延長、期間長/幅grid、2016/2017/予約群への追試は行わない。

入力の新6確認、模型接続の新3確認はいずれも一回passed。実行成功と性能条件達成は分ける。直接研究PAUSED/automation PAUSED、再開には次の問いの判断が必要。

## 公開データで使った意味

名目8月日を季節指標とし、実営業表はunknownのまま。public sales meanの模型で、confirmed営業日の条件付きmeanや店舗閉鎖0を推定したものではない。名目休日へ一律0maskを掛けず、Christmas欠測を0labelにしない。

元の固定630fitkeyは8週入力/labelの完全性で選ばれている。その窓には元日とChristmasの±3日label支持がなく、対応14channelは両側とも無効、残り42channelは2013/2014の支持がある。**今回の結果は元日/Christmasの入力効果や連休長の検証ではない。** 支持不足を結果後の窓入替えで補っていない。

## 二件の条件

正尺度15店各42窓、2013–14 fit、原fit uを再利用。店21/22/29はzero-fit-scale/baseline-only、2015要求にも残す。単storeの自己56日/patch7/14日、D32/L1/4headの共通encoder、量/u・観測mask・2統計・曜日/年位相4＋event56の60暦。

30,081parameters。日次headはmax(0,baseline+u*g)、総量は日次和、quantileなし。初期head0でbaselineへ一致。公開meanと営業条件付きcomposerを混ぜない。モデル/損失/256×8 sampler/initial stateを同一にし、当日controlだけ相対日!=0を0へする。

AdamW/CPUfloat32/2threads/interop1/deterministic、seed20261014、256step固定。両方の最終重み保存後に2015実績を数値解釈、checkpoint/seed選択なし。源snapshot/fit selection/scales/key列/sampler/initial/final/journal/2015selection/predictionsをlocal保存。旧weights/学習/確認/CI反復0。

## 主指標と全体指標

positive15のevent±3日macro尺度化日次MSE。重複originの同store/target_date内で誤差を平均してから日平均/店平均。共通event年を店舗数やoverlap数倍の独立年にしない。

|方式|休日周辺macro MSE|全日macro日次MSE|14日macro総量MSE|
|---|---:|---:|---:|
|同条件mean28|0.143306676769|0.118398085511|0.023675084746|
|休日当日のみ|0.143221827110|0.118211248847|0.023481126878|
|前後3日あり|0.143194515722|0.118187449482|0.023461105939|

前後候補の主指標はmean28比0.078266%、当日control比0.019069%改善。全日の日次/総量macroも両対照以下。ただし両対照より休日周辺が小さい店は9/15（6, 7, 9, 13, 14, 17, 19, 23, 27）、固定10/15条件に未達。小幅差を有意差/一般優位/実用性へしない。

原単位positive15の総量RMSEはmean28 596.036302、当日 594.187244、前後 594.117790。主指標の尺度化MSEと同一数値ではない。全18/positive15/zero-scale3、店別/kind-offset別の原指標とBias/WAPEもsummaryに保持。旧mean28＋限定暦配分のfit条件の違う原係数を混ぜて方式横断の勝者にしていない。

450要求、NN支持375、zero-scale baseline-only75、baseline不能0。全14日labelを持つ432窓（positive15 360/zero3 72）、総量label不能18は欠測のまま。日次は観測6282点（positive15 5235/zero3 1047）だけ採点し、欠測を成功例へ補わない。

## 限界と次の判断

これは2015を既知にした後の回顧開発で、未知系列や新年度の独立検証ではない。実休業表がないため、休業0の構造処理を公開データで性能確認していない。顧客休暇の長さ、将来販促、メーカー出荷/潜在需要/PSIも未確認。

今回の前後情報の追加差は小さい。さらに模型を回して条件を通す作業はしない。次に再開する場合は、(a)現在の目的に合わせ実営業予定/販売チャネルと期間入力の支持を確保する、または(b)元日/Christmasを対象とする別の支持契約を、結果を見る前に固定する判断が必要。今回の固定630key条件は遡及変更せず保全する。期間長の実証には同種eventの長さ変動も必要で、単日名目calendarから捏造しない。

## 保存と原失敗

計算経過11.350920秒、OS peak private1150619648B、900秒/2GiB範囲のcheckpoint。全native/runtime閉包やblocking中断保証ではない。元の文書生成は新6入力確認/支持保存後にdict記述TypeErrorでfailed。原script/traceback/結果を閉鎖保存し、新doc-only continuationで文字列一箇所を訂正。原確認/支持集計の再実行0。模型3確認と二件比較には新helper失敗0。

本体representative-demand-calendar-pair-20261014は22files/原closure全pin照合、追加0。全childstdout/stderr/returnはpair-launch-records、後保存はpair-doc-records、Git後pair-git-records post-save優先。sourceと入力/結果の対応、原failed/root不変を保持。

direct PAUSED/automation PAUSED、追加agent0/CARE手動待ち・自動確認0。全実行/記録/prep上限維持、formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。Git独自code/架空確認/集約docsのみ、原quantity/ledger/尺度/係数/予測/重み送信0。
