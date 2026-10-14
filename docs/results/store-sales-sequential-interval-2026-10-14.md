# 完了した誤差で更新する14日総量区間（2026-10-14）

[固定設計](../research/store-sales-sequential-interval-design-2026-10-14.md)に従い、各予測起点より前に完了した窓の残差で区間を更新した。全体の改善は小さく、店舗ごとの悪化が残るため実用区間として採択しない。mean28点予測は原保存値のまま。

## 実施手順と先読み境界

固定6店舗4/8/16/20/24/28、2016Jan1+14*k（k0..24）の150窓。新archive/2017/予約群は読まない。元自身2013–15のcalibration ledgerと元2016のpoint/actual/scaleを閉鎖記録からpin照合して再利用した。2016は既知の回顧期間であり未見評価としない。

各origin dの使用候補は同storeでtarget終端(origin+13日)<dの窓だけ。日付・storeのheaderを先に選別し、未完了窓のavailability/context/residual payloadへ触れない。保存JSON全体の読取り自体は行うため、本番の受信時刻・アクセス制御の証明ではない。新selectorと評価側の遅延読取りwrapperが数値アクセスの境界を確認した。

元availabilityと過去56日正値ありの条件を維持し、最新26完了窓・最低20・row重み1・Q10/Q90を一案として固定。欠測を0誤差にしない。局所scale=max(B,.01*14*u)は元保存値と一致。支持不足はown Q=null/理由付き、元共有local分位点fallback。labelはtarget完了の前日締め後に使えるという研究仮定で、実際の公開遅延や訂正履歴はデータにない。本番as-of可用性は未証明。

使用日付/target終端/残差/支持を全Q計算前に保存。日付・残差・重みが元自身poolと同じ店20の初回21窓は原Qを再利用し、再計算しない。新集合149件だけ新Q計算、同新集合の再計算0、実fallback0。店20支持21〜26、他5店舗26。fallbackの実データ指標はn0/null、確認例の通過を性能へしない。

## 新区間と保存固定区間

新時点別区間のrestore/assessmentを一回だけ実行。旧point、固定区間、旧score、元calibration、元確認は反復しない。原pointとlocal scaleを150件すべて照合した。

|方式|包含数/150|包含率%|下/上の外れ|平均幅|平均interval score|
|---|---:|---:|---|---:|---:|
|固定自身・原保存|122|81.33|11/17|1559.877767|1909.937034|
|最新26完了窓・新|124|82.67|11/15|1472.267796|1897.620559|

平均幅5.62%減、score0.64%改善。区間scoreは低い方が良い。包含率だけで判断しない。全体の変化は記述値で、統計的有意性・名目80%の有限標本保証ではない。

|店舗|固定包含率%|更新包含率%|固定幅|更新幅|固定score|更新score|
|---|---:|---:|---:|---:|---:|---:|
|4|80|80|1166.043203|1163.253683|1337.223890|1414.310254|
|8|92|88|2267.083617|1894.079085|2361.519741|2195.378517|
|16|76|76|612.057792|642.591742|847.269896|893.473333|
|20|84|88|1783.636571|1790.340572|2017.642213|2091.275124|
|24|64|72|1745.753572|2097.792850|2834.941343|3063.376785|
|28|92|92|1784.691845|1245.548841|2061.025121|1727.909342|

score改善は店8/28だけ、4/16/20/24は悪化。店24は64→72%と包含率が上がる一方、平均幅1745.75→2097.79/score2834.94→3063.38で対価が残る。店16は76%のまま。店20は84→88%でもscore悪化。店舗別に方式を選び直すことはしない。

店24の四半期別：

|四半期|n|固定包含数|更新包含数|固定score|更新score|
|---|---:|---:|---:|---:|---:|
|1|7|4|4|3025.005940|3601.592289|
|2|6|4|4|3033.686747|2500.539205|
|3|7|4|5|3044.694137|3525.510091|
|4|5|4|5|2036.702509|2338.293545|

時点更新だけでは全店舗の不足を解消していない。26窓・20支持・確率・尺度を2016結果後に探索して改善へ補わない。時系列依存/context重複を独立標本へ読み替えない。メーカーのサービス水準、在庫/廃棄費用、PSI、TimesFM同等性能、正式受入は未評価。

## 新実装・原証拠

新demand_sequential_interval.py、新5確認一回allpassed：未完了payload拒否、最新26/19対20境界、原同一pool Qの再利用、異store拒否、欠測と実0残差の区別。旧確認/fit/point/CI反復0。新モデル・確認helper失敗0、先行原2helper失敗と全closedrootは不変。

実計算0.232198秒/OSpeak private21266432B、CPython3.14.0/Windows/CPU、Torch/新NN0。計算親HEAD bd006f5220932b7a53e1343b6a146ef3112c9b82＋未commit新sourceでclean commit計算とはしない。

文書用scriptを生成するforeground Python stdinが、外側と内側の三重引用符の衝突でSyntaxError/exit1。isolate/モデル失敗ではなくforeground parserの失敗で、doc helper/root作成・tracked変更前だった。tool chunk d46f61の選択エラーmetadataを別rootへ保存。原stdin全体・元process全stdioの保存ではない。原未起動rootを再実行せず、このv2文書helperだけで保存数値を文章化した。旧評価・新5確認の反復0。

new script/source全文/固定設計/元input pins/時点別pool日付・支持/Q/原Q reuse/新150区間・assessment/全6店舗・四半期/原stdio・exit0を新閉鎖rootへ保存。本文sequential-interval-doc-v2-records。原Git保存はcommit2完了後push通信切断でfailed、別continuationもremote読取りexit128でfailed/追加push0。停止保存はsequential-interval-pause-recordsを優先し、原failedは変更しない。Gitは独自codeと集約docsだけ、原数量/ledger/尺度/予測を送信しない。

## 研究上の判断と次

同じ2016で区間候補を増やす段階はここで区切る。研究基準mean28総量＋限定暦配分を維持し、区間は採択せず研究用の記述として保持する。区間更新の機構は成立したが、それだけで独自小型モデルの追加価値は示せない。

次unitは研究ロードマップの主問へ戻り、保存済み小型モデル・平均出力・共有残差・区間の設計と結果を読取りで整理する。どの仮説を否定でき、どの仮説は未検証かを分け、独自モデルを次に学習するために必要な追加情報・群・評価契約を文章で固定する。既存scoreを再計算せず、同じ数量差NN/区間grid/2017追試を自動で始めない。未来販促予定がないことを研究全体の停止条件には戻さない。

direct ACTIVE/automation PAUSED、CARE手動報告待ち・自動確認0、追加agent0。900秒2GiB/output1GiB/single32MiB/files32、通常24file768MiB/失敗8file256MiB、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files不変。formal_permission=false/credit0/native reader禁止/登録holdout未読/正式受入未完了。

## 保存後の通信停止

時点別区間の独自code/集約docsはローカル2commitを作成したが、GitHubへのpushはexit128/Recv failure: Connection was reset。別rootでremoteを一度読取る操作もexit128になり、反映を確認できなかった。新commitや評価を繰り返さず、追加push0。元full stdout/stderr/return/traceとfailed状態を各閉鎖rootへ保存した。人の自走停止方針に従いdirect PAUSED、automation PAUSED不変。停止文書をlocalだけcommitして保全する。remote反映不明、送信完了とはしない。
