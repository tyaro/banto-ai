# 公開暦と営業予定を分ける小型モデル接続の条件（2026-10-14）

営業日水準と休業0の機構、[区間入力](../results/demand-event-interval-input-2026-10-14.md)の次unit。保存報告/sourceの読取りから接続条件を固定する。新数量読取り・模型実装・学習・旧確認/評価/CIは今回行わない。

## 研究の問い

**名目イベントの当日だけでなく前後3日の入力を残すと、同じ小型模型の期待販売数量が改善するか。** 公開小売売上での回顧開発の問いであり、休業calendarや休暇の長さが実際の需要を改善するかを同じ比較へ含めない。

旧候補も当日の名目8eventを既に受け取っている。次の差分はevent入力の有無一般ではなく前後の情報。休業構造・営業日水準・モデル形状・損失を同時に替えた結果を「休日前後の効果」と解釈しない。既知2015で設計した後の検証なので、未見性能や因果効果とはしない。

## 情報の可用性を二つの経路へ分ける

|情報|公開Store Salesでの次の扱い|確認済み営業予定を持つ実用経路|
|---|---|---|
|日付/曜日/年内位相|既知日付から計算|同じ|
|名目8月日|固定の季節指標として前/当/後を生成|実予定と名目指標を区別|
|実休日/振替/Bridge/地震後Event|公表履歴がなく未来既知入力にしない|起点までの版だけ|
|店ごとのopen/closed|unknown、祝日からclosedにしない|独立した営業予定|
|休暇の実開始/終了/期間長|不明。名目単日を連休へ拡張しない|区間と確認範囲/長さmask|
|未来販促|使用しない|予定版/施策属性が別途必要|

固定月日は01-01/05-01/05-24/08-10/10-09/11-02/11-03/12-25。これは保存済みの2013–15暦調査で抽出して既研究でも使ったpolicy。2013–14時点の実公表予定を復元したという証拠ではない。今回の設計前に固定された名目季節指標として使い、未来のCSV行は読まない。

元日観測0は原salesとして残すが、全店休業という証明にしない。Christmas欠測を0labelへ補わない。11月2/3日の隣接eventは別ID/種別で保持し、連続休暇長2日の確認とみなさない。期間入力を実装できたことと期間長の数量効果を検証できることは別である。

### 公開販売と営業条件付き予測の意味

公開経路は実観測salesの平均を予測する。過去の観測0を全て保持し、営業不明を除外してstrict営業日水準を捏造しない。同曜日mean28は全観測から作る新比較基準で、確認済みopen-only平均とは別のnamespace/policyを持つ。

営業表がない公開経路ではdemand_operating_sales.apply_operating_salesを使わない。この関数は営業する場合のmeanから条件付きsalesを作るため、公開sales模型のmeanを入力すると意味が変わる。unknownを全てopenと仮定したシナリオを、公開経路の無条件sales予測へ読み替えない。

確認済み営業予定の経路ではopen-only水準と営業時meanを使い、明示した対象契約のclosedだけ0にする。unknownの日は営業仮定付き、期間meanは日次の和。新12機構確認があるが、公開データ上の性能評価はない。

## 次の入力adapter

単一storeの自己過去56日・未来14日、過去observed mask、固定fit尺度u、mean28日別baseline、2統計、過去/未来暦を返す。店舗数3やtrain尺度buffer3への固定を外し、店舗間の同日量やseries attentionを使わない。共有はパラメータで、他店の未来数量ではない。

暦は曜日sin/cos・年内sin/cosの4要素＋8event×相対日−3..+3の56要素、計60。単日の名目eventをevent-kind別に作り、距離はtarget−event_date。年越し/閏年も日付演算で処理する。各channelの意味とschema版を保存する。実予定のknown_atは捏造せず、名目policyの生成履歴を別metadataへ置く。

過去数量はorigin前56日だけget。missingは数値tensorで0とmask=false、実0はmask=true。q/uで水準を残し、context mean/uとpopulation std/max(mean,.01u)を補助にする。過去28日同曜日の有効観測が3以上なら日別baseline、支持不足はnull。全欠測、尺度0はNN適用不能。尺度0群は基準だけの別役割を維持する。

当日controlも同じ60次元で、offset!=0の56channelを0にする。候補だけ前後channelを有効にする。両側のbaseline/量/尺度/曜日位相/shape/重み初期化を一致させる。期間長/営業状態をこの固定入力へ追加しない。

次unitはこのpure adapterと、日付・maskだけのfit支持確認。原modelのforwardや完成確認を再実行しない。少数の新確認で年越し、前後と当日controlの差、同じbaseline/統計、future量getter、実0/missing/支持不足、公開policyと営業条件付き経路の分離を確認する。

