# 許可prefix受渡しと2014共通残差モデル一巡：追加改善なし

2026-10-15 JST。人の「続けてください」に基づき、入力境界後の[許可prefix受渡し・支持監査](../research/demand-prefix-adapter-design-2026-10-15.md)を実装・独立照合し、その後に[単一仕様契約](../research/demand-common-residual-design-2026-10-15.md)を凍結して2014だけの一巡時系列診断を行った。学習支持は210/250/310/380窓へ広がったが、全季節の発行前alphaが0となり、260予測は同休業mean28と完全同値。追加改善は得られなかった。

[Astra設計・結果確認](../research/demand-common-residual-astra-review-2026-10-15.md)でも、支持拡大と予測力を区別し、過去校正での停止をouter後差替えや支持消失と混同しないことを確認。独立readerも完了した。λ・特徴・期間を結果後に変更せず、予定した一巡で終了した。2015新内容参照・学習・予測・再評価はない。

## 学習関数へ渡すデータと固定2特徴

[adapter](../../tools/demand_prefix_adapter.py)は、cutoff時点のaccepted keysだけを通知する形から、許可された具体的な過去row・ラベル・必要変換だけをfresh payloadへコピーする形へ進めた。fit関数はそのpayloadだけを受け取り、全470入力・全label reader/index・元ファイルpathは受け取らない。別childのconsumerチェックではprefix以外のPath.openを禁止した。非許可future rowのcontextを整合的に変えた4カナリアでも、許可payloadは完全不変だった。Python/OS sandboxではない。

固定特徴はx=(1,(T7−B)/(14u),2*(latest7−previous7)/(14u))。T7は最新7日の曜日値を未来14日open仮定maskへ反復した総量。過去14日が全て観測・非休業相当、B>0だけ適格。真0は有効、欠測/01-01・12-25はinput fallback。未来ラベルの欠測では発行適格性を変更しない。

| Q開始cutoff | 完全ラベルprefix | feature適格 | 適格な40店Qcellの最少窓 |
|---|---:|---:|---:|
| 2014-01-01 | 210 | 210 | 3 |
| 2014-04-01 | 270 | 250 | 5 |
| 2014-07-01 | 330 | 310 | 5 |
| 2014-10-01 | 400 | 380 | 5 |

2014発行260のうち特徴適格240、Jan1/Jan15の20窓は入力fallback。窓数・40cell・共有する履歴は独立標本数や信頼性の保証ではない。特徴支持の結果から期間/λ/特徴を選び直す工程は行っていない。

## 成績前に凍結した一仕様

年特徴/成功gate/店季節偏差なしの共通3係数。対象r=(Y14−B14)/(14u)、Q×店cell内適格窓数n_qsに対してw=1/(4*10*n_qs)、和1の残差MSE＋λ=1*全係数二乗（切片含む）。全40cell支持がなければ全betaベクトル0/B、数値解失敗はfailure停止。uはcutoff以前のfull2013尺度で、2013当時の予測再現には使わない。

各Q開始だけbetaをfitし、過去の同Q全complete窓からalphaを決める。R=max(B+14u*xβ,0)を先に作ってD=R−B、P=B+alpha_q D、日次はB比例。alphaは同じD/集合/店等重みからの総量MSE・平均under・平均over非悪化区間内のC/A。D=0fallbackも分母に残す。betaと同じラベルによる内部最適化で独立校正ではない。

先行Qの確定ラベルを次cutoffの固定fit規則で使うことは許可し、同originの未到来targetは利用しない。全4state/全260予測を採点前に保存。outerの結果を見てそのQをBへ置換しない。

## 非ゼロbetaは推定できたが、同季節の過去riskが停止

| Q | beta 切片 / 水準差 / 週変化 | 同Q過去complete / 非ゼロD | 適用alpha | 停止理由 |
|---|---|---:|---:|---|
| Q1 | 0.001579708174 / 0.001741629069 / 0.001459624392 | 30 / 30 | 0.000000000000 | 過大量上限0 |
| Q2 | -0.001180381367 / 0.001425442581 / 0.001599983032 | 60 / 60 | 0.000000000000 | 過小量上限0 |
| Q3 | -0.000758647265 / 0.001190016309 / 0.001015980187 | 70 / 70 | 0.000000000000 | 過小量上限0 |
| Q4 | 0.004054725884 / 0.002918177280 / 0.003282516217 | 50 / 50 | 0.000000000000 | MSE上限0・過大量上限0 |

全4モデルは構造的支持を満たし非ゼロbetaを推定した。以前の2点支持や支持消失ではなく、推定した固定方向が過去同季節の三条件を通らなかった。次は独立readerが保存journalから求めたalpha=0右側の平均数量risk微分。

| Q | alpha開始点の過小量微分 | 過大量微分 | C（MSE改善方向） |
|---|---:|---:|---:|
| Q1 | -3.430182699 | 2.191879420 | 6.67097847729e-05 |
| Q2 | 2.269348126 | -1.700010373 | 4.54142496964e-06 |
| Q3 | 1.195606917 | -1.808754952 | 9.01822898722e-06 |
| Q4 | -5.560580196 | 10.008183996 | -0.000116753600711 |

Q1はover、Q2/Q3はunderが、alphaを正へ動かす開始点で増える。C>0でMSE改善方向でも両側条件を満たせない。Q4はC<0で正alphaはMSEも悪化する。これらの固定Dに対し、幅をさらに小さくするだけでは厳密な非増加を回復できない。別の特徴/λ/方向一般が不可能という意味ではない。

## 2014観測のみ・欠測0仮定を分離、全260予測を保持

次表は候補と同mask mean28が完全同値だった2014の値。日次数量MSE/総量MSE/平均under/overとも同値で、paired差は全群0。eligible=trueは非悪化条件の同値充足であり、追加改善や学習モデルの予測力の証拠ではない。

