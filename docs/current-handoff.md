# 次のタスク用の短い引継ぎ

更新: 2026-09-21 JST。最初にこの文書を読み、下記候補worktreeの `git status` / `git log -3 --oneline` を確認する。全履歴は必要箇所だけ読む。

## 場所と最新保存点

- **作業先**: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 実装保存点: **60b2bdb3d2556b280b10991a2fd1d47d4566714d**。その後のcommitは本結果・引継ぎの保存。
- 本流 `D:\develop\banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。push/mergeなし。
- **既存dirtyを保全・commit除外**: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes、SHA-256 `443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621`。

## 目的と現在地

[研究ロードマップ](research-roadmap.md)のPhase 2（予測モデル比較）、Phase 3（異常検知・ドリフト）が目標。現在はPhase 3のanomaly v0.3、全dev/smoke実行へ進むための接続作業。小さい保存点の完了をPhase全体の完了として数えない。

通常の単一writer保存を優先する方針を採択済み。初回固定6件の実計算・保存・再計算、および保存score以降の独立ledger検算は成功済み。全dev/smokeはdev96＋smoke24＝120 chunks/720 evaluations、1 chunkは同一seed/layoutのcore/stress×3候補。全体実行は未開始。

実装済み: 固定campaign planとhash-linked journal、metadata専用追記store/receipt回復、固定attempt descriptor、実ファイルhash reader、旧形式chunk 0の `attempt-audit`。最新の **`anomaly_v03_chunk_contract.py`** で全120から選ぶ6件の新結果形式と `audit_chunk_payloads` を追加した。外部campaign/index/attempt/source pinを検査するが、新APIのIO/監視/CLI接続はまだ。

**次に行う作業**: 新chunk形式を既存のattempt読取り・producer終了監視・audit report・audit終了監視・campaign journal/descriptor照合へ接続する。旧6件契約とCLI互換を維持。新APIのinput bytes mappingのテストを実ファイル接続へ進める。構造が揃った後に実行側controllerと予算/source/consumer freezeを整える。実行予算を暗黙に確定せず、旧trialを新campaignのcoverageへコピー・再ラベル化しない。

`attempt-audit` CLIは現在 **旧形式chunk 0専用**。新manifest `anomaly-v03-dev-smoke-chunk-result-v1` / scope `engineering-dev-smoke-chunk` は未接続。共通validatorの上限はprovisionalのみ。campaign credit=0、execution/resume/formal_permission=false。profile/score導出・bootstrapの独立検算、runtime inventory、全体実行、holdout、性能評価は残件。

## 検証と資源

最新は小規模 **70件pass/約16秒/peak private約51MiB**、独立レビュー指摘0/進捗poll0、safety/diff-check pass。新接続テストではschema/数値mockを明示、別の12件で既存の小規模ledger実計算を確認。広い数値テストはMemoryError歴があるため自動実行しない。

Pythonは **`C:\Python314\python.exe -B`**、`$env:PYTHONPATH='src'`。最新の選抜:

```powershell
C:\Python314\python.exe -B -m unittest tests.test_anomaly_v03_chunk_contract tests.test_anomaly_v03_engineering.ContractTests tests.test_anomaly_v03_saved_audit tests.test_anomaly_v03_ledger_audit tests.test_anomaly_v03_attempt_files tests.test_anomaly_v03_checkpoint_evidence
```

新変更に必要な範囲だけ検証し、合格済み試験/実演を理由なく繰り返さない。2026-09-21試験後は空きRAM約12.35GiB、C約159.15GiB、D約111.3GiB。短時間観測で長期リーク不在は未評価。

Windows 26200.9457、boot2026-09-19T03:46:06.5+09:00、CPython3.14.0。Windows Updateはengineeringでは実値記録で許容、旧正式pinは不変。別プロジェクトの連続稼働テストは終了済みだが、資源監視は継続。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、全dev/smoke/holdoutの長時間実行を自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [最新結果](results/anomaly-multiseed-v0.3-chunk-contract-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜130（現在の実装経緯）。全体の再読込みは不要。
- 最新ローカル証拠: `artifacts/chunk-contract-2026-09-21/savepoint-evidence.json`。前回証拠27 filesを保持・照合。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
