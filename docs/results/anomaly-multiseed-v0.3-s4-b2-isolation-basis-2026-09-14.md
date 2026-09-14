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
