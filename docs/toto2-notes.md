# Toto 2.0 4M 実装・評価ノート

Toto 2.0 4M は Datadog の multivariate foundation model です。今回の adapter は `toto-2==2.0.0`、umbrella `toto-models==1.0.0`、checkpoint `Datadog/Toto-2.0-4m@8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9` に固定します。PyPI wheel SHA-256、HF API で確認した全 sibling と推論・license 証跡用の required sibling（`README.md`、`config.json`、`model.safetensors`）、`model.safetensors` 16,582,848 bytes（16582848 bytes）／SHA-256 `316660d5afb47943e531f39242e0b02ca0b8bb73be5709dfe07ca80dfce9805e` は [`environments/toto2/package-provenance.json`](../environments/toto2/package-provenance.json) に記録しています。package provenance の公式 source commit は `toto-2/v2.0.0` の dereference commit `44ea4e88852228039564aa3e76fac26aafac0803` です。

## 入出力契約

Toto は input `batch × variates × time`、output `quantiles × batch × variates × horizon`、quantiles `0.1..0.9` を使います。Banto の target と past-only covariates を一つの multivariate input にし、全 variates を同時予測しますが、結果には target だけを返します。current 2.0 は fine-tuning と exogenous／known-future covariates に対応しないため、known-future request は拒否します。

MetroPT-3 の既存契約は context=120、horizon=15、targets=`tp3`／`oil_temperature`／`motor_current`、past-only covariates=11 のままです。checkpoint config の `patch_size=32` に合わせ、120点の先頭へ8点の未観測 padding を内部追加して effective model input length=128 とします。padding は zeros を実値として扱わず mask=false とし、公式呼出しは `has_missing_values=True`。これはデータ欠損の許容ではなく、観測120点は quality、finite、regular timestamp を満たす必要があります。

## 安全境界

core import 時には torch、numpy、toto2、huggingface_hub を import しません。外部 cache の固定 snapshot と license／package provenance を benchmark 前に検証し、benchmark 開始後は `local_files_only=True`、CPU、batch=1、`decode_block_size=None`、offline／telemetry-disabled を強制します。quantile crossing、nonfinite、output shape の異常は補正せず失敗にします。重み、データ、生成 artifact は Git 管理対象外です。

## 評価範囲

初回は Toto 4M のみを既存 runner に接続します。22M、matrix、fine-tuning、実 model download／MetroPT-3 数値 benchmark はこの実装コミットの必須範囲外です。CPU fake-backend smoke と tool／docs の契約テストで実装を検証し、実測値を性能結論として文書化しません。
