# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。**120区間/720評価の比較に続き、停止中・欠損重複の見逃し原因を保存データで調査済み。次は正常profile・score導出の独立検算。追加評価は起動していない。**

- [上司向け報告](results/banto-ai-anomaly-briefing-2026-09-24.md)
- [比較表・件数・残項目・再現手順](results/anomaly-multiseed-v0.3-dev-smoke-comparison-2026-09-24.md)
- [見逃しの原因調査](results/anomaly-multiseed-v0.3-failure-analysis-2026-09-24.md)
- 今回OUT: `artifacts/dev-smoke-failure-analysis-2026-09-24`。findings.json、summary.json、input-pins.json、validation.json。最終commit/pinはsavepoint-evidence.json。
- 前段比較OUT: `artifacts/dev-smoke-comparison-2026-09-24`、保存点b5b9403、manifest SHA256 `074647cbe858e92d0fe064ab3902c8fab6304a2037cb9d28280b6668a521b095`。既存artifactを変更しない。
- 候補: C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。集計器保存点eb3f4cc。長い引継書§151。

## 結果と次の作業

開発8 seeds/576評価、smoke2 seeds/144評価を分離し、欠損なし/ありと両条件合算を出した。両条件合算でC1は機械異常2200/2400（91.67%）、センサー異常2280/2400（95.00%）、正解警報4480/4680（95.73%）。C2は機械異常2158/2400（89.92%）、センサー異常95.00%、正解警報4438/4680（94.83%）。C1/C2は正常区間の誤警報0件だが、全区間の未対応警報200/242件。検知できた異常の平均delayはC1約1.26秒、C2約1.25秒。母集団が異なるため速度優位とは解釈しない。

C1/C2共通の見逃しはlayout6（コンベヤー・停止）の機械異常。C2はlayout0（モーター・停止）にも追加見逃し。欠損ありではセンサー異常検知率が100%→90%、C2は温度欠損が他3信号の判定にも影響した。3件の保存評価を例としてhash確認して読み、停止条件のfirst_candidate_no_target_onsetと欠損重複時のno_candidate_in_windowを記録した。全原因をこの3例から断定しない。

**原因調査完了：** 全10 seedsのcore停止2 layouts×C1/C2（40評価）と、最初のdev seedの全12 layouts×C1/C2のquality-stress（24評価）を確認。コンベヤー停止100件/方式は速度scoreが6秒窓で一度も閾値を超えず、振動警報があっても対象速度の検知として正解にならない。C2モーター停止21見逃しは3 seedsに6/10/5件、offset 1/2の28点が閾値以下で、他信号（主に振動）の項が電流の異常残差を打ち消していた。欠損重複の10回目はoffset 1..4が利用不可で2点連続を作れない。stress sensor recall上限90%は計画§3.3の登録済み仕様であり、不具合として直ちに修正する必要はない。

64評価・68入力ファイル約1.295GBを約40秒で読み、680 incidentを調査。保存profileと依存値から3,704点の残差/scoreを別途算出し、絶対/相対各1e-12以内で一致。最初のseedの停止2 layouts×両条件の4観測ファイルで1,680依存セルも一致。保存profileの生成過程は検算していないので完全S6の代用にしない。新規生成/評価/holdoutは0。新規出力は約4.8MB。資源は前後観測のみでpeak/リーク証明ではなく、D空き約1.21GiBの減少の原因は未特定（終了時約374.40GiB空き）。

**次の作業は保存観測からC0/C1/C2の正常profile・score導出を別実装で検算するconsumerの不足分を進めること。** 観測時刻/qualityからのphase/availability、正常fit/calibrationからのprofile復元、残差/scoreを順に検証する。今回の抽出例は回帰確認に使える。正常生成/overlay/丸め、bootstrap/CI/gateの独立検算は別に残る。登録済み方式・閾値・分母・困難な配置を維持する。単一writer・OS更新許容の受入条件、完全runtime inventory、producer/consumer凍結、資源見積りも正式評価前に整理する。保留した専用principal試験を再開する意味ではない。

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
