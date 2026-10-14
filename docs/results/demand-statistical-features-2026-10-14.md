# σ・EMAを模型の追加入力にする新接続（2026-10-14）

## 人の修正と判断

人の「そのまま使うより前処理/一緒に入力する情報として使えないか」に従い、[学習入力の設計](../research/demand-statistical-feature-input-design-2026-10-14.md)へ修正。旧等重み/固定EMA補正の悪化は、この学習入力の仮説を否定していない。固定point補正を再試行せず、統計の寄与を学ぶ新branchを実装した。

前処理は既存q/u・量mask/weekday残差を維持し、normalize変更を同時に行わない。追加統計は元56日の量から計算する要約であり、新しい外部観測ではない。raw contextのstdと、曜日基準一歩先誤差のσは対象が違う。

## 8次元の情報

|入力|意味|
|---|---|
|mean_error/u|最近の偏り|
|EMA7/u・EMA28/u|短期/長期の偏りの推移|
|sample_sigma/u|曜日基準から外れる散らばり|
|support/28・staleness/28|どれだけ観測でき、どれだけ古いか|
|statistics_available・staleness_known|統計0と未取得を区別するmask|

短長差は2つのEMAから復元できるため追加の独立次元にしない。profileのorigin/past_end/last_error_dateを数値より先に確認。未来profile拒否、σ0/欠測を区別、尺度0は任意floorで補わずbranch不能。未支持の4統計は0とvalid=false、原null/理由をmetadataに残す。point/区間をこのencoderだけで変更しない。

## 学習接続

新StatisticalFeatureMeanは8→32の独立projectionをencoder summaryへ加える。新288parameter、合計30,369。weight/bias0初期化で、入力の有無による初期mean差を作らずbaselineへ一致。通常の日次headが情報の寄与を学習する。

EMAを必ず加算する、σで予測を必ず上げる等の制約なし。新接続fixtureで同じσ入力の寄与を正/負にできること、feature/新projectionへ有限な勾配が届くことを確認した。必要なら統計を無視できる表現であり、実際の学習で無視/利用されるかはまだ確認していない。

## 新6確認

|新確認|結果|
|---|---|
|単位対応・統計実0対欠測mask|passed|
|未来profile headerを数値payloadより先に拒否|passed|
|曜日patternのraw変動と残差σを区別|passed|
|古さ/mask・尺度0・矛盾support拒否|passed|
|新branch0初期化・30,369parameters・日次総量整合|passed|
|feature勾配・σ寄与の正/負の両方向|passed|

架空量/profileでの経路確認一回のみ。旧σ/EMA確認6、旧NN/暦確認、旧fit/forward/採点/CIは反復0。新public量/学習/精度比較も0。元σoverlay/base模型/source/result bytes不変。

## 次

比較は追加入力branchを全0にした同shape control対、有効8次元入力の候補。新initial/sampler/256step、baseline/scale/loss/暦を同じにし、normalize・σloss重み・期間長は替えない。fit630key/uは元条件、2015profileは保存ledger再利用。旧weights/原forward再実行0。新訓練は別unitで、主joint MSE/10of15条件を出力前に固定済み。

局所平均/stdの正規化/逆変換の研究例は[RevIN著者project](https://github.com/ts-kim/RevIN)を参照。OpenReview本体/PDFはbrowser verificationに阻まれfull paperは未読、author project/著者教科書の参照はmetadata保存のみ。codeのコピーなし、このモデルでの精度保証でもない。

計算/checkのparent経過8.935349秒、子2件の全stdio/exit0を判定前保存。whole model容量の認定ではない。本文representative-demand-statistical-features-records、Git後同-features-git-records post-save優先。新helper失敗0、原failed/閉鎖root不変。

direct ACTIVE（人の修正した入力研究）/automation PAUSED、追加agent0/CARE待ち。全上限維持/formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。Git独自code/架空確認/集約docsのみ、原quantity/profile/尺度/ledger/予測/weights送信0。
