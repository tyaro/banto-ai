# 2014時系列分離選択・2015の10店すべてで改善、2%目安未達

2026-10-15 JST。[実行前契約](../research/demand-temporal-selection-design-2026-10-15.md)に従い、一軌跡と一回の固定2015評価を完了。2014前半inner60でNN checkpointと各補正係数、後半outer50で方式を選択した。主はrolling校正、2015 jointはmean28比1.811781%改善、10/10店・4四半期で改善。日次/総量MSEとMAE/WAPEも改善するが、暫定2%目安未達・PSI採用false。既読開発の探索的検証で、未知性能や有意性を主張しない。

## 選択と時点境界

許可済みfit10店(6,7,10,13,15,17,19,23,26,27)/300fit、原尺度u、暦42支持、56→14日を保持。time120の全label末日<2014-10-01のinner60、origin>=境界のouter50、跨ぎ10は選択外。新NNは原初期stateと全tensor一致、30369parameter/seed20261014/原optimizer・300から8件×4096上限の原sampler。更新1408でinner停止、inner厳密最良640を固定。Cやouter50をcheckpoint監視に使わない。NN計算はfloat32、検証/校正は原quantityと尺度をfloat64で集計した。

inner60 alphaはNN 1.0000000000000000、rolling 0.2063357718495031（日次非悪化上限0.3849226803005874）。後半で再校正しない。outer50のjoint最小/tie順mean28→NN→rollingを固定。旧NN3328は比較だけで、outer選択に含めない。

| outer50方式 | 日次scaled MSE | 総量scaled MSE | joint |
|---|---:|---:|---:|
| baseline | 0.110653800226 | 0.031120064999 | 0.070886932612 |
| nn_calibrated | 0.108568349931 | 0.029398578121 | 0.068983464026 |
| rolling_calibrated | 0.107090944245 | 0.027850736354 | 0.067470840300 |

最小rolling_calibratedを2015 snapshot解釈前に保存。frozen-selectionのouter_used=false/development_used=falseはfrozen-innerから継承されたNN/checkpoint/alpha固定時の記録であり、方式選択はselection_period=2014 outer50 only及びscoresに示す後半50窓を使った。development_used_for_selection=false、crossing_used_for_selection=false。

rollingは旧closed rootの因果的365日/lambda0.01/72列の37stateを再利用し、新ridge fit0。各originのpoolを670headerから再照合し全label末日<発行日・各店均等支持を確認。跨ぎpacketは10月7日以降の過去完了fitのみ利用。2015はpast-only特徴へ閉鎖stateをforwardし、新inner alphaを適用。旧alpha0.5934170450546611で旧rolling_fixedを再構成した最大差0.0、旧alphaを新選択に使わない。

## 固定2015評価

2015-01-13から14日間隔25origin×10店=250要求、各店349観測日/24完全総量、合計3490日/240完全総量。Christmasの欠測をnull保持し13日総量に置換しない。全予測をlabelなし保存後に原actualを付与した。

| 方式 | 日次scaled MSE | 総量scaled MSE | joint | mean28比改善 | 改善店舗 |
|---|---:|---:|---:|---:|---:|
| mean28 | 0.134053954571 | 0.020878675703 | 0.077466315137 | 0.000000% | - |
| 主rolling（inner alpha固定） | 0.132506798845 | 0.019618791454 | 0.076062795150 | 1.811781% | 10/10 |
| 新NN640（事前副比較） | 0.133065531395 | 0.020050418095 | 0.076557974745 | 1.172562% | 7/10 |
| 旧NN3328（比較のみ） | 0.133491411548 | 0.020265515764 | 0.076878463656 | 0.758848% | 7/10 |

日次/総量scaled MSE非悪化・支持不変=true、改善1.8117810108507548%<2%、development_progress=false/business_adoption=false。前回の全time120校正rolling副評価2.357761%を今回の主結果と混ぜず、係数/方式を2015で合わせ直さない。小さい補正で全店/四半期が改善したことは記述できるが、分離選択の因果効果は未同定。

| macro副指標 | mean28 | 主rolling | 旧NN |
|---|---:|---:|---:|
| daily_MAE | 48.845588649 | 48.428857454 | 48.983572680 |
| total_MAE | 328.732636813 | 314.545816713 | 341.514018303 |
| daily_WAPE_percent | 17.067803322 | 16.960160066 | 17.228645969 |
| total_WAPE_percent | 7.852857053 | 7.564897374 | 8.145699047 |
| daily_bias | 1.179059349 | -0.102876029 | 0.669372233 |
| total_bias | 3.764422340 | -14.990657501 | -1.234698048 |

