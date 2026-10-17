# 休暇期間と店舗休業を分ける入力処理（2026-10-14）

[Astraと検討した期間設計](../research/demand-holiday-duration-design-2026-10-14.md)に従い、数量を読まない新adapterと新6代表確認を一回実施。全passed。既存一点eventの6確認・旧評価・fit・forecast・CIは反復していない。実需要への効果は未検証。

## 入力と出力

tools/demand_event_intervals.pyのbuild_interval_inputsはevent/日別営業予定/対象日/as_of/store/kindsだけを受け取る。sales/label/forecast/学習/外部IOなし。既存sourceの版選択/時刻/scope/取消helperを使い、起点までに既知の同ID最新版を選択してから日付・期間payloadを読む。既存source/test/設計/結果bytesは不変。

有限区間はstart/endの両端を含み、end_status=scheduled。単日は同じstart/end。全lengthはend-start+1で、予測窓が1日でも元の5日間eventを1日に縮めない。開始/終了距離と前/中/後を保存する。

終了未定はend/length/終了距離=null、end_status=ongoingまたはschedule_unavailable、確認範囲confirmed_throughを要求する。確認範囲内はduring、その後はundetermined。継続予定という理由だけで無期限activeにせず、予定未取得との理由の違いを保持する。未定eventを完全calendarと認定しない。

種別ごとに開始3日前/2日前/前日、期間中、終了翌日/2日後/3日後、未確定の8channel。±3は初期の機構範囲。channelはbinaryで、同種event重複でも合算しない。個々のID/kind/length/known-mask/距離をevent_positionsに残す。期間長のtensor集約・係数・長短区分はまだ決めていない。

## 営業予定は別

日別open/closed/unknownはeventから生成しない。対象窓の外も含む既知営業予定で連続closedを区切り、両隣のopenが確認された場合だけ休業全長を返す。それ以外はlength=null、確認できたlength_lower_boundと両境界の既知flagを保持する。予定表の空白/unknownや予測窓の端を休業終了にしない。

|架空例|event全長|営業予定から得る休業|
|---|---|---|
|5日間の行事で休・休・営業・休・休、前後営業|5日|2日ずつの二つの休業|
|5日間の行事で全日営業|5日|休業なし|
|確認できたclosed2日の前後がunknown/未取得|eventと独立|下限2日、全長未定|

同じ休業日をevent数だけ重複計上しない。祝日/販促/顧客行事と店/物流の営業機会を区別する。現在は日付全体のopen/closedで、営業時間や部分営業はこの契約の対象外。

## 新6確認

|新代表確認|結果|
|---|---|
|単日/連日・年越し・開始終了境界・窓による全長切詰めなし|passed|
|途中営業で休業を分割・窓外の営業予定で境界確認|passed|
|期間中全営業と、境界unknownの休業下限|passed|
|終了未定の2理由・確認範囲後unknown・完全性拒否|passed|
|後日の延長/営業予定payload非アクセス・既知版延長/取消|passed|
|重複/kind/scope・休業重複計上なし・逆転等の不正期間拒否|passed|

future版はheaderだけ読めるfixtureで、起点時点3日→後日5日の予定を区別。全例は架空予定の機構確認であり、当時の店舗予定や休暇効果を実証していない。原publicの営業表/公表履歴欠如、元日実0/Christmas欠測を維持。

## 次のunitと保存

次は営業日からの過去同曜日水準・確定closed sales0・unknown/missing/営業実0・支持不足・全休業・日次と総量整合のpure処理。原実績をcalendarで補った0へ書換えず、unknownを自動closedへ変えない。event効果と期間長の模型接続/学習は別出力前契約で、実需要の増減/精度改善/販促効果は未検証。

新6確認のparent経過0.197717秒、child全stdout/stderr/return0を判定前保存。whole model資源測定ではない。新script/source/固定設計/pins/新scopeをfresh閉鎖rootへ保存、元closed/failed root不変。本文representative-demand-event-intervals-20261014-records、Git後同-intervals-git-records post-save優先。

direct ACTIVE/automation PAUSED、追加agent0/CARE手動待ち・自動確認0。全実行/記録/prep上限維持、formal_permission=false/credit0/native reader禁止/登録holdout未読/正式受入未完了。Git独自code/架空確認/集約docsのみ、原quantity/予定実績/ledger/係数/予測送信0。
