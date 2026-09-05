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

## standalone analysis contract

analysis configは [`examples/configs/anomaly-multiseed-analysis-v0.2.json`](../examples/configs/anomaly-multiseed-analysis-v0.2.json)、config schemaは [`schemas/anomaly-multiseed-analysis-config-v0.2.schema.json`](../schemas/anomaly-multiseed-analysis-config-v0.2.schema.json)、strict result schemaは [`schemas/anomaly-multiseed-analysis-result-v0.2.schema.json`](../schemas/anomaly-multiseed-analysis-result-v0.2.schema.json) に固定する。analysis idは `anomaly-multiseed-analysis-v02`、input rootは `artifacts/anomaly-multiseed-v02`、output rootは `artifacts/anomaly-multiseed-v02-analysis` である。analysis config canonical SHA-256は `33237908ea60cdfa55a311a2f46157884b9b3564c91e9d6d38218df9ebcc37ce`、config schemaは `550fdde93e7bf25470872bc91f8516226cb843efcd3f42806d65a37f070cef03`、result schemaは `00541b2770c8e682ef1b14d2e3dd354f404b6b3c796c2bbc3995a68913d841b8` であり、configにもresult schema path/digestを明記し、codeでpinする。

bootstrapはseed cluster（10 seed）をreplacementありで10000回再標本化し、各replicateでseed内12 layout・48 eventを丸ごと保持する。drawは `sha256-counter-rejection-v1` とし、入力文字列 `algorithm_id:seed:replicate:cluster:counter` のSHA-256をbig-endian整数化し、`floor(2^256/n)*n` 未満だけを採用して `mod n` を取る。percentile CIは type 7 の線形補間、位置 `(n-1)*p`、95% CIは `p=.025/.975` と固定する。golden draw digestは `5b311c270aaef7bb942e0c4fbe761e8e225aaa0a1314a8bd2e70875f0fd46548` である。replicateの必要cluster不足、denominator 0、non-finite、または一つでもundefinedなら、そのmetricのCIは捨て直さず `inconclusive` とし、undefined countを保存する。

point estimateとbootstrap replicateはすべてraw numerator/denominatorのratio-of-sumsで計算する。incidentはoverall delay summary、by_class 2、by_equipment 2、by_mode 6、class×equipment×mode 24の計34 sliceを固定し、後者は各seed1件、10 seedのn=10としてrecall、eligible/detected count、検出条件付きdelay（count/mean/median）を記録する。CIはrecall/rateだけをseed-cluster再集計し、overallを含むdelayはpointのcount/mean/medianのみでCI対象外とする。missed incidentはdelay 0秒にしない。class precisionはclean false alertに固有classがなく一意な帰属ができないため `not_applicable` と固定し、promotion gateには使わない。clean false-alert equipment episodeはsource signal episodeをequipment×mode内で再dedupし、mode boundaryでclipする。exposureはavailable target-score intervalをequipment×modeでunionし、enabled eventのexpanded windowをclip/subtractして整数millisecondsで保持し、hoursへは出力時だけ換算する。clean rateはequipment×mode 12、by_equipment 2、by_mode 6の計20 sliceを保存する。availabilityはexact 8 signalおよびsignal×mode 48 sliceごとに `sum(available)/sum(total)` とする。suppressed event-window alertはpositive/cleanへ再分類せず、lead timeは算出しない。

analysisはmatrix artifactをread-onlyで検証し、aggregate summaryをresultからrunnerのdeterministic summaryとして再生成してbyte exact比較する。config、schema、result、marker、全cellの7 dataset file／3 evaluation file、directory inventory、path containment、current clean revision、TOCTOUを検証し、extra/missing/linkを拒否する。`run_status=not_run`、`performance_status=not_evaluated` はanalysis config validationの状態であり、formal v0.2 runおよびanalysisは現時点で未実行である。

## 実行順序と境界

preregistrationの順序はA〜C（validator、deterministic runner、fake/unit tests）→standalone seed-cluster bootstrap／performance analyzer本体とartifact非依存unit testの完了・監査→D（clean 120-cell run）→E（独立analysis）とする。v0.2の現savepointではD/Eを開始せず、正式artifact `artifacts/anomaly-multiseed-v01` の変更・移動・削除、v0.2 formal run、customer data、weights／checkpoint、control write、Banto Hub writeを行わない。

正式runは、clean revision、v0.2の別output root、入力snapshot、summary byte exact再生成、atomic non-overwriteを満たす場合だけ開始できる。run開始後にseed、layout、detector、bootstrap、metric、CI、thresholdを変更しない。追加変更や再実行が必要になった場合は、別versionのpreregistrationと別identityを作る。

## 関連証跡

- v0.1 integrity audit: [`docs/results/anomaly-multiseed-v01-integrity-audit-2026-09-05.md`](results/anomaly-multiseed-v01-integrity-audit-2026-09-05.md)
- v0.1 preregistration: [`docs/anomaly-multiseed-evaluation-plan.md`](anomaly-multiseed-evaluation-plan.md)
- v0.2 config: [`examples/configs/anomaly-multiseed-v0.2.json`](../examples/configs/anomaly-multiseed-v0.2.json)
- v0.2 config schema: [`schemas/anomaly-multiseed-matrix-config-v0.2.schema.json`](../schemas/anomaly-multiseed-matrix-config-v0.2.schema.json)
