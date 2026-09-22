# 次のタスク用の短い引継ぎ

更新: 2026-09-23 JST。最初にこの文書を読み、下記候補worktreeの `git status` / `git log -3 --oneline` を確認する。全履歴は必要箇所だけ読む。

## 場所と最新保存点

- **作業先**: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 最新実装保存点: **c01d1c978f78bab51391392d56cdcb7aab5afaab**（環境snapshotと明示起動CLI、§135）。前回chunk57〜80の24区間/144評価も成功し、累計81区間/486評価（§140）。実装変更なし。
- 最新の完了済み実データ確認も **c01d1c9**。前回chunk57〜80の最終保存点 **855e359136d568ddf5b29bef84a7d69e82e9e009**、開始09eb51f/中間8f23587・ba25ca0・26e0d0a。今回はそこから次の24区間を開始した。実装変更なし。過去の保存点・試行は保持する。
- 本流 `D:\develop\banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。push/mergeなし。
- **既存dirtyを保全・commit除外**: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes、SHA-256 `443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621`。

## 目的と現在地

**現在の実行**: JST2026-09-23 08:50に次の`continue --max-chunks 24`を起動した。対象chunk81〜104/最大144新規評価、control000006、controller PID29852/開始UTC2026-09-22T23:50:51.3450097Z。前回の81区間/486評価は完了済みで、今回分は未確定。[今回の記録](results/anomaly-multiseed-v0.3-chunks-81-104-continuation-2026-09-23.md)。状態は候補`artifacts/chunks-81-104-continuation-2026-09-23/status.py`で読み、PID・開始日時・wrapperを照合する。同じrunを重複起動しない。

**継続確認**: 30分間隔heartbeat **banto-24** を今回の区間81〜104だけを対象に更新・再開した。手順は候補`artifacts/chunks-81-104-continuation-2026-09-23/FOLLOWUP.md`。稼働中は1回確認し、新規6/12/18区間で中間保存する。wrapperは60秒診断と各区間のreceipt保持を行う。成功・異常終了時とも記録を保全してheartbeatを停止し、追加invocationは起動しない。前回PID39544/collectorは正常終了済みで再実行しない。

今回の開始前にも、前回5221 files/10761163678 logical bytesと前回証拠50件の不変を確認した。関連計算processなし、runtime一致。下記000005のclosedは今回の開始pinであり、実行中の再開に使わない。終了後の最新pinは000006へ更新する。

**前回の保存点**: 最終855e359、manifest10443 bytes/SHA256 c4017dacb4a80da2a27fe90c57f53c0fab95991ce44bb8a91b969909c891f0ca。過去の起動・中間・最終証拠を保持する。

**今回の保存点**: 起動後の2文書commitと起動記録のpinは候補`artifacts/chunks-81-104-continuation-2026-09-23/launch-savepoint.json`へ保持する。中間保存は新規6/12/18区間の節目に行い、各commit・観測値を同folderの`followup-state.json`に記録する。

[研究ロードマップ](research-roadmap.md)のPhase 2（予測モデル比較）、Phase 3（異常検知・ドリフト）が目標。現在はPhase 3のanomaly v0.3、全dev/smoke実行へ進むための接続作業。小さい保存点の完了をPhase全体の完了として数えない。

通常の単一writer保存を優先する方針を採択済み。全dev/smokeはdev96＋smoke24＝120 chunks/720 evaluations、1 chunkは同一seed/layoutのcore/stress×3候補。新engineering runの先頭81 chunks/486 evaluationsが完了し、残り39 chunks/234 evaluations。正式campaign加算は0を維持する。

実装済み: 固定campaign plan/journal、追記store/receipt回復、attempt descriptor、実ファイルreader、新形式6件のproducer・独立audit、controller、所有process監視。実コマンドで生成→両再計算→別process監査→fresh照合→journal確定まで接続済み。launcherの5回の継続実行でjournal243記録を確定した。

**継続入口**: `anomaly_v03_campaign_launcher.py` / `tools/evaluator/run_anomaly_v03_campaign.py`。`prepare`は所有processで実環境snapshotを収集し、新しいmetadata/初期closed記録と外部prepared pinを作る。`continue`は外部prepared/最新closed hashと明示`--max-chunks`を必須にし、Run.run活動時間内でfresh inspectionしてからNativeCallbacksへ進む。終了不明の元ownerはCLIが終了確認まで保持する。別requestの48時間/32GiB候補、逐次処理、未閉鎖呼出しの再使用拒否を維持する。

**次に行う作業**: 起動済みの区間81〜104を観測・中間保存し、終了後に照合・最終保存する。今回見積りは約9.4〜9.5時間/追加約3GiBで、最初の約3.5時間は既存81区間の再照合が中心。累積活動の開始値86406.475041秒、48時間候補の残り86393.524959秒（約24.00時間）。仮に残りを24/15に分ける線形試算は全累積約41.65〜41.74時間だが保証ではない。今回の上限は24区間のみ。成功時next105/累計630評価、残り15区間/90評価。追加invocationを自動起動しない。

source/consumer/controllerはすべてc01d1c9、Python3.14.0を維持。snapshotはsource397/stdlib2559/native48/extension8の時点観測で、worker/auditorのruntime closureや完全S6ではない。全体上限は境界での協調停止で、controller/process treeへの強制上限は未整備。再開時の過去verified再照合には一連の処理途中のwrapper予算検査がない。旧trialを新runのcoverageへコピーしない。

**再開対象run**: clean `C:/Users/TKent/.codex/worktrees/v03p/banto-ai` / c01d1c9、`artifacts/v03-runs/r1`。最新closedは **`run/control/000005/closed.json`** / raw SHA-256 **a6b8fd6160b496d9a7dea83cef3ec22814c8b12676df273eb591fb5368384758**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。旧000004以前のclosedや中間receiptは再開pinに使わない。 5221 files/10761163678 logical bytes、journal243/next81/yielded、累積活動86406.475041秒。外部stdout/evidenceは候補`artifacts/chunks-57-80-continuation-2026-09-22`。prepareを同じrootで再実行せず、再開する場合は最新pinと明示上限を使う。

controllerは最新receiptと各verified sequenceのdescriptor hash mapを外部保持し、再起動時に完了済み証拠を再照合する。同じsession内の再検算は省く。`TransitionIncomplete` は未確定intentを保持して停止する状態で、自動再使用不可。確定後のreceipt喪失だけは外部intent hashから読取り回復できる。`UnreapedWorker` は元のprocessを保持し、終了確認が必要。現在のattemptやログを上書きしない。

`attempt-audit` CLIは **旧形式chunk 0専用**。新manifestは **`audit_anomaly_v03_chunk.py` / `checkpoint_anomaly_v03.py attempt-chunk-audit`** で読む。producer監視のbinding/runtime_after、audit監視のexact argv/runtime_before/afterが必須。新しいengineering起動CLIを正式gateの許可に読み替えない。campaign credit=0、formal_permission=false。profile/score導出・bootstrapの独立検算、完全runtime inventory、全体実行、holdout、性能評価は残件。

## 検証と資源

最新の実確認は**mockなし追加24区間/144評価成功**、30205.374秒（約8時間23分）、監査24件とも`ledger_checks_passed`。終了後のcollectorは522.586秒のIO/hash照合のみ、数値再計算なし。今回は文書のみ更新し、追加agentや合格済み回帰試験の再実行なし。diff-checkを最終保存前に確認する。

実装時のsnapshot/launcherと従来owner保持回帰は **17件pass/6.691秒/peak private40.25MiB**。独立P0〜P2指摘0/進捗poll0、safety/diff-check pass。小規模実IOでOS/source/native/数値mockを明示した。mockなし実prepare67.650秒/inspection37.20MiB、継続API17件、native接続42件＋path修正後13件、以前の実6評価の証拠も保持。広い数値テストはMemoryError歴があるため必要な選抜を使う。

Pythonは **`C:\Python314\python.exe -B`**、`$env:PYTHONPATH='src'`。最新の選抜:

```powershell
C:\Python314\python.exe -B -m unittest tests.test_anomaly_v03_campaign_launcher
```

新変更に必要な範囲だけ検証し、合格済み試験/実演を理由なく繰り返さない。producer最大334.3MiB、audit最大188.6MiB、controller peak225.6MiB/終了時90.2MiB。60秒間隔501標本の空きRAM最小9602994176 bytes（約8.94GiB）、観測エラーなし。controller privateは終了時に低下したが、長期リーク不在は未評価。

連続運転終了UTC2026-09-22T18:08:59.297124+00:00（JST2026-09-23 03:08）、空きRAM11659157504/C161118416896/D119168434176 bytes。Windows26200.9457/CPython3.14.0とexe/DLL hashは前回同値、開始・終了・各workerのruntime一致、全所有process終了済み。

Windows 26200.9457、boot既存観測2026-09-19T03:46:06.5+09:00、CPython3.14.0。Windows Updateはengineeringでは実値記録で許容、旧正式pinは不変。ユーザーはこのPCで他作業なし・大きめ作業OKと許可済み。資源監視とセーブポイントは継続する。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、全dev/smoke/holdoutの長時間実行を自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [今回の区間81〜104の記録](results/anomaly-multiseed-v0.3-chunks-81-104-continuation-2026-09-23.md)、[前回区間57〜80の結果](results/anomaly-multiseed-v0.3-chunks-57-80-continuation-2026-09-22.md)、[snapshot/launcherの操作](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜140（現在の実装経緯）。全体の再読込みは不要。
- 最新ローカル証拠: `artifacts/chunks-57-80-continuation-2026-09-22/savepoint-evidence.json`。前回`artifacts/chunks-33-56-continuation-2026-09-22/savepoint-evidence.json`（10290 bytes/SHA256 6f734135d9712a477fef2b2a88b5b234e47701737139324e7c941f8a8a21ef77）と記載48ファイルを保全。さらに以前の証拠も保持し、過去の実試行は再計算しない。
- 以前の実6件: clean `C:\Users\TKent\.codex\worktrees\v03\banto-ai` / 25d1084の `artifacts/anomaly-v03-chunk-trials/trial-01`（68 files/133323148 bytes）。`trial-evidence.json` に全pin。完走済みで再起動不要。
- 保持する新しい失敗試行: `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387の同名trial（54 files/107889570 bytes）。261文字pathで6件目保存に失敗し、終了・failed記録済み。`failed-trial-evidence.json` に全pin。修理・再使用・削除せず、今後も登録保存pathを248 UTF-16文字未満に抑える。OS設定は変更しない。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
