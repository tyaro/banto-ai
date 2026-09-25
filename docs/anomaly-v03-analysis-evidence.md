# 保存済み記述結果を準備するanalysis役割の実観測

2026-09-26 JST、現実装 `140e91de93e2cc43c45fab9efb9a7cbc6ece43c7`。[今回の検証結果](results/anomaly-multiseed-v0.3-analysis-dependency-profile-2026-09-26.md)、[初回の実観測](results/anomaly-multiseed-v0.3-analysis-observed-evidence-2026-09-26.md)、[共通validator](anomaly-v03-consumer-evidence.md)。

## 対象

operationは`prepare-saved-descriptive-result`。writer終了後、通常権限で7保存fileを認証し、report JSON/Markdown/HTMLとconsumer receiptの4payloadを新しい確認directoryへ準備する。数値再計算・登録観測データの読取・公開完了marker発行は含まない。

## 別のreferenceから解析用候補を準備する

```python
from banto_ai.anomaly_v03_analysis_evidence import prepare_with_evidence
from banto_ai.anomaly_v03_analysis_profile import prepare_profile

request = {
    "format": "anomaly-v03-observed-analysis-request-v1",
    "mode": "engineering-dev-smoke",
    "role": "analysis",
    "operation": "prepare-saved-descriptive-result",
    "binding_savepoint": absolute_binding_path,
    "report_savepoint": absolute_report_path,
    "analysis_input": absolute_input_path,
    "expected_binding_pin": retained_binding_pin,
    "expected_report_pin": retained_report_pin,
}
reference = prepare_with_evidence(
    request, expected_revision=full_current_candidate_commit,
    receipt_parent=existing_separate_parent, receipt_name="reference",
)
# 呼出し側で成功・終了回収を確認し、result_pinを保持する。
candidate = prepare_profile(
    reference["check_directory"], expected_result_pin=retained_reference_result_pin,
    expected_revision=full_current_candidate_commit,
    profile_parent=existing_separate_parent, profile_name="analysis-candidate.json",
)
# profile_pinを別に保持した後、異なる子processで比較する。
checked = prepare_with_evidence(
    request, expected_revision=full_current_candidate_commit,
    receipt_parent=existing_separate_parent, receipt_name="subsequent-check",
    dependency_profile=candidate["profile_path"],
    expected_dependency_profile_pin=retained_analysis_profile_pin,
)
```

referenceは同じcheckout/revisionの成功した未profile化analysisのみ。外部result pinを起点にresult/evidence/binding/dependencies/stdout/requestと4payloadを照合し、source/runtime/依存の前後一致と現在のdisk/Git一致を確認する。既存候補は上書きせず、profiled実行から候補を自動更新しない。保存先と元入力/source/referenceの重複は拒否する。

候補はanalysis専用format、role=analysis、operation、full revision/root/runtime、採取境界`request-decoded-before-saved-result-preparation-and-staging-v1`を持つ。reader候補のformatや役割は受理しない。共通collectorを利用することと、役割の候補を流用することは別である。

## 起動前の保持と比較

親はselected source13/Python2file、host実値と起動条件、外部anchorで認証した7入力、期待4payloadを保持する。同一の準備関数を親でも使った期待bytesとの照合であり、独立した数値検算ではない。

profile指定時はpathとpinを必ず対で渡す。親は候補のpin/role/runtime/disk/Gitを検査してmemoryに保持し、確認directoryへ同じbytesを保存する。request/invocationに候補を加えた10入力を証拠に結ぶ。未指定時は従来どおり9入力の観測のみで、依存全体への事前一致は要求しない。

子は`-I -S -B`で起動。request解読後、準備・payload保存の前に依存とruntimeを候補へ比較し、完了後にも比較する。前段不一致時はpayloadを作らない。親は元Popen handleによるexit0/回収/観測errorなしを確認してから、原本候補・保存copy、子の前後一覧、全payloadの実bytesを保持期待へ照合する。子の返信から基準を再採用しない。

候補のfile hashやidentityの差、追加/欠落module、runtime差、reader候補、未知欄、保存copy改変を拒否する。UnreapedWorkerは記録保存失敗でもownerを保持し、未終了workerの出力を読まない。

## 保存と上限

従来のpayload4file、request/invocation、source-tool、launch/expected/supervision、worker stdout/stderr、evidence/binding/dependencies/dependency-crosscheck/resultを保存。profile指定時はdependency-profile.jsonと、成功時のみdependency-profile-binding.jsonを追加する。bindingはrole/operation/profile pin/reference result pinとexact-before-and-afterを保持する。

子30秒/private512MiB/stdout+stderr1MiB、候補512KiB。payloadはJSON4MiB/Markdown1MiB/HTML2MiB/receipt1MiB、合計8MiB。入力は1file16MiB/合計32MiB。依存は最大512file/1file64MiB/合計256MiB。親Gitは各10秒で、親preflightを含む正式総予算は未確定。payload制限はchild/parent検査であり、supervisorの全directory容量監視ではない。

候補は観測由来の`candidate-not-accepted`。source/runtime全閉包・memory code・実使用cacheを証明しない。numerical_analysis_performed/published/formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。次は、照合済みの4payloadを既存のsingle-writer公開処理へ接続し、writer終了後の別readerまでを小さな架空入力で通す。公開時に解析証拠と保持pinを結合し、数値再計算や正式採択へ範囲を広げない。

## 通常公開と別readerへの接続（2026-09-26）

[publish_and_check](anomaly-v03-analysis-publication.md)で、外部result pinに結び付いたprofile付き成功の4payloadを既存LocalPublicationへ渡し、writer終了後のobserved readerへ接続した。全43試験pass。[結果](results/anomaly-multiseed-v0.3-analysis-publication-chain-2026-09-26.md)。解析側のpublished=falseは「解析処理自体は公開しない」の意味で維持し、公開状態は別chain resultのpublication_statusで記録する。数値再計算・正式文書・独立S6は含まない。
