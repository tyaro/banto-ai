# TimesFM-3 評価ノート

## 対象範囲

この文書は評価プロトコルを定義します。adapter用の入力はPyPI `timesfm` 3.0.0、checkpointは`google/timesfm-3.0-pytorch`のimmutable revision `43046b85ec22d584a13f8098c2ed39c889e129c2`へ固定しています。今回のhardware targetはWindows amd64／CPython 3.14.0／CPUで、exact-version lockを作成済みです。hash-pinnedなsupply-chain lockは未作成です。

最初に答える問いは実務的なものです。複数の horizon と運転状態において、TimesFM-3 は単純なベースラインと比べて産業設備に近い信号を有用に予測できるでしょうか。

## 2026-09-03時点の位置づけ

公式の[TimesFM repository](https://github.com/google-research/timesfm)と[TimesFM 3.0 model card](https://huggingface.co/google/timesfm-3.0-pytorch)で、次を確認しています。

- 0.3B parameter、F32のpretrained model。
- univariateとnative multivariate forecastingに対応。
- past-onlyとpast-and-future covariateに対応。
- point forecastと0.1～0.9の9 quantileを出力可能。
- source codeはApache-2.0。
- TimesFM 3.0 pretrained weightsは別の `timesfm-non-commercial-license-v1.0` で、非商用・非本番用途に限定。

PyPI `timesfm` 3.0.0は2026-08-28公開で、確認したwheel SHA-256は`0ad3e6b2226a85d665ebca3b5711b875cdef816a6f8ae0d3acbd5361f3e4b63d`です。`requirements.in`は`timesfm[torch]==3.0.0`をtop-levelで固定しますが、完全なtransitive lockではありません。詳細は[`environments/timesfm3/README.md`](../environments/timesfm3/README.md)と[`ADR-0003`](adr-0003-timesfm3-isolation.md)を参照してください。

共通`Forecaster` adapter、official backendの遅延import、known-future整列、9 quantile検証、license／provenance gate、fake backend testsは実装済みです。専用環境で実モデルCPU smokeを2回実行し、速度・Peak RSS・単一synthetic window上の指標を記録しました。さらに固定24時間・1設備・3 targetのMetroPT-3で、5 baselineおよびChronos-2との同一契約比較を実施しました。広範な精度、calibration、実設備一般性能は未評価であり、この状態をPhase 2完了とは扱いません。

実評価の入口は、`tools/timesfm3/preflight.py`、`prepare_checkpoint.py`、`run_smoke.py`です。preflightはCLIで指定したcache pathだけを確認します。checkpoint準備には`--accept-research-only-license`が必須で、取得対象は公式siblingsで確認した4ファイルに固定し、`model.safetensors`のサイズとSHA-256を検証します。smoke実行は`local_files_only=True`と明示cache_dirを維持します。smokeは2 target、past-only covariate、known-future covariateを含む決定的な合成入力から、point予測とp10/p50/p90を新規artifactへ記録します。正式2回の実測値は結果文書に記録済みですが、単一synthetic windowのためPhase 2完了や一般性能の結論には使えません。

直線入力のpreliminary smokeは推論経路の成立確認として扱い、正式な採用数値からは除外しました。正式な非線形case 2回測定値は [`results/timesfm3-cpu-smoke-2026-09-04.md`](results/timesfm3-cpu-smoke-2026-09-04.md) に記録しています。いずれも単一synthetic window／cold processの結果であり、性能採否やPhase 2完了を示すものではありません。

## 2026-09-04 rolling-origin benchmark

[`rolling benchmark実測結果`](results/timesfm3-rolling-benchmark-2026-09-04.md)では、`synthetic-motor-small`、seed `42`、fingerprint `6427bd2da97958f04b8c34e3a09a101d8bc3fc85eced003aaf022e81567312b6`を使い、2 equipment、`motor_current`／`motor_temperature`、context 12、horizon 3を評価しました。`load_proxy`はpast-only、known-future covariateはなしです。各 equipmentのvalidation originは `[36, 45]`、test originは `[48, 57]`で、modelごと24 prediction points、test forecast callは4回です。追加configの`benchmark-timesfm3-known-load.json`は、load_proxyの計画値をorigin時点で確実に取得できる実設備を模したsynthetic known-future／oracle-styleの別scenarioです。known-futureはcontext+horizonちょうどで、split外へは渡しません。

| 指標 | LastValue | TimesFM 3.0 |
| --- | ---: | ---: |
| MAE | 0.219726 | 0.124178 |
| RMSE | 0.298245 | 0.162091 |
| MASE | 1.159370 | 0.626709 |
| WIS | 0.359569 | 0.173315 |
| p10-p90 coverage | 16.666667% | 70.833333% |
| p10-p90 interval width | 0.389116 | 1.758446 |

この限定条件のcomposite値ではTimesFM 3.0がpoint forecastとWISでLastValueを上回りましたが、native intervalのcoverageはnominal 80%未達で、interval widthはbaselineの4.519074倍でした。MAE、RMSE、WIS、interval widthは、AとdegCの異なる単位を持つ2 targetを同数point-weightで混合した固定構成の値です。物理量として直接解釈したり、target構成が異なるrun同士で比較したりしてはいけません。MASEはunitlessですが、同数point平均です。3回のrunでpredictions SHA-256、metrics、originsは一致しました。clean savepointから実行したrun3をprimary reproducibility runとし、run1/run2はdirty pre-savepointの確認として残しています。ただし、24 points、各2 origins、単一generator、LastValueのみの比較であり、一般性能・実設備性能・製品採否を示しません。

result schema `0.2`では、composite値だけに依存しないよう、target別およびequipment-target別のmetrics集計を追加済みです。

統計baselineを含む正式なtarget別比較は [`timesfm3-baselines-comparison-2026-09-04.md`](results/timesfm3-baselines-comparison-2026-09-04.md) に記録しています。past-onlyを標準scenario、known-loadを計画値がorigin時点で確実に取得できるsynthetic oracle-styleの別scenarioとして扱います。known-loadは実績先読みや本番効果を意味しません。各model-targetはtest 12点、各equipmentは2 origins×horizon 3、validationも各equipment 2 originsであり、coverage／WISは暫定値です。

2 seeds×2 horizons×2 context lengthsの実TimesFM matrixは8 cellsすべて成功し、[`timesfm3-matrix-2026-09-04.md`](results/timesfm3-matrix-2026-09-04.md)へ記録しました。seed 17／42は観測file SHA-256も異なります。seed間cell-macroではTimesFM 3.0が温度の4条件でMAE最良、電流では4条件とも6モデル中4位でした。macroはpooled metricではなく、validation／test originも各equipment 2つだけなので一般化しません。

実行時はTimesFM package `3.0.0`、checkpoint revision `43046b85ec22d584a13f8098c2ed39c889e129c2`、CPU、offline、research-only／non-commercialでした。weightsの利用制限はMITのrepository licenseによって緩和されません。

このため、TimesFM 3.0は`banto-ai`の研究benchmarkには含めますが、顧客PoC、本番shadow、製品artifactの候補には含めません。実験結果と生成artifactには `research-only` を明記します。利用条件が将来変わった場合も、固定したcheckpointのlicenseをrunごとに再確認します。MetroPT-3の同一契約比較は完了しましたが、採用判断は行わず、Phase 2も完了扱いにしません。次工程はseedを最低5以上、originとhorizon／context候補の追加、欠損・regime・fault slice、cold／warmとモデル単独memory／latencyの分離、Toto／Granite TTMなどライセンス適合候補との比較です。詳細は[`results/timesfm3-metropt3-evaluation-2026-09-04.md`](results/timesfm3-metropt3-evaluation-2026-09-04.md)を参照してください。

[TimesFM 2.5](https://huggingface.co/google/timesfm-2.5-200m-pytorch)は200M parameterで、codeとweightsがApache-2.0です。最大16k context、optional quantile headによる最大1k horizon、XReg covariate対応が公式に案内されています。TimesFM系の商用利用可能fallbackとして別runで比較しますが、3.0のnative multivariateと同一機能とはみなしません。

他候補との比較方針は [`time-series-model-survey.md`](time-series-model-survey.md) を参照してください。

## 評価マトリクス

| 観点 | 初期値 |
| --- | --- |
| 信号 | motor current、motor temperature、vibration proxy、conveyor speed、load proxy |
| 運転状態 | stopped、low speed、nominal speed、high load、startup、cooldown |
| Horizon | サンプリング間隔に対して short、medium、long |
| タスク | まず point forecasting。対応していれば、または校正 wrapper を使い probabilistic／quantile output も評価 |
| Context | 文書化した window の直近履歴。既知 covariate は別 ablation として評価 |
| Baseline | last value、seasonal-naive、moving average、小型 learned baseline |
| Split | 時系列順の train／validation／test。regime と fault 期間は明示的に分離 |

## プロトコル

1. 正確な model release、checkpoint、tokenizer／preprocessing の挙動（該当する場合）、runtime 環境を固定します。
2. 各 split の training 部分から得られる統計量だけで normalization します。
3. 信号を明示的に resample し、不規則な timestamp を model call の中に隠しません。
4. 集約する前に、信号ごと・horizon ごとに評価します。
5. 運転状態、欠損条件、forecast horizon 別に結果を報告します。
6. 同一 window 上で baseline と比較します。
7. runtime が許せば固定 seed で繰り返し、hardware と runtime を記録します。
8. prediction と metric は、リポジトリで安全な合成データから生成したものを除き、Git の外に保存します。

## 指標

point forecast では MAE と RMSE から始めます。zero-heavy な信号で意味が薄くなる場合は sMAPE を使いません。interval では empirical coverage と interval width を報告し、実装が対応していれば weighted interval score などの proper interval score も報告します。

産業用途では、全体平均だけでなく次の運用スライスを必ず含めます。

- startup と shutdown の遷移
- nominal の定常運転
- high-load 運転
- 欠損または遅延した観測
- regime change
- fault-like な合成イベント

## 答えるべき問い

- 対象 horizon で seasonal-naive baseline を上回るか？
- 設備個体間で性能を移せるか、それとも校正が必要か？
- sampling rate、欠損、mode 変更にどの程度敏感か？
- forecast interval は normal envelope を作れる程度に校正されているか？
- context が不足した場合に、性能は段階的に劣化するか？
- Banto Hub の shadow service に必要な最小 runtime footprint はどの程度か？

## 再現性の記録

各 run に、次のような小さな manifest を持たせます。

```yaml
run_id: <timestamp-or-uuid>
model:
  name: timesfm3
  release: <pinned-release>
  checkpoint: <immutable-reference>
  code_license: Apache-2.0
  weights_license: timesfm-non-commercial-license-v1.0
  allowed_use: research-only
data:
  dataset_id: <synthetic-or-public-id>
  split: <manifest-reference>
preprocessing:
  frequency: <duration>
  context_length: <integer>
  missing_policy: <description>
evaluation:
  horizons: [<integer>]
  metrics: [mae, rmse]
runtime:
  device: <cpu-or-accelerator>
  seed: <integer>
```

## 現時点での非対象

- benchmark 前に production checkpoint を選ぶこと。
- TimesFM 3.0のpretrained weightsまたは派生成果物をproduct candidateへ昇格すること。
- zero-shot の結果を commissioning profile とみなすこと。
- model output から threshold、recipe、control parameter を書き込むこと。
- 公開実験で顧客データを使うこと。
