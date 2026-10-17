# 総量過小非増加と元日前後数量の有限比較

2026-10-15 JST。人の直接委任「14日総量の過小予測が増えない条件も加える/元日前後改善/2014以前調整/同仮定mean28/観測と欠測0仮定分離」に従う。前の通年主は通常MSE改善でも過小量増加・元日MSE悪化だった。平均予測の候補を上方補正に制限し、日次/総量のMSEと一方向の過小量を同時に検査する。quantile学習へ変更しない。既読の探索的研究で未知holdoutとは扱わない。

許可済みFIT10店/2013–2015のみ。休業相当01-01/12-25・営業unknown・raw0/nullを維持。mean28は同じ休業maskを適用したmatched_mean28。過小量は全ての完全14日窓を分母とするmax(実績総量−予測総量,0)の平均（販売数量単位）、10店等重み。過小窓だけの平均ではない。

上方制約: 各候補は B + 非負係数 * 非負方向、休業相当日0。全日予測>=Bをlabel読取り前に検査する。この構造から、任意の完全総量labelについて各店舗/各窓の過小量がB以下となる（観測only/欠測0仮定とも成立）。欠測窓の観測only総量は採点しない。過大/MSE/平均biasの改善はこの保証から導かない。

事前候補順 matched_mean28 / upward_ridge / seasonal_uplift / newyear_uplift。raw ridge/過去inputs/最終stateは閉鎖macos-demand-seasonal-quantity-20261015をread-only再利用（2013尺度/72列/lambda.01/2014内過去26fit/2015前最終250完全窓/last label2014Dec16）。新ridge/NN学習なし。source/fullstate/closureを新rootへ保存し、新係数を2014以前だけで求める。

upward_ridgeの方向はmax(raw_prediction−B,0)。2014奇数k校正130窓の観測onlyでBを基準に、alpha[0,1]をjoint二次式の解析解と日次/完全総量各MSE非悪化上限から一度固定する。欠測を0とした校正はしない。seasonal_upliftは旧2014校正だけで学習済みの四半期delta_qを固定し、max(open_mean28 + delta_q*2013尺度*openmask−B,0)を方向とする。旧deltaはQ4=0。新period/lambda/倍率gridなし。

newyear_upliftはseasonal_upliftを固定イベント区間12-26〜12-31/01-02〜01-14だけに適用、それ以外はB。元日/Christmasは休業相当0を維持。イベント専用倍率はfitしない（2014交互校正にJan2〜14の直接支持がなく、そこから架空の局所係数を求めない）。正月後は校正Q1の数量水準を移す仮説として、元日2014を含む独立した方式選択130窓で検査する。年末Q4=0でも、open_mean28による差があるときだけ上方修正できる。12月は原全季節評価のtarget内を含み、元日より前のcontextも維持する。

2014は前契約と同じJan1+14*k/k0..25、奇数130校正/偶数130方式選択。校正係数と方向を保存してから選択。候補適格条件は、選択130全窓及びそのJan1の10窓の両方で、非休業仮定日の観測数量MSE・完全14日総量MSE・平均過小量が同仮定mean28以下（tolerance1e-12）。同じ条件を観測only/固定休業欠測0仮定の別評価で表示・確認し、原ラベルは維持する。この選択群に欠測がないことも支持を明記する。適格候補の観測only joint最小、tie1e-12順序優先。baseline常に適格。四季と年末の成績も表示し、全四季の非悪化保証と誤称しない。2014末回顧の交互分割/context依存/同暦10店1年の元日支持を明記する。

方式/alpha/delta/元stateを2015予測作成より前に保存。2015入力だけ閉鎖sourceから読み、全候補を作って全260窓のpointwise>=B/休業0/元日前日までの入力を検査・保存した後に2015labelを読む。原250窓と元日10窓は別（20店日重複合算なし）、観測onlyと休業欠測0仮定も別。2015数量・総量MSE/MAE/bias/過小量/過大量と同仮定mean28差を報告。2015後の主昇格/倍率調整なし。改善してもPSI採用認定なし。

fresh macos-demand-shortfall-quantity-20261015、execution/readback/doc-records。全stdio/exit/source/state/closure/失敗prefix/非増加の予測証明とlabel結果を保存。親900/子870秒/Mac sampled physical footprint・peak RSS各2GiB。artifact通常24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。旧変更/失敗/closed roots保持。2016–17/予約31–54/販促/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/追加agent/本番採用なし。Mac共通検証とWindows固有/OS依存未実行は別報告。heartbeat PAUSED保持。この有限比較を実装・検証・文書保存まで完了する。
