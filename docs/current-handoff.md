# 次のタスク用の短い引継ぎ

更新: 2026-09-24 JST。最初にこの文書を読み、下記候補worktreeの `git status` / `git log -3 --oneline` を確認する。全履歴は必要箇所だけ読む。

## 場所と最新保存点

- **作業先**: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`、branch `codex/s4-b1-windows-engineering`。
- 最新実装保存点: **c01d1c978f78bab51391392d56cdcb7aab5afaab**（環境snapshotと明示起動CLI、§135）。前回chunk57〜80の24区間/144評価も成功し、累計81区間/486評価（§140）。実装変更なし。
- 最新の完了済み実データ確認も **c01d1c9**。前回chunk57〜80の最終保存点 **855e359136d568ddf5b29bef84a7d69e82e9e009**、開始09eb51f/中間8f23587・ba25ca0・26e0d0a。今回はそこから次の24区間を開始した。実装変更なし。過去の保存点・試行は保持する。
- 本流 `D:\develop\banto-ai` は **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、作業対象にしない。push/mergeなし。
- **既存dirtyを保全・commit除外**: `docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md`、8461 bytes、SHA-256 `443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621`。

## 目的と現在地

**現在地**: ユーザーの再開指示に従い、区間81〜104（最大24新規区間）を診断付きcontrol000007として起動した。controller PID **40372**、開始UTC **2026-09-23T11:06:21.3962444Z**（JST20:06）。[今回の再開記録](results/anomaly-multiseed-v0.3-chunks-81-104-retry-2026-09-23.md)。開始時の確定数は累計81区間/486評価、残39区間/234評価。新規18区間まで中間確定し、累計99区間/594評価。今回全24区間の最終照合は未完了。前回control000006/PID29852はMemoryErrorで終了・保全済みで、[旧停止記録](results/anomaly-multiseed-v0.3-chunks-81-104-continuation-2026-09-23.md)を変更しない。

**継続確認**: heartbeat **banto-24** を今回の再開へ更新しACTIVEにした。候補 `artifacts/chunks-81-104-retry-2026-09-23/FOLLOWUP.md` に従い、30分ごとに1回だけ状態・資源・新しい診断を確認し、新規6/12/18区間で保存する。旧失敗folderや今回controllerを重複起動しない。正常/異常終了とも記録を保存して定期確認を停止する。

今回の再開前に成功済み5221＋失敗control6件の計5227ファイルを1回hash照合し、旧成功・失敗・調査・診断検証の証拠94ファイルを確認した。今回OUTのbaseline.json/preserved-artifacts.jsonに保存した。数値計算は行わず、前回の失敗状態と累積活動を維持して起動した。

**前回の保存点**: 最終855e359、manifest10443 bytes/SHA256 c4017dacb4a80da2a27fe90c57f53c0fab95991ce44bb8a91b969909c891f0ca。過去の起動・中間・最終証拠を保持する。

**今回の保存点**: 再開OUT `artifacts/chunks-81-104-retry-2026-09-23/` のlaunch-savepoint.jsonに起動保存点9340199/pinを保持する。新規6区間は0c98a7d/milestone-06.json、新規12区間は28ca9f7/milestone-12.jsonに保存済み。新規18区間の中間観測をmilestone-18.jsonへ保存し、今回2文書のcommitをfollowup-state.jsonへ記録する。前回の失敗は保存点3bba1bdと旧OUT/failure-savepoint-evidence.jsonに保持し、診断コードと短い確認は27346e9に保存済み。

初期確認UTC11:09:21（JST20:09、180.2秒）: 既存chunk0再照合中、journal243/新規0、メモリ診断エラー/欠落0、stderr空。空きRAM約14.28GiB/C144.76GiB/D47.95GiB、commit余力約15.50GiB。PID40372のwrapper/開始日時も一致。以降は30分間隔の1回確認へ任せる。

**新規6区間の中間保存**: UTC2026-09-23T16:48:08.366742+00:00（JST2026-09-24 01:48、20506.3秒）。区間81〜86の6区間/36評価が確定し、累計87区間/522評価。区間87はrunning、journal262/保持receipt6、既存81区間の再照合は終了（active_audit=null）。PID40372の同一性を確認した。空きRAM14446272512/C154833727488/D441718124544 bytes、commit31256702976/limit47691943936/余力16435240960 bytes。controller private132116480/peak233762816 bytes、診断エラー0/欠落0/無効化なし、stderr空。6件の保持receiptは原本とhash一致。milestone-06.jsonに保存した中間観測で、全24区間の最終照合やclosed再開pinではない。次は新規12区間で保存し、今回の処理をそのまま継続する。

**新規12区間の中間保存**: UTC2026-09-23T18:22:20.220959+00:00（JST2026-09-24 03:22、26158.0秒）。区間81〜92の12区間/72評価が確定し、累計93区間/558評価。区間93はrunning、journal280/保持receipt12、active_audit=null。PID40372の同一性を確認した。空きRAM14104588288/C154597003264/D441718099968 bytes、commit31135866880/limit47691943936/余力16556077056 bytes。controller private131391488/peak233762816 bytes、診断エラー0/欠落0/無効化なし、stderr空。今回増えた6件の保持receiptは原本とhash一致、先の6件は保存済みpinを再利用し、milestone-12.jsonへ中間観測を保存した。次は新規18区間で保存する。処理は継続中であり、全24区間の最終照合は未実施。

**新規18区間の中間保存**: UTC2026-09-23T19:57:32.353575+00:00（JST2026-09-24 04:57、31870.1秒）。区間81〜98の18区間/108評価が確定し、累計99区間/594評価。区間99はsaved_pending_verification、journal299/保持receipt18、active_audit=null。PID40372の同一性を確認した。空きRAM14217084928/C153837621248/D441718063104 bytes、commit31022981120/limit47691886592/余力16668905472 bytes。controller private133799936/peak233762816 bytes、診断エラー0/欠落0/無効化なし、stderr空。今回増えた6件の保持receiptは原本とhash一致、先の12件は保存済みpinを再利用し、milestone-18.jsonへ中間観測を保存した。残り6区間を継続し、正常終了後に今回24区間の照合と最終保存を行う。追加区間は起動しない。

[研究ロードマップ](research-roadmap.md)のPhase 2（予測モデル比較）、Phase 3（異常検知・ドリフト）が目標。現在はPhase 3のanomaly v0.3、全dev/smoke実行へ進むための接続作業。小さい保存点の完了をPhase全体の完了として数えない。

通常の単一writer保存を優先する方針を採択済み。全dev/smokeはdev96＋smoke24＝120 chunks/720 evaluations、1 chunkは同一seed/layoutのcore/stress×3候補。新engineering runの先頭81 chunks/486 evaluationsが完了し、残り39 chunks/234 evaluations。正式campaign加算は0を維持する。

実装済み: 固定campaign plan/journal、追記store/receipt回復、attempt descriptor、実ファイルreader、新形式6件のproducer・独立audit、controller、所有process監視。実コマンドで生成→両再計算→別process監査→fresh照合→journal確定まで接続済み。launcherの5回の継続実行でjournal243記録を確定した。

**継続入口**: `anomaly_v03_campaign_launcher.py` / `tools/evaluator/run_anomaly_v03_campaign.py`。`prepare`は所有processで実環境snapshotを収集し、新しいmetadata/初期closed記録と外部prepared pinを作る。`continue`は外部prepared/最新closed hashと明示`--max-chunks`を必須にし、Run.run活動時間内でfresh inspectionしてからNativeCallbacksへ進む。終了不明の元ownerはCLIが終了確認まで保持する。別requestの48時間/32GiB候補、逐次処理、未閉鎖呼出しの再使用拒否を維持する。

**次に行う作業**: 今回のcontrollerだけを継続確認する。[MemoryError調査](results/anomaly-multiseed-v0.3-memory-error-diagnosis-2026-09-23.md)の原因は未確定。検証済み外部helper27346e9を今回OUT/memory_diagnostics.pyへ保存し、SHA256 4c44f9de74f5e3207efce471442be55b4ebb7f650968578fd1887602b7531c72を起動時照合した。最新状態のsystem_memory/active_audit/memory_diagnostics、異常時はmemory-events.jsonlの例外位置を見る。累積活動97603.864249秒から継続、起動時残り75196.135751秒。既存81区間の再照合を含め約9.4〜9.5時間の見込みで、今回を越える区間は起動しない。

source/consumer/controllerはすべてc01d1c9、Python3.14.0を維持。snapshotはsource397/stdlib2559/native48/extension8の時点観測で、worker/auditorのruntime closureや完全S6ではない。全体上限は境界での協調停止で、controller/process treeへの強制上限は未整備。再開時の過去verified再照合には一連の処理途中のwrapper予算検査がない。旧trialを新runのcoverageへコピーしない。

**稼働中runと開始pin**: clean `C:/Users/TKent/.codex/worktrees/v03p/banto-ai` / c01d1c9、`artifacts/v03-runs/r1`、今回control000007。開始closedは **`run/control/000006/closed.json`** / raw SHA-256 **18af12a119e3acc0600594d8eaf6263607f5f7c85d68ff3acbda31931d4b9e4c**、status=failed/stop_reason=exception。今回起動中にこのpinを再使用しない。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。開始journal243/next81、成功時はclosed000007の実測hash/journal315/next105を保存する。

controllerは最新receiptと各verified sequenceのdescriptor hash mapを外部保持し、再起動時に完了済み証拠を再照合する。同じsession内の再検算は省く。`TransitionIncomplete` は未確定intentを保持して停止する状態で、自動再使用不可。確定後のreceipt喪失だけは外部intent hashから読取り回復できる。`UnreapedWorker` は元のprocessを保持し、終了確認が必要。現在のattemptやログを上書きしない。

`attempt-audit` CLIは **旧形式chunk 0専用**。新manifestは **`audit_anomaly_v03_chunk.py` / `checkpoint_anomaly_v03.py attempt-chunk-audit`** で読む。producer監視のbinding/runtime_after、audit監視のexact argv/runtime_before/afterが必須。新しいengineering起動CLIを正式gateの許可に読み替えない。campaign credit=0、formal_permission=false。profile/score導出・bootstrapの独立検算、完全runtime inventory、全体実行、holdout、性能評価は残件。

## 検証と資源

最新の実確認は今回MemoryErrorで停止、新規確定0。終了UTC2026-09-23T02:57:30.180163+00:00（JST2026-09-23 11:57）、今回11198.201秒（約3時間7分）、累積活動97603.864249秒、48時間候補の残り75196.135751秒（約20.89時間）。終了時の空きRAM7879757824/C131049820160/D116994351104 bytes、controller peak232960000/終了時private159330304 bytes。 直前の成功記録はchunk57〜80/144評価、累計81区間/486評価（§140）。controller PID29852の消失、診断threadの終了、inspection worker PID35784のexit0/終了確認を記録した。新規producer/auditは起動記録なし。前回manifestと記載49ファイルの計50件、既存journal243ファイルのpinを照合済み。runの名前一覧は前回5221ファイル＋今回control6ファイルの5227件で一致。既存の数値payload全体は再hashしていない。今回controlの6ファイルはfailure-controlへコピーし原本とhash一致。成功用collect.py/finalize_evidence.pyと数値計算は再実行していない。

実装時のsnapshot/launcherと従来owner保持回帰は **17件pass/6.691秒/peak private40.25MiB**。独立P0〜P2指摘0/進捗poll0、safety/diff-check pass。小規模実IOでOS/source/native/数値mockを明示した。mockなし実prepare67.650秒/inspection37.20MiB、継続API17件、native接続42件＋path修正後13件、以前の実6評価の証拠も保持。広い数値テストはMemoryError歴があるため必要な選抜を使う。

Pythonは **`C:\Python314\python.exe -B`**、`$env:PYTHONPATH='src'`。最新の選抜:

```powershell
C:\Python314\python.exe -B -m unittest tests.test_anomaly_v03_campaign_launcher
```

新変更に必要な範囲だけ検証し、合格済み試験/実演を理由なく繰り返さない。以下は前回成功時の観測: producer最大334.3MiB、audit最大188.6MiB、controller peak225.6MiB/終了時90.2MiB。60秒間隔501標本の空きRAM最小9602994176 bytes（約8.94GiB）、観測エラーなし。controller privateは終了時に低下したが、長期リーク不在は未評価。

前回成功した連続運転の終了UTC2026-09-22T18:08:59.297124+00:00（JST2026-09-23 03:08）、空きRAM11659157504/C161118416896/D119168434176 bytes。Windows26200.9457/CPython3.14.0とexe/DLL hashは前回同値、開始・終了・各workerのruntime一致、全所有process終了済み。

Windows 26200.9457、boot既存観測2026-09-19T03:46:06.5+09:00、CPython3.14.0。Windows Updateはengineeringでは実値記録で許容、旧正式pinは不変。ユーザーはこのPCで他作業なし・大きめ作業OKと許可済み。資源監視とセーブポイントは継続する。

調査時UTC2026-09-23T10:03:22（JST19:03）は、空きRAM約14.16GiB、system commit約28.98/44.42GiB、C空き約144.83GiB、D空き約49.35GiB。ページファイル自動管理。停止から約7時間後の観測なので停止時の状態と混同しない。現在のD空きは停止時約108.96GiBより減少しているが原因未確認。

診断準備の最新probeはUTC2026-09-23T10:51:58（JST19:51）。空きRAM約14.25GiB/C144.77GiB/D47.95GiB、runtime pin不変。固定sourceの `open_run` による状態確認1.251秒/peak private約26.98MiB。新invocationなし、closed000006 bytes/control一覧不変。累計件数や活動時間を増やしていない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、全dev/smoke/holdoutの長時間実行を自動起動しない。push/merge/CIはこの工程では行わない。

## 必要になったときに読む記録

- [今回の区間81〜104の記録](results/anomaly-multiseed-v0.3-chunks-81-104-continuation-2026-09-23.md)、[前回区間57〜80の結果](results/anomaly-multiseed-v0.3-chunks-57-80-continuation-2026-09-22.md)、[snapshot/launcherの操作](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)、[API/CLI仕様](anomaly-v03-independent-audit-and-checkpoints.md)。まず次工程に関連する末尾を読む。
- [長い引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)の§116（運用変更）、§123〜141（現在の実装経緯と今回停止）。全体の再読込みは不要。
- 最新の失敗・保全証拠: `artifacts/chunks-81-104-continuation-2026-09-23/failure-savepoint-evidence.json`。直前の成功証拠は`artifacts/chunks-57-80-continuation-2026-09-22/savepoint-evidence.json`（10443 bytes/SHA256 c4017dacb4a80da2a27fe90c57f53c0fab95991ce44bb8a91b969909c891f0ca）と記載49ファイル。過去の証拠は保持し、数値再計算しない。
- 以前の実6件: clean `C:\Users\TKent\.codex\worktrees\v03\banto-ai` / 25d1084の `artifacts/anomaly-v03-chunk-trials/trial-01`（68 files/133323148 bytes）。`trial-evidence.json` に全pin。完走済みで再起動不要。
- 保持する新しい失敗試行: `C:\Users\TKent\.codex\worktrees\engineering-chunk-20260921\banto-ai` / 8b34387の同名trial（54 files/107889570 bytes）。261文字pathで6件目保存に失敗し、終了・failed記録済み。`failed-trial-evidence.json` に全pin。修理・再使用・削除せず、今後も登録保存pathを248 UTF-16文字未満に抑える。OS設定は変更しない。
- 元の実6件: clean producer `C:\Users\TKent\.codex\worktrees\engineering-v03-20260916` / `0086ffe226ed58c618f6bc001ebd0c99a90e66e9` の `artifacts/anomaly-v03-engineering-dev/trial-01`（46 files/132553275 bytes）。必要がなければ再検算しない。
- 元の独立consumer: `C:\Users\TKent\.codex\worktrees\engineering-audit-20260916` / `0c8377d0d55fc2813f2c18fa618c33646bc6666c`。保存auditは候補の `artifacts/independent-ledger-audit-2026-09-16/audit.json`（SHA-256 `e61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021`）。保存score以降の検算であり、完全S6ではない。
