# σ・EMAを学習入力として使う設計への修正（2026-10-14）

人の「そのまま使うより前処理/一緒に入力する情報として使えないか」を受け、研究を入力表現の問いへ修正する。前の固定EMA補正/等重み併用の悪化は、統計を学習入力として利用する仮説を検証した結果ではない。原結果とfailed/閉鎖rootは保全する。

## 前処理と追加入力を分ける

|使い方|例|役割と注意|
|---|---|---|
|前処理|fit尺度uで数量単位をそろえる、曜日を除いた過去残差を計算する|未来量で中心/尺度を求めず、実0と欠測を分ける|
|追加入力|過去残差の平均・EMA7/28・sample σ・支持/古さ|予測への寄与を学習する。固定で加算しない|
|別の前処理案|局所平均/σによるz-scoreと逆変換|水準を消したままにしない。今回は同時導入しない|

平均と分散で局所的に正規化し元尺度へ戻す考え方は時系列NNの研究にもある。[RevIN著者論文・ICLR 2022](https://openreview.net/forum?id=cGDAkQo1C0p)。これは現在のデータでの成功や採択を意味しない。今回は既存q/u・context mean/uと変動係数を維持し、追加統計の価値とnormalize変更を同時に比較しない。

移動平均やσは元56日の系列から作れる要約。新しい外部観測が増えるのではなく、限られた模型/学習予算で使いやすい表現になるかが問い。既存入力にもraw contextの標準偏差/平均があるが、新σは曜日基準の一歩先誤差のstdで対象が違う。

## 最初の追加入力を固定

過去一歩先誤差の定義、残差20以上、EMAの半減期7/28、sample σは[旧統計部品](demand-statistical-overlay-design-2026-10-14.md)のまま。origin前56日だけを使い、各過去tのweekday基準はt前28日だけ。未来label/将来販促/実休業を使わない。

8次元branch：`mean_error/u, EMA7/u, EMA28/u, sample_sigma/u, support/28, staleness/28, statistics_available, staleness_known`。短長差はEMA7−EMA28から復元できるので独立の追加次元にはしない。既知origin/past_end/last_error_dateを先に検証し、未来profileの数値payloadへ触れない。

統計支持不足は先頭4値を0とavailability=falseでencodeし、実際に統計0を観測した場合と区別する。古さ不明も0とknown=false、σ0をcertaintyへ読み替えない。u<=0では他店尺度/floorを借りずbranch不能、正尺度NNの対象外。すべてに原単位/理由をmetadataとして保持する。

## 学習する接続

新namespaceで、既存D32/L1の構造へ `Linear(8,32)` の統計branchを加え、過去encoder summary/既存2統計へ加算する。288parameter追加、合計30,369。新projectionはweight/bias0初期化。未来の日次headは従来どおりbaseline+u*gを学習し、日次非負/総量和を保持する。

EMAをpointに固定加算しない。σが大きいと予測が必ず上がる/下がるという制約も付けない。学習が必要なら寄与を0にでき、需要量/日付/前後eventとの関係で寄与を決められる。未来h別σや予測区間を出すheadではない。

新少数確認は、単位対応・支持/未知mask、profile cutoffの数値アクセス前拒否、原週間patternのstdと残差σの区別、branch0初期化/同初期shape、branch入力への勾配・σ寄与の両方向。架空profile/量で接続だけを確認し、性能向上/条件付き確率の実証へしない。

## 次の比較案

接続確認を保存してから、追加入力branchを全0にしたcontrolと、8次元入力を有効にした候補を新しく学習する別unit。両側のshape/parameter数・初期状態/sampler/基準/損失/尺度を同じにして、表現追加だけを比較する。過去のweights/完成forward/確認を再実行しない。旧EMA等重み候補はpoint対照として選び直さない。

前処理z-score、σによるloss重み、期間長入力は一緒に変更しない。σでlossを割ると誤差の大きい場面の重要度を変え、平均数量の目標も変わり得るため、追加入力と別仮説にする。

fitは原630key/u/2013–14の正尺度15、回顧比較2015の18店25起点、尺度0群はbaseline-only。原fit統計profileを数量前に新規組立する必要はなく、fit量を使う新特徴処理としてweights前に保存する。2015profileは既保存統計ledgerを再利用し、同σ/EMAの再集計をしない。元日/Christmasのfit支持不足はそのまま。

学習を始めるunitでは、同initial/sampler/256step各一回・2015による選択なしを固定する。主問は追加入力対同shape control。primaryは全日/総量の店舗macro joint MSE、候補がcontrolとmean28の両方より小、かつ15中10店で両方より小を進捗条件。未達なら同統計の半減期/幅/seed/step探索を行わず保存する。今回はその学習を始めない。

direct ACTIVE（人の修正方針に従う入力研究）/automation PAUSED。新6機構確認のみ、新public数量/fit/予測評価/旧確認/CI0、追加agent0/CARE待ち。全実行/記録/prep上限、formal_permission=false/credit0/native禁止/登録holdout未読維持。Git独自code/架空確認/集約docsのみ、原quantity/profile/尺度/ledger/予測/weights送信0。
