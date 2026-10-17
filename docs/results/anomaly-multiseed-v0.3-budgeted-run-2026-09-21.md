# v0.3 全体予算候補と閉鎖記録からの逐次継続

2026-09-21 JST。前回保存点 `f6db21c404a4f1a882c1309f485db0e58bcb39e4` からの変更。

実装保存点: **eee93cfa8162e3e161f3b22cf1644a79b02b5a52**。その後の保存は結果・仕様・引継ぎ文書のみ。

## 今回の到達点

`anomaly_v03_budgeted_run.py` に、新規metadataの準備と、完了記録がある呼出し境界から次の区間へ継続するPython APIを追加した。既存の固定plan、controller、producer/auditの形式と個別上限は変更していない。新規CLIや全120区間の実行は追加・開始していない。

前回の実6評価からの単純外挿は約31.2時間/14.9GiB。これを参考に、**48時間/新規出力32GiBを候補上限**として別のrequestへ記録する。完全runtime inventory、全体実行のsource/consumer選定と予算の最終確定は残る。従来のmetadata planの未確定budgetや正式gateは維持する。

| 項目 | 候補値・適用範囲 |
| --- | --- |
| 累積時間 | `Run.run` の活動時間合計48時間。準備・外側の読取り・呼出し間の休止・最終closed記録の書込み時間は含めない |
| 新規出力 | 専用run root内の論理file bytes合計32GiB。hardlink別名も加算する |
| 次区間の開始余裕 | 残り2460秒（41分）、出力1GiB＋32MiB。時間内完了を保証する値ではない |
| controller private | 呼出し/区間境界で2GiB以下を検査 |
| 空き資源 | 開始/区間境界でRAM4GiB、出力volumeのdisk20GiB以上 |
| 所有producer | 900秒/2GiB/log1MiB、既存監視を維持 |
| 所有audit | 600秒/1GiB/log8MiB、既存監視を維持 |

**全体予算は境界での協調的な開始拒否・停止判定であり、controllerやprocess treeへの強制上限ではない。** 1区間の途中や終了時inventory走査で超過する可能性がある。最終区間が検証済みでも時間超過を`stopped/time_budget`として優先する。再開時は過去のverified証拠をcontrollerが再照合するため、再開位置が後ろになるほど追加時間が必要になり、その一連の再照合中にはこのwrapperの途中検査は入らない。区間内検算の既存開始/終了検査は維持する。

## 保存と再開

`prepare(parent, name, plan, observed)` は全120区間の登録pathを事前検査し、まだ存在しない専用rootへ `request.json`、metadata、attempts、初期closed記録を作る。実計算は行わず、既存root・旧trialは使用できない。

`Run` は外部保持したrequest hash、最新 `control/NNNNNN/closed.json` のpath/hash、producer/consumer rootとverifier revisionを必須にする。closed記録にはreceipt、全verified sequenceのdescriptor hash、累積活動時間、前回closed hashを保存する。以前のclosed状態を連鎖して読み、時間の巻き戻し、古い状態の再使用、別の未閉鎖呼出しがある場合を拒否する。

`run(observed, max_chunks=...)` は呼出しごとに新規control directoryを確保し、`started.json` と各journal遷移の小さいreceiptを別々に保持する。区間の順番は既存controllerが決め、1区間ずつ生成→保存→監査→fresh照合→verifiedへ進める。指定件数または予算不足でclosed記録を返す。次の呼出しは返された最新path/hashを外部へ保存してから作成する。

実行中の `control/NNNNNN/stop.request` は区間の境界で読む。停止した呼出しは再利用せず、次の呼出しに新しい番号を割り当てる。通常の失敗を記録できた場合はclosed記録も保存し、次の試行は新attemptを使う。失敗前の成果物は保持する。

`UnreapedWorker`、未確定transition、失敗記録を確定できない状態ではclosed記録を作らない。未終了workerの場合は出力inventoryにも触れず、元のprocess ownerを持つ例外を呼出元へ返す。**API呼出元はそのownerを保持して終了確認を行う必要がある。** このAPIだけを呼んで例外を捨てるlauncherはまだ用意していない。書込み・時計・診断の二次エラーで一次例外を置き換えない。未閉鎖呼出しや途中書込みの自動修理・再開は行わない。

## 検証と制限

小規模の実journal/publication IOを使い、native process・source・runtime・数値計算・時計は明示mockで検証した。2区間→再開後1区間、累積時間、保存prefix不変、停止要求、時間/出力/メモリ不足、失敗後の新attempt、外部pin/履歴改変、未終了worker、未確定transition、二次エラー、最終区間/最終inventoryの時間超過を対象とする。全120の登録path検査も1回確認する。

初回15件pass/76.956秒。独立レビューのP2指摘1件（最終区間と最終inventoryの時間超過表示）を修正し、対応2件を追加した。**最終17件pass/78.522秒/peak private66396160 bytes（63.32MiB）**。再レビューの残存指摘0、進捗poll0。最終測定は `artifacts/budgeted-run-2026-09-21/tests-final.json` に保存した。証拠driverの初回起動はrepository rootをimport pathに含めずloader errorとなったため、driverだけを修正した。失敗記録 `tests.json` / `tests.txt` も保持する。

UTC2026-09-21T12:57:49.595269+00:00、終了後空きRAM13260709888/C174123429888/D119513456640 bytes。Windows26200.9457、CPython3.14.0、exe/DLL hashは前回と同じで試験前後runtime一致。試験process終了確認済み。今回は新しい長時間workerを起動していない。

この試験は全120区間/720評価の実計算、長期メモリリーク評価、完全S6、Phase 2/3全体の完了を追加しない。campaign加算0、formal_permission=false、full_runtime_inventory_complete=false。Windows Updateはengineeringの実値記録方針を維持する。既存dirty、過去の成功/失敗trial、本流は保持する。保護root/principalへの参照、UAC/ACL/service/taskの変更、push/merge/CIは行わない。