| 2014群 / label | 採点日 / 完全総量 | 数量MSE | 総量MSE | 平均過小量 | 平均過大量 |
|---|---:|---:|---:|---:|---:|
| all260/assumed_missing_zero | 3640 / 260 | 0.094337148064 | 0.024679842358 | 203.551222359 | 147.345141122 |
| all260/observed | 3630 / 250 | 0.094337148064 | 0.023472177931 | 205.258387253 | 132.322898507 |
| normal250/assumed_missing_zero | 3500 / 250 | 0.093001268930 | 0.024452580340 | 188.188366040 | 150.502946767 |
| normal250/observed | 3490 / 240 | 0.093001268930 | 0.023185127311 | 189.326543792 | 134.986352611 |
| newyear10/assumed_missing_zero | 140 / 10 | 0.130200364813 | 0.030361392809 | 587.622630333 | 68.400000000 |
| newyear10/observed | 140 / 10 | 0.130200364813 | 0.030361392809 | 587.622630333 | 68.400000000 |
| Q1_all/assumed_missing_zero | 980 / 70 | 0.109454587999 | 0.012602158510 | 202.486397048 | 97.468387524 |
| Q1_all/observed | 980 / 70 | 0.109454587999 | 0.012602158510 | 202.486397048 | 97.468387524 |
| Q2_all/assumed_missing_zero | 840 / 60 | 0.049764233366 | 0.008466906356 | 163.811141833 | 90.480449833 |
| Q2_all/observed | 840 / 60 | 0.049764233366 | 0.008466906356 | 163.811141833 | 90.480449833 |
| Q3_all/assumed_missing_zero | 980 / 70 | 0.099253641202 | 0.044899171222 | 303.945763857 | 114.974957000 |
| Q3_all/observed | 980 / 70 | 0.099253641202 | 0.044899171222 | 303.945763857 | 114.974957000 |
| Q4_all/assumed_missing_zero | 840 / 60 | 0.115974700272 | 0.031394192508 | 127.406634000 | 300.164593083 |
| Q4_all/observed | 830 / 50 | 0.115974700272 | 0.026698740401 | 120.713540800 | 255.617270400 |

通常250と元日10は2014の別群で、旧2015の250窓成績とは別。Q別normal、年末の値もartifactへ保存し、元日を外した成績で悪化を隠さない。原0/null・営業unknown・休業相当01-01/12-25を維持。欠測0仮定は休業相当位置だけの別採点で、学習targetに使わない。

入力未支持20窓はB、残り240窓も発行前alpha0によりBとなった。outerを見たB差替え0、変更予測0、追加改善0。今回の候補を既存方式へ採用・置換しない。Bの実用安全性や独立性能も認定しない。

## 検証・保存・終了

新prefix10fixtureとmodel8fixture pass。prefix独立readerは具体的受渡row/固定特徴/4非許可rowカナリア/consumer読出し境界を照合。common独立readerは別のGauss-Jordan解法で4正規方程式、厳密有理数の二分探索で16alpha上限、全260予測、両labelの48群scalarとpaired三条件、旧source-state-closed roots/失敗不変を確認。最大beta差8.6736173798840355e-19、上限差0、alpha差0、予測差0。

passは固定仕様どおり計算した確認であり、将来性能や独立性を検証したものではない。実着荷時刻/timezoneは以前からの日単位仮定のまま。既読2014で独立性は回復しない。

| 保存root | files / bytes | child秒 | footprint / peak RSS bytes |
|---|---:|---:|---:|
| macos-demand-prefix-adapter-20261015 | 14 / 2,753,845 | 7.254308 | 171,606,808 / 211,877,888 |
| macos-demand-common-residual-20261015 | 13 / 2,987,556 | 2.747268 | 169,984,768 / 210,829,312 |

全stdio/exit/source/旧state/4新state/closure、負結果を保存。親900/子870秒/footprintとpeakRSS各2GiB/既存artifact・EvidenceStore上限内。OS hard limitやWindows private bytesではない。旧変更/失敗/閉鎖root（前回のGit文書検査failed含む）を保持。

共通Mac/Python3.14.8はadapter・一巡診断・独立reader・文書整合pass。Windows固有/nativeとOS依存包括suiteは未実行（Mac resource計測のみ）。文書diff検査は前回確認済み同梱Git2.53.0を明示し、Xcodeライセンス/設定変更なし。未commit/push/削除/採用。2015新内容参照・fit・予測・再評価0、2016/17・予約31–54・販促・正式holdout・CARE・課金API・新取得・外部送信なし。

本一巡は完了。支持を広げる受渡しと共通推定は実装できたが、指定risk条件下でこの固定補正を有効に使うことはできなかった。規則・λ・特徴・期間を救済調整して同outerへ戻らず、新候補/2015確認へ自動接続しない。heartbeat PAUSED、PSI採用なし。別の研究を開始する場合は、この負結果と既読期間の再利用を引き継ぎ、別仮説と評価契約が必要。

証拠: [prefix](../../artifacts/macos-demand-prefix-adapter-20261015/summary.json)、[prefix execution](../../artifacts/macos-demand-prefix-adapter-20261015-execution-records/root-closed.json)、[prefix readback](../../artifacts/macos-demand-prefix-adapter-20261015-readback-records/root-closed.json)、[model](../../artifacts/macos-demand-common-residual-20261015/summary.json)、[execution](../../artifacts/macos-demand-common-residual-20261015-execution-records/root-closed.json)、[readback](../../artifacts/macos-demand-common-residual-20261015-readback-records/root-closed.json)、[doc-records](../../artifacts/macos-demand-common-residual-20261015-doc-records/root-closed.json)。
