# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。最初にこの文書と候補worktreeのgit status/logを確認し、全履歴は必要箇所だけ読む。

## 場所と最新保存点

- 作業先: `C:/Users/TKent/.codex/worktrees/70b0/banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 実計算source: clean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、出力`artifacts/v03-runs/r1`。固定sourceは変更していない。
- 今回の最終保存先: `artifacts/chunks-81-104-retry-2026-09-23/savepoint-evidence.json`。最終commitは同manifestとfollowup-state.jsonに記録する。起動9340199、中間0c98a7d/28ca9f7/1bcbcbeを保持。
- 本流 `D:/develop/banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。
- 既存dirtyを保全・commit除外: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes/SHA256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621**。

## 目的と現在地

診断付きcontrol000007で区間81〜104の24区間/144評価がすべて成功し、累計105区間/630評価となった。終了UTC **2026-09-23T21:17:02.345893+00:00**（JST2026-09-24 06:17）、exit0/yielded/stop_reason=null、journal315/next105。controller PID40372の消失と全所有workerの終了を確認した。今回36639.971秒（約10時間11分）、累積活動134242.935420秒（前回失敗分を含む）。

保存済み6769 files/13947570419 logical bytesを照合し、開始前5227ファイルはすべて不変。各区間の監査はledger_checks_passed。終了後のcollectorは574.907秒のIO/hash照合のみで、数値計算を繰り返していない。latest.jsonは最後の60秒標本で23件のままだが、最終run-report/stdout/closed/24件の保持receiptとjournal315で全24件の完了を照合した。

最新closedは **`run/control/000007/closed.json`** / raw SHA-256 **04f198137bbcace5176734e594e5cf3fb9a19c422a7186c002b50a78ab52035c**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。旧control000006は失敗履歴として保全し、古いclosedや中間receiptを次回の再開pinに使わない。

全120区間の残りは15区間/90評価。48時間候補の残り活動時間は38557.064580秒（約10.71時間）。次回は完了済み105区間の再照合費用も含め、最新closedからの明示上限を判断する。今回のheartbeat banto-24は最終保存後に停止し、追加invocationは起動しない。

前回control000006のMemoryError停止、原因調査、外部診断の検証と全中間保存は保持する。今回の成功を前回失敗の原因解明へ読み替えない。中間receiptはclosed再開pinではない。

研究ロードマップPhase 2（予測モデル比較）/Phase 3（異常検知・ドリフト）が目標。全dev/smokeはdev96＋smoke24＝120区間/720評価。1区間は同一seed/layoutのcore/stress×3候補。実計算source c01d1c9は不変、外部診断helper27346e9を使用。監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory、profile/score導出・bootstrapの独立検算、全120/holdout/性能評価、Phase 2/3全体は未完了。

継続入口は`anomaly_v03_campaign_launcher.py` / `tools/evaluator/run_anomaly_v03_campaign.py`。同じsourceと外部prepared/最新closed hash、明示max-chunksを必須にする。未閉鎖invocationは再使用せず、終了不明workerは元ownerが保持する。48時間/32GiB候補は区間境界の協調停止で、既存区間再照合中のwrapperによる強制停止ではない。旧試行をcoverageへ加算しない。

## 検証と資源

診断は608標本/824イベント、audit_begin/end各105件（既存81＋新規24）の順序が一致。観測エラー0/欠落0/無効化なし、例外イベントなし、診断thread終了済み。controller peak235261952 bytes（約224.4MiB）、終了時private95719424 bytes（約91.3MiB）。producer最大333.0MiB、audit最大187.3MiB。空きRAM標本最小10996932608 bytes（約10.24GiB）、commit余力標本最小10455838720 bytes（約9.74GiB）。今回MemoryErrorは再発しなかったが、前回の原因解明や長期リーク不在の証明にはしない。

終了時空きRAM14128013312/C153025306624/D441718030336 bytes。最後のrun_end診断はcommit30933463040/limit47691886592/余力16758423552 bytes。Windows26200.9457/CPython3.14.0・exe/DLL hashは開始/終了・各workerで一致。Windows Updateはengineering実値を記録し旧正式pinを維持した。OS/pagefile/Python設定変更なし。

終了時診断の補足はOUT/diagnostics-summary.json、controller消失確認はcontroller-exit-check.json、全所有worker・runtime・旧5227ファイル不変はevidence.jsonに保持する。最終保存時には94保持pinと既存dirty・実計算source・本流を照合する。

Pythonは`C:/Python314/python.exe -B`、候補のimportには`PYTHONPATH=src`。外部診断helperは27346e9、SHA256 **4c44f9de74f5e3207efce471442be55b4ebb7f650968578fd1887602b7531c72**。診断12件/既存launcher16件は保存済みで、今回追加の回帰試験や数値再計算は行わない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、全dev/smoke/holdoutの長時間実行を自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [今回の区間81〜104の最終結果](results/anomaly-multiseed-v0.3-chunks-81-104-retry-2026-09-23.md)、[前回区間57〜80の結果](results/anomaly-multiseed-v0.3-chunks-57-80-continuation-2026-09-22.md)、[snapshot/launcherの操作](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜144（実装経緯・前回停止・今回成功）。全体の再読込みは不要。
- 最新の失敗・保全証拠: `artifacts/chunks-81-104-continuation-2026-09-23/failure-savepoint-evidence.json`。直前の成功証拠は`artifacts/chunks-57-80-continuation-2026-09-22/savepoint-evidence.json`（10443 bytes/SHA256 c4017dacb4a80da2a27fe90c57f53c0fab95991ce44bb8a91b969909c891f0ca）と記載49ファイル。過去の証拠は保持し、数値再計算しない。
- 以前の実6件: clean `C:\Users\TKent\.codex\worktrees\v03\banto-ai` / 25d1084の `artifacts/anomaly-v03-chunk-trials/trial-01`（68 files/133323148 bytes）。`trial-evidence.json` に全pin。完走済みで再起動不要。
- 保持する新しい失敗試行: `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387の同名trial（54 files/107889570 bytes）。261文字pathで6件目保存に失敗し、終了・failed記録済み。`failed-trial-evidence.json` に全pin。修理・再使用・削除せず、今後も登録保存pathを248 UTF-16文字未満に抑える。OS設定は変更しない。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
