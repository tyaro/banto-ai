# CARE-A-MAINT-PRACTICAL-20261017 — 保全の実用性評価と基盤モデル比較の契約

2026-10-17 JST。人が決めた方針（先行時間と誤警報は複数で報告し基準は後で決める、TimesFM 3・Chronos-2・Toto 2の3つを比べる、CARE testは開発材料として使う）に沿い、実行より前に固定する。機械可読版は[実用性評価契約](../../examples/configs/care-a-maintenance-practical-20261017.json)。

元の[CARE保全契約](care-a-maintenance-contract-2026-10-16.md)（CARE-A-MAINT-20261016-r1）の条件はすべてそのまま使う。split・時点（利用可能時刻＝記録時刻＋600秒）・score・閾値・警報の開閉・主hit・誤警報の数え方は変えない。この契約は、先行時間別の集計・誤警報の換算・基盤モデルの追加だけを定める。

## データの位置づけ

CARE testは既に読まれており（自作モデルの結果は[保存済み](../results/care-macos-learning-evaluation-2026-10-16.md)）、**未知のholdoutではない**。この比較は開発材料での評価として記録し、業務での合否や本番採用の根拠にしない。既存の自作モデルとbaselineは保存済みの予測・警報をそのまま使い、閾値・持続・checkpointを調整し直さない。

## 比べるもの

| 方法 | 内容 |
| --- | --- |
| 自作モデル | 保存済みのSmallForecaster（5fold）の予測・閾値・警報。再学習・再推論しない |
| baseline | 保存済みの負荷bin別温度中央値（共通支持とnative支持） |
| TimesFM 3 | google/timesfm-3.0-pytorch（固定revision）。非商用の研究用途として記録 |
| Chronos-2 | amazon/chronos-2（固定revision） |
| Toto 2.0 4M | Datadog/Toto-2.0-4m（固定revision） |

基盤モデルは学習・fine-tuningをしない（zero-shot）。既存adapter（`src/banto_ai/adapters/`）と固定package versionを使う。

- 入力：自作モデルと同じ各origin nの過去128row `[n−128,n)` の3信号（元単位）。TimesFM・Chronosは2温度を予測対象、powerを過去だけの共変量とする。Totoは3信号すべてを変量とする（adapterの既定どおり）。
- 出力：horizon 1、分位点はp50だけを要求する。警報に使うのはlead1のp50だけで、元契約と同じ。
- 支持：自作モデルと同じ共通支持の行だけで予測する（過去128rowと現在の2温度がfinite・連続）。adapterが失敗した行は、その方法の非支持として記録し、別の値で埋めない。
- 校正：foldごとに、元契約と同じ校正区間（validation anchorのprefix後半30%）で同じscoreを計算する。閾値は方法別に99.5%点、警報の開閉も元契約と同じ。

## 指標と集計

元契約の主指標（asset macroの検知率、正常1000 record-hour当たりの誤警報、正常の警報時間割合、miss込みearliness）と実数・pooled・event別・asset別・支持をすべて報告する。加えて次を報告する。

- **先行時間別の検知**：W＝0・24・72・168時間。主hitのOPENが「推定異常期間の終わりの利用可能時刻−W」以前であるeventだけを、Wでの検知と数える。W＝0は元契約の主hitと同じ。推定異常期間の終わりは実際の故障時刻と保証されないため、ここでの先行時間は代理値である。
- **誤警報の換算**：正常1000 record-hour当たりに加え、asset・30日（720 record-hour）当たりの件数でも示す。
- **event別の対比**：方法ごとの検知の有無・OPEN時刻・先行時間をevent単位で並べる。anomalyは12件しかないため、差の有意性は主張しない。

必要な先行時間と許容する誤警報の基準は、この比較の結果を見てから人が決める。今回は合否を出さない。

## 手順と停止条件

1. 環境：基盤モデル用の別Python環境を作り、package versionと、downloadしたcheckpointのrevision・hashを記録する。
2. 推論：5foldの校正区間とtest区間を全方法で推論する。予測・score・閾値・警報を保存し、hashを付けて固定する。
3. 採点：全方法を固定した後に、評価者だけがlabelを読んで採点する。元契約と同じ順序。
4. 保存物：CARE由来の入力・予測・labelは公開リポジトリに入れない（gitignoreの`artifacts/`）。リポジトリにはhashと集計だけを残す。

- 資源：1単位あたり親900秒・子870秒で、区間ごとに分けて再開できるようにする。メモリはTimesFMだけ4GiB、他は2GiB（人が承認）。batch推論は使ってよく、batch sizeを記録する。
- 推論の失敗・非有限値・時間超過は記録して止める。結果を見た後に入力・context長・閾値・支持条件を変えない。
- より長いcontext、共変量の別の扱い、fine-tuningは、この契約の範囲外とする。

## 必要な保存物

Macから、評価者のlabel（`care-evaluator-contract-20261016`）、fold1〜4の学習結果（`care-learning-fold-{1..4}-20261016`）、保存済みの採点結果（`care-learning-scores-20261016`）、split manifest（`care-metadata-inventory-20261016`）、学習の実行許可（`care-learning-campaign-launch2-20261016`）が必要。fold0と数値入力は受け取り済み。
