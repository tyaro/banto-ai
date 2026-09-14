# S4-B2 固定済み親内のNT leaf rename結果

2026-09-14、基準7aa4d30e65b8adef7e5e61c916a1ac4a2b6d0495。
実装・限定実機savepoint **685d670499cdc42e72d3f3ab948349fea2f4281c**。

**新規10＋既存172＝182 tests pass。親/子のDACL固定・証跡保存は成功したが、
NULL RootDirectory＋単一leafの同一親内renameもNTSTATUS0xc0000022/WinError5で拒否された。**
28 tracked handles/token2個close、worker終了を確認した。1回枠は終了し、追加試行は行わない。
[設計・公式API資料](../anomaly-v03-same-parent-rename-design.md)と[前回の親policy比較](anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md)を参照。

## 実装・検証と作業領域の分離

SameParentDirectoryRenameは既存DirectoryRenameの親/source結合、全子close、DACL固定、同一物/SD/権限、証跡後検査を継承する。
parent_policy=frozenを固定し、要求だけをNULL RootDirectory/固定payload leafにする。
専用WindowsNtSameParentBackendはこのwireだけを受理し、既定の保持親backendとは相互に異なるwireを拒否する。
native class10/40 bytes、IOSB16、completion_unknownとbuffer寿命・資源停止は共用する。
probeのsame_parent modeは親private比較と併用できず、entry/監視ともattempt-2を拒否する。
旧encoder/BoundRename/6工程/S3/D2/productionは不変、API/親/名前の自動fallbackなし。

部品39件pass/0.041秒、記録済み最終182件pass/0.186秒、failure/error/skip/expected failure/unexpected success全て0。
固定wire/ABI、異種wire拒否、親結合、子close不明、証跡後の親入替え、同名衝突、返却喪失、pending/中断時buffer保持を確認した。
initial-checks.jsonlが最終根拠。以後コード変更なし、同じ試験の再実行なし。
実装・probe・監視・仕様の独立レビューは新規P0〜P3=0、read-only、進捗ポーリングなし。
repository safety/差分空白検査/PowerShell構文確認pass。

元candidateでclean検査を行った際、今回の変更対象外である前回親policy結果書に作業差分を検出した。
起動前の検査で停止したため、その領域ではworkerを起動していない。文書差分を上書きせず原bytes/patchを保存した。
同じ685d670のclean detached checkoutを作成し、実機だけ次の領域で実行した。

`C:\Users\TKent\.codex\worktrees\same-parent-685d670\banto-ai`

テスト実行は元70b0、native実行は上記である。28 source＋補助2 filesのraw bytesが両領域とGit blobで一致することを照合した。
native側もclean exact HEAD・監視hashを固定した。これは文書差分を試験の実装変更へ混ぜずに保存するための分離である。
追加checkoutはtracked448 files/論理5603301 bytes。共有Git領域・filesystem占有量や全追加disk量を表す値ではない。
元の文書編集差分は保持しており、今回のcommitへ含めない。

## 1回の限定実Windows結果

| 項目 | 結果 |
| --- | --- |
| 新規構造 | source-fixture/stage/facts.json45 bytes、別private-evidence。marker file/.completeなし |
| 取得権限 | writer0x12019f→file0x160081、root0x1600a7/stage0x1700a1 |
| 固定 | file/stage/root frozen、同一物・SD・固定前後保持権限の照合成功 |
| API | NtSetInformationFile/class10/40 bytes、source_parent、NULL RootDirectory、固定payload leaf、no-replace |
| 結果 | NTSTATUSとIOSBとも0xc0000022、WinError5。native非pending/completion_unknown=false |
| operation | directory_statesは両方verified、evidence=saved、rename=pendingのまま停止 |
| 証跡 | prepare2817＋seal_payload2886＋verify_final3014＝8717 bytes。いずれもrename前 |
| 所有終了 | source13＋sink14＋file1＝28 tracked handles、query token2個close、teardown succeeded |
| worker | exit1、外側0.562秒、stderr0 bytes、資源停止なし |
| 終了後source確認 | 未実行。最終reader0/postclose一致0。失敗sourceの再検査・hash取得・複製・再利用・削除なし |

