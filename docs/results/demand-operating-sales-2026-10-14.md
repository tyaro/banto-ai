# 営業日水準と休業販売0の処理・新6確認（2026-10-14）

[出力前の条件](../research/demand-operating-sales-design-2026-10-14.md)に従い、pure処理と新6代表確認を一回実施、全passed。架空数量のみで、原public quantity読取り/fit/実予測/旧確認/CIは0。需要精度・休日や期間長の効果の実証ではない。

## 営業日水準

tools/demand_operating_sales.pyのestimate_open_levelsは起点前28暦日だけを読取り、起点まで既知の営業予定で曜日別open-only平均を作る。各曜日3観測以上を初期支持規則とする。休業日を取り除いて日付を詰めず、曜日・leadを暦上に残す。実0は有効な営業観測、欠測Noneは分母に入れない。

確定closedの原実0は通常営業平均へ入れず原値/理由を保持。営業unknownの観測0は休業と認定せず、open+unknownの参考平均に含める。strictな営業日平均と参考平均は別fieldで、自動fallbackなし。支持不足のstrict平均はnull。confirmed closedで正値があると営業表と対象売上の不整合として拒否する。

架空の同曜日4件がclosed0/open0/open100/open100なら、営業支持3件・平均200/3。欠測1/unknown0/open100/open100なら、営業支持2でstrict=null、参考支持3・平均200/3。unknown0を無断closedへ扱うことも、欠測を観測0にすることもない。

historyは呼出し側がas_ofまでに利用可能と確認したprefixを渡す契約で、実績公表履歴を認証する機能はない。as_ofはoriginと同local timezoneで表し、起点より後を拒否する。future quantity getterと後日の営業版payloadへアクセスしない。

## 日次売上と総量

apply_operating_salesは営業するときの日別point meanと独立した営業予定を受け取る。対象販売チャネルで休業が売上0になる明示contractがある時、confirmed closedを厳密0にする。contractなしのclosedはnull。openは元mean、unknownは元meanを残し営業仮定を併記。closedの日の模型meanは読まず、全日closedなら営業平均の支持がなくても全日/総量0。

全日が数値なら日次point meanの和を返す。unknown営業を含む総量は営業仮定付きで、無条件期待値と呼ばない。1日でもnullなら全期間総量もnull。既知部分合計を完全総量にせず、日次quantile合計機能を持たない。原実績/label/欠測maskは変更しない。販売0と潜在需要0は異なる。

架空open10/closed/unknown30なら日次10/0/30・総量40、unknown日に営業を仮定した結果。閉店の明示contractがなければclosed日と総量はnull。14日全closedなら日次と総量0、模型getter不要。この構造だけでは休暇前後の買いだめ/反動を表さない。

## 新6確認

|新代表確認|結果|
|---|---|
|営業実0と休業実0の別役割・原history不変|passed|
|欠測とunknown0・strict支持不足と参考平均の分離|passed|
|future数量getter/後日営業版payload非アクセス・遅いcutoff拒否|passed|
|open/closed/unknown出力・明示contract・条件付き総量|passed|
|14日全休業・営業平均支持不要・模型getter不要|passed|
|支持不足の組合せ・不整合closed正値/NaN拒否|passed|

元calendar/区間/weekly source・区間確認/結果bytesは不変。元の一点/区間の各6確認は反復しない。新処理の成立は原Store Salesに営業表があるという認定でも実精度改善でもない。原の元日実0/Christmas欠測と営業予定/公表履歴欠如は維持。

## 次のunit

休日期間入力・営業水準・構造0の機構を分けて準備できた。次は公開データで予測時点に利用できる情報を明示して、営業calendarの仮定とevent模型接続の条件を出力前に固める。仮定のcalendarを実当時予定に読み替えず、既知2015に係数/長短閾値を合わせる追加探索を開始しない。

公開営業表なしでstrict水準が支持不足なら、その状態を報告し、参考値へ黙って切替えない。休日構造とevent効果の比較を分け、期間長固有の実証には同種eventの長さ変動/独立年の支持が必要。新模型/学習/実データ評価は今回未開始。

新6確認parent経過0.296987秒、child全stdout/stderr/return0を判定前保存。whole model資源測定ではない。新script/source/固定設計/pins/新scopeをfresh閉鎖rootに保存、原closed/failed root不変。本文representative-demand-operating-sales-20261014-records、Git後同-operating-sales-git-records post-save優先。

direct ACTIVE/automation PAUSED、追加agent0/CARE手動待ち・自動確認0。全実行/記録/prep上限維持、formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。Git独自code/架空確認/集約docsのみ、原quantity/予定実績/ledger/係数/予測送信0。
