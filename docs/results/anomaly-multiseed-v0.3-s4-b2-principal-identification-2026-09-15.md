# S4-B2 識別用token修正と管理者起動取消

2026-09-15。実装 **35c46670f560bff054af63ffe0ac7c346404b01a**、[仕様・根拠・次の確認枠](../anomaly-v03-principal-identification-diagnostic-design.md)。AccessCheck専用tokenの複製要求をlevel2から1へ下げた一行の変更で、SID/非昇格/危険権限mask/所有・解放/資源上限は維持。OSの権限設定は追加していない。既存34件＋診断9件＋loader10件pass、独立所見0。
新規公開DLL24576 bytes/SHA256 **05a77ce8bfe3c16d166eabd14c614ce85040f2f0089cdfc673c611ae161d6e6f**、command16754文字/SHA256 **9694e60e2c6fcac316aeaeab5c862176e0d77711d93f7cff18fbd4d24826876c**。

通常ControlはUTC05:09:31.1403070〜05:09:33.7452769、PID18720/exit41、起動97ms/待機2479ms/合計2603ms。Handle取得・終了・解放成功、例外なし。
管理者RunはUTC05:09:45.9749820〜05:11:49.2404897、request-launch段階で123260ms、合計123261ms後にWindows error1223を返した。外側MethodInvocationException/HRESULT -2146233087、内側Win32Exception/HRESULT -2147467259/native1223、chain切詰めなし。PID/Handle/exitは未取得、修正後のPreflight実行・成功は未確認。Windowsがキャンセル扱いで返した事実を記録し、手動取消と時間経過による取消を区別できたとはしない。
通常側の観測sessionは終了。今回helperの開始/終了は不明であり、未知processへ操作しない。準備Entry・作成phase・SAM/root APIのない固定診断で、OS設定変更なし。通常/管理者両guard閉鎖、旧root3件への再訪なし。

98 sourceをGit/raw照合、前回97中94不変/3変更/新仕様1。前回17 artifacts不変。input19693 bytes/hashd31a7712253012bdcb125dd13e6d45e2c1b909ec7d2688b89eb6dfceaa600d7f、input時8 artifacts不変。
artifacts/principal-identification-diagnostic-2026-09-15の最終manifest **21412 bytes/SHA256 55b53f9d0125575392a8752ef939c94133995c3606fce138e869341281fea7ec**。14 artifacts/論理75372 bytes（最終manifest集計外）。
UTC05:09:17 RAM5913649152/C148318298112/D219493740544 bytes→05:13:24 RAM6085988352/C148317212672/D219493744640 bytes。D約204.42GiB。点観測から長期リーク不在は判断しない。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。

新しい確認枠を準備し、ユーザー「今なら操作できます」の回答を受領した。記録先/source/inputを保存してから新規Runを行う。再承認要求ではない。環境準備/P-U/正式B2-S4未完了、全許可flags=false、acceptance_status=not_completed。
