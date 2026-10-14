# 固定した統計入力モデルの時間順検証契約（2026-10-14）

## 問いと現在の状態

[2015の同条件比較](../results/demand-statistical-feature-pair-2026-10-14.md)では統計8入力ありの差が約0.0141%と小さかった。次は**学習を増やさず、同じ店舗の後の年でも追加差が残るか**を一回確認する。本書は新数量を読む前に固定する契約であり、2016年の評価結果はまだない。

本unitは旧保存metadata・source・weightsのhash照合と契約の作成のみ。新2016数量、新profile、forward、fit、旧確認/評価/CI反復は0。契約を保存してから、次のunitで小抽出と固定二件の推論に進む。

## 既読範囲の確認と選択理由

|範囲|過去の研究での扱い|今回の扱い|
|---|---|---|
|店舗1/2/3/5/11/12の2016–17|各種予測/区間/小型模型で既読|使わない|
|店舗4/8/16/20/24/28の2016|共有残差150窓と区間で既読|使わない|
|今回18店の2013–15|prefix/支持/学習/回顧比較で既読|2015末のcontextを保存prefixから再利用|
|今回18店の2016|保存scope metadataでは数量未解釈|新たな時間順検証の対象|
|店舗31–54|予約・数量未読|保持し、使わない|
|登録済み正式holdout|未読・正式permission=false|使わない|

[群/入力契約](store-sales-shared-series-input-contract-2026-10-14.md)、[共有prefixの支持報告](../results/store-sales-shared-series-support-2026-10-14.md)、[共有残差の報告](../results/store-sales-shared-residual-2026-10-14.md)と閉鎖recordのconfig/input-bindingを照合した。prefixは24店の2013–15、2016抽出は検証6店だけで、今回18店の2016数量を解釈していないという保存fieldを確認した。

この確認は保存された実行scopeを根拠とする。公開benchmarkの全行bytesをhash/streamした過去があり、2016の同一暦は別店舗の結果から既知である。**全く見たことのないdataset/年度、別チェーン、厳密な盲検holdoutとは呼ばない。** 今回モデルのfit/developmentから離れた後期labelで、固定した入力表現の追加差を確認する限定的な時間順検証である。

## 固定する対象

- family：BREAD/BAKERY、小売の観測sales mean。
- 正尺度15店：6, 7, 9, 10, 13, 14, 15, 17, 18, 19, 23, 25, 26, 27, 30。2015の成績で店舗を追加/除外しない。
- fit尺度0の3店：21/22/29、baseline-onlyとして原要求/結果に残す。2016の水準で尺度を作り直さない。
- 全18店×25起点＝450要求。起点は2016-01-13＋14*k、k=0..24。最終起点2016-12-14、label終端2016-12-27。
- origin前56日、horizon14日。新入力全体の最初は2015-11-18。
- 2015の既保存prefixを再利用し、2016-01-01〜12-27の対象18店/familyだけを原trainから小抽出。日付/store/family選別後にだけsalesを数値解釈する。

固定gridは成績や欠測で移動させない。2015の25起点の月日anchor/stride/countを維持した翌年で、閏年による末尾1日の違いはcalendarが処理する。Christmasを含む最後の窓も要求に残し、欠測を0や13日総量へ変えない。

## 模型・前処理を固定

使用するのは前回のfeature_off-final.ptとfeature_on-final.ptの二件。30369parameters、各256step終了済みの状態を読み、eval/no_gradで各新入力一回だけ推論する。optimizer/fit/追加step/checkpoint選択/別seed/半減期変更は0。

|固定weight|bytes|SHA256|
|---|---:|---|
|入力なし|129688|bb3712725f620350659d1951ef62fa7089722bf701d043b043ac7b2a3e49fc39|
|入力あり|129688|e7db09e1e811ce1de853721de188b197e7aeb7b325752d453d87e8f07d5c485d|

原2013–14のfit尺度u、数量q/u・観測mask・context2統計、曜日/年位相と名目60暦、enabled42を維持する。元日/Christmas14channelのfit支持不足を、新年度のlabelで解除しない。実営業表/連休長/将来販促版を補わない。

