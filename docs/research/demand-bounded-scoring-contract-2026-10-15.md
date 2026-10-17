# 保存260予測の有界区間集計：2014再採点の事前契約

2026-10-15 JST。人の依頼「2015停止、桁数内の集計方法をAstraと確認、保存260窓で2014評価完了」を受けた新しい採点工程。旧季節共有契約の推定法・入力・予測・評価母数・指標・四季条件を変えず、巨大な単一Fractionへのmacro通分だけを回避する。旧failed root/既存変更/全closed rootsを保持する。新fit/新予測/削除fit/2015内容decode・fit・予測・再評価0。2014結果から精度や方式を選ばない。

## 固定入力と数式

`artifacts/macos-demand-seasonal-shared-2014-20261015` の260窓predictions-before-scoring.json、freeze-before-scoring.json、scoring-labels.jsonをpin照合する。4state/旧source/旧closed rootsもbytes照合し変更しない。既に分離・保存された2014ラベルだけを使用し、2015を読まない。raw_actual=observed、assumed_missing_zeroはrawnullかつ休業相当mask falseの位置のみ0、営業unknown/実0/null/01-01・12-25休業相当を維持する。

候補/Bとも保存canonical総量P/B、Y=Fraction(math.fsum(actual14))、unit=14Fraction(scale)。総量MSE=((P−Y)/unit)^2、過小量=max(Y−P,0)、過大量=max(P−Y,0)。日次は保存exact候補配分/B binary64のFraction、all daily MSEと営業相当観測日のquantity MSEをscaleで正規化する。Bコピー時のcanonical端数例外を維持し、表示日次を再総和してcanonical総量へ置換しない。

各指標は店内の利用可能項を平均し、その10店平均。指標ごとの支持数n_sを別に使う。外側nullを埋めず、14日総量は14日完全な窓だけ。全260/通常250（元日以外）/元日10/年末/四季all-normalを両modeで別集計する。rawnull10、欠測0仮定10、真元日zero10を照合する。2014既読探索的結果であり独立検証ではない。

## 数値表現と判定

単一loss項・候補loss−B loss項をexact Fractionで作る。整数入力/分子/分母、算術の積・和、canonical Y、重み適用後の項を8192bit以内で検査し、超過は工程failure。項を省略/丸めて通過させない。solverとその8192bit上限は一切変えない。

固定binary小数精度p=192、S=2^192。各項tへ店内なら1/n_s、macroなら1/(10n_s)をexactに掛け、その後 lo=floor(S*t)、hi=ceil(S*t) を整数で求める。負数も数学的floor/ceil。境界整数だけを加算して[Σlo/S,Σhi/S]とする。macroのexact全項を通分しない。各scalarの項数≤8192、丸め境界幅≤項数/S、整数演算≤8192bit。実行中にp/上限を増やさない。

paired差はmacro候補区間−B区間ではなく、同じ支持の候補loss−B lossに同じ重みを掛けたdirect項を区間化する。保存するのはlo/hi整数・p・項数・非ゼロ項数・表示中点・幅上界。表示値と中点は判定に使用しない。全paired項0なら厳密同値の十分条件（正負相殺の同値を排除しない）。そうでない場合もupper≤0なら非増加を保証、upper<0なら厳密改善、lower>0なら悪化を保証。区間が0を跨ぐ/下端0上端正で未証明ならunresolved。上端0は非増加passだが厳密改善ではない。許容損失EPSではなく包含保証である。

四季all/normalと元日10、両modeの総量MSE・過小・過大の全必須条件は「厳密同値またはupper≤0」だけpass。lower>0はfail、残りunresolved。どれかunresolvedなら全条件充足を認めず、確定failとは別に記録する。全必須passかつ全260両modeMSE upper<0だけを厳密総量改善とする。日次数量MSEなども同じ区間で報告し、候補選択・後差替え・採用に使わない。

## 事前確認と独立readback

Astra方法/進め方をread-onlyで確認する。人工fixtureでnegative floor/ceil、厳密0、正負相殺、0跨ぎ、上端0、厳密正負、不均等店支持/欠測指標別支持、複雑な異分母（全体通分は8192超）、単項/項数/整数上限拒否、canonical端数例外・観測/仮定分離を検査する。新入口を直接importする確認を含め、旧テスト対象の取り違えを繰り返さない。

契約・source・人工結果を凍結してから保存予測だけを一巡採点し、group/mode単位の完了結果を保存する。独立readerは集計関数をimportせず、保存pred/labelからloss・支持・重み・paired項・整数境界・判定を再構築する。元予測/4state/source/旧閉鎖不変を前後照合し、solverをimportしない。不一致・空支持・上限超過は失敗、途中結果とresourceを保存して停止する。Astra結果レビュー、報告、引継ぎ、文書closureまで行う。

## 資源・保存・終了

準備/採点/readback/文書閉鎖ごと親900秒/子870秒、Mac sampled physical footprintとpeak RSS各2GiB。OS hard capではない。artifact通常24files/768MiB、総32files/1GiB、単一32MiB、failure8files/256MiB。EvidenceStore16MiB/512files/part256KiB/failure2MiB16files。全stdio/exit/source/設定/入力pins/部分結果/失敗/最終resource（失敗時もbest effort）/closureをfresh rootsへ保存する。

2015再評価、2016–17、予約31–54、販促、正式holdout、Windowsnative、CARE、課金API、新取得、外部研究データ送信、push/commit/削除、依存lock/Xcode変更、PSI採用なし。heartbeat PAUSED。本工程は保存予測の再採点と独立確認まで。21削除fitへ自動接続しない。共通Mac計算とWindows固有/OS依存suiteの結果を分ける。
