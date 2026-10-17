# 学習量の妥当性：固定全窓の曲線と早期停止（2026-10-14）

## 今回分かったこと

人の「このモデルは256stepで足りるか」を受け、[出力前の新診断手順](../research/demand-training-adequacy-design-2026-10-14.md)で時系列分離・学習側だけの尺度・固定全窓の曲線を追加した。**この新条件では256stepは改善途中だった。**

内部検証jointの最良は両模型とも **1664step**。256stepからの改善は、入力なし **8.877577%**、あり **8.947989%**。その後は学習誤差が下がる一方で内部検証誤差が悪化し、両方 **2432stepで早期停止**した。最後まで増やせばよいという結果でもない。

旧256step比較と2016の9/15未達を保全する。新診断は学習窓数・尺度・validationが変わっており、旧630窓モデルの最適stepが1664だと証明したものではない。しかし、収束を見ず256で打ち切った従来手順では学習量の十分性を判断できなかったという問題を、実測で確認できた。

## 時系列分離と漏洩対策

旧630key metadataから、label終端が2014-07-01未満の450窓（15店各30）を学習、originが2014-07-01以降の180窓（各12）を内部検証とした。学習最後のtargetは2014-06-30、検証最初のoriginは2014-07-01。跨ぎ窓0、ランダム分割0。元の窓は過去の観測maskで選ばれた適格窓であり、この支持選別を未記録の窓や休業日へ一般化しない。

uは各店舗の2013-01-01〜2014-06-30の観測平均から再計算。546暦日、実0を含み欠測を除いた545観測日。検証量/maskをuへ使わないことを未来payload poisonの新確認で検査した。旧2014末までの尺度の流用0。positive15はu>0、元21/22/29はこの期間も0なので対象外理由を保存、他店尺度/floorへ置換0。

保存prefix pinを再利用し、必要な2013–14だけ数値解釈。2015/2016/2017・新archive/予約群/正式holdoutの数量や旧weights/旧予測は読まなかった。保存された630のpast-only profileは再利用し、新uで8特徴をencode。原profile再集計0。calendar支持は新450学習窓のmaskだけで求め、結果は42/56。元日/Christmas支持なしchannelを内部検証で増やしていない。

各originの数量入力は前56日getterで制限し、過去profileのorigin/past_end/last_error_dateを確認。検証contextに学習期間の既知履歴が入るのは通常の時間順予測の利用可能な過去であり、現在の検証labelを入力に渡していない。

## 二模型と終了方法

30369parameterのStatisticalFeatureMeanを新initialから二件学習。seed20261014、同initial/sampler、450keyから8窓/step。数量q/u・mask・context2統計・calendar・baseline・lossを共通にし、相違は統計8入力の有効/全0だけ。旧weightの継続学習や、完成済みouter forwardの反復は0。

AdamW lr3e-4/betas(.9,.999)/eps1e-8/wd.01/gradnorm1、CPUfloat32/2threads/interop1/deterministic。上限4096step、0step＋128stepごとに固定train450/validation180全件をeval/no_gradで測った。各店の日次尺度化MSEと総量尺度化MSEを.5ずつ足し、15店を等重み平均。更新batch lossを固定評価lossと混同しない。

warmup512step後、内部検証jointが相対0.01%超の改善を6回連続示さなければ停止。厳密な最小lossのbest weightはclone保存し、patience判定とは別に扱った。0stepの初期baselineも候補に含めたが、今回は両側で1664stepが最良だった。2432stepはbest以降6checkpointで改善なし、上限4096には達していない。

|step|入力なし train|入力なし validation|入力あり train|入力あり validation|
|---|---:|---:|---:|---:|
|0|0.042262242|0.082152416|0.042262242|0.082152416|
|128|0.042167986|0.082039161|0.042167292|0.082039603|
|256|0.041303144|0.081709098|0.041303405|0.081698724|
|512|0.038262066|0.079600418|0.038230143|0.079504760|
|1024|0.034520830|0.077554202|0.034387279|0.077149808|
|1664|0.033904076|0.074455310|0.034310184|0.074388332|
|2048|0.032094547|0.076427202|0.031921496|0.076579339|
|2432|0.030945165|0.079792302|0.031271263|0.077631836|

