# 営業日水準と休業による販売0の純粋処理（2026-10-14）

[休日入力](demand-holiday-event-input-design-2026-10-14.md)と[休暇区間](demand-holiday-duration-design-2026-10-14.md)の次unit。新処理/新代表確認の条件を実行前に固定する。実データの学習・原予測変更は行わない。

## 水準

起点前28暦日を保持し、曜日別に、起点までの営業予定でopenと確認できた観測だけから平均を求める。最小支持は各曜日3件（元の同曜日baselineと同じ初期規則、最適条件ではない）。観測0も件数/平均に入れ、欠測Noneを0にしない。日付を詰めたり未来数量から補間しない。28日外/起点以後のhistory getterへアクセスしない。

closedの原実0は営業日の水準に入れず原値を保持する。closedで正値がある場合は営業表と対象販売量の不整合として拒否し、値の切捨てで成立させない。営業状態unknownの観測は理由付きで残し、休業0と認定しない。

strictなopen-only平均と、open+unknown観測の参考平均を別fieldに返す。unknownの実0は参考平均に含まれる。後者は営業日平均とは呼ばず、自動fallbackへ採用しない。open-only支持不足はnull/理由付きで返す。原publicデータの営業状態欠如から、strict平均を計算済みと補わない。

## 日次出力

入力は営業する場合の日別point meanを想定する。確定closedなら、その販売チャネルで休業が売上0になるという明示contractがある時だけ0を返す。contractなしはnull。openは入力値、unknownも入力値を残すが「営業すると仮定した条件付き値」と明示し、強制0にしない。非負有限値かNoneだけを受け付ける。

0処理が成立するclosedの日は元の日次模型値getterへアクセスしなくてよい。全日closedかつcontractありなら、営業日水準の支持がなくても全日/期間とも0。元実績/label/欠測maskは変更しない。潜在需要が0とは解釈しない。

期間の全日が数値なら日次point meanの合計を返す。unknown営業日を含む総量は営業仮定付きシナリオで、無条件期待値ではない。1日でもnullなら全期間総量もnull、既知部分の合計を完全な総量へしない。日別quantileを合算する機能は持たない。

## 時点と確認

営業予定は既存のknown_at<=as_of同ID最新版・store scope・取消の処理を使い、未来版payloadを読まない。originはlocalな予測開始日、as_ofは同local timezone表現で、originより後の利用可能時刻を拒否する。historyは呼出し側がそのas_ofまでに利用可能と確認した日次実績のprefixを渡す契約。この処理は実績の公表履歴を新たに認証しない。

新確認は、営業実0と休業0、欠測とunknown参考平均、未来getter/未来営業版、closed/open/unknownの出力・contract、全休業・支持不足、組合せと不整合拒否。架空量は機構確認のみ。実需要精度・休日効果・期間長効果・メーカーPSIの改善は未実証。

確認後の次は、公開データで利用できる暦仮定と未確認営業状態を明示した模型接続の出力前契約。確認済み全店営業表を捏造せず、休業構造とevent効果を別々に比較する。旧fit/予測/確認/CI/予約quantity反復0、全実行/記録/prep上限とformal_permission=false/credit0/native禁止を維持する。
