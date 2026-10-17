# consumer入力宣言の検査

`anomaly_v03_consumer_input` は、[入出力契約案](anomaly-v03-consumer-io-proposal.md)の前段となる、I/Oなしのmetadata検査である。対応は `fixture` と `engineering-dev-smoke` のみ。正式modeは対象一覧の展開より前に拒否する。

既存の観測reader、解析、保存CLIは変更していない。この検査を通ってもファイルは開かれず、データ認証・実行許可・正式受入は付かない。

```python
from banto_ai.anomaly_v03_consumer_input import planned_input, validate_input

# 架空の1区間6評価、または全dev/smoke 120区間720評価の未開始宣言を作る。
packet = planned_input("fixture")

# 呼出し側が外部で保持したcanonical JSONのSHA-256を渡す。
# 下記2変数は、将来の認証adapterが用意する入力。
report = validate_input(
    decoded_metadata,
    expected_mode="engineering-dev-smoke",
    expected_sha256=caller_retained_canonical_sha256,
)
```

digestはdecoded metadataのcanonical JSONに対する値であり、元ファイルのraw SHA-256ではない。raw bytes/重複JSON/path/markerの検証は今後のI/O adapterの責務。受信した値からその場で計算したhashだけを、信頼された外部anchorの代わりにしない。

## 入力の閉じた構造

formatは `anomaly-v03-consumer-input-metadata-v1`。辞書のkey集合を完全一致で検査し、余分な `accepted` / `formal_permission` 等を拒否する。整数・booleanの混同、未知mode/status、hash形式、identityとcoverageを検査する。独立した保存用schemaファイルや正式schemaの変更は、この段階では追加していない。

| 欄 | 内容 |
| --- | --- |
| `format`, `mode` | 固定formatと呼出し側が明示したmode。fixtureとengineeringの読み替え禁止 |
| `policy_id`, `registry_raw_sha256` | fixture専用ID/null、または既存engineering方針ID/固定registry hash |
| `producer` | state、writer終了の宣言、receipt/markerのhash参照、failure。参照先の存在・実行・終了は未確認 |
| `chunks` | 固定順のchunk index、6 identities、attempt履歴。fixtureは独自IDの1pair、engineeringは登録済みdev/smoke全120pair |
| `coverage` | 最新attemptのsuccess/inconclusive/partial/failed/not_started件数。未開始chunkも6枠ずつ残す |

attemptは1から連番。各attemptはstate、failure、6評価を持つ。評価はidentity、status、profile_status、input_hashes、evaluation_sha256の閉じた5欄。input_hashesはobservations/events/quality_mask/split/origins/targetsの6種。1datasetの3候補、および再試行間で、判明している入力hashは一致しなければならない。

再試行前のattemptはfailedに限り、reason/evidence hashを残す。成功済み・進行中のattemptを飛び越す再試行、連番の欠落、hash/source/runtime不整合後の同じ宣言内での再試行は拒否する。1chunkあたり64attemptはmetadataのサイズ制限であり、64回の実行許可ではない。

## 完了と不完全な状態

- successはcalibrated、inconclusiveはprofile inconclusiveで、どちらも入力/resultのhash参照が必要。計算上の判定不能をsoftware failureやsuccessに置き換えない。
- partial/failedは完全なevaluationのhashを主張できない。残った部分bytesの参照は失敗記録に保持する。not_startedはprofile/入力/resultの証拠を持たない。
- complete attemptは6評価すべてsuccessまたはinconclusive。complete producerは全chunk完了、writer終了宣言、receipt/marker両参照が必要。
- producerがfailedなら、全chunkが完了してmarker参照があっても `declared_complete=false`。公開後の監視失敗を保存完了と混同しない。開始前の失敗も全予定枠を残す。
- in_progressはwriter終了や最終markerを主張できない。解析へ進めず `next_step=wait_for_writer` を返す。

失敗時のstageはinput/compute/publication/supervision/verification、reasonはexception/worker_exit/resource_limit/interrupted/hash_mismatch/source_mismatch/runtime_changed/verification_failed。producerとattemptの双方に適用する。failure evidenceのhashが不明ならnullのまま保持し、架空の証拠を補わない。

## 戻り値と限界

`validation_status=metadata_contract_valid` と、呼出し側digestとの一致、宣言上のcoverage/完了数、失敗履歴を返す。完了宣言の場合の `next_step=authenticate_input_bytes` は次に必要な工程の案内であり、その工程を実行・許可するものではない。

常に `input_bytes_verified` / `source_runtime_accepted` / `result_trusted` / `execution_authorized` / `analysis_authorized` / `formal_permission` / `promotion_allowed` / `independent_s6_complete` はfalse。performanceはnot_evaluated、selected_candidateはnull。返した履歴を変更しても元入力は変わらない。

この段階で確認するのは**同じ入力だという宣言の整合**まで。正常系列のcore/stress対応、元bytesとhashの一致、実source/runtime、payloadの数値、実writer終了、失敗履歴の網羅性は、信頼された外部記録と今後のadapterで確認する。新しい自己整合metadataを作れば実行が認証される、という境界にはしない。

2026-09-25追記：[checkpoint adapter](anomaly-v03-consumer-checkpoints.md)を実装し、共通slot検査へ接続した。区間別markerと全体producer markerの違い、失敗時の未知内訳を保持する別envelopeであり、このv1のproducer完了条件は変更しない。37試験と保存済み120区間/720評価の管理記録への適用を確認。次は公開印と終了記録を認証するreader結合。
