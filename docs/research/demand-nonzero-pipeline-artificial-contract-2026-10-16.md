# 非ゼロ最適の人工prefix→consumer→solver→日次予測：事前契約

2026-10-16 JST。実データ学習/2015再評価停止のまま、[solver人工検証](../results/demand-weighted-solver-artificial-2026-10-16.md)で未確認だった非ゼロconsumer解の日次接続を検証する。実source/実problem/実labelは内容decodeしない。旧source/closed roots/失敗/変更は保持する。

## 起動前に固定する人工問題

FIT10・固定2013暦21発行日を自Qに分け、各storeのpast56を14日blockの10/12/14/16、scale10、同休業mean28から生成する。全ラベルはbaselineに営業相当日だけ+1または−1（休業相当日は0）で完全非負とする。正負×Q1–Q4の8primaryだけをcompile/solveし、結果後の選別やprefix探索、削除25の再試験をしない。旧consumer/encoder/solver/bridgeは変更しない。

old feature x0=[1,Fraction(binary64 .1),0]、target t=±1/10は別表現。z_i=r_i*x0、R1=Σw r_i、R2=Σw r_i²とし解析β=t R1 x0/(1+R2||x0||²)をoracleとする。Q1初発行のpast56に元日が含まれrが異なり得るため、全row同zと仮定しない。r_i>0、元E/I/w-v、非ゼロβ、stationarity、全Pのbaselineとlabel間包含をexactに検査して解析解の元hinge可行性を確認する。結果不一致は失敗で保存し、λ/τ/期間/labelを変えて救済しない。

各consumer問題を既存solverで一度解く。独立verifierが元全hinge/非負、J尺度KKT・gap0と解析βの一致を確認し、各Qの学習側平均under/over非増加を確認する。これは完全人工ラベルなので両評価modeは一致するが、後の欠測scenarioのmodeは分離する。

## 接続の証跡と日次入力

fresh connectorはcompiledとcertificateからだけβを作り、caller任意βを受けない。独立verifier callbackで証明を検査し、同Q・cutoff・consumer input/problem/certificate/verification pinsを保存する。2014人工issueのinput/transforms/weightedだけを旧bridgeへ投影し、評価labelを渡さない。

旧bridgeのnested fit_performed=falseは『そのpure bridge component内でfitしない』を示す局所flagであり、係数の来歴を示さない。外側schemaにartificial_prefix_fit_performed=true、real_fit_performed=false、全provenance pinsとlegacy payload pinを必ず持たせ、人工prefixからsolveした事実を明記する。実学習済み係数や実学習再開へ読み替えない。

人工issueは2014-01-01/03-26/04-02/07-02/12-17の5日。uniform/weekday（weekday×.25をpastへ加算）×全10店×正負=200予測。追加のflat/missing/B0/open_zero×同5日×store6×正負=40、計240に固定する。Q1の03-26から4月のtargetまでQ1係数を使い、12-17のtargetは全て2014内。各stateは自身の発行Qだけへ接続する。r0/旧None/B0と過去休業の重複理由もそのまま保存する。

非均一baselineで正負のexact比例配分、canonical総量と日次exact和の区別、日次copy、閉鎖mask0、unknown、営業0/None、同休業mean28、未来/別Q/係数・proof・pin改変拒否を確認する。floorの分岐自体は既存人工検証範囲であり、今回得られたβでfloorを必ず踏むとは要求しない。今回踏まなければ非ゼロ解→floor接続は未確認と明記する。

評価labelは全予測後の別処理で作る。store6の60予測だけにmatching_truth/baseline_truth/open_missingの3種、休業を含む24予測にはclosure_missing/closure_positiveも加え、計228人工label scenarioを固定する。観測のみと休業相当Noneだけ0仮定を分離し、営業Noneを0にせず、営業0/休業正値を消さない。baseline_truthでの悪化も保存し、学習側の制約から未来の非悪化を保証しない。このscenario atom検査は全10店の実四季ゲートではない。

matching_truthはmax(baseline±1,0)を営業相当日に置く固定人工規則とする（B0 stressの負数量を避けるため）。学習prefixにはB0を入れず上の±1規則がそのまま適用される。rank1/週変化係数0のfixtureであることを明記し、実学習のrank条件を緩和しない。I/O canaryは保存240予測とは別の1回の接続呼出として数える。

## 独立検証・資源・停止

独立readerはconsumer/encoder/solver/connector/bridgeをimportせず、保存された人工元prefixからB/Y/unit/旧x/r/z/fullencoder数値state・母数/重み、解析解、全certificate、日次入力からbaseline/r/z/配分・総量・flags、全228scenarioの両modeのloss/supportを再構築する。全8state/240予測/228labelの名前集合・配列長・provenanceを固定一致させる。encoderの記録max_bits値そのものとsolver runtime max_bitsは独立同値再現の対象外の診断とする。

約分前に形成する整数積/和/比較も8192bit、同solver有限上限、親900/子870秒、sampled Mac physical footprint/RSS各2GiB。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持。全source/入力/pins/解析/compile/solver全pivot-round/証明/予測・label atom/state/stdioexit/partialfailure/resourceclosureをfresh rootへ保存し、失敗はβ0成功にしない。

Astraに起動前と保存結果をread-only確認してもらう。調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/overとMSE非増加・annualMSE厳密改善、同休業mean28と評価mode分離を維持する。実性能ゲートは今回未評価。

fit_ready=false/can_launch_learning=false、実fit/実problem内容decode/実2014採点/2015内容参照再評価0、heartbeat PAUSED。新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/Windowsnative/OS依存包括suite/採用なし。人工接続完了から自動的に実データ適用へ進まない。
