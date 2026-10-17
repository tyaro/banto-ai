# v0.3 既存監査の再利用と残り15区間の再開

2026-09-24 JST。ユーザーの「再開できますか？ ところで既存の照合は必要なのですか？」に対応。直前の失敗保存点はdaf17f2d747f080eba893cd1b9f320ce02e5c3c5。control000008のMemoryError後も105区間/630評価は保存済みであり、残り15区間/90評価（105〜119）だけを再開対象とする。

## 既存照合の役割と今回の変更

前回の監査で合格した結果がそのまま残っているかを確認する必要はある。同一の保存内容・ソース・runtimeで、既存105区間の数値監査を再度約5.2時間かけて実行することは省ける。今回は外部helper `tools/evaluator/anomaly_v03_verified_resume.py` を追加し、成功保存点のファイル一覧とSHA256、失敗control8の6ファイルを結合した外部snapshotに全6775ファイルのbyte数/hashを照合する。欠落・追加・同じサイズの改変・journal/checkpoint/source/runtime不一致は停止する。

全照合の成功証拠を書き終えてから、実際にRun.runが選ぶ新しいControllerの既存105区間の監査cacheだけを初期化する。以降は元の `_revalidate_completed` に戻り、新しい15区間のproducer、独立audit worker、controller側監査、終了確認を変更しない。固定計算source c01d1c978f78bab51391392d56cdcb7aab5afaabや数値algorithmは編集しない。変更は明示的な外部再開policyであり、運用上の変更がないとは扱わない。

単一writerの通常運用が前提。既存snapshotは前回の独立監査済みbytesを参照し、任意の現存ファイルを「合格済み」として採用しない。新しい数値監査を実施したという主張にも使わない。同時書換えへの敵対的な隔離・完全S6の代用ではない。

## 検証結果

変更部分13項目はPASS。実Controllerの再照合メソッドを使い、既存hashがcacheへ入り、新しい区間は監査に進むことを確認した。同一サイズ改変、ファイル欠落/追加、inspection未完了、source/runtime/checkpoint不一致、証拠保存失敗、別Controllerへの誤適用、二重導入を拒否する。最初の試験ではWindowsのlstat/fstatのctime差で2項目が失敗したため、ctimeは同じAPIの前後で比較し、API間はfile identity/size/mtime/link数を比較するよう修正した。修正後13項目が通過。関連する既存45項目（memory diagnostics/budgeted run/campaign launcher）も初回実行で通過した。

実データの読取専用検証では、6775ファイル/13,948,054,577 bytesを**65.357秒**で照合した。1MiB単位で読み、プロセスpeak privateは68,460,544 bytes（約65.3MiB）。前回保存時から全bytes/source/runtimeが一致し、既存105区間のcache初期化を確認。Run.run、producer、数値監査は起動していない。

証拠は `artifacts/chunks-105-119-fast-resume-2026-09-24/`。snapshotは1,468,546 bytes/SHA256 **05152fb2b81570b573fc96932a1576970e85aaab2673fb067c4b6df2e1cd1d37**、helperは10,626 bytes/SHA256 **97990096b9ccea31054209b164c8643fab7b54c2d512d8ce52256efe7fa8063d**。`dry-verification.json`に実測を保持。過去196保持artifactのpinも一致し、元の成功/失敗OUTは変更していない。

## 再開条件

最新closedはcontrol000008、raw SHA256 **02531b247b12b1275a57c8907924f5ac710c90c4d8dfd079f885d0fd2d5c9211**。preparedは **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7**。次は新しいcontrol000009として最大15区間のみ起動する。開始時に同じsnapshotを再照合してからcacheを初期化し、読取専用試験時のcacheを流用しない。

48時間/32GiBと各workerの上限は維持する。失敗時間を含む累積144993.320914秒、残り27806.679086秒（約7.72時間）から続行。新規15区間の見積りは約3.86時間に開始時のbyte照合・inspection等を加えた約4時間。負荷による増減があり完走保証ではない。新規6/12区間で中間保存、15区間終了時は全120区間/720評価、journal360、status=completed/next_unverified_chunk=nullを確認する。

