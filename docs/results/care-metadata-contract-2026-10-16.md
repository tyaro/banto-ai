# CARE v6 — 版・利用条件・sensor/asset確認と評価条件の固定

2026-10-16 JST。保全・点検支援（異常の予兆）を第一優先に、人の指定したCARE原本を照合した。**今回の成果は入力/labelの分離と実行前契約の固定まで。CAREの学習・警報生成・性能採点は行っていない。**

## 原本・版・利用条件

[公式Zenodo record 15846963](https://zenodo.org/records/15846963)、DOI `10.5281/zenodo.15846963`（v6、2025-07-09公開）と一致した。[取得したAPI metadata](../../artifacts/care-zenodo-v6-metadata-20261016/record.json)は2026-10-12更新の内容で、今回のknown issuesも保存した。

| 照合 | 結果 |
| --- | --- |
| ZIPサイズ | 5,503,439,673B、公式と一致 |
| 公式MD5 | `2547b58c21ac8c242d13232860cf500c`、原本全体を計算して一致 |
| ローカルSHA-256 | `ca61379e98956d891041ad45c885109bd8a14199fde0688d0184a11c2d4194f1`、前回pinと一致。公式SHA公開と取り違えない |
| データlicense | `CC-BY-SA-4.0`、公式APIのlicense欄で確認 |
| 出典 | Christian Gück / Cyriana Roelofs、上記dataset DOIと関連論文 `10.3390/data9120138`を保存 |

データの利用・変更物の配布には帰属、licenseリンク、変更表示、ShareAlike等の条件を保持する。[CC BY-SA 4.0の条件](https://creativecommons.org/licenses/by-sa/4.0/)と[保存したlegalcode](../../artifacts/care-cc-by-sa-legalcode-20261016/legalcode.txt)を参照。これを自作Rustコードやモデルのlicenseを一律に認定する説明へ広げない。今回データ/派生物の外部配布は0で、bantoへ含める対象の権利・帰属はmodel packageに分けて記録する。

## 確認した構成と重要な相違

全95 CSVをstreamで読み、timestamp/asset/id/train_test/statusの構造列だけを解釈した。センサー値のfloat decodeは0、約20GBの全展開も0。ZIP memberは最後まで読んでCRCを確認し、file SHAを保存した。

| farm | CSV数 | asset数 | 構造行数 | 列数（うち構造5列） | 600秒超gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 22 | 5 | 1,196,747 | 86 | 460 |
| B | 15 | 9 | 859,065 | 257 | 87 |
| C | 58 | 22 | 3,187,136 | 957 | 40 |
| 計 | 95 | 36 | 5,242,948 | — | 587 |

assetキーは`(farm,asset_id)`。同じ番号が複数farmに存在する。各fileは単一assetで、file内のid/timestamp重複・時刻逆行は0。file間の時刻は匿名化されており、同一時刻でも同一観測と決めつけず、実際の前後関係も復元しない。[公式FAQ](https://aefdi.github.io/EnergyFaultDetector/care2compare_faq.html)の意味に合わせてfileを独立segmentにする。

原本の実labelは**45 anomaly / 50 normal**、内訳A12/10・B6/9・C27/31。READMEの44/51は古い記載として原文を保持し、v6のevent_infoを正とした。Aの22件はevent_start/endのIDとCSVの時刻の対応44点も一致した。statusは正常truthと同じではなく、Aでは故障log由来のためtest入力/除外gateに使わない。公式説明のMin/Max/Std品質問題を避け、最初はAvgのみを固定した。

## 最初の有限対象と入力

ラベル内容を開く前に、最初の限定対象をFarm A、3信号、asset分割規則、anchor規則として[事前保存](../../artifacts/care-contract-20261016-evidence/prescan-policy.json)した。B/Cは今回inventoryのみ。root-cause説明や検知成績で対象を選び直していない。

| 入力順 | 意味 | 原単位表記 | 警報の対象 |
| --- | --- | --- | --- |
| sensor_13_avg | generator bearing 2 / Drive End温度 | `�C` | 対象 |
| sensor_12_avg | gearbox oil温度 | `�C` | 対象 |
| power_30_avg | grid power | kW | 負荷情報。警報targetにはしない |

温度のreplacement characterは原本自体に含まれる。`℃`へ修復したと主張せず、原表記/native数値を保持し、数値変換・絶対温度の業務閾値は使わない。powerは匿名化によるscaleも保持し、実設備の定格電力と同一視しない。これらの意味をbanto側の実tagへ自動対応させない。

## 分割と物理的な分離

Farm Aのassetは0/10/11/13/21。各assetの最小event IDをanchorにする。anchorは0→0、10→3、11→25、13→14、21→13で、**学習・validationにはanchorのtrain区間だけ**を使う。他fileの重複し得るprefixを繋がない。

| fold | test asset | validation asset | train assets |
| --- | --- | --- | --- |
| 0 | 0 | 10 | 11,13,21 |
| 1 | 10 | 11 | 0,13,21 |
| 2 | 11 | 13 | 0,10,21 |
| 3 | 13 | 21 | 0,10,11 |
| 4 | 21 | 0 | 10,11,13 |

各test assetの全fileを保持し、22件を一度ずつtestにする。validation anchorはtrain prefixの先頭70%をcheckpoint選択、後半30%をalarm校正に分離。train/validation/test assetはfold内で完全に分かれる。fold間の学習assetは重なるため5独立試験と解釈しない。

- [入力専用root](../../artifacts/care-input-contract-20261016/input-manifest.json)と[学習recipe](../../artifacts/care-input-contract-20261016/learning.json)：3信号とstructural lineage、固定source/splitだけ。event label/境界/descriptionやlabel pathを含めない。
- [評価者専用root](../../artifacts/care-evaluator-contract-20261016/evaluation.json)と[label manifest](../../artifacts/care-evaluator-contract-20261016/label-manifest.json)：truthと採点条件。学習・警報consumerへ渡さない。
- split/入力側bytesを保存した後にlabel側を処理した。5種類のtruth key注入を拒否する境界検査がpass。これは今回のmanifest検査で、未実装のCARE learnerやOSアクセス制御まで検証したものではない。

label metadataは既に監査で参照しており、未知の正式holdoutとは呼ばない。将来の学習/推論consumerでは、全5foldの予測・警報をfreezeするまで評価labelを渡さない。

## 固定した評価と残る工程

詳細は[固定契約](../research/care-a-maintenance-contract-2026-10-16.md)、[設定JSON](../../examples/configs/care-a-maintenance-20261016-r1.json)。一つのfull forecasterを、過去powerの負荷binで温度中央値を出す単純基準と比較する。警報は観測時点での温度残差を使い、閾値はvalidation prefixの99.5%点、3連続超過/3連続解除で固定。testのstatusやevent labelで警報条件を変えない。

主評価はevent検知・正常record-hour当たり誤警報・警報時間割合・missを0に含めたearliness。`event_start..event_end`は**故障へ至る推定異常期間**なので、その区間内の検知を主とする。終端への先行時間はproxyであり、実故障や点検に必要な時間とは認定しない。残差警報は対象実績の利用可能時刻からしか出せない。

長いcontextによる欠損後の無予測時間を隠さず、baselineのnative support結果も必須にした。共通支持の最低70%は、センサー数量を見る前に、構造だけの最小可用率77.7003%を踏まえて固定した研究上の床。全eventを保持し、品質不良後にfile/assetを差し替えない。数値finite検査とevent内支持の確認はまだで、満たさなければ不成立で保存する。

次は固定22file/3信号の数値入力・quality maskを作り、実consumerの時点/label境界と支持を確認する工程。今回は**sensor float decode0、CARE学習0、予測/採点0**。計画固定と数量品質・モデル性能の成立を混同しない。課題がなければmetadata監査を繰り返さない。

## 保存・資源・Rust

[metadata監査](../../artifacts/care-metadata-inventory-20261016/summary.json)は親122.569秒、child peak RSS51,134,464Bで900/870秒・各2GiB内。[時点/label整合](../../artifacts/care-contract-support-20261016/summary.json)、[契約固定](../../artifacts/care-contract-freeze-20261016/summary.json)もexit0。全source/stdio/exit/partial-failure口/closureを保存し、旧README/原本/M1/失敗/closed rootsを改変しない。artifact normal24file/768MiB・single32MiB、全体32file/1GiBと失敗reserve、Evidence16MiB/512file・part256KiB等の既存上限を維持した。

Rustの最終目的は**学習・推論の両方とbanto統合**。今回の3信号順・dtype/欠測mask・時点・model/optimizer/checkpoint・alarm state/reset・label gateを移植契約として保持する。実Rust実装/学習再開/製品採用は未確認。Macでのmetadata/契約検証を、Windows native/OS依存suiteの成功にしない。需要の2014以前/同休業mean28/四季非悪化/評価分離と2015停止、heartbeat PAUSEDを維持する。
