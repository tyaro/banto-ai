# S4-B2 特権復元確認後の新規principal準備e

2026-09-15。[必要特権の確認・復元診断](results/anomaly-multiseed-v0.3-s4-b2-security-privilege-2026-09-15.md)が管理者exit0で終了した後の、承認済み専用環境準備。
新規rootは **C:\ProgramData\BantoAI-S4B2-principal-20260915e**、記録は **artifacts/principal-setup-e-2026-09-15**。account名BantoS4Publisherと同名不存在条件を維持。末尾なし/b/c/dの4閉鎖rootへ存在確認/再open/列挙/hash/copy/deleteしない。旧作成/診断guardの再使用なし。eも新規CREATE_NEW max1、失敗・応答不明時は閉鎖して再試行しない。

[特権scope](anomaly-v03-principal-security-privilege-design.md)を維持し、B自身の既存SeSecurityPrivilegeだけを必要時に有効化し、CloseAdminTokenの前に元の有効ビットへの復元を再照会する。新たなOS特権付与はしない。SID/非昇格/識別用token/ancestor dangerous mask、BA所有・初期からの保護DACL/medium label・U/P readonly、disabled標準account/Users、unmanaged secretを維持する。Pのenable/logonなし。
C#変更はroot定数d→e。launcherは出力場所/attempt.rootをeへ変更し、Buildが新しい特権15件も必ずcompile/実行する。DLL・通常試験exe・特権試験exeの既存出力が一つでもあれば上書きせず停止する。通常compileの34＋15件、通常load-only、独立レビュー、commitとsource/hash/resource保存後に新規Run一度。

通常側の事前照会は対象SAMと新規e不存在だけ。helperも祖先保持後に再確認する。[既存準備順序](anomaly-v03-principal-setup-design.md)のroot/account作成・初期/最終policy・preclose receipt・child/root/ancestor/token解放を維持。直接Process.Start/UseShellExecute/runas/Hidden/System32、observer45秒、内側watchdog40秒/private256MiB/working384MiB/空きRAMとC各2GiB。UAC待ちは別記録。
exit0・終了確認・観測/解放例外なしが揃った場合だけ、eの既知bootstrap-result.jsonとSAMを読取確認する。失敗時はeへ再訪せず、SAM状態だけを読取り、code順序による推論と実観測を区別する。通常側の昇格process kill、account/root補償削除は行わない。
現在のOSはbuild26200.9445/boot2026-09-15T14:30:24.5000000+09:00。前回bootからの変更を記録し、Windows Update engineering緩和/正式pin不変を維持する。既存Python3.14.0/.NET、新runtime/service/task/VM/profileなし。
成功してもP activation/reset/logon/disable、protected code/process/thread/token/IPC、P/U、namespace共通期間/全publisher/frozen/marker/正式B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。
