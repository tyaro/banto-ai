# S4-B2 隔離条件の具体化とAPI存在確認

2026-09-14、基準1f70faa、設計savepoint **5b81bf032768d0ac486aff48143b77268ab36158**。
[設計書](../anomaly-v03-isolation-basis-design.md)に、生成時の取得競合・既取得parent権限・handle移管・consumer整合の条件を記録した。
次の候補はCreateDirectory2Wで作成と初回handle取得を1回の呼出しにする限定部品。隔離成立や方式採用を認定したものではない。
**新規設計1ファイルの独立レビューはP0〜P3=0**。read-only、進捗ポーリングなし。レビュー担当によるAPI資料再照合・実機実行はない。

現行private DACLは同じuser等へfull allowを与え、CreateDirectoryWの後に別openでrootを取得する。
新APIでこの間隙を減らしても、private期間のADD/DELETE_CHILD、外側parentの既取得権限、marker writerの移管経路は別に確認が必要。
share設定名やrootの削除拒否だけで、子の追加/削除も拒否されたことにしない。
consumerも固定pin・同じhandleとbytes・共通の変更不能期間等を必要とし、二度の一致観測だけでは同時性やABA不在を証明しない。

## 今回の読取り確認

- 既存Windows SDK10.0.26100.0のfileapi.hでCreateDirectory2Wの5引数HANDLE宣言とredirect拒否flag=1を確認した。
- 既存Python3.14.0/Win64からkernel32のexport有無だけを照会し、CreateDirectory2Wの存在を確認した。
- 関数本体の呼出し、directory fixture作成、新しいSDK/runtime導入は行っていない。
- [公式ページ](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createdirectory2w)の5引数syntax/6引数例、失敗0本文/INVALID_HANDLE_VALUE例の食い違いを記録した。ローカルSDKと[Microsoft header](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/fileapi.h)に一致する5引数を設計基準とし、0とINVALID_HANDLE_VALUEをどちらも成功にしない。

header原fileは40460 bytes/hash f8927178c75de487c0e57f044a215e455522bf6eaa0b660421be09cd06ae05a1。
資料の各根拠と設計上の推論は設計書内で区別した。API存在・宣言一致を実取得成功や競合耐性の証拠にしない。

## 保存・検証・資源

ignored artifacts/isolation-basis-2026-09-14/へ保存した。
前回202件passの対象32 sourceとGit blob/作業領域の一致、前回manifestと6 artifactsのhash不変を照合した。
今回は製品・試験コードの変更がなく、新規テスト0・既存テストの再実行0。202件を今回実行の件数として加算しない。
repository safety・差分空白検査pass、今回追加の文書リンクと保存hashの一致を確認した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| local-api-basis.json | 993 | 261decf99e6fbd0e9495008427a3500ad932812a24ddd9e48b208640237a9780 |
| savepoint-evidence.json | 9337 | bb10fdd7744db58c7e0b87e04e85fdea5f8864b73089c1966fbf4d868aa2d7f6 |

manifest以外5 artifactsの論理bytes7725。記録用processは終了、新規常駐/監視/checkoutなし。
開始UTC11:05:49の空きRAM13.30GiB/C118.92GiB/D74.23GiB、終了11:12:38はRAM12.77GiB/C118.91GiB/D74.02GiB。
点観測からprocessピーク・長期リーク不在や空き容量変動の原因を断定しない。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00を記録。Windows Update engineering緩和・正式pin不変。
前からある親policy結果書の作業差分8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持し、今回commitから除外した。

次は設計書末尾の単一呼出し取得部品とfake backend故障確認を実装する。局所実機仕様はその検証・レビュー後に別途固定する。
全隔離条件が未確認ならnative publisherへ進まない。専用account等の追加判断は現時点で不要。
旧batch/B1・失敗sourceへの操作、push/merge/CI、別project、新account/service/runtimeの追加なし。本流889cfc3不変。
親全保護、marker/全publisher、独立token/native競合、consumer/runtime closure、正式OS整合/VM digest、B2/S4受入は未完了。
formal_permission/execution_authenticated/protected_commit_allowed=false、acceptance_status=not_completedを維持する。

## 2026-09-15 権限分離準備の現状

後続作業の最新状態は[引継書110節](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)と[長さ不具合の結果](anomaly-multiseed-v0.3-s4-b2-token-length-2026-09-15.md)を参照する。
通常/管理者で公開DLLの読み込みに成功。新規準備cはPreflightのerror24で終了し、固定コード上はroot/account作成phaseへ到達していない。終了後SAM2221でaccount不存在を確認したが、rootの再確認はしていない。末尾なし/b/cの3 rootと各guardを閉鎖し、再訪・再実行しない。
通常の自token4条件で64-byte指定の失敗、8/4-byte指定の成功を観測した。7a2f066で2行修正、34件pass/独立所見0。修正後の管理者Preflight全体は未確認なので、環境準備完了やP/U隔離の根拠にはしない。次は作成phaseを含まない新規の管理者Preflight専用診断を仕様化し、token/watchdogの終了まで確認する。
専用環境準備の既存許可は継続。正式受入条件は緩和せず、全許可flags=false、acceptance_status=not_completed。

