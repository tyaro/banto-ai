# 14日総量の共有区間と尺度案の結果（2026-10-14）

[元区間設計](../research/store-sales-shared-total-interval-design-2026-10-14.md)と[尺度だけを変える固定案](../research/store-sales-shared-local-interval-design-2026-10-14.md)を実施。点予測mean28は全行変更0。区間は14日総量残差から直接求め、日次quantileの合算やmeanの区間内clipをしない。

## 学習残差と支持

新閉鎖shared-residualの18store×69=1242行と元store重みを再利用。無条件pool1242にはzero context174行、origin前56日正値ありpool1068はそれを除く。条件は過去だけ、future labelのゼロを選別に使わない。正値poolの店舗寄与は店21が10、22が4、29が19、他15店舗各69。条件分け後に少数店舗を等重みへ拡大し直さない。母集団/メーカーへの校正保証なし。

固定尺度は14*u、uは元2013–15観測平均。local尺度はmax(保存基準B,.01*14*u)、同じ正値pool/weight/Q10/Q90を維持して尺度だけ変更。floorは計算を有限にするもので、最低需要や営業状態ではない。

|残差pool/尺度|支持|Q10|Q90|
|---|---:|---:|---:|
|無条件/fixed|1242|-0.131799113969|0.119958657206|
|過去正値/fixed|1068|-0.146549975885|0.132068542174|
|過去正値/local|1068|-0.132405566600|0.136754782571|

分位点を保存してから、元閉鎖validation-ledger150窓の基準/actual/uへ復元した。2016は既知の回顧期間。新quantity抽出/point forecast/point fit/旧学習/2017/予約群の読取り0。nominal80%は目標値で、以下の実測をcoverage保証にしない。

## 全体150窓

|方式|covered/150|coverage%|below/above|平均幅|平均interval score|
|---|---:|---:|---|---:|---:|
|無条件/fixed|119|79.33|12/19|1535.484876|2132.646885|
|過去正値/fixed|123|82.00|11/16|1699.310090|2190.071778|
|過去正値/local|137|91.33|4/9|2070.600570|2198.416510|

正値poolだけでfixed区間を広げるとcoverage79.33→82%だがscore悪化。local尺度はcoverage91.33%、平均幅はfixed正値群より約21.85%大、scoreも僅かに悪化した。coverageが大きいことだけで採択しない。全例で過去56日に正値あり、zero contextの検証性能はn0/null。localの検証floor作動0、train正値poolでは店14の1行のみ。

## 店舗別：全体値が隠す違い

|店舗|無条件fixed coverage%|正値fixed coverage%|local coverage%|正値fixed score|local score|B/(14*u)検証中央値|
|---|---:|---:|---:|---:|---:|---:|
|4|88|92|96|1513.075083|1688.207392|1.190250|
|8|92|92|100|2752.911319|3331.705502|1.343763|
|16|88|92|80|942.735136|844.613587|0.756174|
|20|32|36|76|2977.945461|2000.201681|2.942784|
|24|80|84|100|2666.099732|2962.160173|1.205573|
|28|96|96|96|2287.663935|2363.610725|1.054825|

店20はfixed32/36%しか覆わず、localで76%へ改善。検証基準Bは固定尺度14*uの中央値約2.94倍で、長いゼロを含む過去平均と今の水準が異なることを数値で記述できる。ただし尺度差を悪化の単独因果と認定しない。

店16はlocalでscore改善しcoverage80%、店8/24はcoverage100%で幅の対価が増えた。全体一律の確率/倍率変更・store20除外・結果後に店舗別の良い方式を選ぶ修正はしない。今回の2pool/1尺度案は不採択。区間の一律配布に不足がある記録として残す。

## 機構確認と失敗の保存

新shared interval5確認は一回allpassed：weighted CDF境界、総量復元とmean変更なし、過去だけの条件/重み維持、n0/missing null、interval score手計算。新local2確認も一回allpassed：単位倍率の不変性、zero floorとmean変更なし。完成5/2確認の反復なし。

localの最初のhelperは分位点保存後、fresh supportの整数storeキーと保存JSONの文字列キーを直接比較してAssertionError。原failed12file62426B、launcher failed15file11959Bに原script/source/分位点/支持/stdio/exit1を保全。保存JSON同士では全field一致を確認。通過2確認と分位点計算を再実行せず、continuationへ未完了の復元だけ渡した。

continuation-v1/prepとlauncher/prepはoriginal_source_scriptのpin表示を実行前に訂正するため未起動のまま閉鎖保全。v2は原failed scriptのpinを参照し、150区間の復元/score/ledger保存を完了した後、要約のratios関数を引き継ぎ損ねたNameErrorでfailed。v2原14file176576B/launcher10file8823Bを保全、元failedをpassedへ書換えない。

別summary-onlyはv2保存150ledgerのassessmentから未保存要約だけを完成。量予測・分位点・150区間復元/score・確認は反復しない。原2helper失敗は集計scriptの失敗であり、原区間数値の欠落やnative/Sol/正式性能failureへ読み替えない。元例外/完了prefix・その後の要約completeを別rootとして保持。

shared区間記述0.074118秒/OSpeak18427904B。localのoriginal calibration/restore全peakは未保存、summary-only 0.112237秒/private16584704Bを元全runtimeへ補わない。CPython3.14.0/Windows、Torch/weights/新NNなし。計算ed88f親＋未commit新source、clean commit計算claim0。

全新prep/records閉鎖、source全文/元input pin/支持宣言/Q/区間/assessment/指標/失敗/原stdioをlocal保全。本文interval-result-doc-records、Git後interval-result-git-records post-save優先。

## 次の未完成unit

[自身の過去残差を使える場合の設計](../research/store-sales-own-history-interval-design-2026-10-14.md)を準備。6店舗の自身の2013–15残差poolの支持を先に確認し、同日付/同尺度/同確率で共有分布との違いを分ける。自身のcalibrationを使うならcalibration未使用/zero-shotを主張しない。新計算はまだ未開始、既存区間や失敗helperの反復ではない。

メーカーPSI費用・本番サービス水準・TimesFM同等・正式採択は未確認。direct ACTIVE/automation PAUSED、CARE手動報告待ち/自動確認0、追加agent0。実行900秒2GiB/output1GiB/single32MiB/files32・通常24file768MiB/失敗8file256MiB、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files維持。formal_permission=false/credit0/native reader禁止/登録holdout未読/正式受入未完了。Git独自code/集約docsのみ、原量・ledger・分位点fit・予測を送信しない。
