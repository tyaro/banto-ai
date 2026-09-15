# S4-B2 専用principal環境の準備成功

2026-09-16 JST、実装revision **1f253cc4fa984462a3d0bf7d4e66d23d230eaf56**。[準備j仕様](../anomaly-v03-principal-setup-j-design.md)により、初期D:Pを維持し、最終DACLの要求状態だけD:PAIへ変更した。両protected、owner/group/全ACE bytes、S:PAIのmedium/no-write-upを維持し、全SDDLの厳密比較を通過した。
**専用環境の準備は完了。P/Uの独立起動・干渉試験や正式B2/S4受入は未完了。** BantoS4Publisherは既存の無効accountを維持し、今回のaccount作成/変更/reset/enable/logonはない。

## 検証と管理者実行

50＋特権15＋launcher13の78件pass、独立レビュー指摘0、safety/diff pass。通常load-only PID20772/exit0、command17271文字。DLL26112 bytes/SHA256 **4d6b2fa835176986faa4791a62865144451fd4a6b6823dc95a711a5b9a34be25**。
107 sourceをGit/raw照合（前回103不変/3変更/新規1）、旧i11公開artifacts不変。UTC15:43:24.0015819Z、既存SAM/name/SID/flags/Usersの固定条件と、新規j root attributes0xffffffff/error2を確認。input21338 bytes/hash5fe087c324fa68b2882908c3d3bced0b4d01f7c780a9dbadd466850e4ee92b17。
Run UTC2026-09-15T15:44:08.8914053Z〜15:44:17.7382677Z、**PID3284/exit0**、Handle/終了/observer解放確認、観測/解放例外なし。launch4125/wait4680/total8841ms。既存P専用20 phaseを完了し、初期/最終検査、receipt write/flush、child/root/ancestor/token close、元の特権有効bitへの復元・再照会、watchdog終了を確認した。初期特権bitの実値は記録しておらず、最初から有効だったかは断定しない。

## 成功後の既知receipt・SAM確認

準備済みrootは **C:\ProgramData\BantoAI-S4B2-principal-20260916j**。成功終了を確認してから、既知bootstrap-result.jsonだけを64KiB上限で読み、public artifactへ同じbytesを保存した。1128 bytes/hashf736744e7870f492f6913cba9476327246d0b82babc5a9f198ec6e58224a06d4。schema/state/SID群/無変更flags/厳密policy/root pin/資源を検証した。prepared-preclose receipt単体から正常終了を認定せず、別のexit0証拠を組み合わせている。
root identity部分は **taBg2tdg2iouDAAAAABPAAAAAAAAAAAA**（FILE_ID_INFOの24 bytesをbase64化）。root_pinはこの値＋コロン＋次の実SDDLに一致した。

```text
O:BAG:BAD:PAI(A;;FA;;;SY)(A;;FA;;;BA)(A;;0x1200a9;;;S-1-5-21-2169670816-255940906-2713565042-1001)(A;;0x1200a9;;;S-1-5-21-2169670816-255940906-2713565042-1010)S:PAI(ML;;NW;;;ME)
```

owner/groupはAdministrators、SYSTEM/Administrators full、U/P readonly、DACL/SACL protected。取得範囲はowner/group/DACL/mandatory label（0x17）であり、全audit SACLや将来の不変性を認定するものではない。
終了後UTC15:45:24.5721775Z、SAM/解放各0、BantoS4Publisher/SID **S-1-5-21-2169670816-255940906-2713565042-1010**/flags515=0x203/disabled=true、group照会/解放各0、read=total1/Usersのみ。account/groupの永続不変やP tokenの全権限は未検証。
旧末尾なし/b/c/d/e/f/g/h/iの9 rootは全て閉鎖し、存在確認/再open/列挙/hash/copy/deleteしていない。jは準備済み環境として保存するが、作成guardは消費済みで再実行しない。

## 資源と保存

receipt UTC15:44:15.3372168Z/elapsed148ms、precloseまでの観測peak private63029248 bytes（約60.1MiB）/working73957376 bytes（約70.5MiB）、minimum RAM5974740992/C149730889728 bytes。これはprecloseまでの標本であり、PowerShell起動全体やclose後を含む厳密な最大値ではない。
終了後RAM6247051264/C149730881536/D198225158144 bytes、D約184.61GiB。OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00。Windows Update engineering緩和/正式pin不変、長期リーク不在やPC全体の容量変動原因を主張しない。
success-verification.json953 bytes/hash1d70cd4dd4ab95a2be7a472a4506a51554548920357185ff4d6eb521826a6eb2。最終savepoint-evidence.json **26606 bytes/hash03a60920912a2157ea3183f2645829a2f0211dbc4a42c736c37cd2b11c4b3afe**。自身除外13 artifacts/論理93657 bytes。107 sourceと入力artifact不変、本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全。

次は[principal境界案](../anomaly-v03-principal-boundary-design.md)の残件を具体化する。保護code/runtime、B/P/U process/thread/tokenの初期SD・起動経路、IPCと所有台帳、単回有効化/ログオン/再無効化と全process終了を設計・故障試験する。準備成功からP/U隔離やmarker方式、全期間/frozen契約を認定しない。全許可flags=false、acceptance_status=not_completed。
