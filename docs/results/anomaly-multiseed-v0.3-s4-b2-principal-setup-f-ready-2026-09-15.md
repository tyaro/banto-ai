# S4-B2 新規準備fの通常側準備・画面操作回答待ち

2026-09-15。実装 **d2bdb66a88a51ee7cdc25afc9605c9a11097ae46**、[仕様](../anomaly-v03-principal-setup-f-design.md)。root定数とlauncherの記録先/attempt.rootだけを新しいfへ変更し、初期保護、disabled account、特権の存在確認/有効化/復元、上限、失敗停止を維持した。34＋15件pass/独立所見0。
新公開DLL25088 bytes/SHA256 **3d236d9b2b920a4bbbf0550839bac94abd551f7debee73c02ec531a086d6f1bf**。通常load-only PID33568/exit0、command16727文字。作成Entry/SAM/root APIなし。
**新規Runは未開始、直前の対象SAM/f不存在照会も未実施。** 今回の管理者画面操作の都合への回答を待っている。以前の「今なら操作できます」は以前の確認枠の回答であり、今回の未回答を操作可能と扱わない。方式自体の許可は継続している。

103 sourceをGit/raw照合、前回102中100不変/2変更/新規1、前回10 artifacts不変。artifacts/principal-setup-f-2026-09-15に6 artifacts/論理55047 bytes、**ready-evidence.json 20120 bytes/SHA256 4e77c062459bcd2b9e0d646afd7b0f3492732092fcc2eb09bb8e71d00c07688b**（自身は集計外）。これは実行前savepointで、成功結果や消費済みguardではない。
UTC08:40:41 RAM13034573824/C144674852864/D204764569600 bytes。D約190.70GiB。開始08:26:44のD211023683584からのPC全体の変動原因は未確認。今回の小規模出力の論理bytesと区別し、長期リーク不在も断定しない。
build26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。新runtime/service/task/VM/profileなし、push/merge/CIなし。

再開時は回答を確認後、saved source/DLL/ready-evidenceと旧e証拠の不変、直前の資源と対象SAM/f不存在を確認し、新規inputを別名で保存してRun一度だけ行う。既存ready-evidenceを上書きしない。旧5 root（末尾なし/b/c/d/e）とguardへ再訪・再使用しない。成功時だけfの既知receipt/SAMを照会し、失敗ならfも閉鎖する。
環境準備/P-U/IPC/namespace共通期間/全publisher/frozen/marker/正式B2-S4未完了。全許可flags=false、acceptance_status=not_completed。
