# 非ゼロ係数から日次予測への接続：人工検証完了

2026-10-15 JST。[事前契約](../research/demand-weighted-daily-bridge-contract-2026-10-15.md)、[fixture修正補記](../research/demand-weighted-daily-bridge-fixture-amendment-2026-10-15.md)、[Astra確認](../research/demand-weighted-daily-bridge-astra-review-2026-10-15.md)。

**固定した人工係数の日次接続39件・人工label82例、189check・期待拒否30件が通り、独立4,553比較が一致した。daily_bridge_artificial_ready=true。学習/solve/実データ接続/2015参照・再評価は実行せず、fit_ready=false / can_launch_learning=falseのまま。**

## 接続した式と配分

新pure [demand_weighted_daily_bridge.py](../../tools/demand_weighted_daily_bridge.py) は、input/transforms/weighted/人工stateだけを受け、ラベル・path・readerを受け取らない。既存学習core/solverはimportしない。係数は手指定の検査点であり学習済みstateではない。全metadata検査後、βをfallback前に検査し、mean28・旧x・past56だけによる固定r/z/encoder state pinを照合して予測を生成した。

```text
B = Fraction(math.fsum(baseline))
E = sum(Fraction(each baseline))
unit = 14 * Fraction(scale)
rawP = B + unit * dot(r * old_x, beta)
P = max(rawP, 0)
```

切片を含む全3列へ固定rを掛け、発行Qの同じ係数を14日全体へ適用する。予測期間が次Qへ入っても途中で係数を切り替えない。休業相当01-01/12-25・営業状態unknownを維持し、他の祝日を自動0にしない。

| 分岐 | 件数 | 規約 |
|---|---:|---|
| changed_proportional | 29 | daily_i=Fraction(baseline_i)*P/E、exact日次和=P |
| baseline_copy | 8 | delta0/旧不支持/B0では日次をexact/displayともそのままコピー |
| floor_zero | 2 | rawP丁度0/負でP=0、全日0。clip前総量・floor有無を別保存 |

r0、β0、非ゼロβの2つ以上の非ゼロ積が相殺するdot0もcopyを確認した。負rawPのfloorは従来の発行側規約であり、学習時のraw非負制約を満たした証明にはしない。新しいrow縮小・上限・店/日別例外は加えていない。

## 人工・独立検査

39caseは許可10店/4Qを含み、切片・水準・週変化・混合の正負係数、旧None/B0/r0、元日/年末、営業0/None、Q境界、float境界と微小非ゼロ補正を検査した。週変化列を実際に非ゼロにするため最終7日の固定+1を使い、曜日.1×weekdayを加えた非均一baselineで正負両配分を確認した。均一日次では誤った均等配分も通り得るというAstra指摘への対応である。

独立readerはbridge/consumer/encoder/旧feature/core/solverをimportせず、人工inputから旧x/r/z・係数binding・全39case名/全scenario集合・全日次配列・各branch・exact/表示丸め差を別checked arithmeticで再構築した。非均一8caseでは各196組のcross-productによる日次比率も照合した。元baseline0の18日について、営業日を含め0を保持した。encoder全stateを保存し供給pin一致を確認したが、全stateの数値max_bitsまで独立再構築したとはしない。

不正beta、未来state、他Q、2015、不正mask/旧x/r/z/pin、raw観測flags、baselineの1e-12改変、bit上限、表示overflowを拒否した。None/B0/r0のfallbackでもβとstateを検査し、未来metadata＋数量bombでは数値変換0回で拒否した。各日次floatが非有限になる場合と、各日次は有限でも表示fsumだけoverflowする場合を別に停止した。

## canonical総量と日次の丸め差

12caseでcanonical Bとexact日次和Eの差を保存した。copy枝ではexact和=Eを保ち、Bに合わせた再配分をしない。changed枝の分母はEで、Bを使わない。scale=.1ではunit=14*Fraction(.1)とFraction(14*.1)の差も確認した。exact予測をlossに使い、float displayは表示用としてfsum(display)−Pを別保存した。

