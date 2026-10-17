# ADR-0004: Chronos-2 optional backendの隔離

- Status: Accepted
- Date: 2026-09-04
- Decision owners: banto-ai research

## Context

TimesFM 3.0の初期評価は完了したが、学習済み重みの利用条件によりresearch-onlyである。次の比較対象には、商用利用可能性を検証でき、univariate／multivariate、past-only／known-future covariate、native quantileを扱えるChronos-2を加える。

Chronos-2はcore runtimeに直接依存させると、PyTorchやTransformersの依存解決、checkpoint download、CPU／GPU差分がbaselineの再現性とCIへ波及する。また、Apache-2.0であることだけでは、実性能、欠損挙動、共変量のleakage、resource、運用安全性は保証されない。

## Decision

### 固定するもの

- package: `chronos-forecasting==2.3.1`
- checkpoint: `amazon/chronos-2@29ec3766d36d6f73f0696f85560a422f50e8498c`
- model: 120M encoder-only、max context 8192、max prediction 1024
- native output: `predict_quantiles`のpointは公式変数名`mean`ではなく、実体のmedian／p50として扱う
- 初期run: `batch_size=1`、`context_length=12`、`device_map="cpu"`、`local_files_only=true`、`cross_learning=false`

revisionを省略したlatest取得、実行中の自動upgrade、Gitへのcheckpoint追加は禁止する。package wheel、checkpoint file、依存lockのhashと取得時点は、実装時のrun provenanceへ記録する。2026-09-04に実取得した`model.safetensors`は477,930,472 bytes、実計算SHA-256は `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42` であり、checkpoint固定証跡にはこのsizeとSHA-256を使う。HTTPの`X-Linked-ETag`も同じSHA-256だったが、header値だけに依存せず、取得fileを毎回hash検証する。package wheel SHA-256は `d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496` とする。

### 境界

Chronos-2のadapterとその依存は専用venv／外部cache／専用entrypointに置く。通常のbaseline CLI、schema validator、CIはChronos-2、Torch、Transformers、NumPyをimportしない。cacheはrepository外で、`local_files_only`を既定にする。

共通`Forecaster`へは、targetの順序、timestamp、unit、past-only／known-futureの意味を保ったまま変換する。known-futureへ渡せるのはorigin時点で本当に確定していた計画値だけであり、評価対象期間の実績値を後から渡すoracle leakageは禁止する。

missing、stale、不規則timestamp、context／horizon長の不一致は、初期adapterで補間やforward fillを行わずfail closedとする。欠損耐性を評価する場合は、欠損処理の仕様と実測を別の実験として記録する。

Chronos-2の利用段階は`commercial-evaluation`とする。package、repository code、weightsはApache-2.0として一次情報を確認しているが、product-candidateへの昇格は、精度、p50整合、coverage／WIS、CPU p95／memory、再現性、degraded state、データ／ライセンス証跡のGateを通過した場合に限る。未達なら昇格せず、commercial-evaluationで停止または撤退する。

TimesFM 3.0は比較基準として残すが、weights条件によりresearch-onlyであり、Chronos-2との比較結果から商用artifactへ昇格させない。

## Verification status

2026-09-04にPython 3.14専用venvで`chronos-forecasting==2.3.1`のinstall／importと、固定checkpointを使った公式APIのreal CPU smokeを確認した。smoke条件は2 targets、prediction horizon 3、3 quantilesで、推論時間は1.335秒だった。これはpackage、checkpoint、公式APIの契約成立を確認する証跡であり、Banto上の精度・latency合格を示すものではない。

Banto adapter／tool経由のend-to-end smokeとrolling benchmarkは未完である。これらが完了するまでPhase 1全体を完了扱いせず、`commercial-evaluation`から`product-candidate`へ昇格しない。

## Consequences

### Positive

- coreの外部依存ゼロとbaseline CIの再現性を維持できる。
- model、package、checkpoint、cache、licenseの変更をrun単位で監査できる。
- Chronos-2のmultivariate／covariate／quantile能力を既存runnerの共通metricsで比較できる。

### Negative

- 専用環境の構築とcheckpoint準備が必要になる。
- 実modelのCPU／GPU検証は通常CIから分離され、別途実行証跡が必要になる。
- missing処理を初期段階で厳しく拒否するため、欠損データの性能評価は後続phaseになる。

## References

- [Amazon Science: Chronos](https://github.com/amazon-science/chronos-forecasting)
- [chronos-forecasting v2.3.1 pyproject.toml](https://github.com/amazon-science/chronos-forecasting/blob/v2.3.1/pyproject.toml)
- [Chronos-2 v2.3.1 pipeline](https://github.com/amazon-science/chronos-forecasting/blob/v2.3.1/src/chronos/chronos2/pipeline.py)
- [Chronos-2 model card](https://huggingface.co/amazon/chronos-2)
- [Chronos-2 pinned config](https://huggingface.co/amazon/chronos-2/blob/29ec3766d36d6f73f0696f85560a422f50e8498c/config.json)
