# Toto 2.0 4M の隔離実行

この入口は Datadog の `toto-2==2.0.0`（umbrella package `toto-models==1.0.0`）と、HF の固定 revision `8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9` による CPU 評価専用です。コード／重みはいずれも Apache-2.0 ですが、利用区分は `commercial-evaluation` に固定し、本番制御や Banto Hub／PLC write は行いません。

専用環境は [`environments/toto2/requirements.in`](../../environments/toto2/requirements.in) と、実際に解決・検証した [`requirements-windows-cpu-py314.lock`](../../environments/toto2/requirements-windows-cpu-py314.lock) を使います。モデル重みとデータは repository 外に置きます。

```powershell
py -3.14 -m venv ..\.venv-banto-ai-toto2
$totoPython = '..\.venv-banto-ai-toto2\Scripts\python.exe'
& $totoPython -m pip install --upgrade pip
& $totoPython -m pip install -r environments\toto2\requirements-windows-cpu-py314.lock
& $totoPython tools\toto2\preflight.py --cache-dir C:\banto-cache\toto2 --format both
& $totoPython tools\toto2\prepare_checkpoint.py --cache-dir C:\banto-cache\toto2 --accept-apache-2.0
& $totoPython tools\toto2\run_smoke.py --cache-dir C:\banto-cache\toto2 --output artifacts\toto2\cpu-smoke.json
& $totoPython tools\toto2\run_benchmark.py --config examples\configs\benchmark-metropt3-toto2-4m.json --cache-dir C:\banto-cache\toto2
```

実行開始後は network を禁止し、cache snapshot の sibling set、revision、`model.safetensors` の exact size/SHA-256、package version、license を検証します。短い horizon の公式推奨どおり `decode_block_size=None`、CPU、batch=1 を固定します。Toto 2.0 は current 2.0 で fine-tuning／exogenous variable をサポートしないため、known-future covariate request は fail closed です。MetroPT-3 の context=120 は変えず、patch_size=32 に合わせて adapter 内で先頭8点を未観測 padding し、effective model input length=128 とします。実測値を padding に使わず、実入力の missing／stale／irregular／nonfinite は拒否します。

この初回追加では4MのCPU smokeとMetroPT-3 benchmarkを実行済みです。結果は[`docs/results/toto2-metropt3-evaluation-2026-09-04.md`](../../docs/results/toto2-metropt3-evaluation-2026-09-04.md)を参照してください。22M、matrix、fine-tuning、seed拡大、fault slice、実設備一般化は対象外です。
