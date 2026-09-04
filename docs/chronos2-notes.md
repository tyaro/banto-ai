# Chronos-2 実装・評価ノート

確認日: 2026-09-04

## 1. 採用理由と位置づけ

Chronos-2は、Amazon ScienceのChronos系列における120M parameterのencoder-only時系列foundation modelです。公式APIでunivariate、multivariate、past-only covariate、known-future covariate、native quantile forecastを扱え、CPU／GPUの実行経路があります。TimesFM 3.0で作った共通`Forecaster`、rolling-origin、target／equipment-target metricsを再利用しやすいため、次の汎用forecast候補にします。

ただし本書の結論は製品採用ではありません。package、repository code、model weightsは一次情報上Apache-2.0として扱いますが、現段階のBanto用途は`commercial-evaluation`です。実性能、欠損・stale挙動、resource、再現性、read-only／shadow境界を確認するまで`product-candidate`へ昇格しません。

## 2. 固定対象

| 項目 | 固定値・方針 |
| --- | --- |
| package | `chronos-forecasting==2.3.1` |
| checkpoint | `amazon/chronos-2@29ec3766d36d6f73f0696f85560a422f50e8498c` |
| 規模 | 120M encoder-only |
| 上限 | context 8192、prediction 1024 |
| quantile | native。Bantoのpointはmedian／p50 |
| 初期環境 | 専用venv、repository外cache、CPU、batch 1、local files only |
| 利用段階 | `commercial-evaluation` |
| Banto core | Chronos／Torch／Transformers／NumPyをimportしない |

2026-09-04に実取得した`model.safetensors`は477,930,472 bytes、実計算SHA-256は `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42` です。HTTPの`X-Linked-ETag`も同じSHA-256でしたが、固定証跡にはheaderではなく実取得fileのsizeと計算SHA-256を使います。package wheel SHA-256は `d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496` です。実行前にこれらを検証し、run provenanceへ保存します。

## 3. 共通契約への変換

Chronos-2公式の`predict_quantiles`へは、Bantoの1 originにおける全targetを1 requestとして渡します。

```text
Banto ForecastRequest
  contexts: targetごとの過去系列
  past_only_covariates: origin直前までの系列
  known_future_covariates: context prefix + horizon分の計画値
        |
        v
Chronos-2 input
  target: (n_variates, history_length)
  past_covariates / future_covariates: 明示された共変量だけ
        |
        v
ForecastResult
  point_forecast: Chronos-2 median / p50
  quantiles: requested native levels
```

`predict_quantiles`の戻り値にある`mean`という名前はBantoの算術平均を意味しません。Bantoではmedian／p50として検証し、requested quantileの0.5と整合させます。quantile crossing、timestamp、horizon長、target ID順が一致しない場合は結果を採用しません。

## 4. 共変量とleakage

past-onlyはoriginの直前までの観測値だけを使います。known-futureは、originの時点で計画システムから確定して取得できたload／speed／recipe計画値だけを使います。test期間の実績loadを計画値として再利用すること、fault発生後に更新された計画を過去originへ渡すこと、target由来の未来特徴量を渡すことは禁止します。

`benchmark-chronos2-known-load.json`はこの契約を確認するsynthetic scenarioです。名前に反してoracleを許可する設定ではなく、oracle leakageを禁止し、評価前に計画値の出所・確定時点・更新履歴を確認できるfixtureだけを受け付けます。実データで同条件を主張するには、Banto Hub側の計画値のversion／as-of証跡が必要です。

## 5. missingとquality

初期実装はfail closedです。以下を検出した場合、無理に予測を返さず、reasonとquality statusを持つ失敗として記録します。

- missing、NaN、inf、stale quality flag
- timestampの不規則、重複、timezone不整合
- context不足、horizon不一致、共変量のkey／長さ不一致
- context 8192またはprediction 1024の公式上限超過

forward fill、線形補間、暗黙のzero埋め、将来実績からの埋め戻しは初期adapterの責務にしません。後続のmissing実験では、前処理版、欠損率、評価slice、補間によるleakage防止を別途固定します。

## 6. Phase 0／1受入基準

