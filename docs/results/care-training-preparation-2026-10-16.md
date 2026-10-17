# CAREの学習用尺度とbaseline profileおよび抽出列の固定

2026-10-16 JST。保全・点検支援を最優先とする[計画](../research/timesfm-inspired-practical-evaluation-plan-2026-10-16.md)と固定契約CARE-A-MAINT-20261016-r1に従い、全5foldのtrainだけから尺度・共通MAD・負荷bin温度中央値を推定し、実学習用のbatch列を保存した。全20負荷binの支持は固定下限128組を通過し、最少30,440組だった。ニューラルモデルの学習前準備として固定できた段階である。

[前工程の数値入力・consumer確認](care-numeric-consumer-2026-10-16.md)、[固定契約](../research/care-a-maintenance-contract-2026-10-16.md)を維持した。Farm A22file/3信号、5fold/anchor、10分cadence、C128/H32、4,096更新×batch8、sampler seed20262016、asset等重み、bin/支持/予算を変更していない。[実行前phase](../../artifacts/care-train-profile-schedule-20261016/phase.json)を数量集計前に保存し、不成立時の差替えやrebinを禁止した。

## trainだけの尺度と共通MAD

| asset | anchor event | 尺度に一度ずつ使ったbin | baseline用の適格学習origin |
| --- | ---: | ---: | ---: |
| A:0 | 0 | 47,252 | 44,775 |
| A:10 | 3 | 41,635 | 38,824 |
| A:11 | 25 | 49,844 | 48,025 |
| A:13 | 14 | 49,422 | 47,603 |
| A:21 | 13 | 40,642 | 38,664 |

尺度は各foldのtrain3 assetについて、anchor prefixの全3信号finiteかつstatus0の各binを一度だけ使用した。gapの近くでも有効な個別binは尺度に使い、窓やsamplingの重複回数で重くしない。asset内平均・共有平均からの二乗偏差をfloat64 fsumで集計し、3 assetを等重みにした。T=max(sigma,1e−5)、context floor=max(.01sigma,1e−5)のfloat64/float32を保存し、全15尺度で有限・正を確認した。forward時の平均とscaleを計算する対象は引き続き発行前contextだけである。

両検知器で共用する温度のMADも同じtrain bin母集団・asset等重みで計算した。R=max(1.4826×MAD,1e−3)は全10値で有限・正となった。validation/testの数量で尺度を更新せず、event truth、警報残差、testのstatusを使わない。status0は回顧的な学習用annotationであり健康truthの保証ではない。

weighted quantileは同値のrow重みをfsumで結合し、累積massもfsumで計算、累積/全massがp以上になる最小値とした。補間や逐次加算による累積のdriftを使わない。細部は実行前phaseと[参照実装](../../models/mini-transformer/care_training_preparation.py)に保存した。これらのprofileの推定は実施したが、ニューラル学習や校正閾値の推定とは区別する。

## 負荷binと抽出列

baselineは適格160点学習窓のoriginごとにpower[n−1]と2温度[n]の組を一つ使った。pairには元のasset内件数Nに応じた1/(3N)のmassを与え、負荷quartileとbin内温度中央値を計算した。binへ制限した後は元のmassを正規化し、bin内のassetをもう一度均等にはしない。

| fold | train asset順 | 負荷bin 0 / 1 / 2 / 3のpair数 | 抽出された3 assetの件数 |
| --- | --- | --- | --- |
| 0 | 11, 13, 21 | 33905 / 33297 / 33596 / 33494 | 10863 / 11002 / 10903 |
| 1 | 0, 13, 21 | 32810 / 32744 / 32808 / 32680 | 10949 / 10953 / 10866 |
| 2 | 0, 10, 21 | 30768 / 30440 / 30468 / 30587 | 10965 / 10944 / 10859 |
| 3 | 0, 10, 11 | 33070 / 32869 / 32784 / 32901 | 10971 / 10854 / 10943 |
| 4 | 10, 11, 13 | 33736 / 33627 / 33550 / 33539 | 10910 / 10953 / 10905 |

実データでは全4binが各foldで非空、全20binが下限128組を通過した。重複したquartileはそのまま残し、境界の一致は低いbin、空binは最寄りの非空bin（同距離なら低い方）という規則を維持する。人工確認では重複cut/空bin/小さいbinの支持不成立も残し、都合のよいbin数への変更をしない。

各foldの全4,096更新×batch8=32,768例、計163,840例を、固定seedのasset→origin置換抽出で生成した。sorted train assetとsorted適格originの順序を固定している。scheduleは1例12byte little-endian `<III`（Farm A内asset ID、anchor event ID、origin ordinal）で、5fold合計1,966,080B。更新順・batch内順をそのまま保持し、各assetの全適格origin集合もuint32-leで保存した。全scheduleとprofileのhashをmanifestに記録した。