CWDは新規attempt親で、保持source-fixtureとは異なる。今回はrename自体が拒否されたため、名前解決成功の実機証明ではない。
非NULL保持親とNULL同一親内の両形式が親frozen下で失敗したが、内部の拒否箇所までtraceしたものではない。
IOSBに返された同値から内部処理箇所を断定しない。API形式だけで解消したとは扱わない。
journalはprepare unknown/stopped、teardown succeeded、commit not_started。第3証跡の予約名をmodelのverify_final成功にしない。
最大1回枠は終了。旧batch/B1の再開なし。正式受入・全publisher・独立token/実衝突/競合の成功ではない。

## 保存記録と資源

元candidateのignored artifacts/same-parent-rename-2026-09-14/へ試験記録・文書差分・manifestを保存した。
native原記録は別checkoutの同名artifacts rootに残し、明示した10記録だけを元側のnative-run/へ複製して一致を検証した。
失敗source treeは複製も走査もしていない。前回親policy manifestと24 artifactsのhash不変も照合した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| initial-checks.jsonl | 132318 | ed7c7bf5b7474c7ff324e2a7c9a1034552cf7ea260ae7246786967587aac58bd |
| native-run/attempt-1/probe-result.json | 16094 | d85a51af8efa6baa275986f8e383909c9b6282959848b50353c5eef9a3a12f5a |
| native-run/attempt-1.supervision.json | 521 | ade67f2b234ac8b1d10b9582548a41c921850455249de0dc805a0a44e9866897 |
| native-run/resources-final.json | 223 | 1f41da9ecee6b6ecf8f949932c34f3aa7a95b57d27143665bdf54fb6c302d7a5 |
| workspace-isolation.json | 528 | b4a4d3f74b0adc2ac1fe52d1299b637bb287bf3ad6766bdf049b5b34824c27a1 |
| savepoint-evidence.json | 11246 | e3eba37e48436c02918e4214d8417f410b1932992c0c375a06d60b584979b719 |

manifest以外18 artifactsの論理bytesは219345。native側に保持する原記録やcheckoutを含む総disk占有量ではない。
文書の保存原bytesは8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621。

実機前UTC10:24:10 RAM13.44GiB/C119.18GiB/D76.44GiB、終了後10:27:17 RAM13.49GiB/C119.17GiB/D76.44GiB。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和・正式pin不変を維持。
worker2境界でprivate最大20.79MiB/working28.04MiB/peak working35.24MiB、外側は1秒未満でsamples0。
worker・検証processは終了、常駐処理なし。資源上限での停止なし。点観測は長期リーク不在・全期間最大値の証明ではない。

## 次の設計作業

[未採用の順序案](../anomaly-v03-publication-order-options.md)に、親private中のpayload rename→親固定→最終検査→
予約した空markerへ保持writerでwrite/flush/closeする候補と、consumer/故障条件をまとめた。
独立レビューP2で別actorが固定前に取得した親の追加/DELETE_CHILD等の残存権限が指摘され、
sealでその権限を消去しないmodel、検査後/公開後の変更、隔離根拠不明なら保護済みcommit不可を追記した。
再レビューの新規P0〜P3は0。これは案の限界を適切に記録した確認であり、方式の成立・採用の認定ではない。

次は残存権限を含む小modelとconsumer条件を具体化する。別actorを脅威範囲から除外せず、
事前取得を防ぐ/隔離する条件が固まるまで、この候補のnative実装へ進めない。
既存6工程/marker/S3/D2契約を黙って変更せず、正式契約に触れる点を具体的な判断材料にする。
全publisher、独立token、native競合/故障、正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
formal_permission/execution_authenticated=false、acceptance_status=not_completed。src/科学config/schema/registry/正式pin、本流889cfc3不変。
旧Linux CIへ件数加算なし。push/merge/CI、新runtime/サービス/account、別project、旧failure roots操作なし。