## その後の小型模型案

入力機構・fit支持を保存した後の別unitで新namespaceを実装する。B<=8、V1/C56/P7/H14/D32/L1。過去7日ごとにquantity/mask/calendarを並べ、434→32のpatch projection。8過去tokenに位置埋込み、4head・feedforward128・dropout0・GELU・norm_firstの一層encoderとLayerNorm、過去token平均に2統計の32次元projectionを加える。未来の日ごとにhidden32＋calendar60＋lead1を結び93→32→1の共有headで補正g_dを作る。

`sales_mean_d = max(0, baseline_d + u*g_d)`、`total_mean = sum_d(sales_mean_d)`。final layerを0初期化して初期pointはbaselineに一致。eventの効果を総量保存の配分だけに制限しない。これは非負point meanの近似で、ReLUの0点/負領域は勾配の制約があり、全ゼロ群への外挿成功を保証しない。

出力meanのみ。既存quantile head/weightsを変更・流用せず、総量quantileの比較は今回の主問へ混ぜない。営業表経路の構造0は別interfaceであり、この公開経路にnominal holiday maskを掛けない。

損失は `.5*日次MSE/u² + .5*総量MSE/(14u)²`。日次は観測labelだけ、総量labelは全14日観測時のみ。欠測を0として損失を作らない。母数が不足するbatchは理由保存して停止し、未完batchを成功へしない。

## 数量実験の固定案と順番

入力の支持確認までが次unit。以下の学習をその前に開始しない。

- 既保存正尺度15店6/7/9/10/13/14/15/17/18/19/23/25/26/27/30、2013–14 fit。元の閉鎖cohort記録の630store/origin keyとfit uを再利用する。旧8週特徴やsolverは再実行しない。日次の必要量/label組立は新候補のために元snapshotから行う別作業。
- 2015Jan13〜Dec15の既固定25起点、18店450要求を回顧開発として維持。positive15をNN、zero-fit-scale21/22/29はbaseline-only。2016/2017/予約31〜54は読まない。不能/欠測も要求対応を残す。
- 当日control一件と前後候補一件だけ。新initial stateを一つ保存して両側へ使い、同じ新256×8 sampler key列をfit630keyからseed20261014で作る。旧3store samplerは対象が違うので使わない。
- CPUfloat32/2threads/interop1/deterministic、256step、AdamW lr3e-4/betas(.9,.999)/eps1e-8/weight_decay.01/foreach=false/fused=false/gradnorm1。最後のstep256を固定、2015でcheckpoint/seed/幅を選ばない。二件とも係数/重みを保存してから2015labelを開く。
- 主問は前後候補対当日control。同条件mean28を学習なしの対照へ併記。旧mean28総量＋限定暦配分の完成結果は研究基準として保持するが、fit条件の違う原補正係数を新実験へ混ぜて勝者にしない。

fit metadataから、kind/offsetごとのdistinct store/date・event-year・observed label支持を数量前に保存。支持0のchannelは両側とも0に固定して支持なしと表示する。支持があるだけで信頼できる休日係数とはしない。kindと実休業の交絡は解消していない。

主指標はpositive15のevent前後日におけるmacro尺度化日次MSE。複数originが同じstore/target_dateを予測する場合はその日内で誤差を平均してから日平均/店平均とし、重複originでevent年の支持を増やさない。event評価日の定義は上の8種±3、重複日は一日として採点。支持0channelも評価の範囲から黙って除かない。

全日の日次/14日総量MSE・Bias・原単位RMSE/MAE/WAPE・store別・kind/offset別・要求/不能/fallback数も保存する。新進捗条件は主指標がcontrolとmean28の両方より小、15店中10店以上で両対照より小、かつ全日macro日次MSE/総量MSEが両対照以下。これは工程上の条件で、独立検定や一般優位の保証ではない。

条件未達なら同仮説のseed/幅/step/期間長追加gridは行わず、結果保存で区切る。支持不足で主指標を定義できない場合も採択せず保存する。未使用系列への適用やメーカー用途は別条件が必要。

## 境界

今回固定したのは入力・接続・比較案、模型/学習/支持確認は未実行。進捗に合わせsource/pins/原エラーをfresh rootへ保存し、完成rootへ追記しない。二模型の新実験も一unit全体の900秒/2GiB/output1GiB/single32MiB/files32を緩和しない。通常24file768MiB/失敗8file256MiB、診断16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16filesを維持する。

direct ACTIVE/automation PAUSED、追加agent0/CARE手動待ち・自動確認0。formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。Git設計/集約文書のみ、原quantity/予定実績/ledger/尺度/係数/予測/重み送信0。
