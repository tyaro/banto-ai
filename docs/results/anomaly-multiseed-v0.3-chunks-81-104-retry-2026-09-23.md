# v0.3 区間81〜104の診断付き再開

2026-09-23 JST起動、2026-09-24 JST中間保存。ユーザーの「再開しましょう」に従い、失敗したcontrol000006のclosed状態から、**control000007・最大24新規区間（81〜104）**として起動した。起動時の完了済みは81区間/486評価。今回の24区間/144評価がすべて正常終了し、最終照合済み。累計105区間/630評価となった。

## 起動と保全

実計算sourceはclean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、出力 `artifacts/v03-runs/r1`。前回のMemoryErrorによる停止記録は変更しない。開始pinは `run/control/000006/closed.json` / raw SHA256 **18af12a119e3acc0600594d8eaf6263607f5f7c85d68ff3acbda31931d4b9e4c**、prepared hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7**。旧000005へ戻さず、失敗時間を含む累積活動97603.864249秒を引き継ぐ。

起動UTC **2026-09-23T11:06:21.3962444Z**（JST20:06）、controller PID **40372**、非表示background process。起動前に既存のBanto Python processがないことを確認した。今回のwrapper/証拠は候補 `artifacts/chunks-81-104-retry-2026-09-23/` に分離し、前回folderを再使用しない。

既存runの**5227ファイル**（成功済み5221＋失敗control6）を1回hash照合し、旧成功・失敗・原因調査・診断検証の証拠94ファイルも保持pinと一致した。baseline.jsonとpreserved-artifacts.jsonに保持する。準備中のwrapper文字列置換が一致件数のassertで停止したため、置換指定を修正し、保存済みのhash照合結果と再確認した一覧/サイズ・closed hashを用いて準備だけを完了した。この時点ではcontrollerは起動されておらず、数値計算を繰り返していない。経緯はpreflight.jsonにも記録した。

## 診断と資源

外部helperは検証保存点 **27346e985924cdcfde829faca83751824fd11ab1** のコピーを今回OUTに保存し、SHA256 **4c44f9de74f5e3207efce471442be55b4ebb7f650968578fd1887602b7531c72** を起動時に照合する。固定sourceのファイルは変更しない。一時的な観測wrapperで再照合中chunk、例外のfile/function/line、Windowsのcommit/pagefileを記録し、元の引数・結果・例外・所有process終了処理を保持する。

新設helperの12件/既存launcher16件・実機の短い確認は前保存点で合格済み。今回のwrapper/collector/finalizerは構文確認し、変更箇所を確認した。長時間運転での診断欠落や実際のメモリ枯渇への耐性は今回の観測で確認する。原因未確定のため、単に再起動したことをMemoryError解消の証明と扱わない。

preflight UTC11:05の空きRAM15104352256/C155433873408/D51483267072 bytes（約14.07/144.76/47.95GiB）。system commit31150252032 / limit47693520896 bytes、余力16543268864 bytes（約15.41GiB）。起動直前にもcommit余力4GiB以上、既存の空きRAM4GiB/disk20GiB条件を確認する。Windows26200.9457/CPython3.14.0・exe/DLL hashは以前と一致。pagefile/OS/Python設定は変更していない。

wrapperは既存60秒threadでRAM/C/D、controller private/peak、system memory、監査中の区間、診断エラー/欠落を記録する。verified receiptは新規区間ごとに外部保存。heartbeat **banto-24** を今回のFOLLOWUPへ更新し、30分間隔で再開した。各回1回の確認に留め、新規6/12/18区間で中間保存する。追加agent・短時間pollは行わない。

初期確認UTC11:09:21（JST20:09、180.2秒）では既存chunk0の再照合中、journal243/新規receipt0。空きRAM15331557376/C155435704320/D51483267072 bytes、commit余力16639852544 bytes、controller private76189696/peak196096000 bytes。新しい診断のエラー/欠落0、stderr空、PID・wrapper・作成日時を照合済み。PowerShellによるJSON日時の暗黙変換が開始時刻の比較を誤らせたため、実値をtimezone付きで比較して一致を確認し、FOLLOWUPへ解析上の注意を残した。controllerを再起動していない。

