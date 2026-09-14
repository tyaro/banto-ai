# S4-B2 親DACL条件と相対renameの比較結果

2026-09-14、基準594bf1d282653b54dbe881ab63e9856cff9f826c。
実装・2条件の実行savepoint **a31ae9b5119ed28c5271502d252ce2425c4b448e**。

**新規5＋既存167＝172 tests pass。親privateでは相対renameと終了後3 objectsの一致確認が成功し、
親frozenではNTSTATUS0xc0000022/WinError5の拒否が再現した。両workerと全tracked handlesの終了を確認した。**
同じ実装・NT要求で親policyによる差が観測された。内部拒否箇所の特定や全publisher受入ではない。
[設計・公式API資料](../anomaly-v03-parent-policy-rename-design.md)と[前回の失敗結果](anomaly-multiseed-v0.3-s4-b2-directory-rename-2026-09-14.md)を参照。

## 変更・検証

DirectoryRenameに明示parent_policy=privateの比較modeを加え、既定frozenを維持した。
private条件はrootのDACL設定だけを省く。stage/全子fileの固定、全子close、rootの元ID/private SD完全一致、
保持実権限、証跡保存後の再検査は両条件で共通。root状態はprivate_verifiedとし、frozen verifiedと混同しない。
終了後の別読取り確認もrootは選択policy、payload/factsはfrozenで元ID/bytes/SDを照合する。

新規parent_policy_probe entryはattempt-1をprivate、attempt-2をfrozenに固定する。
監視scriptは1の同じrevision・rename成功・3 objects一致・所有終了・worker exit0を確認したときだけ2を開始する。
各条件1回の比較であり、失敗後の再試行ではない。2の拒否はdirectory_rename=fail/worker exit1のまま記録する。

pure比較は親privateでもstage固定/証跡/全終了を行うこと、途中の親入替え、close不明、保持権限の変化、
不正policy、既取得親とは別のtarget-parent openを模した許否差を検証した。
初期29件のうち2件は、故障後finish()が元例外を再送出する期待漏れを修正し、29件pass/0.045秒。
記録済み最終172件pass/0.181秒、failure/error/skip/expected failure/unexpected success全て0。
initial-checks.jsonlを最終根拠とする。以後コード変更なし、同じ試験の重複実行なし。
コード・probe・監視・仕様の独立レビューは新規P0〜P3=0、read-onlyで進捗ポーリングなし。
25 source＋補助2 filesを記録raw/Git blobへ照合。repository safety/差分空白検査/PowerShell構文確認pass。

## 新規2条件の実Windows結果

clean exact HEADとsource/監視hashを固定し、新規artifacts/parent-policy-rename-2026-09-14/だけで実行した。
両条件ともfile内容45 bytes、元writer0x12019f、固定file0x160081、root0x1600a7/stage0x1700a1を保持する。
stage/fileは両方frozen、CWDは保持source-fixture rootとは異なる新規attempt親。
APIはNtSetInformationFile/class10/40 bytes、非NULL保持親・leaf payload、no-replace。API/名前/親のfallbackなし。

| 項目 | 条件1: 親private | 条件2: 親frozen |
| --- | --- | --- |
| root/stage状態 | private_verified/verified | verified/verified |
| 元ID/SD・実権限 | root元private SD不変、stage/file frozen、権限一致 | root/stage/file frozen、権限一致 |
| NTSTATUS/WinError | 0/なし | 0xc0000022/5 |
| rename状態 | confirmed | pendingのまま停止 |
| 終了後読取り | root/payload/factsの3 objectsが元ID/bytes/SDと一致 | 未実行、失敗source treeを再検査しない |
| tracked handles | source13＋sink14＋file1＋最終reader3＝31 close | source13＋sink14＋file1＝28 close |
| 照会token | 2個close | 2個close |
| worker終了 | exit0、外側0.454秒 | exit1、外側0.392秒 |
| 証跡 | prepare2817＋seal_payload2886＋verify_final2950＝8653 bytes | 2817＋2886＋3014＝8717 bytes |
| メモリ点観測 | 4境界、private最大18.03MiB/working26.04MiB | 2境界、private最大18.03MiB/working25.98MiB |
| stderr/資源停止 | 0 bytes/なし | 0 bytes/なし |

