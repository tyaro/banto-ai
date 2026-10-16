# 自走で進める平均予測の有限比較

2026-10-15 JST。人の「自走して進めてください」により、従来の一件ごとの再開確認を今回の有限campaign内では求めず、実装・内部選択・既読2015開発評価・検証・引継ぎまで進める。既存店舗の将来販売数量の平均をtargetとし、PSI損失/分位点/中央値へ変更しない。automationは再開しない。

## 仮説と固定候補

300学習窓に30369parameterの模型だけでは容量に対する対照が不足する。原因を断定せず、同じas-of入力の72係数の共有線形残差回帰を小容量対照として追加する。候補はこれと固定Transformerの補正抑制の二つだけ、mean28を選択の対照/候補に含める。

- Ridge: intercept1＋過去残差統計8＋context統計2＋既存future暦60＋lead1 =72列。日次残差(Y−B)/uを予測。fit300だけで各非intercept列のmean/population stdを固定し、std<=1e-12列は0にする。interceptは1、他列をlambda0.01で正則化、interceptは罰則なし。fit平均日次MSEと平均14日総量MSEの半々にridge罰則を加えたfloat64正規方程式を一回solve。係数探索/seed探索なし。
- Transformer: Mac閉鎖root time_selected3328/SHA166171df43537141ea6174b0180f21e5044ddc54d4ea35c4ea7af5018d05aaf6を変更せず、time validation120へ一回推論する。新Transformer学習なし。元の軌跡終了にはC移行validationが関与していたことを保持。
- 両者のraw出力は非負にclip。候補P=B+alpha(Praw−B)、alphaは2014 time validation120だけで選ぶ。daily d=(Praw−B)/u,r=(Y−B)/u、totalは各14日平均。joint最小alpha=clip(Cjoint/Ejoint,0,upper)、Cはdr平均、Eはd²平均、upper=min(1,2Cd/Ed,2Ct/Et)。各C<=0ならupper0、E=0の項は制約なし。これで同支持の内部daily/total MSE悪化を抑える。alpha0はbaseline。MAEを目的関数へしない。
- 内部joint最小をbaseline/ridge_calibrated/nn_calibratedから選択。1e-12以内のtieはbaseline→ridge→nn。生NNは参考表示だけ。選択規則・λ・features・尺度を2015結果で変更しない。

## データと順序

元 `artifacts/macos-demand-rebuild-20261015` の閉鎖snapshotからfit既存10店6/7/10/13/15/17/19/23/26/27の2013–2014だけをmetadata選択後に数値化。保存split300 fit/120 timeを固定、Cの数量/profileを追加利用しない。各uは原前期2013Jan〜2014Jun、暦有効42flag。各origin前56日だけの新入力/profile、label14日。
両候補のfit/内部推論/校正/選択を終え、state/alpha/全source pinと選択を保存してから `artifacts/macos-demand-existing-stores-2015-20261015` の既読snapshot/予測前後を使用する。
既存10店2015Jan13+14*kの250要求を保持、新profileと候補予測をlabelなし保存後に実績を付与。NN候補の2015 raw値は保存済みtime_selected予測をそのまま再利用、同state hashと同baselineを照合。Ridgeは固定stateで一回適用。元time_selected予測を参考として併記、2015で候補を選び直さない。

主指標は元どおり10店等重みの日次MSE/u²と完全14日総量MSE/(14u)²の半々。全店舗/全四半期/MAE/WAPE/bias/支持を保存。250予測/3490日/240完全総量を要求、Christmas nullを保持。暫定2%改善・日次/総量悪化なし・支持不変を事前どおり報告、MAE/WAPEは別併記。PSI採用はfalse。
2015は既読で、今回の仮説はその診断を受けたため完全な未知評価とは呼ばない。新しい年度や正式holdoutを消費しない。根拠が弱い場合も別λ/gridを足さず負の結果を保存する。

## 実行と保存

fresh root `artifacts/macos-demand-autonomous-mean-20261015` と同`-execution-records`、読戻し/文書は別fresh記録。模型通常24files768MiB/全32files1GiB/single32MiB、失敗8files256MiBを保持。EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。親全体900秒/子870秒、Mac sampled footprint/peakRSS各2GiB。全stdio/exit/source/state/失敗prefix/閉鎖root前後一致を保存する。失敗rootを修復・上書きせず、無目的な再試行をしない。

この有限campaignの完了で区切り、追加の探索/年度延長を自動で始めない。2016/2017/予約31–54/販促数量/正式holdout/Windows native/CAREへ進まない。formal_permission=false、製品採用0、追加agent0。既存変更とclosed roots保持、原data/profile/予測/weightsのGit送信0。Mac指標はWindows private bytesと同義ではない。
