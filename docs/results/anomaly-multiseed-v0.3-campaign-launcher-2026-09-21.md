# v0.3 実行環境の観測と全体起動入口

2026-09-21 JST。実装保存点 **c01d1c978f78bab51391392d56cdcb7aab5afaab**。前回は `5a358a8652bf06a040ae77d9d430da7916c40998`。

## 実装

`anomaly_v03_engineering_inventory.py` は、engineeringのWindows実値でsource、stdlib tree、OSが列挙したloaded native、Python extension、CPU/features、起動条件を収集し、bytesとinventoryを再読する。既存のstreaming hash/native hardlink観測を再利用し、sourceのclean/Git照合と固定科学条件も維持した。正式S4の古いWindows pin、collector、schemaは変更していない。

snapshotは**launcherをimportしたinspection processの時点観測**である。stdlibはsite-packagesを除く通常treeと任意の標準zip、nativeはEnumProcessModulesExで実際に列挙したDLL/CRTを含む。未知のDLLを信頼済みに変えず、数値worker/auditorの実行中すべての依存関係やwarmup/runtime closureの保証は追加しない。`full_runtime_inventory_complete=false`、`formal_permission=false`。環境変数は従来どおり許可された名前のpresenceのみで、値は保存しない。

`anomaly_v03_campaign_launcher.py` / `tools/evaluator/run_anomaly_v03_campaign.py` を追加した。

- `prepare`: cleanな同一revisionをproducer/consumer/controllerに選び、全120の保存pathを事前検査する。新しい専用rootで所有inspection workerを動かし、正常終了・PID・stdout hash/size・runtimeを照合してから、固定planと空journal、初期closed記録、外部保持用prepared pinを作る。実データ生成は開始しない。
- `continue`: 外部prepared hashと最新closed path/hash、明示した`--max-chunks`（1〜120）を必須とする。各呼出しの活動時間内でfresh inspectionを行い、そのpinを保存してから既存NativeCallbacksへ接続する。開始前inspectionと基本runtimeが異なる場合は数値workerを起動しない。
- inspectionは1 processだけを所有し、300秒/private512MiB/stdout＋stderr16MiBを外側で監視する。失敗時も監視記録を保持し、終了不明の場合は出力に触れず元ownerを返す。
- CLIは終了不明のownerを共通helperで保持し、stderr書込み失敗や再度のinterruptでも終了確認を続ける。従来の単発trial CLIも同じhelperへ移し、動作は維持した。

48時間/32GiBは前回の候補設定のまま。全体の厳密な強制上限ではなく、区間境界での協調停止である。preparedやsnapshotは受入freeze、全campaign coverage、S6の代用ではない。全dev/smoke/holdoutの自動起動は追加しない。

## 操作

短いclean checkoutを使用し、Pythonは`C:\Python314\python.exe -B`、`PYTHONPATH=src`とする。

```powershell
C:\Python314\python.exe -B tools/evaluator/run_anomaly_v03_campaign.py prepare `
  --root <clean checkout> --expected-head <full revision> --name <new name>
```

出力は`<checkout>/artifacts/v03-runs/<name>`。`prepared.json`のraw hashと初期closed path/hashはstdoutへ返すので、出力rootとは別の記録にも保持する。続行は次の形で、件数を明示する。

```powershell
C:\Python314\python.exe -B tools/evaluator/run_anomaly_v03_campaign.py continue `
  --root <same clean checkout> --expected-head <same full revision> --name <same name> `
  --prepared-sha256 <externally retained raw hash> `
  --state-path <latest externally retained closed path> --state-sha256 <its raw hash> `
  --max-chunks <explicit count>
```

固定source revisionと出力先を途中で差し替えない。以後は返された新しいclosed pinを外部に保存する。失敗時にsafe closed記録がある場合はCLIのstderr JSONにもpinを返す。未閉鎖状態からの自動回復は行わない。

## 検証

新しいsnapshot/launcher試験16件と従来CLIのowner保持回帰1件が**17件pass/6.691秒/peak private42209280 bytes（40.25MiB）**。小規模の実file/journal IOで、OS/source/native process/数値処理をmockした。2回の内容読取り、DLL一覧やstdlib bytesの変化、Windows値の記録、prepared hash/保存snapshot改変、dirty source/長いpath、inspection失敗、明示件数、owner保持、fresh inspectionから1区間の完了までを確認した。既存budget試験17件や実6評価は繰り返していない。

初期試験で新規testの括弧、tupleのJSON比較、wrapper/controllerの参照、runtime fixtureの不一致を修正した。最終差分の独立レビューP0〜P2指摘0、進捗poll0。repository safety/diff-check pass。記録は`artifacts/campaign-launcher-2026-09-21`へ保存する。

実準備は短いclean checkout `C:/Users/TKent/.codex/worktrees/v03p/banto-ai` / c01d1c9 の新規`r1`で**engineering_run_prepared / exit0**。mockなし、全体67.650秒。inspection PID6136/60.791秒/peak private39006208 bytes（37.20MiB）、正常終了・終了確認・停止理由なし・観測エラー空。controller peak30990336 bytes（29.55MiB）。source397 files、stdlib2559 files/51017552 bytes、loaded native48件、Python extension8件を収集した。これらの実ファイルは収集中に再読した。

専用出力 `artifacts/v03-runs/r1` は **7 files/749075 bytes**。prepared raw hashは `be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7`。初期closedは `run/control/000000/closed.json`、raw hashは `85a6163034c5392ce1ef78f4cbaa6da0faf9c06a66faae03c8c0f8df0c8ebf39`。外部stdoutのpinから再度`open_run`で照合し、journal0/next chunk0/ready/累積活動時間0を確認した。準備後の環境再収集や実データ計算は行っていない。証拠は`prepare-evidence.json`と全7ファイルのpinに保存した。

UTC2026-09-21T13:18:09.894216+00:00、終了後空きRAM13306019840/C174107738112/D119513100288 bytes。Windows26200.9457/CPython3.14.0/exe・DLL hashは前回同値、準備前後runtime一致。全所有process終了済み、既存本流/dirty/過去trialは保全した。

次はこの同一sourceとprepared pinを使い、まず3区間/18評価のengineering連続運転とclosed記録を確認する。全120区間への拡張、実計算processのruntime closure、予算の最終確定、独立S6と性能評価は別に残る。3区間が成功した事実を全120やPhase 2/3完了に読み替えない。
