# 丸め差付き比例配分・floor到達の人工接続事前契約

2026-10-16 JST。実学習と2015参照再評価を停止したまま、前回の制約付き非ゼロ解から未到達だった日次分岐を補う。旧変更/source/失敗/closed rootsは保護し上書き削除しない。実source/problem/quantity/labelは内容decodeせず既存保護hashだけ確認する。

## 係数と人工入力の固定

前回`macos-demand-active-pipeline-artificial-20261016`の四季正負8stateを、そのcompiled problem/certificate/独立proof/input pinsとともに再利用する。すべてrank3・全3係数非ゼロ・元hinge正dual/gap0で、非制約uから異なる制約解である。新consumer compile/solver/学習は0回。係数・λ1・τ1/20・p32・元E/I/w-vは変更しない。外側artificial_prefix_fit_performed=trueは係数の過去の人工学習由来、今回の新fitを意味しない。nested fit_performed=falseもpure bridge内でfitしない局所flagとして保持する。

同一transforms/scale10/同休業mean28・fixedmask/unknownを保持し、inputだけに次の2人工historyを使う。発行前56日を最古から並べる。

| kind | uniform past56 | weekday past56 |
|---|---|---|
| rounding | .025/.05/.075/.125 各14日 | uniform各値+weekday/1024 |
| small | 10/12/14/16 各14日×2^-20 | (uniformの係数10/12/14/16+weekday/1024)×2^-20 |

roundingはmean28約.1（weekdayでは曜日差あり）で、canonical B=F(math.fsum(baseline))とexact E=ΣF(baseline)が異なること、P>0かつdelta!=0、正しい比例分母Eを要求する。smallは全数量を2^-20にした相対履歴でr>0を維持し、positive stateの負interceptによりrawP<0、P=0、floor_applied=true、全日次0を要求する。negative stateはP>0の対照。丸め前rawPを保存し、floorを学習時raw非負可行性の証明にしない。rawPちょうど0の到達や境界付近の連続性は今回要求しない。

発行日は2014-01-01/03-26/04-02/07-02/12-17、各FIT10×正負×uniform/weekday×2kind、計400予測。全targetは2014内、03-26の4月targetもQ1。元日のpast14はChristmasによる旧unsupportedなので80件をcopy対照とし、残り320でrounding比例160・small正80floor/負80比例を要求する。全Q・両profileに成立を要求し、不成立はfailedとして保存し探索や再調整で救済しない。

## 接続・検査・評価

既存consumer/solver/encoder/connector/bridge無変更。旧root/全state/pinsの再利用bindingを新予測前freezeし、既存connectorの独立証明検査から同Q/利用可能cutoffのbetaだけをinput-only旧bridgeへ渡す。全source/input/proof/legacy/pinsを保存。全400予測freeze後に評価labelを作る。

rounding比例ではE≠B、exact日次=baseline_j*P/E・exact和P、非均一配分の比例性、Bを分母に誤用した値との差を厳密確認する。B/Eの差・表示値と表示fsumとcanonical差を保存し、表示をexact値と混同しない。floorではstrict negative rawとmax(raw,0)、delta=-B、全日次/表示0・閉鎖日0を確認する。nonfloor対照とcopyは別に集計する。

各inputで週項/制約差をraw式として保存する。floor後の日次へraw寄与の線形等式を拡張しない。制約差はunit*z·(beta-u)、raw-unconstrained_rawと一致させる。これはuでのconnector再実行でない。B≠Eの比例配分ではrawP=Pとして、日次=baseline_j*(B+各項和)/Eを確認する。copyではexact baselineをそのまま保つ。

固定canaryは任意beta/issue label/未来/別Q/cutoff/problem/cert/state/target/proofの元12接続改変に、保存uへのcert差替え1、配分分母Bへの改変とfloorの未clip値への改変の直接2検査を加え計15拒否。I/O canary追加1件は400予測と別に数え、指定関数のopen各0と出力一致を確認する（OS sandboxではない）。

store6の40予測にmatching_truth/baseline_truth/open_missing、休業あり16予測にclosure_missing/positiveも付け152scenario。matching_truthは営業相当日max(baseline±1,0)、休業0の人工stress規則。営業NoneはNone、営業0と休業正値を保持し、観測のみ/休業相当Noneだけ0仮定を別に検証する。baseline真値でunder/overが悪化する反例も保存。実10店四季性能ゲートではない。

独立readerはconsumer/solver/encoder/connector/bridgeをimportせず、旧人工prefix→rank/全encoder/r-z/元ledger/重み/別2×2 oracle/元facet/J/KKT/gap0を再構築したうえで、新input生成式・名前集合/長さ/strict型/有限非負/正scale/曜日support・全400日次と152label両modeを別実装で照合する。全freeze/再利用pinと過去の保護root/sourceを確認する。runtime max_bits値そのものの一致は主張しない。

## 保存・停止条件

各親900/子870秒、Mac sampled physical footprint/peak RSS各2GiB、整数形成/比較8192bit、既存有限solver上限を維持。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiB。全source/reusedstate/pin/input/raw/floor/配分/日次/label/stdioexit/state/partialfailure/resources/closureを保存。Astraが起動前と結果を確認する。

調整2014以前、自Q共有λ1、四季all/normal・元日両modeの平均under/over・総量MSE非増加/annualMSE厳密改善、同休業mean28/元支持/観測と欠測0仮定の分離は不変。実性能ゲート・将来非悪化・PSI採用は認定しない。実のrank/集中/開始AND条件を緩和しない。

real_fit/real_problem_decoded/new2014_scores/new2015=false、fit_ready/can_launch_learning=false、heartbeat PAUSED。2015参照再評価/実学習/実予測/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/Windowsnative/OS依存包括suite/採用なし。人工検証から実適用へ自動接続しない。
