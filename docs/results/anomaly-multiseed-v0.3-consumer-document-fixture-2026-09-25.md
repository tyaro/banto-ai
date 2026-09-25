# 40-cluster推論から文書草稿への接続（2026-09-25）

[API](../anomaly-v03-document-fixture.md)を追加。非登録の架空40clusterを既存算術へ渡し、9表・180gateと結果文書10項目の草稿を組み立てた。実装`e2abbdce00719db482253c140a200d0776288284`、OUT `artifacts/consumer-document-fixture-2026-09-25`。最終文書revision・全artifact pinはsavepoint-evidence.json。

## 試験・保存例

12新規試験pass、failure/error/skip0、1.085秒。旧suiteの再実行なし。40-cluster母数、絶対CIとpaired差のType-7区間を手計算と照合。overallのraw和、delayの全件結合、C1優先/C2代替/該当なし/engineering未受入を確認した。64drawの上限、余分な実入力項目、順序・母数・diagnostics不整合、schema変更、未充足欄の捏造や採択flag変更も確認した。

最初の試験10件中1件は、controlのprecision=nullを選択停止条件とする試験側の想定が誤っていた。固定ルールではcontrol precisionはpaired non-inferiority項目ではない。算術/閾値は変更せず、null保持とengineering未受入による選択停止を分けて試験した。初回log/結果/start等はtest-attempt-1に保全。

保存例は40cluster・4draw・160index、実行0.089秒。C1 coreのmachine recallは4600/4800、overall sensor検出は8880、overall delayは18080件、median4秒、mean54320/18080秒。候補の選択は架空結果だけに記載する。入力279174bytes / SHA256`0c269fc912a58533279b2c7aae832ad080805b5c36afd597002751ba3160dd93`、出力220078bytes / SHA256`2d26ad83778bc068ec41da01b9b84468a4e16b2e7c4a1a3a3b79021a769d1b5d`。保存後の再読取で構造と対応を検査し、正式validatorが草稿を拒否することを確認。

今回の測定process peak private 31.09MiB、最小空きRAM 10.01GiB / commit余裕 19.26GiB、例の保存後C/D 129.89/327.19GiB。 OS26200.9457 / CPython3.14.0を観測。短い処理の測定で、長時間メモリリークの有無は評価していない。

## 到達範囲

文書10項目中、識別値2・候補表・架空選択・架空decisionの5項目を接続。status/provenance/analysis_consumer/bootstrap/slicesはnullとして不足を明示する。正式full document、登録holdoutの推論、source/runtime受入、独立S6は未完了。5項目は全体の残作業数ではない。

新評価・登録データ読取・実データbootstrap0。架空入力での少数draw計算は実施した。旧保存点、実計算c01d1c9、本流clean6f1285d、closed、既存dirty guardは不変。banto-24 PAUSED、formal/promotion/S6/trust=false、performance=not_evaluated、実selected=null。

次は架空診断からincident recall/availabilityのslice行を作り、今回の文書草稿へ接続する。正式実行・上限変更・principal/UAC/ACL試験を起動しない。
