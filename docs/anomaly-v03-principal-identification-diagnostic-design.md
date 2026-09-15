# S4-B2 識別用tokenによるPreflight確認

2026-09-15。[Preflight専用診断](anomaly-v03-principal-preflight-diagnostic-design.md)の管理者Runはphase1/error1346で終了した。exit66882、PID39304、終了・observer解放を確認。明示token closeやwatchdog joinの成功は未確認で、成功と扱わない。通常Control/管理者Run両guardを閉鎖した。SAM/rootには触れていない。

error1346は[ERROR_BAD_IMPERSONATION_LEVEL](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1300-1699-)。個別API名を記録していないため失敗箇所は未確定だが、コードではAccessCheck専用peerTokenをDuplicateTokenのlevel2（SecurityImpersonation）で要求している。
[識別levelの公式定義](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ne-winnt-security_impersonation_level)は、SecurityIdentificationでSID/privilegeを取得してアクセス判定ができ、クライアントへのなりすましはできないことを示す。[AccessCheck](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-accesscheck)はclient impersonation tokenのTOKEN_QUERYを必要とし、[DuplicateToken](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-duplicatetoken)は指定levelのimpersonation tokenを返す。今回の用途からlevel1を選ぶ。linked tokenがこのPCで実際にどのlevelかは照会しておらず、推測を観測値としない。

変更はPrincipalSetup.csのDuplicateToken要求levelを2から1へ下げる一行。GetTokenInformationの正確長、SID/非昇格/noninherit、所有・解放・予算、祖先アクセス判定のdangerous mask、root/account policyを維持する。privilege有効化やOS設定変更なし。SeTcb等を追加せず、impersonation/logonも行わない。
同じ5 phase限定診断をこの修正sourceとcompileし、新規artifacts/principal-identification-diagnostic-2026-09-15へ隔離する。既存launcher/loader試験は新しい公開DLLのpathとhashへ固定し、以前の公開build/guardは上書きしない。通常Control/管理者Runはそれぞれ新規max1。Entry前のidentity解放を維持する。準備用Runは閉鎖済みcのままなので再使用しない。
既存34件・診断9件・loader10件、独立レビュー、commitとinput証拠を保存後に実行する。管理者exit0と終了・observer解放成功が揃えば、修正したPreflightから3 token close/StopWatchdogまで通過した根拠とする。前回失敗箇所が個別API照会で確定したとはしない。失敗したらこの新規guardも閉鎖し、次は内部stageの識別から進める。
元の3閉鎖rootへ再訪せず、新規root/accountも作らない。成功しても祖先AccessCheckの実機評価、環境準備、P/U、IPC、全期間/全publisher/marker/frozen/B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。既存資源上限とWindows Update engineering緩和/正式pin不変を維持する。
