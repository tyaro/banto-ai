# S4-B2 SACL自動継承状態を明示する新規準備h

2026-09-16 JST。[準備gの診断](results/anomaly-multiseed-v0.3-s4-b2-principal-setup-g-2026-09-16.md)は初期rootの厳密SDDL比較、SACL部分とauto flagsの差で停止した。gは閉鎖済みで再訪しない。g記録はAI/ARの区別やlabel raw bytes一致を返さないので、過去の実SDDLをS:PAIだったと断定しない。
新root C:\ProgramData\BantoAI-S4B2-principal-20260916h、記録artifacts/principal-setup-h-2026-09-16。初期/最終rootとreceiptの要求SDDLをS:P(ML;;NW;;;ME)から **S:PAI(ML;;NW;;;ME)** に限定変更し、作成時にAI状態を明示する。所有者/グループ、protected DACL/SACL、ACE順/権限/非継承、medium/no-write-up labelは全て維持。比較は引き続き全SDDLの厳密一致であり、差の無視、AR許容、P除去、継承ACEの許容はしない。

[SECURITY_DESCRIPTOR_CONTROL](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-control)はSACL auto-inheritedをOSの自動継承処理で設定する状態、SACL protectedを継承ACEによる変更を防ぐ別のbitとして定義する。[SDDL仕様](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-descriptor-string-format)のPとAIを併記する。これは新しいhについて検証する仮説であり、hが一致するかは実行前には未確認。
追加の純粋試験は初期/最終の両descriptorについて、旧表現とのbinary差がcontrolの0x0800だけで、owner/group/DACL/SACL全bytesが一致すること、両protectedとlabel1件を検査する。44＋特権15＋launcher12件、通常load-only、独立レビューとcommit後に新規一回。

[準備gの診断/失敗契約](anomaly-v03-principal-setup-g-design.md)と[準備eの資源・account契約](anomaly-v03-principal-setup-e-design.md)を継続。旧末尾なし/b/c/d/e/f/gの7 rootへ存在確認/再open/列挙/hash/copy/deleteしない。SAMと新規h不存在、source/DLL/hash/直前資源を確認後に新しいguardを一度使用し、失敗時はhも閉鎖。成功exit0・終了・observer解放が揃う場合だけh既知receipt/SAMの読取へ進む。
新たなOS特権付与、P enable/logon、runtime/service/task/VM/profile追加なし。40秒watchdog/private256MiB/working384MiB/空きRAM・C各2GiB、Windows Update engineering緩和/正式pin不変。全許可flags=false、acceptance_status=not_completed。環境準備や正式B2-S4を事前に完了扱いしない。
