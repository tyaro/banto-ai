# S4-B2 最終DACLのAI状態を明示する準備j

2026-09-16 JST。[準備i](results/anomaly-multiseed-v0.3-s4-b2-principal-setup-i-2026-09-16.md)は最終policyの厳密比較、DACL部分とauto flags差で停止した。新規rootはC:\ProgramData\BantoAI-S4B2-principal-20260916j、公開記録先artifacts/principal-setup-j-2026-09-16。旧末尾なし/b/c/d/e/f/g/h/iの9 rootへ存在確認/再open/列挙/hash/copy/deleteしない。
要求descriptorはpublisher=nullの初期状態をD:P/S:PAIのまま維持し、publisherを含む最終状態だけ **D:PAI/S:PAI** とする。owner/group/ACE順/権限/ラベルは変えず、protected DACL/SACLとmedium/no-write-upを維持。最終DACL設定のAPI・maskは既存のSetSecurityInfo(...0x80000004)のまま。設定後の実SDDLが一致するかはjで確認し、差を無視する条件は加えない。
[SECURITY_DESCRIPTOR_CONTROL](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-control)と[SDDL仕様](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-string-format)のAI状態とprotectedを別のbitとして扱う。iの差68はDACLの文字列/ACL差とauto flags差を併合した記録であり、AI/ARの区別や実ACEの一致を過去に遡って断定しない。
純粋試験は初期descriptorが不変、最終descriptorは旧とのbinary差が0x0400だけであること、owner/group/全ACL bytes・両protectedが不変でARを要求しないことを確認する。50＋特権15＋launcher13=78件、通常load-only、独立レビュー、source/DLL/hash/資源とcommitの保存後に新規guard一度。
[iの既存P固定経路](anomaly-v03-principal-setup-i-design.md)を継続。P name/SID末尾1010/flags0x203/Usersを照会するだけで、作成/所属変更/reset/enable/logon/delete/RNGなし。初期policy/失敗停止/特権復元/終了順、40秒/private256MiB/working384MiB/空きRAM・C各2GiB、Windows Update engineering緩和/正式pin不変を維持。
成功exit0・終了・observer解放が揃った場合だけjの既知receiptとSAMを読取確認する。失敗時はjも閉鎖しSAMのみ確認。全許可flags=false、acceptance_status=not_completed。環境準備/P-U/IPC/全publisher/正式B2-S4を事前に完了扱いしない。
