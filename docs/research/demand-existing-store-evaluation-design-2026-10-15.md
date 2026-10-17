# 既存10店2015年の一回評価 — 実行契約

2026-10-15 JST。人の「その設計で、既存10店の2015年の評価を進めてください」に従い、[主用途と固定設計](demand-existing-store-purpose-2026-10-15.md)を実行する。

主問は既存店舗の将来販売数量の平均予測。fit10店6/7/10/13/15/17/19/23/26/27、BREAD/BAKERY、origin2015-01-13+14*k（k=0..24）、250要求を固定。raw解釈は同10店2014-11-18〜2015-12-28だけ。原本ZIP22,416,355B/SHA25612e9c1dc4833cc804b3ff1515bd7b688f45fd8216fb2b340525036b006d625beをstreamする。

原root `artifacts/macos-demand-rebuild-20261015` をcomplete closureで照合。主模型はtime_selected3328step、SHA256166171df43537141ea6174b0180f21e5044ddc54d4ea35c4ea7af5018d05aaf6。副比較はtransfer_selected3072step、SHA25658fbb3e1cf0684f630e17beb60ad8d546e234ebcba5cf3345a628ed00d275a95。両stateをCPU/float32/weights_only/strictで読み、原本の対象数量解釈前に主/副の役割とhashを保存する。

時間選択は元軌跡の候補点中でtime validationだけの最小。元軌跡そのものの終了はC店舗移行validationで決まっており、時間用途専用にearly stopした学習との比較ではない。今回その軌跡や選択を変更しない。

uは原rootの各店2013-01-01〜2014-06-30観測平均、全店positiveを要求。calendar56flagは原fit300で有効42のまま。contextと統計profileは各origin前56日だけ。全250行のbaseline・time・transfer予測をlabelなしに保存してから、別経路で14日実績と完全label maskを付与する。実0と欠測nullを区別する。

日次MSE/u²と完全14日総量MSE/(14u)²の半々jointを10店等重みで算出。全店・全4origin四半期、日次/総量MAE・WAPE・biasと各方法の支持を保存。欠測日は日次だけ除外し、部分和を14日総量にしない。未対応窓/店舗を削除して母集団を変更せず、支持不一致なら暫定条件は不合格。
主模型だけに元の開発目安「joint2%以上改善・日次/総量悪化なし・支持不変」を適用。副模型は参考、2015の結果で主模型を差し替えない。改善店数は記述のみ。既読公開benchmarkの開発評価であり、正式盲検holdout/PSI業務採用/有意性の証明ではない。

模型/評価rootはfresh `artifacts/macos-demand-existing-stores-2015-20261015`、実行記録は同`-execution-records`、読戻し/文書は別fresh roots。通常24files768MiB/全32files1GiB/single32MiB、失敗reserve8files256MiB。EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。親全体900秒/子checkpoint870秒、Mac sampled physical footprintとpeakRSS各2GiB。全source/契約pin、child全stdio/exit、失敗prefix、前後原root不変とclosureを保存する。

新学習・新seed・checkpoint選び直し・倍率最適化・gridなし。原closed rootへ追記/上書きなし、失敗を盲目的再実行しない。2016/2017、予約31–54、販促数量、正式holdout、Windows native、CAREを数値解釈/実行しない。一回保存後研究停止、automation PAUSED、formal_permission=false、製品採用0、追加agent0。既存Mac変更保持、原data/profile/予測/weightsをGit送信しない。