### Phase 0: 契約・隔離

- run／result schemaがChronos-2のnative quantileと指定6 parameterだけを受け付ける。
- 不正revision、context範囲外、batch 0、空device_map、unknown parameter、quantile policy変更を拒否する。
- 3つの設定例がJSONとして読み込め、past-only／known-futureの意図が文書と一致する。
- package／checkpointの固定値、license判断、cache外部化、TimesFM research-onlyが文書化される。

### Phase 1: 小規模実行（初期実測完了）

- 確認済み: Python 3.14専用venvでpackage install／importに成功した。
- 確認済み: 固定checkpointを使う公式API real CPU smokeが、2 targets×prediction horizon 3×3 quantilesで完走した。推論時間は1.335秒だった。
- 確認済み: Banto adapter／tool経由のCPU smokeが、2 targets×horizon 4、past-only `speed`、known-future `planned_load`、p10／p50／p90で完走した。`snapshot_verified=true`、cold elapsedは12.057009100011783秒だった。
- 確認済み: 60 samples×2 equipment、context 12、horizon 3、各equipmentのvalidation／test各2 originsで、past-only 6 modelsとknown-future 7 modelsの初期rolling benchmarkが完走した。
- 確認済み: known-future条件のChronos-2はaggregate MAE `0.1691488806622826`、WIS `0.15937026919725228`で7 models中1位となり、past-onlyのMAE `0.20672198138554906`、WIS `0.1952207659517925`から改善した。
- 確認済み: seed `[17, 42]`×horizon `[1, 3]`×context `[6, 12]`のChronos-2実model matrix 8 cellsが、固定clean HEADから8/8成功した。currentは4条件すべてmoving-averageがMAE首位、temperatureはWIS 4条件すべてChronos-2が首位だった。詳細は[`results/chronos2-matrix-2026-09-04.md`](results/chronos2-matrix-2026-09-04.md)を参照する。
- 未実施: origin拡大、公開実データ、missing／stale／regime／fault slice、known-future対past-onlyの同一契約比較、校正拡張、拡張した評価条件をclean savepointから再実行すること。

公式API smokeはpackage／checkpoint／API shape、Banto tool smokeは共通adapter経路の契約確認です。rolling benchmarkとmatrixも小標本・合成データ上の初期結果であり、実設備性能の証拠ではありません。matrixはpast-only条件で、known-futureは別の初期rolling benchmarkでorigin時点に確定済みの計画値を模した条件です。詳細は[`results/chronos2-initial-evaluation-2026-09-04.md`](results/chronos2-initial-evaluation-2026-09-04.md)と[`results/chronos2-matrix-2026-09-04.md`](results/chronos2-matrix-2026-09-04.md)を参照してください。Chronos-2は`commercial-evaluation`を継続し、追加gateが完了するまで`product-candidate`へ昇格しません。

## 7. 撤退条件

- 固定revision／package／weightsのprovenanceを再現できない。
- Apache-2.0の適用範囲、依存package、checkpoint取得条件に未解決の不明点が残る。
- 必須sliceでseasonal-naiveを改善せず、p95／memoryにも運用上の利点がない。
- known-future契約をBanto Hubのas-of情報で証明できない。
- model unavailable、missing、timeout時に制御系から安全に分離できない。

撤退時も、比較結果と理由を保存し、TimesFM 3.0を製品代替として昇格させません。次候補または軽量baselineへ戻します。

## 8. 公式一次情報

- [Amazon Science: Chronos repository](https://github.com/amazon-science/chronos-forecasting)
- [chronos-forecasting v2.3.1 pyproject.toml](https://github.com/amazon-science/chronos-forecasting/blob/v2.3.1/pyproject.toml)
- [Chronos-2 v2.3.1 pipeline.py](https://github.com/amazon-science/chronos-forecasting/blob/v2.3.1/src/chronos/chronos2/pipeline.py)
- [Chronos-2 model card](https://huggingface.co/amazon/chronos-2)
- [Chronos-2 pinned config.json](https://huggingface.co/amazon/chronos-2/blob/29ec3766d36d6f73f0696f85560a422f50e8498c/config.json)
