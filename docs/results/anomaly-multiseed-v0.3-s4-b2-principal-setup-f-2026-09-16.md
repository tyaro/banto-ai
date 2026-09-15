# S4-B2 準備fの初期検査停止

2026-09-16 JST、実行revision c8c4a367e94b29bb5dbde8da254f3ced532aca4e。ユーザーの「次に進めてください」で保存済みfを再開。103 source、ready6 artifacts、旧e10公開artifacts、既存結果書、本流cleanの不変を確認した。
UTC2026-09-15T15:09:11.5218936Z、SAM2221/free0、新規fのattributes0xffffffff/error2で不存在。RAM5267570688/C146161594368/D199940796416 bytes。input-manifest.json20213 bytes/SHA256 35a526d12fe57dd6a52f941314402e974fdb13990d36c8d4d1d739cbc89ff485。ready記録は上書きしていない。

Run UTC15:09:38.8557043Z〜15:09:48.2338376Z、PID12448/Handle取得/終了確認、exit393215 = phase5/detail65535。launch4227/wait3126/total9371ms、観測例外と解放例外なし、process object解放済み。release_failed=falseは失敗helperの特権復元や正常teardown完了を示さない。
コード順序上はphase4のroot作成から戻った後、phase5で停止しaccount作成へ進まない。ただしphase5は冒頭のBudget/祖先検査も含み、65535は非Win32例外と範囲外native codeをまとめるため、具体的停止条件は未確認。rootの実SDDL不一致や原因を確定しない。
UTC15:11:03.1958922Z、終了後SAM2221/free0でaccount不存在。**fへ再訪せず、現在状態unknownとして閉鎖**。旧末尾なし/b/c/d/e/fの6 rootは存在確認/再open/列挙/hash/copy/deleteしない。

最終savepoint-evidence.json22508 bytes/SHA256 541dfa7c139626693e011668f2ea32f52a1a73f83c687815c952c1866abd0553。自身を除く12 artifacts/論理97805 bytes。保存済みDLL25088 bytes/hash3d236d9b2b920a4bbbf0550839bac94abd551f7debee73c02ec531a086d6f1bf、source不変。
終了後RAM3706265600/C145987731456/D199164497920 bytes、D約185.49GiB。PC全体の変動原因と長期リーク有無は未確認。build26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全。独立レビューで確定欠陥0、停止条件を固定診断で識別する[新規g](../anomaly-v03-principal-setup-g-design.md)へ進む。全許可flags=false、acceptance_status=not_completed。環境準備/全publisher/正式B2-S4は未完了。