## 中間保存: 新規6区間

UTC **2026-09-23T16:48:08.366742+00:00**（JST2026-09-24 01:48）、起動後20506.3秒の観測で、区間81〜86の**6区間/36評価**が確定した。累計87区間/522評価。journal262、区間87はrunning、保持receiptは6件。既存81区間の再照合を終え、active_auditはnull。PID40372の作成日時・wrapperも一致した。

空きRAM14446272512/C154833727488/D441718124544 bytes（約13.45/144.20/411.38GiB）。system commit31256702976 / limit47691943936 bytes、余力16435240960 bytes（約15.31GiB）。controller private132116480/peak233762816 bytes。診断ログ332662 bytes、観測エラー0/欠落0/無効化なし、stdout/stderr/console-stderrは空。

観測値と6件の保持receiptのhash・原本一致をOUT/milestone-06.jsonに保存した。今回の結果文書とcurrent-handoffだけをcommitし、commitをfollowup-state.jsonへ記録する。数値再計算・controller再起動は行わず、処理を継続する。これは中間保存であり、closed再開pinや全24区間の最終照合として扱わない。

## 中間保存: 新規12区間

UTC **2026-09-23T18:22:20.220959+00:00**（JST2026-09-24 03:22）、起動後26158.0秒の観測で、区間81〜92の**12区間/72評価**が確定した。累計93区間/558評価。journal280、区間93はrunning、保持receiptは12件。既存区間の再照合は終了しており、active_auditはnull。PID40372の作成日時・wrapperも一致した。

空きRAM14104588288/C154597003264/D441718099968 bytes（約13.14/143.98/411.38GiB）。system commit31135866880 / limit47691943936 bytes、余力16556077056 bytes（約15.42GiB）。controller private131391488/peak233762816 bytes。診断ログ396153 bytes、観測エラー0/欠落0/無効化なし、stdout/stderr/console-stderrは空。

前の6区間保存点0c98a7dとmilestone-06.jsonのpinを保持し、今回増えた6件の保持receiptだけを原本とhash照合した。先の6件は保存済みpinを再利用し、観測値と計12件のpinをOUT/milestone-12.jsonへ保存した。今回の結果文書とcurrent-handoffだけをcommitし、commitをfollowup-state.jsonへ記録する。数値再計算・controller再起動は行わず、次の保存は新規18区間。中間保存をclosed再開pinや最終照合として扱わない。

## 中間保存: 新規18区間

UTC **2026-09-23T19:57:32.353575+00:00**（JST2026-09-24 04:57）、起動後31870.1秒の観測で、区間81〜98の**18区間/108評価**が確定した。累計99区間/594評価。journal299、区間99はsaved_pending_verification、保持receiptは18件。既存区間の再照合は終了しており、active_auditはnull。PID40372の作成日時・wrapperも一致した。

空きRAM14217084928/C153837621248/D441718063104 bytes（約13.24/143.27/411.38GiB）。system commit31022981120 / limit47691886592 bytes、余力16668905472 bytes（約15.52GiB）。controller private133799936/peak233762816 bytes。診断ログ460207 bytes、観測エラー0/欠落0/無効化なし、stdout/stderr/console-stderrは空。

前の12区間保存点28ca9f7とmilestone-12.jsonのpinを保持し、今回増えた6件の保持receiptだけを原本とhash照合した。先の12件は保存済みpinを再利用し、観測値と計18件のpinをOUT/milestone-18.jsonへ保存した。今回の結果文書とcurrent-handoffだけをcommitし、commitをfollowup-state.jsonへ記録する。数値再計算・controller再起動は行わず、残り6区間を継続する。中間保存をclosed再開pinや最終照合として扱わず、終了後に今回24区間の照合と最終保存を行う。

## 範囲と終了時

上限は今回24新規区間/144評価だけ。既存81区間の再照合を含め約9.4〜9.5時間、追加約3GiBの見込み。失敗分を加味した残39区間の仮の総活動試算は約44.76〜44.84時間で48時間候補内だが、速度差・新たな再試行・診断費用を保証しない。現在残り候補活動は75196.135751秒（約20.89時間）。32GiB候補出力上限、controller private2GiB、既存producer/audit上限を維持する。資源検査は境界で協調的に行われ、既存区間再照合中の強制上限ではない。

