# S4-B2 直接Shell起動診断の準備・通常control

2026-09-15、実装savepoint **558b118a378d0819f0776e727e9a78cb125f289a**、[仕様](../anomaly-v03-shell-launch-diagnostic-design.md)。[準備b停止](anomaly-multiseed-v0.3-s4-b2-principal-setup-b-2026-09-15.md)後、元Win32 errorを保存するProcess.Start経路と、15331文字のASCII Command形式を新しい読取専用probeで確認した。

新規3ケースpass（引数同一性、Shell設定、実際のmissing-exe code2保持）。code2確認は非Shell経路で子process/UACなし、Shell/runas自体の実証とは区別する。独立P0〜P3所見0、レビューはread-only、繰り返し進捗確認なし。
このPCのWindows PowerShell Management assembly version3.0.0.0/StartWithShellExecute IL63 bytesを実行せず調べ、Win32Exception catchからInvalidOperationException(string)への置換を確認した。全文ILは保存せず、観測要約をinputへ記録した。番号欠落の理由を準備失敗の原因確定としない。

Verifyの引数SHA256 **21d6c88f3189451971464c90615fa7c7d2a54af9db2fc4c9eb5063d7e822ec44**、15331文字。通常ControlはUTC03:08:52.5534863Z〜03:08:53.0880129Z、PID43368、起動要求103ms/待機400ms/合計532ms、exit41（固定U SID/非admin）。Handle確保・終了・解放成功、一次/解放例外なし。OS設定変更なし。
Control枠は閉鎖。**Runは未実行、run-attemptなし**。直前の準備bでWindows確認画面が表示されたかをユーザーへ質問中で、返答待ち。既存の環境準備許可は継続しており、方式再承認は不要。未回答から表示有無や操作有無を推定しない。

input16278 bytes/SHA256 **90da7ba37f5a9c71652d60e1bb562c4d3812e418fd31f1159b3c3ac8329740f1**。前回83 sourceと11 artifacts不変、新規3 sourceを含む86 sourceをGit/raw照合した。
ignored artifacts/shell-launch-diagnostic-2026-09-15に6 artifacts/論理18438 bytes、checkpoint-evidence.json17947 bytes/SHA256 **57d8b1e198c1ea5ffa90ffc31fea7242e3f858bffeb2b3fa25b04716d2a3fa9c**（checkpoint自身は集計外）。Run結果を含まない途中savepointであり、後で上書きせず別の最終記録を作る。

途中の記録追記＋commit複合操作は自動承認審査でblocked by policy（詳細なし）。副次的な個別review/IL記録の追加を省き、対象4ファイルだけのstage、差分確認、commitへ操作を限定すると成功した。拒否された複合操作は再実行していない。レビュー/IL要約は後続inputへまとめた。
UTC03:09:42 RAM10321457152/C130921562112/D202743402496 bytes。D空き約188.82GiB、build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和/正式pin不変、長期リーク不在の主張なし。
旧root2件のunknownを維持し、再訪なし。観測した今回の通常probeは終了済みで、以前の不明helperまで終了済みと扱わない。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。

次はユーザーの表示状況への回答を確認し、新しいShell診断Runだけをmax1実行する。旧Control/準備の再実行、旧root探索、guard解除を行わない。準備再開用のさらに別rootは未定で、作成処理へ直行しない。全許可flags=false、acceptance_status=not_completed。
