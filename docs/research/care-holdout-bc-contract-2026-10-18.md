# CARE Farm B・Cの1回限りholdout契約（2026-10-18）

2026-10-18 JST。[判定基準](care-maintenance-criteria-2026-10-18.md)（CARE-MAINT-CRITERIA-20261018）で「合否を言えるのはこの経路だけ」とした、CARE Farm B・Cでの1回限りの評価を、開封前に固定する。機械可読版は[契約JSON](../../examples/configs/care-holdout-bc-20261018.json)。契約IDは CARE-BC-HOLDOUT-20261018。

## 人の承認（2026-10-18）

- Farm B・Cで自作モデルとbaselineを新たに学習する。R0.2で止めている「正式R2以外の実データ学習」の例外で、この契約の範囲に限る。
- 元データはZenodoから取得する（record 15846963、v6、CC-BY-SA 4.0）。
- 契約を固定するまでは、metadataだけを見る。
- Farm Cの2つ目の温度信号は、主軸受温度1で代替する。
- 合否はB＋Cの合算で判定する。
- 基盤モデルは評価しない。

## 開封前に分かっていること

この契約は次の情報だけから作った。いずれもlabelの中身ではない。

- 2026-10-16のmetadata監査（Mac）の構造情報：file数（B 15、C 58）、asset、列名、行数、train/prediction区間の行数、status件数、時刻gap。
- 各farmのfeature_description.csvとREADME。
- 同じ監査が数えたlabelの件数：Bはanomaly 6・normal 9、Cは27・31。この件数は監査の集計として記録済みで、どのfileがどちらかは、このセッションでは見ていない。
- 監査ではB・Cのevent_info.csvもlabel rootへ写した（Mac側、評価者専用）。どのモデル・閾値・警報もそれを読んでいない。人やagentが中身を見たかどうかは記録からは確かめられないため、「完全に未知」とは呼ばず、「評価に一度も使っていないholdout」と呼ぶ。
- センサー値はまだ1つも読んでいない（float decode 0）。

## 固定する内容

**元データ**
- `CARE_To_Compare.zip`：5,503,439,673 bytes、MD5 `2547b58c…cf500c`（公式）、SHA-256 `ca61379e…d4194f1`（前回の照合値）。一致しなければ止める。

**信号**（Avgだけ。並びは[温度1, 温度2, 電力]で、Farm Aの[発電機軸受, 歯車油, 電力]に対応させる）

| farm | 温度1（警報対象） | 温度2（警報対象） | 電力（入力のみ） |
| --- | --- | --- | --- |
| A（参照） | sensor_13_avg 発電機軸受温度2（DE） | sensor_12_avg 歯車箱の油温度 | power_30_avg Grid power |
| B | sensor_33_avg 発電機軸受温度2 | sensor_39_avg 歯車箱油タンク温度 | power_62_avg Active power |
| C | sensor_196_avg 主軸受温度1（**代替**） | sensor_186_avg 歯車箱油温度1 | power_6_avg Active power HV grid |

- Farm Bの軸受は、Aと同じ番号の「軸受2」を取る。DEかどうかはmetadataに書かれていない。
- Farm Bの油温は、「油温度」に最も近いタンク温度を取る（入口温度sensor_38は取らない）。
- Farm Cには発電機軸受温度がない。駆動系の軸受温度で最も近い主軸受温度1で代替する。代替であることを結果に明記する。
- 単位はmetadataの表記のまま（Bは「�C」、Cは「Celsius」）。数値の変換はしない。

**split**（farmごと。Farm Aと同じ規則で、labelを見ずに構造情報だけから決めた）
- assetを番号順に並べ、各assetを1回ずつtestにする。次のasset（循環）をvalidation、残りをtrainにする。foldはBが9、Cが22。
- 各assetのanchorは最小のevent ID。学習とvalidationには、anchor fileのtrain区間（status 0の行だけ）を使う。
- validation anchorのtrain区間は、先頭70%をcheckpoint選択、残り30%を警報の校正に使う。
- test assetの全fileのprediction区間を採点する。
- anchor：
  - B：0→21、2→83、5→82、6→23、7→27、11→19、12→77、13→2、14→34。
  - C：2→12、5→89、12→15、13→29、14→85、15→64、16→30、21→47、23→37、32→5、33→41、34→4、35→31、38→6、42→32、43→11、44→44、50→8、52→28、53→1、55→9、56→63。
