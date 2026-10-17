# v0.3 架空完成評価の保存読取りと次の役割境界（2026-10-04）

基準保存点 `294bf02`、今回のcode保存点 `2e92d58`。正式評価前の[5まとまりの受入範囲](anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)のうち、登録形式の架空完成評価を外部pin付きの保存ファイルから読む候補境界と、全工程予算の一部分を進めた。旧正式gate、25H2正式runtime pin、未使用40 seedの実観測は変更・読取り・生成していない。

## 完成した架空6評価を通した範囲

[手製fixture試験](../../tests/test_anomaly_v03_registered_completed_contract_fixture.py)は、登録holdoutのidentityとイベント予定を形式マーカーとして使い、各評価に48件の `inconclusive` profile、14,400件の `profile_inconclusive` score、処理済み20件の非検出incidentを組み立てる。6評価は全て架空の `inconclusive` 結果で、評価JSONは各8,762,192〜8,995,240 bytes、18 payloadの合計は53,215,686 bytes。`audit_saved_contract_candidate` は6件の完全schema・receipt/report・外部pin・最新attempt・報告scoreからの独立ledger・ledgerからの主count/exposure/遅延histogram一致を検査して通過した。2試験は28.021秒でpassした。

[限定保存reader](../../src/banto_ai/anomaly_v03_registered_saved_reader_fixture.py)は、呼出し側の外部pinと固定の登録identityから導いた21 fileだけを新しい架空rootで読む。相対pathはreceipt/reportから採用せず、通常file・単一リンク、サイズ、read前後、SHA-256を照合する。最新attemptに完成行がなければ古いreport/payloadを読まない。[読取試験](../../tests/test_anomaly_v03_registered_saved_reader_fixture.py)8件は31.963秒でpassし、53 MBの架空完成6評価を実際に保存してbyte境界から意味境界まで通した。receipt/評価bytesの改変、複数リンク、余分なpath、formal modeと非架空receiptは拒否した。外部pinの独立保持は呼出し側の前提であり、試験は新規保存bytesからpinを作るfixture機構と、そのpinを保持した後のdisk改変検出を確認した。

この物理配置は **invented receipt-key layout** で、現dev/smokeの実保存attempt rootや `observations.jsonl` / `event-ledger.jsonl` の名前とは異なる。`fixture_saved_files_read=true` だが、実登録保存readerではなく `real_saved_chunk_reader_used=false`、`registered_observations_read=false` である。報告score→ledger→主summaryは再計算したが、元観測→profile/score、score→条件別slice、元観測の生成、source/processの出所、実worker終了は検証していない。sliceは手製countの形と主summaryとの整合のみを確認した。`campaign_evaluations_credited=0`、`formal_permission=false`、`independent_s6_complete=false` を維持する。

## 26H2の5役割と予算で残る範囲

現26H2で実process通過を保存したのは[限定fixtureのwriter→別reader](anomaly-multiseed-v0.3-preformal-registered-contract-platform-v2-2026-10-04.md)である。数値analysis/auditの旧所有workerは25H2 engineering runtimeへ結ばれ、そのまま26H2には通せない。今回のproducer結合は純粋bytes処理で、所有producer子の実行・終了証拠ではない。既存のreader用profileと記述報告準備用analysis profileは、数値analysis/auditやproducerへ流用できない。

[連続予算測定](anomaly-multiseed-v0.3-preformal-join-budget-2026-10-04.md)は、架空宣言生成→主・slice結合→1 draw解析入力投影の親processだけを計測した。clean保存点 `2e92d58` のa3は55.640秒、選択6 sourceの作業rawとHEAD blobが一致し、監視と保存pin再照合がpassした。これは実producer、登録保存reader、所有analysis/audit、50,000 draw、公開後readerを含まず、既存の50,000 draw算術値と足して[全工程予算の合否](anomaly-multiseed-v0.3-preformal-end-to-end-budget-closure-proposal-2026-10-04.md)を出さない。

次の固定入力実験は、26H2専用の別ID/rootで数値analysis・auditのruntime scopeを版付きにし、架空40 cluster・1 drawの2所有子からwriter・readerへ、終了/reapと保存pinを順に渡すものとする。各役割の正常参照を外部pinにして別PIDで再照合し、producerの所有子と依存契約は別工程で定義する。実保存attempt layout・観測からのprofile/score・slice再導出、全5役割のsource/runtime閉包、Linux必須job、正式同形の全工程予算、独立再監査と運用契約採択を揃えるまで、S4/S5/S6は開始しない。
