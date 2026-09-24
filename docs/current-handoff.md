# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**ユーザーが最後の1区間の再試行を許可。区間119/attempt2をcontrol000010で1回だけ再開準備中。確定済み119区間/714評価と失敗attempt1を保持する。**

今回OUTは `artifacts/chunk-119-retry-2026-09-24`。まずそのFOLLOWUP.md/followup-state.jsonを読む。[今回の再試行](results/anomaly-multiseed-v0.3-final-chunk-retry-2026-09-24.md)。外部helperを失敗末尾の明示pinに対応させ、関連18テスト通過。起動時に既存7730ファイルを1回hash照合して119監査だけ再利用する。新規attempt2は元の監査を行う。worker900秒/48h/32GiBは不変。成功時journal362/全120区間720評価/next=null。再失敗したら保全し停止、attempt3なし。以下は前回停止の記録。

## 場所と保存点

- 候補: `C:/Users/TKent/.codex/worktrees/70b0/banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 今回OUT: `artifacts/chunks-105-119-fast-resume-2026-09-24`。failure-evidence.json/diagnostics-summary.jsonが停止証拠。最終commit/pinはfailure-savepoint-evidence.json/followup-state.json。実装aab4d58、起動dd45a37、中間eb1a67e/105960c。
- 実計算source: clean c01d1c978f78bab51391392d56cdcb7aab5afaab、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、出力`artifacts/v03-runs/r1`。
- 本流D:/develop/banto-aiは889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e/clean。既存dirty親policy文書は8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持、stage/commitしない。
- [今回の停止記録](results/anomaly-multiseed-v0.3-verified-resume-2026-09-24.md)、長い引継書§147。保存済みの旧成功・失敗OUTは変更しない。

## 現在地

control000009は最後の区間119/attempt1のproducerが900秒（15分）の上限に達し、ResourceStop/time_limitでexit2となった。producer実測909.083秒、worker PID17908/exit1/終了確認済み。終了UTC **2026-09-24T05:46:49.451914+00:00**（JST **2026-09-24 14:46:49**）。新規14区間/84評価が確定し、累計**119区間/714評価**。残り**1区間/6評価**。journal359/next119、最終recordはfailed/resource_limit。全120区間の完了ではない。

最新closedは **run/control/000009/closed.json** / raw SHA256 **362c2ed425d38a6a6ae3436518fa4cafa0cc4d9a017b012f15de4816fa44156d**、status=failed/stop_reason=exception。累積活動**159294.585066秒（44.25時間）**、48時間候補の残り**13505.414934秒（3.75時間）**。失敗時間を含めて保持し、48h/32GiBとworker上限は変更していない。prepared pinはbe582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7。旧control8や中間receiptを最新closedの代わりに使わない。

controller PID25724の消失と全所有workerの終了を確認済み。失敗attempt1には6件のstageファイルが残るが完了markerなし/audit未開始のため成功扱いしない。生存workerの放置や追加起動はない。

## 診断と保全

診断は238周期標本/273イベント、audit_begin/end各14件（105〜118）、ResourceStop例外1件、観測error/drop=0、無効化なし、診断thread終了済み。今回の停止はMemoryErrorではなくproducerの時間上限。標本UTC **2026-09-24T05:44:43.907054+00:00** でsystem commit 54.90/54.96GiB、割当余力**52.73MiB**を記録した。同時刻のpagefile確保量は23.26GiB。空きRAM最小標本は3.38GiB。controller peak 0.22GiB、失敗producer peak 326.05MiB。システム全体の資源逼迫は観測したが、割当元process・時間超過への因果寄与・実際のCPU/I/O競合は未確定。メモリリークの有無を断定しない。

既存105区間は起動時の全byte/source/runtime照合（56.252秒）で監査を再利用し、新規105〜118の14区間は元の独立監査とcontroller監査を通過した。今回保全では新規14区間のdescriptor/control pin、完了markerが示すpayload raw hash、全6件success、producer/audit workerの終了を照合した。新規runファイル955件/1999730138 bytesをstreaming hashし、前回6775ファイルの一覧/サイズと旧journal315件のhashを確認。旧payload全体の再hashや数値再計算はしていない。全体は7730 files/15947784715 logical bytes。過去196artifact pinsと起動時24immutable artifactsも保持。小さなcontrol/journal/失敗worker記録98ファイルをOUT/failure-controlへ複製してhash照合した。成功用collector/finalizerは実行していない。

## 前回停止時の判断（今回のユーザー指示で再試行を許可）

次の判断は、システムの負荷が落ち着いた状態で、残り1区間だけを別の試行として再実行するか。今回の失敗attempt1は未公開stageを含めそのまま保持し、再使用・削除しない。現在の高速再開helperは「完了数×3＝journal件数」を要求するため、今回のfailed末尾2recordを含む359件をそのまま受け入れない。再開する場合は外部pinに基づく失敗末尾の扱いを検証する必要がある。無条件にcacheへ追加したり、上限引上げ・新しいinvocationを自動実施したりしない。

Python C:/Python314/python.exe -B。既存外部helperのraw hashは97990096b9ccea31054209b164c8643fab7b54c2d512d8ce52256efe7fa8063d、起動snapshotは05152fb2b81570b573fc96932a1576970e85aaab2673fb067c4b6df2e1cd1d37。今回も実OS26200.9457/CPython3.14.0、exe/DLL pinは開始/終了で一致。旧正式pinは維持。

formal_permission=false/campaign加算0、保存score以降の監査という範囲を維持。完全runtime inventory・profile/score導出/全bootstrapの独立S6・全120/holdout/性能評価・研究Phase 2/3全体は未完了。実計算source c01d1c9と本流889cfc3は変更せず、既存dirty親policy文書を保全しcommit除外。OS/pagefile/Python設定変更、追加agent、回帰試験、push/merge/CIなし。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
