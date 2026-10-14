# 内部選択済み模型の未学習店舗への評価（2026-10-14）

人の「進んでください」を受け、[学習量診断](../results/demand-training-adequacy-2026-10-14.md)で内部検証から選んだbest二件を固定し、選択に使わなかった店舗へ一回適用する。追加学習/旧weights延長/epoch再選択は0。本契約を新評価量の数値解釈前に保存する。

## 選択と評価を分ける

学習は元positive15の2013〜2014-06-30、終了選択は同15店の2014後半。両bestは1664stepだったが、その数字で再学習せず、保存したbest weightを直接使う。

対象は元metadata選定の検証6店：4/8/16/20/24/28。今回のニューラル模型のfit・内部検証・終了選択には使っていない。各店の2013–15数量を過去の支持診断で読み、2016は別の共有残差研究で使ったので、情報を全く見ない系列・盲検dataset・別チェーンの独立holdoutとは呼ばない。「この二模型の学習/選択に未使用の店舗への、既存publicデータでの固定転移評価」とする。

店舗31–54の予約、2017、登録済み正式holdoutには進まない。旧2015/2016の完成模型forwardも反復しない。新評価はこの新best二件×新対象入力だけ。

## 固定状態・入力

|weight|bytes|SHA256|
|---|---:|---|
|feature_off-best.pt|128984|192fabdea7f1cfac46d59cba9dfa4e1dce3f7269123c5b89d664639e6dfeb0e8|
|feature_on-best.pt|128984|d57c7c606c627619f2ea1c0e019478437a43050e9a61aaf8587e8b987599adc8|

source/old model root closure/上記weightsの実pinを評価量の数値解釈前に確認する。30369params/単系列56日→14日、eval/no_grad/CPUfloat32/2threads/interop1/deterministicを固定。ID embeddingや固定店舗位置headを持たない共有模型なので、各店の自己履歴を同じ関数へ渡す。

評価店舗の尺度uは、その店の2013-01-01〜2014-06-30の観測平均。模型に合わせた予測前の履歴統計であり、模型係数のfitには使わない。2015/2016labelや将来観測maskで尺度を選ばない。zero-scaleは他店尺度/floor/後期再尺度へ切り替えずbaseline-only。保存された過去ゼロ期間から店20のu=0が想定されるが、実際の前期データで確認して理由を保存する。

対象6店は全て要求に残す。positive-uの店4/8/16/24/28の5店をNN主比較、店20はbaseline-onlyの診断とする。前期尺度がこの宣言と一致しなければ入力条件不成立として保存・停止、店を交換しない。

数量q/u・実0/欠測mask・context2統計・名目60暦/学習側の42有効channel・baseline・8統計encodingを維持。元日/Christmasのfit支持なしを評価量で解除しない。future営業/販促計画や休暇長を補わない。

## 固定期間と可用性

2015-01-13＋14*k、k=0..24の25起点/店、horizon14。最後は2015-12-15起点/label終端2015-12-28。6店150要求、NN対象125/zero-scale baseline25。必要なcontext最初2014-11-18。過去の誤差を見て店/日付を入替えない。

閉鎖prefixの24店2013–15 snapshotをpin再利用し、尺度は前期、評価入力/実績は対象6店・必要日だけを数値化する。新archive/2016/2017数量読取り0。新profileはこの6店の各新origin前56日から一回生成する。各過去残差のbaselineもその過去t前28日だけ、σ/EMAは固定のまま。入力getterはorigin前56日に制限し、全予測をlabelなしfileへ保存してから別経路で実績を付ける。

欠測はnull/観測mask、実0は観測数量として残す。各positive店で共通NN/基準入力20/25以上、完全14日label20/25以上を最低支持とする。Christmasを含む最後の窓も要求に残し、13日和を14日総量にしない。支持不足なら群/日付の置換なしで停止。

## 二つの問いと判定

主問は、内部選択を経た学習模型が未学習店舗でmean28基準より有用か。副問は、統計8入力が同shape controlに追加する差があるか。旧2016の統計追加9/15未達の主条件を遡及変更せず、この新評価では問いを出力前に分ける。

主指標は各店の観測日次MSE/u²と完全14日総量MSE/(14u)²を.5ずつ足し、固定positive5を等重み平均する。同じ共通対象で三方式を比較する。

- 模型の転移：各NNについて、macro jointがmean28より小、かつ5店中4店以上でmean28より小なら、そのNNに方向の進捗根拠あり。
- 統計追加入力：入力ありのmacro jointがmean28/control両方より小、かつ5店中4店以上で両方より小なら追加差の方向根拠あり。
- いずれも実務の最小改善幅/PSI費用削減・有意差・採択の基準ではない。絶対差/相対差を併記する。副問未達を主問の失敗へ混ぜない。

補助はmacro日次/総量、店別joint/RMSE/MAE/WAPE/Bias、origin/四半期別の差、zero-scaleの原単位誤差/正値/欠測件数。分母0のWAPEはnull。150窓を独立な試験と数えず、bootstrap/区間校正/複数seedを追加しない。

## 区切りと保存

一回の固定評価を保存してdirect PAUSEDで区切り、結果から次の問いを人と判断する。失敗/支持不足なら原exception・入力/予測prefixを保全、盲目的再試行なし。達成時も追加学習・対象入替え・別checkpoint/seed/半減期/LR gridや2017/予約群へ自動進行0。

実行900秒/2GiB/output1GiB/single32MiB/files32（normal24file768MiB/failure8file256MiB）、記録16MiB512file/256KiBpart/failure2MiB16file、prep128KiB16file維持。source/契約/weight pin、対象前期u/入力snapshot/新profile/label前予測/label対応/指標/失敗を新local rootへ保存し、閉鎖rootへ追記しない。

人の再開でdirect ACTIVE/automation PAUSED維持、追加agent0/CARE手動待ち。formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。Git独自code/集約docsのみ、原quantity/profile/尺度/ledger/予測/weights送信0。
