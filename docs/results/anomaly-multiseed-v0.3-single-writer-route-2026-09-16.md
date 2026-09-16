# 単一writer評価経路と現行契約の照合

2026-09-16 JST。提案savepoint **7f1708a7450857517f28fe3b23dd05404088b73b**。
[具体的な移行案](../anomaly-v03-single-writer-evaluation-proposal.md)。今回は文書とREADMEのみ変更し、実行処理・科学計画・registry・旧gateは変更していない。

## 到達点

現行公開runnerはruntime probeと受入拒否の後に実行処理がなく、gateを外すだけでは評価を開始できない。
既存の計算関数は再利用可能だが、登録identityと全18,000行・metadata・イベント台帳を要求する。部分入力のlocal previewから検出性能を判断する経路にはしない。
旧engineはrole全体のinventoryと結果契約に結合しているため、固定6件専用のcontrollerと外側のmanifestが必要になる。
旧runtimeはOS26200.9168を固定しており、観測9445を記録する新しい運用境界も必要。現作業コピーの既存doc変更を保持するため、将来の実行は確定commitの別clean作業コピーを使う。

提案は `anomaly-v03-single-writer-v1` / `engineering-dev`。最初のdev seed・layout 0・2層・全3候補の **2 dataset / 6 evaluation / 288 profile / 86,400 score行** に固定する。
科学的な式・seed・閾値・分母等を維持し、単一writer保存とOS更新の扱いを別の運用改訂として登録する。全dev/smokeの代替や正式受入passとせず、holdoutを開かない。
上限案は全体15分・所有worker private bytes 2GiB・新attempt出力1GiB、開始条件は空きRAM4GiB/出力volume20GiB。
独立レビューP0〜P3所見0、進捗poll0。文書変更のため新規テストや重い評価moduleは実行していない。

## 読取り専用の設定検証

既存CLIを `--validate-only` で実行した。両方exit0 / configuration_valid。

| Role | Dataset | Evaluation | Score行 | 実行状態 |
| --- | ---: | ---: | ---: | --- |
| dev | 192 | 576 | 8,294,400 | not_run / output_created=false |
| smoke | 48 | 144 | 2,073,600 | not_run / output_created=false |

acceptance_status=not_completed、performance_status=not_evaluatedのまま。設定検証はruntimeや実評価の成功ではない。
登録seedの生成・evaluation・通常publicationは今回0。試行用の出力親も未作成。

## 保存と次の判断

選抜131 sourceのworkspace/Git blob一致（前回129不変・README変更1・提案追加1）。選抜は完全な依存閉包ではない。
前回公開artifact8件とmanifest不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。
証拠は `artifacts/local-evaluation-route-2026-09-16`。最終manifest26953 bytes/hash4da69a1b957a701be90f9bd2ed0851f67d6641d2bac8601bcb82c823cf04e32c、manifest込み4 files/34572 bytes（約34KiB）。
終了側観測UTC01:50:17、空きRAM16886415360/C153019449344/D171638751232 bytes（D約159.9GiB）。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00。Windows Update engineering緩和・正式pin不変。長期リーク不在は未評価。

**次はこの運用改訂を採択する判断。** 計画§9の「条件削減は新登録」に対応するため、旧条件を暗黙に外さず提案を具体化した。採択後はpolicy/manifest validatorと固定6枠planから実装し、保存・順次計算・再検証を接続してから1回の制限付き試行へ進む。
§116の単一writer方針、専用principal試験保留、旧root閉鎖・jの消費済みguardを継続。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。
