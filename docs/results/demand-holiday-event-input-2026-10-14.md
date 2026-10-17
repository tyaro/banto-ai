# 休業状態と休日の前後を分ける入力経路（2026-10-14）

人の「売上0の休日は事前処理が必要では」「休日をevent入力として前後の特性を扱う」に従い、[新設計](../research/demand-holiday-event-input-design-2026-10-14.md)を固定し、入力prototypeと新6確認を一回実施。allpassed。新学習・予測・精度評価は0。前の8週補正の未達は維持。

## 現行方式の不足と修正方向

これまで欠測と観測0は区別したが、営業日における実0と休業による0は分離せずに通常水準や補正へ入れていた。名目event当日one-hotは追加したが、休日前後と営業状態の明示的な分離は未実装だった。元mean modelのsoftplus/平滑化配分は厳密な日次0を表せない制約がある。単に暦flagを渡すことは、その構造の修正ではない。

確定休業で売上0になる対象については、営業日の数量モデルに休業状態を適用する設計が適している。休業0を通常営業の低需要として学習せず、過去営業日から通常水準を推定する。一方、営業中の実0は有効な観測、欠測はnull、状態不明の0は不明のまま保持。祝日を一律にclosedへ変えない。

今回prototypeはイベントと営業予定の入力経路だけで、通常水準の再推定・closed日の出力mask・loss変更はまだ実装していない。これらを行った新候補の改善を既存結果へ補わない。

## 新入力

tools/demand_event_calendar.pyは営業日やイベントの予定版と、localな対象日付だけを使う。sales/label/forecastを引数に持たず、Torch/学習/外部IOを持たない。event種別ごとに相対日−3/−2/−1/0/+1/+2/+3の別channel。当日だけと同じ係数へ潰さず、イベント種別や重複も残す。±3は機構の最初の範囲で、最適窓とはしない。

|fixtureの対象日|元日までの位置|新しい入力|
|---|---|---|
|2014Dec29|3日前|new_year/−3|
|2014Dec31|前日|new_year/−1|
|2015Jan1|当日|new_year/0|
|2015Jan2|翌日|new_year/+1|
|2015Jan4|3日後|new_year/+3|
|2015Jan5|4日後|今回の前後channel外|

この表は架空予定での経路確認。買いだめ、反動、連休明けの実需要効果を測定したものではない。event featureの有無とoperating_status=open/closed/unknownは別field。祝日だけなら営業状態はunknown。

## 起点と予定版

known_atはtimezone-awareで、起点時刻までに利用できた最新版だけを選ぶ。後の取消や発表はpayloadを読まずに除外、既知になった取消は反映。時点不明は除外理由を保持し、完全な予定表と認定しない。予定情報なしのfeature0は「選べる既知eventがない」であり、通常日を確認済みにはしない。store scopeと営業予定の取消を区別する。

予定の版や公表時刻は実データでは未確認。既保存Store Salesでは元日は観測0、Christmasは欠測、個別営業予定や改訂時刻は原カレンダーにない。原Christmasを観測0へ置き換えず、全店休業を確認したことにしない。休日効果を表すindicatorや前後日の扱いは[教科書の回帰](https://otexts.com/fpp3/regression.html)と[欠測/休日の説明](https://otexts.com/fpp3/practical.html)にも示されるが、本データの効果検証の根拠ではない。

## 新6確認

|新確認|結果|
|---|---|
|前/当/後の別channelと年越し|passed|
|event種別の区別と重複|passed|
|未来の取消payload非アクセスと既知最新版取消|passed|
|known_at不明と予定表の完全性を区別|passed|
|祝日flagと営業状態/店舗scopeを分離|passed|
|営業予定取消・同時刻版の曖昧さ・naive時刻拒否|passed|

旧入力/回帰/NN/CI確認は反復しない。新6確認は機構の成立で、予定履歴の実在、当時の営業情報、精度改善、実用性の認定ではない。

## 次の優先unit

入力支持通知の予定を後段に移し、まず営業日からの基準水準と、確定休業日のsales0を作る小さい純粋処理を設計する。実0/欠測/unknown、営業日支持不足、全予測日休業、当時未知だった予定の変更、日次と総量整合を少数確認する。原実績は改変せず、calendarから推定した0を実測labelの成績へ補わない。

その後にevent前後入力を模型へ接続する条件を固定する。event当日、前日、翌日等の効果は営業日の予測モデル側で学習し、営業状態の構造処理と組み合わせる。希少eventは異なる年の支持を数え、店舗/重なるoriginによる反復を独立年へしない。予定履歴不明を研究全体の停止条件にせず、明示した仮定の機構研究と実データ実証を分ける。

現在は新6確認だけ/NN再学習0/原予測変更0。人の最新方針で直接研究ACTIVE、automation PAUSED不変。旧8週補正不採用、mean28総量＋限定暦配分の原研究基準は比較用に維持。営業状態処理を加えた新基準は未評価。

## 原証拠と境界

新確認・原証拠保存のparent経過0.182345秒、実CPython3.14.0/Windows。child全stdout/stderr/return0を判定前保存。モデルwhole peak測定ではない。新source全文/設計/pins/新scopeをfresh閉鎖rootへ保存し、現weekly入力・旧mean source・原calendar文書のbytesは不変。今回新helper失敗0、原failed/closedroot不変。

本文representative-demand-holiday-input-20261014-records、Git後同-holiday-input-git-records post-save優先。追加agent0/CARE手動待ち・自動確認0、全実行/記録/prep上限維持、formal_permission=false/credit0/native reader禁止/登録holdout未読/正式受入未完了。Gitは独自code/集約docsのみ、原quantity/予定実績/ledger/係数/予測を送信しない。
