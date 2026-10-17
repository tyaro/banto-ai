# 店舗間の共有数量残差：一回実装・検証（2026-10-14）

[固定設計](../research/store-sales-shared-residual-design-2026-10-14.md)と[群/入力契約](../research/store-sales-shared-series-input-contract-2026-10-14.md)に従い、新しい一候補だけを実行した。共有補正は事前進捗条件に達せず、不採択。mean28総量基準を維持し、同じ数量差を使うNN/係数grid/別seed/2017追試は始めない。

## 機構と入力

新tools/demand_shared_residual.pyを追加。past_inputはorigin前56日だけを読み、自己の直前14日総量とmean28総量の差xを尺度14*uで正規化する。labelsは別関数。fitは宣言した18学習店舗・2015年までの行だけ、重複window/未来/検証店舗を拒否。店舗等重み、固定ridge1、切片無罰。x不能はz0で切片fallback、非負総量に復元。

5つの新少数確認を一回allpassed：未来getter拒否/店舗等重みとridge式/検証店・未来fit拒否/ゼロ・欠測・fallback/欠測targetはnull。旧確認・モデル・CIは反復していない。新関数の確認を全repository回帰成功や正式受入へしない。

保存prefixの24店舗2013–15数量・mask・71適格window/store・尺度を照合し再利用。学習18：6,7,9,10,13,14,15,17,18,19,21,22,23,25,26,27,29,30。検証6：4,8,16,20,24,28。予約/旧storeの新数量読取りなし。同family・共通都市があり、新都市/メーカー/別チェーンへの結果ではない。尺度uは各店舗の2013–15観測平均、実ゼロは含み欠測は含まない。検証6のprefixは過去の尺度と入力支持に使うが、係数には使わない。

## fitを検証読取り前に固定

元71適格windowのうち直前14日全支持69/store、計1242行をfit。各store寄与69、総重み1242。ゼロcontext174行/ゼロtarget174行を除去せず保持した。型/期間/店舗/featureの支持以外で行を選ばない。

共有x中心0.008391991815/尺度0.316741493962、切片0.023982191423/標準化x傾き0.184392771397/ridge1。係数・使用日付・source/input pinをfit-before-validationへ保存してから2016年の新quantityを読んだ。

元ZIP/memberのSHA/bytes/3000888行をstream照合。新検証6店舗のみ、固定25起点（2016Jan1+14*k）のcontext/labelに必要な2016Jan1〜Dec15の数量2100行を抽出し、原IDを保存した。2015contextは元prefixを使う。onpromotion・2017・予約群・学習店舗2016を数値化しない。原archive/閉鎖root変更0。

## 固定150窓の結果

150/150利用可能、不能0。x支持144/不足6、後者は切片fallback。予測起点前56日に正値のある群150、ない群0（指標null）。全ゼロcontextでの予測性能を今回の検証から補わない。

|方式|尺度化総量MSE|原単位総量RMSE|総量WAPE%|総量Bias%|
|---|---:|---:|---:|---:|
|mean28基準|0.017249834|538.161442|5.194279|-0.436950|
|共有切片|0.017506118|551.505006|5.428210|1.456110|
|切片＋共有数量差|0.020508816|559.336306|5.603785|1.182175|

|検証店舗|基準RMSE|切片RMSE|共有数量差RMSE|両対照より主MSE小|
|---|---:|---:|---:|---|
|16|227.811967|240.588984|242.332906|no|
|20|573.594534|572.470095|637.346375|no|
|24|758.073750|799.403576|789.784549|no|
|28|472.670977|505.100091|512.443888|no|
|4|383.995276|386.936515|370.031846|yes|
|8|641.288865|628.847767|623.638551|yes|

事前条件は、全体主MSEが基準/切片の両方より小さく、かつ4/6店舗以上で両者より小さいこと。今回2/6店舗、全体悪化のため未達。店4/8の局所改善を一般採択へしない。全体過小Biasから過大Biasへ動いた。この一特徴・一係数の失敗は、共有学習全般や独自モデル全般の不可能性を示すものではない。

長いゼロ期間の原因や尺度が悪化を生んだ因果は未確認。店舗20等を結果後に除外/尺度変更して成功へ補わない。新検証店の2016は今回初めて選別数値を読んだが、同じ公開dataset・都市・familyの限定的探索であり、正式/メーカー独立holdoutではない。

## 実行・保存

新fit/検証5.275921秒、OSpeak24932352B。CPython3.14.0/Windows CPU、Torch/旧weights未使用。計算parent 77094ed23bc1f28fb1ee916315329f71dabeae8d＋未commit新sourceの実行、clean commitからの計算とはしない。

閉鎖記録root 14files/530555B。script/source全文/固定設計/元snapshot・window支持pin/使用除外行/係数/2016原ID付き数量/予測/理由/店舗・入力支持・正値群別metrics/summaryをlocal保存。launcherの原stdout-stderr/exit0と5確認を閉鎖記録へ保存。原例外/旧失敗/旧closedroot不変、新helper失敗0。

## 次の未完成unit

[14日総量の不確実性の設計案](../research/store-sales-shared-total-interval-design-2026-10-14.md)を準備。元数量基準を維持し、新閉鎖train残差と検証ledgerから、未使用店舗への残差分布共有を確認する。新点予測/fit/抽出を反復しない。無条件とorigin前正値群の混合の違いを先に固定し、coverage/幅/interval scoreを別目的として扱う。2016はすでに点予測比較を見た回顧期間、未見testへ戻さない。区間比較はまだ未実装・未実行。メーカーPSI費用・採択・TimesFM同等・正式受入は未確認。

実行900秒2GiB/output1GiB/single32MiB/files32、通常24file/768MiB＋失敗8file/256MiB、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files不変。direct ACTIVE/automation PAUSED、追加agent0/CARE手動報告待ち・自動確認0。formal_permission=false/credit0/登録holdout未読/native reader禁止。Gitは独自code・集約文書のみ、原quantity/ledger/尺度/fit/予測送信0。本文shared-residual-doc-records、Git後shared-residual-git-records post-save優先。
