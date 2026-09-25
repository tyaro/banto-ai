# consumer source/runtime候補と固定方法の整理（2026-09-25）

[固定方法と判断資料](../anomaly-v03-consumer-source-runtime-plan.md)。対象`e9826bd0245cf26cf540e1ff470528c001f3cd5f`、OUT `artifacts/consumer-source-runtime-review-2026-09-25`。今回はsource変更・実freezeを行わず、静的候補と起動条件を記録した。最終文書revision/pinはsavepoint-evidence.json。

## 確認内容

- 5役割の依存候補は、writer23、reader25、架空推論/文書17、独立監査部品15、inspection19。重複除外41source/566551bytes。
- 39sourceはworking/Git raw一致。generator.pyとmanifest.pyはCRLF/LF差のみで、正規化後一致。既存sourceを変更していない。
- 設定/build/workflow等18fileはすべてraw/Git一致。追加CLI2fileも一致。13method参照をfile/line/pinへ対応づけた。
- 外部top-level import33名はstdlib候補。動的/native/subprocessの15箇所を記録した。完全依存閉包とはしない。
- 直近4保存点の54試験結果と8つのsource/test pinを照合。新unit test実行0、旧suiteや720評価の再計算なし。

Pythonの起動probeを2回実施。現reader相当の-I -Bではsystem site-packagesが検索対象、-I -S -Bでは除外された。両方ともproject moduleはimportしておらず、consumer/evaluatorを起動していない。両probeのOSはProfessional25H2/26200.9457、CPython3.14.0で一致。Python exe/DLLのhashを記録。DLL/CRT/stdlib全体の受入やreader子processの完全runtime観測ではない。

Gitは2.51.2.windows.1のpath/version/実行file hashを記録した。consumerのPATH解決やGit helper/DLLの固定は未実装。旧240h/96GiB/空き32GiBの予算案は外部保存点から照合して再利用し、再計算・設定適用していない。

主確認7.670秒、最大private 52.37MiB、最小空きRAM 10.26GiB / commit余裕 18.97GiB、主確認後C/D 124.43/370.49GiB。 機器の長時間リーク試験ではない。資源値は当該短時間確認の観測である。

## 成果と残件

freezeまでの6作業と将来の採択2まとまりをfreeze-plan.jsonへ保存。採択は運用契約と完全予算で、consumer/証拠結合・正式推論/audit予算を先に具体化する。現時点で実行許可を求めたり、既存の更新許容方針を取り消したりしていない。

次はreaderの-I -Bへ-Sを追加し、通常権限の小さい接続試験で固定する。その後source/runtime証拠の入力validatorを具体化する。現readerの6source pinは、今回の静的25候補の完全closure確認ではないことも記録した。

新評価、登録観測読取、bootstrap、正式freeze、正式受入0。旧保存点、実計算c01d1c9、本流clean6f1285d、closed、既存dirty guardは不変。banto-24 PAUSED、formal/promotion/S6/trust=false。
