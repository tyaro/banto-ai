# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**120区間/720評価の完走・照合に続き、開発・動作確認データの3方式比較と上司向け資料を作成済み。追加評価は起動していない。**

- [上司向け報告](results/banto-ai-anomaly-briefing-2026-09-24.md)
- [比較表・件数・残項目・再現手順](results/anomaly-multiseed-v0.3-dev-smoke-comparison-2026-09-24.md)
- 今回OUT: `artifacts/dev-smoke-comparison-2026-09-24`。data/summary.json、evaluations.json、input-pins.json、diagnostic-examples.json。最終commit/pinはsavepoint-evidence.json。
- 候補: C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。集計器保存点eb3f4cc。長い引継書§150。

## 結果と次の作業

開発8 seeds/576評価、smoke2 seeds/144評価を分離し、欠損なし/ありと両条件合算を出した。両条件合算でC1は機械異常2200/2400（91.67%）、センサー異常2280/2400（95.00%）、正解警報4480/4680（95.73%）。C2は機械異常2158/2400（89.92%）、センサー異常95.00%、正解警報4438/4680（94.83%）。C1/C2は正常区間の誤警報0件だが、全区間の未対応警報200/242件。検知できた異常の平均delayはC1約1.26秒、C2約1.25秒。母集団が異なるため速度優位とは解釈しない。

C1/C2共通の見逃しはlayout6（コンベヤー・停止）の機械異常。C2はlayout0（モーター・停止）にも追加見逃し。欠損ありではセンサー異常検知率が100%→90%、C2は温度欠損が他3信号の判定にも影響した。3件の保存評価を例としてhash確認して読み、停止条件のfirst_candidate_no_target_onsetと欠損重複時のno_candidate_in_windowを記録した。全原因をこの3例から断定しない。

**次の小さな作業は、停止中の2条件と欠損重複の失敗理由を保存済みデータで切り分けること。** その結果を文書化し、profile/残差/score導出の独立検算範囲を具体化する。登録済み3方式・閾値・分母・困難な配置を維持し、結果に合わせた除外や緩和はしない。単一writer・OS更新許容の受入条件、完全runtime inventory、producer/consumer凍結、資源見積りも正式評価前に整理する。保留した専用principal試験を再開する意味ではない。

今回集計は124入力/20179770bytesの保存監査等をhash確認して0.602秒。巨大な観測/scoreの全再読込み・再計算は不要だった。集計器7テスト通過。raw数/分母を合算し、ゼロ警報のprecisionや未検知delayをnullとして保持。平均delayは検知件数で加重し、全体中央値は推定しない。補助の診断例3評価は別途約53.5MBを読んだだけ。

formal_permission=false/promotion_allowed=false/performance_status=not_evaluated、holdout未参照、bootstrap未実施。今回の比較は合成dev/smokeの記述統計であり、完全S6・正式gate・実設備性能・Phase2/3全体の完了ではない。今回のC1の良好さで登録済みholdoutの比較方式を減らさない。

## 完走証拠と保全

今回集計の起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。旧OUT artifacts/chunk-119-retry-2026-09-24のsavepoint-evidence.jsonは8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。旧OUTは変更禁止。失敗chunk119/attempt1は保存し、監査済みattempt2のみ集計した。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiはclean 889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

最終実行control000010は2026-09-24 JST17:54:05に正常終了。全120区間/720評価、journal362、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a、累積160357.1738277001秒。controller/所有worker終了確認済み、heartbeat banto-24はPAUSED。追加invocation/holdoutは起動しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
