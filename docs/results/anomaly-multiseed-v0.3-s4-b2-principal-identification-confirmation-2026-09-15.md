# S4-B2 修正後の管理者Preflight成功

2026-09-15。ユーザー「今なら操作できます」の回答後、新規確認枠を57904679ef4b11c401fa176f04012f6c513a8e52で保存して実行した。[仕様](../anomaly-v03-principal-identification-diagnostic-design.md)。code変更は記録先一行のみで、前回の公開DLL24576 bytes/SHA256 **05a77ce8bfe3c16d166eabd14c614ce85040f2f0089cdfc673c611ae161d6e6f**とcommand16754文字/SHA256 **9694e60e2c6fcac316aeaeab5c862176e0d77711d93f7cff18fbd4d24826876c**を再照合した。同じcommandの通常Control（PID18720/exit41）は既存結果を参照し、再実行していない。対象ロジック不変の34/9/10件も再実行せず、差分独立所見0。

UTC **05:16:32.0030613Z〜05:16:40.5498031Z**、PID **43308**、**exit0**。起動4715ms、待機3754ms、合計8541ms。Handle取得・終了観測・observer解放成功、一次/解放例外なし。
固定5 phaseの順序とexit0から、修正後Preflight・3 token close・StopWatchdogのSet/Join完了を確認した。これはroot/account作成phase・祖先AccessCheck・P/U隔離を完了した意味ではない。固定診断Entryのみで準備Entry・SAM/root・OS設定操作なし。今回Run guardを閉鎖し、旧3 rootにも再訪なし。
前回のerror1346発生APIは個別には記録していないが、DuplicateToken要求level2→1を含む修正後の全Preflightが成功した。旧1223や以前の原因不明の起動障害をこの成功から遡及確定しない。

98 sourceをGit/raw照合、前回96不変/2変更、前回14 artifacts不変。input19529 bytes/hash6ae5933ff97b1ebd0bd408b515d0d3a60a7653e583327d62b55dbc9e91e44f1b、input時2 artifacts不変。
artifacts/principal-identification-confirmation-2026-09-15最終manifest **18985 bytes/SHA256 92de13846a4f7208994ee1a2b9606f84333a3bdca3f6a2497d92d8e29be21d76**、6 artifacts/論理22240 bytes（manifest集計外）。
UTC05:17:28 RAM5770031104/C148558110720/D218699362304 bytes。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。空き変動原因や長期リーク不在は断定しない。本流889cfc3/clean不変、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。
次は新規[準備d](../anomaly-v03-principal-setup-d-design.md)。専用環境の既存許可は継続。環境準備/P-U/正式B2-S4未完了、全許可flags=false、acceptance_status=not_completed。
