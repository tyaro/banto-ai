# S4-B2 writer解放後のreader再取得結果

2026-09-14。基準c50aabcfde1f5fc7937a30b0de8cfd773f8af413。
実装・native実行savepoint **cbb5a8263eef1be110ab86333a986dca9f4e87ba**。

**新規16＋既存108＝124 testsがpass。実Windowsでwriterを閉じた後にreader2個を再取得し、
元ID・bytes・SDと、Windowsが実際に与えた読取り権限を照合できた。**
[設計・試行仕様・公式API資料](../anomaly-v03-reader-reacquisition-design.md)を参照。
native publisher、DACL seal、S4受入の完了ではない。

## 実装と検証

ReacquiredReadersは新世代の全cellを取得前に保持し、元owner/cell双方のwriter close確認後だけ開く。
元rootのborrow内で全readerを検査・終了し、旧closed slotsは復活させない。
新readerが閉じたwriterと同じhandle番号を使っても、旧slotを再closeしない。
再入、親の早い終了、途中取得失敗、元例外＋後発資源停止、閉鎖応答喪失で後続処理を止める。

既存inspect_nativeに外部guardを接続し、reader側だけでなく親owner/journalの停止も各観測境界で確認する。
同bytesの別ID、改変bytes、正規化SD変化、余分なwrite/DELETE権限やread不足を拒否する。
返却長56 bytes/GrantedAccess offset4のNtQueryObject ABIと、失敗NTSTATUS→WinErrorの資源分類を検証した。
新backendはOPEN_EXISTING/share READ/非継承/OPEN_REPARSE_POINTに固定し、新readerではwrite/flushを行わない。

前回のobserved prepare driverへ固定scenarioフックを追加して再利用した。
writer権限照会→prepare保存/元file選択解放→reader再取得/照合/close→通常teardownの順である。
scenario cleanupの資源失敗でも通常snapshot/JSONを作らず、固定通知/exit80へ進む回帰を追加した。

部品14件、scenario接続を含む33件の確認後、記録済み初回123件pass/0.116秒。
資源cleanup回帰追加後の最終124件pass/0.119秒。両記録failure/error/skip/expected failure/unexpected success0。
独立レビューは本体・追加scenario/共通probe/監視/仕様の2範囲とも新規P0〜P3=0。
担当はread-onlyで試験/native/編集なし。進捗ポーリングなし。
repository safety・staged diff-check・監視PowerShell構文確認pass。
最終実行時18 sourcesとtests初期化/coreを含む20 filesを確定Git blobとraw bytes照合した。

## 限定実機結果

clean HEADと監視script hashをlaunch-plan.jsonへ固定し、新規
artifacts/reader-reacquisition-2026-09-14/attempt-1だけで1回実行した。

| 項目 | 実結果 |
| --- | --- |
| 元writerのGrantedAccess | 2個とも0x12019f（1180063） |
| 新readerのGrantedAccess | 2個とも0x120081（1179777）。read data/attributes/control/synchronizeに一致 |
| 再取得した対象 | facts.json / marker-pending.json。元volume/file ID/type/hash・exact bytes・正規化SD bytesに一致 |
| source/証跡 | source2 files計460 bytes、prepare.json2880 bytesを保持。終了後exact inventory/raw/hash一致 |
| 所有終了 | 元source13＋sink12＋new reader2＝27 tracked handles、照会token2個close、worker exit0 |
| 時間 | Windows26200.9445 / CPython3.14.0 MSCv1944 Win64、外側0.400秒 |
| 観測資源 | worker内4境界、最終0.049秒。private最大18.17MiB/peak working25.94MiB、資源停止なし |
| 標準エラー | 0 bytes |

reader2個は親borrowを返す前に閉じる。後続seal/renameへlive readerを渡す試行ではない。
新規ファイルのprivate DACLは変更せず、readerの取得権限を縮小した。
永続的なwrite禁止、独立tokenでの拒否操作、writer/reader権限照会以外のnative故障注入は未実施。
同一物照合はprobe内で行い、reader報告は対応slot・照合結果・実権限・終了状態を記録する。
新readerの全ID/SDの生値を別の証明書として再出力・認証するものではない。

journalは公開前で意図的に停止し、prepare=unknown/model_status=stopped、
teardown=succeeded、commit_observation=not_startedを維持した。
今回の最大2回枠は1回目成功で終了。未使用枠繰越なし。過去の終了済み枠を流用しない。
DACL seal、rename/.complete、token変更、正式publisher/キャンペーンは実行していない。

外側1秒監視は短時間終了のためsamples0。worker4境界の値であり全期間の最大メモリ・長期リーク不在を保証しない。
Start-Process内部の起動後返却喪失、hard時間上限、電源断耐久性は別の限界として残る。

## 記録・資源・残件

新規ignored root artifacts/reader-reacquisition-2026-09-14/へ保存した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| final-checks.jsonl | 90397 | e400e7c0c2f5cb8c2f881bbee3eaa2506fab1eb9cc040fb6ebf230b4a4d8f5d8 |
| attempt-1/probe-result.json | 13977 | b4720d37857665c54b39cc06a9c8051cc13a81398076c1f826bd6a607167aa20 |
| attempt-1/private-evidence/prepare.json | 2880 | a4851869d6e5c33b9052ed931896e0969efcc5228e343c8ae231d39e303f8d45 |
| attempt-1.supervision.json | 518 | 2dca2d22263bd79e7c077e08f14793dac8de62cb074106587d216b650bf24899 |
| resources-final.json | 395 | 028bfedf63f7666fcd27a1b4c4dbca04e4d46f4d7eb0d396e13886f08dcf0c28 |
| savepoint-evidence.json | 8320 | 11fbba243086a44670ffe23f3000ab673299b99447b084fd4a0a6db613bbbb4a |

manifest自身を除く17記録は259832 bytes。scriptや試験stderrを含む論理bytesでありdisk占有量ではない。
source/実行HEAD/監視script/原bytesのhashを結び付け、前回observed evidence manifest内の全artifact不変も照合した。

開始UTC08:15:31 RAM8.64GiB/C109.48GiB/D87.12GiBは当時の取得結果を転記。
実機前保存08:26:21 RAM7.61GiB/C119.94GiB/D87.12GiB、
最終保存08:28:08 RAM7.78GiB/C119.96GiB/D87.12GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00を記録した。
大きなC空き増加の原因は調査せず、本作業の効果やリークの有無に帰属させない。
worker・短い検証processは終了、常駐処理なし。別project連続稼働終了後も通常の資源確認を継続した。

次はsealに必要な検査用権限とrename用権限の取得・寿命、DACL固定と読戻し、保持親/sourceの接続を具体化する。
今回の一時的な読取り世代を、既存ownerへの動的slot追加や公開用handle移管の完了として扱わない。
formal_permission=false、execution_authenticated=false、acceptance_status=not_completedを維持する。
正式OS整合、VM digest、runtime closure/consumer、独立token/競合/失敗native全受入、S4受入は未完了。
src/科学config/schema/registry/正式pin、本流889cfc3は不変。旧Linux CIへ件数を足さない。
push/merge/CI起動、新runtime導入、共有環境/別project/旧failure rootsへの操作なし。
