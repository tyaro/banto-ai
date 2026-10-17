# 小型需要モデルのtrain側診断（2026-10-14・計算前設計）

目的は、追加学習や系列拡大を始める前に、既存3店舗の学習材料と入力情報の不足を特定すること。保存snapshotと元学習のorigin/scheduleだけを使い、数量の数値読取りは2013–15に限定する。2016/17の数量、モデル・旧基準のforward、fit、checkpoint再選択を使わない。

## 固定診断

1. 元991共通train originに対し、過去28日同曜日平均と14日labelから総量・日次残差を記述する。これは新しいtrain側診断で、既存2017予測の反復ではない。991日次originはlabelが重なり、独立991試行と数えない。
2. 14日以上の観測ゼロ連続区間をtrain側から検出。欠測で区間を切り、欠測をゼロにしない。label接触/contextだけ接触/どちらも非接触の排他的群で、誤差と初期設計lossへの寄与を集計する。原因は不明で、休業・欠品・無需要のいずれとも確定しない。
3. 元モデルの初期zero-weight headが作る総量倍率0.8/1/1.2と平滑化配分を式で計算し、総量pinballと日次MAEの等重みlossを集計する。学習後モデルの損失原因や因果的ablationとはしない。固定尺度は元inputに保存されたtrain平均を使う。
4. 名目8記念日を年・店舗・日で数える。観測された日数と、共通train labelに含まれる日数を分ける。重複origin/leadを独立イベントへ増やさない。過去同曜日基準が0なら比率はnullとして支持数を別記する。
5. 保存batch日付列をstep64時点と256完了時点で数え、unique origin、イベントを含むdrawの数、distinctイベント日、長いゼロ区間を含むdrawを記述する。samplingの反復はせず元scheduleを読む。
6. 元context正規化がheadへ渡さない水準・相対変動量をsourceと数点の式で検討する。mean28総量から原単位を戻せても、正規化前の相対分散を識別できるとは限らない。新しいモデルを計算して証明を補わない。

1–5の原ledger/集約/入力pin/sourceを新閉鎖rootへ保存。新parser・連続ゼロ・初期lossの3確認だけ行う。既存確認/評価/学習/CIは反復しない。実行900秒2GiB/output1GiB/single32MiB/files32と、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16filesを維持する。

結果から次の情報追加を決めるが、この診断でモデル採択や新学習は行わない。Gitは独自codeと集約文書だけ。直接研究ACTIVE/automation PAUSED、追加agent0、正式gate不変、formal_permission=false/credit0/native reader禁止/登録holdout未読。
