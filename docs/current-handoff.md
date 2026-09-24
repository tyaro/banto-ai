# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**信頼区間・候補比較の独立算術を実装。21試験通過、全200万個の固定bootstrap抽出番号と凍結hashが一致。実データの信頼区間は未算出。**

- [今回の計算層検証](results/anomaly-multiseed-v0.3-independent-inference-math-2026-09-24.md)、[全240datasetsの生成検算](results/anomaly-multiseed-v0.3-independent-generation-audit-2026-09-24.md)、[全720評価のscore/ledger検算](results/anomaly-multiseed-v0.3-full-connected-audit-2026-09-24.md)。長い引継書§156。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。推論算術実装/実行 `4dd9795c347fc5d00a38c4dfb42379ffc1f8337d`。今回OUT `artifacts/independent-inference-math-2026-09-24`、最終文書revision/pinは`savepoint-evidence.json`。

## 今回の成果と次の作業

`anomaly_v03_inference_audit.py`はstdlibのみ。固定drawのrejection sampling、ratio-of-sums、同じcluster drawでの候補差、type-7 CI、null replicate保全、全層/8 targetsのabsolute/paired gate、C1優先選択を実装した。入力は手計算用cluster集計で、実データの認証や12-layout coverageをまだ検査しない。

40×50,000=2,000,000個の固定index全列hashはe375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5と一致。4 golden行も一致。観測生成用の登録seedは実行していない。21単体試験通過、7手例を各2 clusters/4 replicates・9tables/180gatesで保存した。結果はfixture_*欄だけ。実際のselected_candidate=null、formal/promotion=false、performance=not_evaluated。

所要3.633秒、peak private 29.26MiB、最小空きRAM 17.71GiB / commit余裕 21.68GiB、終了時C/D空き 131.04/298.63GiB。初回の十進手答えassertの1 ULP差は試験側だけを修正。算術やgate比較を丸めず、境界試験通過。旧artifacts/実計算source/本流/dirty guardは不変、banto-24 PAUSED。

**次は、監査済み保存結果からseed単位のraw countsを認証・集計する入口を実装する。** 登録順、12 layouts×両層×3候補、profile状態、予定母数、重複/欠落、今回の算術との対応を検査する。現dev8/smoke2はroleを区別した記述集計まで。正式40 holdout bootstrapを現10 seedへ代用しない。holdout/producer/正式gateは起動しない。

正式analysis schemaへの接続、実データCI/全gate/選択監査、slice/delay、runtime/単一writer受入は残る。Phase 2/3全体や完全S6を完了扱いしない。CIを算出するための算術検証と、Bantoの実性能CIの完了を混同しない。

## 前工程の到達範囲

全120区間・240datasetsの正常生成/overlay/丸めは4,320,000保存観測行で完全一致。全720評価のprofile/score/ledger検算と入力pinで接続済み。旧C1/C2の記述統計は変わらない。生成検算の実装47dbc165f12fb1ce7608bb57625cb498bc4a4d04、文書31b73008828a52681f2ae9a887d88ddedecb516f、OUT artifacts/independent-generation-audit-2026-09-24、成功はverified/、manifest 29473bytes/SHA256322a7fe20b23febcb4467ba16034ab9bae5c209777590150c61bccbae09c90f8。

前工程は既存10 seedを120 pairs分メモリ内で検算再構成し、新dataset/新評価は0だった。今回の算術検証は観測seed再構成も0で、固定bootstrap indexだけを計算した。旧観測/score検算は不要に繰り返さない。

## 完走証拠と保全

起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。`artifacts/chunk-119-retry-2026-09-24/savepoint-evidence.json`は8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。前回全件score検算保存点は26529bytes/SHA256 b591663d8026e348b81e427da8a169702625b160a1352cd7e7e2c07c6e43e9c9（文書commit64fa36c）。これら旧OUTは変更禁止。失敗chunk119/attempt1は保全し、verified attempt2だけを使用。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiはclean 889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

control000010は終了済み。journal362、全120区間/720評価、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a。controller/所有worker終了確認済み、banto-24 PAUSED。旧保存点・元payloadを理由なく再計算しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
