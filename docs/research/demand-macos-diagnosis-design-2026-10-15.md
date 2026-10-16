# Mac保存予測の補正誤差分解 — 実行前契約

2026-10-15 JST。人の「次のステップ」による一件の記述的診断。入力は閉鎖済み `artifacts/macos-demand-rebuild-20261015` の予測前後、前期尺度、summaryだけ。closure照合には全fileのhashを読み、weightsのdeserialize・forward・fit・原本ZIP再抽出・profile再生成は行わない。

固定6店4/8/16/20/24/28、2015-01-13+14*k（k=0..24）の150要求を保持。positive5店を等重み、店20の25fallbackは正規化外として別記。Christmas欠測は観測日だけ日次、完全14日のみ総量に使う。

time_selectedとtransfer_selectedをそれぞれbaselineに、transfer_selectedをtime_selectedに比較。既存pure分解器のfeature_off/on欄へ順に写すが、これは同一軌跡の選択点比較でありfeature有無の比較ではない。
日次d=(P-B)/u、r=(Y-B)/u、総量は14u。補正二乗量d²、整合2dr、MSE差d²−2drを全体・全5店・origin四半期1〜4で保存。既存summaryの各差と全90値を1e-10以内で照合。

結果を見て倍率・store・quarter・scale・label支持を選び直さない。性能悪化の算術的内訳を示し、原因・未知性能・有意性・PSI適合の証明としない。次の学習は主用途と追加したい能力を固定してから別unitとする。

記録はfresh `artifacts/macos-demand-diagnosis-20261015-records`。EvidenceStore16MiB/512file、part256KiB、失敗reserve2MiB/16file。親900秒/子checkpoint870秒、Mac sampled footprintとpeakRSS各2GiB。契約/source/新fixture/全childstdio/exit/結果/元root不変を保存しclosure照合する。失敗を上書きせず、そのunitを停止する。

一件保存後研究停止、automation PAUSED、formal_permission=false、製品採用0、追加agent0。2016/2017、予約31–54、販促数量、正式holdout、Windows native、CAREへ進まない。既存変更と閉鎖rootを保持。原data/profile/予測/weightsをGit送信しない。
