# 次のタスク用の短い引継ぎ

更新: 2026-09-22 JST。最初にこの文書を読み、下記候補worktreeの `git status` / `git log -3 --oneline` を確認する。全履歴は必要箇所だけ読む。

## 場所と最新保存点

- **作業先**: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 最新実装保存点: **c01d1c978f78bab51391392d56cdcb7aab5afaab**（環境snapshotと明示起動CLI、§135）。前段の継続APIはeee93cf/§134。初回3区間/18評価（§136）の後、追加6区間/36評価も成功し、累計9区間/54評価（§137）。
- 最新の実データ確認も **c01d1c9**。今回の開始保存点1873c37、中間保存点ed28579、最終commitは下記`savepoint-evidence.json`に記録。変更は結果・引継ぎ文書のみ。前回6557188と以前の25d1084による単一区間試行も保持。
- 本流 `D:\develop\banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。push/mergeなし。
- **既存dirtyを保全・commit除外**: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes、SHA-256 `443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621`。

## 目的と現在地

**現在の実行**: 2026-09-22 JST02:36、`continue --max-chunks 24`を起動した。対象chunk9〜32/最大144新規評価、control000003、controller PID2320/開始UTC2026-09-21T17:36:34.2941005Z。実行中は同じrunを再起動しない。[今回の実行記録](results/anomaly-multiseed-v0.3-twenty-four-chunk-continuation-2026-09-22.md)。候補`artifacts/twenty-four-chunk-continuation-2026-09-22/status.py`で小さい状態ファイルを読む。PID・開始日時・コマンドを照合する。

**継続確認**: このタスクの30分間隔heartbeat **banto-24** が稼働・資源と6区間ごとの保存を確認し、終了後の照合・最終保存まで行う。wrapper自身も60秒診断と各区間のreceipt保持を行う。詳細は同artifact folderの`FOLLOWUP.md`。会話側で短い間隔のポーリングを追加しない。成功・異常終了を記録したらheartbeatを停止し、追加invocationを自動起動しない。

前回までの完了は累計9区間/54評価、595保存ファイル。今回の開始前にも595ファイルと前回証拠21ファイルの不変、関連計算processなし、runtime一致を確認した。下記000002のclosedは今回の開始pinであり、終了後に新しいpinへ更新する。

[研究ロードマップ](research-roadmap.md)のPhase 2（予測モデル比較）、Phase 3（異常検知・ドリフト）が目標。現在はPhase 3のanomaly v0.3、全dev/smoke実行へ進むための接続作業。小さい保存点の完了をPhase全体の完了として数えない。

通常の単一writer保存を優先する方針を採択済み。全dev/smokeはdev96＋smoke24＝120 chunks/720 evaluations、1 chunkは同一seed/layoutのcore/stress×3候補。新engineering runの先頭9 chunks/54 evaluationsが完了し、残り111 chunks/666 evaluations。正式campaign加算は0を維持する。

実装済み: 固定campaign plan/journal、追記store/receipt回復、attempt descriptor、実ファイルreader、新形式6件のproducer・独立audit、controller、所有process監視。実コマンドで生成→両再計算→別process監査→fresh照合→journal確定まで接続済み。launcherの2回の連続実行でjournal27記録を確定した。

**継続入口**: `anomaly_v03_campaign_launcher.py` / `tools/evaluator/run_anomaly_v03_campaign.py`。`prepare`は所有processで実環境snapshotを収集し、新しいmetadata/初期closed記録と外部prepared pinを作る。`continue`は外部prepared/最新closed hashと明示`--max-chunks`を必須にし、Run.run活動時間内でfresh inspectionしてからNativeCallbacksへ進む。終了不明の元ownerはCLIが終了確認まで保持する。別requestの48時間/32GiB候補、逐次処理、未閉鎖呼出しの再使用拒否を維持する。

**次に行う作業**: 起動済み24区間の終了確認と保存結果の照合。今回の目安は約6時間/追加約3GiB。前回、既存3区間を含む再開確認に約9〜10分かかった。残りを6区間ずつ再開する線形試算では累積約81〜88時間、24区間単位なら約40〜42時間となるため、実行を終了させずに途中保存する方式を選んだ。試算は1回の再開実測だけに基づき、固定起動費、seed/layout差、inventory増加・再試行を分離していない。48時間/32GiBへの収束保証や全残区間の自動起動許可ではない。

source/consumer/controllerはすべてc01d1c9、Python3.14.0を維持。snapshotはsource397/stdlib2559/native48/extension8の時点観測で、worker/auditorのruntime closureや完全S6ではない。全体上限は境界での協調停止で、controller/process treeへの強制上限は未整備。再開時の過去verified再照合には一連の処理途中のwrapper予算検査がない。旧trialを新runのcoverageへコピーしない。

**再開対象run**: clean `C:\Users\TKent\.codex\worktrees\v03p\banto-ai` / c01d1c9、`artifacts/v03-runs/r1`。prepared raw hash **`be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7`** は不変。最新closedは **`run/control/000002/closed.json`** / raw hash **`37b94e035b4468b18ff6381e0a17ed7ca6aaedb99cccb14cfaebcb10d8597501`**。595 files/1196786729 logical bytes、journal27/next9/yielded、累積活動時間8005.085221秒。外部stdoutと`evidence.json`は候補`artifacts/six-chunk-continuation-2026-09-21`。古い初期closed、000001、中間receiptは再開に使わない。prepareを同じrootで再実行せず、最新pinから`continue`する。

controllerは最新receiptと各verified sequenceのdescriptor hash mapを外部保持し、再起動時に完了済み証拠を再照合する。同じsession内の再検算は省く。`TransitionIncomplete` は未確定intentを保持して停止する状態で、自動再使用不可。確定後のreceipt喪失だけは外部intent hashから読取り回復できる。`UnreapedWorker` は元のprocessを保持し、終了確認が必要。現在のattemptやログを上書きしない。

`attempt-audit` CLIは **旧形式chunk 0専用**。新manifestは **`audit_anomaly_v03_chunk.py` / `checkpoint_anomaly_v03.py attempt-chunk-audit`** で読む。producer監視のbinding/runtime_after、audit監視のexact argv/runtime_before/afterが必須。新しいengineering起動CLIを正式gateの許可に読み替えない。campaign credit=0、formal_permission=false。profile/score導出・bootstrapの独立検算、完全runtime inventory、全体実行、holdout、性能評価は残件。

## 検証と資源

最新の実確認は**mockなし追加6区間/36評価成功**、全体5442.063秒、監査6件とも`ledger_checks_passed`。保存後のcollectorは128.340秒のIO/hash照合のみ、数値計算は繰り返していない。今回は文書のみ更新し、追加agentや合格済み回帰試験の再実行は行っていない。repository safety/diff-check pass。

実装時のsnapshot/launcherと従来owner保持回帰は **17件pass/6.691秒/peak private40.25MiB**。独立P0〜P2指摘0/進捗poll0、safety/diff-check pass。小規模実IOでOS/source/native/数値mockを明示した。mockなし実prepare67.650秒/inspection37.20MiB、継続API17件、native接続42件＋path修正後13件、以前の実6評価の証拠も保持。広い数値テストはMemoryError歴があるため必要な選抜を使う。

Pythonは **`C:\Python314\python.exe -B`**、`$env:PYTHONPATH='src'`。最新の選抜:

```powershell
C:\Python314\python.exe -B -m unittest tests.test_anomaly_v03_campaign_launcher
```

新変更に必要な範囲だけ検証し、合格済み試験/実演を理由なく繰り返さない。今回のproducer最大333.3MiB、audit最大185.9MiB、controller peak216.6MiB/終了時77.3MiB。60秒間隔90標本の空きRAM最小約11.88GiB、観測エラーなし。controller privateは増減し終了時に低下したが、長期リーク不在は未評価。

連続運転終了UTC2026-09-21T15:55:10.529690+00:00（JST2026-09-22 00:55）、空きRAM13211693056/C173294256128/D119512580096 bytes（C約161.4GiB/D約111.3GiB）。Windows26200.9457/CPython3.14.0とexe/DLL hashは前回同値、開始・終了・各workerのruntime一致、全所有process終了済み。

Windows 26200.9457、boot既存観測2026-09-19T03:46:06.5+09:00、CPython3.14.0。Windows Updateはengineeringでは実値記録で許容、旧正式pinは不変。ユーザーはこのPCで他作業なし・大きめ作業OKと許可済み。資源監視とセーブポイントは継続する。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、全dev/smoke/holdoutの長時間実行を自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [最新6区間の継続結果と次回試算](results/anomaly-multiseed-v0.3-six-chunk-continuation-2026-09-21.md)、[snapshot/launcherの操作](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)、[継続API結果](results/anomaly-multiseed-v0.3-budgeted-run-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜137（現在の実装経緯）。全体の再読込みは不要。
- 最新ローカル証拠: `artifacts/six-chunk-continuation-2026-09-21/savepoint-evidence.json`。前回`artifacts/three-chunk-run-2026-09-21/savepoint-evidence.json`（4953 bytes/SHA256 `adf08b7f2f32907c45c94bf8e9656a91292137efe02f83a00f6cb0d68ff1d5aa`）と記載11ファイルを保全。過去の実試行は再計算しない。
- 以前の実6件: clean `C:\Users\TKent\.codex\worktrees\v03\banto-ai` / 25d1084の `artifacts/anomaly-v03-chunk-trials/trial-01`（68 files/133323148 bytes）。`trial-evidence.json` に全pin。完走済みで再起動不要。
- 保持する新しい失敗試行: `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387の同名trial（54 files/107889570 bytes）。261文字pathで6件目保存に失敗し、終了・failed記録済み。`failed-trial-evidence.json` に全pin。修理・再使用・削除せず、今後も登録保存pathを248 UTF-16文字未満に抑える。OS設定は変更しない。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
