# MetroPT Mac M1 — 3seed実学習・有限評価

2026-10-16 JST。人のM1実学習・評価の明示指示により、[固定仕様r2](../research/metropt-macos-multiday-protocol-2026-10-16.md)を実行した。目的はTimesFM3参考の自作モデルの実用性検証、第一用途は保全・点検支援（異常の予兆）。[実行前仮説/条件](../../artifacts/metropt-m1-20261016-authorization/prescore-contract.json)を学習前に保存した。

## 結果の判断

**3seed×full/self-onlyは全て4096更新を完了し、全予測保存後の一括採点まで成立した。** fullの集約pinballはself-only比2.105%低く、2/3seedで改善したため、事前規則の「この条件で系列間経路の探索的利点」を満たした。一方、1seedと圧力のpinballは悪化した。

fullのp50 MAEは3targetともvalidationで固定したMA15を下回り、各3/3seedで改善した。単純基準を超える点予測の利点がこの条件で見られた。ただし油温の名目80%coverageは約69.4%で、区間は未校正。故障予兆、正常envelope、実設備一般化、公式TimesFM同等性、製品採用は未認定。

## 固定条件と情報境界

- train 2020-02-03/04/15/16/18/22/25、validation 03-08/18/22、test 03-23/25/26。日時上の完全日を選んだ回顧的な13日、1compressorであり、未知の正式holdoutとは呼ばない。
- 3target/C128/H32/P32、各109,024 parameters、CPU float32。Python3.14.8/既存Torch2.14.0。3初期seed/3独立samplerseed、AdamW、4val時点、train-only尺度、context-only正規化は固定のまま。
- 全8,967/123/123窓を保持し、日内独立、共通支持、日/target等重み。testは各target3,936点、全target合計11,808実績値。重複contextや同一設備・seedを独立設備数へ数えない。
- 各seedのfull/selfは共有初期stateとbatch列。全6構成の選択checkpointは4096で、予算末端が選ばれた。4096を収束・能力上限と解釈せず、この一巡では延長しない。
- 各seedのcheckpoint/baseline選択と全test予測を保存し、[freeze記録](../../artifacts/metropt-m1-20261016/scores/freeze.json)の後にだけtest labelを開いた。先行test成績を後続seedへ返さず、best seedを選ばない。全targetと悪化も保存。

## 機構の比較：full対self-only

固定train尺度pinball、低い方がよい。差率は(full/self−1)。

| seed | full | self-only | 差率 |
| --- | ---: | ---: | ---: |
| 20261016 | 0.213537607 | 0.221820520 | -3.734% |
| 20261017 | 0.205101076 | 0.211557428 | -3.052% |
| 20261018 | 0.219065963 | 0.218039597 | +0.471% |
| seed平均 | 0.212568215 | 0.217139182 | -2.105% |

2/3一致は事前の探索判定で、統計的有意性ではない。異なる単位のMAEは平均せず、上表は固定train尺度で無次元化したpinball。target別の原単位pinballも示す。

| target | full | self-only | 差率 |
| --- | ---: | ---: | ---: |
| 圧力 TP3 | 0.096247894 | 0.095898320 | +0.365% |
| 油温 | 0.901374303 | 0.911738755 | -1.137% |
| 電流 | 0.342689713 | 0.363388378 | -5.696% |

圧力の原単位pinball悪化とseed20261018での悪化を残し、全target/全seedの一様な改善とはしない。

## 点予測：単純基準との比較

fullはp50 MAEのseed平均。3targetとも主baselineはvalidation MAEで選ばれたMA15（testで再選択なし）。last-valueも併記する。改善率はMA15比。

| target | full MAE | MA15 MAE | last-value MAE | 改善率 | 改善seed |
| --- | ---: | ---: | ---: | ---: | ---: |
| 圧力 TP3 (bar) | 0.300552 | 0.560788 | 0.688864 | 46.41% | 3/3 |
| 油温 (℃) | 2.774300 | 4.618036 | 5.272246 | 39.92% | 3/3 |
| 電流 (A) | 1.066700 | 1.843129 | 1.940285 | 42.13% | 3/3 |

各targetで3評価日の日別seed平均MAEもMA15未満だった。日別/seed別/lead別は[全metrics](../../artifacts/metropt-m1-20261016/scores/metrics.json)に保存している。3日だけで季節・故障・欠測条件への一般性を示したとはしない。baselineは一つの固定予測で、seedの独立反復へ水増ししない。点MAEとモデルWISの大小は比較しない。

## 予測区間の限界

