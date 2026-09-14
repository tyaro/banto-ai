# S4-B2 directory権限固定と相対renameの実機結果

2026-09-14。基準9375b3ee78f58a47a0580bda9c03480102611a80。
初回実装・実行 **a20988688e65d829a6619c399813da2a319d22a2**、修正実装・実行 **91cd5acfc29b9186739d3e99831f6f19ede08502**。

**最終167 tests pass。file/stage/rootのDACL固定・読戻しと証跡3個保存は両試行で成功したが、
相対renameは初回WinError87、修正後WinError5で失敗した。各28 tracked handlesとtoken2個をcloseし、worker終了を確認した。**
今回の最大2回枠は終了。directory rename成功・B2/S4受入は未達である。
[接続仕様・公式API資料・静的解析](../anomaly-v03-directory-rename-design.md)を参照。

## 接続・修正・検証

新規fixtureのrootを0x1600a7、stageを0x1700a1で最初から一つずつ取得する。
祖先保持は従来どおり。45 bytesのfacts.jsonをwrite/flush/照合し、prepare証跡保存後にwriterを閉じる。
payload-onlyを明示したSealedFilesで0x160081の短命世代を取得し、fileのDACL固定・読戻し後に証跡を保存して閉じる。
元writer・新世代の全子closeを確認してから、保持stage→rootの順にDACL固定と同一物/SD/実権限の検査を行う。
さらに証跡を保存し、保持rootを親に上書きなしstage→payloadを1回要求する。
workerのCWDは新規attempt親であり、保持したsource-fixture rootとは異なる。

初回Win32 wrapperはWinError87。インストール済みKernelBase.dllのexport/分岐/importを静的に読んだところ、
class3分岐はDOS名からNT名への変換後も入力RootDirectoryを複写していた。
絶対名への変換と非NULL親の組合せが87の原因という推定と整合するが、内部呼出しの動的traceはしていない。
解析対象のversion/hash/RVAは設計書と保存JSONに記録した。追加のrename試行やDLL関数呼出しは行っていない。

修正後は新規attempt-2でWindowsNtDirectoryBackendを明示選択し、同じ保持親・単一leafを
NtSetInformationFileへ直接渡した。FileRenameInformation=10、native buffer40 bytes、IO_STATUS_BLOCK16 bytes。
初回からの自動fallbackではない。非pendingの返却NTSTATUSを根拠に、失敗時はRtlNtStatusToDosErrorで変換する。
NT呼出し直前にcompletion_unknownを立て、正常な非pending返却の検証後だけ解除する。
返却喪失・STATUS_PENDING時は入出力bufferを保持したまま資源停止とし、所有終了後workerをexit80で終える。
この中断時寿命について独立レビューのP2を1件修正し、再レビューの新規P0〜P3は0件。
本体およびscenario/監視/仕様の先行レビューも各新規指摘0、全てread-onlyで進捗ポーリングなし。

初期部品確認ではowned import漏れによる12 NameErrorを修正し、54件pass/0.068秒。
記録済み初回162件pass/0.220秒、NT切替後166件pass/0.218秒、寿命修正後の最終167件pass/0.366秒。
最終は新規24＋既存143、failure/error/skip/expected failure/unexpected success全て0。
final-checks.jsonlを最終根拠とし、実装変更後の同じ試験の再実行は行っていない。
初回24 sourceは初回Git blob、最終24 sourceと補助2 filesは修正Git blob/rawへ照合した。
166件の中間記録は当時のraw hashを保持し、最終Gitと一致したとは扱わない。
repository safety・差分空白検査・監視PowerShell構文確認はpass。

## 2回の限定実機結果

clean HEAD・source hash・監視hashを固定し、新規artifacts/directory-rename-2026-09-14/の各attemptだけで実行した。

| 項目 | attempt-1 | attempt-2 |
| --- | --- | --- |
| 実装 | a209886、SetFileInformationByHandle/class3/36 bytes | 91cd5ac、NtSetInformationFile/class10/40 bytes |
| rename結果 | BOOL0、WinError87 | NTSTATUS0xc0000022、WinError5 |
| file/stage/root固定 | 全てverified | 全てverified |
| root/stage実権限 | 固定前後0x1600a7/0x1700a1一致 | 固定前後0x1600a7/0x1700a1一致 |
| private証跡 | prepare2817＋seal_payload2886＋verify_final3014＝8717 bytes | 同じ3サイズ、別の実観測hash |
| 所有終了 | source13＋sink14＋file1＝28 handles、token2個close | 同じく28 handles、token2個close |
| worker | exit1、1.208秒、資源停止なし | exit1、0.441秒、資源停止なし |
| stderr | 0 bytes | 0 bytes |
| 終了後source検査 | 未実行 | 未実行 |

