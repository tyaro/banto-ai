# 単一writer方式の固定6件評価・保存後再計算

2026-09-16 JST。運用改訂確認後の「次に進めてください」を受け、`anomaly-v03-single-writer-v1` を採択。
実装savepoint **0086ffe226ed58c618f6bc001ebd0c99a90e66e9**。[実行ガイド](../anomaly-v03-engineering-evaluation.md)。

## 実装と検証

固定plan/manifest検査、実source/runtime記録、2層を保存してから6候補を順次処理するcontroller、保存済み入力による全件再計算、単一worker監視を追加した。
対象は最初のdev seed・layout 0・core/quality-stressのC0/C1/C2。role/seed/layout/candidateや上限を変更する引数はない。
通常LocalPublicationを使用し、同名の再実行・上書きは拒否。失敗を未実施や成功へ置換せず、可能な失敗manifestとjournalを保持する。
科学計画・config/schema・計算式・materializer・旧runtime/runner gate・保存APIの既存実装は変更していない。

新規25件＋既存通常保存12件＝**37件pass / 7.941秒 / failure・error・skip0**。初期19件も10.729秒でpass。
小さなfixtureで固定順序、両層保存後の計算、候補間の同一入力、改変拒否、再計算、途中失敗、重複拒否、資源停止、spawn/監視障害を検証した。テスト中の登録観測生成0。
独立レビューのP2（監視の二次障害で終了結果を失う）とP3（資源値の計測期間が曖昧）を是正し、再レビュー指摘0/進捗poll0。repository safety/diff-check pass。
Windowsの実runtime/空き資源/所有processメモリ取得も確認した。UAC・専用principal・ACL変更はない。

## 初回の制限付き実試行

同じcommitのclean detached worktree `C:/Users/TKent/.codex/worktrees/engineering-v03-20260916` を作成。
`artifacts/anomaly-v03-engineering-dev/trial-01` へ1回だけ実行し、**exit0 / complete / 6 success・0 inconclusive・0 failed・0 not_started**。
全360対象sourceをGitと作業コピーで照合。2 dataset / 288 profile / 86,400 score行を保存した。
公開前にpair再生成と全評価再計算を行い、writerを閉じた後も全件をreaderで再検証。`local_verified=true`、payload41件。
marker SHA256: `ebe96bacce7ec85bf032fc196c383efa3a5a01a09a99f0d23521e9a60b615106`。

| 実測 | 値 | 上限 |
| --- | ---: | ---: |
| 全worker時間（両再計算・終了を含む） | 572.048秒（約9分32秒） | 900秒 |
| peak private bytes | 337,215,488 bytes（321.59MiB） | 2GiB |
| 出力（trial/control計46 files、marker二名を含む論理量） | 132,553,275 bytes（126.41MiB） | 1GiB |

所有worker PID31828の終了を確認。stop_reasonなし、observation_errors空。監視のモデル進捗照会ではなくローカルsupervisorで資源を監視した。
manifest内の計測は最初の計算・保存段階まで（189.136秒/254111744 bytes/manifest除外payload132460659 bytes）。上表の試行全体値は `trial-01-control/supervision.json` による。
保存の完了印だけでは成功とせず、終了監視記録と最後のreader成功receiptを合わせて確認した。

## この1 seed/layoutで得た値

下表は保存済み各evaluationの分子/分母であり、全devや性能gateの合格ではない。1条件だけで候補選定・閾値変更をしない。

| 層 | 候補 | 機械異常検出 | センサー異常検出 | Precision | clean区間の誤警報episode |
| --- | --- | ---: | ---: | ---: | ---: |
| core | C0 | 0/10 | 0/10 | 0/3 | 3 |
| core | C1 | 10/10 | 10/10 | 20/20 | 0 |
| core | C2 | 4/10 | 10/10 | 14/20 | 0 |
| quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 |
| quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 |
| quality-stress | C2 | 4/10 | 9/10 | 13/19 | 0 |

## 拡張時の概算と次工程

同じ6件単位の実測を単純に倍数化した概算。seed/layout差・bootstrap・独立consumer・追加証拠/余裕容量は含まず、上限保証や正式な容量freezeではない。

| 範囲 | 評価数 | 1 workerでの概算時間 | 出力概算 |
| --- | ---: | ---: | ---: |
| 全dev | 576 | 約15.3時間 | 約11.9GiB |
| 全smoke | 144 | 約3.8時間 | 約3.0GiB |
| 合計 | 720 | 約19.1時間 | 約14.8GiB |

**次は、保存済み6件を使う独立consumerの検査項目と、全dev/smokeへ拡張する固定inventory・中断時の進行記録を設計する。** 現行CLIの固定対象や上限をその場で拡大せず、新scopeの受入・consumer revision・runtime inventoryを整理してから長時間実行へ進む。今回の完了だけではholdoutを開かない。

証拠は候補worktreeの `artifacts/engineering-evaluation-2026-09-16`（6 files/54234 bytes）と実行用worktreeのtrial/control。
trial-evidence44532 bytes/hash1ca9c3a33eca0adc60a36526dcfb12c8d336542d9dc48b67ead80969fbb478a2、最終manifest1060 bytes/hasha22b4bd142a046b7833556a6c3dbe2e535df48849f2c8aa127e5ba854396cb58。
前回公開3 artifactsとmanifest不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。
終了後UTC02:24:22、空きRAM17062436864/C152602251264/D171823501312 bytes（D約160.0GiB）。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00を記録。Windows Update engineering緩和・正式pin不変。worker終了を確認したが長期リーク不在までは主張しない。
§116の専用principal試験保留、旧root閉鎖・j/診断guard消費済みを維持。専用principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
engineering_trial_completed=true。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。