既存メモリ診断helper27346e9を変更せず使い、60秒ごとのsystem commit/空きRAM/C/D/controller private/診断欠落を記録する。30分heartbeatは対象をこの呼出しだけに更新し、1回確認して次回へ任せる。今回のaudit_begin/endは新規105〜119の15件ずつが期待値で、既存105件の再利用は別のresume-verification.jsonへ記録する。

前回のsystem commit急増を起こしたprocessは未特定。今回の正常再開を原因解明やメモリリーク不在の証明にはしない。formal_permission=false/campaign加算0、保存score以降の監査という範囲を維持。完全runtime inventory・profile/score導出/全bootstrapの独立S6・holdout/性能評価・Phase 2/3全体の完了ではない。

## 再開済み

control000009をUTC 2026-09-24T01:48:22.1234253Z（controller PID 25724）に非表示で起動した。既存Banto Pythonがないことを確認し、PID/作成日時/wrapperを照合。外部再開helperの実装保存点はaab4d58e5359497fa8016b8ccb808101dfe9fd40。

実起動内の全6775ファイル照合も成功し、56.252秒で既存105監査を再利用した。初期観測UTC 2026-09-24T01:51:22.837388+00:00、journalの最新状態{"attempt": 1, "chunk_index": 105, "sequence": 316, "status": "running"}、今回確定0区間。まだ15区間の完了は主張しない。診断error/drop=0、無効化なし、stderrは空。

起動前の空きRAM/C/Dは14.51/144.05/382.44GiB、system commit余力15.58GiB。30分heartbeat banto-24を今回OUT/FOLLOWUP.mdへ更新してACTIVE。6/12区間で中間保存、今回15区間の終了・失敗時に保存し停止する。追加invocation/holdoutは起動しない。

## 新規6区間の中間保存（2026-09-24 JST）

観測UTC 2026-09-24T03:24:31.095120+00:00、起動後5768.2秒。区間105〜110の6区間/36評価がverified_complete、累計111区間/666評価。区間111はrunning（journal334）、今回残り9区間。保持receipt318/321/324/327/330/333の原本とコピー、journal終端hash/6件ずつsuccessを照合し、OUT/milestone-06.jsonへ保存した。中間receiptはclosed再開pinではない。数値payloadの再読・再計算なし。

controller PID25724/作成時刻/wrapper一致。既存105再利用の証拠pinも一致。診断error/drop=0、disabled=false。controller private/peakは107708416/232718336 bytes。空きRAM/C/D約13.64/143.20/415.02GiB、system commit合計/上限/余力約29.30/44.42/15.12GiB。pagefile確保量13653180416 bytes。次は新規12区間の節目で保存。今回のcontrol000009を継続し、追加起動はしない。

## 新規12区間の節目・14区間確定まで中間保存（2026-09-24 JST）

観測UTC 2026-09-24T05:29:41.972864+00:00、起動後13279.0秒。今回14/15区間（105〜118、84評価）が確定し、累計119区間/714評価。最終区間119はrunning（journal358）、残り1区間。新規12区間の節目は区間116/receipt351（累計117区間/702評価）。その節目を含め、前回保存後の8区間（111〜118、receipt336〜357）の原本/保持コピー/journal hash/6件ずつsuccessを照合してOUT/milestone-12.jsonへ保存した。前回6区間のpinはmilestone-06.jsonから再利用し、重複照合しない。

controller PID25724/作成時刻/wrapper一致。既存105再利用の証拠pin一致、診断error/drop=0、disabled=false。controller private/peakは125247488/237760512 bytes。空きRAM/C/D約14.12/142.32/402.88GiB、system commit合計/上限/余力約29.07/44.42/15.35GiB。pagefile確保量13653180416 bytes。中間receiptはclosed再開pinではない。数値再計算/追加起動なし。次回、今回15区間の終了を確認して最終照合・保存を行う。

