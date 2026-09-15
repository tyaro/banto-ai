# S4-B2 作成用process内のSeSecurityPrivilege管理

2026-09-15。[準備dのphase4/error1314](results/anomaly-multiseed-v0.3-s4-b2-principal-setup-d-2026-09-15.md)後の修正。[新規objectのSACL](https://learn.microsoft.com/en-us/windows/win32/secauthz/sacl-for-a-new-object)は明示SACL作成時にSeSecurityPrivilege有効化を要求する。前回Bの特権状態は未観測なので、前回原因の確定とは区別する。

固定の作成用B process tokenへQUERY/DUPLICATE/ADJUST_PRIVILEGES（0x2a）でアクセスする。LookupPrivilegeValueWはSeSecurityPrivilegeだけを指定する。TOKEN_PRIVILEGESの読取りは固定4096-byte上限/返却長/件数/12-byte entry/完全LUID一致/重複拒否で検証し、特権がなければ1314で止める。新しいOS特権の付与、他の特権やaccountの変更は行わない。
PrivilegeLeaseは開始時の有効ビットを保存する。無効時だけ一件をenableし、有効を再照会する。既に有効ならadjustしない。終了側は元が無効の場合だけdisableし、元の有効ビットに戻ったことを再照会する。同一backend/tokenに結び付け、各開始/復元は単回。USED_FOR_ACCESS等の参照属性まで元に戻すという主張はしない。
[AdjustTokenPrivileges](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-adjusttokenprivileges)はBOOLがTRUEでもERROR_NOT_ALL_ASSIGNEDの場合があるため、直後のerrorが0かも必須確認する。固定一件・DisableAll=false・attributeはENABLEDまたは0だけ。削除・全無効化・OSへの追加付与はしない。復元はqueryで保存した有効ビットを同じ一件へ適用する。

既存PreflightのSID/linked U非昇格/識別用token/noninherit/runtime確認の後でleaseをenableする。CloseAdminTokenで復元・再照会を完了してからadmin tokenを閉じる。phase番号と失敗後の後続操作停止は維持する。失敗/復元失敗では再試行せずraw handleとleaseをprocess終了まで保持し、callerは即時終了する。失敗後の復元完了を偽らない。watchdog40秒/private256MiB/working384MiB/空きRAMとC各2GiBを維持する。
既存Preflight冒頭のWindowsIdentityもusingで解放する。通常C#試験はfake privilege backendで元の無効/有効、5箇所の失敗、検証不一致、再利用拒否、TRUE+1300、native ABI、LUID/境界/欠落/重複を確認する。既存34件と5 phase診断9件、loader10件も新buildで確認する。

最初の実機対象は5 phase限定の診断だけ。新規artifacts/principal-security-privilege-diagnostic-2026-09-15へ固定し、新しい公開DLLを有界inline/hash/同bytesロードする。通常Controlと管理者Run各max1、直接Shell/Hidden/System32/共有observer45秒。Entry前のidentity解放を維持。exit0/終了/observer解放/例外なしが揃ったときだけ、特権存在・有効化確認・元の有効ビットへの復元とtoken/watchdog終了が通った根拠とする。開始時の有効ビットそのものはexit記録へ出力しないので、その値を推測しない。
この診断は作成・SAM/root・祖先handle・logonを呼ばない。process内の一時的なtoken状態変更はあり、OSの永続設定変更はない。root定数は閉鎖済みdのままで準備Runは再使用しない。末尾なし/b/c/dの4閉鎖rootへ存在確認/再open/列挙/hash/copy/deleteしない。診断を確認してから新規準備を具体化する。
全許可flags=false、acceptance_status=not_completed。専用環境準備の既存許可を維持する。既存Python3.14.0/.NET、Windows Update engineering緩和/正式pin不変。新runtime/service/task/VM/profileなし。