lossは固定窓に対するjoint MSE。各20checkpointをraw curveに保存した。検証は固定した2014後半の同じ窓を20回監視してbestを選んでおり、独立未見testではない。真の最適点、複数seed安定性、未知性能、完全収束の認定ではない。

## 256step以降と入力追加の効果を分ける

今回の主問は学習量だった。入力なしも256から1664で約8.88%改善、入力ありも約8.95%改善したため、両方の学習を早く止めすぎる可能性を調べることが先に必要だった。

最良同士の内部検証jointは入力なし0.074455309859、あり0.074388331514。入力追加の差は **0.089958%** と小さい。学習を増やした約9%と、統計入力の約0.09%は別の比較であり、「σ/EMAで約9%改善」とは言わない。8入力の一括比較なのでσ単独の効果でもない。

候補の初期baseline比は約9.450830%改善したが、この値もcheckpoint選択に使った内部検証値。2015/2016の新性能、実設備/メーカーPSIへの効果を示していない。最良以降の検証悪化は過学習又は最適化の不安定さの兆候で、原因を一つに同定していない。

## 新確認と保存

新4確認一回allpassed：label境界の分離/跨ぎ拒否、検証payload非アクセスの尺度計算、warmup/patience/停止後再入拒否、微小bestと改善閾値の分離/非有限拒否。旧model/暦/統計の確認、旧fit/evaluation/CIは反復0。

source15実bytes・出力前契約・split/u/fit支持・使用key/入力ledger・原ID/mask付き2013–14選択量・sampler/initial・1024/2048prefix・全更新journal・固定全件曲線・best/final weights・summaryをlocal保存。模型root22files/3655002bytes、immutable closure。raw checkpoint JSONは全child stdoutに残り、child stderr/exit0も判定前保存。正常出力の環境警告を保持した。

実行37.708865秒、OS peak private 1141428224bytes。実行900秒/private2GiB/output1GiB/single32MiB/files32、normal24file768MiB/failure8file256MiB、記録16MiB512file/256KiBpart/reserve2MiB16file、prep128KiB16fileを維持。宣言source pinsはfull loaded/native runtime閉包やglobal coupled容量認定ではない。

計算parent HEAD04a4239＋未commit新source/設計の実bytesを保存、clean commitからの計算へ補わない。原pure/helper模型sourceと元closed roots不変。新helper失敗0、追加agent0/CARE手動待ち。本文representative-demand-training-adequacy模型rootと同-launch-records、文書照合は同-doc-records、Git後同-git-records/post-saveを優先。

## 次の判断と区切り

この新手順では学習の改善途中と検証悪化を測れたので、今後の学習終了は固定256ではなく内部検証で決める方法を研究の基本にする。1664という数字を別の学習窓数/期間へそのまま流用しない。

次に進むなら、この選択手順を固定したうえで、学習後の性能を測る対象・期間を別契約にする。2015/2016は既読の回顧評価であり、新checkpointで再利用する場合は未見評価と呼ばない。未知対象を使う場合も予約群/正式holdoutを無断解除しない。今回の曲線から自動で追加training/別seed/learning-rate/半減期gridや2017推論に進まない。

事前設計どおり一回の診断を保存してdirect PAUSEDで区切り、次の問いを人と判断する。旧256条件の失敗を消さず、σ追加が大きく有効とも、時系列NNが不可能とも結論しない。automation PAUSED不変、formal_permission=false/credit0/native禁止/登録holdout未読/正式受入未完了。Git独自source/架空確認/集約docsのみ、原quantity/profile/尺度/ledger/予測/weights送信0。
