# 店舗移行に合わせた学習終了点の選択 — 一軌跡比較（2026-10-14）

人の「次のステップに進んでください」を受け、Astra案Bを具体化する。保存補正の診断では補正負担に対する実績整合不足が分かったが、原因は未同定。本試行は終了点選択と店舗移行の目的を合わせる研究である。診断が選択過適合を証明したための修正とはしない。

## 問い・店舗・時間

同じfamilyの正尺度店舗について、学習していない店舗へsales平均予測を移す限定的な開発評価。潜在需要、費用最適化、PSI採択は別問題。元positive15のID交互分割を固定する。

- A={6,10,15,19,26}、B={7,13,17,23,27}：計10店舗だけでparameter fit。
- C={9,14,18,25,30}：parameter fitに使わず、移行validationと終了点選択に用いる。
- 各店の元42起点を維持。label末尾が2014-07-01より前のA+B各30窓、計300をfit。2014後半のA+B各12窓、計120を時間validation、C各12窓、計60を移行validation。
- Cの前期150窓はparameter fitから外す。Cの自己過去観測と前期尺度は入力に使える。C後半labelは内部選択にだけ使用。
- 学習/検証境界を跨ぐ窓は保存して除外。現元keyでは0を期待し、store/dateを入れ替えない。

2013Jan〜2014Junだけの既存自己尺度uをpin再利用し、尺度・評価分母・履歴長・label支持を変更しない。zero-scale店は学習対象外。名目60暦の支持はA+Bのfit300窓だけで決め、C又は外部評価で追加しない。元630key、前期尺度、過去統計8encoding、2013–14小snapshotは閉鎖学習rootからpin再利用。原ZIP/新quantity抽出/過去統計再集計は0。

## 一候補・一学習軌跡・二保存点

統計8入力ありのStatisticalFeatureMean（30369params）だけを使用。これは既読開発で選んだ候補で、統計入力効果の再検定ではない。新initial、seed20261014、固定sampler4096×8、各fit窓を等確率で抽出（各店30窓なので店も等確率）。旧weightsの延長0。CPUfloat32/2threads/interop1/deterministic、joint loss/AdamW lr3e-4/betas(.9,.999)/eps1e-8/weight_decay.01/gradnorm1を固定。

0stepと128stepごと、固定train300/time120/transfer60を全件eval/no_gradで測る。日次MSE/u²と14日総量MSE/(14u)²を.5ずつ、各群の店舗を等重み平均する。0stepのbaselineも候補。全測定点で時間validation最小stateと移行validation最小stateを別々にcloneする。

最大4096、停止猶予512、相対0.01%超の意味ある改善なし6回で停止。停止は**Cの移行validationだけ**で決める。停止猶予はlearning-rate warmupではない。時間validationはもう一つのclone選択だけで、停止/延長を左右しない。時間選択最良もCが止めた同一軌跡内の最良で、独立した時間選択の停止手順全体との比較ではない。

同じ軌跡の二cloneは、fit条件・initial・更新・入力が共通で選択点だけが異なる。旧15店fitとの違いにはfit店舗数もあるため、旧結果対新結果を選択方法だけの因果効果としない。単一seed・単一splitで一般化や収束を認定しない。

## 二clone固定後の既読開発

保存time-selected/transfer-selectedを固定しsource/weight pinを保存した後、元評価6店4/8/16/20/24/28、2015Jan13＋14*k（k=0..24）へ各一回適用。両stateが全tensorで同一なら予測を再利用して二度forwardしない。新選択点の予測であり、完成した旧weightの再評価ではない。

入力は閉鎖済み店舗評価の2014-11-18〜2015-12-28小snapshot、前期尺度、保存過去profile/8encodingをpin再利用。各input getterはorigin前56日だけ、暦支持は新fit300だけ。各baselineは原保存値との一致を確認。全150予測をlabelなしで保存した後に、別label経路で実績を添付する。新profile作成、原archive/新量抽出、2016/2017/予約31–54/登録holdout読取り0。

positive5は各入力25/25、完全label24/25を期待、最低各20/25。日次観測labelと完全14日総量を分け、Christmas欠測6窓を要求に残す。店20はu=0のbaseline-only25要求を保持。主模型は移行選択clone、主基準mean28。時間選択cloneとの差は補助。同じfixed positive5に対して元joint、日次・総量、原単位Bias、適用率、店別・四半期を併記する。

## 事前の研究判断と限界

次の限定した安定性確認へ投資する暫定目安を、移行選択cloneのmacro jointがmean28比2%以上改善、日次・総量とも悪化なし、適用支持低下なしとする。2%はAstraが提案した任意の開発打切り基準を本試行で採用するもので、実務価値/検出力/PSI費用から導いた数値ではない。変更して成功へ補わない。

店別paired差、固定四半期差、各1店舗を外したmacro差の範囲を集中の記述として併記する。最後の値を採択や信頼区間に使わず、実際の主対象は全5店のまま。店舗別損害も全表示。原4/5条件を過去へ遡及変更しない。0–2%改善は「小幅で次投資の根拠不足」、悪化/副条件未達は「今回の候補未達」。未知優位/統計的有意性/正式受入/製品採択は主張しない。

2015とCは既読なので、選択手順を改善しても未知確認にはならない。達成時もseed/split/gridを自動追加せず、残る不確実性に合わせて次の一手を人と判断する。全店refit・checkpoint延長・補正倍率・尺度/モデル幅/event/LR変更を混ぜない。

## 記録・停止

新group分離・時間境界・二選択点・Cだけの停止・非有限拒否・暫定判断/支持を少数架空fixtureで一回確認。source/契約/使用pin、300/120/60key、未使用C150key、尺度/fit支持、input ledger、initial/sampler、全curve/journal、best2/final、label前予測/label対応/失敗を新local rootへ保存。全child stdout/stderr/exit又はtimeout観測prefixは別EvidenceStoreへ判定前保存する。

実行900秒/private2GiB/output1GiB/single32MiB/32files（normal24file768MiB/failure8file256MiB）、記録16MiB512files/part256KiB/reserve2MiB16files、prep128KiB16files、Git各batch512KiB16path/stdout1MiB/累積30秒維持。script/失敗/closureも新書込み前に件数とbytes確認。原閉鎖root追記0。入力/容量/停止で原prefix/exceptionを保全してPAUSED、盲目的再試行なし。

人の再開指示により今回direct ACTIVE、automation PAUSED維持。新学習と固定開発の一報告でdirect PAUSEDへ戻す。追加agent0/CARE手動待ち、formal_permission=false/credit0/native7役禁止/登録holdout未読/正式受入未完了。Git独自source/架空fixture/集約docsだけ、原quantity/profile/尺度/ledger/予測/weights送信0。