## 2026-09-15 管理者Preflight成功後の更新

最新は[引継書111節](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)。識別用token要求をlevel1へ修正し、[管理者Preflight](anomaly-multiseed-v0.3-s4-b2-principal-identification-confirmation-2026-09-15.md)は3 token close/StopWatchdogまで成功した。後続の[準備d](anomaly-multiseed-v0.3-s4-b2-principal-setup-d-2026-09-15.md)は祖先確認と不存在確認を通過したが、phase4のroot作成でerror1314。終了後SAMはaccount不存在、dの状態は再確認せずunknownとして閉鎖した。閉鎖rootは末尾なし/b/c/dの4件。
次は明示SACLに必要な既存特権の確認と、B process内だけの一時有効化/復元を検証する。初期保護条件を省かず、OSへの追加特権付与や閉鎖root再使用をしない。環境準備/P-U/正式受入は未完了、全許可flags=falseを維持する。

## 2026-09-15 既存特権の復元確認後

最新は[引継書112節](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)。B processの既存SeSecurityPrivilege一件について存在/有効確認/元の有効ビットへの復元を実装し、管理者診断exit0でtoken/watchdog終了まで確認した。追加のOS特権付与はない。
後続準備eは管理者起動のrequest-launch/error1223でPID/exit未取得。SAMはaccount不存在、eへ再訪せず閉鎖したため、閉鎖rootは末尾なし/b/c/d/eの5件となる。新規fは49件と通常load-onlyを通過し、今回の管理者画面操作の回答待ちでRun未開始。環境準備や隔離を完了扱いせず、全許可flags=falseを維持する。

## 2026-09-16 初期検査通過・専用account無効状態を確認

最新は[引継書113節](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)と[準備h結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-h-2026-09-16.md)。fの初期検査停止を受けgで固定診断を追加し、SACL/auto flags差を観測した。hではS:PAIを明示し、初期の全SDDL厳密比較、disabled account作成/Users確認、最終DACL設定まで通過。phase11の最終検査で停止し、具体的な条件は未特定。
P SID S-1-5-21-2169670816-255940906-2713565042-1010、flags0x203、Usersのみを終了後SAMで確認。Pをenable/reset/logonしていない。旧8 rootは全て閉鎖し、次は既存の無効Pを変更しない新規準備経路を設計する。71件pass/独立指摘0。環境準備/隔離/正式受入は未完了、全許可flags=falseを維持する。

## 2026-09-16 専用環境の準備完了

最新は[引継書114節](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)と[準備j結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-j-2026-09-16.md)。既存無効P専用経路でaccount変更APIを除去し、iで最終DACL比較の差を観測。jは最終D:PAI/S:PAIを厳密照合し、receipt/特権復元/close/watchdogまでexit0で終了した。成功後の既知receiptとSAMも検証済み。P SID末尾1010/flags0x203/Usersのみ、enable/logonなし。
jは保存された準備済み環境、旧9 rootは閉鎖、作成guardは全て消費済み。78件pass/独立指摘0。専用環境準備のみ完了し、P-U process/token/IPC/干渉、全publisher/正式受入は未完了。全許可flags=falseを維持する。

## 2026-09-16 起動・終了のmodel検証とlinked token照会

最新は[引継書115節](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)と[worker lifecycle結果](anomaly-multiseed-v0.3-s4-b2-worker-lifecycle-2026-09-16.md)。26操作の純粋model、応答不明時のcontainment、QUERY用handleの取得確定/単回解放を実装し、65＋8＋15の88件pass、レビューのP2計3件修正後は残存0。
通常Uのlinked full tokenを一度だけ読み取り、SeIncreaseQuotaPrivilegeは存在/無効、SeAssignPrimaryTokenPrivilegeは不存在、SeImpersonatePrivilegeは存在/有効。両query handle close/launcher exit0。将来のP token assignabilityや別UAC tokenの証明ではない。
今回P/SAM/全保護rootへアクセスせず、privilege調整/UAC/worker起動もなし。既存権利の範囲で起動API/初期SD/原子的job参加が成立する条件を先に確定する。native backendと隔離/正式受入は未実装・未完了、全許可flags=false。

## 2026-09-16 ユーザーの運用前提に合わせた保留

[引継書§116](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)が現在の作業方針。同じ出力先へ同時に書かない単一writer運用を優先し、専用principal/起動API/厳密な分離検証は保留する。通常の非上書き・重複使用拒否・途中終了時の未完了判定は残す。上記の観測結果や未達の隔離保証は変更せず、次の開発指示で分離試験を自動再開しない。今回OS操作・削除・受入gate変更はない。
