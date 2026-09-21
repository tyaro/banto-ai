# 次のタスク用の短い引継ぎ

更新: 2026-09-21 JST。最初にこの文書を読み、下記候補worktreeの `git status` / `git log -3 --oneline` を確認する。全履歴は必要箇所だけ読む。

## 場所と最新保存点

- **作業先**: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 最新実装保存点: **c01d1c978f78bab51391392d56cdcb7aab5afaab**（環境snapshotと明示起動CLI、§135）。前段の継続APIはeee93cf/§134。実prepareまで成功、全120区間は未起動。
- 実データで確認した実装: **25d1084ecf8f24f17fe6f8f5b253c317bc80daa7**（native接続8b34387＋path長事前検査）。その後のcommitは結果・引継ぎ・docstring説明の保存。
- 本流 `D:\develop\banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。push/mergeなし。
- **既存dirtyを保全・commit除外**: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes、SHA-256 `443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621`。

## 目的と現在地

[研究ロードマップ](research-roadmap.md)のPhase 2（予測モデル比較）、Phase 3（異常検知・ドリフト）が目標。現在はPhase 3のanomaly v0.3、全dev/smoke実行へ進むための接続作業。小さい保存点の完了をPhase全体の完了として数えない。

通常の単一writer保存を優先する方針を採択済み。初回固定6件の実計算・保存・再計算、および保存score以降の独立ledger検算は成功済み。全dev/smokeはdev96＋smoke24＝120 chunks/720 evaluations、1 chunkは同一seed/layoutのcore/stress×3候補。全体実行は未開始。

実装済み: 固定campaign plan/journal、追記store/receipt回復、attempt descriptor、実ファイルreader、新形式6件のproducer・独立audit、controller、所有process監視。**`anomaly_v03_chunk_execution.py` / `run_anomaly_v03_chunk.py trial`** で実コマンドへ接続し、新しい6評価を生成→両再計算→別process監査→fresh照合→journal確定まで完走した。6 success/0 failed・inconclusive、running→saved_pending_verification→verified_complete。campaign加算0、全体実行は未開始。

**今回追加した入口**: `anomaly_v03_campaign_launcher.py` / `tools/evaluator/run_anomaly_v03_campaign.py`。`prepare`は所有processで実環境snapshotを収集し、新しいmetadata/初期closed記録と外部prepared pinを作る。`continue`は外部prepared/最新closed hashと明示`--max-chunks`を必須にし、Run.run活動時間内でfresh inspectionしてからNativeCallbacksへ進む。終了不明の元ownerはCLIが終了確認まで保持する。別requestの48時間/32GiB候補、逐次処理、未閉鎖呼出しの再使用拒否を維持する。

**次に行う作業**: 下記の実prepare済み`r1`を使い、まず3区間/18評価のengineering連続運転とclosed記録・資源を確認する。source/consumer/controllerはすべてc01d1c9、Python3.14.0。snapshotはsource397/stdlib2559/native48/extension8の時点観測で、worker/auditorのruntime closureや完全S6ではない。全体上限は境界での協調停止であり、controller/process treeへの強制上限は未整備。再開時の過去verified再照合は一連の処理中にwrapperの途中予算検査がなく、追加時間がかかる。全120の単純外挿約31.2時間/14.9GiBにseed/layout差・再試行等の保証はない。48時間/32GiBは候補であり全体自動起動や正式freezeへ読み替えない。旧trialを新runのcoverageへコピーしない。

**準備済みrun**: clean `C:\Users\TKent\.codex\worktrees\v03p\banto-ai` / c01d1c9、`artifacts/v03-runs/r1`。prepared raw hash `be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7`、初期closedは`run/control/000000/closed.json` / raw hash `85a6163034c5392ce1ef78f4cbaa6da0faf9c06a66faae03c8c0f8df0c8ebf39`。7 files/749075 bytes、journal0/next0/ready。外部記録は候補`artifacts/campaign-launcher-2026-09-21/prepare-stdout.jsonl`と`prepare-evidence.json`。prepareの再実行やrootの再使用作成はせず、最新pinから`continue`する。

controllerは最新receiptと各verified sequenceのdescriptor hash mapを外部保持し、再起動時に完了済み証拠を再照合する。同じsession内の再検算は省く。`TransitionIncomplete` は未確定intentを保持して停止する状態で、自動再使用不可。確定後のreceipt喪失だけは外部intent hashから読取り回復できる。`UnreapedWorker` は元のprocessを保持し、終了確認が必要。現在のattemptやログを上書きしない。

`attempt-audit` CLIは **旧形式chunk 0専用**。新manifestは **`audit_anomaly_v03_chunk.py` / `checkpoint_anomaly_v03.py attempt-chunk-audit`** で読む。producer監視のbinding/runtime_after、audit監視のexact argv/runtime_before/afterが必須。新しいengineering起動CLIを正式gateの許可に読み替えない。campaign credit=0、formal_permission=false。profile/score導出・bootstrapの独立検算、完全runtime inventory、全体実行、holdout、性能評価は残件。

## 検証と資源

最新はsnapshot/launcherと従来owner保持回帰 **17件pass/6.691秒/peak private40.25MiB**。独立P0〜P2指摘0/進捗poll0、safety/diff-check pass。小規模実IOでOS/source/native/数値mockを明示した。別途mockなし実prepareは67.650秒、inspection60.791秒/37.20MiB、終了確認済み。前回継続API17件、native接続42件＋path修正後13件、mockなし実6評価の完走証拠は保持して再実行していない。広い数値テストはMemoryError歴があるため必要な選抜を使う。

Pythonは **`C:\Python314\python.exe -B`**、`$env:PYTHONPATH='src'`。最新の選抜:

```powershell
C:\Python314\python.exe -B -m unittest tests.test_anomaly_v03_campaign_launcher
```

新変更に必要な範囲だけ検証し、合格済み試験/実演を理由なく繰り返さない。実6件は全体1008.679秒、producer666.089秒/326.0MiB、audit91.316秒/180.34MiB、controller peak210.82MiB。全process終了確認済み。終了後は空きRAM約12.22GiB、C約162.18GiB、D約111.3GiB。長期リーク不在は未評価。

今回の実prepare後はUTC2026-09-21T13:18:09.894216+00:00、空きRAM13306019840/C174107738112/D119513100288 bytes。Windows26200.9457/CPython3.14.0とexe/DLL hashは前回同値、前後runtime一致、全所有process終了済み。新しい実データworkerは起動していない。

Windows 26200.9457、boot既存観測2026-09-19T03:46:06.5+09:00、CPython3.14.0。Windows Updateはengineeringでは実値記録で許容、旧正式pinは不変。ユーザーはこのPCで他作業なし・大きめ作業OKと許可済み。資源監視とセーブポイントは継続する。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、全dev/smoke/holdoutの長時間実行を自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [最新のsnapshot/launcher結果と操作](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)、[継続API結果](results/anomaly-multiseed-v0.3-budgeted-run-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜135（現在の実装経緯）。全体の再読込みは不要。
- 最新ローカル証拠: `artifacts/campaign-launcher-2026-09-21/savepoint-evidence.json`。前回`artifacts/budgeted-run-2026-09-21/savepoint-evidence.json`（4338 bytes/SHA256 `f95fc1fff451eaf035eab372d51ab186bee5485d2d67e7d2810c43abc92c9d02`）と記載7ファイルを保全。過去の実試行は再計算しない。
- 最新実6件: clean `C:\Users\TKent\.codex\worktrees\v03\banto-ai` / 25d1084の `artifacts/anomaly-v03-chunk-trials/trial-01`（68 files/133323148 bytes）。`trial-evidence.json` に全pin。完走済みで再起動不要。
- 保持する新しい失敗試行: `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387の同名trial（54 files/107889570 bytes）。261文字pathで6件目保存に失敗し、終了・failed記録済み。`failed-trial-evidence.json` に全pin。修理・再使用・削除せず、今後も登録保存pathを248 UTF-16文字未満に抑える。OS設定は変更しない。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