過去一歩先weekday残差のmean/EMA7/28/sample σ/support/staleness/validを同じ部品で作る。新2016profileは各origin前56日だけ、過去residualのbaselineも各過去t前28日だけ。支持不足は原null/reason＋valid=false、実0とは区別する。尺度0は新尺度/floorで補わずbaseline-only。

原sourceとweightのpinを数量抽出前に照合する。CSV snapshotを予測起点別の読み取り範囲へ渡し、未来量getterを許さず、日付だけの未来calendarを使う。各起点の予測を保存してから別経路でlabelを付ける。前日締め観測が使える研究仮定であり、現実の公開遅延/訂正履歴を確認したものではない。

## 支持と採点

対象の変更はしない。入力不能・不能理由・profile支持・日次label maskを全450要求に残す。統計支持不足だけで候補の要求を消さず、既存encodingを使う。各positive店で両NN/基準の同対象入力支持20/25以上、完全14日label20/25以上を、比較を判断できる最低支持条件とする。未達なら支持不足で保存し、別店/別日を試さない。

主指標は前回どおり、店舗ごとに観測日次のMSE/u²と、完全14日labelの総量MSE/(14u)²を.5ずつ加えたjointを、固定15店の等重みで平均する。baseline、入力なし、入力ありを同じ支持/label対象で比較する。日次と総量の件数を個別保存し、欠測を平均や0で補わない。

補助はmacro日次/総量MSE、店別joint/RMSE/MAE/WAPE/Bias、起点/四半期別の差、尺度0の原単位誤差・正値/欠測件数。数量0は分母0ならWAPE nullとする。補助指標が良い部分だけを主結果へ置き換えない。店舗/起点は共有季節・連続履歴があり、450独立試験と数えない。今回bootstrap/統計有意差/信頼区間推定を追加しない。

## 判定と止め方

進捗条件は入力ありが両対照よりmacro jointで小さく、かつ固定15店中10店以上で両対照より小さいこと。これは**方向の再確認条件**で、実務的な最小改善幅やPSI費用削減を保証する基準ではない。絶対差と相対差を併記し、小幅なら小幅と報告する。

条件未達/支持不足なら保存してdirect PAUSED、同統計のseed/step/半減期/幅/店/期間探索、2017追試、他の予約群への切替えは行わない。条件達成時も採択しない。実務上の利益に見合う差か、比較のばらつきをどう測るかを結果と別の次判断とする。2016を見た後はこのstore/yearも既読と記録する。

実行/入力/保存のエラーでは原exception・部分予測・source/weight/原ID/入力pinを保全し、盲目的再試行しない。Sol容量又は人の停止でも保存後PAUSED。正常終了・能力条件達成・正式採択を区別する。

## 保存上限と承認範囲

原ZIP/member pinは旧記録を使い、次抽出時にarchive identity/hashとmember stream bytes/hash/行数を照合する。対象以外のquantity/onpromotion、2017、test.csvは解釈しない。原archive/閉鎖rootへ追記0。新quantity/profile/予測は新local root、source・契約・raw stdio・失敗は新EvidenceStoreへ保存する。

実行900秒/2GiB/output1GiB/single32MiB/files32（normal24file768MiB/failure8file256MiB）、記録16MiB512file/256KiBpart/failure reserve2MiB16file、prep128KiB16fileを維持。新snapshotは18×406暦行以内で既存記録の通常14MiB枠に収まる見込みだが、実bytes/件数を新書込み前に確認し、足りなければ新rootで分ける。上限緩和や失敗枠の通常使用はしない。

Gitは本契約・集約報告・独自sourceだけ。原quantity/profile/尺度/ledger/予測/weights送信0、metadataのhashは内容の代わりに保存する。direct ACTIVE/automation PAUSED、追加agent0/CARE手動待ち。formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。

契約のmetadata保存はrepresentative-demand-stat-validation-contract-records、Git後は同-contract-git-records/post-save優先。foreground rgのWindows literal glob失敗と誤った旧設計filename読取りはselected metadataを保全し、helper/model実行の失敗にしない。
