# 季節内10店共有係数：2014一巡と発行日削除影響の事前契約

2026-10-15 JST。人の明示依頼により[季節別第一案](demand-seasonal-coefficients-plan-2026-10-15.md)を単一仕様として適用し、既読2014を検証する。2015内容decode/fit/予測/再評価は停止のまま。新取得/2016–17/予約31–54/販促/正式holdout/CARE/課金API/外部研究データ送信/push/採用なし、heartbeat PAUSED。

## 仮説と適用要件

共通係数を自Qの係数へ分ければ、他Qからの制約・目的の干渉を外し、同じ特徴で両側条件を満たす補正が得られる余地がある。前回の固定方向診断では自Q内のtradeoffもあり、成功は前提としない。係数共有解除だけでなく、各係数に効くデータと制約対応も変える方式である。

許可10店(6,7,10,13,15,17,19,23,26,27)、2014Q開始cutoff4個、保存済み許可prefixを使用。親adapterは当該発行Qのrowだけをmetadataで選び、fresh payloadを渡す。学習関数は他Q row、全inputs、label reader/index、sourcepathを受け取らない。cutoff以前完結/available、2013尺度の2014可用性、raw0/nullとmaskの検査を継承する。

currentQの完全/適格rowは30/60/70/50、発行日3/6/7/5、全て2013だけと固定照合する。各10店の特徴適格row≥1を構造要件とし、欠ければ例外停止、後Q/採点/削除診断へ進まない。行単位の特徴不支持/B0はB固定としてrisk分母へ残す。発行日数や年度の追加「合格」閾値は置かず、全Qを少数・単一年支持として報告する。≥1も3〜7日も統計的十分性や採用根拠ではない。

## 学習仕様

自Qの3係数β_q、既存切片/水準差/週変化、λ=1全係数罰則。自Q適格集合のw=1/(10*nE_qs)和1に対し、r=(Y−B)/(14u)、Lq=Σw(r−xβ_q)²。最小化はLq+||β_q||²。全体表現(1/4)Σq[Lq+||β_q||²]で元の罰則尺度へ揃え、λを4倍にしない。

自Q全観測完全集合（入力不支持含む）のv=1/(10*nI_qs)で平均under≤同休業mean28、平均over≤同B、学習row P=B+14u*xβ_q≥0を課す。Q別MSE hard制約・後段alpha・総量固定・soft penalty・部分共有・特徴/期間/λ/閾値探索なし。欠測0仮定を学習しない。

旧exact3D core/v2数量総和/verifierを不変で使用する。B/Y=Fraction(math.fsum(日次))、unit=14Fraction(u)、目的/制約重みも有理数。各fitで元hinge/非負/全cut/KKT/gap0を確認後に確定し、βは有理数で保存。failureや支持不足をbeta0成功へ置換しない。

## Primary予測・採点

各2014発行Qの開始stateを14日全体へ使用し、target中のQ境界では切り替えない。入力支持/非負floor/日次配分/canonical総量は[前回契約v2](demand-constrained-2014-contract-v2-2026-10-15.md)を継承。Δ0/不支持/B0はbaseline日次コピー（canonical Bとの端数例外を台帳へ）、P0<Bは全日0、変更はexact比例和P。

4primary state・全260予測・pinを保存してから2014labelだけ別に採点する。観測のみはrawnullを維持、欠測0仮定は休業相当位置だけ別採点。営業unknown/01-01・12-25休業相当を維持。全260/通常250/元日10/四季all-normal/年末を別報告。主総量MSEは店平均((P−Y)/(14u))²の店等平均、under/overは元数量。営業相当観測日の数量MSEも報告。

exact paired差が僅かでも正なら違反。必須は四季allとnormal・元日10の両modeで総量MSE/under/over≤B。全必須passと全260両mode総量MSE厳密減を「本一巡の総量改善」とし、同値と分ける。既読2014の探索的判定で、独立性能/本番採用ではない。悪化QのB事後差替えはしない。

## 少数発行日依存：21通りの削除影響

Primaryを先に完成・凍結・採点し、その方式や採否を変更しない別実行工程で行う。各primary学習payloadの異なる発行日を全列挙し、当日の全10店を一緒に除く。Q別3/6/7/5、合計21通り。除外後は特徴適格の目的重みと全completeのrisk重みをそれぞれ再計算し、同じλ/特徴/制約で再推定・certificate検証する。行・制約集合の変更も含む手続き全体の感度で、純粋な係数ノイズの推定ではない。

固定probeはprimaryに保存した同じ発行Qの2014入力専用情報（baseline、features、scale、origin/key）とし、別Qへその係数を適用しない。各Q70/60/70/60窓、入力不支持も分母に保持。Primaryとの差として係数差、総量差の最大絶対値/RMS/平均絶対値、変化窓数、全probe/特徴適格probe別の分母を記述し、全体平均でfallbackの希釈を隠さない。窓別total差も保存する。RMSはexact平均二乗差と表示sqrtを別保存。

除外方策を2014targetで採点せず、LOOの成績比較・候補選択・primary係数変更・採否救済に使わない。CV予測/21独立検証/標準誤差/信頼区間ではない。小さい感度でも未観測日や別年度への頑健性を認めない。正常解で大きい変化なら削除感度、solver上限/証明失敗は計算上未解決と区別する。

除外時に構造支持が欠けるか数値failureなら、失敗fold・完了分・部分予測/差を保存し、その時点で削除工程を停止する。Primaryは変更せず、依存性評価未完了と報告する。成功foldだけで安定性を結論しない。

## 資源・保存・終了

準備/primary/削除診断/readback/文書閉鎖それぞれ親900秒・子870秒、Mac sampled physical footprint/peak RSS各2GiB。旧512rows/64round/512cuts/4096pivot・総65536/bit8192/cert512KiBを各solveに継承。削除工程の21問題にも同じ工程wall/resource上限を適用し、無制限にしない。

artifact通常24files/768MiB、総32files/1GiB、単一32MiB、failure8files/256MiB。EvidenceStore16MiB/512files/part256KiB/failure2MiB16files。全stdio/exit/source/primary・削除state/certificate/途中結果/失敗/closureをfresh rootsへ保存。既存変更/失敗/closed rootsは不変。途中予測はQ別にも保存し、failure予約枠にも保持する。

独立readerで自Q選択/再重み/4primaryと21削除問題/証明/予測/label別scalar/削除probe差を照合する。不一致なら成功認定を止めfailure保存。primary数値failureなら後Q/採点/削除を停止し、上限緩和やB代替・救済をしない。改善/悪化/全B/未解決いずれでも固定一巡と21影響診断で終了し、結果後の別候補/2015確認へ接続しない。p値/CI/bootstrapは今回実施しない。

共通MacとWindows固有/native/OS依存包括suiteの結果を分け、Windows工程は起動しない。PSI採用・依存lock/Xcode変更/commit/push/削除なし。Astra方法・進め方担当のread-only確認を受け、実装と結果もレビューする。
