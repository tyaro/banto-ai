# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**最後の1区間の再試行に成功し、全120区間/720評価の照合完了。今回の評価は終了、追加起動なし。**

候補C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。今回OUTはartifacts/chunk-119-retry-2026-09-24。最終commit/pinはOUT/savepoint-evidence.jsonとfollowup-state.json。実装f4cda3b、起動06c9f88を保持。[今回の結果](results/anomaly-multiseed-v0.3-final-chunk-retry-2026-09-24.md)、長い引継書§149。

control000010のchunk119/attempt2は正常終了し、最後の6評価がすべてsuccess、累計**120区間/720評価**の保存結果を照合した。status=completed/next_unverified_chunk=null、journal362件。失敗したattempt1の2記録とstageは保持した。終了UTC **2026-09-24T08:54:05.861275+00:00**（JST **2026-09-24 17:54:05**）、exit0、所要1063.882秒（約17分44秒）。

producer 558.891秒、独立audit 91.668秒、audit_status=ledger_checks_passed。controller PID35264の消失をUTC2026-09-24T09:11:55.6213023Zに確認。producer/audit/inspectionの所有workerはすべてexit0/終了確認済み。既存119区間は全7730ファイルのbyte/source/runtime一致（75.222秒）後に監査を再利用し、新規attempt2は元の監査を完了した。

終了後のcollectorは7800 files/16081676236 logical bytesをhash照合し、前回7730ファイルと過去356artifact pinsの不変、最新receipt000362/descriptor/marker/全6successを確認した。所要50.227秒。数値再計算は行わず、最終manifest作成時の全payload再hashも省く。証拠は新OUTのevidence.jsonとdiagnostics-summary.json、最終commit/pinはsavepoint-evidence.jsonに保存する。

診断は17周期標本/25イベント、新規audit_begin/end各1件、観測error/drop=0、無効化なし、診断thread終了済み。system commit余力の最小標本14.50GiB、空き物理RAMの最小標本12.62GiB。controller peak private 218.80MiB、producer peak 330.73MiB。終了時空きRAM/C/Dは13.52/140.62/402.76GiB。今回の標本は安定していたが、前回失敗の原因やリーク不在は断定しない。

最新closedはrun/control/000010/closed.json / SHA256 **a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a**。累積活動160357.173828秒（44.54時間）、48hまで残り12442.826172秒。失敗時間・worker900秒/48h/32GiBは維持。追加invocationは起動しない。heartbeat banto-24はPAUSEDに変更済み。今回の継続確認は停止した。

今回予定の120区間の実行と保存score以降の監査は完了。formal_permission=false/campaign加算0を維持し、完全runtime inventory・profile/score導出/全bootstrapの独立S6・正式gate/holdout/性能評価・研究Phase2/3全体の完了とは区別する。次はこの結果を根拠に研究計画の残項目を整理する判断であり、新たな評価はこのheartbeatでは開始しない。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiはclean 889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e。旧OUTと既存dirty親policy文書は保全しcommit除外。prepared pinはbe582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7。最新stateにはclosed000010を使う。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
