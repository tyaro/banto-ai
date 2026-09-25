# 保存済みcheckpointからconsumerへのmetadata変換

`anomaly_v03_consumer_checkpoints.adapt_completed_journal` は、完了したdev/smokeのplan・journal・attempt別manifestをdecodedなPython値として受け取り、120区間の最終評価と失敗履歴を返す。I/O、観測生成、score再生、推論、writer起動は行わない。[確認結果](results/anomaly-multiseed-v0.3-consumer-checkpoint-adapter-2026-09-25.md)。

```python
from banto_ai.anomaly_v03_consumer_checkpoints import adapt_completed_journal

result = adapt_completed_journal(
    plan, records, attempt_manifests,
    expected_mode="engineering-dev-smoke",
    expected_plan_sha256=anchor_plan_hash,
    expected_record_count=anchor_record_count,
    expected_head_sha256=anchor_journal_head,
    expected_manifests_sha256=anchor_manifest_bundle_hash,
)
```

4つのhash/countは呼出し側が保持した外部anchorから渡す。planとmanifest一覧はcanonical metadata hash、journal headは既存record_hash（canonical bytes＋LF）の連鎖。raw file hashとの混同を避ける。manifest bundleを作る場合は、既知の外部保存点に全選択raw manifestが一致した後でcanonical hashを導出する。未知のmetadata自身から期待値を作っても実行証明にならない。

`attempt_manifests` は全attemptについて `{chunk_index, attempt, manifest}` をjournal順に並べたlist。成功した最後のattemptだけ渡す形は拒否する。manifestは既存chunk resultの全宣言で、独自に組み立て直した簡易slot表ではない。途中のfailed/interrupted attemptにmanifestがない場合だけnullを許す。

## 変換する内容

- 既存checkpoint reducerで固定plan、全record連鎖、連番、120区間の完了宣言を確認。formal/holdout/fixture/未知modeはこの処理より前に拒否する。
- manifestの区間・attempt・identity・source revision・runtime・6評価を既存契約へ照合し、最後の検証済みoutcomeとも一致させる。
- [consumer入力検査](anomaly-v03-consumer-input.md)と共通のslot検査へ渡し、observations/events/quality_mask/split/origins/targetsの6種hashとevaluation hashを保持。同一datasetの候補間・判明している再試行間で入力hash不一致を拒否する。
- 最新の検証済みattemptだけでcoverageを数える。inconclusiveは完了扱いだがsuccessへ昇格させない。
- 過去のjournal failureはreason、context、record番号、publication evidence、terminal record全体とhashを保持する。manifest側のfailureも別に残す。監視側と計算側の失敗理由は同じとは限らない。
- manifestが欠けた失敗は `evaluations=null / evaluation_detail=unreported`。未実行6枠と推測しない。判明していない入力hash間の一致も主張しない。

profile_statusはmanifest slotのsuccess/inconclusiveから対応づけた宣言であり、profile bytesの検査結果ではない。戻り値に `profile_status_source=manifest_slot_status_only` を明示する。

## 公開完了・信頼の境界

戻り値formatは `anomaly-v03-consumer-checkpoint-adapter-v1`。既存の `consumer-input-metadata-v1` をそのまま生成するAPIではない。区間別markerを持つcheckpoint方式と、全体producerのreceipt/markerを要求する既存宣言の違いを残す。全体markerやcontroller終了を捏造せず、既存validatorのproducer条件を緩和しない。

`journal_declares_coverage_complete=true` はjournalの宣言だけを表す。`input_bytes_verified`、`publication_verified`、`producer_exit_verified`、`source_runtime_accepted`、`result_trusted`、`campaign_completed`、execution/analysis/formal/promotion/S6はfalse。performance未実施、selected_candidate=null。

必要な次工程は `authenticate_checkpoint_publications_and_controller_exit`。このadapterは既存chunk契約の構造validatorを呼ぶが、同モジュールのpayload audit関数は呼ばない。raw file/path/marker認証、実writer終了、source/runtimeの正式受入は未実装。旧正式運用の契約案はdraftのまま。

2026-09-25追記：[公開・終了記録reader](anomaly-v03-consumer-publication.md)を接続し、14新規試験と全120区間の実metadata照合が完了。adapter本体と上記のfalse flagsは変更しない。reader側でmetadata/manifest/worker終了記録を限定的に認証し、全payloadとcontrollerプロセス自体の終了は未認証と分ける。
