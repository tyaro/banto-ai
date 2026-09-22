# 次のタスク用の短い引継ぎ

更新: 2026-09-22 JST。最初にこの文書を読み、下記候補worktreeの `git status` / `git log -3 --oneline` を確認する。全履歴は必要箇所だけ読む。

## 場所と最新保存点

- **作業先**: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 最新実装保存点: **c01d1c978f78bab51391392d56cdcb7aab5afaab**（環境snapshotと明示起動CLI、§135）。前段の継続APIはeee93cf/§134。初回3区間、追加6区間に続き、今回24区間/144評価も成功し、累計33区間/198評価（§138）。
- 最新の完了済み実データ確認も **c01d1c9**。前回chunk9〜32の最終保存点 **28100c4da280c3c56e043e871923ff9cc5e1a0d8**、開始af393cb/中間dad47ee・82e69de・55faa8d。今回はそこから次の24区間を開始した。実装変更なし。過去の保存点・試行は保持する。
- 本流 `D:\develop\banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。push/mergeなし。
- **既存dirtyを保全・commit除外**: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes、SHA-256 `443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621`。

## 目的と現在地

**現在の実行**: JST2026-09-22 10:24に次の`continue --max-chunks 24`を起動した。対象chunk33〜56/最大144新規評価、control000004、controller PID6872/開始UTC2026-09-22T01:24:22.5430796Z。前回の33区間/198評価は完了済みで、今回分は未確定。[今回の記録](results/anomaly-multiseed-v0.3-chunks-33-56-continuation-2026-09-22.md)。状態は候補`artifacts/chunks-33-56-continuation-2026-09-22/status.py`で読み、PID・開始日時・wrapperを照合する。同じrunを重複起動しない。

**継続確認**: 30分間隔heartbeat **banto-24** を今回の区間33〜56だけを対象に更新・再開した。手順は候補`artifacts/chunks-33-56-continuation-2026-09-22/FOLLOWUP.md`。稼働中は1回確認し、新規6/12/18区間で中間保存する。wrapperは60秒診断と各区間のreceipt保持を行う。成功・異常終了時とも記録を保全してheartbeatを停止し、追加invocationは起動しない。前回PID2320/collectorは正常終了済みで再実行しない。

今回の開始前にも、前回2137 files/4384532669 logical bytesと前回証拠49件の不変を確認した。関連計算processなし、runtime一致。下記000003のclosedは今回の開始pinであり、実行中の再開に使わない。終了後の最新pinは000004へ更新する。

**前回の保存点**: 6/12/18区間の節目をdad47ee/82e69de/55faa8dで保存した（観測時の新規確定数は7/12/19）。各commitと観測値は前回の`followup-state.json`に記録。前回の最終manifestは10289 bytes/SHA256 `ddbb32983dadb84fbdca50d990f346c02cdaa5bedc8949d016504562e6d48ec8`。今回の起動保存は新artifact folderの`launch-savepoint.json`に記録する。

**今回の中間保存（6区間の節目）**: UTC2026-09-22T05:03:05.021046+00:00（JST14:03）の診断で、新規7区間/42評価（chunk33〜39）のverified receiptを保持、累計40区間/240評価。journal121、chunk40/attempt1はrunning、経過13121.9秒。同じcontroller PID6872の開始日時・wrapperコマンドを照合済み。空きRAM12813946880/C165461995520/D119512002560 bytes、controller private116826112/peak230563840 bytes、エラーログは空。今回全24区間の終了・最終照合は未完了。保存commitは今回の外部`followup-state.json`に記録し、次の中間保存は新規12区間到達後に行う。

[研究ロードマップ](research-roadmap.md)のPhase 2（予測モデル比較）、Phase 3（異常検知・ドリフト）が目標。現在はPhase 3のanomaly v0.3、全dev/smoke実行へ進むための接続作業。小さい保存点の完了をPhase全体の完了として数えない。

通常の単一writer保存を優先する方針を採択済み。全dev/smokeはdev96＋smoke24＝120 chunks/720 evaluations、1 chunkは同一seed/layoutのcore/stress×3候補。新engineering runの先頭33 chunks/198 evaluationsが完了し、残り87 chunks/522 evaluations。正式campaign加算は0を維持する。

実装済み: 固定campaign plan/journal、追記store/receipt回復、attempt descriptor、実ファイルreader、新形式6件のproducer・独立audit、controller、所有process監視。実コマンドで生成→両再計算→別process監査→fresh照合→journal確定まで接続済み。launcherの3回の継続実行でjournal99記録を確定した。

**継続入口**: `anomaly_v03_campaign_launcher.py` / `tools/evaluator/run_anomaly_v03_campaign.py`。`prepare`は所有processで実環境snapshotを収集し、新しいmetadata/初期closed記録と外部prepared pinを作る。`continue`は外部prepared/最新closed hashと明示`--max-chunks`を必須にし、Run.run活動時間内でfresh inspectionしてからNativeCallbacksへ進む。終了不明の元ownerはCLIが終了確認まで保持する。別requestの48時間/32GiB候補、逐次処理、未閉鎖呼出しの再使用拒否を維持する。

**次に行う作業**: 起動済みの区間33〜56を観測・中間保存し、終了後に照合・最終保存する。今回の見積りは約7.1時間/追加約3GiBで、最初の約1.8時間は既存33区間の再照合が中心。累積活動の開始値28855.997764秒、48時間候補の残り143944.002236秒（約39.98時間）。前回実測から仮に残りを24/24/24/15に分ける線形試算は全累積42.1〜42.7時間だが、固定費・seed/layout差・inventory増加・再試行等を分離しておらず保証ではない。今回の上限は24区間のみ。成功時next57/累計342評価、残り63区間/378評価。追加invocationを自動起動しない。

source/consumer/controllerはすべてc01d1c9、Python3.14.0を維持。snapshotはsource397/stdlib2559/native48/extension8の時点観測で、worker/auditorのruntime closureや完全S6ではない。全体上限は境界での協調停止で、controller/process treeへの強制上限は未整備。再開時の過去verified再照合には一連の処理途中のwrapper予算検査がない。旧trialを新runのcoverageへコピーしない。

**再開対象run**: clean `C:/Users/TKent/.codex/worktrees/v03p/banto-ai` / c01d1c9、`artifacts/v03-runs/r1`。prepared raw hash **`be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7`** は不変。最新closedは **`run/control/000003/closed.json`** / raw hash **`af04684d25c99f69e64a2ac5aacffd92be930d6325ceddd5d9a0ee254f5fa7a0`**。2137 files/4384532669 logical bytes、journal99/next33/yielded、累積活動時間28855.997764秒。外部stdoutと`evidence.json`は候補`artifacts/twenty-four-chunk-continuation-2026-09-22`。古い初期closed、000001、000002、中間receiptは再開に使わない。prepareを同じrootで再実行せず、次の実行時は最新pinから明示上限付き`continue`を使う。

controllerは最新receiptと各verified sequenceのdescriptor hash mapを外部保持し、再起動時に完了済み証拠を再照合する。同じsession内の再検算は省く。`TransitionIncomplete` は未確定intentを保持して停止する状態で、自動再使用不可。確定後のreceipt喪失だけは外部intent hashから読取り回復できる。`UnreapedWorker` は元のprocessを保持し、終了確認が必要。現在のattemptやログを上書きしない。

`attempt-audit` CLIは **旧形式chunk 0専用**。新manifestは **`audit_anomaly_v03_chunk.py` / `checkpoint_anomaly_v03.py attempt-chunk-audit`** で読む。producer監視のbinding/runtime_after、audit監視のexact argv/runtime_before/afterが必須。新しいengineering起動CLIを正式gateの許可に読み替えない。campaign credit=0、formal_permission=false。profile/score導出・bootstrapの独立検算、完全runtime inventory、全体実行、holdout、性能評価は残件。

## 検証と資源

最新の実確認は**mockなし追加24区間/144評価成功**、全体20851.249秒（約5時間48分）、監査24件とも`ledger_checks_passed`。保存後のcollectorは456.468秒のIO/hash照合のみ、数値計算は繰り返していない。今回は文書のみ更新し、追加agentや合格済み回帰試験の再実行は行っていない。diff-check pass。

実装時のsnapshot/launcherと従来owner保持回帰は **17件pass/6.691秒/peak private40.25MiB**。独立P0〜P2指摘0/進捗poll0、safety/diff-check pass。小規模実IOでOS/source/native/数値mockを明示した。mockなし実prepare67.650秒/inspection37.20MiB、継続API17件、native接続42件＋path修正後13件、以前の実6評価の証拠も保持。広い数値テストはMemoryError歴があるため必要な選抜を使う。

Pythonは **`C:\Python314\python.exe -B`**、`$env:PYTHONPATH='src'`。最新の選抜:

```powershell
C:\Python314\python.exe -B -m unittest tests.test_anomaly_v03_campaign_launcher
```

新変更に必要な範囲だけ検証し、合格済み試験/実演を理由なく繰り返さない。今回のproducer最大333.3MiB、audit最大186.3MiB、controller peak218.5MiB/終了時88.5MiB。60秒間隔346標本の空きRAM最小12526116864 bytes（約11.67GiB）、観測エラーなし。controller privateは終了時に低下したが、長期リーク不在は未評価。

連続運転終了UTC2026-09-21T23:24:06.304847+00:00（JST2026-09-22 08:24）、空きRAM13213487104/C169208168448/D119512244224 bytes。Windows26200.9457/CPython3.14.0とexe/DLL hashは前回同値、開始・終了・各workerのruntime一致、全所有process終了済み。

Windows 26200.9457、boot既存観測2026-09-19T03:46:06.5+09:00、CPython3.14.0。Windows Updateはengineeringでは実値記録で許容、旧正式pinは不変。ユーザーはこのPCで他作業なし・大きめ作業OKと許可済み。資源監視とセーブポイントは継続する。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、全dev/smoke/holdoutの長時間実行を自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [今回の区間33〜56の記録](results/anomaly-multiseed-v0.3-chunks-33-56-continuation-2026-09-22.md)、[前回24区間の結果](results/anomaly-multiseed-v0.3-twenty-four-chunk-continuation-2026-09-22.md)、[snapshot/launcherの操作](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜138（現在の実装経緯）。全体の再読込みは不要。
- 最新ローカル証拠: `artifacts/twenty-four-chunk-continuation-2026-09-22/savepoint-evidence.json`。前回`artifacts/six-chunk-continuation-2026-09-21/savepoint-evidence.json`（6331 bytes/SHA256 `f16e7470bac1ef637f2bb019f80ebe36ffcc7499c4c07844699d1a2a969d4754`）と記載20ファイルを保全。さらに以前の証拠も保持し、過去の実試行は再計算しない。
- 以前の実6件: clean `C:\Users\TKent\.codex\worktrees\v03\banto-ai` / 25d1084の `artifacts/anomaly-v03-chunk-trials/trial-01`（68 files/133323148 bytes）。`trial-evidence.json` に全pin。完走済みで再起動不要。
- 保持する新しい失敗試行: `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387の同名trial（54 files/107889570 bytes）。261文字pathで6件目保存に失敗し、終了・failed記録済み。`failed-trial-evidence.json` に全pin。修理・再使用・削除せず、今後も登録保存pathを248 UTF-16文字未満に抑える。OS設定は変更しない。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
