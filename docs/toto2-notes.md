# Toto 2.0 4M 実装・評価ノート

Toto 2.0 4M は Datadog の multivariate foundation model です。今回の adapter は `toto-2==2.0.0`、umbrella `toto-models==1.0.0`、checkpoint `Datadog/Toto-2.0-4m@8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9` に固定します。PyPI wheel SHA-256、HF API で確認した全 sibling と推論・license 証跡用の required sibling（`README.md`、`config.json`、`model.safetensors`）、`model.safetensors` 16,582,848 bytes（16582848 bytes）／SHA-256 `316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e` は [`environments/toto2/package-provenance.json`](../environments/toto2/package-provenance.json) に記録しています。package provenance の公式 source commit は `toto-2/v2.0.0` の dereference commit `44ea4e88852228039564aa3e76fac26aafac0803` です。

## 入出力契約

Toto は input `batch × variates × time`、output `quantiles × batch × variates × horizon`、quantiles `0.1..0.9` を使います。Banto の target と past-only covariates を一つの multivariate input にし、全 variates を同時予測しますが、結果には target だけを返します。current 2.0 は fine-tuning と exogenous／known-future covariates に対応しないため、known-future request は拒否します。

MetroPT-3 の既存契約は context=120、horizon=15、targets=`tp3`／`oil_temperature`／`motor_current`、past-only covariates=11 のままです。checkpoint config の `patch_size=32` に合わせ、120点の先頭へ8点の未観測 padding を内部追加して effective model input length=128 とします。padding は zeros を実値として扱わず mask=false とし、公式呼出しは `has_missing_values=True`。これはデータ欠損の許容ではなく、観測120点は quality、finite、regular timestamp を満たす必要があります。

## 安全境界

core import 時には torch、numpy、toto2、huggingface_hub を import しません。外部 cache の固定 snapshot と license／package provenance を benchmark 前に検証し、benchmark 開始後は `local_files_only=True`、CPU、batch=1、`decode_block_size=None`、offline／telemetry-disabled を強制します。quantile crossing、nonfinite、output shape の異常は補正せず失敗にします。重み、データ、生成 artifact は Git 管理対象外です。

## 評価範囲と実測結果

初回対象の Toto 4M は既存runnerへ接続し、固定snapshotを使ったCPU smokeとMetroPT-3数値benchmarkを実行済みです。statusは`success`、predictionは4,320、failureは0で、target別metricsとruntimeは[`docs/results/toto2-metropt3-evaluation-2026-09-04.md`](results/toto2-metropt3-evaluation-2026-09-04.md)に記録しています。main環境のREADME記載direct invocationは既存cacheで実成功し、size／SHA-256を再検証済みです。automated subprocessは4 scriptの相対／absolute pathを`--help`で確認し、accept flagからprepare_checkpointへの到達は`python -c`＋mockでdownloadなしに確認済みです。22M、fine-tuning、seed拡大、fault slice、実設備一般化は次工程であり、今回の限定評価から製品採用を判断しません。

同日、Toto 2.0 4Mの小規模matrixも実測しました。seed `[17, 42]` × horizon `[15, 30]` × context `[64, 120]`の8 cellで、2 equipment、各seed 480 samples／equipment、各equipment validation／test各2 origins、全6 modelsを評価し、8/8 success、partial 0、failed 0でした。正本、8条件のtarget別cell-macro metrics、origin、runtime、memory、制約は[`docs/results/toto2-matrix-2026-09-04.md`](results/toto2-matrix-2026-09-04.md)に記録しています。既存predictionのevent slice post-hoc解析も完了し、詳細と次gateは[`docs/results/toto2-event-slices-2026-09-04.md`](results/toto2-event-slices-2026-09-04.md)に記録しています。次はseed／origin／event位置／設備／mode拡大、missing／stale／fault専用scenario、event単位不確実性、model-only resource測定、22M、公開／実設備一般化です。Phase 2は未完了です。
