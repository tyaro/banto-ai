# S4-B2 準備DLLの管理者読込み成功

2026-09-15、実装 **64307e50aef7d48902e3a5db76a78d1bec7d377e**、[仕様](../anomaly-v03-principal-loader-diagnostic-design.md)。公開build-01 DLL22528 bytes/SHA2564ea7c99167a71c9ba6e26f2d6d3a74ad16226d8209dc3535d19660696440a88aの有界展開/hash/Assembly.Loadだけを通常/管理者で各max1確認した。準備Entry.Runは呼んでいない。

| 観測 | 通常Control | 管理者Run |
| --- | --- | --- |
| 開始UTC | 03:31:32.1184103Z | 03:31:47.0172339Z |
| PID | 4592 | 33600 |
| 起動要求ms | 128 | 3221 |
| 終了待機ms | 2817 | 3686 |
| 合計ms | 2980 | 6951 |
| 終了code | 41（固定U SID/非admin） | 40（固定U SID/admin） |

両方Handle確保・終了・解放成功、一次/解放例外なし。同一15714文字/引数SHA256 **98a008b5bc78ce312b6d13ffb7df152abdb7666bb41b03e649211dc053e5cea7**。DLL pathへB側から再アクセスせず、検証済みinline bytesだけを読み込んだ。OS設定変更・account/root操作・旧rootへの再訪なし。両診断guardは閉鎖した。
この公開buildの管理者側load経路が動作した。以前の準備Entryの実行成功や失敗原因、policy一般、権限隔離は未証明。C#Entry内watchdogをこの診断に適用したとはしない。

8確認pass/独立P0〜P3所見0/repository safety・staged diff-check pass。前回86 source/11 artifacts不変、新規3 sourceを含む89 sourceをGit/raw照合した。input16691 bytes/SHA256 **1ff848cc26e0dd2676687d74b6f7d683fa22a10f3209894858518ff89f04a185**。
artifacts/principal-loader-diagnostic-2026-09-15へ9 artifacts/論理20661 bytes、最終manifest19096 bytes/SHA256 **e0698abf81077fcca1828c00534bbb6d0f1814102bbbc41b0109f539465fe2bf**（manifest自身は集計外）。
UTC03:30:20 RAM9329078272/C129879052288/D202743111680 bytes→03:33:02 RAM8738693120/C129508577280/D202743091200 bytes。D約188.82GiB、長期リーク不在の主張なし。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。
本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。新runtime/service/task/VMなし。

次は実機で確認した直接Process.Startを準備launcherへ反映し、旧rootを避けた新規root/記録場所を仕様へ固定する。確認・レビュー・savepoint後の承認済み準備だけに進む。account/root作成はこの診断に含めない。全許可flags=false、acceptance_status=not_completed。
