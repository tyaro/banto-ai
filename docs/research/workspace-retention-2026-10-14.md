# 方向転換後のファイル整理とMacへの移行範囲（2026-10-14）

## 完了した削除

人の「旧研究の証拠はもういらない」に従って対象を具体化し、以前の閉鎖root/原証拠保全指示を変更する範囲を確認した。人は、913フォルダ＋26単独ログ・41,450files・3,462,579,416bytesの対象一覧へ「この対象をバックアップなしで削除する」と明示回答した。その一覧だけを一回削除した。

|対象|今回の扱い|
|---|---|
|旧C0/C1/C2合成評価・seed/layout解析の記録|対象一覧にあるrootを削除|
|旧異常検知・Windows受入準備・旧CIの証拠|対象一覧にあるroot/単独ログを削除|
|`data/archives/retired-anomaly-evaluation-20261014/`|約243MBの旧C0保管archiveも削除。追加backupなし|
|現在の需要研究、公開原本、Gitのsource/tests/docs|保持|
|未分類のartifact、登録済み/アクセス保護領域|対象外として保持|

約3.46GBは削除したfileの論理bytes合計で、hardlink・filesystem・他の同時活動を含むdrive空き容量の増分を測った値ではない。削除した原ログ・中間入力・旧archiveはこのworkspaceから復元できない。集約報告やsourceはGitに残るが、それだけで失われた原証拠の再検証をできるとはしない。

## 残すものとMacへ移すもの

最新需要研究の最小artifactセットは、最新引継ぎが指定した26root・8,663,838bytes（約8.66MB）。これは最新3模型/input rootと、今回の学習・診断・Astraレビュー・引継ぎのprep/recordsを含む。需要研究の全過去記録の容量ではなく、最小セットの調査値である。具体rootは[Mac引継ぎ](pc-handoff-2026-10-14.md)を参照する。

- コードと文書：Gitの最新branchから取得する。旧source/tests/docsは今回削除していない。
- 主入力：`data/public/store-sales-user-provided-20261014/` をmanifest/parts/closureごとコピーする。
- 最新研究の入力・結果・weights：Mac引継ぎの最小artifact rootを**全体ごと**コピーする。
- 油圧/Online Retail II等の公開原本：Windows側で保持。需要研究の当面のMac最小移行には含めなくてよい。
- 旧Windowsのvenv/cache：Macへコピーしない。Mac専用環境を作る。
- 登録済み保護領域・未分類の旧artifact：このPCに保持。需要研究の最小移行には含めない。

workspace全体の一括コピーは、現在の需要研究を進めるための必須工程ではなくなった。最新研究の26rootもraw予測・尺度・weightsを含むのでGitへは送信しない。Mac側でのコピー受領・hash照合・runtime移植はまだ実施していない。

## 調査で分かった内訳

削除前のmetadata調査では、読める範囲でartifacts約3.44GB、environments約736MB、data約388MB、docs約7MBだった。登録済み/保護領域28pathとGit内部は除外したため、これをworkspace/drive全体の完全な使用量とはしない。artifactsの直下には単独CIログもあり、directoryとfileを区別して削除対象を固定した。

現在の需要entrypoint3件から静的に辿ったlocal Python moduleは17file/158,034bytes。これは動的import・tests・外部APIを含む完全runtime閉包ではなく、辿られなかったsourceを安全に削除できる証明でもない。sourceの整理と大きい旧証拠の削除を混ぜていない。

## 削除の検証・保存

承認済み一覧は `artifacts/representative-old-evidence-delete-plan-v2-20261014-records/deletion-targets.000001.part`、222704bytes/SHA256 `9d62e0a16b6826213c6ed3fb599de8259c2f5da0c04db0f54a3ab33d107b6d28`。このpinと対象数/bytesを削除前に固定した。

PowerShellで全939entryの絶対pathがworkspace内の指定artifact直下又は指定旧archiveと一致すること、重複なし、reparseなし、全41,450file/bytesが一覧どおりであることを**全件削除前に**確認した。登録/current demand/公開原本は対象に入れず、ACL変更0。列挙とRemove-Itemは同じPowerShellで行った。全指定target不存在を確認した。

需要/store-sales/引継ぎartifactと `data/public` の全保存fileについて、relative path・bytes・mtime一覧が前後一致。Gitのsource/docsは削除対象外。元指定target以外のmodel/確認/CI実行0、native回収claim0、formal_permission=false。実行28.875194秒、sampled private最大90,435,584bytes、全PowerShell stdout/stderr/exit0と各削除entryを新EvidenceStoreへ判定前保存。sampled checkpointをblocking/global/native容量保証へ読み替えない。

旧保全指示の変更はこの承認済み一覧だけであり、他の閉鎖rootの削除・追記を一括許可するものではない。研究とautomationはPAUSED、Macへ再開する研究は別の未完成unit。全実行/記録/prep/Git上限、登録holdout未読/native7役禁止/credit0/正式受入未完了/CARE手動待ちを維持する。

調査は `representative-workspace-retention-audit-20261014-records`、削除計画は `representative-old-evidence-delete-plan-v2-20261014-records`、承認/実削除/全stdioは `representative-old-evidence-delete-20261014-records`、本文照合は `representative-workspace-retention-doc-20261014-records`、Git後は同retention-git-records/post-saveを優先する。新閉鎖rootへの追記0。

初foreground集計は旧登録rootのAccess deniedで未完了、次のmetadata調査では登録scopeを読まず除外した。初計画は単独CIログをdirectoryとして扱うassertで削除開始前に失敗。原script/selected tool errorをv2へ保存し、file/directoryを分けて一覧を完成した。原foreground full stdioは未捕捉と明記し、失敗を模型/CI/nativeへ補わない。
