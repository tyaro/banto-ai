# 固定重み：集中・自店信号なしの分析と学習開始条件

2026-10-15 JST。人の「2015再評価と学習を止めたまま分析し条件固定」に対応する事前契約。[入力接続監査](../results/demand-ordered-weight-input-audit-2026-10-15.md)の保存状態だけを使い、新r/旧xの再生成、fit、β、候補予測、ラベル数量decode、性能採点は0とする。既存閉鎖root/source/失敗/変更を保持する。

## 今回の有限分析

既読のQ4最大日energy70.71%、Q1店15/17・Q4店19の自店学習行r0、2014発行側の分布を出発点とする。新しい独立性能仮説の検証とは呼ばない。元input-auditのencoded-rows/audit-groups/support-auditをpinし、key/store/origin/旧x/保存z=r*x/r/元w/vだけのfresh projectionを凍結して分析childへ渡す。history/target/baseline量/scale/label/path/reader/全CSVは渡さない。旧210候補学習行と保存2014入力260行だけを使う。

全Qの各学習発行日を1つずつ、その日の10店を一緒に除く計21通りを固定列挙する。**元wを固定し、残存行へ再重みしない幾何診断**である。各除外の残存行・非ゼロ行/店/発行日、旧/新Gram/trace/列別除外energy比、exact rank、det(G_remaining)/det(G_full)を保存する。rank3→低下の有無は調べるが、energy/determinant比を予測変動/係数変化/不確実性としない。元学習E/I/w/vを書き換えない。最大日だけを選別せず全21通りを終了する。

全10店×4Qについて自店の保存学習zのrank/spanと、同店同Qの保存2014発行zの関係を調べる。rank(train_store∪issue_z)>rank(train_store)を自店span外とし、旧不支持None・eligible z0・nonzero z・span内外を分離する。pool rank3ならpool spanは全3次元なので、その包含を補間/十分な裏付けとは呼ばない。自店rank3でも凸包/典型的な水準/将来正誤は示さない。診断flagを店舗の固定分類や補正停止ルールにしない。

z0行の学習目的w*((Y−B)/(14u)−zβ)²はβ非依存定数、P=Bなのでpaired under/over差0。非負もbaselineにより満たされる。分母に残るが係数への信号や変化する制約は増えない。学習時の全z0店舗でも、発行時にz≠0なら他店で得た共有βが適用され得る。この影響の正誤/大きさはβ/labelなしでは判定しない。ゼロ店舗だけでなく全40組へ同じ診断を適用する。

新分析に適切な人工確認、独立再構築、Astra確認を行う。算術は8192bitで、rank/Gram/比較の約分前中間も検査し、超過は停止。保存rや元fit artifactを再計算/修復しない。各準備/分析/readback/文書の親900秒/子870秒、sampled Mac footprint/peakRSS各2GiB、旧artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16filesを維持。stdio/exit/source/projection/state/partial/failure/resource/closureをfresh rootへ保存する。

## 学習開始の必要条件（性能合格条件と分ける）

以下のANDを将来のcan_launch_learningとする。この文書は学習を起動する許可ではなく、現在の学習停止は有効。