両方ともoperation.renameはpendingのまま停止し、後続IOを実行しなかった。
attempt-2のnative pending=false/completion_unknown=falseは、失敗の同期応答を受け取れたことを表す。
operation側pendingはrename成功を確認できなかった状態であり、非同期処理が継続中という意味ではない。
IOSBは初期値0xffffffffのままだが、非pending返却NTSTATUSを採用する仕様に従う。
親DACLを先に固定したため内部target openが拒否された可能性がある。保持親にADD権限が残るだけでは
renameの成立を示せないことは観測したが、拒否原因を一変数の比較で分離した証明ではない。

証跡のverify_final.jsonは既存sinkの第3予約名を使ったrename前記録であり、rename後検証の成功記録ではない。
marker file/.completeは作成していない。journalはprepare unknown/model stopped、teardown succeeded、commit not_started。
終了後読取り用3 handlesは取得せず、postclose一致数0。失敗source treeの再検査・hash取得・再利用・削除をしていない。
初回記録もそのまま保持した。3回目、既存batch/B1枠の再開は行わない。

## 保存記録と資源

新規ignored root artifacts/directory-rename-2026-09-14/へ原記録、静的解析、監視、資源値、manifestを保存した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| initial-checks.jsonl | 117422 | cf7269249d2b9568f33516189e1cd592fb712a9621b933ce3dcc14948370a42d |
| corrected-checks.jsonl | 120162 | c12c28f5a9bb5d8e225817b82292f4ab41fac500e1c5d755cb41f93e2017ba95 |
| final-checks.jsonl | 120883 | c22784dfc37249bd233229ff3ac148ab53cb311b7f3e0737fe2787ec5491ba26 |
| attempt-1/probe-result.json | 15584 | 7428e3078436bb1f0c373b8323e75bc45732d40ce688ab1f2a3307dd2e2dff7a |
| attempt-2/probe-result.json | 15815 | e140067e2c9bf35b1c4c12bbf9624d023f309a661a5f56302f862191d34b34c8 |
| attempt-1-evidence.json | 2048 | 78951ff22e251f13801654d7e6f51116fbf11f539e46be3873db172d757863d4 |
| resources-final.json | 223 | e983f35ecd4a79e57e6dda9a8c0ff7b014988ec01a640b6f435922755a9ffbac |
| savepoint-evidence.json | 27893 | 4aa5e974f3211bf328c2c388818c01f0fcdf0eeff3df18562568280ad91edfbe |

manifest以外34記録の論理bytesは548113。失敗source treeを走査せず、明示したreport/証跡だけを収録した。
初回receiptの12 artifactsと、前回file-sealing manifestの15 artifactsが不変であることも照合した。
論理bytesはdisk占有量ではない。

| 保存時刻（UTC） | 空きRAM GiB | C空き GiB | D空き GiB |
| --- | ---: | ---: | ---: |
| 初回前09:08:09 | 7.40 | 119.67 | 90.94 |
| 2回目前09:21:30 | 9.50 | 119.70 | 87.92 |
| 終了後09:22:23 | 9.49 | 119.71 | 87.92 |

build26200.9445/boot2026-09-09T10:43:08.5000000+09:00を記録。Windows Update後のengineering緩和を維持し、正式OS pinは不変。
各workerは2境界のみ観測。初回private最大18.71MiB/working26.61MiB、外側1 sampleのworking26.68MiB。
2回目private18.68MiB/working26.60MiB、外側は1秒未満でsamples0。256/384MiBのprocess上限・空きRAM/disk2GiBを超える停止なし。
試験worker・短い検証processは終了し、常駐処理を追加していない。空き容量変化の原因は未調査で、本作業へ帰属させない。
点観測は長期リーク不在・全期間最大メモリの証明ではない。

## 次の作業

親をfrozenにしてからrenameする現在の順序は成功していない。次は親保護と名前変更の順序を再設計する。
まず同じrelative NT要求について、親private/親frozenの違いを切り分ける小さい仕様を作り、
親をprivateに保つ時間帯のadd/delete競合と、marker commitまでに要求する保護条件をpure modelへ反映する。
root固定を後ろへ動かすだけで全公開を安全とみなしたり、絶対path/NULL親へ自動退避したりしない。
既存6工程model・S3 hardlink marker・D2 rename契約を変更する必要性は別途具体化する。
今回枠は閉じており、新たなnative比較は新規仕様・review・source固定の後の別枠となる。

独立token実操作、rename後同一物検査、後続phase証跡、marker/全publisher、実native故障/競合、正式OS整合、VM digest、
runtime closure/consumer、S4受入は未完了。formal_permission/execution_authenticated=false、acceptance_status=not_completed。
src/科学config/schema/registry/正式pin、本流889cfc3不変。旧Linux CIへ件数加算なし。
push/merge/CI起動、新runtime/共有環境/別project/旧failure roots操作は行っていない。
