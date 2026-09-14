# S4-B2 file権限固定と保持世代の接続

2026-09-14、基準c73a602。tests/fixturesのengineering部品。
[短命reader世代](anomaly-v03-reader-reacquisition-design.md)の親borrow/全終了を再利用し、
DACL変更と同一handleの同期continuationを追加する。正式publisherの入口ではない。

## 取得・変更・寿命

SealedFilesはpayloadとmarker-pending.jsonの計2〜8 files、既存root直下の固定相対名に限定する。
元writerの確定close、元pin/raw hash/descriptorとjournalのmarker hash対応を取得前に要求する。
旧ownerのclosed slotsは履歴のままで、新世代のTrackedOpenだけがraw closeを担当する。

| 対象 | 取得する実権限 | 共有・作成条件 |
| --- | --- | --- |
| 通常file | READ_DATA / READ_ATTRIBUTES / READ_CONTROL / SYNCHRONIZE / WRITE_DAC = 0x160081 | share READ / OPEN_EXISTING / OPEN_REPARSE_POINT / 非継承 |
| marker-pending.json | 上記＋DELETE = 0x170081 | 同上。DELETEはDACL固定前に取得する |

書込み内容・追記・属性変更の権限を取得しない。全対象の取得・実権限・元ID/bytes/private SDを検査してから、
各対象を再検査し、保持した同handleでprotected frozen DACLを1回設定する。
変更後に同ID/exact bytes/frozen ACE列を読み戻し、owner/group/integrity/mandatory policyの不変も比較する。
実GrantedAccessを再照会してWRITE_DAC/marker DELETEが保持されていることを確認する。
DACLの変更で既取得handleの権限が取り消されるとは扱わない。

全対象がverifiedになった時だけSealedPinsを同期continuationへ渡す。
親borrowと新世代全handleがliveの期間に限り呼び、戻り値はNoneだけを成功応答とする。
戻った直後のguard確認後は全新世代を逆順closeし、親borrowを返す。
continuationが直接別handleを開く・保持pinを外へ持ち出す行為を防ぐsandboxではなくtrusted内部契約である。
既存ownerへの動的slot追加や恒久的所有移管は導入しない。今回continuationは観測のみで、renameはしない。

## DACL backendと失敗境界

[SetSecurityInfo](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setsecurityinfo)へ
SE_FILE_OBJECT=1、DACL_SECURITY_INFORMATION|PROTECTED_DACL_SECURITY_INFORMATION=0x80000004を渡す。
owner/group/SACLの変更引数はNULL。返却DWORD自体がerrorで、0だけを成功としGetLastErrorは呼ばない。
[GetSecurityDescriptorDacl](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getsecuritydescriptordacl)で
present・非NULL・非defaultedを確認してから設定し、NULL DACLによる許可拡大を拒否する。
既存B1のfrozen policy生成・検証だけを再利用し、B1 harness/token操作は呼ばない。

frozen fileはEveryoneへ0x10116をdenyし、user/SYSTEM/AdministratorsのallowとRestricted Codeのread allowを持つ。
protectedで継承ACEなし。普通の新規write/deleteの拒否が意図であり、独立tokenの実操作は別試験となる。
権利定義は[File Access Rights Constants](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants)を参照。
owner/admin/WRITE_DACによる意図的変更、mapping、hostile同userには耐えると主張しない。
親rootはprivateのままであるため、親経由delete等を含む全保護の完了ではない。

backend内部のdescriptor作成・DACL抽出・設定それぞれの後でguardを確認する。
変更応答喪失/不正応答、途中失敗、読戻し不一致、再入、親停止では以後の観測/変更/continuationを止める。
設定中のstateはset_pending、読戻し中はreadback_pendingであり、例外時の変更結果は未確定。
DACLを元に戻すrollbackや再設定・再open・不明closeの再試行はしない。
LocalFreeはfinallyで1回。一次例外を保ち、後発の解放失敗も親/世代へ記録して資源停止を昇格する。
このbackendで確保したdescriptorの解放を確認する範囲で、既存共通API内部の全割当やOOM耐性を証明しない。

## 新規限定native仕様

| 項目 | 固定範囲 |
| --- | --- |
| 前提 | pure/fault試験・独立レビュー後、exact clean HEADと監視script hashを固定 |
| runtime | 既存Windows CPython3.14.0 Win64、実build/bootを記録 |
| root | 新規artifacts/file-sealing-2026-09-14/attempt-1またはattempt-2だけ |
| source/evidence | 新規source2 files各4096 bytes以下、prepare証跡1個64KiB以下、probe報告128KiB以下 |
| 実操作 | 新規source/prepare保存/元writer解放→2 filesの別権限取得→frozen DACL設定/読戻し→保持権限再照会→親不変の観測continuation→close |
| 対象外 | directory/rootのDACL変更、実rename/.complete、write/delete拒否試験、token変更、旧root/別project/正式publisher操作 |
| 資源 | private256MiB/working384MiB、空きRAM/drive各2GiB以上。境界40秒/外側45秒、約1秒監視 |
| 回数 | 最大2。原因特定・修正レビュー後だけ新rootで2回目。成功で終了、未使用枠繰越なし |
| 終了 | source13＋sink12＋new files2＝27 tracked handles、照会token2個close、exact inventory/bytes・worker exit0 |
| 異常時 | 後続操作停止、所有解放のみ。資源停止時は通常snapshot/JSONを作らず固定通知/exit80。fixture削除なし |

新entry SealingScenarioは既存observed prepare driverを使い、元writer実権限と変更後SDを記録する。
journalはprepare unknown/stopped、teardown succeeded、commit not_startedとなる局所試行である。
seal_payload等の全工程を実行したと見せる状態遷移は作らない。
4境界のworker資源観測と外側監視は、長期リーク不在・全期間最大メモリ・hard時間上限を証明しない。
Windows Update後のUBRはengineering記録として扱い、正式OS pinは更新しない。

次はstage/root directoryの取得権限・DACL固定と保持source/parentによる相対renameを接続する。
directory rename前の子handle解放、後続phaseの証跡更新、独立token/実故障/競合は未完了。
formal_permission/execution_authenticatedはfalse、acceptance_statusはnot_completedのまま。

## 実行結果

48f701fのclean HEADで1回目成功。新規2 filesにfrozen DACLを設定し、固定前後の実権限
0x160081/0x170081・同一物/bytes/SDを照合した。親root不変、27 tracked handles/token2個close、worker exit0。
外側0.555秒、stderr0 bytes。今回枠は成功で終了、未使用繰越なし。
[結果・保存記録](results/anomaly-multiseed-v0.3-s4-b2-file-sealing-2026-09-14.md)を参照。
