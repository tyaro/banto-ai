# consumer入出力・保存契約の具体化

2026-09-25 JST。[契約案](../anomaly-v03-consumer-io-proposal.md)を作成した。提案ID `anomaly-v03-consumer-io-proposal-v1`、状態draft。正式運用方針の採択、実装の接続、S4/S6受入、正式評価の実行はまだ行っていない。

入力mode/契約/外部anchor/source/runtime/出力/予算、順次読取りから独立auditまでの8工程、予定payload、完了前後の失敗処理を具体化した。旧formal gateや科学config/schema/registryは変更していない。単一writerと更新時の実値記録を維持し、保留principalは再開しない。

10consumerモジュールの22関数と正式schemaの必須10欄を対応づけた。現行reader・集計の120区間/720評価固定、dev/smoke限定、fixture adapterとfull documentの違いを明記。既存720評価を40holdout/2,880評価に加算しない。

sliceは凍結schemaの一意keyと単一metricの制約から、主analysisにはincident recallとscore availability、別diagnosticsに4系列すべてを保存する案とした。予定の主slice1,233行/sidecar2,835行は在庫の設計値で、実行結果ではない。補助sliceは記述値とし、CI/有意差探索/gateを追加しない。formal mappingは未採択。

新しい接続の確認をT01〜T12の12群として整理した。既存の対応test methodが存在することをASTで確認し、旧合格試験の再利用と新入口の接続検査を分けた。**この12群を実行・合格したわけではない**。今回の整合確認は、22関数の実在、12test参照の実在、schemaの必須欄・固定40/50,000/2,000,000値・9表・slice構造、23ファイルのpin、文書link/diffである。

OUT `artifacts/consumer-io-contract-2026-09-25` に `contract-map.json`、`verification.json`、resource/start、確認scriptを保存。起点は `0b75c1ea89a15e04dbde0963ae2b634648a10201`、前保存点manifest6,612bytes/SHA256 `c865ee66dc19471c99dc25992d8fc9b4b6c91f14171080066d264623282b4133`。最終文書revisionとartifact/docのhashは同OUT `savepoint-evidence.json` を参照。

資源の前後観測はprocess peak private22.72MiB、空きRAM最小11.67GiB、commit余裕最小20.34GiB、C124.98/D293.92GiB。リーク有無は点観測だけで断定しない。新評価・観測読取り・bootstrap・試験実行は0。元payloadや既存720評価を再検査していない。

前保存点、実計算checkout c01d1c9、本流clean6f1285d、closed、既存dirty guardは不変。manifest.pyのCRLF/LF差は未修正で、正式freeze前に別clean checkoutでraw一致を確認する。banto-24はPAUSED、保護root/account/ACL/UACに操作なし。

**次はT01〜T04の前段となるI/Oなしの入力契約validatorを、fixture/engineering専用として実装する。** 正式modeを明示拒否し、identity/coverage/失敗状態を扱う。観測reader・推論・writerの接続や正式運用方針の採択はその完了と区別する。5作業群全体やPhase 2/3の完了とはしない。
