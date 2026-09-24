# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**control000009で残り15区間を再開済み（PID 25724）。既存105区間の全byte照合と監査再利用は成功。** 起動済みかは今回OUT/launch.jsonとfollowup-state.jsonを先に読む。重複起動しない。

起動UTC 2026-09-24T01:48:22.1234253Z、実装保存点aab4d58e5359497fa8016b8ccb808101dfe9fd40。heartbeat banto-24は今回OUTを対象にACTIVE。初期観測journal 316/running、新規確定0、診断欠落なし。起動保存点はOUT/launch-savepoint.json参照。

最新観測UTC 2026-09-24T03:24:31.095120+00:00：**新規6/15区間完了、累計111区間/666評価**。区間111実行中（journal334）。新規6区間のreceipt318〜333と終端journal hashを照合し、OUT/milestone-06.jsonへ中間保存。診断error/drop=0、空きRAM約13.64GiB、commit余力約15.12GiB。次の保存は新規12区間。commitはOUT/followup-state.json参照。

## 現在の作業と場所

- 候補: `C:/Users/TKent/.codex/worktrees/70b0/banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 今回OUT: `artifacts/chunks-105-119-fast-resume-2026-09-24`。次のheartbeat手順はOUT/FOLLOWUP.md。結果は[再開記録](results/anomaly-multiseed-v0.3-verified-resume-2026-09-24.md)、長い引継書§146。
- 実計算source: clean c01d1c978f78bab51391392d56cdcb7aab5afaab、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、出力`artifacts/v03-runs/r1`。固定sourceを変更せず外部helperだけで再開policyを切り替える。
- 本流D:/develop/banto-aiは889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e/clean。既存dirty親policy文書は8461 bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommit除外。

## 再開方針と保存点

最新closedはcontrol000008/closed.json、SHA25602531b247b12b1275a57c8907924f5ac710c90c4d8dfd079f885d0fd2d5c9211。preparedはbe582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7。control8は失敗終了/保全済み、journal315/next105、累計105区間/630評価。失敗保存点daf17f2d747f080eba893cd1b9f320ce02e5c3c5、旧OUT chunks-105-119-continuation-2026-09-24のfailure manifest SHA2566dbe0e6780a011fcd601fed8a0647275eb2404c977fdd6a6209eaebcd448a32b。元の成功/失敗OUTは変更しない。

新しい外部helperは全6775 files/13,948,054,577 bytesとsource/runtime/closed/journalを照合して既存105区間のcacheだけを初期化する。読取専用の実検証65.357秒/peak約65.3MiB。新規13試験と既存関連45試験は通過。起動時にも同じsnapshotを再照合してから再利用する。snapshot SHA25605152fb2b81570b573fc96932a1576970e85aaab2673fb067c4b6df2e1cd1d37、helper SHA25697990096b9ccea31054209b164c8643fab7b54c2d512d8ce52256efe7fa8063d。新しい15区間の数値監査は従来どおり。単一writer前提で、敵対的同時書換えの隔離ではない。

48h/32GiB・worker上限は不変。累積144993.320914秒、残り27806.679086秒（約7.72h）を継承し、失敗時間を戻さない。既存105の約5.2h再計算を省き、残り15は約4h見込み。control9のみ最大15区間（105〜119）、完走時は全120区間/720評価・journal360・status=completed/next=null。6/12区間で中間保存。終了時に照合・最終保存しheartbeatをPAUSED、追加呼出しやholdoutは起動しない。

## 資源・診断

60秒診断/30分heartbeatを再利用する。今回のaudit_begin/end期待値は**新規105〜119の各15件**。既存105再利用の証拠はresume-verification.json。error/drop/disabled、RAM/C/D、system commit余力を確認する。1回確認したら次回へ任せ、連続poll/追加agent/再計算なし。

前回は既存区間58のdataset読込みstream.readでMemoryError。直前52.4秒でsystem commit+26.56GiB/pagefile+16.68GiB、controller peak約223MiBを記録した。他作業との競合は考えられるが急増元processは未特定。今回の正常再開を原因解明やリーク不在の証明にはしない。Windows26200.9457/CPython3.14.0。OS/pagefile/Python設定を変更しない。

正式許可false/campaign加算0、監査は保存score以降。完全runtime inventory・profile/score導出/全bootstrapの独立S6・holdout/性能評価・Phase 2/3全体は未完了。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