微小な非ゼロdeltaでもB!=Eならcopyから比例枝へ切り替わり、baseline日次に丸め差相当の再配分が生じる。その差を隠さず保存し、この写像の日次連続性や日別誤差改善は主張しない。

今回の微小例はB−E=1/2^54で、exact日次和はPになる一方、float表示のfsumはBに留まり表示差は−deltaだった。微小な総量補正から、同じ小ささの日次変化や表示上の変化は保証しない。

## ゼロ・欠測と四季条件

予測をmaterializeして保存するまで人工labelを作らず、その後の別関数で82例を観測のみ/休業相当欠測だけ0仮定に分けた。営業Noneは残し、観測元日0・営業0・休業正値を消さない。休業は営業数量の母数から除き、complete14日だけ総量lossを作る。同休業mean28との比較を維持した。

各Qでbaselineに等しい人工実績へ正補正を加えるとoverが増え、負補正ではunderが増える反例を両mode計16セルに保存した。これは**各人工caseの反例**で、全10店季節平均の性能ゲートを評価した結果ではない。任意の非ゼロβやr>0が過小/過大非増加、最適性、改善を保証するとはしない。

調整2014以前、元E/I・w=1/(10nE)/v=1/(10nI)・自Q共有λ1、四季all/normal・元日の両modeで総量MSE/平均under/平均over非増加とannualMSE厳密改善という既存条件は変更していない。今回は学習/母数の変更・2014実性能採点を行わず、これらの条件は未評価。

## 失敗保持と資源

初版はfractional fixtureからmean28がちょうど1.5となりB==Eだったため、丸め差を確認するassertionでexit1となった。39予測とsource/stdio/partial/failure closureを保持し、初回をpassと数えない。fresh fixture v2の4block値.025/.05/.075/.125でmean28=.1/B!=E/r>0へ修正し、同じassertionを通した。予測core・配分式・閾値・上限は変更していない。人工検証は2回の試行、独立照合は1回で完了。

forecast最大222bit、独立の全予測・loss計算最大333bit（8192以内）。人工child 0.291756秒 / sampled footprint 25,641,464B / peak RSS 38,060,032B。reader 0.587695秒 / 18,612,728B / 30,801,920B。親900/子870秒・各2GiB以内。sampled資源確認でありOS hard capではない。

成功stdout 819,047Bは既定1MiB内。EvidenceStore16MiB/512file/part256KiBとfailure reserve、既存artifact上限を拡張せず、全stdio/exit/source/input/encoder・予測state/partial/failure/resource/closureを保存した。旧source/失敗/closed roots/変更と、handoff/indexの旧全文を保持した。

## 到達点

人工の日次接続は確認できた。実weighted-label prefix統合、最適化、非ゼロ学習済み係数の実データ接続、最大25solve/2014性能検証は未実行・未検証。人の学習停止は有効で、人工確認の完了から学習や実接続へ進まない。次に準備する場合も、別の明示依頼の範囲で実prefix統合の時点/来歴契約を固定する段階である。2015再評価の許可は別に必要。

Mac Python3.14.8の共通人工処理・独立照合pass、Mac固有footprint/RSS観測pass。Windows固有/nativeとOS依存包括suiteは未実行。2015内容参照・再評価0、heartbeat PAUSED、PSI製品採用認定なし。2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

証跡：[初版failed](../../artifacts/macos-demand-weighted-daily-bridge-20261015-execution-records/root-closed.json)、[人工v2 complete](../../artifacts/macos-demand-weighted-daily-bridge-20261015-v2-execution-records/root-closed.json)、[独立complete](../../artifacts/macos-demand-weighted-daily-bridge-20261015-v2-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-weighted-daily-bridge-20261015-v2-doc-records/root-closed.json)。
