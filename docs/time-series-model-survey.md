# Banto向け時系列モデル技術調査

調査日: 2026-09-04

## 1. 目的

本書は、Banto ecosystemで扱う設備時系列に対し、予測、異常検知、試運転時の校正、継続的な適応を実現できる技術候補を比較し、`banto-ai`で検証する優先順位を定めるものです。

公開情報だけで製品採用を決定するのではなく、公式リポジトリと公式モデルカードから確認できる機能・利用条件を整理し、Banto固有の合成データと将来の承認済み実データで再評価することを前提とします。

## 2. 結論

研究計画全体は実現可能です。ただし、1つのfoundation modelに、予測、異常検知、continual learning、commissioning auto-tuningのすべてを担当させる構成は採りません。役割を次のように分けるのが現実的です。

| 役割 | 第一候補 | 位置づけ |
| --- | --- | --- |
| 最新性能の研究基準 | TimesFM 3.0 | 高機能だが、現行の学習済み重みは非商用・非本番用途に限定。研究比較専用 |
| 汎用予測の製品候補 | Chronos-2 | 多変量、共変量、分位点予測を備え、Apache-2.0。最初の商用利用可能候補 |
| 軽量・多変量予測 | Toto 2.0 4m／22m | 観測・テレメトリ向け。edge候補として計算量を実測 |
| 設備別fine-tuning | Granite TTM R2 | 約1M parameter級。CPU／laptopで扱いやすく、設備固有適応の候補 |
| 異常検知・補完 | Granite TSPulse R1 | 約1M parameter級。予測ではなく異常検知、補完、分類、類似検索を担当 |
| 学習型baseline | NeuralForecast | N-HiTS、PatchTST、TFT、iTransformerなどを同じ評価系で比較 |
| online適応 | River | drift検知、逐次統計、閾値・profile更新を担当。大型TSFMの逐次再学習には使わない |

最初の同一契約比較対象は `seasonal-naive + Chronos-2 + TimesFM 3.0 + Toto 2.0 4m` とします。Granite TTM R2はcontext／covariate契約が異なるため、別のsensitivity runとして扱います。異常検知では `予測残差 + robust統計 + TSPulse` を比較します。

## 3. Banto側の要求

### 3.1 必須要件

- 複数tagを同時に扱える、または共通adapterでunivariate／multivariateを切り替えられること。
- 点予測だけでなく、正常エンベロープに利用できる分位点または予測区間を出せること。
- speed、load、recipe、operating modeなどの既知情報を共変量として評価できること。
- 欠損、stale data、不規則timestamp、startup／shutdown、regime changeを明示的に扱うこと。
- model、checkpoint、license、preprocessing、dataset split、hardware、metricをrun単位で固定できること。
- Banto Hubとはread-onlyまたはshadow接続とし、PLC値や安全設定を書き換えないこと。
- 顧客データと設備識別情報をGitHubへ置かないこと。

### 3.2 サンプリングと推論周期

Banto Hubが100 ms間隔で収集できても、すべてのraw tagを100 msごとにfoundation modelへ入力する必要はありません。最初は次の二層構成とします。

```text
100 ms raw collection
  -> quality check / windowing / feature extraction
  -> 1～10 s cadenceの非同期forecast・anomaly inference
  -> shadow resultをBanto Hubへ返す
```

振動・音響のような高周波信号は、raw waveformを汎用forecast modelへ直接投入せず、RMS、peak、kurtosis、crest factor、band power、FFT特徴などへ変換する経路と、TSPulse等の専用表現を比較します。

## 4. 候補比較

機能とライセンスは2026-09-03時点の公式情報です。ライセンス欄は法的助言ではなく、技術選定前の一次確認です。採用時には対象version、コード、重み、依存packageを改めて棚卸しします。

