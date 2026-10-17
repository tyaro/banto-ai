# σ・EMAを追加入力にした同条件学習比較（2026-10-14）

## 判断

人の「前処理/一緒に入力する情報として」の問いを[出力前の固定設計](../research/demand-statistical-feature-input-design-2026-10-14.md)に従い実行した。統計入力ありはなしより主指標が **0.014124%改善**、正尺度15店中 **12店**で同shape controlと保存mean28の両方より小さかった。事前の進捗条件を満たした。

**差は小さく、採用・有意差・未知期間での優位を示したものではない。** 固定EMAをpointへ足した前案の悪化と、今回の学習入力は別の仮説の結果として保持する。σ単独の寄与や予測区間の校正は測っていない。

## 同条件の二件

|項目|両側に共通の条件|
|---|---|
|学習|2013–14、原630窓・正尺度15店・原fit尺度u|
|模型|30,369parameters、D32/L1/4head、単系列56日→14日|
|元入力|数量q/u・実0/欠測mask・context mean/uとCV・名目暦60・前後42有効channel|
|相違点|controlは統計8次元を全0、候補は有効8次元|
|初期/順序|新同一initial state、同一256×8 sampler、seed20261014|
|最適化|CPUfloat32、2threads/interop1、deterministic、AdamW lr3e-4/wd.01、gradnorm1|
|目的/終了|日次と14日総量の尺度化MSEを.5ずつ、日次非負/総量和、最終256step固定|

8次元は過去残差mean/u・EMA7/u・EMA28/u・sample σ/u・support/28・staleness/28・valid・age-known。元56日の数量の要約で、新しい外部観測ではない。両側の8→32projectionはweight/bias0初期化、入力なしでもbiasは学習する同shape control。parameter数差はない。

EMAの固定加算、σ方向制約、局所z-score変更、σloss重み、期間長変更は0。候補のprojection weight normは0.111434817、controlは0。接続が学習された記述であり、σだけの有効性の証拠ではない。

## 主指標

店舗ごとに観測日次のMSE/u²、完全14日labelの総量MSE/(14u)²を計算し、.5ずつ足して15店を同じ重みで平均した。前回の休日周辺主指標と取り替えて過去結果を合格にしない。

|方式|macro joint MSE|macro日次MSE|macro総量MSE|
|---|---:|---:|---:|
|保存mean28|0.071036585129|0.118398085511|0.023675084746|
|統計入力なし|0.070825974123|0.118189158993|0.023462789253|
|統計入力あり|0.070815970862|0.118179390550|0.023452551174|

候補はmean28比0.310564%、同shape control比0.014124%改善。主指標のcontrolとの差は1.00032609586e-05。事前条件はjointが両対照より小、かつ15店中10店以上で両対照より小であり、今回12店。日次/総量も小幅改善、集計後の条件変更なし。

|店|保存mean28 joint|入力なし joint|入力あり joint|店舗条件|
|---|---:|---:|---:|---|
|6|0.026488617|0.026427222|0.026426347|両対照より小|
|7|0.032150523|0.032134010|0.032137615|条件未達|
|9|0.016342659|0.016319844|0.016318907|両対照より小|
|10|0.040935005|0.040892844|0.040889276|両対照より小|
|13|0.475920659|0.474812692|0.474762965|両対照より小|
|14|0.039612628|0.039494256|0.039488412|両対照より小|
|15|0.028234213|0.028189517|0.028186481|両対照より小|
|17|0.036336740|0.036267273|0.036267999|条件未達|
|18|0.012067024|0.012080288|0.012076273|条件未達|
|19|0.035819238|0.035689580|0.035687943|両対照より小|
|23|0.016700260|0.016660094|0.016658983|両対照より小|
|25|0.213403548|0.212124240|0.212050843|両対照より小|
|26|0.035770697|0.035675453|0.035666446|両対照より小|
|27|0.025779867|0.025689130|0.025688062|両対照より小|
|30|0.029987098|0.029933169|0.029933010|両対照より小|

店7/17は候補がcontrolより悪化、店18はcontrolより改善したがmean28より悪い。平均だけで全店改善へ補わない。

## 保存と対応

原fit selection/630key/u/42channelはpin再利用。fit profile630は2013–14の各origin前56日から新規計算し学習前保存。両側の最終weights保存後だけ2015の選択数量と既保存profile450を読み、新2015profile再集計0。profile origin/past_end/last_error_dateはencoderが数値payloadより先に検証する。

18店×25起点450要求、NN375、尺度0の店21/22/29はbaseline-only75。完全14日label432、18窓の欠測は欠測のまま。旧point/actualと一致を確認し、baseline指標は保存summaryからコピー。旧baseline再採点/旧weights/NN forward/旧確認/CI反復0。

source11実bytes、fit/dev選択・尺度・key・sampler・initial/final weights・step64/128/192 prefixと全256step journal・fit profile・開発feature・予測・指標をlocal保存。模型root23files/4796038bytes、immutable closure。parent code HEAD633e273、今回runner未commit時のraw pinをconfig/sourcesに保存。宣言source pinsはfull loaded/native runtime閉包の認定ではない。

実行11.624473秒、OS peak private 1160040448bytes。実行900秒/2GiB/output1GiB/single32MiB/files32、normal24file/768MiB・failure reserve8file/256MiB維持。child全stdout/stderr/exit0は別EvidenceStoreへ判定前保存、正常出力の環境警告も保持。記録16MiB/512file/256KiBpart/failure reserve2MiB16file、prep128KiB16fileを維持。

foregroundで旧prepのrun.py名を2件誤って参照したGet-Contentエラーはselected metadataを保存。文書script書込みの初回functions.execはTextEncoder未定義でisolate内拒否、nested tool/process/mutation0。別書込みで安全な文字数上界確認へ修正。いずれも模型/helper実行の失敗やprocess全stdioではない。学習/保存helper失敗0、原failed/閉鎖root不変。

本文はrepresentative-demand-stat-feature-pair模型rootと同-launch-records、文書照合は同-doc-records、Git後は同-git-records/post-save優先。Gitは独自runnerと集約文書のみ、原quantity/profile/尺度/ledger/予測/weights送信0。

## 次に必要なこと

2015は過去の検討ですでに見た回顧開発期間、単一initialの小幅差である。この二件を固定し、同条件seed/半減期/幅/step探索で差を膨らませない。次のunitは独立な期間又は未使用系列での検証契約を作る。別研究で使った2016範囲を未見へ補わず、既読期間・予約群・正式holdoutを区別し、対象/指標/停止条件を出力前に固定する。未知検証はまだ実行していない。

名目暦で実休業表を補わず、元日/Christmasのfit支持不足は保持する。将来販促の版履歴・休暇長・メーカー出荷/潜在需要/PSI実用性・σのh別/総量区間校正も未確認。8統計の一括比較から特定σ/EMAだけの効果を主張しない。

direct ACTIVE/automation PAUSED、追加agent0/CARE手動待ち。formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。進捗条件達成は正式採択でも容量認定でもない。
