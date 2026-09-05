# Event-aware anomaly evaluation v0.2 multi-seed replay preregistration

策定日: 2026-09-05

## 位置付けと変更理由

これは、summary integrity fix後に行う将来の正式再実行のためのpreregistrationである。v0.1の正式artifact `artifacts/anomaly-multiseed-v01` は旧runnerのsummary integrity bypassが判明したため `REJECT` evidenceとして変更せず保全する。v0.1の監査結果と3つのaggregate hashは [`docs/results/anomaly-multiseed-v01-integrity-audit-2026-09-05.md`](results/anomaly-multiseed-v01-integrity-audit-2026-09-05.md) に記録する。

v0.2の変更理由は、evaluator summaryを初期captured inputsからpure replayしてbyte exact検証するsummary integrity fixである。対応するcode lineageは、e160c16（summary integrity）、9d6293d（summary scalar strictness）、および00ad3a1（v0.1 reject audit documentation）である。これは結果を見てseed、layout、metric、CI、thresholdを変更する更新ではない。

現時点ではv0.2 formal run、bootstrap、performance analysis、promotion判定を実行していない。固定状態は `run_status=not_run`、`performance_status=not_evaluated` である。

## 固定条件

v0.2は、次の項目をv0.1とsemanticに同一とする。

- seed: `[11, 17, 23, 29, 37, 42, 53, 67, 79, 97]`
- 12 layouts、各layoutの4 event class、test split `[720,900)`、30 sample mode window、offset `[2,9,16,23]`、duration `3`、grace `3`
- detector: `min_calibration_points=10`、`robust_z_threshold=4.0`、`persistence_points=2`、`detection_grace_points=3`
- bootstrap: seed `20260905`、resamples `10000`、confidence level `0.95`
- 8 fully qualified target signal、event accounting、clean exposure、slice定義、promotion thresholds

promotion thresholdsはoverall incident precision point `>=0.80`／CI lower `>=0.60`、machine-fault recall point `>=0.80`／CI lower `>=0.60`、sensor-fault recall point `>=0.90`／CI lower `>=0.75`、clean false alerts per 8 equipment-hours point `<=1.0`／CI upper `<=2.0`、8 signal availability各 `>=0.95`で固定する。bootstrap不能、undefined、sample不足は補完せず `inconclusive` とする。

## v0.2 identityとprovenance

変更を許可するのは次のidentity／provenanceだけである。

| item | v0.1 | v0.2 |
| --- | --- | --- |
| matrix id | `anomaly-multiseed-v01` | `anomaly-multiseed-v02` |
| per-cell dataset id | `anomaly-multiseed-v01-{cell_id}` | `anomaly-multiseed-v02-{cell_id}` |
| matrix config schema_version | `0.1` | `0.2` |
| config path | `examples/configs/anomaly-multiseed-v0.1.json` | `examples/configs/anomaly-multiseed-v0.2.json` |
| output root | `artifacts/anomaly-multiseed-v01` | `artifacts/anomaly-multiseed-v02` |
| config schema path | `schemas/anomaly-multiseed-matrix-config.schema.json` | `schemas/anomaly-multiseed-matrix-config-v0.2.schema.json` |
| config canonical SHA-256 | `1c014476f9e9a3112b60323453b7e00359b1e45a831a43ab52d1c4e11d3341db` | `3e206fc6c988850953d7ddd739a0504cb8cdd92f6726848b78ce4803461daa26` |
| config schema canonical SHA-256 | `3bcc8d170dd59d64eb566dc21e51900ed84f253f2f0ad6e86d2778932fb29829` | `fbd081961bfd8a56f3ac24514310f0a17f89c02174db44bfeb3fb6b3911f1c4d` |
| result schema path | `schemas/anomaly-multiseed-matrix-result.schema.json` | `schemas/anomaly-multiseed-matrix-result-v0.2.schema.json` |
| result schema canonical SHA-256 | `9912286f5007e203f1637b182505b1ab9101733a41d89ba52dab9edf983da713` | `79acd31482bae6702dcb6bf6145a58342730a0b61c053592a720fa9e01e53326` |

base generator config canonical SHA-256 `16165735d4fdb71213fec301f26d9c04a593ee36afbb51d255be535dd98f8b93` とbase generator schema canonical SHA-256 `e6e743ef4cb28902b3869cf20a0227df0340fe6b6ce0227d63eb2d2b0b55fd89`は変更しない。matrix result schemaは既存v0.1を変更せず、v0.2用 `schemas/anomaly-multiseed-matrix-result-v0.2.schema.json` を使う。v0.2 result schema canonical SHA-256は `79acd31482bae6702dcb6bf6145a58342730a0b61c053592a720fa9e01e53326` である。result schemaはmatrix profile別identityを持つが、matrix aggregate payloadの構造 `schema_version` はv0.1の `0.1` 据え置きである。

v0.1とv0.2のconfigは、上表のschema version、matrix id、schema path／digest、output root以外を完全一致させる。runnerは各cellのdataset idにも選択済みmatrix idを使い、v0.1／v0.2のdataset identityを混在させない。未知config path、v0.1／v0.2 identity混在、schema／config digest差し替え、duplicate／non-finite JSON、unsafe path、link／reparse pointはvalidatorでfail closedにする。

## 実行順序と境界

preregistrationの順序はA〜C（validator、deterministic runner、fake/unit tests）→standalone seed-cluster bootstrap／performance analyzer本体とartifact非依存unit testの完了・監査→D（clean 120-cell run）→E（独立analysis）とする。v0.2の現savepointではD/Eを開始せず、正式artifact `artifacts/anomaly-multiseed-v01` の変更・移動・削除、v0.2 formal run、customer data、weights／checkpoint、control write、Banto Hub writeを行わない。

正式runは、clean revision、v0.2の別output root、入力snapshot、summary byte exact再生成、atomic non-overwriteを満たす場合だけ開始できる。run開始後にseed、layout、detector、bootstrap、metric、CI、thresholdを変更しない。追加変更や再実行が必要になった場合は、別versionのpreregistrationと別identityを作る。

## 関連証跡

- v0.1 integrity audit: [`docs/results/anomaly-multiseed-v01-integrity-audit-2026-09-05.md`](results/anomaly-multiseed-v01-integrity-audit-2026-09-05.md)
- v0.1 preregistration: [`docs/anomaly-multiseed-evaluation-plan.md`](anomaly-multiseed-evaluation-plan.md)
- v0.2 config: [`examples/configs/anomaly-multiseed-v0.2.json`](../examples/configs/anomaly-multiseed-v0.2.json)
- v0.2 config schema: [`schemas/anomaly-multiseed-matrix-config-v0.2.schema.json`](../schemas/anomaly-multiseed-matrix-config-v0.2.schema.json)
