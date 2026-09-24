# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**保存済み全120区間/720評価の観測→profile/score→ledger検算が完了。前回比較表の全720件とも一致した。新しい実験は起動していない。**

- [今回の全720評価検算](results/anomaly-multiseed-v0.3-full-connected-audit-2026-09-24.md)、[接続実装](results/anomaly-multiseed-v0.3-connected-observation-audit-2026-09-24.md)、[最初のscore検算](results/anomaly-multiseed-v0.3-independent-score-audit-2026-09-24.md)
- [720評価の比較](results/anomaly-multiseed-v0.3-dev-smoke-comparison-2026-09-24.md)、[原因調査](results/anomaly-multiseed-v0.3-failure-analysis-2026-09-24.md)、[上司向け報告](results/banto-ai-anomaly-briefing-2026-09-24.md)
- 候補: C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。検算実装2505fed6527a00891b9991720421b504a678899f、今回実行HEAD f727be6bfb02b8fb7385bd34ce1121a866d8f64f。長い引継書§154。
- 今回OUT: artifacts/full-connected-audit-2026-09-24。checkpoint-120-completed.jsonが全件完了記録、summary.jsonが前回比較との照合・資源・集計。最終文書commit/pinはsavepoint-evidence.json。前回接続検算OUTも変更しない。
- 前段原因調査の保存点1f4242f、OUT artifacts/dev-smoke-failure-analysis-2026-09-24のmanifestは2704bytes/SHA256 0c1cd127e95f1ad2e8924ed410f5ab33b73372f47261684a5ac889f109af0c1e。比較・原因調査・完走の既存artifactは変更しない。

## 今回の成果と次の作業

src/banto_ai/anomaly_v03_score_audit.pyはstdlibのみでC0/C1/C2を復元する。producer/数値helper/契約定数をimportしない。phaseは観測transitionから、profileは正常fit/calibrationだけから作る。C2逆行列は別方式のpivot付きGauss-Jordan。浮動小数値はabs/rel各1e-12、状態/整数/判定フラグと依存観測値は厳密に照合する。保存score自身と閾値フラグの矛盾も拒否する。

前回41項目を通過した検算本体はhash不変。今回の実行補助4試験通過。全120区間（dev576/smoke144、計720評価）の34560 profiles/10368000 score行、source17272/equipment9949 episodes、incident14400件と指標が一致。全件の保存評価結果success。前回比較表の元データとも全720件でidentity/attempt/件数/指標が一致した。119区間714評価を新規検算し、区間0の6評価は外部pinと全対象入力hash一致後に再利用。過去12評価を別加算しない。ユニークな導出検算数は720に更新。

現在は完全なdev/smoke capture・正常prefix健全に限定。ゼロMADや非有限演算の判定不能について理由・部分的な校正sample・score利用不能を照合し、evaluation_outcome=inconclusiveを維持する。部分capture/正常prefix欠損/holdoutは拒否する。新CLI audit_anomaly_v03_observations.pyは外部SHA256付き完走保存点から登録計画・最終監査済みattempt・各入力pinを照合し、独立score検算後に同じ結果をledger監査へ渡す。元controller/監査CLIや旧720評価のaudit reportは変更していない。過去publication/source/runtime/supervisionは保存点を前提とし、再検査したとは扱わない。

**次は正常生成/overlay/丸めの独立検算を設計し、保存観測の作成工程まで確認する。** 全720評価へのprofile/score/ledger検算は完了した。bootstrap/CI/gate、単一writer受入/runtime inventory/資源見積りは別の残件。新しいholdoutや長時間producerは起動しない。

今回の全720件にはprofile/score/ledger_derivation_verified=trueを返すが、independent_s6_complete/formal_permission/promotion_allowed=false、performance_status=not_evaluatedを維持。整数等を浮動小数の許容誤差で緩めない。照合成功と評価のsuccess/inconclusiveを分けて報告する。

研究上はC1が有力（機械91.67%・センサー95%・警報正解率95.73%）。停止中コンベヤーは対象速度が弱く、C2モーターは補正による相殺が見られた。欠損重複の90%上限は計画§3.3の想定どおり。閾値/候補/分母を変更せず、正式採用や実設備性能とは分けて扱う。

所要1196.095751秒（約19分56秒）、6新規区間ごとの中間保存19回。照合入力は重複除外2281files/15903023776bytes、240datasets。119区間の資源を記録し、process peak private187.53MiB、処理後private最大129.89MiB。最小空きRAM14.59GiB/commit余裕13.42GiB、終了時RAM15.47GiB/commit15.58GiB、C/D空き137.72/323.55GiB。新OUT約7.96MB。継続的なリーク不在やPC全体の容量変動原因は保証しない。

## 完走証拠と保全

今回集計の起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。旧OUT artifacts/chunk-119-retry-2026-09-24のsavepoint-evidence.jsonは8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。旧OUTは変更禁止。失敗chunk119/attempt1は保存し、監査済みattempt2のみ集計した。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiはclean 889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

最終実行control000010は2026-09-24 JST17:54:05に正常終了。全120区間/720評価、journal362、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a、累積160357.1738277001秒。controller/所有worker終了確認済み、heartbeat banto-24はPAUSED。追加invocation/holdoutは起動しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
