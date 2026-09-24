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
