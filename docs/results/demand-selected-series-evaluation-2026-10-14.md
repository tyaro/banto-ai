# 内部選択済み模型の未学習店舗への固定評価（2026-10-14）

## 判断

[評価量読取り前に固定した契約](../research/demand-selected-series-evaluation-design-2026-10-14.md)に従い、内部検証で選んだbest二件を未学習店舗へ一回適用した。主指標はmean28より入力なし **27.135004%悪化**、入力あり **23.849310%悪化**。各模型がmean28より小さいのは **1/5店**で、事前の4/5条件未達。模型の転移進捗条件を満たさず、採択しない。

一方、入力ありは同shapeの入力なしより **2.584414%改善**し、5店すべてで入力なしより小さかった。このcontrol限定の差は保存する。ただし副問の固定条件はmean28/controlの両方より小＋4/5店であり、今回1/5店のため未達。「統計入力がNNを改善した」と「そのNNが単純基準を置き換えられる」を分ける。

支持・実行は成立し、処理exit0と性能条件未達を別に保持する。事前契約どおり結果を保存してdirect PAUSEDで区切り、追加学習/対象入替え/別checkpoint/seed/期間探索を行わない。

## 学習・選択から離した評価

使用weightは[学習量診断](demand-training-adequacy-2026-10-14.md)のfeature_off-best.ptとfeature_on-best.pt、各1664stepで内部検証最良だった状態。学習は元positive15の2013〜2014June、終了選択は同15店の2014後半。新学習・終了点再選択0。source/weight pinsは前後一致した。

新対象はmetadata選定の検証6店4/8/16/20/24/28。これらの店は今回のニューラル模型fit/内部検証/終了選択に使っていないが、過去に2013–15数量支持と別方式2016を研究した既読系列である。完全盲検dataset/別チェーン/正式holdoutの証明ではなく、模型の学習/選択に未使用の店舗への固定転移評価とする。

store ID embedding/固定店舗位置headを持たない単系列共有模型に、各店の自己56日の履歴だけを渡した。30369parameter、CPUfloat32/2threads/interop1/deterministic、eval/no_grad。各店舗の尺度は予測前の2013Jan1〜2014Jun30の観測平均。評価量/観測maskで尺度を選ばず、模型係数をfitし直していない。

この前期で店4/8/16/24/28はu>0、店20はu=0と事前宣言どおり確認した。positive5をNN主比較、店20はbaseline-onlyとして全要求に保持。u floor/他店尺度/後期再尺度へ切替え0。元数量q/u・mask・context2統計・名目60暦の42有効channel・baseline・8統計encodingは維持し、元日/Christmas支持不足channelを評価で解除しなかった。

## 入力・予測・labelの対応

原prefix snapshot 776915B/SHAb7805b258cb6e7a268b3b3289ac1b9688bd54cf03e1f06b01f8e74172fdeddc4をpin再利用。対象6店の前期尺度を保存した後に、必要な2014-11-18〜2015-12-28の入力/labelを数値化した。他店、新archive/2016/2017/予約群/正式holdout数量は数値解釈0。

2015Jan13＋14*k/k0..24、25起点×6店=150要求。新profile150を各origin前56日から一回作り、入力getterの範囲/アクセス日付とprofile headerを保持。σ/EMAはpast-onlyで、未来calendarは日付だけ。全予測をlabelなしfileへ保存してから、別経路で実績を付けた。snapshotには対象範囲の数値があるが、模型/統計から未来quantity getterへのアクセスは拒否される。

NN支持125、店20のbaseline-only25、完全14日label144。positive5全店で共通入力25/25・完全label24/25、事前の各20/25最低支持を満たした。Christmas欠測6窓を要求に残し、日次の観測labelだけ採点、完全総量はnullのまま。13日和や欠測0への変換0。

## 主指標と店別

店別の観測日次MSE/u²と完全14日総量MSE/(14u)²を.5ずつ足し、positive5を等重み平均した。同じ共通対象の三方式で比較、小さいほどよい。

