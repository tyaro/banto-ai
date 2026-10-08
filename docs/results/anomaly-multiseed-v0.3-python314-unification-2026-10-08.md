# Python 3.14固定への改訂

2026-10-08の人の「了解です。3.14固定で構いません」に従う限定作業。開始2026-10-08T11:21:36Z、HEAD2e36bf8a18a8429e0c2f15bbb1e50ff83cebde12/origin一致・clean。停止時の元3helper creation同original不在/repo helper・critical ownerなしをread-only CIMで確認。heartbeat banto-10はPAUSEDを維持する。追加agent/業務worker/native/登録holdout観測0。

## 変更

- pyproject.tomlは>=3.14,<3.15。3.14系へ限定し、CIは3.14系の実patch/buildを記録する。
- Ubuntu 24.04のtest job一つとverify-python314-journalを使用。3.12 job、旧版間比較、3.12 artifact downloadを外す。
- 新tools/ci_verify_python314_journal.pyは外部fullHEAD/workflow/run/attempt pinと実3.14 ABI、全journal完了・共有29fixture owner/digest/canonical inventory・必須28ID・正確なskip理由を確認する。新format ci-python314-journal.1。cross_python_comparison_performed=false、execution_authenticated=false、acceptance_status=not_completed/formal_permission=falseを維持する。
- 現inspection receiptはs4-a.3と別v2 schemaへ更新し、linux-3.12必須要件を外す。旧s4-a.2/v1 schemaの形とbytesを保持し、版を明示して履歴だけを読める。旧2journal comparison/regression toolsも変更せず保持する。
- collectorの新3.12呼出しはpath/native IO前、CI reportはdiscovery前に拒否する。Windows正式runtimeのCPython 3.14.0/build/hashと科学的な式・seed・登録config/科学schemaは変更しない。
- 評価計画のplatform必須条件とREADMEを同判断へ同期。過去の3.12/3.14証拠は元source/runtime/runの記録として保存し、新revisionの合格へ読み替えない。

## 今回の確認

最初の対象13試験は一回1.5574426999664865秒、fail0/error0/skip0。新singleton journalの正常入力、3.12/3.13/3.15拒否、外部pin不一致、必須ID不足・未承認skip、partial/重複fixture/failure、CLI入力数、新旧schema、active receipt、reportの版拒否を確認した。focused.log2512B/92f0d85a93dd29bbe15d58284e941172b81dccd8951376ba9d32890cf0579730。

reviewでcollector早期拒否を追加し、新1だけ一回0.7683391000027768秒pass。focused-v2.log293B/19dc8843ec767dbed4586b48749f01e6c5b3e65673eca53b981620f80da924aa。先の13は再実行しない。別source/runで最終source単一14successではない。synthetic journal/宣言runtime/純粋schemaと小temp FileIOのengineering確認で、実Linux runner/実Win ABI/native/全経路wall/容量認証ではない。full suite・旧CI raw・完成focus・実profile再観測0。

専用artifacts/python314-unification-20261008-prep/（512KiB32entry/reserve128KiB/single128KiB）へ原helper identity/live/execution/選択/log/source metadataを保全し、code/docを同unit一回commit/pushする。旧閉鎖raw rootへ追加・整理・上限緩和0。変更後の3.14 CI終端結果は未確認。正式受入未完了/formal_permission=false/credit0/登録holdout観測未読とPAUSEDを維持する。
