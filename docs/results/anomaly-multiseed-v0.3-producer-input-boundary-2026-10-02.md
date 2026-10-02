# 架空producerからconsumer主集計への入力境界

2026-10-02 JST。[API](../anomaly-v03-producer-input-fixture.md)。登録、全予定枠、最新試行、供給入力bytes、要約count、全体終了記録を結ぶadapterを追加した。実観測を読む前の、I/Oなし・fixture専用の実装である。

開始文書revision a0aee2ff732c45173cab1da4b3e5d804e1e5d65c、実装35032159133aa4d3866863b555bd23a3718f07be、clean候補pi01/banto-ai。新module/testの2本だけを追加し、旧76code/18dataはraw pin不変。今回78codeとなる。最終文書revision/pinはOUTのsavepoint-evidence.jsonへ保存する。

前保存点 artifacts/fixture-publication-2026-10-01/savepoint-evidence.json は43,429bytes、SHA256 16c93767a452d7c9169f9cb0bd0a8c4d50c18a87df9c7cc812c4dd87ce7de5e3。旧公開記録と候補fp02は保持し、旧試験/analysis/audit/writer/readerは再実行していない。今回の23試験と過去の試験結果を同じrevisionでの全回帰passとは表現しない。

## 検証

新23項目が全pass、failure/error/skip 0、2.584秒。[試験結果](../../artifacts/producer-input-boundary-2026-10-02/tests-1/test-results.json)、[詳細ログ](../../artifacts/producer-input-boundary-2026-10-02/tests-1/tests.log)。外部pin、欠落/余分/同数差替え、全identity/順序、候補間input、summaryの別枠流用、分母/precision/delay/型、旧失敗/最新失敗、未開始、failure証跡、終了記録の矛盾、上限、正式modeの早期拒否を検査した。

40 clusterの保存例は2.539秒。480区間/2,880最新評価枠に対してattempt481、旧失敗履歴1件、最新success2,879＋inconclusive1を保持した。ゼロ分母のprecisionも残し、全profile成功へ補正していない。これは架空記録の結合・加算で、新評価は0。

| 保存対象 | bytes | SHA-256 |
| --- | ---: | --- |
| manifest.json | 1,397,735 | dd39ae6f1e400343c764396239422a37e15afd1bcc5cb909fd8cd2208ad95b4b |
| snapshots.jsonl | 10,128,441 | 0f22119185c46a405ca4e18740e4dcb7eb8fdf0840e0ef26340438079f81de61 |
| bound-inputs.json | 1,118,312 | 88aafc8e78a21c9ea433b8da042155e40eb74e6d44407a107402af70d53e93aa |

論理payload9,123件/8,685,031bytesとmanifestを照合した。JSONLは各論理pathとraw UTF-8 bytesを1本へ格納した容器で、実ファイル件数とは異なる。終了保存時にも容器内の全pin/inventoryを確認するが、集計を再実行しない。

[保存例の結果](../../artifacts/producer-input-boundary-2026-10-02/tests-1/full-invented-example/result.json)、[出力](../../artifacts/producer-input-boundary-2026-10-02/tests-1/full-invented-example/bound-inputs.json)、[形式接続の結果](../../artifacts/producer-input-boundary-2026-10-02/tests-1/full-invented-example/compatibility-check.json)。既存document入力、diagnostics、wrapper coverageの形式に接続できた。drawを使った数値計算はせず、owned worker起動0、推論/audit/公開再実行0。

## 資源と保全

[資源記録](../../artifacts/producer-input-boundary-2026-10-02/tests-1/full-invented-example/resource-budget.json)。保存例は12sample、監視errorなし・終了確認済み、親peak private 80.33MiB、監視中directory最大12.06MiB、commit最小余裕27.16GiB。120秒/512MiB/32MiB等の既存上限は据置き。診断保存用の予約を含み、監視中の最大値は最終成果物総量とは区別する。

保存例後RAM空き14.70GiB、C/D空き114.77/384.81GiB。短い観測でメモリリークの有無は断定しない。最終OS/資源はsave-checks.jsonに保存し、旧formal OS pin9168を更新しない。実計算c01d1c9・本流clean6f1285d・closed・既存dirty文書/改行差・旧候補を保持。banto-24 PAUSED、principal/保護root/UAC/ACL/同時書換え保留、push/mergeなし。

## 到達点と次工程

信頼された呼出し側が保持する期待pinへ、供給された架空bytesと宣言を結び付けた。実producerの過去の実行やraw観測から要約への導出を認証したものではない。未完了なら集計を返さず全枠と失敗を保持し、最新結果だけを採用する境界を具体化できた。

実登録データの読込み・新評価・既存720評価の再実行・推論/正式50,000反復は0。正式契約、登録観測から要約への導出、実producerの実行認証、最終役割profile、全工程予算の受入は残る。formal/promotion/S6/trust/execution_authenticated/full closure=false、analysis_authorized=falseを維持する。

次は架空producerのslice/sidecar用要約を同じ登録・入力pin・最新attemptへ結合する。主集計と補助集計の対応を検査し、既存720評価や保存済み解析・公開を再実行しない。 この入力は主count/有効時間/delayまでで、既存slice auditの正しさとproducerのslice入力の結合は別の残件。Phase2/3全体は未完了。
