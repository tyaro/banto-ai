# 総量区間の尺度だけを変える一案（検証前固定）

共有残差区間は全体coverage79.33%/過去正値群82%だったが、店20は32%/36%。元2013–15平均には長期ゼロが含まれる。これを原因と断定せず、**同じ過去正値poolのまま、尺度だけをorigin前の数量水準へ合わせる**一案を固定する。元区間の計算/予測/fitは反復しない。

## 変更するものと固定するもの

学習元1242行からorigin前56日正値あり1068行を選ぶ条件、元store重み、Q10/Q90、weighted empirical quantileの定義を維持。元のfixed scale S=14*uから、local scale `S=max(B, .01*14*u)` へ変える。Bは保存mean28の14日総量で、origin前28日だけの量。uは保存prefix2013–15観測平均。floorはゼロ・小量で分母を有限にする固定工程条件であり、最低需要や営業状態ではない。

calibration残差を `z=(actual_total−B)/S` とする。元yに14*u/Sを掛ける計算と原保存actual−Bの対応を照合する。元入力・calibration行・weightを置換しない。pool支持/店舗寄与、floor件数、B/(14*u)のmin/median/maxを分位点前に保存してから新Q10/Q90を一回計算する。

各保存validation行の区間は `max(0,B+S*Q10)`〜`max(0,B+S*Q90)`。mean点Bは変更/区間内clipをしない。B0でも有限floorを使うが、潜在需要・営業開始・欠品・休業を推定で補わない。

## 比較

元shared-interval閉鎖rootの過去正値poolの保存区間を再利用し、同150窓と原actual/B/uを照合する。旧評価を再計算せず、newlocalのcoverage/上下外れ/平均幅/interval score(alpha.2)を一回集計。店舗別とfloor群、B/(14*u)の記述も保存する。2016は既知の回顧期間、変更案はその失敗を見た後の探索。区間のサービス水準採択や未見成功へしない。

global scoreが下がることと店舗coverageが均一なことを分ける。一店舗改善のため全体を一律拡幅する確率/倍率/閾値gridをしない。store20を除外した成功へ補わない。追加store/2017/新archive読取り/新point forecast・fit/NNを行わない。正式calibration保証なし、母集団/メーカーへの転用は未確認。

新少数確認は単位の倍率を変えても残差が不変・区間が同倍率で復元すること、ゼロpointの有限floorとmean変更なし。前の5確認は反復しない。script/source/design/inputpin/支持/分位点/原区間ledger/stdio/失敗を新rootへ保存、既存閉鎖root不変。Git独自codeと集約docsだけ、実行と記録上限・formal gate・CARE手動待ち・追加agent禁止・automation PAUSEDを維持。