- fold全体は[契約JSON](../../examples/configs/care-holdout-bc-20261018.json)に置く。

**学習・警報**（Farm Aの[固定契約](care-a-maintenance-contract-2026-10-16.md)と同じで、値を変えない）
- SmallForecaster full V3/C128/H32、seed 20261016、AdamW、batch 8、4,096更新、sampler seed 20262016。
- checkpointは512/1024/2048/4096からvalidationのpinballで選ぶ。
- 閾値は校正scoreの99.5%点で、厳密な超過とする。3連続でOPEN、3連続でCLOSE。scoreは2温度の`max(|y−p50|/R)`で、Rはtrainだけの温度MAD×1.4826（floor 1e−3）。
- baselineは負荷binの温度中央値で、共通支持とnative支持の2種。
- 利用可能時刻は記録時刻＋600秒。gap・欠測・file境界でstateをresetする。
- testのstatusとlabelは、入力にも警報にも使わない。
- 床はFarm Aと同じ。
  - 件数：anchorごとのfit originが4,096以上、selectionが256以上、calibrationが512以上。
  - 支持：各prediction fileの共通支持が70%以上。各anomaly区間も70%以上で空でないこと（採点時に確認）。各正常assetのeligible時間が24時間以上。
- 1foldでも床割れ・未完・非有限・境界違反があれば、残りを止めてcampaignを「不成立」として保存する。fileやassetの差し替え、seedの追加、延長はしない。

## 判定（1回だけ）

判定する方法は自作モデル（共通支持）だけ。baseline 2種は比較として並べる。

**合格の条件**（すべて満たすこと。B＋Cの合算）
1. W＝72時間で、検知可能なanomalyの50%以上を検知する。
2. W＝24時間で、検知可能なanomalyの60%以上を検知する。
3. 正常fileの誤警報が、pooledでasset・30日あたり1.0件以下。
4. 正常fileを持つ全assetで、asset別の率も1.0件以下。assetは(farm, asset_id)で区別する（BとCには同じ番号2・5・12・13・14があるが別の風車）。

- 検知可能なeventが0件のWは、合格としない。
- 次はfarm別にも示すが、合否には使わない：誤警報の目標0.25件、Clopper–Pearsonの95%信頼区間、注釈区間外の警報件数、168時間の既定値と見られる区間の印、先行時間の代理値とearliness、baselineとの差。
- 4は、正常時間が短いassetほど1件で上限を超えやすい厳しい条件である。基準どおりに適用し、ここでは緩めない。

**開封後の扱い**
- labelは、全foldの予測・閾値・警報を固定して閉じた後に、評価者だけが読む。
- 固定後に、モデル・閾値・信号・split・警報規則は変えない。
- 採点の誤りを直して採点し直す場合は、直す前の結果も残す。開封後に変えた点が採点以外に及ぶなら、合否は主張しない。
- 不合格でも同じholdoutでやり直さない。次の候補には新しいholdoutが必要になる。

## 実行の手順と上限

1. 元データを取得し、上のhashと照合する。
2. B・Cの3信号と構造列だけの入力rootを作る。event_info.csvは読まない。支持とfinite値の確認もlabelなしで行う。
3. 全31 foldで学習・選択・校正・予測・警報を行い、全体を固定して閉じる。
4. 評価者がevent_info.csvを読み、時刻とIDの対応を確認してから1回採点する。

- 各fold：親900秒、子870秒、peak RSS 2GiB。
- campaign：全体で8時間以内。止まっても、閉じたfoldから再開できるようにする。
- 実行環境は固定する：CPython 3.14.6、torch 2.14.1+cpu（git 5c488690…、libtorch_cpu SHA-256 `e7b6071e…eb9da4`）、Linux x86_64。threadはFarm Aのコードと同じ（演算2、interop 1、deterministic algorithms有効）。各foldは学習前に環境を記録・照合し、違えば止める。
- Farm AはMacで学習したため、同じ設定でもbytesは一致しない。
- 保存物はgitignoreの`artifacts/`に置く。公開するのはhashと集計だけ。

**コードの変更**
- Farm A用の入力作成・学習コードを、farm・信号・splitを引数にとる形へ一般化する。設定値（上記）は変えない。
- 一般化の確認として、Farm Aの入力rootを作り直し、保存済みのbytesと一致させる。これは学習を伴わない。Farm Aの再学習はしない。
