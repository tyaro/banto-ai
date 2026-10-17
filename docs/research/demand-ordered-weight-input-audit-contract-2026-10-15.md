# 固定D1重みの発行前入力接続・支持とrank監査の事前契約

2026-10-15 JST。人の依頼により、[固定数値契約](demand-ordered-weight-numeric-contract-2026-10-15.md)の次工程を一巡する。学習・係数推定・候補予測・ラベル値の新decode・性能再採点を行わず、2015は参照/再評価とも停止。τ=1/20、絶対p32最近接偶数丸め、encoder v2、3特徴・2013尺度・休業相当01-01/12-25/営業unknownを変更しない。店13/特定日/支持分布に合わせた式/期間/閾値/λ/分類/定数探索なし。

## 境界と来歴

既存closed root artifacts/macos-demand-input-boundary-20261015-v2 の inputs.json/transforms.json/cutoff-availability.json だけを意味decodeする。labels.jsonl、mixed source、raw CSV、state/予測/評価、2015ファイル内容は読まない。旧保護rootのbytes hash検査は許可範囲で継続する。inputsは許可FIT10=(6,7,10,13,15,17,19,23,26,27)、全470行、2013–2014だけと既存validatorで照合。2014の全260発行日calendarを入力だけで照合する。

inputsからorigin前56日のdate/available_at/valueだけをfresh packetへコピーし、固定encode_featuresへ渡す。key/store/baseline/scale/target_dates/labels/path/readerは重み関数へ渡さない。旧xは既存input_featuresで算出し、new_x=r_stored*xをexact保存する。baseline/assumed maskと旧特徴理由を保存し、同休業mean28を変更しない。元入力を書換えない。

2013尺度/固定休業policyは2014cutoffで利用可能であり、2013行の旧xは2014での遡及学習用再現である。2013当時のprospective前処理とは呼ばない。一方、新rのμ/曜日平均/Vは常に当該origin前56日だけで、2013全期間profileを遡及適用しない。next-calendar-dayは既存の可用性仮定で、実到着時刻/タイムゾーンの証明ではない。

各2014Q開始cutoffのIは、以前検証・凍結されたcutoff-availability.jsonのaccepted_keysに基づく。そのうち発行Qがcurrent Qの行だけをmetadataで選ぶ。target末日<cutoff、origin+14≤cutoff、transform usable≤cutoffを再検査し、全て2013、Q別I/E=30/60/70/50、発行日3/6/7/5を固定照合する。Iを入力の欠測やlabel-indexの可用性だけから推測しない。旧ラベル数量を読み直さない。accepted membershipと来歴pinを保存する。

Eは旧input_featuresが非NoneでB>0の集合。元I/Eを保持し、r0をzero vectorとしてE分母へ残す。各storeの目的w=1/(10*nE_qs)、risk v=1/(10*nI_qs)を保存。r非ゼロだけの再正規化/行削除なし。旧不支持の履歴r>0はあり得るためraw非ゼロと旧適格非ゼロを分ける。算術/入力エラーはr0救済せず停止する。

2014issue側は入力適格Eだけで記述し、将来labelの完全性を調べない。issueのI/risk集合はunknown（未decode）と明示し、全入力をcomplete Iと呼ばない。記述用wは同じ店等重み・店内適格窓等重みを使い、学習/採点重みとは主張しない。Eが無いstoreは質量0、残るstoreへ再配分しない。

## 固定する監査量

train Q1–Q4の4集合、issue全260/通常250/元日10/年末、Q1–Q4のall/normalの12集合を別保存する。重なりは独立標本・独立検証としない。

1. 全行/旧E/I（既知の場合）/r_raw正/r_stored正/旧Eかつr正/方向2特徴非ゼロの行・店・発行日数、computed/support不足/旧不支持/丸め0等の理由を別集計する。全r分布の店・発行日別表も保存する。
2. E上でcount、Σr、Σr²（無重み）、Σw*r、Σw*r²、Σw*||x||²、Σw*r²*||x||²、各3列の旧/新energyを算出する。r massとfeature energyを混同しない。列座標/2013尺度/切片を固定したenergyであり、leverage/最終予測への影響量ではない。
3. 店軸と発行日軸で非負量ごとの質量/share、top1/top3、HHI=Σshare²、mass-equivalent groups=1/HHIを記述する。top-kは量降順、同量はstore数値/origin昇順。境界tieを明示する。総量0ならshare/HHI/1HHIはnull（undefined）で0や∞へ救済しない。独立標本数/標準誤差/信頼区間に読み替えない。
4. 元Eの旧3列とnew3列を、罰則なしexact Fractionでrank計算する。最大3pivot key/columnとbasisを保存し、全行がbasisに包含されることを検査する。rank(new_x)=rank(old_xをr_stored>0に制限)を照合。列2/3だけのdirection rankも記述する。r0行をrankに含めてもE/Iからは削除しない。
5. 目的重みの旧/新3×3 Gram、対角energy/trace/determinant、det(G)/積diag（全diag>0の場合）、非中心化列cos²=Gij²/(Gii*Gjj)をexact保存する。zero diagonalはundefined。これはPearson相関/中心化rankではない。数値effective-rank閾値や固有値による合否を追加せず、exact rankはexactのまま、近い共線性は数値を記述する。店/発行日別rankも同じ方法で保存する。

rank3や分散した質量でも少数・単一年の発行日支持は増えず、ridgeが可逆でもデータが十分とはしない。集中やrank低下があってもτ/λや店舗/日付除外を再探索しない。これは診断結果であり、under/over/MSE条件を判定しない。

## 人工・独立照合と終了

実データのr計算前に、fresh入力adapterのfields/時点/canary、元membership/1n保持、rank0/1/2/3/近共線、rank同値、zero-total集中、top tie、均等/単一集中、途中bit上限の人工試験を行う。実行sourceと契約を先にpin。旧数値37fixtureの無目的反復はしない。

実行後の独立readerは新adapter/encoder/audit/solverをimportせず、元inputのpast56と保存packetを照合しFraction/独自丸めで全470r/特徴積、元x/baseline/mask、accepted membership、各行重み、全監査量・rank/Gram・集中を再構築する。使用した保存sourceとinputpinを照合し、不一致/上限時は失敗と部分結果を保持し停止。上限を緩めずrankをfloat代替しない。

各準備/実行/独立readback/文書工程は親900秒・子870秒、sampled Mac physical footprint/peak RSS各2GiB、算術8192bit。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files。全stdio/exit/source/input-pin/state/partial/failure/resource/closureをfresh rootへ保存。旧source/失敗/closed roots/変更を保持し、上書き/削除なし。

この監査一巡で終了。input_integration_audited=trueになり得てもfit_ready=falseを維持する。次の学習の許可や成功認定に読み替えない。調整2014以前、自Q10店共有λ1、四季all/normal平均under/over非増加・MSE条件、同休業mean28、観測のみ/休業欠測だけ0仮定の別評価を維持。2015停止・heartbeat PAUSED・PSI採用なし。Windows native/OS依存包括suite、新取得/外部送信/追加研究agent/commit/push/依存lock/Xcode変更なし。ユーザー指定Astra1名はread-onlyで設計・コード・結果を確認する。
