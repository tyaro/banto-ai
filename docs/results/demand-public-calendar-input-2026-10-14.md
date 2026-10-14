# 公開名目暦の共通入力とfit支持（2026-10-14）

[接続条件](../research/demand-calendar-model-connection-design-2026-10-14.md)で単store自己56日/14日・暦60・量mask/u/2統計/mean28のpure adapterを実装。新6確認一回allpassed。営業表がない公開sales平均の経路で、名目休日closed化/Christmas label0化なし。

当日controlと前後候補は同shape/数量/統計/baseline。4位相＋8kind×±3=56channel。fit支持0は明示maskで0に固定。future量getter非アクセス・年越し/閏年・当日対前後・実0/missing/支持不足・単位/意味・distinct support/cutoffを確認した。旧確認は反復していない。

既存ready/ledgerの数値tokenを文字列として保持して630key（15店各42）だけ抽出し、元snapshotから2013–14のstore/date/observed列だけ新解釈。sales fieldは読まず、2015のmask/quantityも解釈0。fit uは保存値の文字列として次unitへbinding。支持はdistinct store/target_date・event-yearで重複originを割引。

有効channel 42/56、支持0 14。支持0内訳：[{"kind": "01-01", "relative_day": -3}, {"kind": "01-01", "relative_day": -2}, {"kind": "01-01", "relative_day": -1}, {"kind": "01-01", "relative_day": 0}, {"kind": "01-01", "relative_day": 1}, {"kind": "01-01", "relative_day": 2}, {"kind": "01-01", "relative_day": 3}, {"kind": "12-25", "relative_day": -3}, {"kind": "12-25", "relative_day": -2}, {"kind": "12-25", "relative_day": -1}, {"kind": "12-25", "relative_day": 0}, {"kind": "12-25", "relative_day": 1}, {"kind": "12-25", "relative_day": 2}, {"kind": "12-25", "relative_day": 3}]。event-year支持：{"01-01": [], "05-01": [2013, 2014], "05-24": [2013, 2014], "08-10": [2013, 2014], "10-09": [2013, 2014], "11-02": [2013, 2014], "11-03": [2013, 2014], "12-25": []}。元日やChristmasの欠測/少数支持を精度の成立へ補わない。

新fit/forecast/quantity float解釈/CI0、旧source/完了結果不変。parent経過0.449515秒、child全stdio/exit0を判定前保存。本文representative-demand-public-calendar-input-recordsを優先。原input rootは6確認/支持後の文書dict記述TypeErrorでfailed保持、新doc rootで文書だけ限定訂正。確認/集計再実行0。次は固定V1/D32/L1の新模型/少数接続確認、通過後のみ同initial/sampler/256step二件の回顧比較へ進む。

direct ACTIVE/automation PAUSED、追加agent0/CARE待ち、全上限/formal_permission=false/credit0/native禁止/登録holdout未読維持。Git独自code/架空確認/集約docsのみ、原quantity/ledger/尺度/重み送信0。
