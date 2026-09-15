# S4-B2 token情報長さの読取診断

2026-09-15。準備cは管理者起動/終了まで確認できたがPreflightでnative error24となり、作成phaseへ進まなかった。固定C#はTokenLinkedToken(19)とTokenElevation(20)の両照会へ64 bytesを渡すため、通常権限の自process tokenで渡す長さを比較する。

[診断](../tools/windows_token_length_diagnostic.ps1)は固定4ケース（class19:64/8、class20:64/4）だけを実施。失敗した同一caseのretryではない。Windows x64/固定U SID/非昇格を確認し、22528 bytes/SHA48eb8f4dfbaa09a38fb4642af23f49412534da150b4ef9ca6eb41725a91893bfの保存済み公開DLLからP/Invoke宣言を使う。準備Entry、SAM/root、UAC、impersonation、他process tokenへ接続しない。
新規artifacts/token-length-diagnostic-2026-09-15のCREATE_NEW/flush済みguardでmax1。allocationは各case64 bytes。API返却直後のBOOL/error/required_lengthを解釈前に保存する。class19成功/ABI確認後のlinked handleだけを一度closeし、class20成功時は4-byte値を読む。OpenProcessTokenが成功して有効handle取得を確認した場合だけown tokenをcloseし、不確実なnonzero出力を推測closeしない。一次/解放例外を分けて記録し、途中結果を失わない。

[GetTokenInformation](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-gettokeninformation)は情報classで出力構造が変わる。[TOKEN_LINKED_TOKEN](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_linked_token)はHANDLE一つで、返却handleのcloseが必要。[error24](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-)はERROR_BAD_LENGTH。資料だけから今回の正確なAPI失敗位置を断定せず、比較観測を残す。
この通常tokenの比較を管理者preflight全体の成功証明としない。独立レビューで取得未確認handleのclose（P2一件）を修正し、解釈前のquery記録も追加した。再確認残0。実機比較以外の反復・OS設定変更なし。旧root3件/旧作成guardは閉鎖状態を保全し再訪しない。全許可flags=false、acceptance_status=not_completed。