| 候補 | 主用途 | 規模の目安 | 多変量 | 共変量 | 確率／分位点 | 公開条件 | Bantoでの判断 |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| TimesFM 3.0 | zero-shot予測 | 0.3B | native | 過去のみ／既知未来 | 9分位点 | コードApache-2.0、重みはTimesFM Non-Commercial License v1.0 | 研究比較のみ |
| TimesFM 2.5 | zero-shot予測 | 200M + optional head | 基本は系列単位 | XReg | optional quantile head | Apache-2.0 | TimesFM系の商用可能fallback候補 |
| Chronos-2 | zero-shot汎用予測 | 120M encoder-only | native | 過去／既知未来 | native quantile | package／code／weights Apache-2.0 | TimesFM 3.0評価後のcommercial-evaluation候補 |
| Toto 2.0 | observability予測 | 4M～2.5B | native | 2.0では未対応 | quantile head | Apache-2.0 | 4M／22Mをedge候補として評価 |
| Granite TTM R2 | 小型予測・fine-tuning | 約0.8～1M級 | zero-shot／fine-tuning | zero-shotのpast-only活用は別契約 | native quantileなし・主に点予測 | Apache-2.0 | context=512／target-only sensitivity候補 |
| Granite TSPulse R1 | 異常・補完・分類 | 約1M | 対応 | タスク依存 | forecast modelではない | Apache-2.0 | 異常検知の第一候補 |
| MOMENT-1 | 汎用表現 | model variant依存 | 対応 | 限定的 | task依存 | MIT | 研究用の汎用比較候補 |
| Moirai 2.0 small | zero-shot予測 | 11.4M | common adapterで要確認 | common adapterで要確認 | quantile loss | CC-BY-NC-4.0 | 非商用比較のみ |
| NeuralForecast | supervised予測 | model依存 | model依存 | 対応modelあり | lossにより対応 | Apache-2.0 | 必須の学習型baseline |
| River | online ML | algorithm依存 | pipeline次第 | 対応 | algorithm次第 | BSD-3-Clause | drift・逐次校正用 |

## 5. 主要候補の評価

### 5.1 TimesFM 3.0

TimesFM 3.0はnative multivariate、過去のみ／既知未来の動的共変量、点予測と0.1～0.9の9分位点を備え、Bantoが必要とする機能との一致度は高いです。0.3B parameter、F32のため、対象hardware上のlatencyとmemoryは実測が必要です。

最大の制約はライセンスです。公式リポジトリのコードはApache-2.0ですが、TimesFM 3.0のpretrained weightsは `timesfm-non-commercial-license-v1.0` で、現時点では非商用・非本番用途に限定されています。そのため、次の用途に限ります。

- 合成／公開データ上の性能比較
- multivariate、covariate、quantile APIの設計参考
- 他の商用利用可能候補に対する研究上限の確認

製品への組み込み、顧客PoC、本番shadow運転への持ち込みは、利用条件が変わるか別途権利を得るまで行いません。

### 5.2 TimesFM 2.5

TimesFM 2.5は200M parameter、最大16k context、最大1k horizonのcontinuous quantile forecast用optional head、XRegによる共変量対応を持ち、重みもApache-2.0です。一方、TimesFM 3.0のnative multivariateと同じ入力構造ではありません。

TimesFM方式を商用利用可能な条件で残すfallbackとして価値がありますが、Chronos-2、Toto、TTMより優先するかはBantoデータ上の精度・速度で決めます。

### 5.3 Chronos-2

Chronos-2は120M parameterのencoder-only modelで、zero-shotのunivariate、multivariate、past-only／known-future covariate forecastingとnative quantile outputを1つのAPIで扱えます。max contextは8192、max predictionは1024で、CPU／GPUのdeployment経路があります。package、repository code、`amazon/chronos-2` weightsは、今回固定した公式情報上でApache-2.0です。

Bantoでは、TimesFM 3.0に近い機能を商用利用可能な条件で比較できる候補です。最初の汎用forecast adapterをChronos-2で実装し、CPU p95 latency、memory、共変量の効果、p50整合、欠損挙動を測定します。ただしライセンス確認だけで製品採用とはせず、実性能・運用検証前は`commercial-evaluation`に固定します。

#### Chronos-2固定契約（2026-09-04確認）

- package: `chronos-forecasting==2.3.1`。依存環境は専用venv／cacheへ隔離し、core runtimeへ持ち込まない。
- checkpoint: `amazon/chronos-2@29ec3766d36d6f73f0696f85560a422f50e8498c`。revisionを省略したlatest取得は禁止する。
- 実行: CPU／GPUを`device_map`で明示し、初期設定は`batch_size=1`、`context_length=12`、`local_files_only=true`とする。
- point契約: 公式`predict_quantiles`の戻り値の変数名`mean`は算術平均ではなくmedian／p50として、Bantoの`point_forecast`へ対応付ける。
- 共変量: past-onlyはorigin直前まで、known-futureはorigin時点で実際に確定していた計画値だけを渡す。評価期間の実績値を埋め戻すoracle leakageは認めない。
- 欠損: 初期adapterは補間、forward fill、暗黙のmask処理を行わず、missing／stale／不規則timestamp／長さ不一致をfail closedとする。耐性を主張するには別実験と証跡が必要。
- 利用判断: 現段階は`commercial-evaluation`。product-candidateへの昇格には精度、calibration、resource、再現性、degraded state、データ／ライセンス証跡のGateを通す。

### 5.4 Toto 2.0

Toto 2.0はobservability metricsを主対象とし、time attentionとvariate attentionを交互に使うmultivariate modelです。4M、22M、313M、1B、2.5Bがあり、quantile headと高次元series対応を持ちます。今回の初回実装対象はCPU向け4Mだけです。

