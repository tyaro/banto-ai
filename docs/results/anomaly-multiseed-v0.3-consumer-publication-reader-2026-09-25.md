# consumer公開・終了記録readerの確認（2026-09-25）

[読取API](../anomaly-v03-consumer-publication.md)を追加し、全120区間の公開印・結果目録・終了記録を外部hashへ照合した。実装revision `1b3021f8debbd4edb78b8d75efcf73cd6de88a7c`、OUT `artifacts/consumer-publication-reader-2026-09-25`。最終文書revisionと証跡pinはsavepoint-evidence.json。

## 試験と実記録

新規14試験pass、failure/error/skip0、62.046秒。架空metadataを通常temp directoryへ保存し、追加権限なしで確認した。外部hash、plan、closedのstatus/root/journal、別attemptへのdescriptorすり替え、marker scope/在庫/hash、hardlinkのidentity、manifest変更・多重link、終了未確認/exit code/runtime/資源矛盾、サイズ上限、path traversalを検査。読取を8固定管理ファイルへ制限した状態でも通過し、生成・process起動・再帰payload読取・score auditは呼ばない。旧37試験の再実行は不要なため行わず、旧実装は変更していない。

保存済みadapter（raw 1,581,421bytes、SHA256 a829bde9ae98725d0b6b4fd97288e7b846349e9c306694d248a54a85839c776c）を前保存点へ照合。そのcanonical hashと既知closed raw hashをreaderへ渡した。

最初に区間0/95/96/119の4区間を確認（0.867秒）。dev/smoke境界と最後のattempt2が通過したため、残り116区間を確認（18.140秒）。最初の4区間は再読取りせず、hashで保全した報告を併合。全120区間/720評価の管理参照が一致した。区間119の過去失敗は元adapterに保全したままで、attempt2だけを選択する。

8file/区間、960読取、同一区間の各fileは1回。closedは独立した区間呼出しごとに照合するため合計14,663,483bytes、重複を除く841file/13,518,584bytes。別途読んだ前保存点・adapter・plan等の準備metadataはこの数に含めない。観測、evaluation本文、score、audit report本文の読取・再評価・bootstrap・正式gate/holdout起動は0。

`publication-checks.json` と `saved-publication-check.json` に境界4区間、`all-publication-checks.json` と `all-publication-summary.json` に全120区間の結果と参照pinを保存した。

## 資源と保全

peak44.61MiB、最小空きRAM10.71GiB、commit余裕17.57GiB、C122.85GiB／D270.18GiB。旧実計算checkout c01d1c9、本流clean6f1285d、closedと保存点、開始前のdirty guardは不変。banto-24 PAUSED。OS/runtime設定変更、UAC、principal試験、追加controllerなし。

## 到達範囲

公開metadata・manifest bytes・worker終了監視記録・controller closure記録の認証が完了。全payload/監査本文は未読。controller closedは処理完了記録なので、OSプロセス自体の終了確認とは区別する。`full_payload_bytes_verified`、`controller_process_exit_verified`、trust、analysis/execution/formal/promotion/S6はfalse。

次は、既存の独立監査済み集計入力と認証済み公開metadataのhash対応を固定する。重い観測/scoreを再計算せず、再利用する保存点・導出履歴と今回検査したbytesの範囲を区別する。正式採択・freeze・Phase 2/3全体は未完了。
