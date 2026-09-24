# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**区間105〜119の呼出しはMemoryErrorで停止・保全済み。自動再起動しない。** 最初にこの文書と候補worktreeのgit status/logを確認する。

## 場所と保存点

- 候補: `C:/Users/TKent/.codex/worktrees/70b0/banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 今回OUT: `artifacts/chunks-105-119-continuation-2026-09-24`。failure-evidence.json/diagnostics-summary.jsonに停止証拠、failure-savepoint-evidence.json/followup-state.jsonに最終commitを保持。起動保存点5bcb3cfa913f6dca7388678ca4818804f4c0a68c。
- 実計算source: clean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、出力`artifacts/v03-runs/r1`。固定source変更なし。
- 直前成功: **3307826745b37479e1d2b2d3d118087ce9fa65bd**、旧OUT `chunks-81-104-retry-2026-09-23` のmanifest11938 bytes/SHA256 **edb33338a5fc6be033b18feae64eb64dc462a63c1de068c2a7bfd6a395824bf9**。最終保存済みOUTは変更しない。
- 本流 `D:/develop/banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。
- 既存dirtyを保全・commit除外: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes/SHA256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621**。

## 現在地と判断点

control000008は既存区間58の保存データを再照合中、MemoryErrorでexit2となった。終了UTC **2026-09-24T00:55:23.946366+00:00**（JST **09:55:23**）。新規区間の開始・確定は0、journal315/next105とcheckpointは前回のclosed000007と同一。累計**105区間/630評価**、残り**15区間/90評価**を維持する。

controller PID36728の消失、診断threadの終了、inspection worker PID20240の終了確認済み。新規producer/audit試行は作成されていない。heartbeat **banto-24はPAUSED**。同じinvocationの再使用・追加起動はしない。

最新closedは **control000008/closed.json** / raw SHA256 **02531b247b12b1275a57c8907924f5ac710c90c4d8dfd079f885d0fd2d5c9211**（failed/exception）。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7**。旧000007や中間receiptを最新再開pinにしない。

今回は10751.957秒、累積活動144993.320914秒（約40.28時間）。48時間候補の残りは27806.679086秒（約7.72時間）。前回見積りの105区間再照合＋残り15区間は約9.03〜9.06時間で、残予算を上回る。次の判断は原因調査と再開方法/累積予算の見直し。無条件再試行や上限変更はしない。

## 今回の診断で分かったこと

今回はtracebackを保存でき、最深部は実計算sourceの `_anomaly_v03_io.py:101` / `read_regular` の `stream.read()`。呼出し元は保存datasetの読込み（`anomaly_v03_saved_audit.py:60`）。失敗したpayloadの個別path・割当要求サイズは記録されていない。既存区間0〜57の再照合を終え、58で失敗した（audit_begin59件/end58件）。例外2イベントは同じMemoryErrorが監査とcontinue_runへ伝播した記録であり、別々の2回の停止ではない。

診断は177周期標本/303イベント、観測エラー0/欠落0/無効化なし、診断thread終了済み。直前周期標本から最初の例外資源標本まで52.417秒で、system commitが30.79→57.35GiB（+26.56GiB）、pagefile確保量が12.72→29.40GiB（+16.68GiB）へ変化した。例外直後標本のcommit上限は61.10GiB、余力3.75GiB、空き物理RAM12.56GiB。標本は割当失敗そのものより後であり、失敗瞬間の余力を確定するものではない。

controllerのOS peak privateは233918464 bytes（約223.08MiB）、終了時private143798272 bytes。大きなsystem commit変動とpagefile拡張は実測したが、急増分を割り当てたprocessは診断対象に含まれていない。Bantoのメモリリークや特定の他process、pagefile拡張遅延のどれかを原因と断定しない。

## 保全・検証

旧6769ファイルの一覧/サイズは不変、journal315ファイルはhash一致、closed checkpointは前回と同一。新規はcontrol8の6ファイルだけで全6775ファイル。6ファイルのコピーとhash、過去154保持pin・起動時18immutable artifactsを照合済み。旧数値payload全体の再hashや成功用collector/finalizer、数値計算は行っていない。詳細は[停止記録](results/anomaly-multiseed-v0.3-chunks-105-119-continuation-2026-09-24.md)、長い引継書§145。

Pythonは`C:/Python314/python.exe -B`、候補importは`PYTHONPATH=src`。外部診断helperは27346e9/SHA256 **4c44f9de74f5e3207efce471442be55b4ebb7f650968578fd1887602b7531c72**。Windows26200.9457/CPython3.14.0・exe/DLL hashは開始/終了で一致。Windows Updateはengineering実値記録を許容し旧正式pinは維持。OS/pagefile/Python設定変更なし。

campaign加算0/正式許可falseを維持。監査は保存score以降のみ。完全runtime inventory、profile/score導出・bootstrapの独立S6、全120/holdout/性能評価、研究ロードマップPhase 2/3全体は未完了。実装変更・追加agent・回帰試験・push/merge/CI・OS/権限設定変更なし。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [直前成功の区間81〜104の最終結果](results/anomaly-multiseed-v0.3-chunks-81-104-retry-2026-09-23.md)、[前回区間57〜80の結果](results/anomaly-multiseed-v0.3-chunks-57-80-continuation-2026-09-22.md)、[snapshot/launcherの操作](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜145（実装経緯・直前成功・今回停止）。全体の再読込みは不要。
- 今回の失敗証拠: `artifacts/chunks-105-119-continuation-2026-09-24/failure-savepoint-evidence.json`。前回MemoryErrorの証拠は`artifacts/chunks-81-104-continuation-2026-09-23/failure-savepoint-evidence.json`。直前成功は`artifacts/chunks-81-104-retry-2026-09-23/savepoint-evidence.json`（11938 bytes/SHA256 edb33338a5fc6be033b18feae64eb64dc462a63c1de068c2a7bfd6a395824bf9）と記載59ファイル。過去の証拠は保持し、数値再計算しない。
- 以前の実6件: clean `C:\Users\TKent\.codex\worktrees\v03\banto-ai` / 25d1084の `artifacts/anomaly-v03-chunk-trials/trial-01`（68 files/133323148 bytes）。`trial-evidence.json` に全pin。完走済みで再起動不要。
- 保持する新しい失敗試行: `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387の同名trial（54 files/107889570 bytes）。261文字pathで6件目保存に失敗し、終了・failed記録済み。`failed-trial-evidence.json` に全pin。修理・再使用・削除せず、今後も登録保存pathを248 UTF-16文字未満に抑える。OS設定は変更しない。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
