# S4-B2 初期検査の停止条件を識別する新規準備g

2026-09-16 JST。準備fのphase5/detail65535を受け、元の保護条件とnative呼出し順序を維持して診断だけ追加する。fは終了確認済み、後続SAM2221/free0。旧末尾なし/b/c/d/e/fの6 rootへ存在確認/再open/列挙/hash/copy/deleteしない。
新規rootはC:\ProgramData\BantoAI-S4B2-principal-20260916g、公開記録先artifacts/principal-setup-g-2026-09-16。既存の環境準備許可と2026-09-16 JSTの「次に進めてください」に基づく新規一回。P enable/logonや追加のOS特権付与はない。[準備eの保護・寿命契約](anomaly-v03-principal-setup-e-design.md)を維持する。

## 固定値の診断

事前確保FailureStateへInspectionStepと1-byte PolicyDifferenceを保持する。phase5の最初にbudgetを記録し、volume pin、parent pin、volume/parent AccessCheck、root identity、actual SDDL取得、expected SDDL変換、差の分類、元の厳密比較の順で更新する。その他のphaseではNoneと差0へリセット。watchdogは診断フィールドへ書き込まない。
祖先の短絡評価を、volume比較に成功した場合だけparent比較へ進む同じ順序の二条件へ分ける。失敗後のnative API、追加の権限照会、retry、補償、closeは増やさない。

既存のphase5/detail65535だけ、stepがある場合にbit29を立てて詳細化する。bit30は従来のrelease失敗、phaseはbits16..28、kindはbits13..15（0その他/1 InvalidOperation/2 OOM/3範囲外Win32/4一次release停止）、stepはbits8..12、差はbits0..7。既知native error、その他phase、step未取得の符号化は変更しない。catch側では例外Message/Data/stackや新しいOS情報に触らず、固定数値だけ返す。loader/watchdog終了は従来通り。
差はowner1/group2/DACL4/labelを含むSACL8、DACL保護bit差16/SACL保護bit差32/DACL auto flags差64/SACL auto flags差128。差の分類が完了したstep10だけpolicy_difference_available=true。差0からpolicy一致を推定せず、成功判定は従来のactual SDDL == canonical expectedのまま。
比較は既に取得した上限付きSDDLから行い、新たなnative読取をしない。RawSecurityDescriptor.GetSddlForm(Audit)だけではこのruntimeでmandatory label ACEが省かれたため、raw ACL binaryも比較する。build-01のlabel差試験失敗を保存し、build-02で修正を検証する。途中で分類自体が失敗すればstep9のまま停止し、差は利用不可とする。
launcherの純粋decoderはmarkerをnative errorと混同せず、元のunknown detail65535を別記録し、kind/step/phaseの範囲外はencoding_valid=falseとする。標準成功/旧失敗code、release flagを保持する。

## 実行と未完了事項

通常試験43＋特権15＋launcher純粋試験12、通常load-only、独立レビュー、source/DLL/hash/資源保存後、SAMと新規g不存在を直前照会して新規guard一回。入力記録は上書きしない。exit0/終了/observer解放が揃う場合だけgの既知receipt/SAMを確認する。失敗時はgも閉鎖しSAMだけ確認する。
40秒watchdog/private256MiB/working384MiB/空きRAM・C各2GiB、UAC待ち別記録。別projectの走査/停止なし。OS build/bootと資源を記録し、Windows Update engineering緩和/正式pin不変。全許可flags=false、acceptance_status=not_completed。環境準備/P-U/IPC/全publisher/正式B2-S4未完了。

## 調査根拠

[SECURITY_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-information)ではlabelと全SACLの取得範囲・必要アクセスが異なる。[MS-FSAの照会手順](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/0a9f223c-b258-4f61-8b59-92f970341400)ではlabel単独の照会でもSACL control bitsをコピーする。0x17だから必ず保護bitが消えるとは推定しない。fは祖先/属性/資源/SDDL等のどこで失敗したか未確認であり、gの観測をfの過去の原因確定に転用しない。
