# S4-B2 保持handle内の有界consumer読取

2026-09-14、基準4976bb3。実装savepoint **8c35fce85ced37c8d3edf2d9bde9b4f5487ecae1**。
[設計](../anomaly-v03-held-consumer-design.md)に従い、元rootと全sealed fileを保持したcontinuation内から、同じhandleで直接読む部品を追加した。
新規25＋既存306＝331件pass/0.286秒。独立レビューのP2計2件を修正し、最終P0〜P3残件0。
今回はfake Win32 APIと既存所有部品の接続まで。新規実機試行0回、native入口は変更していない。

取得したactual bytesは部品内の証拠として保持するが、外部へ返すのは状態・長さ・hashだけ。
**親/祖先namespaceと全inventoryの一貫性は未解決のため、consumer_payloadは常に返却を拒否する。**
前回modelの明示的test仮定で返却を許可するswitchは、この実読取部品には設けていない。
isolation/protected commit/future immutability/formal permission/execution authenticatedはfalse、B2/S4受入は未完了。

## 実装した順序と上限

1. 開始前に外部の元root Observation、既存plans/marker、source revisionを照合し、全file分のbufferを確保する。
2. 元rootと全子の同handle ID/type/SD/長さ・全子の実アクセス権を確認してから最初の読取を始める。
3. 元handleを先頭へseekし、各fileを同期ReadFileで1回読む。実際に取得したbytesの型・長さ・内容・SHAを照合する。
4. 全子と元rootを再照合する。読み終えた子も最後の照合まで保持し、途中の差替え・close・移管・再入・停止を拒否する。
5. callbackから戻った後、既存SealedFilesの全子close応答と最後のguard、owner/generation/journalの停止状態が確認できた場合だけ収集completeとする。

consumer自身はpathの再open、ACL変更、名前列挙、rename、marker write、handleの取得/closeを行わない。
周囲の既存SealedFilesが準備段階で行うopen/seal/path確認は残る。
_Bound.check/readは再openを伴うためconsumerでは使わず、observeと同handleの情報照会・securityを使う。
expected plan bytesを取得結果として代入せず、実readが返した同じbytesを保存する。

通常のlocal NTFS、既存WindowsSealBackendが取得した非OVERLAPPED fileだけを扱う。
期待長Nに対しN+1を要求しexact Nを許可する。空fileは1要求/0返却、file最大64KiB、buffer最大65537 bytes。
最大8 files、既存plan総量256KiB、marker16KiB、descriptor8KiB、guard512回を維持する。
短い読取・余分bytes・異常count/BOOL・seek/read失敗は単回で終了し、再試行やpointer復元は行わない。
ABIはFILE_STANDARD_INFO size24/BOOLEAN offsets20・21。DeletePending=false、links1、directory=false、allocation>=lengthを要求する。
[ReadFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile)、
[SetFilePointerEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfilepointerex)、
[FILE_STANDARD_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_standard_info)の同期仕様に基づく実装であり、今回の実OS確認ではない。

## 故障確認とレビュー

初回327件passの後、独立P2で最終guardがowner/generationへ停止を記録して正常returnした場合の成功誤判定を検出した。
終了時にも上位状態を取り込み、一次例外・resourceを維持して取得候補を破棄する処理と3試験を追加し、330件pass。
再レビューのP2では、その状態取得のjournal snapshotが二次障害を出すと、既知の一次例外が隠れる組合せを検出した。
既知の例外/resourceをsnapshotより先に確保し、MemoryError/RuntimeErrorの二次障害でも元の例外を保つ回帰を1件追加した。
最終331件はfailure/error/skip/expected failure/unexpected successが全て0。最終根拠はfinal-checks.jsonl。

同じfake Win32 surfaceで通常readを通し、全子保持、全metadataの先行検査、後続read中の既読file/root変更、実権限差分、異常read結果、全API境界の故障を検査した。
再入を握りつぶすcallback、別子close/移管/view差替え、close応答不明、一次失敗と後発resource停止、上限、0/1/65536 bytesも確認した。
独立レビューはread-only、進捗ポーリングなし。最終再レビュー後にコードを変更していない。repository safety/diff検査pass。

readerは所有権を取得せず、同期失敗後のcloseは元SealedFilesに委ねる。
子close不明ではrequires_exit=true。元root/関連祖先を保持して専用worker終了へ進む新callerの接続は未実装。
元rootの最終closeはcallerが担う。内部API全体の割当/cleanupや完全なOOM耐性、全期間不変性をこの結果から認定しない。

## 保存と資源

57 sourceのraw bytes/Git blob/候補checkoutが一致。前回retention-windowの54 sourceと8 artifactsは全て不変。
final-checks.jsonl242599 bytes/hash95cc1f9bf25ce8840916f25c1874abf2a9f6054ad91a9cb88bcfdb9f6d5266cf。
savepoint-evidence.json13272 bytes/hashba126b80b360bfa4ac84d1a47415ff61065df92101a2e9d44cfdca5ebd2f55a0。
ignored artifacts/held-consumer-2026-09-14/へ10 artifacts/論理924883 bytes（manifest自身を除く）。初回/修正後/最終の3テスト記録を保持。

保存した初期点UTC13:46:18は空きRAM14.55GiB/C117.56GiB/D52.68GiB、最終13:57:20はRAM14.36GiB/C117.56GiB/D52.68GiB。
開始時の軽量観測UTC13:34:14はRAM13.84GiB/C117.51GiB/D53.45GiB（ツール応答のみで保存初期点とは別）。
PC全体の変動原因は未特定。記録量と分けて扱い、長期リーク不在や全期間最大の証明にしない。他processへの操作なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和を維持し、正式pinは変更しない。
既存Python3.14.0を使用。新規worker/監視/checkout/常駐process/実機fixtureは追加していない。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変。旧batch/旧source、S3/D2/production、push/merge/CI、新runtime/account/serviceへ操作なし。

## 次の具体化

この部品を新規fixture専用の有界driverへ接続し、元root/祖先の保持、子close不明時のworker終了、資源監視、結果保存を先にfake故障で固定する。
その後、新規の限定native仕様を別途固定する。既存成功source/閉鎖済み最大回数枠は再利用しない。
全inventory/namespaceの共通観測期間、marker write/renameと全publisher、独立process/token・競合、正式OS/VM digestは引き続き未完了。
外部返却・隔離認定・B2/S4受入のgateを開く根拠はまだない。別account/サービスや受入条件の変更が必要なら、具体的な差分と運用負担を判断材料にする。
