# mean出力の最小実装と一回評価の固定条件（2026-10-14）

[期待数量とquantileを分ける設計](demand-mean-and-quantile-model-design-2026-10-14.md)を実行条件へ固定する。声掛けまでの直接自走承認を受領。既存automationはPAUSEDのまま、追加agentは使わない。

## 候補と確認

新namespaceのmean候補だけを作る。C56/P7/H14/V3/D64/L2、暦12/統計2を維持し、mean倍率head64→1を追加、名目120805parameters。mean用headはzero weight/inverse-softplus(1) bias、量の配分headはmeanへ接続、Q10/50/90は総量用の独立head。初期化は独立seed20261014、旧weightsは使わない。

meanをQ50に代入しない。daily_meanの和とtotal_meanを一致させ、meanをquantile範囲内へ強制しない。softplus/正配分の有限parameterで完全なゼロを表せない制約を保持し、実ゼロ・欠測・休業を混同しない。

新しい少数確認は、出力の分離と整合、meanとquantileの大小関係を強制しないこと、mean用二乗誤差/gradientの対象、ゼロcontextでの有限gradient。旧確認は再実行しない。

## 学習・選択

train/validation/test991/25/16origin、原保存256×8 batch日付列、元train尺度、同snapshotとsupportを使用。train2013–15/validation2016/test2017。スケール・対象・originを変えず、testは既知の回顧期間とする。

`Lmean=.5*日次の固定尺度MSE+.5*14日総量の固定尺度MSE`

`Ltrain=Lmean+.25*固定尺度総量pinball`

固定尺度は店舗別u（元train平均）、総量14*u。meanの同じ出力にMAEを追加しない。validationはLmeanだけを主指標にしてstep64/128/192/256を選択、同値は早いstep。選択保存後test16originを一回forward。

CPUfloat32/2threads/interop1/deterministic、256step/batch8、AdamW lr3e-4/betas(.9,.999)/eps1e-8/weight_decay.01/foreach=false/fused=false/gradnorm1。延長・別seed・loss重み探索・test bias補正なし。

## 保存結果との比較

mean候補の日次/総量RMSEとBiasを主に保存し、MAE/WAPEは補助。quantileのpinball/coverage/幅/interval scoreは別欄。旧入力候補Q50と単純基準は保存予測から新しくRMSEを集計するが、旧forward/学習/fitは行わない。Q50とmeanは統計対象が異なることを明記し、RMSEの勝者を一般モデル優位へしない。

店舗・origin・日付・実績の対応を照合する。全体/店舗別と元日/その他の内訳は保存予測から一度記述し、結果を使った再fitはしない。decision_quantityはnull/未確定。新候補採択・メーカーPSI・正式受入は今回の判定に含めない。

実行900秒2GiB/output1GiB/single32MiB/files32、通常24file/768MiB＋失敗reserve8file/256MiB、診断16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16filesを維持。source全文/設計/input/batch列/initial/4checkpoint/prefix/選択/meanとquantileの原予測/比較/journal/summary/closureを新rootへ保存し、元例外と完了prefixを保全する。閉鎖rootへ追加/同helper再試行なし。

新機構確認後に一候補のみ実評価する。結果後の次研究は、追加価値の具体的不足を見て決める。単純な連続学習を自走の目的にしない。正式gate不変/formal_permission=false/credit0/native reader禁止/登録holdout未読、独自codeと集約文書だけGit継続承認内で保存し、原数量/予測/fit/重みはlocalのみ。