Bantoの多数tagを扱う用途と相性が期待できます。現行2.0はfine-tuningとexogenous variableに未対応であり、それらが必要な実験ではToto 1.0または別候補を使います。公式要件はPython 3.12+、PyTorch 2.5+で、最適性能にはCUDA-capable deviceが推奨されています。初回adapterは`toto-2==2.0.0`／`toto-models==1.0.0`、HF 4M固定revision、native p10／p50／p90、commercial-evaluationに固定します。

### 5.5 Granite TTM R2

Tiny Time Mixersは約1M parameterからの小型pretrained forecasting modelで、zero-shot、few-shot／fine-tuning、multivariate channel mixing、exogenous／control variableを扱えます。現行 package は `granite-tsfm==0.3.9`（Python >=3.11,<3.14、Apache-2.0）です。R2.1には context 52／90／180／360／512 系があり、context=120／horizon=15の標準get_modelは `90-30-ft-r2.1`（revision `6e5cb8ee51e0634a45637490f5db43148b2fa6be`）を選び実効context=90となるため、現行MetroPT-3の120点同一契約ではありません。zero-shotではpast-only covariatesをTimesFM／Chronosと同じ意味で利用できず、native quantileもありません。

短い系列へのzero prependは公式cardが非推奨であり、180モデルへ左zero paddingして120点契約を合わせる方式は採用しません。次候補はcontext=512／horizon=15、`512-48-ft-r2.1`（revision `b972f0c22190b7502764526004d16e2b4ed39e8c`）のtarget-only／covariate-ablated sensitivity runです。これは標準同一契約benchmarkとは別集計にします。Bantoの1秒以下の信号にそのまま適合する保証もないため、resampleと設備別fine-tuningの効果は別途検証します。

### 5.6 Granite TSPulse R1

TSPulseは約1M parameterのGPU-free modelで、anomaly detection、imputation、classification、similarity searchを対象とします。時間領域と周波数領域を共同で扱うため、設備信号の異常パターン検出候補として有望です。

forecast modelの代替ではありません。予測残差方式、robust z-score／EWMA方式と同じevent splitで比較し、誤警報数、incident recall、検知リードタイム、欠損補完品質を測ります。

### 5.7 NeuralForecastと自前mini-Transformer

Foundation modelが有効かを判断するには、対象データで学習するN-HiTS、PatchTST、TFT、iTransformer等と、単純な自前モデルが必要です。NeuralForecastは外生変数とprobabilistic lossを扱えるmodelを含み、Apache-2.0です。

自前mini-Transformerは「最先端性能」を目標にせず、次を理解・検証するために使います。

- channel mixingの効果
- operating mode／recipe featureの効果
- quantile lossとcalibration
- model sizeとlatencyの関係
- 異常期間が学習データへ混入したときの影響

### 5.8 River

Riverは逐次学習、drift検知、anomaly、forecastingを含むonline ML libraryです。Bantoでは、大型foundation modelを観測ごとに再学習するためではなく、次の小さくrollback可能な適応に使います。

- mean／variance／quantileの逐次更新
- forecast bias補正
- residual thresholdとpersistenceの調整
- drift detectorによる再校正要求
- commissioning profileの候補生成

Production modeでは更新をlockし、Commissioningまたはoffline replayだけで候補を作ります。

## 6. 評価基盤

### 6.1 fev

`fev`はpoint／probabilistic forecast、各種共変量、rolling window、dataset fingerprintを扱えるApache-2.0の軽量評価libraryです。Banto独自dataset adapterを作りやすいため、共通benchmark harnessの第一候補とします。

### 6.2 GIFT-Eval

GIFT-Evalは秒～年粒度、univariate／multivariate、短期／長期、probabilistic forecastを含み、test-data leakageも追跡します。公開データ上で一般性能を確認する補助benchmarkとして使い、Banto向け合成benchmarkの代替にはしません。

## 7. 実現可能性

| 項目 | 判定 | 条件 |
| --- | --- | --- |
| 合成データによるoffline比較 | 高 | generator、manifest、共通metricを先に固定する |
| Banto Hubのread-only export連携 | 高 | 既存の時系列query／export境界を利用し、IDと単位を固定する |
| Python sidecarによるshadow推論 | 高 | 非同期window処理、degraded state、timeoutを実装する |
| Chronos-2のCPU推論 | 中 | target hardware上でp95 latencyとmemoryを計測する |
| Toto 4M／22M、TTM、TSPulseのCPU利用 | 中～高 | sampling、batch、thread数を含めて実測する |
| commissioning profile自動生成 | 中～高 | base model再学習ではなく、正規化、bias、interval、thresholdの校正から始める |
| 本番中のcontinual learning | 中以下 | frozen base + versioned profile + rollbackに限定する |
| AIからPLCへの直接書き込み | 対象外 | 安全と制御の権威はPLC／Banto Hub側に残す |

