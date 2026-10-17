# 自己の8週間を残す入力境界の確認（2026-10-14）

研究中間整理と[固定設計](../research/store-sales-weekly-history-design-2026-10-14.md)に従い、新しい純粋入力関数を実装し、新5確認を一回実行した。全件passed。これは新情報を入力に保持する機構の確認であり、予測性能の改善・共有学習の成功ではない。fit・新データ読取り・新forecast・旧確認・CIは0。

## 実装の契約

`tools/demand_weekly_history.py`は任意の一店舗の自己履歴を受け取る。Torch・label読取り・fit・外部IOを持たない。origin前56日を古い順8×7日へ分け、全週観測時だけ `r_k=(W_k−B/2)/(7*u)` を返す。Bは直前28日の同曜日平均14日総量、各曜日3以上を要求する。

実0は観測値、Noneは欠測。週に一つでも欠測があればその週合計はnull、新特徴全体もnull。不足週・日付・観測数を保存し、Bが作れる場合はbaseline fallback、Bも不能なら予測不能とする。欠測合計を0へ補わない。全56日が実0ならB0/8特徴0で利用可能。

`fit_scale`は対象store・日付を先に確認し、2013〜fit cutoff前の量だけを数値で読む。observed=bool・欠測null・重複日付拒否、実0を分母へ含める。今回既定cutoffは2015Jan1。尺度なし/0はunsupported、2013–15全体尺度を2015評価のfitへ流用しない。

## 新5件の結果

| 確認 | 結果 |
|---|---|
| origin以降getが失敗するhistoryで過去だけ組立 | passed |
| 同じB/直近xでも古い4週の違いが8特徴に残る | passed |
| 全実0、週欠測、全欠測、非正尺度を区別 | passed |
| quantitiesとuの共通10倍で特徴不変・B10倍 | passed |
| 2015/異storeのpayloadを触れず2013–14尺度作成 | passed |

説明用の8週間例は固定設計のまま。全週700に対し、古い4週350/1050/350/1050・新しい4週700でもB1400/x0は同じ。8特徴は全0と、−.5/+.5/−.5/+.5/0/0/0/0を区別した。実績labelを置かず、合成例の予測精度を測っていない。

欠測例は最古週の1日欠測。新全週特徴はnull/週支持6、同曜日基準は作れるためfallback指定、旧直近xは0のまま。新支持は旧一変数より厳しいため、今後の実評価ではfallback数と全対象の結果を併記する。都合の良い完全観測窓だけの精度へ置き換えない。

全0尺度や全欠測はunsupported。平均が正でないときの新回帰を実行したものではない。数量単位不変性も推論資源・実設備適合・メーカー箱数の保証ではない。

## 保存と次

実CPython3.14.0/Windows、確認・原証拠保存のparent経過0.202589秒。test childの全stdout/stderr/return0を判定前保存した。whole-modelのpeak計測ではない。source全文/固定設計/元source pin/新確認scopeをfresh閉鎖記録へ保存。原shared residual/mean model・固定設計はbytes不変。原失敗/閉鎖rootを変更せず、新script/確認を反復しない。

次unitは8特徴ridge1のsolver・等店舗重み・fit尺度/中心/定数列・非負復元・baseline fallbackの新少数確認と、保存18店snapshotから2013–14 fit/2015開発の日付・支持・新尺度を係数前に固定する準備。まだsolver/新fit/2015評価は未実装・未実行。量の大小や残差で群を変えない。支持不足は保全して止める。

今回の全5passを理由にNNの学習を自動開始しない。一回ridgeが全体macro MSE両対照より小＋12/18店を満たして初めて次の共有モデル設計の根拠となる。旧検証6の2016/2017・予約31〜54は追加読取り0、既知時期の試行を未知系列の実証へしない。

研究はACTIVE、automation PAUSED不変、追加agent0/CARE手動報告待ち・自動確認0。基準mean28総量＋限定暦配分維持/区間不採択、TimesFM同等/メーカーPSI/正式採択0。900秒2GiB/output1GiB/single32MiB/files32、通常24file768MiB/失敗8file256MiB、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files維持。formal_permission=false/credit0/native reader禁止/登録holdout未読。

本文representative-store-sales-weekly-history-checks-20261014-records、Git後同-weekly-history-git-records post-save優先。Gitは独自codeと集約docsのみ、原quantity/ledger/尺度/fit/予測は送らない。
