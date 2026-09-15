# S4-B2 既存SeSecurityPrivilegeの確認・復元成功

2026-09-15。実装 **ec94a5920f08a824cbf35bb1433f61b0e9b68c30**、[仕様と一次資料](../anomaly-v03-principal-security-privilege-design.md)。B process tokenの既存SeSecurityPrivilege一件だけを扱い、開始時の有効ビットを保存し、必要時にenable、終了前に元の有効ビットへ復元・再照会する。TRUE+1300も失敗とし、新たなOS特権付与・他の特権変更はない。
34件＋Preflight9件＋特権15件＋loader10件の計68件pass、独立所見0。公開DLL25600 bytes/SHA256 **cc7a3d42b26ea79015955cb76047d90ced4bd7dc109e74b1bec5898548b6ac1d**。同じcommand17566文字/SHA256 **82e9b02eee0c24ced40b6c087e2c9506dba9337ca01e76af23df39dab0bb26a3**で通常/管理者を確認。

| 実行 | UTC開始〜終了 | PID | exit | 起動/待機/合計ms |
| --- | --- | ---: | ---: | --- |
| Control | 08:26:57.2984421〜08:27:06.1569883 | 9756 | 41 | 5000/2599/8855 |
| Run | 08:27:17.4000397〜08:27:25.3555877 | 33600 | 0 | 4977/2916/7950 |

両processのHandle取得・終了・observer解放成功、例外なし。Runの固定5 phaseとexit0から、特権存在、有効の再確認、元の有効ビットへの復元再確認、token3個のclose/watchdog終了の完了を確認した。開始時ビットの値は終了記録へ出していないため、元から有効だったか今回enableしたかを断定しない。前回dの特権状態も遡及確定しない。
今回の変更はprocess内tokenの一時状態だけ。準備Entry/作成phase/SAM/root/祖先handle/logonは呼んでいない。通常/管理者両guard閉鎖、旧4 rootへの再訪なし。
101 sourceをGit/raw照合、前回99中96不変/3変更/新規2。前回9 artifacts不変。input20660 bytes/hash7f478085abb6b7063d720aa14e553b11e931c4ded2001aed3792e6a40c7b4782、input時10 artifacts不変。
artifacts/principal-security-privilege-diagnostic-2026-09-15の最終manifest **21910 bytes/SHA256 4ebea15097d1a5d1e5a53461875412bc99e41f7ff62aa6e8a337a15eb7bd10ef**。16 artifacts/論理87900 bytes（最終manifest集計外）。
UTC08:26:44 RAM12702773248/C144744599552/D211023683584 bytes→08:28:23 RAM10675208192/C144742756352/D211054731264 bytes。build26200.9445/boot **2026-09-15T14:30:24.5000000+09:00**。前回記録の9/9起動から変更あり、再起動原因は未確認。Windows Update engineering緩和/正式pin不変を継続し、長期リーク不在や他の資源変動原因は断定しない。
本流889cfc3/clean不変、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全、レビュー進捗ポーリングなし。次は[新規準備e](../anomaly-v03-principal-setup-e-design.md)。環境準備/P-U/正式B2-S4未完了、全許可flags=false、acceptance_status=not_completed。
