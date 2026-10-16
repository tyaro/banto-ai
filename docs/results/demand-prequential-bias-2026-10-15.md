# 完了済み自己誤差による更新 — 内部で補正0を選択

2026-10-15 JST。人の「こちらから声かけるまで自走」に従い、[固定契約](../research/demand-prequential-bias-design-2026-10-15.md)を実装・検証・実行・保存した。新fit/NNforward/profile生成/原ZIP抽出はない。

**56日以内に完了した自己予測誤差の平均を引く方式は、2014内部で補正係数0を選択した。** 更新は採用せず、選択は元Transformerのまま。2015の結果を見て係数や方式を変更していない。

## 発行日時点の状態

mean28と元NN3328それぞれのraw予測−実績をuで正規化して記録する。予測窓全体のcalendar末日がorigin前に終了し、誤差の日付がorigin前56日以内の記録だけを同店で使用する。14観測日以上なら平均を引き、なければ0へfallbackする。欠測日は記録せず、部分14日総量を生成しない。
2014 time120は空履歴から開始。各originの予測を生成後に、その行の実績を将来状態へ追加する。2015は2014の完了履歴でwarm startし、同じ順序で進める。状態は更新済み模型の誤差ではなくraw自己予測の誤差を使う。
これにより現在行の実績は現在行の補正に使わない。予測窓がまだ終わっていれば、その観測済みの日についても今回の方式では使わない。無観測と実0を区別する。

## 内部校正と選択

2014 time120だけで、各自己参照とのconvex blendのalphaをjoint最小/日次・総量MSE悪化なし/0<=alpha<=1として校正した。選択はmean28/元NN/更新mean28/更新NNのjoint最小、tieはこの順。

|更新候補|日次の補正二乗量E|日次の補正と必要量の積C|alpha|
|---|---:|---:|---:|
|mean28の自己bias更新|0.007277613491|−0.003784002829|0.0|
|NNの自己bias更新|0.006295537173|−0.002567064547|0.0|

どちらもCが負となり、日次/総量の副条件から補正0へ戻った。今回の固定期間・平均更新法を支持しない結果であり、全online更新が無効という結論ではない。

|2014選択用指標|日次|総量|joint|
|---|---:|---:|---:|
|mean28/更新mean28(alpha0)|0.107542732365|0.039950946158|0.073746839261|
|元NN/更新NN(alpha0)|0.101377210687|0.034554858816|0.067966034751|

事前tie順で元NNを選択し保存してから2015を順次処理した。内部alpha校正と模型選択に使用した期間であり、独立した未知性能の評価とは呼ばない。元checkpointは以前の2014 time validationで選択済みであることも保持する。

## 2015結果

原10店の250要求/3490観測日/240完全総量、Christmas nullを維持。今回は元NNが選ばれたため、候補予測は保存済みNN予測と全250件同じ。

|方法|日次MSE/u²|総量MSE/(14u)²|joint|
|---|---:|---:|---:|
|mean28|0.134053954571|0.020878675703|0.077466315137|
|内部選択候補＝元NN|0.133491411548|0.020265515764|0.076878463656|

元の0.758848%改善/7of10店改善を維持、事前2%目安未達・不採用。新しい性能改善として数えない。MAE/WAPEの旧悪化も維持する。全店舗/全quarter/MAE/WAPE/bias/支持をsummaryに保存。2015は既読の探索的開発データで、未知性能やPSI損失の改善は未認定。

内部のcold fallbackは各店最初の1窓、全10窓。2015は全250窓で14件以上の完了履歴がありfallback0。支持があっても更新の有効性を意味しない。

## 保存と確認

評価root `artifacts/macos-demand-prequential-bias-20261015` はclosure含め12files/1,183,160B。契約/source/config、120内部予測・過去支持・warm履歴、固定alpha/選択、250予測前後・過去支持・指標を保存。
全child stdout/stderr/exit0、fixture/heartbeat設定snapshotは同execution-records。新架空fixture7件pass（current/future label poison、全窓完了前の拒否、56日境界、他店payload拒否、実0/欠測、warm state保全、選択tie/非有限拒否）。readbackで全support traceの完了日/56日境界、固定選択、label前後不変、元baseline/NN/実績一致、原3rootとsource不変を照合した。モデル/実行/読戻しclosure complete、文書は同doc-records。
読取り用の一行inspectionで括弧余分のSyntaxErrorがあったが、模型/評価を起動しない補助表示だけで、修正後は保存summaryの表示のみを行った。childの成功記録を書き換え/再実行していない。

CPython3.14.8/Torch2.14.0 Mac arm64 CPU。child3.130403秒/親3.774634秒、sampled footprint161,596,160B/peakRSS197,656,576B、各2GiB以内。NumPy未導入warningは全stderr、tensor経路exit0。Mac指標はWindows private bytesと同じ定義ではない。
Windows native/OS依存包括suiteは今回未実行、旧runtime結果は変更しない。formal_permission=false、製品採用0、CARE待ち、追加agent0。原data/profile/予測/weightsのGit送信0、closed rootsと既存変更保持。

## 継続工程

heartbeat `banto-ai-mac` をACTIVE/15分間隔でこのチャットに設定・読取り照合。[継続方針](../research/autonomous-continuation-2026-10-15.md)に従い、人の声かけまで研究を継続する。
次の有益な一件は、固定365日窓の完了済みlabelだけによる共有リッジのローリング再fit。72列/lambda0.01、固定前期尺度/暦のまま、各originで学習packetのorigin>=origin−365かつpacket末日<originをmetadata選択してからlabelを使う。140窓以上/全10店支持を満たさなければmean28へfallbackする。
2014 time120でこの手順を順次評価してalpha/方式を固定し、2015で再選択せず一回逐次評価する。係数と標準化は毎originの過去poolだけで作る。未来label-poisonと同時刻他店の未完了label拒否を先に検査する。仮説/条件を別契約に保存してから実装し、更新方式を今回の結果だけで認定しない。
2016/2017/予約31–54/販促数量/正式holdout/新データ取得/課金API/外部送信/Git push/本番採用/削除には進まない。