biasはprediction−actual。主はmacro日次約−0.103、総量約−14.991で過小側に移動。MAE/WAPEは等店舗macroで、全店量を合算したWAPEではない。店舗13は日次MAE/WAPEが小幅悪化するので、全店joint改善を全副指標改善と言い換えない。

| 店舗 | mean28 joint | 主rolling joint | 旧NN joint | 主改善 |
|---|---:|---:|---:|---:|
| 6 | 0.030615689834 | 0.029626654828 | 0.030298146902 | 3.230484% |
| 7 | 0.035496020747 | 0.033473977444 | 0.032189971123 | 5.696535% |
| 10 | 0.044967569176 | 0.044513738767 | 0.046810447825 | 1.009239% |
| 13 | 0.473769593958 | 0.469202059963 | 0.472987845623 | 0.964083% |
| 15 | 0.030465331000 | 0.029974107039 | 0.032012695798 | 1.612403% |
| 17 | 0.039808442892 | 0.038163718007 | 0.037197827252 | 4.131598% |
| 19 | 0.038493684175 | 0.037781111769 | 0.032742124248 | 1.851141% |
| 23 | 0.017402618728 | 0.016909729137 | 0.017400711544 | 2.832273% |
| 26 | 0.034396222704 | 0.033051799381 | 0.038770566654 | 3.908637% |
| 27 | 0.029247978158 | 0.027931055162 | 0.028374299592 | 4.502612% |

| 四半期（発行originで分類） | mean28 joint | 主rolling joint | 旧NN joint | 主改善 |
|---|---:|---:|---:|---:|
| Q1 | 0.194912419323 | 0.192702466262 | 0.190971474928 | 1.133818% |
| Q2 | 0.044230547576 | 0.043635684774 | 0.044377075232 | 1.344914% |
| Q3 | 0.037737245269 | 0.036558435358 | 0.037673429864 | 3.123731% |
| Q4 | 0.037196701935 | 0.035412037861 | 0.038769654828 | 4.797909% |

前回全time120校正ではQ2悪化だったが今回inner校正ではQ2も改善。Qごとの窓数・欠測支持は違うため四半期jointを単純平均して年間値としない。

## 保存・検証と次の工程

artifacts/macos-demand-temporal-selection-20261015は20files/4,972,087B/complete。contract/source/config/binding/fit-inner profile/sampler/initial/final/inner-selected state/全1408更新journal/0–1408のcurve/frozen inner/frozen outer/50outer予測/250dev profile/raw予測/label前後予測/summary/closureを保持。同execution-recordsに7個の新境界fixtureとunitの全stdout/stderr/exit0、親source/root前後照合を保存。

同readback-recordsはcomplete、独立scalar式でinner60のalphaと最良loss/outer50のMSEと選択/10店・年間2015MSEを再集計。新stateをstrict loadしinner60だけforwardしてstate/loss/alphaを読戻し、原initial全tensor一致・原sampler全4096batch一致・37過去pool・250label前後固定・3490/240支持・原4root/source不変を照合。新fit/選択再実行0。doc-recordsで文章値/links/closure/Git差分空白を確認する。

child 9.703434秒/親15.313981秒、Mac sampled peak physical footprint 325,501,864B、peakRSS 356,794,368B。親900/子870秒・各2GiB・保存上限以内。sampled checkpointでhard OS capではなく、Windows private bytesとの同等性を主張しない。NumPy未導入のTorch警告はstderrに保存、今回のtensor処理は成功。

共通CPU需要研究と新架空7確認をMacでpass。Windows native機能とOS依存包括testは新実行0/未検証で分離。2016–17、予約31–54、販促数量、正式holdout、CARE、新取得、外部送信、Git push、削除、追加agentを行わない。製品採用0、既存変更/原失敗/closed rootsを保持、Mac未commit。

次は新模型を増やさず、保存した250予測の改善が少数店・発行窓に依存していないかを固定条件で診断する。各発行originを10店まとめて対応付け、店舗一つずつ除外、origin一つずつ除外、56日(4origin)blockのpaired resamplingを事前契約から一回実施する。選択/alphaを変更せず、既読開発内の記述的な頑健性だけ報告する。PSIの業務損失・入荷・在庫条件が未指定であることは残る。heartbeat ACTIVE、routine質問なしでこの次工程を継続する。
