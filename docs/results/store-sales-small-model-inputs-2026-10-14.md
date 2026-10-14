# 水準・相対変動とイベント別入力の確認・一回接続結果（2026-10-14）

## 到達点と判断

水準・相対変動を保持する入力とイベント別入力を実装し、新7機構確認、別候補への新3接続確認、一回学習まで完了した。**情報を残してモデルへ渡す経路は成立した。予測方式の採用判断は引き続き保留**とする。

[入力設計](../research/store-sales-small-model-input-design-2026-10-14.md)、[接続・一回評価の出力前設計](../research/store-sales-small-model-input-pilot-design-2026-10-14.md)、[元候補の結果](store-sales-small-model-2026-10-14.md)。

総量誤差と旧候補の区間評価は少し改善したが、日次は限定暦配分基準に届かず、過小偏りも増えた。基準の **mean28総量＋限定暦配分** を維持する。入力2統計・暦・parameter形状を同時に変えた一候補であり、どちらかの入力だけの因果効果や一般性能を主張しない。

## 純粋入力関数での確認

`tools/demand_input_features.py`はTorch/fit/予測/IOを持たない。数量はorigin前56日だけgetし、未来14日は日付から暦を作る。

- 観測平均m / 固定train平均u、population std s / max(m,0.01*u)を保持。欠測を統計から外し、実ゼロを含める。
- 曜日sin/cos・年内sin/cos・名目8イベントone-hotの12要素。実際の営業日・移動休日・販促実施値は使わない。
- distinctな観測train label日の支持数はfeatureに入れずmetadataへ付ける。元日2、他6event各3、Christmas0/店舗。少数事例があることも効果検証済みとはしない。
- 全観測ゼロは有効で統計[0,0]、全欠測は統計null・予測不能。contextに観測があっても過去28日に必要な曜日の支持がなければ、基準を0へ補わず予測不能。

shift例100/200→1100/1200は同じ正規化列でも、追加統計が[1.5,1/3]→[11.5,1/23]へ変わった。8イベントを別channelへ写像し、閏年の年内位相も確認した。future quantity lookupを拒否するmappingでもinput組立が成功し、未来数量先読みがないことを確認した。

新7件は一回all passed（0.005秒）。parserは支持ledgerのcutoff判定前に後年のquantityを読まない。重複store/dateは拒否し、origin反復を支持数へ加えない。

## 保存train入力の組立

2013–15の数量と保存train尺度・支持ledgerだけを使い、3起点でinputを組み立てた。新forecastではない。

| 起点・店舗 | m/u | s/max(m,0.01*u) | 観測context日数 |
| --- | ---: | ---: | ---: |
| 2015-02-01・5 | 1.274264 | 0.230772 | 55 |
| 2015-02-01・11 | 1.017907 | 0.236782 | 55 |
| 2015-02-01・12 | 1.016624 | 0.366469 | 55 |
| 2015-04-30・12 | 0.538950 | 1.170333 | 56 |

最後の行は観測ゼロ区間がcontextに含まれる。ゼロを削除していない。2015-12-20起点の未来Christmasは全店舗 `no_observed_training_labels`、quantity_effect_verified=false、operating_status_known=false。観測不能を休業や販売ゼロの成功へ補わない。

純粋入力の組立0.177711秒、OS peak private/pagefile19,156,992B。これとは別にモデルadapterの数量読取りは元と同じ公開snapshotを使い、label採点は選択後に開く。

## 別候補への接続

旧sourceを変更せず、`demand_data_inputs.py` / `demand_model_inputs.py` / `demand_train_inputs.py`を追加した。

C56/P7/H14/V3/D64/L2を維持。patch98→64、未来暦168→64、店舗別統計2→64をqueryへ加算、日次配分入力77→32→1。120,740 parameters（旧110,916）。総量の非負ordered Q10/Q50/Q90と日次pointの整合配分は維持。

新3接続確認は一回all passed（0.334秒）。統計を加えたshift contextで総量倍率の経路が変わること、連続暦を固定してevent IDだけ変えた際の配分経路、実adapterのorigin/尺度/scheduleと未支持Christmas metadataを確認した。新統計・未来暦projectionの勾配も有限かつ非ゼロ。経路確認ではzero-weight初期headを明示的な非zero headに変更したfixtureを使い、予測性能とはしない。

## 一回学習と選択

train991 / validation25 / test16 origin、保存された256×8 batch日付列を再利用。新sampler生成・旧学習反復なし。CPU float32/2threads/interop1/deterministic、独立init seed20261014。同じseedでもparameter形状が異なるので同一初期stateではない。

AdamWとlossは旧と同じ。lossは0.5*総量pinball/(14*固定train平均)+0.5*日次MAE/固定train平均。256stepを一回完了し、2016 validationで選択後、2017固定16originを新candidateで一度だけforwardした。

| step | 新validation loss |
| --- | ---: |
| 64 | 0.0693210042 |
| 128 | 0.0703478338 |
| 192 | 0.0690742849 |
| 256（選択） | 0.0690161481 |

旧選択loss0.0693295431との差は小さい。2017は元候補の結果も既知の回顧探索で、未見性能・有意差・勝者を出していない。

## 点予測の比較

旧candidate、mean28、暦配分の原保存結果を再利用した。店舗・日付・実績・split/尺度・scheduleの対応を確認。原数量の精度で集計し、旧forwardを反復していない。

