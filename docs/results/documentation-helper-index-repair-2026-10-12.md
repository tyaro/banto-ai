# 文書helperの索引更新修正（2026-10-12）

## 確認した原因

layout8 C2 qualityの文書source変換は、前回リンクを含むPython source文字列を厳密一致で置換していた。探した文字列はリンクlabel直後でquoteが閉じ、実sourceはURL開始括弧を含むため一致しなかった。索引件数も前回templateから固定していた。今回の直接原因はsource文字列の不一致で、docs移動先pathの不在ではない。docs/results/README.mdと結果報告の配置は継続しており、tracked toolsにはこの索引置換処理はなかった。

元selected errorは閉鎖済み保存rootのsource-builder-failureに保持する。変換はnested tools/process/tracked mutation/Git helper開始前で停止した。今回も元scriptやモデルを再実行していない。

## 修正

- [update_results_index.py](../../tools/update_results_index.py)を追加。sectionを件数なしで探し、実リンク数から件数を作る。
- 現在の索引/報告pathから相対URLを作り、日本語・空白・丸括弧をencodeする。
- pending UTF-8報告を受け、既存報告の上書き、重複・衝突・不在見出し・壊れた項目を文書書込み前に拒否する。同じ登録は重複追加しない。
- 新しい参考templateの索引処理を共通helper呼出しへ更新して新rootに保存。旧runに結び付く全templateは実行していない。
- [使用手順](../anomaly/execution/documentation-helpers.md)に新文書生成の呼出しを記載。
- docs入口の古い再開予定/layout6一時停止参照を、ACTIVEと現在の引継ぎ・結果索引への案内へ更新。

helperは候補bytesを返す。CLIはdiff/読取り確認だけを行い、書込み/Gitは既存の容量照合とEvidenceStoreを使う。閉鎖/外部固定artifact、固定計画・科学config・元評価結果を変更しない。

## 新規確認と失敗保全

初回新規6methodsはsandboxの既定一時folderでfixtureのmkdir/cleanup権限エラーとなった。6setup/cleanup error12、本文0、helper failedを原log/summary/例外と共に保持。fixture保存先だけworkspace内artifactsへ訂正し、未完了6methodsを新rootで一回6pass/failure0/error0/skip0。初回failedを書き換えていない。権限エラーをモデル/CI/native/Sol容量失敗へしない。

移動した報告path、Unicode/空白/括弧、件数drift、idempotence、見出し不在/重複、link重複/衝突、pending報告の上書き/UTF-8/docs外拒否、壊れた/外部リンクを確認。現在dev索引48linksの既存登録もAPI/CLI --checkでbytes不変・exit0。reviewでUTF-8 CLI差分と空sectionの空行保持の新2methodsだけ一回2pass。CLI stdoutをUTF-8 bytesへ固定し、空sectionの見出し/list間の空行を整えた。全8distinctは6+2の別source/runで、最終source単一8試験successとはしない。旧評価・replay・完成試験・完成CI再実行0、追加agent0。

修正報告のJS source構築でもMarkdown backtickがtemplate literalを閉じるSyntaxErrorが一回発生。isolate評価前/nested tools-process-tracked mutation0、元sourceのFS保存なし/selected error保持。instrumented helper failureへ追加せず、別source構築で未実行の文書保存だけ継続した。

保存後metadataの初回-finalは旧cache補足の参照rootをlayout6qualityへ取り違えFileNotFoundError/exit1で停止。元script/失敗/creation/閉鎖状態を保持。元保存sourceの正しいlayout1coreC2参照へ別continuationを作り、未完了metadataだけ保存。元Git/helper/モデル/試験/CI再実行0。Git code修正6b69a82の成功を変更しない。初回-post-saveはhandoff全履歴の同文字列14件を一件と誤要求し書込み/Git前AssertionError、原failed保持。最新sectionだけへ対象を限定した別-post-save-continuationで未保存doc追補だけ完了。最終-final-continuationを優先。

## 保存と次の作業

新記録 artifacts/docs-helper-repair-20261012-prep、-tests（failed）、-tests-continuation（passed）、-save、-git、-final（failed）、-post-save（failed）、-post-save-continuation、-final-continuation。各閉鎖manifestと順序付きpartを優先。新記録16MiB/512files/part256KiBと失敗予備枠を維持。Git原stdout/stderr/exitと対象pinは-git、保存後metadataは-final。保存整合性をモデル性能や正式受入へしない。

次dev unitはlayout8 quality C0、新ID dev-layout8-quality-c0-20261012。今回未実行。入力と原保存状態は[直前C2報告](anomaly-multiseed-v0.3-layout8-c2-quality-evaluation-2026-10-12.md)とcurrent-handoffを参照。新文書生成からprepare_result_indexを使い、件数/前回リンクを含むsource置換を再利用しない。

実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry512KiB/stdout1MiB/stderr128KiB、protocol/native制限維持。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0、holdout未読・正式5残件/最終受入未完了・create_native早期拒否/7役reader禁止。ACTIVE。Sol容量又は人停止は原証拠保全後PAUSED、重複再試行なし。
