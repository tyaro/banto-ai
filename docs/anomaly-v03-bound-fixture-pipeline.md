# 結合済み架空producer入力から解析・独立検算への接続

2026-10-02。[実装](../src/banto_ai/anomaly_v03_bound_fixture_pipeline.py)、[試験](../tests/test_anomaly_v03_bound_fixture_pipeline.py)、[保存結果](results/anomaly-multiseed-v0.3-bound-fixture-pipeline-2026-10-02.md)。前工程で検証した主入力・補助入力の結合結果を外部pinで受け取り、既存の解析workerと主表/sliceの独立auditへ順番に渡す。

## 起点と受渡し

`prepare_inputs(raw, *, expected_mode, expected_pin, expected_revision, draws)` は純粋関数。最大16MiBの結合結果raw bytesと呼出し側のbytes/SHA-256を照合し、fixture専用・全予定枠完了・正式許可falseを検査する。40cluster/2,880枠、補助240セル/各12layout、coverage/profile、主count/遅延との対応を確認し、既存worker用の4ファイルをcanonical bytesへ写す。

| ファイル | 内容 |
| --- | --- |
| fixture/input.json | clusterごとの主count・診断・呼出し側が選んだ1〜8 draw。engineering_ready_assumptionはfalse |
| fixture/slices.json | 結合結果の補助内訳。分類を再割当せず保持 |
| fixture/coverage.json | 判定不能を含む全予定枠 |
| fixture/operation.json | 対象revisionと既存fixture operation |

各ファイルの上限と合計10MiBは既存workerのものを維持する。projectionには元結合結果pin、主manifest/登録/slice manifest pin、4入力pin、draws、coverage、旧失敗履歴を記録する。最新成功のために旧失敗を削除しない。

この入口は、呼出し側が保持した**検証済み結合結果の保存点**を信頼する。上流の全producer receiptやraw観測を再読込み・再集計する入口ではない。自己申告のpinを無条件に期待値に使わず、保存点から得たraw pinの由来を保持する。

## 順次実行

`run_pipeline(raw, *, expected_mode, expected_pin, expected_revision, draws, expected_document_pin, receipt_parent, receipt_name, resource_budget=None)` を呼ぶ。fixture以外は出力先に触れる前に拒否する。毎回新規directoryを使用し、既存成果物/sourceへの重複を拒否する。親の接続moduleも対象revisionのGit bytesと前後照合する。

1. 制限内で4入力とprojectionを保存し、読み戻してpinを確認する。
2. 所有analysisを1回起動し、入力・source/runtime・PID/生成時刻・終了記録・起動前の文書pinへの一致を確認する。既存5payloadも保存される。
3. 完了したanalysisのresult/evidence/documentをそのまま参照し、同じ主入力/sliceを別の所有auditへ渡す。複製やanalysis再起動で代替しない。
4. 別実装で主9表/180gateと本文1,233行・補助2,835行・詳細9表を検算する。両方の実行記録の入力pinがprojectionと一致した場合だけpipelineをverifiedにする。

既存 `calculate_with_evidence` と `audit_with_evidence` は変更しない。元handleと子の生成時刻、終了・観測error、前後source/runtime、入出力を既存validatorで結ぶ。事前受入済み全依存profileや実行コードの完全な認証へ読み替えない。

## 文書の期待pin

`expected_document_pin` は起動前に呼出し側で保持する必須の期待値。pipeline自身がanalysisの返却hashを期待値として採用したり、参照文書を計算したりはしない。

今回の保存例では新しい架空入力に対応する参照文書を同じ文書計算実装で1回作り、そのpinを保持してからanalysisを起動した。この参照値との一致だけでは独立検算にならない。その後の別実装auditが主表とsliceの数値検査を担当する。参照作成1回・所有analysis1回・所有audit1回を分けて記録する。

## 資源と失敗

共有120秒/親private512MiB/新規成果物32MiB/256entries、RAM/commit余裕各2GiB、disk余裕5GiBを維持。子は各60秒/256MiB/stdout+stderr1MiB。共有monitorを渡して入力準備からauditまで累積監視する。sample/checkpointと所有子の停止であり、純粋関数やnative callを即時中断するhard quotaではない。

analysis失敗ではauditを起動しない。audit失敗でもanalysisの成功記録は残し、pipelineはfailedにする。自動再試行・予算引上げ・元成果物削除は行わない。未終了workerの例外は元process ownerごと再送出し、呼出し側が終了確認を引き続き担う。`analysis_runs/audit_runs` は入口を呼んだ回数で、失敗時に実子が起動したかは各supervisionを確認する。

## 範囲

成功時はfixture_inference_performed / fixture_numerical_audit_performed / fixture_slice_audit_performedをtrueにする。一方、正式許可・昇格・S6・trust・execution_authenticated・full closure・analysis_authorizedはfalseのまま。正式文書のnull4欄/ready=falseも保持する。

登録観測からの導出、実seed/coverageの真正性、正式50,000反復、正式契約と全体予算の受入は別。今回writer/readerによる公開は起動しない。次はこの新しい解析・検算結果の5payloadを、既存の通常公開・別readerへ元のprojectionを保持して接続する。元analysisを再実行しない。

## 2026-10-02：producer結合済みの新解析結果への適用

[今回の保存・別reader接続](results/anomaly-multiseed-v0.3-bound-fixture-publication-2026-10-02.md)で、producer結合結果/projectionから生成・独立検算済みの新5payloadを既存経路へ渡し、10.801秒で成功した。元1,987,587bytes→公開1,987,592bytesは各末尾LFのみ。元analysis/audit再実行0、writer/reader各1回、両子exit0/reaped/error0、資源pass。本体コード変更0、82code/18data不変、既存16公開試験を再利用しsuite再実行0。 source-anchor.jsonとbound-publication-binding.jsonへ、元保存点/producer結果/projection入力と今回のpublication result/binding/marker/両役割証跡を結ぶpinを保持した。元科学payloadの状態欄は作成時点のまま保持し、今回の保存成功は外側に記録する。登録観測導出・正式契約/profile/全工程予算は未受入。次は実producerの保存形式と現在の架空入力契約の差分を具体化し、観測・score・ledgerから主/補助要約へ渡す読取り境界を実装する。小さい固定入力で既存の独立監査部品を接続し、登録・coverage・最新attempt・入力pinの食い違いを拒否する。今回の公開/readerや既存720評価を反復せず、正式契約の採択・holdout・50,000反復はまだ開かない。
