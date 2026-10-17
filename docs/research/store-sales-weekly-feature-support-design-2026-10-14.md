# 保存8週入力の学習範囲監査（2026-10-14）

補正の二乗量が大きかった保存診断を受けた、新しい入力支持の記述unit。範囲監査を計算する前に本案を固定する。精度を改善するgate・方式選択を作る評価ではない。

## 入力と固定した範囲

閉鎖weekly-ridge-readinessのfit630行（正尺度15店・各42）とweekly-ridge-cohortの保存入力を読む。各fit特徴8列のmin/maxを全630行共通で定義し、店舗別min/maxも同じfit側から別欄に作る。2015値から境界を調整しない。補正の大きい2店だけを監査せず、全15店の8列を保存する。

評価入力は、保存input.featuresがある全窓を対象とする。target欠測か否かを選別条件にしない。未来actual・新score・forecastはこの監査に使わない。数量0・欠測は原のinput availabilityとして保持。入力がnullの45窓、尺度0の3店は範囲外と混ぜず、元理由と件数で別欄にする。最後のtarget欠測18窓は、監査入力が存在すれば監査する。

各originで、共通fit min/max外の列、店舗内fit min/max外の列を保存し、any outsideの窓数を集計。判定は厳密なx<minまたはx>max、値が境界と等しい場合はinside。さらに共通fitに対する最近傍の距離を、fit側の8列population stdで標準化したEuclidean距離として記述する。定数列は差0なら寄与0、差ありなら距離null/理由付き。閾値を探索せず、距離は事実の記述に留める。

## 読み方と後続

座標ごとの範囲内でも、8次元の組合せや将来関係に支持があるとは限らない。範囲外だから必ず悪化したという因果にもならない。店舗内と共通の範囲差は、共有する表現の問題候補として読む。監査対象のnと原予測評価のnを一致と仮定しない。

学習範囲だけで作った境界は未来labelを必要としないが、今回の監査自体は既知2015の事後診断である。範囲外窓を採点から削除したり、その窓だけ基準へ戻した成績を新しい独立評価として出したりしない。過去8週候補の未達は維持。

次の機構設計を行う場合、未支持入力の通知と予測方式のfallbackを分ける。通知は「学習範囲外」であり、故障・営業状態・需要変化の原因判定ではない。fallbackの追加価値は別の出力前契約と別の確認で検証する必要がある。元日等の希少日を機械的に範囲外の異常へしない。

原script/本案/input pins/fit範囲/全originの支持判定/距離/原stdio・失敗をfresh rootへ保存。旧fit/model/score/確認/CI反復0、新archive/2016/2017/予約数量0。実行900秒2GiB/output1GiB/single32MiB/files32、通常24file768MiB/失敗8file256MiB、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files不変。formal_permission=false/credit0/native reader禁止/登録holdout未読、追加agent0/CARE手動待ち/automation PAUSED。Gitは集約docsのみ、生feature/quantity/ledger/係数/予測を送信しない。
