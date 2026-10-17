# 自身の過去残差による総量区間と期間診断（2026-10-14）

[自身の区間設計](../research/store-sales-own-history-interval-design-2026-10-14.md)と[保存残差診断の固定条件](../research/store-sales-own-interval-diagnosis-design-2026-10-14.md)を実施。自身の過去を使う方法は共有分布より全体score/幅を改善したが、店舗ごとの不足を残す。今回は採択しない。点予測mean28は変更0。

## 入力と役割

対象は固定6store 4/8/16/20/24/28。閉鎖shared-prefixの2013–15 quantity/maskから対象storeだけを数値読取りし、元18trainの共通69日付を照合して新しい過去窓のcalibrationを作成した。元18train/2016のpoint forecastは反復しない。新archive/2017/予約群を読まない。

自己のorigin前56日から基準Bと支持を作り、label14日を別に取得。context49以上/label14全観測/28日各曜日3以上、過去56日正値ありでpoolを選ぶ。future labelがゼロか否かでは選別しない。scale=max(B,.01*14*u)、signed total residual=(A−B)/scale、Q10/Q90、row重み1。uは元保存2013–15観測平均、欠測と実ゼロを区別。

support20以上で自身の分位点、不足はown Q=null/理由付き・元共有分位点fallbackという固定方針。n20は工程上の目安でcoverage保証ではない。各storeの日付/支持/floorを分位点前保存→Q保存→元2016の150point/actualを読む順。6storeは先行pointモデルfit未使用でも、今回は自身のcalibrationに使用したのでzero-shotやcalibration未使用storeとはしない。

|店舗|要求過去窓|正値context支持|除外zero context|floor|自身Q10|自身Q90|
|---|---:|---:|---:|---:|---:|---:|
|4|69|69|0|0|-0.077620683|0.108372854|
|8|69|69|0|0|-0.078582833|0.104569315|
|16|69|69|0|0|-0.129694957|0.128950883|
|20|69|21|48|0|-0.130284858|0.164875540|
|24|69|66|3|2|-0.087533348|0.071096711|
|28|69|69|0|0|-0.085588465|0.134881224|

6storeとも最低支持を満たし、実際のfallback0。支持不足の経路は新機構例で確認したもので、実データでのfallback性能はn0/null。店20の支持は2015年だけ21窓、店24は66窓/floor2。欠測/0/原因不明の長期ゼロを別に保持し、休業/未開店/欠品へ補わない。

## 保存150窓での一回比較

mean point/actual/scaleを原local共通区間と照合し、自身の区間だけを新しく復元・score計算した。原共通区間は保存値を再利用。2016は既知の回顧期間で、未見holdoutへ戻さない。

|方式|covered/150|coverage%|below/above|平均幅|平均interval score|
|---|---:|---:|---|---:|---:|
|共有/local原保存|137|91.33|4/9|2070.600570|2198.416510|
|自身/local新|122|81.33|11/17|1559.877767|1909.937034|

平均幅は約24.7%小、scoreは約13.1%改善。coverage91.33→81.33%は、区間を狭くした対価とともに読む。名目80%に近い全体値だけで各storeのcalibrationを認定しない。

|店舗|共有coverage%|自身coverage%|共有幅|自身幅|共有score|自身score|
|---|---:|---:|---:|---:|---:|---:|
|4|96|80|1687.438184|1166.043203|1688.207392|1337.223890|
|8|100|92|3331.705502|2267.083617|3331.705502|2361.519741|
|16|80|76|636.939256|612.057792|844.613587|847.269896|
|20|76|84|1626.519840|1783.636571|2000.201681|2017.642213|
|24|100|64|2962.160173|1745.753572|2962.160173|2834.941343|
|28|96|92|2178.840466|1784.691845|2363.610725|2061.025121|

店24は64%、店16は76%で不足。店20は84%へ改善したが支持21で尾部事例が少ない。結果後にstore別の良い方式を選ばず、全storeの原結果を残す。区間のメーカーPSI・サービス水準・finite sample保証・TimesFM同等の採択には進まない。

## 保存残差の事後診断

Q/区間を再fit・再計算せず、calibration年と2016四半期の残差zを記述した。標準偏差はddof0の記述統計。context重複/時系列依存があり、CI/独立な標本数・因果を示さない。

店20のQ10を与えたoriginは2015Aug11、Q90は2015Nov3。21行でQ10は3番目/Q90は19番目の順序統計であり、工程上の支持通過を安定した尾部推定へしない。

店24のQ10 origin2014Feb25、Q90 origin2015May19。年別に：

|calibration年|n|残差mean|残差std ddof0|floor|
|---|---:|---:|---:|---:|
|2013|21|0.012864995|0.047798647|0|
|2014|21|0.168763348|1.271182712|2|
|2015|24|-0.000172078|0.060759808|0|

2014年のstdはfloor2行を含むため、正常変動の大きさと同一視しない。外れを除去して再fitする変更はしない。2016の店24は以下で、一つの四半期だけが外れた結果ではない。

|四半期|n|残差mean|残差std ddof0|covered|below/above|
|---|---:|---:|---:|---:|---|
|1|7|-0.028071415|0.069832254|4|2/1|
|2|6|0.045995961|0.046200618|4|0/2|
|3|7|-0.022975440|0.072472093|4|2/1|
|4|5|0.006359494|0.047776694|4|0/1|

時点により残差の位置/広がりが変わることを記述したが、販促/営業状態/供給制約の原因を補わない。自己履歴の分布でも、その後の分布を保証しない。

## 実装・原証拠・次

新demand_own_interval.pyは対象store/prefix numeric guard、input/label分離、支持20/own null/shared fallback、role明示を持つ。新4少数確認一回allpassed。旧新7区間確認、元calibration/区間、失敗helper/CI反復0。今回の新helper失敗0、先行原2helper失敗・全旧closedroot不変。

自身calibrationと新150区間0.229414秒/OSpeak22122496B。保存残差診断0.017184秒/private16506880B、CPython3.14.0/Windows、Torch/weights/新NNなし。計算38e400親＋未commit新source、clean commit計算claim0。

source全文/設計/原input・date・Q pin/69過去窓ledger/支持/Q/150区間/assessment/年・四半期記述/原stdout-stderr/exit0を新閉鎖rootへlocal保存。分布借用には原failed local rootの完成済みQ、比較には原failed v2の完成150ledgerをpin照合して再利用し、原failedを書き換えない。本文own-interval-doc-records、Git後own-interval-git-records post-save優先。

次は[完了した誤差だけで時点別に更新する固定案](../research/store-sales-sequential-interval-design-2026-10-14.md)。最新26/最小20を一案として固定し、current/future targetを読まないselector・原同日付Q再利用を少数確認してから新計算する。期間/係数gridやstoreを結果後に選び直さない。新手順は未実装/未実行、本番のlabel確定遅延は未検証。

direct ACTIVE/automation PAUSED、CARE手動報告待ち・自動確認0/追加agent0。実行900秒2GiB/output1GiB/single32MiB/files32・通常24file768MiB/失敗8file256MiB、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files不変。formal_permission=false/credit0/native reader禁止/登録holdout未読/正式受入未完了。Gitは独自code・集約docsのみ、原quantity/ledger/尺度/fit/予測送信0。