2は1の終了後に起動した。両方とも同期非pending返却でcompletion_unknown=false。
条件2のoperation.pendingは成功未確認を表し、nativeの処理継続を表す状態ではない。
親private/frozen以外の要求条件をそろえた新規fixture間の比較であり、ID/handle値や時刻は別になる。
親の固定と成否の差はこの環境で再現したが、内部target openの拒否箇所までtraceしていない。
既取得親のADD権限が残るだけでは、親frozen下のこのrename形式は成立しなかった。

最大2条件枠は終了。第3条件、繰越、再試行、前回batch/B1の再開なし。
条件1の成功sourceだけ追加の原bytes照合を行った。条件2と前回の失敗sourceは再検査・hash取得・再利用・削除していない。
親privateの時間帯のadd/delete拒否は確認しておらず、全保護の成功ではない。
marker file/.completeなし、journalはprepare unknown/stopped・teardown succeeded・commit not_started。
verify_final.jsonはrename前の第3証跡予約名であり、全model工程の完了に読み替えない。

## 保存記録・資源

新規ignored root artifacts/parent-policy-rename-2026-09-14/へ保存した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| initial-checks.jsonl | 124681 | 4b3cc498c2c47b88e4f4e04d23ee02df157130f02e7d8fd8f3119657cb049a03 |
| attempt-1/probe-result.json | 17178 | e0d6b51cc46adf5fe339350f10b2b67d8b08eba6f5e33bc9767c31ebd1563b85 |
| attempt-2/probe-result.json | 15909 | 41e1d5ee323857a8e0a32052eac8a1ac766fe8d39b57eaae6893312e84a33f94 |
| attempt-1/private-evidence/verify_final.json | 2950 | 2f44fe2f3b0a3ea2f0f2df88e50b998f6965976a47bc877fe203d553c74bead4 |
| attempt-2/private-evidence/verify_final.json | 3014 | 31efdcb89af5f3e88b2fddab38d475fdd4cd2efccae23731420eca3f8732b5fe |
| resources-final.json | 222 | 9c87e56df797e786e17cabf8391187bb9a2d85a4855ac5043e305f79a1aec7fe |
| savepoint-evidence.json | 13938 | 3949580d5f6b81787b7d9aad4d8bba10bd7101edc3b712b63ddd7975aa0ac93c |

manifest以外24 artifactsの論理bytesは226568。失敗sourceを走査せず既知の記録/証跡だけを収録した。
前回directory-rename manifestとその34 artifactsのhash不変を照合。論理bytesはdisk占有量ではない。

| 保存時刻（UTC） | 空きRAM GiB | C空き GiB | D空き GiB |
| --- | ---: | ---: | ---: |
| 開始前09:40:05 | 9.25 | 119.70 | 87.92 |
| 条件2前09:40:36 | 9.24 | 119.70 | 87.92 |
| 終了後09:41:28 | 9.25 | 119.70 | 87.92 |

build26200.9445/boot2026-09-09T10:43:08.5000000+09:00を記録し、Windows Update後のengineering緩和と正式pin不変を維持。
各workerは1秒未満で外側samples0。256/384MiBのprocess上限・空きRAM/disk2GiBの資源停止はなかった。
両worker・検証processは終了し、常駐処理なし。点観測は全期間最大値や長期リーク不在を証明しない。

## 次の設計候補

今回の結果だけでroot固定を名前変更の後ろへ動かす案は採用しない。
公式の同じ親内でのrename形式（直接NT、単一leaf、RootDirectory=NULL）が次の検討候補になる。
保持root自体は寿命/同一物検査のため残し、APIの名前解決をsourceの現在の親へ限定する形式を別adapterとして設計する。
文書上の形式は確認したが、親frozen下の成功・競合耐性は未検証であり、既定の保持親形式を変更しない。
固定leafとNULL親のwire、元source/親の結合、CWDが異なる条件、非上書き、故障後再送出なしをpure試験で具体化する。
新規仕様/review/source固定後の別枠とし、今回2条件に第3試行を追加しない。絶対path/失敗後fallbackも作らない。

それでも拒否される場合は、親private期間の競合・marker発行前の保護を含む順序案を具体化し、契約変更の判断点を示す。
既存6工程/S3 hardlink marker/D2契約、production入口、科学config/schema/registry、正式OS pin、本流889cfc3は不変。
marker/全publisher、独立token実操作、native故障/競合、正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
formal_permission/execution_authenticated=false、acceptance_status=not_completed。旧Linux CIへ件数加算なし。
push/merge/CI、新runtime、共有環境、別project、旧failure rootsへの操作なし。
