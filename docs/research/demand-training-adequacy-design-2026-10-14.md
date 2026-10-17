# 学習量の妥当性を確認する新しい手順（2026-10-14）

人の「256stepで足りるか」と「次のstepへ」を受け、学習終了の判断を測る新unitを始める。旧256step/2015/2016結果と条件未達は保全する。今回は旧weightsの延長や再評価ではなく、学習期間内の時間順分離と新尺度を使った新しい学習診断。以前の同仮説grid禁止を、今回の人の明示した学習量確認の範囲で更新する。2015/2016の結果でcheckpointを選ばない。

## 時系列分離と尺度

旧630key（15店各42窓）のmetadataだけで、label末尾が2014-07-01未満の450窓（各30）を学習、originが2014-07-01以降の180窓（各12）を内部検証とする。境界を跨ぐ窓は除外して保存する（現keyでは0）。時間順に分け、ランダムなtrain/validation分割は使わない。検証の過去contextに学習期間の観測が入るのは予測時点の利用可能な履歴として扱う。

尺度uは各店舗の2013-01-01〜2014-06-30の観測数量平均から新規計算する。実0を含み欠測を除く。検証量/観測maskをuへ使わず、旧2014末までの尺度を流用しない。元18店のうち固定positive15だけを学習し、zero-scale3は学習対象外として理由を残す。各positive店でu>0・学習30/検証12全窓が同経路で利用可能でなければ保存して停止、店/日/尺度floorの置換0。

原2013–15 prefixをpin再利用し、必要な2013–14だけ数量解釈する。2015/2016/2017、新archive/予約群/正式holdoutの数量や旧予測は読まない。旧630fit profileはorigin前56日の統計として保存済みなので、その原profileを再利用し、新uで8特徴をencodeする。再profile集計0。calendar支持は新450学習keyのmaskだけで計算し、検証labelでchannelを追加しない。

## 固定二件と学習曲線

同じStatisticalFeatureMean/30369parameterを新initialから二件学習。seed20261014、同initial、同じ4096×8までのsampler、inputなし/ありだけ違う。同じ数量q/u、context2統計、名目calendar、baseline、loss、AdamW lr3e-4/betas(.9,.999)/eps1e-8/wd.01/gradnorm1。CPUfloat32/2threads/interop1/deterministic、架構/半減期/width/learning-rate grid0。

0stepと以後128stepごとに、固定した学習450窓と内部検証180窓をeval/no_gradで全件測る。各storeの日次MSE/u²と総量MSE/(14u)²を.5ずつ足し、15店を等重み平均。更新batchのlossだけを収束の根拠にしない。curveは更新なしで測り、終了判断は内部検証だけを使う。0stepのbaseline状態もbest候補に含め、学習後が悪い場合に無理に学習済みcheckpointを採択しない。

上限4096step/各一回。warmup512step、128step単位で内部検証jointが意味のある改善（相対0.01%超）を6回連続示さなければearly stop。厳密に最小の内部検証lossを持つweightはclone保存し、patience用の意味のある改善判定とは別に管理する。最終weight、最良weight、best step、patience、stop理由を保存する。各側に同じ終了方針と上限を適用し、終了stepが違う場合も明示する。

## 学習量について言える範囲

256step時点の固定train/validation lossと、そこからのbest/最終値・曲線を報告する。256以降に内部検証lossが0.1%以上改善する場合は、この新分離手順では256以降にも改善余地があったと記述する。bestが0/早期でtrainのみ改善する場合は過学習の兆候を記述する。上限に達して改善が続く場合は収束未確認として止め、自動延長しない。

「early stopした」は真の最適点や未知性能の証明ではない。この内部検証は2014既読の回顧診断で、学習窓数・尺度・支持が旧256step実験とは違う。旧モデルの256stepが必ず不足だったという断定、2015/2016での再選択、σ単独効果、実用採択へ補わない。複数初期値の安定性は今回未検証。

新少数確認はlabel境界の分離、検証payloadを尺度計算前に拒否、warmup/patience/停止後再入拒否、微小bestと閾値を超える改善の分離/非有限拒否の4件だけ。旧模型/統計/暦確認・完成CIは反復0。early stoppingの監視値/patience/best保存の考え方は[Keras公式説明](https://keras.io/api/callbacks/early_stopping/)を参照し、Kerasへの移行やcodeコピーは行わない。

## 状態・保存・上限

今回の人の再開指示でdirect ACTIVE、automation PAUSED維持。実行900秒/2GiB/output1GiB/single32MiB/files32、normal24file768MiB/failure8file256MiB、記録16MiB512file/256KiBpart/failure2MiB16file、prep128KiB16fileを維持。モデル各4096でもwall/private capが優先。容量/入力/人の停止時は原証拠を保全してPAUSED、盲目的再試行0。

新initial/sampler/source/期間/尺度と使用除外key/入力pin、固定全件曲線、更新journal、best/final weightsを新local rootへ保存する。child checkpointのJSON stdoutはlauncherが全rawを保持し、失敗/timeout prefixを判定前保存。root closure/失敗分も書込み前の件数・bytesに含める。旧root追記0。

一回の診断保存で自走を区切り、次の問いはcurveを見て人と判断する。同データでcheckpointを選んだことを未知評価にせず、2015/2016/2017追加推論・別seed/grid・予約群へ進まない。formal_permission=false/credit0/native禁止/登録holdout未読、追加agent0/CARE手動待ち維持。Git独自source/架空確認/集約docsのみ、原quantity/profile/尺度/ledger/予測/weights送信0。
