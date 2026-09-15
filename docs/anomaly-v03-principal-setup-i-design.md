# S4-B2 既存の無効Pを維持する準備iと最終検査診断

2026-09-16 JST。[h結果](results/anomaly-multiseed-v0.3-s4-b2-principal-setup-h-2026-09-16.md)と引継ぎ113節を受けた承認済み専用環境準備の継続。新rootはC:\ProgramData\BantoAI-S4B2-principal-20260916i、公開記録先artifacts/principal-setup-i-2026-09-16。旧末尾なし/b/c/d/e/f/g/hの8 rootへ存在確認/再open/列挙/hash/copy/deleteしない。

## 既存Pの固定と読み取り

PはBantoS4Publisher、SID S-1-5-21-2169670816-255940906-2713565042-1010、flags0x203を全bit厳密一致で固定する。通常側の直前SAM照会とhelperのphase3でname/SID/flags/Usersを確認し、成功した場合だけ新規root不存在を照会する。既存Pが消失・再作成・有効化・属性変更された場合は新規root作成前に停止する。通常側照会と後の状態が永続不変であるとは主張しない。
helperはExistingEntry.Runのみを起動し、Sequence(true)はphase6 CreateDisabledAccountとphase8 AddUsersGroupを呼ばず、他20 phaseの順序を保持する。phase3ではInspectAccount→Users SIDからalias解決→InspectGroups、phase7/9/11でも既存検査を繰り返す。UsersのSIDはS-1-5-32-545、全応答成功・read=total1・Usersだけを要求する。
NativeBackendからaccount作成/所属追加の実装とNetUserAdd/NetLocalGroupAddMembers/BCryptGenRandomのPInvokeを除去する。phase6/8を誤って渡した場合も変更APIを呼ばず拒否する。旧phase番号と旧順序の純粋試験モデルは維持するが、現在のnative entryは既存P専用。reset/enable/logon/delete APIの追加なし。秘密情報の生成・保存なし。
成功時receiptにはprincipal_mode=existing-disabled-readonly、account_created_this_run=false、account_modified_this_run=falseを追加する。Pに新規rootのreadonly ACEを与える以外に権限を増やさない。Windows全体のuser rightsや将来のP tokenの隔離は今回の確認範囲外。

## phase11の診断

[g診断](anomaly-v03-principal-setup-g-design.md)のbit29によるunknown-detail細分化をphase11にも適用する。kind/step/差の配置とbit30のrelease状態は維持。Budget、volume/parent pin、各AccessCheck、root identity、実SDDL、期待SDDL、差の分類、厳密比較、account、groupsを順に記録する。追加step11はaccount、12はgroups。差は従来同様step10だけ利用可能。既知native error、その他phase、観測なしの旧codeは維持し、decoderがphase5/11を区別する。
初期・最終DACL/SACLの要求はhと同一（D:P、S:PAI、保護とmedium/no-write-up、U/P readonly）。最終DACLのauto flagsが原因という仮説に合わせて条件を変更しない。失敗後の追加root APIやreceipt探索なし。

## 検証・実行

既存の44件に、20 phaseの成功/全停止位置/再使用拒否、account name/SID/全32flagbitの変更拒否、変更API import不存在、最終検査step符号化を加えて49件。特権15件とlauncher13件を合わせ77件、通常load-only、独立レビュー、source/DLL/hash/資源とcommitを保存後に新規guard一回。
初期/最終の厳密SDDL、祖先保持、phase失敗停止、元の特権有効bit復元、child→root→ancestor→token→watchdogの終了順を維持。内側40秒/private256MiB/working384MiB/空きRAM・C各2GiB、外側終了観測45秒、UAC待ち別記録。
exit0と終了/observer解放が揃う場合だけiの既知receiptとSAMを確認する。失敗/不明ならiも閉鎖しSAMだけ確認。account/root補償削除なし。Windows Update engineering緩和/正式pin不変、既存runtimeのみ、他projectの走査/停止なし。
全許可flags=false、acceptance_status=not_completed。環境準備/P-U/IPC/全publisher/正式B2-S4を事前に完了扱いしない。
