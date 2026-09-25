# consumer入力宣言の純検査

2026-09-25 JST。[APIと構造](../anomaly-v03-consumer-input.md)。実装savepoint `3fb988292e433311cfd86f00c773b8f17384a750`、起点 `befff6bc81a6c20c628594b2fce07bb8987fa5f5`。

`anomaly_v03_consumer_input.planned_input` / `validate_input` を追加した。fixture専用の1区間6評価、または登録済みdev/smoke全120区間720評価のmetadataを扱う。formal/未知mode、権限を主張する余分な欄、identity/order/coverage不整合、入力6種のpin不一致、不正なretry履歴を拒否する。正式API・旧720固定consumer・科学config/schema/registryは変更していない。

chunkごとのattempt履歴を保持し、成功済みの一部評価を含む失敗attemptから、同一区間の新attemptへ進んだ履歴を表現できる。最新attemptだけからcoverageを導出し、過去のfailure/evidenceも返す。integrity失敗後のretryや、既知入力hashの変化は拒否する。これは再試行の実行許可ではない。

profile inconclusiveは入力/result参照を持つ完了評価として残し、qualifiedやsuccessにはしない。全chunk完了でもproducerの終了・公開参照が欠ければcomplete宣言を拒否する。公開後に監視がfailedとなった宣言は、markerを保持したまま完了とは分ける。

新規 **22試験、failure/error/skip0、0.268秒**。小さな架空metadataと、生成した全720枠の登録metadataを使用し、実観測は使っていない。拒否順序、欠落/重複/順序、6種pin、bool/int、全coverage、partial/failure/inconclusive、履歴保全、公開後失敗、non-mutation、JSON roundtripを確認した。ファイルopen・process起動・bootstrapを拒否するpatch下でも検査が通り、I/O入口を呼ばないことを確認した。既存算術・保存試験の再実行はしていない。

外部digestはcanonical metadataへの束縛だけで、payloadや実行の認証ではない。常に実行/解析/正式許可、input bytes検証、source/runtime受入、trust、promotion、S6完了はfalse。次のI/O adapterや実データへの適用は未実施である。

OUT `artifacts/consumer-input-validator-2026-09-25` にtest log、結果、前後資源、source pin、保全境界を保存。前保存点manifest8,226bytes/SHA256 `14915cf458eeac6d2aac5e6797c1031683c632fd73ca09268367fee1e1ff778b`。最終文書revisionとartifact/docのhashは同OUT `savepoint-evidence.json`。

検証process peak private29.58MiB、前後観測の最小空きRAM12.93GiB/commit余裕20.23GiB、C124.32/D294.53GiB。新観測・評価・score・実bootstrapは0、実payload読取0。点観測だけでリーク有無は断定しない。

旧保存点/23参照ファイル、実計算c01d1c9、本流clean6f1285d、closed、dirty guardは不変。manifest.py改行差は保全、banto-24 PAUSED。保護root/account/ACL/UACへの操作なし。正式運用方針・slice mappingの採択やS4/S6・Phase2/3全体の完了にはしない。

**次は既存完了記録から入力宣言への変換adapterを、decoded metadataだけで実装する。** identity・最終attempt・失敗履歴・input pinsの対応を固定し、出典を外部anchorへ結び付ける。実観測の再読取りや再計算、正式modeの開通はその作業に含めない。
