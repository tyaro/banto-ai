# 元日と全季節を含む2014数量検証

人の2026-10-15の直接委任に基づく有限比較。旧Q3校正/Q4選択では元日後の数量を検証できなかった。2014年全季節へ拡張し、四半期で数量水準の偏りが違う仮説を検証する。既読の探索的データであり、正式holdout/未知性能/製品採用を認定しない。

FIT10店(6,7,10,13,15,17,19,23,26,27)、2013–2015既存snapshotのみ。休業相当01-01/12-25、operating_status unknownを維持。2014内部のmaskは2013の全10店0又は欠測だけで支持を確認し、2014/2015から休業予定を捏造しない。欠測を学習target0へ置換しない。観測ゼロは保持する。2015の欠測0仮定は別評価としてのみ保存する。

2014発行日は01-01+14*k、k=0..25の26日、260窓、target01-01..12-30。元日前の12月は入力context、元日と後13日はtargetに含む。偶数kの130窓（元日を含む）を方式選択、奇数kの130窓を校正とする。両方とも全四半期を含む。2014年末時点の回顧的な交互窓分割であり、校正係数が各選択origin当時既知だったとは主張しない。隣接窓のcontextが重なるので独立標本とは扱わない。

初期packetは旧fit_keysから14target末日が2014-01-01より前のもののみ（全店均等・最低140）。内部モデル尺度は2013観測値だけの平均（真の0含む・欠測除外）で固定し、2014数量を正規化に先取りしない。元のuは2015の採点尺度としてのみ保持する。暦56列は予告可能な固定構造として全て入力するが、各fitの過去非休業rowだけで標準化/active列を決め、未支持列の係数寄与を0にする。72列、lambda0.01、open_mean28の曜日最低2件/理由付きfallback、mask付きjoint ridgeは既存実装。

各2014originは過去365日・14label完了・実観測全14・全10店均等・最低140packetからrecent gated ridgeをfit。予測保存後に現packetを追加し、未完了/欠測packetは以後のfitから除外する。日次欠測は校正/評価の分母から除き、欠測窓の14日総量は除外する。四半期は発行日の四半期。

事前候補順 matched_mean28 / open_mean28 / seasonal_level / recent_gated_ridge。校正130窓だけでridge alphaを[0,1]に固定し、日次と総量がそれぞれ校正で悪化しない上限を課す。seasonal_levelは各四半期のopen_mean28への非負補正 delta_q * 2013尺度 * 非休業mask。delta_qは各四半期の校正窓のjoint二次式から一回解析的に求め、日次/総量非悪化上限で制約する。季節・店別倍率・lambda・期間のgridなし。方式選択130窓のjoint最小、tie1e-12で順序優先。日次・非休業日の数量・総量・総量bias・四半期・元日窓を別表示し、joint改善だけで両目的達成と認定しない。

選択/alpha/四半期deltaを保存後、2015-01-01より前に確定した過去365日の完全実観測packetだけで最終ridgeを一回fit。全2015で係数/尺度/校正を凍結し、発行日前の56日contextのみ更新。2014内online fitと2015固定stateの差は報告する。内部と2015で数量モデルは2013尺度を一貫して用い、2015採点は既存uで比較可能性を保つ。

2015は旧250窓と元日10窓を合算せず（20店日重複）、各々同じ休業仮定mean28と比較する。観測only/欠測0仮定を分離しraw_actual/nullを保持。全候補を事前副として保存し、2015後の主昇格なし。負の結果も保存。

fresh macos-demand-seasonal-quantity-20261015及びexecution/readback/doc-records。仮説→source/config→全入力/過去packet→27以下のstate/journal→校正/選択→最終state→2015label前予測→両label評価→読戻し→文書閉鎖。親900/子870秒、Mac sampled physical footprint/peak RSS各2GiB。通常artifact24files768MiB/全32files1GiB/single32MiB/失敗reserve8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。全stdio/exit/source/state/closureを保存。旧変更/失敗/closed roots保持、削除/上書き/commit/pushなし。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/追加agentなし。heartbeat PAUSED保持。新仮説なしの反復をしない。