1. 保存source/input/state/元membershipのpinと時点整合、2013–2014/FIT10/cutoff/変換可用性、同休業mean28、raw0/null/unknown/01-01・12-25仮定の一致。2015や未許可情報へ接続しない。
2. 全Q・全10店で元E/I・w=1/(10nE)/v=1/(10nI)を保持し、r0/旧不支持/B0を混同・drop・非ゼロr再正規化しない。β0がbaselineを再現し非負/paired risk差0となることを、将来の学習consumer/problem生成の人工・独立試験で確認する。
3. 全Qの罰則なしpool rank3、全21通りの1発行日除外後もrank3を満たす。これは保守的な研究手続き上の構造条件で、ridgeの解の存在/一意性に必要な数学条件や統計的十分性ではない。未判定/低下なら当該計画を止め、店舗/日付を除外して救済しない。
4. 今回の集中・自店信号なし/自店span外への共有適用を全40店Qで開示し、定数/λ/期間/特徴/店舗を結果後に選び直さない。70%等の事後集中率閾値は作らない。自店信号なしを黙ってbaselineへ差替えない。
5. 唯一のD1、τ1/20、絶対p32nearest-even、切片含む保存z、共有3係数/自Q/λ1、既存under-over/非負制約、exact証明/旧solver上限と下記有限実験を起動前にsource・問題schema・終了条件まで固定し、学習consumerの人工/独立照合を通す。現在その新consumerは未実装で、開始条件は未完了。
6. 資源/証跡/独立照合が全てpassし、失敗や欠落をβ0成功へ置換しない。全B/失敗/未判定も保存して有限終了する。
7. **人が学習再開を新たに明示する。現在は停止指示が有効なのでfalse。** 2015停止は独立に維持し、学習再開許可を2015再評価許可へ拡張しない。

開始条件を満たしても未来の平均過小量/過大量非増加は保証しない。今回の最終stateはfit_ready=false/can_launch_learning=falseを維持する。

## 将来の単一有限実験を固定する枠

今回は実行しない。別の学習再開指示が来た場合の実装枠だけを固定する。primary4Qの最大4fitと、各Q全発行日を1つ除く最大21再fit、計最大25solve。primary/再fitとも調整はcutoff前の2013自Qだけ、元の特徴・λ・制約を維持する。削除再fitは**残存する各店E/Iからw'=1/(10n'E),v'=1/(10n'I)へ再重みする元手続き**とし、今回の固定w幾何診断と区別する。欠ける店E/I、数値/証明/資源失敗で以後停止し、成功foldだけで頑健としない。

primary4state/全260予測、削除21stateと対応Qの保存入力への全1360probeをlabel採点前に凍結し、一度だけ採点する。以前の削除診断は採点しない契約だったが、この将来計画では削除版も下記の限定的主張を調べるため採点する変更を明示する。旧契約や保存結果は変更しない。probe差はprimaryとの係数差/総量差/変更窓/元fallbackを分け、CV性能/21独立年とはしない。最終学習consumer/problem/予測の数値仕様は開始条件5で別途検証する。全店×Q比較と、自店学習信号なし集合の結果も必ず開示する。outer結果からprimaryの差替え・λ/τ選択・店舗除外・season事後停止をしない。

## 開始後の判断を混同しない

- **総量改善**の既存判定は変更しない。四季all/normalと元日、観測のみ/休業相当欠測だけ0仮定の両modeで、同休業mean28比の総量MSE/平均under/平均overが非増加。全260の両mode総量MSEは厳密改善。店等平均・元支持・固定p192区間符号を維持し、未判定を合格にしない。
- **指定削除版の2014非悪化という限定的主張**は上記primary改善とは別。全21再fitが完成/証明され、対応Qのall/normal（Q1は元日10も）の両modeで同じ三指標非増加を満たす場合に限る。各foldへannual改善条件は追加しない。失敗/未完/違反/未判定なら当該主張をせず、primaryを差替えない。一般的な発行日頑健性/別年度安定性/独立21検証とは呼ばない。
- **自店信号なしの指定セルで2014悪化なしという限定的主張**も別。2013自店学習zが全0の全storeQ（ID手指定でなく共通式）について、2014の各同店同Qセルを個別に、両modeのpaired MSE/under/overで判定し、全セル全指標が非増加の場合に限る。対象セル全体平均での相殺をしない。旧不支持/発行z0による同値と、発行z非ゼロ適用を分ける。支持不足/未判定/悪化なら当該主張をしない。将来の共有適用安全性の保証や、結果後の補正停止ルールには転用しない。

これらは研究上の記述・主張の条件で、PSI製品採用・独立性能認定・2015解禁ではない。今回はいずれも未評価のまま。heartbeat PAUSED、Windowsnative/OS依存包括suite/2016–17/予約31–54/販促/CARE/正式holdout/課金API/新取得/外部送信/commit/push/依存lock/Xcode変更/採用なし。
