# 共有・縮小の有限安定性診断の事前契約

2026-10-15 JST。新候補の性能計算前に保存する。人の依頼と[Astra設計確認](demand-shared-shrink-astra-review-2026-10-15.md)、別担当の[独立プロセス監査](demand-shared-shrink-process-audit-2026-10-15.md)を反映。

## 範囲・仮説・停止

許可FIT10 (6,7,10,13,15,17,19,23,26,27)、既読2013尺度/履歴と2014だけ。少数の非ゼロDを残すgateでC/Aが一例の残差に引かれるため、店舗・季節の情報共有とbaselineへの固定縮小により係数・補正幅の除去感度を抑えられるかを調べる。予測精度や全局面の安定化は保証しない。

今回は新2015入力・ラベル・成績の読出し、予測、再評価を行わない。旧2015成果・state・closed rootsは不変で保持する。2014も既読選択済みであり独立性能検証/逐次検証ではない。有限比較後は成功失敗に関係なく終了。λ/grid/特徴/gate/端点/期間/重み/分割/制約を結果後に変更せず、2015確認へ自動接続しない。heartbeat PAUSED保持、PSI採用なし。

## 固定推定則

候補は matched_mean28 / pooled_shrink / partial_pool の3つだけ。同じ現行persistent_anchorの未校正端点、同じ休業相当mask（01-01、12-25）と基点Bを使う。原0/null・営業unknownを維持。新gateなし、係数fitのためにgateを再変更しない。D=raw総量−B、e=B−Y、uは既定2013尺度。

元cal130の実観測完全120のみ（Q1..4=30/30/40/20）。各店Q内完全窓等重み、各店等重み、global各Q1/4。Aq=sum w*(D/(14u))^2、Cq=sum -w*e*D/(14u)^2。Ag=mean Aq、Cg=mean Cq。窓energyのKish集中度 n=(sum a)^2/sum a^2（energy0なら0）を計算。店/発行日でenergyを合算した集中度も報告し、独立標本数とは呼ばない。

g=ng/(ng+1)*clip(Cg/Ag,0,1)。localq=clip(Cq/Aq,0,1)。定数1を固定した一仕様で、最適化/EB/事後推定ではない。globalは当該Q自身も含み独立観測を増やさない。

QごとのUq=min(1,under上限,over上限,MSE非悪化上限)を既存厳密有理数side_boundで計算。年間共通最小Uは使わない。Aq<=1e-24なら両候補alpha0。支持ありなら pooled_shrink_q=clip(g,0,Uq)、partial_pool_q=clip((nq*localq+g)/(nq+2),0,Uq)。各店同じQalphaを使い、情報共有と同一alpha強制を区別。旧clip(Cq/Aq,0,Uq)は係数/幅の参照値のみ、追加採用候補ではない。

各Q校正under/over非増加tol1e-8、総量MSE非悪化tol1e-12を確認。通常selection120（元日10別、各Q30）で観測のみ・欠測0仮定それぞれの三条件を全て要求し、観測総量MSE最小/同点BでQ別採用停止。選択側の再校正なし。全2014/元日/年末・数量も別報告。欠測0校正は感度報告のみfit/追加選択に使わない。

## 事前固定した影響度診断

元cal130の店10除去と発行日13除去、計23を一回ずつ。残った完全窓についてQ内残店舗を等重み・店内窓等重み、Q等重みを再計算し同じ固定式で再校正する。Q内完全窓なし/A0は支持0で停止。完全journalにない12/17除去は無情報除去と表示する。

各除去のalphaと、元cal完全120/通常selection120の固定Dに適用したalpha*Dの変化（最大、RMS、非ゼロDのみのRMS）を旧参照と2候補で比較する。これらは反実仮想影響度であり、除去群の独立予測検証/多数の成功例ではない。支持2窓を除く場合を中心に報告し、無作動多数で安定と結論しない。全foldを候補選択/縮小定数調整に使わない。

## 証拠・実行制約

親900秒/子870秒、Mac sampled physical footprint・peakRSS各2GiB。既存Files上限（通常24files/768MiB、総32files/1GiB、単32MiB、失敗8files/256MiB）、EvidenceStore16MiB/512files/part256KiB/失敗2MiB16filesを維持。全stdio/exit/source/旧state/closure、仮説・影響度・負結果を新rootへ保存。独立readerでraw端点・重み・A/C・集中度・縮小式・有理数別算法上限・両labelscalar・選択・影響度を照合。共通MacとWindows固有/OS依存suiteは分ける。新データ・2016/17・予約31–54・販促・正式holdout・Windowsnative・CARE・課金API・外部送信・push・削除・本番採用は対象外。

最終Astra整合確認: Ag<=1e-24はg=0、energy総和0はn=0。各leave-outで重み/A/C/集中度/Uを全て再計算。元固定Dへの適用は影響度で、その対象のrisk非悪化保証ではない。partial_poolが常にpooled_shrinkより小さいとは限らず、大小・成績を見て方式/定数を変えない。明確な設計矛盾なしとの回答。
