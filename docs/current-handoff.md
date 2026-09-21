# 次のタスク用の短い引継ぎ

更新: 2026-09-21 JST。最初にこの文書を読み、下記候補worktreeの `git status` / `git log -3 --oneline` を確認する。全履歴は必要箇所だけ読む。

## 実行中の接続確認（§132より新しい状態）

2026-09-21 21:20 JST時点: native接続を8b34387、Windows path長の事前検査を **25d1084ecf8f24f17fe6f8f5b253c317bc80daa7** に保存した。関連42件とpath修正後13件pass、独立指摘解消。ユーザーは他PC作業なし・大きめ作業OKと許可済み。

実行用clean rootは **`C:\Users\TKent\.codex\worktrees\v03\banto-ai`**。このrootの `artifacts/anomaly-v03-chunk-trials/trial-01` で新しい6評価を生成し、6件の保存後に再計算中。consumer監査・journal確定は終了確認前なので成功とみなさない。起動済みの処理や保存先を重ねて再使用しない。候補の `artifacts/chunk-execution-2026-09-21/short-trial-driver-report.json` が終了記録、`run_trial_short.py` がdriver。終了後は同じclean rootをcwdに `collect_trial.py` を実行して保存済み結果だけをpinする。

先行する長いroot `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387では261文字pathで6件目保存に失敗。worker終了・running→failedを確認し、54 files/107889570 bytesを `failed-trial-evidence.json` にpin済み。修理・再使用・削除しない。[進行中結果書](results/anomaly-multiseed-v0.3-chunk-execution-2026-09-21.md)へ実試行終了後の値を追記し、この一時節と以下の現在地を同期する。全campaignは未開始。

## 場所と最新保存点

- **作業先**: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 実装保存点: **bc5f18bb3347fe5f14e60b5381c98d63d5fa6072**（controller/監視）、**8a38a134653d237c2cdbffdd1d6dbf59caa6f3e6**（producer接続）。その後のcommitは本結果・引継ぎの保存。
- 本流 `D:\develop\banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。push/mergeなし。
- **既存dirtyを保全・commit除外**: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes、SHA-256 `443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621`。

## 目的と現在地

[研究ロードマップ](research-roadmap.md)のPhase 2（予測モデル比較）、Phase 3（異常検知・ドリフト）が目標。現在はPhase 3のanomaly v0.3、全dev/smoke実行へ進むための接続作業。小さい保存点の完了をPhase全体の完了として数えない。

通常の単一writer保存を優先する方針を採択済み。初回固定6件の実計算・保存・再計算、および保存score以降の独立ledger検算は成功済み。全dev/smokeはdev96＋smoke24＝120 chunks/720 evaluations、1 chunkは同一seed/layoutのcore/stress×3候補。全体実行は未開始。

実装済み: 固定campaign plan/journal、追記store/receipt回復、attempt descriptor、実ファイルreader、新形式の6件契約と独立audit接続。最新は **`anomaly_v03_chunk_producer.py` / `anomaly_v03_attempt_controller.py` / `anomaly_v03_process_supervisor.py`**。producerを選択chunkへ広げ、排他的intent/descriptor/receiptによる実行管理と、所有Windows子process 1個の有界監視を追加した。controllerは同期callbackを受け取るcoreで、callbackがworkerを終了確認してから戻る契約。

**次に行う作業**: producer worker/独立audit CLIを監視とcontrollerへ接続するadapter。generic監視reportから専用producer/audit監視format・binding・limitsへ結ぶ。まず小規模fixtureで確認し、全体予算/source/consumer freeze・runtime inventoryを整えてから実データ実行を判断する。予算を暗黙に確定せず、旧trialを新campaignのcoverageへコピー・再ラベル化しない。

controllerは最新receiptと各verified sequenceのdescriptor hash mapを外部保持し、再起動時に完了済み証拠を再照合する。同じsession内の再検算は省く。`TransitionIncomplete` は未確定intentを保持して停止する状態で、自動再使用不可。確定後のreceipt喪失だけは外部intent hashから読取り回復できる。`UnreapedWorker` は元のprocessを保持し、終了確認が必要。現在のattemptやログを上書きしない。

`attempt-audit` CLIは **旧形式chunk 0専用**。新manifestは **`audit_anomaly_v03_chunk.py` / `checkpoint_anomaly_v03.py attempt-chunk-audit`** で読む。producer監視のbinding/runtime_after、audit監視のexact argv/runtime_before/afterが必須。上限はprovisional、campaign起動CLIはまだない。campaign credit=0、execution/resume/formal_permission=false。profile/score導出・bootstrapの独立検算、runtime inventory、全体実行、holdout、性能評価は残件。

## 検証と資源

最新はproducer/旧engineering **31件pass/約20秒**、controller/store/監視 **41件pass/約48秒/peak private約55MiB**。独立レビュー修正後0/進捗poll0、safety/diff-check pass。小規模実ファイルIO、source/runtime/schema/数値mockを明示し、printのみの実Windows子process 1個も終了確認した。広い数値テストはMemoryError歴があるため自動実行しない。

Pythonは **`C:\Python314\python.exe -B`**、`$env:PYTHONPATH='src'`。最新の選抜:

```powershell
C:\Python314\python.exe -B -m unittest tests.test_anomaly_v03_attempt_controller tests.test_anomaly_v03_checkpoint_store tests.test_anomaly_v03_process_supervisor
```

新変更に必要な範囲だけ検証し、合格済み試験/実演を理由なく繰り返さない。2026-09-21試験後は空きRAM約12.40GiB、C約162.42GiB、D約111.3GiB。短時間観測で長期リーク不在は未評価。

Windows 26200.9457、boot2026-09-19T03:46:06.5+09:00、CPython3.14.0。Windows Updateはengineeringでは実値記録で許容、旧正式pinは不変。別プロジェクトの連続稼働テストは終了済みだが、資源監視は継続。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、全dev/smoke/holdoutの長時間実行を自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [最新結果](results/anomaly-multiseed-v0.3-attempt-controller-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜132（現在の実装経緯）。全体の再読込みは不要。
- 最新ローカル証拠: `artifacts/attempt-controller-2026-09-21/savepoint-evidence.json`。前回chunk-auditのmanifestと4証拠を保持・照合。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
