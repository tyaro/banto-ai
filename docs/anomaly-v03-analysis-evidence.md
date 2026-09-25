# 保存済み記述結果を準備するanalysis役割の実観測

2026-09-26 JST、実装 `2db441e44a65857f288f800a104ba436339358b9`。[検証結果](results/anomaly-multiseed-v0.3-analysis-observed-evidence-2026-09-26.md)、[共通の証拠validator](anomaly-v03-consumer-evidence.md)、[source/runtime計画](anomaly-v03-consumer-source-runtime-plan.md)。

## 対象の処理

analysis役割のうち、既存engineering consumerが行う保存済み結果の認証・出力準備を対象とする。operationは`prepare-saved-descriptive-result`。元のwriterが終了した後、通常権限で7保存fileを認証し、report JSON/Markdown/HTMLとconsumer receiptの4payloadを新しい確認directoryに作る。

数値集計、score、bootstrap、登録観測データの再読取は行わない。過去の数値検証記録を再利用する。確認directoryのpayloadは準備結果であり、LocalPublicationの完了markerや正式文書は発行しない。

```python
from banto_ai.anomaly_v03_analysis_evidence import prepare_with_evidence

checked = prepare_with_evidence(
    {
        "format": "anomaly-v03-observed-analysis-request-v1",
        "mode": "engineering-dev-smoke",
        "role": "analysis",
        "operation": "prepare-saved-descriptive-result",
        "binding_savepoint": absolute_binding_path,
        "report_savepoint": absolute_report_path,
        "analysis_input": absolute_input_path,
        "expected_binding_pin": retained_binding_pin,
        "expected_report_pin": retained_report_pin,
    },
    expected_revision=full_current_candidate_commit,
    receipt_parent=existing_separate_parent,
    receipt_name="new-analysis-check",
)
```

mode/role/operation・未知欄をIO前に検査する。reader/auditの役割やreader profileをこのrequestへ入れられない。保存先は入力/sourceに重ならない新規directoryで、既存attemptを上書きしない。

## 親が保持する期待値と子の観測

親は指定Git revision/raw source12本とPython executable/loaded Python DLLの内容、host実値・起動条件、外部anchorで認証した7入力を保持する。保存結果を準備する既存関数を親でも呼び、子へ期待する4payloadのbytes/pinを先に確定する。数値の独立検算ではなく、保持した同一処理の期待bytesとの比較である。

子は`-I -S -B`でanalysis専用入口を起動し、request解読後、出力準備・保存の前後でsource/runtime/import origin/loaded image/入力を観測する。requestとinvocationも含む9入力と4出力をevidenceへ結合。子が保存したpayloadを親の期待pinと比較し、余分なfileを拒否する。

supervisorの元Popen handleと子自身のPID/生成FILETIMEを比較する。親のメモリ保持値を基準にし、保存launch/expectedや子が返したhashから期待値を再採用しない。親がexit0・終了回収・観測errorなしを確認してから、expected_role=analysisで共通validatorを使う。UnreapedWorkerは記録保存に失敗しても元ownerを保ったまま返し、未終了workerの出力を読まない。

source12/Python2fileを事前期待へ結ぶ。全依存の補助記録は実子の一覧を親が終了後にdisk/Gitと照合する方式で、まだanalysis専用の事前profileではない。今回の実観測はsource29を含む233file。collectorの低水準処理をreaderと共有するが、role/operation/command/期待出力はanalysis専用に保持する。

## 保存と上限

成功時はpayload/4file、analysis-request、invocation、source-tool、launch、expected、supervision、worker stdout/stderr、evidence、binding、dependencies、dependency-crosscheck、resultを保存する。失敗時は途中の出力を保全し、bindingの成功扱いをしない。元入力へは書き込まない。

子の監視は30秒/private512MiB/stdout+stderr1MiB。準備payloadはreport.json4MiB、Markdown1MiB、HTML2MiB、receipt1MiB、合計8MiBを生成・保存前に検査する。入出力のbyte数を別に記録する。payload側の上限はchild/parentの検査で、supervisorによる全directory容量監視や正式な総予算ではない。親のGit呼出しは各10秒で、親preflightを含む正式全体予算は未確定。

formal/promotion/S6/trust/execution_authenticated/full closure=false、numerical_analysis_performed=false、published=false。既存document_draft.analysis_consumer=nullも維持。analysis専用の依存候補profileを別に準備し、後続の小さな保存結果準備が、起動前から保持した全依存一覧に一致するかを検査する。reader profileは使い回さない。 正式数値consumer・公開・最終独立auditへの接続は残る。
