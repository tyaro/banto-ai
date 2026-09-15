# S4-B2 既存無効P維持・最終DACL比較停止

2026-09-16 JST、revision092fb4b7b83e2467b2f26b4258a30ecd94c8b682。[仕様](../anomaly-v03-principal-setup-i-design.md)のExistingEntry/20 phaseを実装し、account作成/所属変更/RNG実装とimportを削除した。phase11の固定診断を追加。49＋15＋launcher13=77件pass、独立指摘0、safety/diff pass。通常load-only PID33552/exit0/command17203文字。
DLL26112 bytes/hash753a29e069cc6310b7f81d843786297be5fcba99f0b3711102cab4f804328c02。106 source（前回101不変/4変更/新規1）をGit/raw照合、旧h11公開artifacts不変。UTC15:38:55.2832028ZのSAM/name/SID末尾1010/flags515/Users各確認成功、新規i root error2。input21222 bytes/hashc53ba659086415037af8ce32ad928c78889535ec6f3bccac03a12b2ae9a63e5c。

Run UTC2026-09-15T15:39:48.0588805Z〜15:39:57.5490309Z、PID31244/Handle/終了確認、exit537602628。launch5218/wait4229/total9484ms、観測/解放例外なし、process object解放済み。
phase11/kind1/step10 exact-policy-comparison、差68=4(DACL部分)+64(DACL auto flags)。差分類完了後の厳密比較で停止。初期検査/phase7/9のaccount/group再検査/最終DACL設定/phase11の祖先・root identityを通過した。owner/group/SACLと保護bitの差は比較範囲内で検出されなかった。DACL部分は文字列とraw ACL差を併合しているため、AI/ARの区別やACEそのものの一致は未確定。hの過去原因にも遡及しない。
既存Pを変更するphase6/8は呼ばず、変更APIもDLLに含めていない。終了後UTC15:40:51.1917349Z、SAM/解放各0、name/SID末尾1010/flags515/disabled=true、group照会/解放各0、read=total1/Usersだけを確認。iのroot/receiptへ再訪せず、現在状態unknownとして閉鎖。閉鎖は旧末尾なし/b/c/d/e/f/g/h/iの9 root。

最終savepoint-evidence.json24200 bytes/hash3bde24e28de4a1c0076c0ebf0e5826577179fe3217ac4864f4f82ad3a47b2524、11 artifacts/論理90815 bytes（自身除外）。終了後RAM6239539200/C149732270080/D198225215488 bytes、D約184.61GiB。PC全体の変動原因や長期リーク不在を主張しない。
OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。
次は[最終DACLのAI状態を明示する新規j](../anomaly-v03-principal-setup-j-design.md)で厳密一致を検証する。全許可flags=false、acceptance_status=not_completed。環境準備/P-U/全publisher/正式B2-S4未完了。
