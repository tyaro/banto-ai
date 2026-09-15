# S4-B2 準備hの初期検査通過・最終検査停止

2026-09-16 JST。revision aa0bc5e16010e8fd3a61239359ed1f67f41df5fa、[仕様](../anomaly-v03-principal-setup-h-design.md)。SACLの要求状態をS:PAIへ限定変更し、全SDDLの厳密一致を維持した。旧とのbinary差がcontrol0x0800だけである追加試験を含め44＋15＋launcher12件pass、独立レビュー指摘0、safety/diff pass。通常load-only PID11952/exit0、command17859文字。
DLL26624 bytes/hash4b04ed4b32a6e1713cc806804c8532fca22a7e9f32685bf087b4c345b7e93c0f。105 sourceをGit/raw照合、前回101不変/3変更/新規1、旧g14公開artifacts不変。UTC15:25:14.4459618ZのSAM2221/free0・新規h root error2を確認した。input20709 bytes/hash1784e62199d216d66551e0fa7240a44cc2a055f4997507d41b5a31705685bc19。

Run UTC2026-09-15T15:25:59.3588285Z〜15:26:07.5741839Z、PID26248/Handle/終了確認、exit786431=phase11/detail65535。launch3842/wait4330/total8215ms、観測/解放例外なし、process object解放済み。
コード順序上、初期root identityと厳密policy検査、disabled account作成・検査、Users所属追加・検査、root最終DACL設定を通過した。その後のphase11で停止。phase11はBudget/祖先確認/root identity/policy/account/group再検査を含むため、最終DACLの不一致まで確定しない。gの過去の実SDDLもh成功条件から逆算しない。
失敗後のroot/receiptにはアクセスせず、hも現在状態unknownとして閉鎖。旧末尾なし/b/c/d/e/f/g/hの8 rootへ存在確認/再open/列挙/hash/copy/deleteしない。receipt未作成の推論はphase順序によるもので、直接探索した証拠ではない。正常closeや特権復元まで完了したとは扱わない。

## 終了後のSAM読取

UTC15:28:37.4696747Z、NetUserGetInfo/NetApiBufferFree各0。BantoS4PublisherのSIDは **S-1-5-21-2169670816-255940906-2713565042-1010**、flags515=0x203、disabled=true。NetUserGetLocalGroups/解放各0、read=total=1、Usersのみ。Pのenable/reset/logonは実行していない。将来tokenの全権限やuser rightsは未検証。
専用accountは存在するため、今後は従来の「同名account不存在→作成」を再実行できない。accountを削除・再作成して帳尻を合わせない。

## 保存と再開

最終savepoint-evidence.json23372 bytes/hash0540df3b7945f65f7e6a641af7c0f96bb79f4694d7f31a13804df242b654fef4、11 artifacts/論理86253 bytes（自身除外）。入力以後の105 sourceと保存artifactの不変を確認済み。
終了後RAM4387188736/C149664280576/D198225702912 bytes、D約184.61GiB。今回の公開出力は小規模で、PC全体の変動原因や長期リーク有無は断定しない。OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。
次は新規root用の準備経路を設計し、既存Pをname/SID/disabled/Usersで固定して照会する。accountを変更するAPIを呼ばず、新規rootへのP readonly ACEだけを構成する案が対象。phase11のBudget/祖先/root/policy/account/groupを固定診断で区別する。DACL auto flagsの差は現時点で仮説であり、保護条件や厳密比較を緩めない。設計・故障試験・独立レビューとsavepointが揃うまで次の管理者作成は行わない。現launcher/guardとh rootの再使用不可。
環境準備/P-U/IPC/namespace共通期間/全publisher/正式B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。
