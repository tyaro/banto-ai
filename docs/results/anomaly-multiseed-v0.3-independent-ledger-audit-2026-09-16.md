# 保存済み6件の独立ledger検算とcheckpoint設計

2026-09-16 JST。実装savepoint **0c8377d0d55fc2813f2c18fa618c33646bc6666c**。
[検算範囲・使い方・長時間実行設計](../anomaly-v03-independent-audit-and-checkpoints.md)。

## 完了した範囲

保存scoreから閾値超過・streak・signal episode・equipment merge・最初の候補選択・causal support・context・固定母数のmetricsを別実装で再構成した。
数式側はstdlibのみで、producerのscoring/episode/matching/accounting関数を呼ばない。JSON/schema・登録event inventory・保存hash・source検査は共用する。
availabilityは保存されたavailableの集計検算であり、観測からavailableを導出する検算ではない。
profile fit/calibration、残差・score導出、正常生成式/丸め、bootstrap、性能gate、全campaignは未検算。**部分的な独立検算であり、完全S6受入ではない。**

新規**18件pass / 1.516秒 / failure・error・skip0**。手計算M1〜M9、閾値と等しい点、profile切替、推移的merge、coreの無効quality窓、欠落行による分母縮小、0 alert時のprecision=null、未検出delayを0で埋めないこと、改変入力・journal、順次6枠を検証した。
計算コードと長時間実行設計の独立レビューは各所見0/進捗poll0。safety/diff-check pass。テストで登録観測を生成していない。

## 既存結果の実読取り

producerは `C:/Users/TKent/.codex/worktrees/engineering-v03-20260916` / 0086ffe、consumerは新しいclean detached worktree `C:/Users/TKent/.codex/worktrees/engineering-audit-20260916` / 0c8377d。
producer360 source・consumer365 sourceをそれぞれ固定revisionと照合した。既存 `trial-01` の外部marker hashとsupervision hashを指定して実行。
**全6件がledger_checks_passed。** 保存score合計86,400行を起点に再構成し、全episode・incident対応・metricsが一致した。

| 層 | 候補 | signal episode | equipment episode | incident台帳行 |
| --- | --- | ---: | ---: | ---: |
| core | C0 | 3 | 3 | 20 |
| core | C1 | 30 | 20 | 20 |
| core | C2 | 42 | 20 | 20 |
| quality-stress | C0 | 3 | 3 | 20 |
| quality-stress | C1 | 29 | 19 | 20 |
| quality-stress | C2 | 39 | 19 | 20 |

同じ層の3候補は同じイベントを共有しており、台帳行を3倍の独立incidentとして数えない。
PID30824、UTC04:18:09.387366〜04:19:42.422194、監視実測**92.828秒 / peak private186466304 bytes（177.83MiB） / exit0**。
所有processへ10分/1GiB/監視ログ8MiBの上限を付け、0.25秒間隔で監視した。stop_reasonなし、観測エラー0、終了確認済み。
CLI内の資源検査は終了時のみなので、この実行では別の監視helperが途中停止を担当した。ファイル上限をprocessメモリ上限とは扱わない。
入力46 filesの外部pinと実行前後のhashが一致。登録dataset生成0、producerのprofile/score再計算0。既存生成物へ書き込みしていない。

監査JSON136370 bytes/hash `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`。
`score_derivation_verified=false`、`independent_s6_complete=false`、formal_permission=false、performance_status=not_evaluatedを報告している。

## 長時間実行の設計と次工程

metadataだけで固定順序を確認し、dev96 chunks/576 evaluations、smoke24 chunks/144 evaluations、合計120 chunks/720 evaluationsの予定表を保存した。
1 chunkは同じseed/layoutの2層×全候補6件。statusは全not_started、execution_authorized=false、producer/consumer revisionはnot_frozen。長時間controllerを実装・実行したものではない。
chunkごとの保存完了・終了監視・consumer検査を番号付きの不変journalへ記録する設計とした。markerのみは未完了、途中失敗は別attemptへ、確定済みchunkを再検証して次へ進む。旧trialを自動的に新campaignのcoverageへ流用しない。
**次はデータ生成なしで、固定campaign plan/validatorとjournalから状態を復元する処理を実装する。** 同時に、独立consumerのprofile/score導出とruntime inventoryは受入残件として維持する。長時間実行の予算・source/consumer freezeを整える前に全dev/smokeやholdoutを開始しない。

## 保存・資源・保全

証拠は候補worktreeの `artifacts/independent-ledger-audit-2026-09-16`、9 files/231008 bytes（約226KiB）。
最終manifest2479 bytes/hash `99cc2f94a5e3adfafd671e2e7e9b30dddf0bf1ad005c339fbac20c7578f3e96e`。
前回公開5 artifacts＋manifest不変。本流889cfc3/clean、producer/consumer作業コピーcleanを確認。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。
引継書の§120/122/123/121という並びを§120/121/122/123へ訂正した。各節の本文bytesが同一であることを確認してから今回の§124を追加した。
終了側UTC04:20:34、空きRAM16154693632/C151848161280/D171825594368 bytes（D約160.0GiB）。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00。Windows Update engineering緩和・正式pin不変。長期リーク不在は未評価。
§116の専用principal試験保留、旧root閉鎖・j/診断guard消費済みを継続。専用principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
independent_ledger_audit_completed=true。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。
