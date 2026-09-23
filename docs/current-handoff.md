# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。最初にこの文書と候補worktreeのgit status/logを確認する。現在は最後の15区間を実行中。再起動しない。

## 場所と最新保存点

- 候補: `C:/Users/TKent/.codex/worktrees/70b0/banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 今回OUT: `artifacts/chunks-105-119-continuation-2026-09-24`。**FOLLOWUP.md / followup-state.json** を確認する。起動commit/pinはlaunch-savepoint.jsonに保存する。
- 実計算source: clean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、出力`artifacts/v03-runs/r1`。固定sourceは変更していない。
- 直前の完了保存点: **3307826745b37479e1d2b2d3d118087ce9fa65bd**。前回OUT `chunks-81-104-retry-2026-09-23` のmanifestは11938 bytes/SHA256 **edb33338a5fc6be033b18feae64eb64dc462a63c1de068c2a7bfd6a395824bf9**。作成済みOUTは変更しない。
- 本流 `D:/develop/banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。
- 既存dirtyを保全・commit除外: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes/SHA256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621**。

## 現在の実行と次の操作

ユーザーの「次に進んでください」に従い、**control000008・区間105〜119・最大15区間/90評価**を起動。UTC 2026-09-23T21:56:11.2515275Z（JST 2026-09-24 06:56:11）、PID **36728**。確定済みは105区間/630評価で、今回分は実行中。終了状態を見ずに完了扱いしない。

最新の閉鎖済み再開pinは **control000007/closed.json** / raw SHA256 **04f198137bbcace5176734e594e5cf3fb9a19c422a7186c002b50a78ab52035c**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7**。起動前に旧6769ファイルと154保持証拠pinを照合済み。中間receiptはclosed再開pinではない。

heartbeat banto-24はACTIVE/30分間隔、今回OUTのFOLLOWUPに従う。各回controllerのPID・開始時刻・wrapper/小さな状態/資源を1回確認し、正常稼働中なら次回へ任せる。新規6区間・12区間で今回の結果文書と本書だけ中間commit。終了時に結果照合と5文書の最終保存を行い、heartbeatを停止する。異常/途中停止の場合も原本を保全して判断点を報告し、確認を停止する。追加invocationは自動起動しない。

完走時は全120区間/720評価、journal360、**status=completed・next_unverified_chunk=null**。残りが0になるが、Phase 2/3全体・正式gate・holdout完了とは扱わない。

## 予算・資源・診断

48h/32GiB候補は維持。開始時累積活動134242.935420秒（前回失敗分を含む）、残り38557.064580秒/約10.71時間。既存105区間の再照合約5.2時間＋新規15区間で約9.03〜9.06時間/追加約1.85GiBを見込む。前回実測による見積りで完走保証ではない。予算検査は区間境界の協調停止で、再照合中の強制停止ではない。

初期観測UTC 2026-09-23T21:59:11.828054+00:00、journal315・新規receipt0・active_audit={"attempt": 1, "chunk_index": 0, "sequence": 3, "status": "verified_complete"}。診断エラー/欠落0、stderr空、process同一性確認済み。空きRAM/C/Dは約13.07/142.28/412.82GiB、システムcommit余力15.54GiB。

Pythonは`C:/Python314/python.exe -B`、候補importには`PYTHONPATH=src`。外部診断helperは27346e9/SHA256 **4c44f9de74f5e3207efce471442be55b4ebb7f650968578fd1887602b7531c72** のコピー。固定sourceは変えず、既存60秒thread/16MiBログ上限。Windows26200.9457/CPython3.14.0・exe/DLL hashは以前と同じ。Windows Updateはengineering実値を記録し旧正式pinを維持。OS/pagefile/Python設定変更なし。

前回control000007は24区間/144評価成功、診断608標本/824イベントで欠落/エラー0。6769ファイル13947570419 logical bytesを最終照合済み。control000006のMemoryErrorは再発していないが原因は未確定。今回もcommit余力・再照合位置・private memoryを観測する。完全runtime inventory、profile/score導出・bootstrapの独立S6、holdout/性能評価は未完了。campaign加算0/正式許可false。

今回の詳細は[区間105〜119の結果記録](results/anomaly-multiseed-v0.3-chunks-105-119-continuation-2026-09-24.md)。直前の完了詳細は[区間81〜104の結果](results/anomaly-multiseed-v0.3-chunks-81-104-retry-2026-09-23.md)。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、今回許可された区間105〜119の15区間を超える実行やholdoutを自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [今回の区間81〜104の最終結果](results/anomaly-multiseed-v0.3-chunks-81-104-retry-2026-09-23.md)、[前回区間57〜80の結果](results/anomaly-multiseed-v0.3-chunks-57-80-continuation-2026-09-22.md)、[snapshot/launcherの操作](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜144（実装経緯・前回停止・今回成功）。全体の再読込みは不要。
- 最新の失敗・保全証拠: `artifacts/chunks-81-104-continuation-2026-09-23/failure-savepoint-evidence.json`。直前の成功証拠は`artifacts/chunks-57-80-continuation-2026-09-22/savepoint-evidence.json`（10443 bytes/SHA256 c4017dacb4a80da2a27fe90c57f53c0fab95991ce44bb8a91b969909c891f0ca）と記載49ファイル。過去の証拠は保持し、数値再計算しない。
- 以前の実6件: clean `C:\Users\TKent\.codex\worktrees\v03\banto-ai` / 25d1084の `artifacts/anomaly-v03-chunk-trials/trial-01`（68 files/133323148 bytes）。`trial-evidence.json` に全pin。完走済みで再起動不要。
- 保持する新しい失敗試行: `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387の同名trial（54 files/107889570 bytes）。261文字pathで6件目保存に失敗し、終了・failed記録済み。`failed-trial-evidence.json` に全pin。修理・再使用・削除せず、今後も登録保存pathを248 UTF-16文字未満に抑える。OS設定は変更しない。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
