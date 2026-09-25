# 架空40clusterのslice文書接続（2026-09-25）

[API](../anomaly-v03-slice-fixture.md)を追加し、架空診断から本文1,233行と4系列の補助表2,835行を作成した。実装`52a032bf8bb22a1eee301ba0cb6d4bbb77a35bed`、OUT `artifacts/consumer-slice-fixture-2026-09-25`。最終文書revision・artifact pinはsavepoint-evidence.json。

## 確認結果

13新規試験pass、failure/error/skip0、16.694秒。旧suiteの再実行なし。40clusterの各cellと全体についてcounts・delay・profileを照合し、class/equipment/modeの周辺表と結合表、target/modeの対応も確認した。全体の合計が変わらないcluster間delay入替え、結合表内の移し替え、target/mode間の件数移動は拒否した。

本文の行inventory・一意性、4系列の分子の区別、overallのraw和、分母0と検出0のnull、入力の不変性、誤った入力/digest・出力改変・採択flag変更を確認。主CIを再計算する関数を禁止した状態でも接続・照合が通る。

前工程の入力・主表を外部保存点pinから読み、既存主CIを再計算せずに接続例を保存した。接続処理1.831秒。C1 core machineは4600/4800、target利用可能率は838080/864000、overall sensorは8880/9600。minus-2参照は予定19200、対象外4800、試験外960、試験内13440、利用可能6720。利用可能率の分母には13440を用い、予定19200へ置き換えていない。

診断入力は4,337,681bytes / SHA256`820ef31286fa1f572f8ffb9c1839695c4aefe2e7d29bb5565cb23076edac5844`。接続後文書は3,162,172bytes / SHA256`1673653d73b9666fada8d3e7857ca2532846029912b84241784c80d3cfacce56`。保存後に読取り、元countsとの対応と正式validatorによる草稿の拒否を確認した。

測定processの最大private 70.88MiB、最小空きRAM 9.98GiB / commit余裕 18.87GiB、例の保存後C/D 125.54/370.16GiB。 OS26200.9457 / CPython3.14.0を記録。短い処理の測定で、長時間メモリリーク試験ではない。

## 範囲と次の作業

草稿10項目中6項目の配置まで接続。未充足はstatus/provenance/analysis_consumer/bootstrapの4欄。slicesを埋めたことは正式mapping採択、実観測からの導出、正式文書の受入を意味しない。4欄はプロジェクト全体の残件数ではない。

新評価・登録データ読取・実データbootstrap0。試験で架空の主表を作る少数draw計算は行い、保存例では前工程の主表を再利用した。既存算術/schema/consumer入口は変更していない。旧保存点、実計算c01d1c9、本流clean6f1285d、closed、dirty guardは不変。banto-24 PAUSED、formal/promotion/S6/trust=false、実selected=null。

次はsource/runtimeの依存一覧・固定方法を最新consumerに合わせて整理し、正式実行前の残件と判断資料をまとめる。正式freeze/holdout実行・上限変更・principal/UAC/ACL作業は開始しない。
