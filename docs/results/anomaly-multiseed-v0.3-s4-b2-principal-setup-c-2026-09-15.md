# S4-B2 新規準備cの事前確認停止

2026-09-15、実装 **9fec67862b1629193b47bac2f1bcfbcebaa0dfd0**、[仕様](../anomaly-v03-principal-setup-c-design.md)。管理者load-only成功を保存し、直接Process.Startによる新規準備cへ進めた。標準account/保護root準備へのユーザー許可は継続している。
rootはC:\ProgramData\BantoAI-S4B2-principal-20260915c、accountはBantoS4Publisher。UTC03:36:13の事前確認でSAM2221/root attributes0xffffffff・error2。C#はroot名だけ変更、新build-01 DLL SHA48eb8f4dfbaa09a38fb4642af23f49412534da150b4ef9ca6eb41725a91893bf。34件pass、通常load-only PID25000/exit0、15331文字。独立所見0/repository safety・diff pass。

UTC03:37:25.6325778Z〜03:37:54.4438124Z、PID26584、起動要求25947ms/待機2814ms/全体28808ms、exit65560=phase1 Preflight/native24。Handle・終了・解放確認、観測/解放例外なし。今回はhelper開始/終了を確認できたが、準備は成功していない。
固定codeのphase順によれば祖先保持・root/account作成へ進む前に停止した。以前の末尾なし/bの開始不明とは区別する。UTC03:39:29のSAM読取で2221/解放0、account不存在を確認。c rootは再確認せず、旧root2件と同様に閉鎖対象へ再訪しない。作成前停止の推論と終了後のfilesystem再検証を混同しない。今回guardは閉鎖し再実行なし。

input17706 bytes/SHA256 **501fdf00a42207fa6debf4b22ed223b5d26f4cb71ecee69d03d031b4f85f5b5d**、90 sourceをGit/raw照合。前回89 sourceのうち87不変、2変更/1追加。前回9 artifacts不変。
artifacts/principal-setup-c-2026-09-15へ9 artifacts/論理60750 bytes、最終manifest20120 bytes/SHA256 **c6be745af63eb0bc79e5d48170b3fd40f38f8e1d7727e1c56fb438e70a3ead7b**（manifest自身は集計外）。
RAM8122433536/C124418535424/D202743046144 bytes→RAM8225210368/C127443746816/D202743001088 bytes。D約188.82GiB、Cの全体空きは工程中にも変動しており原因をこの小容量artifactへ帰属しない。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。長期リーク不在の主張なし。
本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。新runtime/service/task/VMなし。

次は[自process token情報の長さ比較](../anomaly-v03-token-length-diagnostic-design.md)。管理者起動問題とpreflightのAPI失敗を分け、root作成を重ねて調査しない。環境準備/P-U/IPC/全期間/全publisher/frozen/marker/正式B2-S4は未完了、全許可flags=false。