## 最後の区間の時間上限停止と保全（2026-09-24 JST）

control000009は最後の区間119/attempt1のproducerが900秒（15分）の上限に達し、ResourceStop/time_limitでexit2となった。producer実測909.083秒、worker PID17908/exit1/終了確認済み。終了UTC **2026-09-24T05:46:49.451914+00:00**（JST **2026-09-24 14:46:49**）。新規14区間/84評価が確定し、累計**119区間/714評価**。残り**1区間/6評価**。journal359/next119、最終recordはfailed/resource_limit。全120区間の完了ではない。

区間119のstageには6件のevaluation_savedと途中ファイルが残るが、完了markerがなくauditも未開始のため成功件数へ加算しない。直前14成功区間のproducer時間は535.366〜832.661秒だった。controller PID25724の消失、inspectionおよび所有worker全件の終了を確認済み。

診断は238周期標本/273イベント、audit_begin/end各14件（105〜118）、ResourceStop例外1件、観測error/drop=0、無効化なし、診断thread終了済み。今回の停止はMemoryErrorではなくproducerの時間上限。標本UTC **2026-09-24T05:44:43.907054+00:00** でsystem commit 54.90/54.96GiB、割当余力**52.73MiB**を記録した。同時刻のpagefile確保量は23.26GiB。空きRAM最小標本は3.38GiB。controller peak 0.22GiB、失敗producer peak 326.05MiB。システム全体の資源逼迫は観測したが、割当元process・時間超過への因果寄与・実際のCPU/I/O競合は未確定。メモリリークの有無を断定しない。

既存105区間は起動時の全byte/source/runtime照合（56.252秒）で監査を再利用し、新規105〜118の14区間は元の独立監査とcontroller監査を通過した。今回保全では新規14区間のdescriptor/control pin、完了markerが示すpayload raw hash、全6件success、producer/audit workerの終了を照合した。新規runファイル955件/1999730138 bytesをstreaming hashし、前回6775ファイルの一覧/サイズと旧journal315件のhashを確認。旧payload全体の再hashや数値再計算はしていない。全体は7730 files/15947784715 logical bytes。過去196artifact pinsと起動時24immutable artifactsも保持。小さなcontrol/journal/失敗worker記録98ファイルをOUT/failure-controlへ複製してhash照合した。成功用collector/finalizerは実行していない。

最新closedは **run/control/000009/closed.json** / raw SHA256 **362c2ed425d38a6a6ae3436518fa4cafa0cc4d9a017b012f15de4816fa44156d**、status=failed/stop_reason=exception。累積活動**159294.585066秒（44.25時間）**、48時間候補の残り**13505.414934秒（3.75時間）**。失敗時間を含めて保持し、48h/32GiBとworker上限は変更していない。prepared pinはbe582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7。旧control8や中間receiptを最新closedの代わりに使わない。

heartbeat **banto-24はPAUSED**。停止証拠はOUT/failure-evidence.json/diagnostics-summary.json、最終保存点はOUT/failure-savepoint-evidence.jsonへ保持する。中間保存eb1a67e/105960cを保全。

次の判断は、システムの負荷が落ち着いた状態で、残り1区間だけを別の試行として再実行するか。今回の失敗attempt1は未公開stageを含めそのまま保持し、再使用・削除しない。現在の高速再開helperは「完了数×3＝journal件数」を要求するため、今回のfailed末尾2recordを含む359件をそのまま受け入れない。再開する場合は外部pinに基づく失敗末尾の扱いを検証する必要がある。無条件にcacheへ追加したり、上限引上げ・新しいinvocationを自動実施したりしない。

formal_permission=false/campaign加算0、保存score以降の監査という範囲を維持。完全runtime inventory・profile/score導出/全bootstrapの独立S6・全120/holdout/性能評価・研究Phase 2/3全体は未完了。実計算source c01d1c9と本流889cfc3は変更せず、既存dirty親policy文書を保全しcommit除外。OS/pagefile/Python設定変更、追加agent、回帰試験、push/merge/CIなし。
