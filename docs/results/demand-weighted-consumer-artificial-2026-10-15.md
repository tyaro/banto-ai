# 学習consumerの問題生成・β0 baseline再現：人工検証完了

2026-10-15 JST。[事前契約](../research/demand-weighted-consumer-artificial-contract-2026-10-15.md)、[出力復元の補記](../research/demand-weighted-consumer-output-recovery-2026-10-15.md)、[Astra確認](../research/demand-weighted-consumer-artificial-astra-review-2026-10-15.md)。

**人工27問題・5 replay、107check・期待拒否27件が通り、独立readerの1,270行・28,809比較が一致した。β0で同休業mean28を再現し、元分母と過小・過大の非増加制約を確認した。consumer_artificial_ready=true。学習と2015再評価は停止継続、fit_ready=false / can_launch_learning=false。**

## 実装と固定条件

新しいpure compiler [demand_weighted_problem_consumer.py](../../tools/demand_weighted_problem_consumer.py) は、input・label・weightedを分離した具体payloadから、各季節の10店共有3係数の問題を生成する。旧solver/coreをimportせずsolveも呼ばない。全行のcalendar/FIT10/identity/時点/可用性/固定mask・尺度metadataを数量変換前に検査し、元past56履歴から固定encoder v2のr/z/state pinを照合する。今回の数値は全て人工で、実データや実ラベルは読んでいない。

旧適格Eは旧特徴ありかつB>0、Iはraw観測completeの全行。r0適格は正のwと目的定数に残す。旧不支持・B0はx=None/w0のままIとriskに残す。各店w=1/(10nE)、v=1/(10nI)、λ1は切片も含む3係数に適用する。欠けた店を再配分せず停止する。21削除版はその日を全10店から除き、残存E/Iへ再重みする問題生成。前回の元w固定の幾何診断とは手続きが異なる。

B/YはFraction(math.fsum(日次binary64値))、unitは14*Fraction(scale)。G/rhs/C、h/e、全行の非負normal/bound、元hinge材料・baseline RHS、任意subsetのfacetを生成・保存した。β0ではh/normal/目的・full hingeへ実際に代入して、P=B、slack≥0、各行と季節平均のpaired under/over差0、J(0)=C・正則化0を確認した。全r0でも残差があればG=I、rhs=0、C>0で、行・分母を保持する。

β0の可行性は最適性や改善の証明ではない。activeな2facetでhinge全体を表したとはせず、solverのcut生成・KKT証明は未検証である。

## 人工の確認範囲

| 対象 | 件数 | 確認 |
|---|---:|---|
| 4Q primary | 4問題 | 元E/I、r0・None・B0、正負・ゼロ残差 |
| 全発行日を1つずつ除外 | 21問題 | 全10店同時除外・残存母数への再重み |
| 全適格r0・binary64境界 | 2問題 | 目的定数保持・unitとcanonical総量の丸め差 |
| 2014人工日次replay | 5件 | 観測のみ・休業相当欠測0仮定の分離 |
| 期待拒否 | 27件 | 時点・他Q・重複・欠測・改ざん・母数欠け・8192bit |

全rowの問題/derived/非負/β0配列長、全27問題名と5 replay名の集合、各問題のsupporting facet両side2件と例示6件（空・全・交互subset）を独立readerで検査した。保存値を追認せず、別のchecked Fraction実装で履歴から旧x/r/z、B/Y/unit、母数・目的行列、normal/facet、β0・元hingeを再構築した。state pinは供給pinとの対応を確認し、encoder全stateのmax_bitsまで独立再現したとはしない。

最後の行が未来metadataでも、先行行の数量bombを読む前に拒否した。旧mean28値を1e-12変えても拒否し、許容誤差で異なるbaselineを受理しない。全r0を非ゼロ行だけへ再正規化せず、E欠損もβ0成功へ置換しない。

日次baselineはそのままコピーする。canonical総量と日次exact Fraction総和に差のある26行を検出して別保存し、比例補正しなかった。scale=.1でunitとFraction(14*scale)が異なるfixtureも通した。これは算術上の差の明示で、baseline変更ではない。

## ゼロ・欠測・休業仮定

01-01/12-25休業相当・営業状態unknownを維持し、他の祝日を自動でゼロにしない。営業raw0、休業raw0・正値を保存する。人工replayは2014年の元日と12月の可用な入力で行い、2013変換を2013時点へ遡及利用したとはしない。

観測のみはraw Noneを保持する。欠測0仮定は休業相当のNoneだけ0へ補い、営業Noneはそのまま。休業のみ欠測なら後者だけ14日総量の支持が得られ、営業欠測もある場合は両modeとも総量支持を得ない。営業数量の母数から休業を除き、観測元日0も保持する。各modeのlossはbaselineとβ0コピーで一致した。

学習問題のraw labelはcomplete14日だけ受理し、営業欠測も休業欠測も補完して学習へ入れない。replayのscenario処理を学習入力へ流用しない。

## 記録失敗と復元・資源

初回子プロセスはexit0・全確認passだったが、完全stdout 3,509,389Bがcapture_process既定1MiBを超え、execution-recordsはOutputLimitErrorでfailedとなった。source/全stdio/exit/結果state/失敗closureをそのまま保持した。上限拡張や人工再実行はしていない。保存済み完整stdoutのcaseイベントと最終completeをfresh recovery-recordsへ再構築し、独立readerへ渡した。

人工最大179bit、独立最大179bit。人工child 6.001588秒 / sampled footprint 35,586,552B / peak RSS 48,005,120B。独立reader 14.011644秒 / 37,159,416B / 49,348,608B。各親900/子870秒、Mac footprint/RSS各2GiB、8192bit、既存artifact/EvidenceStore制限内。Mac資源はcheckpointでの観測でOS hard capではない。

全stdio/exit/source/input・binding/全state/partial/failure/resource/closureを保存。旧変更・失敗・source・closed roots・handoff/index旧全文を保持した。初版readerは実行せず保存し、Astra指摘の配列長/集合チェックを独立reader v2で補強した。

## 到達点と次に残る工程

問題生成とβ0の人工確認は完了した。実weighted-label prefixの接続、実際のsolve、非ゼロ係数の日次予測bridge、将来の最大25solve/2014採点は未実行・未検証。人の明示的学習再開指示はなく、今回の完了で開始許可にはならない。次は停止を保ったまま、必要なら実データへ接続しない非ゼロ人工点での日次予測bridgeを別契約で検証できる。

調整2014年以前、同休業mean28比較、四季平均under/over非増加と既存MSE条件、観測のみ・休業欠測0仮定分離を維持する。旧Q1不適格判定を変更せず、2015の参照・再評価なし。heartbeat PAUSED、PSI製品採用の認定なし。

| 実行区分 | 今回の結果 |
|---|---|
| Mac Python3.14.8 共通処理 | 問題生成・β0人工・独立照合pass |
| Mac固有資源観測 | footprint/RSSの記録pass |
| Windows固有/native | 未実行 |
| OS依存包括テスト | 未実行 |

2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit・push/依存lock・Xcode変更/本番採用なし。

証跡：[初回failed（出力完全保持）](../../artifacts/macos-demand-weighted-consumer-artificial-20261015-execution-records/root-closed.json)、[復元complete](../../artifacts/macos-demand-weighted-consumer-artificial-20261015-recovery-records/root-closed.json)、[独立照合complete](../../artifacts/macos-demand-weighted-consumer-artificial-20261015-readback-v3-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-weighted-consumer-artificial-20261015-doc-records/root-closed.json)。
