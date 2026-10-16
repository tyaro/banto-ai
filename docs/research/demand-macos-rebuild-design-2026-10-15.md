# Macで原本から需要研究を新規生成する固定契約

2026-10-15 JST。人の「Windowsからコピーせず、Macで入力・profile・学習済みモデルまで新しく作り直したい」を受けた新unit。
旧Windowsの実行履歴や失敗証拠の復元ではない。元研究は保持し、新しい原本参照・入力・profile・weights・予測・実行記録をMacのfresh rootへ作る。

## 固定する条件

- Git基準 `6690531fd6ef081e3605c3801e610e466e1be0ea`。CPython3.14.8 / Torch2.14.0 Mac arm64 / CPUfloat32 / 2threads / interop1 / deterministic。
- 入力は取得済みStore Sales ZIP22,416,355B、SHA256 `12e9c1dc4833cc804b3ff1515bd7b688f45fd8216fb2b340525036b006d625be`。ZIPからstream読取りし、大きいCSVを展開しない。
- family BREAD/BAKERY。A=6,10,15,19,26、B=7,13,17,23,27がfit。C=9,14,18,25,30が内部移行validation。外部開発は4,8,16,20,24,28。
- 2013-02-26+14*k（k=0..47）の48候補/店。過去56日とlabel14日を完全観測として適格42/店を新生成。実0は保持し、欠測はnull。各30前期/12後期、crossing0を要求し、満たさなければ停止。
- uは各店の2013-01-01〜2014-06-30だけの観測平均。A/B/Cは正、外部5店は正、店20は0を要求。calendar支持はfit300のlabel観測maskだけから生成し、後の評価でchannelを追加しない。
- 最新StatisticalFeatureMean30369parameter、56日→14日、60暦channel、context2＋過去統計8入力。各profileはorigin前56日だけをgetし、EMA/σ/meanは既存pure処理で新生成。
- 一候補・一軌跡。seed20261014、sampler4096×8、AdamW lr3e-4/betas(.9,.999)/eps1e-8/weight_decay.01/gradnorm1、foreach/fused=False。
- 0と128stepごとにfit300/time120/transfer60を固定全件計測。Cのjointだけで512猶予・相対0.01%改善なし6回停止、最大4096。時間/移行の最小stateをそれぞれclone。0stepも選択候補。

## 新生成の順序と評価

原本ZIPのpin確認→前期/2013–14だけ数値解釈→snapshot・尺度・支持・profile・sampler保存→一軌跡学習→二選択state固定→外部6店の2014-11-18〜2015-12-28だけ新数値解釈→各origin前56日入力/profile→全予測のlabelなし保存→別経路でlabel付与・評価。
最初のstreamはA/B/Cの2013–14と外部6店の前期尺度期間だけ、後段streamは外部6店の指定context/2015だけを数値化する。
2015-01-13+14*k（k=0..24）、150要求、NN125とzero-scale25を保持。Christmas欠測で最後の総量labelはnullのまま。各positive店25入力/24完全labelを要求する。

主指標はpositive5を等重みとした日次MSE/u²と完全14日総量MSE/(14u)²の.5平均。移行選択模型のmean28比2%以上改善、日次/総量悪化なし、支持不変を暫定開発条件とする。製品採用や未知性能を認定しない。店別/四半期を併記し、結果を見て母数・LR・seed・閾値を変更しない。
これは既知データのMac新規開発実行であり、Windowsのbinary state・旧snapshot hash・指標の完全一致を約束しない。公式TimesFM weightsや教師出力は使用しない。

## 保存と停止

模型root `artifacts/macos-demand-rebuild-20261015`、実行記録 `artifacts/macos-demand-rebuild-20261015-execution-records`。既存なら開始しない。
模型の通常24file/768MiB、全32file/1GiB、single32MiB。失敗8file/256MiBを保持。記録は既存EvidenceStore16MiB/512file/part256KiB/reserve2MiB16file。source・契約・全childstdio/exit・例外・prefix・closureを保全する。
Macのsampled physical footprintとpeak RSSそれぞれ2GiB、child checkpoint870秒/親timeout900秒。Windows private bytesとの同等性やOS hard memory capとはしない。
一回の新生成と固定開発の保存で停止。失敗時に原rootを修復/上書き/盲目的再試行しない。新仮説/延長/grid/2016/2017/予約31–54/正式holdout/CAREへ進まない。automationは停止を維持。formal_permission=false、製品採用0、追加agent0。原data/profile/ledger/予測/weightsはGitへ送信しない。
