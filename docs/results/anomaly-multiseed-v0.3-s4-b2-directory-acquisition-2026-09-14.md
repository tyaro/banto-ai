# S4-B2 単一呼出しdirectory取得の実装・故障確認

2026-09-14、基準46b8d35、実装savepoint **7f9332289494f9b24e9e5e786737864ac88b0ae3**。
[設計](../anomaly-v03-directory-acquisition-design.md)に従い、作成と初回handle取得を1回のCreateDirectory2W呼出しにする部品を追加した。
今回の試験は全てfake API。実機entry/監視/試行枠は追加せず、CreateDirectory2W本体は呼んでいない。
既存private sink・6工程・S3/D2・productionへの接続はない。

**新規19件＋既存202件＝221件pass/0.361秒**。failure/error/skip/expected failure/unexpected successは全て0。
実装・試験・設計の独立レビュー初回P2=1を修正し、修正差分の再レビューで残件P0〜P3=0。read-only、進捗ポーリングなし。

## 実装と確認した故障

| 部分 | 確認したこと |
| --- | --- |
| 事前準備 | API/5引数ABI、private descriptor、SA24 bytes、root0x1600a7/share READ/redirect拒否/非継承の引数を作成前に準備 |
| 所有取得 | 予約済みTrackedOpenへ原handleを保存してから検査。0/NULL/-1/INVALID_HANDLE_VALUE・異常値・衝突を拒否 |
| 同じhandleの観測 | NtQueryObjectの実権限exact一致、private SD、前後のID/type一致。不一致と観測失敗で停止 |
| path再open | 既存_Bound.checkは使用せず、_Bound.observeだけを借用。名前からの明示的な開き直しを追加しない |
| 正常終了 | 取得したhandleをfinishまで保持し、CloseHandle→LocalFreeの順で各1回。繰返しfinishで再close/freeしない |
| 応答喪失 | 作成の返却前は所有unknown、descriptorを保持しworker終了が必要。close/free応答喪失も再試行しない |
| 例外と再入 | 元の例外objectを保持し後発resource stopを昇格。guard/prepare/create/inspect/finish中の再入を握り潰しても成功にしない |

祖先の保持・pathとの結合はcallerの前提であり、この部品が証明したものではない。
子inventory・peerのADD/DELETE_CHILD・外側parent・handle移管・consumer一貫性も未検証。
API成功、namespace隔離、native所有終了の実証ではなく、全受入/隔離flagsはfalse/not_completedを維持する。

初期の15件pass後に故障条件を4件追加して19件pass。記録した初回全体も221件pass/3.101秒だった。
独立P2はfake試験がホストPython版に依存する点。setUpでsynthetic3.14.0を固定しcleanupで復元する3行を追加した。
本体のWindows/Python3.14.0 exact制限は不変。外側をsynthetic3.12.9/posixとして正常系1件の成功と外側状態の復元も確認した。
これは実Python3.12を実行した結果ではなく、追加runtimeは不要。修正後のcorrected-checks.jsonlを最終根拠とする。

## 保存と資源

ignored artifacts/directory-acquisition-2026-09-14/へ初回/修正後の記録を保存した。
32 source＋補助2 filesのraw/Git blob一致、前回isolation-basis manifest/5 artifactsのhash不変と既存32 source不変を照合した。
repository safety・差分空白検査pass。以後コード変更・重複試験なし。文書リンク/保存hashの最終照合もpass。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| corrected-checks.jsonl | 162016 | cdb64fe52b37b0c645599d942687193086fa10e09cba93c95fbeba2d7916c3f3 |
| savepoint-evidence.json | 11031 | 45084efd046a472c889a9bad65124046e1d033ecdd8ffb3985261511dd443591 |

manifest以外10 artifactsの論理bytes419071。filesystem全占有量ではない。
開始UTC11:26:41の空きRAM12.50GiB/C118.49GiB/D73.73GiB、試験後11:39:00はRAM4.50GiB/C118.16GiB/D66.77GiB。
RAM低下を受けて文書保存に作業を絞り、11:40:40に再観測したところRAM16.00GiB/C118.16GiB/D64.04GiBだった。
上位6 processの名前/PID/working/private memoryを読取りだけで記録し、他processを停止していない。
RAMは再観測時に回復したが、disk空き減少を含む変動の原因は未特定。点観測から長期リーク不在やprocess最大値を断定しない。
今回の試験・記録processは終了し、新規常駐/監視/checkoutなし。次の実機検討時にも資源を再確認する。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和・正式pin不変。

既存親policy結果書の差分8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持し、今回commitから除外した。
旧batch/B1/失敗source、push/merge/CI、別project、新account/service/runtimeへ操作なし。本流889cfc3不変、旧CIへ件数加算なし。
次は局所driverの祖先結合・所有unknown時の終了・記録順序を具体化し、監視/上限/source固定後に別の実機仕様を定める。
局所取得に成功しても全隔離条件が未確認ならnative publisherへ進まない。親全保護、marker/全publisher、独立token/競合、consumer/runtime closure、正式OS/VM digest、B2/S4受入は未完了。
