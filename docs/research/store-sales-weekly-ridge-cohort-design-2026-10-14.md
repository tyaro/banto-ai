# 8週共有補正：数量支持群とゼロ尺度群を分ける別実験

2026-10-14。人の「進めてください」に従う新しい契約。[前実験の固定18店条件未達](../results/store-sales-weekly-ridge-readiness-2026-10-14.md)を保全し、成功へ変更しない。2015数量を新しく読む前に本案を固定する。

## 群と適用範囲

全18店の対応を保持する。2013–14だけの保存支持から、正の観測平均uと10窓以上の完全8週/label支持を持つ15店6/7/9/10/13/14/15/17/18/19/23/25/26/27/30を新fit群に宣言。各42窓・合計630行は前診断の保存feature-label ledgerを再利用し、再組立/旧fitの反復をしない。0 label3窓も保持。

店21/22/29はfit期間の観測平均0/正値日0で新係数に使用しない。unsupported_zero_fit_scaleという役割を固定し、予測時はmean28基準へfallback。0尺度へ任意のfloorや他店の尺度を借用しない。全ゼロの原因を未開店/無需要/営業状態と判定しない。2015結果や初回正値を見て群を入替えない。fit期間に全0だったことと、その後も0であることを区別する。

評価は既固定2015Jan13〜Dec15の25起点×18店、450要求窓。全18店のavailable/不能を保持し、15店の成功を18店の学習成果としない。旧6店2016/2017/予約31〜54・新archiveを読まない。2015は旧研究でも読まれた回顧開発期間であり、未見holdout・未知店舗への移行ではない。

## 係数・尺度・solver

新tools/demand_weekly_ridge.pyは8特徴とy=(A−B)/(14u)だけを受け取る。fit行の店舗/日付/label終端を数値payloadより前に検証し、2015Jan1以降のlabelや対象外store/重複を拒否。15店の支持10以上を要求。

重みはN/(15*n_store)。同重みで特徴中心c/標準偏差sとy平均aを作る。定数列はz0/傾き0。非定数列z=(r−c)/s、G=sum(w*z*z^T)+I、h=sum(w*z*(y−a))、G*b=hを固定Choleskyで解く。8特徴には線形従属があり得るがridge1を緩和しない。切片無罰、特徴やridgeのgrid0。normal equation残差を保存し、solver失敗なら原証拠を保全して停止する。

基準B、共有切片max(0,B+14u*a)、8特徴候補max(0,B+14u*(a+b^Tz))。正尺度店の特徴不足では8特徴候補をBへfallback。B不能は全方式null、label不能は採点不能で理由保存。0尺度群は全方式Bへfallbackしてraw誤差だけ記述し、尺度化MSEを0や別店単位へ補わない。

新少数確認は、相関/従属列の既知解とnormal equation、店等重みと定数列、対象外/未来fit payloadの早期拒否、特徴なし/尺度0のbaseline fallback、負補正の非負復元とB不能のnull。旧入力5確認や旧model/CIを反復しない。

## 実行順と採点

新source/本案/元630行・役割・尺度・日付のpinを保存。fit候補支持と除外理由を保存→新係数630行fit一回→係数と選択なしを保存→元snapshotの18店2015数量だけを新しく数値解釈→origin前の入力から予測→labelを別に採点、の順。2014contextは原snapshotから必要日だけ読取り、fit用uは保存2013–14値を再利用。新尺度fitや前48窓の組立を反復しない。

主指標は正尺度15店の店舗macro尺度化総量MSE。利用可能なB/labelの全窓を含め、特徴不足fallbackを除外しない。全体macroが両対照より小かつ15中10店以上で両対照より小という新群の工程上の進捗条件を固定。旧12/18の条件を満たしたとはしない。条件未達なら同特徴NN/係数grid/seed/2017追試へ進まない。

全18店では原単位RMSE/MAE/WAPE/Biasと不能数、15店と0尺度3店の別集約・店舗別結果を保存。0尺度3店の尺度化指標null、分母0のWAPE/Biasもnull。初回正値・正値期間の有無は評価後の記述として保持し、群の選択や稼働開始の先読みへ使わない。学習3店を除いた理由・旧条件未達の記録を表に残す。

## 保存と停止

一回の新fit/2015回顧評価を保存したところで区切る。採択、メーカーPSI、TimesFM同等、分位点/サービス水準、未知系列への成功は示さない。研究基準mean28総量＋限定暦配分を維持する。原失敗・閉鎖rootは不変、追加agent0/CARE手動待ち・自動確認0、automation PAUSED不変。

900秒2GiB/output1GiB/single32MiB/files32、通常24file768MiB/失敗8file256MiB、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files。formal_permission=false/credit0/native reader禁止/登録holdout未読。Gitは独自codeと集約docsのみ、原quantity/ledger/尺度/係数/予測を送信しない。