fullのseed平均。coverageは端点を含み、missは厳密不等号。幅はtarget原単位。

| target | 名目80% coverage | 幅 | 下側miss | 上側miss |
| --- | ---: | ---: | ---: | ---: |
| 圧力 TP3 | 76.71% | 0.950662 bar | 15.57% | 7.72% |
| 油温 | 69.44% | 7.999962 ℃ | 18.89% | 11.68% |
| 電流 | 79.18% | 3.311378 A | 10.68% | 10.14% |

全targetで名目80%を下回り、とくに油温は不足が大きい。未ラベルの運転/故障を含み得るため、miss率を正常時の誤警報率と呼ばない。区間をそのまま異常閾値へ採用しない。M1のtestに合わせた校正や追加fitは行わない。

## 成立・保存・独立確認

[原結果summary](../../artifacts/metropt-m1-20261016/scores/summary.json)、3seedの全checkpoint/optimizer/schedule/journal/予測/選択、source bundle、全stdio/exit/resource/closureを保存した。[独立検算](../../artifacts/metropt-m1-independent-20261016/summary.json)では保存済みlabel/予測だけから別実装で日重み・MAE/pinball・区間/miss・全lead・両baseline・事前判定を照合し一致した。新しいモデル推論・fitはない。

実学習は3親unitだけ。第3slotは採点も同じ子870秒枠内で完了し、第4学習/採点slotを追加していない。

- 親観測時間：60.159 / 59.545 / 60.789秒、計180.494秒（計上限2700秒）。
- 最大親観測child physical footprint：272,303,064B。最大child peak RSS：315,441,152B。各2GiB以内。

- 通常24file/768MiB・単file32MiB、全体32file/1GiB・失敗reserve8file/256MiB、Evidence16MiB/512file・part256KiB・失敗reserve2MiB/16file、stdout1MiB/stderr128KiBを維持。観測checkpointとOS hard capは別。
- 実行前の記録生成でinline構文エラーがあり、許可file不在の初回起動はauthorize段階でexit1になった。[失敗記録](../../artifacts/metropt-m1-20261016-slot1-records/stderr.txt)を保持。Torch初期化・campaign作成・学習更新は0で、準備を修正後にfresh記録rootから開始した。科学的な候補/seedの再実行ではない。
- 中立形式へのstate書出しと独立数値検算は、学習終了後の保存物処理として別の小さいbounded processで記録した。追加学習・予測・候補探索ではない。

## Rust学習移植へ渡す成果

[全6選択stateのneutral書出し](../../artifacts/metropt-m1-learning-export-20261016/summary.json)を保存した。各stateは240 tensors/1,314,900B。model parameter/bufferに加え、parameter名と対応するAdamW step/一次・二次moment、Torch RNG bytes、学習位置、共通schedule pin、config/source/checkpoint pinを含み、dtype/shape/offset付きで全tensorのunpack値を厳密確認した。選択は全3登録seedの両構成で、良いseedだけを選んでいない。

これはRustで学習/推論を実装・比較する参照資産。Torch RNGはbackend固有のbytesでRust RNG互換ではなく、共通batch scheduleとsampler位置を別にpinした。Pythonでの中断再開やRustのbackward/optimizer/再開を成功確認したわけではない。最終目標は学習を含むRust化とbantoで使いやすいAPI/job/model管理のまま。

## 次工程：保全・点検支援を第一優先に

[CAREイベント評価設計](../research/care-maintenance-evaluation-design-2026-10-16.md)を保存した。次は公式版/利用条件・センサー/asset/時点のmetadata照合から、一候補の入力・asset分割・正常profileとlabel分離・alarm規則・評価条件を固定する。CARE観測/event_info/feature_description payloadは今回は未読、CARE学習は未開始。イベント検知率・正常equipment-hour当たり誤警報・先行時間を主とし、残差警報を実績利用時刻より前へ遡らせない。

このM1のtestは既読評価として凍結し、追加seed、4096超の延長、test校正、期間/targetの差替えを自動追加しない。油圧/XJTU全実験をCARE契約の前提にしない。Rust R0のbackend/API/保存再開契約も独立した次工程として維持。

Mac共通経路の実学習・評価は成立。Windows native/OS依存包括suiteは未実行。需要は調整2014以前、同休業mean28、四季平均の過小量/過大量非増加と既存MSE条件、観測のみ/休業相当欠測だけ0仮定の分離、2015再評価停止を維持。heartbeat PAUSED、新取得/課金API/外部研究データ送信/commit-push/製品採用/追加agentなし。
