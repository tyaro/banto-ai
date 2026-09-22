# v0.3 完了済み33区間からの24区間継続

2026-09-22 JST。**区間33〜56の24区間・144評価がすべて成功し、累計57区間・342評価となった。** 27346.369秒（約7時間36分）で正常終了し、終了後のIO/hash照合を完了した。実装変更なし。以下の起動・中間記録は各保存時点の履歴である。

## 開始確認と外部pin

実計算source/consumer/controllerはclean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`。同じ`artifacts/v03-runs/r1`を閉鎖記録から継続する。今回のcontrolは000004。

prepared raw SHA-256 **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。開始closedは **`run/control/000003/closed.json`** / raw SHA-256 **af04684d25c99f69e64a2ac5aacffd92be930d6325ceddd5d9a0ee254f5fa7a0**。journal99/next33/yielded、累積活動28855.997764秒から継続する。実行中の再起動や追加invocationは行わない。

前回manifestは候補`artifacts/twenty-four-chunk-continuation-2026-09-22/savepoint-evidence.json`、10289 bytes/SHA-256 **ddbb32983dadb84fbdca50d990f346c02cdaa5bedc8949d016504562e6d48ec8**。記載48ファイルとmanifestの計49件を照合し、前回runの2137ファイル/4384532669 logical bytesはhash・一覧とも完全一致。新しいinvocationの追加ファイルがないこと、起動前に関連計算processがないことも確認した。

preflight UTC2026-09-22T01:22:52.725775+00:00。空きRAM13703512064/C167815163904/D119512027136 bytes。Windows11 Pro25H2/AMD64/26200.9457/local NTFS、CPython3.14.0/MSC1944/source v3.14.0:ebf955dとexe/DLL hashは前回と一致。Windows Updateはengineeringの実値記録で許容し、旧正式pinは不変。

本流D:/develop/banto-aiは889cfc3/clean、実計算sourceはc01d1c9/clean。既存dirty親policy文書8461 bytes/SHA-256 443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。保護ProgramData roots/principal/SAM参照、UAC/ACL/service/task/VM変更、push/merge/CIなし。

## 起動・監視・途中保存

候補`artifacts/chunks-33-56-continuation-2026-09-22`に起動記録と外部証拠を保存する。controller PID **6872** / 開始UTC **2026-09-22T01:24:22.5430796Z**（JST10:24）。Windowsの非表示background processとして起動し、実argv/runtimeは`request.json`に保持する。PIDだけで判断せず、開始日時とwrapperコマンドも照合する。

前回のwrapperからcontrol番号・開始closed・対象区間だけを適合させ、60秒診断とverified receipt保持を引き継ぐ。新規verifiedのsequence102〜171を区間ごとに外部保存する。controller private、空きRAM/C/D、journal段階を`progress.jsonl`と`latest.json`へ記録する。中間receiptはclosedの代用にしない。

既存heartbeat **banto-24** を今回のFOLLOWUP.mdへ更新して再開した。30分ごとに状態と資源を1回確認し、新規6/12/18区間の節目でこの文書とcurrent-handoffだけを保存する。追加agent、短い間隔の進捗poll、過去成果物の繰返しhash/数値再計算は行わない。PCとアプリを稼働させたまま継続する。

## 予算の判断と完了条件

前回24区間の診断ログでは、既存9区間の確認を含む最初の新規区間の開始が1810.4〜1870.4秒の間だった。fresh inspection60.285秒を差し引いた単純換算は既存1区間194.5〜201.1秒、新規1区間790.9〜793.4秒。今回の既存33区間を含む見積りは25458〜25738秒（約7.1時間）、追加保存約3GiBとなる。最初の約1.8時間は既存区間の再照合が中心になる。

48時間候補の残り活動時間143944.002236秒（約39.98時間）。残り87区間を仮に24/24/24/15で区切る線形試算は全累積42.1〜42.7時間だが、固定起動費、seed/layout差、inventory増加、再試行・遅延は分離しておらず保証ではない。今回許可された実行範囲は区間33〜56のみ。32GiB候補出力上限、空きRAM4GiB/disk20GiBの開始条件と所有producer/audit上限を維持する。全体上限は協調的な区間境界検査で、process treeへの強制上限ではない。

終了後はexit0/yielded/新規24/next57を確認し、準備済み`collect.py`によるIO/hash照合を1回実行する。全所有process終了、各監査、前回2137ファイル不変を確認し、5文書の最終保存と`finalize_evidence.py`を完了してheartbeatを停止する。異常終了でも記録を保全し、成功専用collectorや未閉鎖invocationを再使用せず判断点を報告して停止する。campaign加算0/正式許可false、独立監査は保存score以降のみ。完全runtime inventory/独立S6、全120区間/holdout/性能評価、Phase 2/3全体の完了は追加しない。

## 中間保存: 新規6区間の節目

UTC2026-09-22T05:03:05.021046+00:00（JST14:03）の診断で、新規7区間/42評価（chunk33〜39）のverified receiptを保持し、累計40区間/240評価となった。journal121の最新状態はchunk40/attempt1/running、経過13121.9秒。PID6872の開始日時とwrapperコマンドが起動記録と一致し、同じcontrollerが継続中。stdout/stderr/console-stderrは空で、終了報告はまだない。

空きRAM12813946880/C165461995520/D119512002560 bytes、controller private116826112/peak230563840 bytes。資源に余裕があることを確認し、6区間の節目としてこの文書とcurrent-handoffだけを中間保存する。対象節目・観測値・commitは今回の外部`followup-state.json`に保持する。次の中間保存は新規12区間到達後。中間receiptは未閉鎖control000004の再開pinに使わず、今回全24区間の終了・最終照合は未完了として扱う。

## 中間保存: 新規12区間の節目

UTC2026-09-22T06:36:10.103033+00:00（JST15:36）の診断で、新規13区間/78評価（chunk33〜45）のverified receiptを保持、累計46区間/276評価。journal140の最新状態はchunk46/attempt1/saved_pending_verification、経過18706.9秒。PID6872の開始日時・wrapperコマンドが起動記録に一致し、同じcontrollerが継続中。stdout/stderr/console-stderrは空で、終了報告はまだない。

空きRAM13726928896/C164462354432/D119511977984 bytes、controller private122306560/peak230563840 bytes。資源に余裕があることを確認し、この文書とcurrent-handoffだけを中間保存する。最初の6区間の節目は85c2f2b1ede558dca4a1f5dd7c61039223f62af6で保存済み。各節目のcommit・観測値は今回の外部`followup-state.json`に保持する。次の保存は新規18区間到達後。未閉鎖状態の再使用や追加起動は行わず、今回全24区間の終了・最終照合は未完了として扱う。

## 中間保存: 新規18区間の節目

UTC2026-09-22T07:40:14.675107+00:00（JST16:40）の診断で、新規18区間/108評価（chunk33〜50）のverified receiptを保持、累計51区間/306評価。journal154の最新状態はchunk51/attempt1/running、経過22551.4秒。PID6872の開始日時・wrapperコマンドが起動記録に一致し、同じcontrollerが継続中。stdout/stderr/console-stderrは空で、終了報告はまだない。

空きRAM13204250624/C165579055104/D119511953408 bytes、controller private121913344/peak231682048 bytes。資源に余裕があることを確認し、この文書とcurrent-handoffだけを中間保存する。6/12区間の節目は85c2f2b1ede558dca4a1f5dd7c61039223f62af6/41dd75d2948ef6018ad8a938acba286348ac78ffで保存済み。各節目のcommit・観測値は今回の外部`followup-state.json`に保持する。次は今回の全24区間が終了した後に最終照合・保存を行う。未閉鎖状態の再使用や追加起動は行わず、今回全24区間の終了・最終照合は未完了として扱う。

## 最終結果

同じclean c01d1c9/r1の`continue --max-chunks 24`でchunk33〜56の新規144評価がすべて成功し、累計57区間/342評価となった。27346.369秒（約7時間36分）、累積活動56201.874418秒、journal171/next57/yielded。各監査は`ledger_checks_passed`、controllerと全所有process終了済み。3679 files/7572651569 logical bytesを照合し、開始前2137ファイルはすべて不変。終了後のcollectorは553.670秒のIO/hash照合のみで、数値計算は繰り返していない。

最新closedは **`run/control/000004/closed.json`** / raw SHA-256 **f21ca40084af17fc0d961c529963c984ccd80d2b0cfea7803fab30c1ce7382a6**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。旧000003以前のclosedや中間receiptは再開pinに使わない。

終了UTC **2026-09-22T09:00:09.756724+00:00**（JST2026-09-22 18:00）。control000004はexit0/stop_reason=null、全24区間のfailed/inconclusive/not_startedは0。開始日時・wrapperを照合してきたcontroller PID6872の消失と正常終了報告、inspection/producer/auditの全所有process正常終了を確認した。stdoutに正常閉鎖を記録し、stderr/console-stderrは空、診断threadは終了済み。外部receipt24件を保持する。collector peak private189.7MiB。

producer最大335.5MiB、audit最大188.3MiB、controller peak220.9MiB/終了時83.7MiB。60秒間隔454標本の空きRAM最小11128786944 bytes（約10.36GiB）、診断エラーなし。終了UTC2026-09-22T09:00:09.756724+00:00（JST18:00）、空きRAM13120614400/C165132275712/D119511928832 bytes。OS26200.9457/CPython3.14.0/exe・DLL hashと各workerのruntimeは開始・終了で一致。Windows Updateのengineering実値記録と旧正式pin不変を維持。controller privateは終了時に低下したが、長期リーク不在は未評価。

開始3859efc、中間85c2f2b（新規7区間で6区間の節目）/41dd75d（新規13で12区間の節目）/dfb4107（新規18）を保存した。最終commit・文書・成果物のpinは候補`artifacts/chunks-33-56-continuation-2026-09-22/savepoint-evidence.json`へ記録する。前回manifest10289 bytes/SHA-256 ddbb32983dadb84fbdca50d990f346c02cdaa5bedc8949d016504562e6d48ec8と記載48ファイルを保全。本流889cfc3/clean、実計算c01d1c9/clean、既存dirty親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。実装変更・追加agent・合格済み回帰試験の再実行なし。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。

残り63区間/378評価、48時間候補予算の残り活動時間116598.125582秒（約32.39時間）。次回は完了済み57区間の再照合費用も含めて明示上限を判断する。今回のheartbeat banto-24は最終保存後に停止し、追加invocationは起動しない。 監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory、profile/score導出・bootstrapの独立検算、全dev/smoke/holdout、性能評価、Phase 2/3全体は未完了。
