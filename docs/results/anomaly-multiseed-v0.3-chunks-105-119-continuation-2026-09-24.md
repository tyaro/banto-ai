# v0.3 区間105〜119（残り15区間）の診断付き継続

2026-09-24 JST。ユーザーの「次に進んでください」に従い、完了保存点3307826745b37479e1d2b2d3d118087ce9fa65bdから、**control000008・最大15新規区間（105〜119）/90評価**を起動した。開始時の確定分は105区間/630評価。今回の15区間は実行中であり、完了を主張しない。

## 起動と保全

実計算sourceはclean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`。出力は `artifacts/v03-runs/r1`。開始pinは最新 `run/control/000007/closed.json` / raw SHA256 **04f198137bbcace5176734e594e5cf3fb9a19c422a7186c002b50a78ab52035c**、prepared hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7**。旧control000006のMemoryError記録と原因調査、診断付きcontrol000007の正常終了証拠を保持する。

起動UTC **2026-09-23T21:56:11.2515275Z**（JST **2026-09-24 06:56:11**）、controller PID **36728**、非表示background process。直前に既存Banto Python processがないことを確認。今回のwrapperと証拠は候補 `artifacts/chunks-105-119-continuation-2026-09-24/` に分離した。

起動前に直前の6769ファイルを1回hash照合し、過去の成功/失敗/原因調査/診断検証を含む154保持pinも一致した。baseline.jsonとpreserved-artifacts.jsonへ記録し、数値再計算はしていない。開始前照合は27.551秒。直前manifestは11938 bytes/SHA256 **edb33338a5fc6be033b18feae64eb64dc462a63c1de068c2a7bfd6a395824bf9**。本流889cfc3と実計算sourceはclean、候補の既存dirty親policy文書8461 bytes/SHA256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621** は変更しない。

## 上限・所要時間

上限48時間/32GiB、workerの制限は維持。累積活動134242.935420秒（前回の失敗時間を含む）、残り38557.064580秒（約10.71時間）から継続する。前回の観測に基づく今回の目安は約9.03〜9.06時間、全体の累積は約46.32〜46.35時間。既存105区間の再照合約5.2時間を含む。追加出力は約1.85GiBと見積もる。負荷・seed/layout・再照合の増加によって延びる可能性があり、完走保証ではない。詳細はcontinuation-estimate.json。

chunk_admission_seconds=2460の予約を含めて残り予算に収まる見積り。実際の予算検査は区間境界で協調停止し、上限変更や追加invocationを自動で行わない。成功時の終端は全120区間/720評価・journal360・status=completed・next_unverified_chunk=null。最終区間119の後にnext120/yieldedと誤判定しないよう、保存collector/finalizerの条件も合わせた。

## 診断と開始確認

外部helperは検証済み27346e985924cdcfde829faca83751824fd11ab1、SHA256 **4c44f9de74f5e3207efce471442be55b4ebb7f650968578fd1887602b7531c72** の同一コピー。固定sourceを変えず、既存60秒threadで空きRAM/C/D、controller private/peak、システムcommit/pagefile、監査中区間、診断エラー/欠落を記録する。ログ上限16MiB。worker所有・終了処理は保持した。今回の変更は外部wrapperの対象番号/上限、保存collectorの終端条件で、差分とPython構文を確認した。検証済み診断helperの回帰試験・数値評価は再実行していない。

preflight空きRAM/C/Dは約12.87/142.25/412.81GiB、commit余力15.55GiB。Windows26200.9457/CPython3.14.0、exe/DLL hashは以前と一致。OS/pagefile/Python設定変更なし。

初期観測UTC **2026-09-23T21:59:11.828054+00:00**、起動後180.0秒、journal315、新規確定receipt0。active_audit={"attempt": 1, "chunk_index": 0, "sequence": 3, "status": "verified_complete"}。PID・作成日時・wrapperが一致し、stderrは空、診断エラー0/欠落0/無効化なし。空きRAM/C/Dは約13.07/142.28/412.82GiB、commit合計28.88/上限44.42/余力15.54GiB。controller private=68780032 bytes、peak=197328896 bytes。

## 保存と継続

heartbeat **banto-24** を今回のFOLLOWUPへ変更して30分間隔で再開。各回の確認は1回だけとし、新規6区間・12区間・終了時に保存する。各区間のverified receiptは自動保持。FOLLOWUP、起動情報、今回の2文書commitをlaunch-savepoint.jsonで束ね、followup-state.jsonへ保存点を記録する。

終了時は全15区間の結果、旧6769ファイル不変、所有worker終了、診断記録を照合する。最終保存後、継続確認を停止する。途中停止・異常時も記録を保全し、判断点を報告して確認を停止する。追加区間やholdoutは起動しない。

今回の完走でengineering dev/smokeの120区間が埋まっても、formal_permission=false/campaign加算0を維持する。監査は保存score以降のみ。完全runtime inventory、profile/score導出・bootstrapの独立S6、holdout/性能評価、研究ロードマップPhase 2/3全体の完了を主張しない。前回MemoryErrorの原因は未確定である。