Rust側はこの実batch列を比較の基準にできる。同seedだけによるPython/Rust乱数の同値は主張しない。profile JSONのfloat64/float32、mask、時点、bin境界の意味も共通参照にする。

## 独立照合と実consumerへの接続

分位点計算は別の整数binary-rational累積mass実装で、平均/分散はasset内分散とasset間平均差を足す方法で検算した。分位点75値、全尺度、MAD、負荷cut、温度中央値とbin件数が一致した。平均64bitの最大絶対差は7.1054273576010019e-15、分散は2.8421709430404007e-14で、検算の事前許容差relative/absolute1e−12以内だった。これをRust実装全体の受入許容差へ自動転用しない。

全163,840件のscheduleは、randrangeを呼ばないgetrandbits＋棄却抽出による独立再現とbytes一致。5 anchorのorigin集合は既存consumerと全件一致し、各originのcontext/32点targetがtrain prefix内に収まることを確認した。尺度母集団の選別にはprefix外へのrow accessで即時失敗するtripwireも通した。入力/evaluator/labelの分離を保ち、両実行プロセスのevent truth読取りは0だった。整合性hash検証は全22binaryのopaque bytesを読むが、統計母集団へ数量を渡したのは5 anchorの許可prefixだけである。

`FrozenPreparation` loaderを実装し、dataset/契約/profile/schedule/origin hash、fold、実consumerの全適格origin集合を照合するようにした。loaderの追加検査はprofile計算の後に加え、旧source snapshotを保持し、独立実行が最終loaderを確認した。先頭・末尾step（0/4095）の実batchを全5foldで取り出し、[8,3,128]入力と別の[8,3,32]targetの形・有限性を確認した。範囲外stepとbool stepは拒否した。

全10batchは[独立検証root](../../artifacts/care-train-preparation-verify-20261016/root-closed.json)にfold別float32-le参照として保存した。順序はstep→例→入力3×128→target3×32、1fold30,720Bである。Torch/model forward・backward・optimizerは実行していない。

[profileとschedule manifest](../../artifacts/care-train-profile-schedule-20261016/manifest.json)、[独立照合](../../artifacts/care-train-preparation-verify-20261016/independent-checks.json)、[準備script](../../tools/public-data/care_training_prepare.py)、[独立script](../../tools/public-data/care_training_preparation_verify.py)。

## 資源と保存

| 実行root | 親観測秒 | sampled footprint B | child peak RSS B | exit |
| --- | ---: | ---: | ---: | ---: |
| care-train-profile-schedule-20261016-records | 4.177 | 147,112,536 | 156,925,952 | 0 |
| care-train-preparation-verify-20261016-records | 5.420 | 207,290,992 | 214,827,008 | 0 |

Pythonはrepository既存3.14.8、追加依存なし。親900/子870秒・Mac physical footprint/peak RSS各2GiB内。OS hard capではなく、既存wrapper/自己checkpointで観測する上限である。準備rootは21file/2,888,634B、独立rootは9file/178,396Bで、normal24file/768MiB・single32MiB内。stdio/source/exit/phase/profile/schedule/参照batch/closureを保存し、旧変更・原本・closed rootsを変更しない。EvidenceStoreは16MiB/512file・part256KiB・failure reserve2MiB/16fileを維持する。

Mac共通の前処理/consumer経路とMac資源観測はpass。Windows固有機能とOS依存包括test suiteは未実行として分ける。

## 次の有限実学習

入力・時点/role・窓/イベント支持に加え、全5foldの尺度、共通MAD、baseline pair支持、全batch列と実batch取得が揃った。次工程は固定profileとscheduleを使うCARE trainerを接続し、各foldの4,096更新・4 checkpoint選択・校正・予測/警報を、親900/子870秒・各2GiBの単位で順次実行する工程である。最後のfold内で全foldの予測等をfreezeしてからevaluatorが採点し、一件でも未完/非有限/境界違反なら残りを止める。条件・seed・更新数の探索を追加しない。

今回ニューラル学習・model forward・校正閾値・test予測・性能採点は0。固定JSONのfalse flagsは凍結時点の記録として不変で、profile準備を予兆性能やRust移植の成立と扱わない。保全・点検支援の第一優先、学習/backward/optimizer/checkpoint再開/推論/警報stateとbanto API/job/model管理まで含めるRust最終目的を維持する。需要2015停止、2014以前だけの調整、同休業mean28、四季平均過小量/過大量非増加、観測のみ・欠測0仮定の分離、heartbeat PAUSEDも維持。新取得・外部研究data送信・Git push・本番採用・追加agentはない。