|方式|macro joint MSE|macro日次MSE|macro総量MSE|
|---|---:|---:|---:|
|mean28|0.030097998779|0.048888499952|0.011307497606|
|入力なし|0.038265091961|0.057212376233|0.019317807689|
|入力あり|0.037276163673|0.056207131403|0.018345195942|

|店|mean28 joint|入力なし joint|入力あり joint|
|---|---:|---:|---:|
|4|0.039886770|0.039577877|0.038702533|
|8|0.023595837|0.032864492|0.031474108|
|16|0.027059779|0.035361074|0.035253679|
|24|0.026842733|0.045939692|0.043816497|
|28|0.033104875|0.037582324|0.037134001|

どちらのNNも店4だけがmean28より小さい。入力ありのcontrol比改善は全5店に見られるが、店8/16/24/28ではmean28に及ばない。店24の悪化も除外せず、店舗構成を入替えて成功へ補わない。

|起点四半期|mean28 joint|入力なし joint|入力あり joint|
|---|---:|---:|---:|
|1|0.040346236|0.042831692|0.043072448|
|2|0.024916705|0.041959370|0.039375317|
|3|0.029321545|0.035321729|0.034759922|
|4|0.026318399|0.031630222|0.030865642|

全四半期でNNはmean28より悪い。統計入力のcontrol比は第1四半期で悪化、残りで改善した。四半期はorigin所属で固定し、targetの境界越えを都合よく分割していない。全年度主指標とは件数/対象が異なり、四半期macroの単純平均ではない。

原単位RMSE/MAE/WAPE/Bias、全25起点の差、不能/欠測理由はlocal summaryへ保存。店20のtargetは観測正値318/実0 31/欠測1で、baseline-onlyの原単位誤差を保存し、u=0の尺度化主指標には含めない。原因を休業/開店/欠品へ同定しない。150窓を独立試験と数えず、bootstrap/有意差/予測区間校正を追加していない。

## 結果の解釈と次の問い

学習量診断で256以降の内部検証改善は確認できたが、内部選択した模型が未学習店舗で単純基準を上回ることは今回確認できなかった。学習終了点の選択と、選択に使わない対象での性能確認が別に必要だったことが分かる。

内部検証への適合、店舗間の分布差、前期尺度と後期水準の差、補正の過大/過小等は候補原因であり、今回の総指標だけで一つを原因と断定しない。学習をさらに回す、bad storeを外す、新しいuを評価量から作る手直しを自動でしない。追加統計全般/共有NN全般/TimesFM再現の不可能性とも結論しない。

再開する場合の次の小unitは、保存した予測と実績対応だけで、baselineからの補正がどの店/起点/水準で誤差を増やしたかを分解する診断が適切。新fit/forward/抽出を反復せず、原因候補の支持を調べてから新模型/入力の問いを決める。事後診断と未見確認は区別する。

## 保存・状態

実行41.480635秒、OS peak private 1059745792bytes。模型root10files/1238026bytes、immutable closure。source17実bytes/契約/前期尺度/原入力binding・原ID/mask付き選択snapshot・新profile/label前予測/label対応/主副問と補助指標を保存。child全stdout/stderr/exit0は別launch EvidenceStoreへ判定前保存、環境警告も保持した。

実行900秒/2GiB/output1GiB/single32MiB/files32（normal24file768MiB/failure8file256MiB）、記録16MiB512file/256KiBpart/failure reserve2MiB16file、prep128KiB16file維持。宣言sourceや実行成功をfull loaded/native runtime閉包・global容量認定/正式受入にしない。計算parent HEAD1da73d7＋未commit新source/契約のraw pinsを保存した。

本文representative-demand-selected-series模型rootと同-launch-records、文書照合は同-doc-records、Git後同-git-records/post-saveを優先。source/old best weights前後不変、新helper失敗0、旧checks/fit/evaluation/CI反復0/原閉鎖root追記0。

direct PAUSED、automation PAUSED不変、追加agent0/CARE手動待ち。formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。Git独自評価code/集約docsのみ、原quantity/profile/尺度/ledger/予測/weights送信0。
