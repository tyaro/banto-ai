# 日次bridge人工fixtureの修正

2026-10-15 JST。初回の39予測は生成・保存されたが、fractional_branchesで失敗した。block値1,1.2,1.4,1.6からmean28がexact binary64の1.5となり、canonical Bと日次exact和Eの差を作れていなかった。狙った境界fixtureの設計誤りであり、coreの配分式や検査条件を緩めて修正しない。

初回source/stdout/stderr/exit1/partial/failure closureを保持する。fresh fixture v2で4block値を.025,.05,.075,.125へ固定し、mean28=.1でB!=E、かつr>0となる人工入力へ修正する。新checker v2は同じstrict丸め差条件を維持し、partial replayも失敗時に保存する。新supervisor v2で旧失敗closureとsource pinsを守る。

人工だけの有限再検証であり、実データ・fit・2015は使わない。39case・5種betaの4Q・2つ以上の非ゼロ積の相殺・曜日別非均一shapeの正負補正・営業0/None/元日/年末を維持する。8192bit/各2GiB/900-870秒/旧保存とstdio上限は変更しない。初回はpassと数えず、人工検証に2回試行した経緯を結果に残す。