成功時は最新closed000007、journal315/next105、累計105区間/630評価、残15区間/90評価。終了確認後に今回OUTのcollect.pyでIO/hash照合を1回行い、5文書（長い引継書§144を含む）とfinalize_evidence.pyで最終保存してheartbeatを停止する。失敗・途中停止時も記録を保全し、成功用collectorを通さず判断点を報告してheartbeatを停止する。今回以外の追加invocationは自動起動しない。

formal_permission=false/campaign加算0、独立監査は保存score以降のみ。完全runtime inventory/独立S6、全120/holdout/性能評価、Phase 2/3全体は未完了。本流889cfc3/clean、実計算c01d1c9/clean、既存dirty親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。保護root/principal/SAM参照、UAC/ACL/service/task/VM変更、push/merge/CIなし。

## 最終結果（2026-09-24 JST）

診断付きcontrol000007で区間81〜104の24区間/144評価がすべて成功し、累計105区間/630評価となった。終了UTC **2026-09-23T21:17:02.345893+00:00**（JST2026-09-24 06:17）、exit0/yielded/stop_reason=null、journal315/next105。controller PID40372の消失と全所有workerの終了を確認した。今回36639.971秒（約10時間11分）、累積活動134242.935420秒（前回失敗分を含む）。

保存済み6769 files/13947570419 logical bytesを照合し、開始前5227ファイルはすべて不変。各区間の監査はledger_checks_passed。終了後のcollectorは574.907秒のIO/hash照合のみで、数値計算を繰り返していない。latest.jsonは最後の60秒標本で23件のままだが、最終run-report/stdout/closed/24件の保持receiptとjournal315で全24件の完了を照合した。

最新closedは **`run/control/000007/closed.json`** / raw SHA-256 **04f198137bbcace5176734e594e5cf3fb9a19c422a7186c002b50a78ab52035c**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。旧control000006は失敗履歴として保全し、古いclosedや中間receiptを次回の再開pinに使わない。

診断は608標本/824イベント、audit_begin/end各105件（既存81＋新規24）の順序が一致。観測エラー0/欠落0/無効化なし、例外イベントなし、診断thread終了済み。controller peak235261952 bytes（約224.4MiB）、終了時private95719424 bytes（約91.3MiB）。producer最大333.0MiB、audit最大187.3MiB。空きRAM標本最小10996932608 bytes（約10.24GiB）、commit余力標本最小10455838720 bytes（約9.74GiB）。今回MemoryErrorは再発しなかったが、前回の原因解明や長期リーク不在の証明にはしない。

終了時空きRAM14128013312/C153025306624/D441718030336 bytes。最後のrun_end診断はcommit30933463040/limit47691886592/余力16758423552 bytes。Windows26200.9457/CPython3.14.0・exe/DLL hashは開始/終了・各workerで一致。Windows Updateはengineering実値を記録し旧正式pinを維持した。OS/pagefile/Python設定変更なし。

起動9340199、中間0c98a7d/28ca9f7/1bcbcbeを保持。今回OUTのevidence.json、diagnostics-summary.json、controller-exit-check.json、24件のreceiptと最終savepoint-evidence.jsonへ保存する。旧成功/失敗/原因調査/診断検証の94保持pin、既存dirty親policy文書と本流889cfc3/cleanを保全する。今回5文書だけを更新し、追加agent・広い回帰試験・push/merge/CI・OS/権限設定変更なし。

全120区間の残りは15区間/90評価。48時間候補の残り活動時間は38557.064580秒（約10.71時間）。次回は完了済み105区間の再照合費用も含め、最新closedからの明示上限を判断する。今回のheartbeat banto-24は最終保存後に停止し、追加invocationは起動しない。

実計算source c01d1c9は不変、外部診断helper27346e9を使用。監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory、profile/score導出・bootstrapの独立検算、全120/holdout/性能評価、Phase 2/3全体は未完了。
