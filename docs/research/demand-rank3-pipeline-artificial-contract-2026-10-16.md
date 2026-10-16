# rank3・週変化係数非ゼロの人工pipeline事前契約

2026-10-16 JST。実データ学習・2015再評価停止のまま、[前回のrank1人工接続](../results/demand-nonzero-pipeline-artificial-2026-10-16.md)を補う。実source/実problem/実labelは内容decodeせず保護hashだけ確認する。既存source・変更・失敗・closed rootsを上書き削除しない。

## 固定した人工prefixと非ゼロ保証

固定FIT10/2013暦21発行日、自Q・scale10・同休業mean28を維持。FIT配列の位置mod3でstoreにA/B/Cを割り当てる人工規則とする。各past56は次の値を日数順に並べる。

| history | past56 | 旧x（表示小数はbinary64） |
|---|---|---|
| A | 10×14日、12×14日、14×14日、16×14日 | [1,.1,0] |
| B | 8×14日、10×14日、12×14日、16×14日 | [1,.2,0] |
| C | 10×14日、12×14日、14×14日、15×7日、17×7日 | [1,.2,.2] |

全ラベルは営業相当日にbaseline±1、休業相当日は0の完全非負。正負×四季8primary、420行出現（input context210を正負で共有）。削除再fitやfixture探索は行わない。λ1・τ1/20・p32nearest-even・元E/I/w-vを変更しない。Q1のpast56内の元日によるr差も保持する。z_i=r_i*old_x_iでrを二度掛けず、旧xのbinary64を有理数へ厳密に変換する。target t=(Y−B)/unitはexact±1/10。

旧xのA/B/Cとr_i>0によりweighted特徴量のrank3を作る。各Qで3行minorと罰則なしweighted Gram行列式をexactに保存し、rankはGの正定値性で代用しない。行毎にz_i成分非負、||z_i||²<4、各列に正のsupport、r_i>0を確認する。

G=I+Σw z_i z_iᵀ、q=Σw z_i tを再構築し、Cramerの3×3行列式からoracle β=G⁻¹qを計算する。正規方程式と恒等式

`||β||² + Σw(z_i·β−t/2)² = t²/4`

をexactに確認する。||z_i||<2から|z_i·β|<|t|、正tでは残差t−z_i·β>0と各列正supportから全β_j>0、負tは符号反転する。よって全β、特に週変化β2が非ゼロで、全Pがbaselineとlabelの厳密な間に入る。これを数値計算でも確認してから既存solverを一度呼び、独立KKT/full hinge/非負/gap0とoracle一致を求める。不成立は失敗で保存し、label・係数・期間を変えて救済しない。

## consumer→solver→日次接続

旧consumer/solver/encoder/connector/bridgeは変更しない。既存connectorの独立verifier callbackでcertificateを検査した後、そのβだけを同Q/cutoff/usable_fromのinput-only旧bridgeへ渡す。consumer input/compiled/problem/certificate/verification/input/legacy-payload pins、states→予測→評価label各段階freezeを維持する。外側artificial_prefix_fit_performed=true/real_fit_performed=false、nested fit_performed=falseはpure bridge component内でfitしないという局所flagに限る。

人工issueは2014-01-01/03-26/04-02/07-02/12-17。A/B/C history×uniform/weekday×10店×正負×5日=600予測と、flat/missing/B0/open_zero×同5日×store6・historyA×正負=40、計640予測に固定する。weekdayは各日のweekday×.25をpastに加える。case名と実input生成式を独立一致させる。正負各QでCの週寄与がraw totalへ非ゼロに伝わり、非均一日次配分でも保持されることを確認する。

各予測で`weekly_component=unit*z2*β2`、`raw_total_without_weekly=B+unit*(z0β0+z1β1)`をexactに保存し、raw_totalとの差と一致させる。これは係数を0に差替えて予測し直す操作ではなく、同じ一回の予測の代数分解。非ゼロ週項を消す・二重rを掛ける改変、rank1/週列0への退化を捕捉するcanaryを含める。

同休業mask、unknown、営業0/None、r0/旧None/B0、canonical Bと日次exact和の区別、日次copy/比例配分を保持。03-26は4月targetまでQ1を使用し、全targetは2014内。floorやcanonical差付き比例配分を必ず踏むことは要求せず、未到達なら今回未確認と記録する。

## 評価と独立検証

全640予測freeze後、store6の100予測にmatching_truth/baseline_truth/open_missing、休業を含む40予測にclosure_missing/closure_positiveも付け、計380scenarioを固定。matching_truthは営業相当日max(baseline±1,0)・休業0。営業NoneはNone、営業0と休業正値を保持し、休業相当Noneだけ0仮定と観測のみを分離する。baseline真値で悪化する反例も保存し、未来の非悪化を保証しない。これは人工atom検査で実全10店四季ゲートではない。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、元人工prefixとinputから旧x/r/z/fullencoder数値state、元分母/重み、rank3 minor/Gram、別実装のCramer oracle/恒等式、全certificate、日次配分・週寄与・全380scenario両modeを再構築する。全8/640/380の正確な名前集合・配列長・strict bool・有限数量/正scale・曜日support・dot等長を検査する。runtime max_bits値そのものは別経路で同値再現せず診断として区別する。

各親900/子870秒、Mac sampled footprint/peak RSS各2GiB、約分前に形成する整数積/和/比較8192bit、旧solver finite上限。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持。全source/人工入力/pins/rank/oracle/問題/証明/全solver pivot-round/週分解/予測/label atom/stdioexit/partialfailure/resources/closureを保存し、失敗をβ0成功へ置換しない。

Astraに起動前と保存結果をread-only確認してもらう。調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/overとMSE非増加・annualMSE厳密改善、同休業mean28・評価mode分離を維持。人工rank3は実データの情報量/集中/頑健性/性能を保証せず、実のrank・開始AND条件を緩和しない。

fit_ready=false/can_launch_learning=false、heartbeat PAUSED、実fit/実problem内容decode/実2014採点/2015参照再評価0。新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/Windowsnative/OS依存包括suite/採用なし。人工検証完了から実適用へ自動接続しない。