| 方式 | 日次WAPE % | 14日総量WAPE % | 総量Bias % |
| --- | ---: | ---: | ---: |
| mean28 | 14.770136 | 7.307154 | -0.839908 |
| mean28総量＋限定暦配分 | 14.424314 | 7.307154 | -0.839908 |
| 元小型候補 | 14.729793 | 7.295235 | -1.214088 |
| 追加入力候補 | 14.614032 | 7.163771 | -3.028263 |

総量WAPEの旧候補との差は約0.131 percentage points。48窓中、総量絶対誤差が旧候補より小さいのは21窓で、全窓で改善したわけではない。

| 店舗 | 日次WAPE 新 / 暦配分 % | 総量WAPE 新 / mean28 % | 新総量区間covered/16 |
| --- | ---: | ---: | ---: |
| 5 | 12.407368 / 12.193467 | 5.041465 / 5.304585 | 14 |
| 11 | 13.846585 / 13.660233 | 6.725227 / 6.847978 | 13 |
| 12 | 21.519523 / 21.363324 | 12.732949 / 12.724551 | 11 |

店舗12の総量は基準より僅かに悪い。日次も全3店舗で暦配分基準に届かない。

保存予測だけの内訳では、元日3窓の日次WAPEが新23.859811 / 旧24.013416 / 暦18.713429%。残り45窓は新14.034677 / 旧14.148067 / 暦14.155551%。新event channelが存在しても、少ない元日事例を今回十分に利用できたとはいえない。営業状態を確定した結果でもない。

新総量中央値/基準総量の比は0.961644–0.996274、平均0.978224。すべて基準より低い方向で、過小偏りを引き続き課題として残す。この値からbias補正係数をfitしていない。

## 総量区間

| 方式 | covered/48 | coverage % | 平均幅 | interval score |
| --- | ---: | ---: | ---: | ---: |
| mean28・固定校正 | 32 | 66.67 | 917.801727 | 2092.694240 |
| mean28・直近校正 | 34 | 70.83 | 1147.818659 | 2080.379115 |
| 元小型候補 | 41 | 85.42 | 1819.699715 | 2301.566831 |
| 追加入力候補 | 38 | 79.17 | 1450.955859 | 2202.258746 |

新候補は下限未満2/上限超過8。旧候補より幅・interval scoreは小さいが、基準よりscoreが大きい。店舗別coverage87.5/81.25/68.75%と差があり、全体で名目80%に近いことを校正や将来保証へしない。再校正・幅grid・実務採択は0。

## 次の研究判断

追加入力の経路が成立したので、単純な学習延長や再試行は次にしない。次は**数量pointとして平均と中央値のどちらを予測するのか**を、現在のlossと用途に照らして整理する。

現在の総量pointはQ50で、条件付き平均のheadではない。日次MAEとpinballが小さくなることは、合計の平均Biasが0になることと同じではない。例として数量20が確率0.8、100が0.2なら、平均36・中央値20。中央値予測の期待絶対誤差16は平均予測の25.6より小さいが、期待Biasは20−36=−16になる。この式は説明用で、今回の負Biasの原因がこれと確定したわけではない。

菓子メーカーの生産数量判断に、期待数量・中央値・欠品/余剰を重み付けした数量のどれが必要かは未確定。公開販売量の研究ではmeanとquantileを分けて記録できる設計を先に考える。2017を使った係数補正や第三候補の連続学習へ進まず、train側の目的式を検討する。販促履歴がないことを研究全体の停止条件には戻さない。

## 保存と資源

新学習elapsed14.076793秒、OS peak private/pagefile1,031,708,672B。実CPython3.14.0/Torch2.14.0+cpu/Windows。閉鎖model18files/3,217,857B、日次和と総量中央値の最大float32差0.001953125。

計算はHEAD5186681751ab4b02571c842ca6a270955f1ee6d6に未commitの新candidate sourceを加えたもの。clean commit計算ではない。source全文・SHA・出力前設計・snapshot/支持ledger・固定日付batch/尺度・initial・checkpoint/prefix・選択・原予測/event metadata/比較・journalをlocal保存した。公式TimesFM重み・教師出力・同等再現claim0。

主要保存先（全閉鎖、追記/再実行禁止）：

- `artifacts/representative-store-sales-input-features-20261014-records` と `...-input-features-launch-20261014-records`：純粋入力と7新確認、全stdio/exit0。
- `artifacts/representative-store-sales-input-model-checks-20261014-records`：3新接続確認、全stdio/exit0。
- `artifacts/representative-store-sales-input-model-pilot-20261014` と `...-input-model-pilot-20261014-records`：原モデル出力と全stdio/exit0。summaryはcandidate-complete、root closureがcomplete。
- `artifacts/representative-store-sales-input-model-analysis-20261014-records` と対応launch：保存新旧予測の対応と内訳のみ。
- 文書 `...-input-model-doc-20261014-records`、Git後 `...-input-model-git-20261014-records` のpost-saveを優先。

新10distinct確認、一回新candidate、旧確認/モデル/評価/CI反復0。実行900秒2GiB/output1GiB/single32MiB/files32、診断16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16filesを維持。局所checkpointはblocking中断/native全容量証明ではない。

生数量・予測・fit・重みのGit送信0。独自codeと集約文書のみ。直接研究ACTIVE/automation PAUSED、追加agent0/CARE手動待ち。formal_permission=false/credit0/native reader禁止/登録holdout未読/正式受入未完了。
