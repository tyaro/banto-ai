# 解析の保存出力を通常公開し、別readerで確認する

2026-09-26 JST、実装 `f8f20bcf4ac7ade2f20e96f37bc1567328d88a48`。[検証結果](results/anomaly-multiseed-v0.3-analysis-publication-chain-2026-09-26.md)、[analysis API](anomaly-v03-analysis-evidence.md)、[reader API](anomaly-v03-reader-evidence.md)。

## 対象と呼出し

profile付きanalysisで準備・照合済みの4payloadを、そのまま既存LocalPublicationへ渡す。対象はengineering-dev-smokeの保存済み記述結果だけ。writer終了後、通常権限の別processで元入力と公開結果を比較する。

```python
from banto_ai.anomaly_v03_analysis_publication import publish_and_check

result = publish_and_check(
    absolute_profiled_analysis_directory,
    expected_mode="engineering-dev-smoke",
    expected_analysis_result_pin=retained_analysis_result_pin,
    expected_revision=full_current_candidate_commit,
    output_parent=existing_publication_parent,
    output_name="new-descriptive-publication",
    receipt_parent=existing_separate_receipt_parent,
    receipt_name="new-publication-check",
)
# resultのstatusとreader_exit_confirmedを確認し、result_pinを外部で保持する。
```

解析result pinは呼出し側が前工程で保持したものを渡す。検査対象のresult.jsonを読んでその場でpinを採用しない。元の7保存入力は存在している必要がある。profileなしreference、失敗・未終了analysis、role違い、別revision、変化したpayload/原本は公開前に拒否する。出力/確認先は互いに独立した新規directoryに限定し、元入力/source/analysis directoryとの重複と既存attemptを拒否する。

## 証拠のつながり

1. 外部analysis result pinから固定名のevidence/binding/profile binding/profile/dependencies/stdout/requestと4payloadを認証する。
2. profileのrole/operation/root/revision/runtime・前後依存の一致を検査し、過去の終了済み解析証拠を再利用する。元7入力から準備した期待bytesとstage実bytesを比較する。数値再計算は行わない。
3. analysis selected source13と接続module1本のGit/raw一致を確認し、保持した4payloadをsingle writerで公開する。
4. writerを閉じ、公開markerを保持してreadbackを確認する。別の確認directoryへpublication-binding.jsonを保存してpinを保持する。
5. 既存observed readerを`-I -S -B`で起動し、元入力・4payload・markerを親の保持期待と比較する。元Popen handleによるexit0/回収/観測errorなしを確認する。
6. 元の解析記録・payloadとpublication-bindingの不変性を再確認し、reader結果pinとともにchain resultを保存する。

public payloadは4fileのまま。publication-bindingは解析result/evidence/profile/profile-binding pin、4payload pin、公開root/marker、revisionと接続module pinを持つ。chain result_pin→publication_binding_pinとreader_result_pin→各保存記録の順に参照する。markerだけで解析とのつながりを受入にしない。

readerは従来のsource10/Python2file/15入力の結合と補助依存採取を使い、この入口でreader専用候補を自動作成しない。analysis候補をreaderへ渡さない。writerの全実行観測や完全なsource/runtime固定は未完了である。

## 結果と失敗時

成功statusは`analysis_publication_reader_verified`、publication_status=completed、reader_exit_confirmed=true。4payloadの通常公開を示す。formal/promotion/S6/trust/execution_authenticated/full closureはfalse。数値の独立検算や正式document_draftへの認証ではない。

書き込み開始後に戻り値を得られない場合はunconfirmedとし、部分出力や完了済みの可能性を残す。削除・再実行・再公開を自動で行わない。公開後のreader失敗はcompletedの公開を保全し、chain全体をfailedにする。未終了readerは元ownerを保持したUnreapedWorkerとして返し、呼出し側が同じownerを回収する。記録保存失敗でもownerを隠さない。

親のpreflight失敗は例外で返し、出力先を作らない。開始後の失敗は記録を残すが、結果記録自体のIO失敗は例外となる。再開や上書きはしない。各工程は呼出し側が直列に実行し、敵対的な同時writer/別principalの保護は対象外。

子の上限は各30秒/private512MiB/観測stdout+stderr1MiB。4payload合計8MiB以下、候補512KiB、固定証拠には各64KiBまたは1MiBの読取上限を適用する。親の全工程時間・保存directory全体を含む正式総予算は未確定。次は、既存dev/smokeの保存済み記述レポートへこの一連の処理を適用し、外部anchor・解析証拠・公開marker・別reader結果を保存する。720評価は再実行せず、数値の正式受入やholdoutへ範囲を広げない。

## 保存済みレポートへの適用（2026-09-26）

実装を変更せず、既存dev/smokeの原本7file/7,896,608bytesへ適用した。4payload/2,755,533bytesとmarkerが旧公開に完全一致し、原本・旧公開は不変。解析子/reader子は正常終了し、約27秒で完了。前回43試験のsource pin不変を確認して再利用し、試験suiteや720評価を再実行していない。[保存結果](results/anomaly-multiseed-v0.3-saved-report-publication-2026-09-26.md)。正式数値受入・独立auditは含まない。