## 8. 推奨アーキテクチャ

研究段階はPython sidecarが最短です。Banto Hubの収集・保存・認可を再実装せず、共通契約の内側でmodelだけを交換します。

```text
Banto Hub / approved export
        |
        v
dataset + quality adapter
        |
        +--> common Forecaster interface
        |      +--> naive / NeuralForecast
        |      +--> Chronos-2
        |      +--> TimesFM 3.0 (research only)
        |      +--> Toto / TTM
        |
        +--> common AnomalyDetector interface
               +--> robust residual
               +--> TSPulse
               +--> River drift detector
        |
        v
versioned report / profile candidate / shadow result
```

Rust／ONNX等への移行は、採用modelとtarget hardwareが決まってから検討します。研究初期にruntime変換を先行させません。

## 9. 主なリスクと対策

| リスク | 対策 |
| --- | --- |
| benchmark上位が設備データでも強いとは限らない | Banto固有のregime、欠損、fault、samplingを含む評価を主判定にする |
| pretrained dataとの重複やleakage | dataset provenanceと公開benchmarkのleakage情報をmanifestへ記録する |
| 合成データだけに最適化する | 公開産業データ、後日の承認済み実データ、cross-equipment splitを段階的に追加する |
| 分位点が未校正 | empirical coverage、WIS、coverage errorを測り、必要なら後段校正する |
| 高周波データで計算量が膨らむ | resampling、event-driven inference、特徴抽出、軽量modelを比較する |
| 異常を正常として継続学習する | mode gate、alarm／maintenance除外、holdout、human approval、rollbackを必須にする |
| model／weight licenseの取り違え | codeとweightsを別項目で記録し、非商用modelをartifact promotion対象外にする |

## 10. 採用判断

現時点の判断は次のとおりです。

1. TimesFM 3.0は研究比較に採用するが、製品候補にはしない。
2. Chronos-2を汎用forecastの第一製品候補とする。
3. Toto 2.0 4m／22mとGranite TTM R2をedge／設備別適応候補として同時評価する。
4. 異常検知はforecast residualだけに依存せず、TSPulseと統計baselineを比較する。
5. continual learningはmodel本体の無制限更新ではなく、frozen base model + versioned calibration profileで開始する。
6. 比較結果が出るまで単一modelへAPIを固定せず、共通interfaceの背後で差し替える。

具体的な作業順と完了条件は [`research-implementation-plan.md`](research-implementation-plan.md) に定めます。

## 11. 公式情報源

- [Google Research: TimesFM](https://github.com/google-research/timesfm)
- [TimesFM 3.0 model card](https://huggingface.co/google/timesfm-3.0-pytorch)
- [TimesFM 2.5 model card](https://huggingface.co/google/timesfm-2.5-200m-pytorch)
- [Amazon Science: Chronos](https://github.com/amazon-science/chronos-forecasting)
- [Chronos 2.3.1 package metadata](https://github.com/amazon-science/chronos-forecasting/blob/v2.3.1/pyproject.toml)
- [Chronos-2 v2.3.1 pipeline](https://github.com/amazon-science/chronos-forecasting/blob/v2.3.1/src/chronos/chronos2/pipeline.py)
- [Chronos-2 model card](https://huggingface.co/amazon/chronos-2)
- [Chronos-2 pinned config](https://huggingface.co/amazon/chronos-2/blob/29ec3766d36d6f73f0696f85560a422f50e8498c/config.json)
- [Datadog: Toto](https://github.com/DataDog/toto)
- [Toto 2.0 4m model card](https://huggingface.co/Datadog/Toto-2.0-4m)
- [Toto 2.0 22m model card](https://huggingface.co/Datadog/Toto-2.0-22m)
- [IBM Granite TSFM](https://github.com/ibm-granite/granite-tsfm)
- [Granite TTM R2 model card](https://huggingface.co/ibm-granite/granite-timeseries-ttm-r2)
- [Granite TSPulse R1 model card](https://huggingface.co/ibm-granite/granite-timeseries-tspulse-r1)
- [MOMENT](https://github.com/moment-timeseries-foundation-model/moment)
- [Moirai 2.0 small model card](https://huggingface.co/Salesforce/moirai-2.0-R-small)
- [NeuralForecast](https://github.com/Nixtla/neuralforecast)
- [River](https://github.com/online-ml/river)
- [fev](https://github.com/autogluon/fev)
- [GIFT-Eval](https://github.com/SalesforceAIResearch/gift-eval)
- [Banto Industrial](https://github.com/tyaro/banto-industrial)
