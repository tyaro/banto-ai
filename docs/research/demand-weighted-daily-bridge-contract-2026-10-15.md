# 固定非ゼロ係数→日次予測の人工接続契約

2026-10-15 JST。人の明示依頼により、[人工consumer](demand-weighted-consumer-artificial-contract-2026-10-15.md)の次の未検証項目を人工だけで検証する。学習/solve/実データ接続/実ラベル/2014性能/2015内容参照・再評価なし。係数は手指定の検査点で学習済みstateではない。旧closed source/失敗/状態を変更せずfresh source/rootへ保存する。

## 固定する接続

新pure bridgeはschema,input,transforms,weighted,stateだけのconcrete payloadを受ける。label/path/reader/外部I/Oなし。input=demand-input-v1、weighted=旧x/reasons・固定r/z/state pin、transformsは固定2013尺度・01-01/12-25休業相当・2014開始。stateは人工専用schema/quarter/cutoff/usable_from/手指定beta3 rational文字列/fit_performed=false。originは2014、全targetは2014以前、stateは同Q開始cutoffでoriginまでに可用。全metadataの検査を数量変換より先に行う。trusted API境界であり認証やOS sandboxではない。

past56のraw0/None、date/翌日可用性、unknown・固定mask、元mean28曜日支持とbinary64日次値のexact一致を確認する。旧xをpast14から再構築し、past56だけの固定encoder v2によるr/z/encoder state pin一致を検査する。変更されたbaseline/r/z/pinを信じない。ラベルはbridgeへ渡さず、人工scenarioは予測凍結後の別関数で処理する。

```text
B = Fraction(math.fsum(baseline daily))
E = sum(Fraction(each baseline daily))
unit = 14 * Fraction(scale)
z = r * old_x      # 切片も含む、τ1/20/p32 v2固定
rawP = B + unit * dot(z,beta)  # old_x=None/B0ではrawP=B
P = max(rawP,0)
delta = P-B
```

既存seasonal_shared_2014_v2の配分規約を維持するが、学習core/solverをimportしない。delta=0/旧不支持/B0ではbaselineをexact/displayともそのままコピーする。r0・beta0・非ゼロbetaの直交dot0もcopy。copy時はcanonical Bとexact Eが異なり得るので再比例しない。P=0かつdelta!=0は全日0。その他はdaily_i=Fraction(baseline_i)*P/Eとし、全日exact和=P、非負・休業0・元の相対日次形を確認する。除数はcanonical BでなくE。元の営業日baseline0も0を保持し、その後に量を配分しない。

clip前rawPとfloor有無を別保存する。floorは既存発行側規約であり、学習時raw非負制約の代用品ではない。新しいrow縮小/上限/季節・店別特例を足さない。float displayは表示用、exact daily/総量を計算・lossへ使う。display丸め差（fsum(display)−P）も別保存し、exact総量一致と混同しない。表示または表示fsum非有限/算術上限超過は拒否しbaselineへ救済しない。

## 人工の検査と反例

4季節・複数店舗、切片/水準/週変化/混合の固定非ゼロbeta、正負delta、非ゼロbeta dot0、r0、旧None/B0、beta0、rawP負/丁度0、営業0/None、元日/年末休業、祝日でも通常open、scale=.1・canonical B!=Eを含める。ゼロ・欠測scenarioは観測のみと休業Noneだけ0仮定を分離し、営業Noneは残す。元日観測0/休業正値を消さない。

任意の非ゼロbetaについて四季平均過小/過大の非増加やMSE改善を保証しない。人工の残差と同方向の補正・overshoot等の負例も保存し、採用条件が維持されるだけで通過/改善とは呼ばない。調整2014以前、自Q元E/I・1/(10n)・λ1、既存四季all/normal・元日両modeのunder/over/MSE条件は変更しない。今回は学習問題を変更せず、これらの実性能ゲートは未評価。

独立readerはbridge/consumer/encoder/旧feature/core/solverをimportせず、保存人工inputから旧x/r/zとβ→rawP/P/daily/branch/丸め差を別checked arithmeticで再構築し、全case名/全配列長/全値・別scenario lossを照合する。供給encoder state pinとの対応確認と、encoder全stateの独立再現を区別する。前回と同じchecked reference numbers v2を使用する。

親900/子870秒、Mac sampled physical footprintとpeakRSS各2GiB、整数・約分前積/和/比較8192bit、artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持する。小さい有限case集で全stdio/exit/source/input/state/partial/failure/resource/closureを保存し、失敗rootを修正しない。

完了してもdaily_bridge_artificial_readyだけを更新し、fit_ready/can_launch_learning=false、heartbeat PAUSED、2015停止。実prefix/solve/係数最適性・性能改善・PSI採用は未認定。Windowsnative/OS依存包括suite/2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit/push/依存lock/Xcode変更なし。

Astra事前確認により、発行Qの係数をtarget途中のQ境界でも切り替えないことを明記する。fallbackでもbetaとstate可用性を検査する。非ゼロbetaの直交dot0、丁度floor境界の係数は人工inputのexact式から事前決定し、label/損失による調整をしない。B!=Eのfixtureで微小非ゼロdeltaを与えるとcopy→比例枝切替による丸め差相当の再配分があるため、当該差を保存し、日次写像の連続性や日別誤差改善は主張しない。

人工履歴は最終7日を固定+1する例と、全56日に固定曜日加算.1×weekdayを与える例を追加し、週変化列が非ゼロの係数接続を検査する。4Qのweek-onlyは非ゼロ負delta、mixedは正deltaで、異なる正baseline値がある両枝の相対形をexact cross-productでも独立確認する。直交例は2つ以上の非ゼロ積がexact相殺することを必須にする。各Qのunder/over負例は人工1行の反例で、全10店季節平均ゲートを実施した結果とはしない。
