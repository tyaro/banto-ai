# Chronos-2専用実行ツール

ここにあるentrypointは、Chronos-2をcore runtimeから隔離して評価するためのものです。全ツールは明示された外部cacheだけを使用し、実行時はCPU・offline・`local_files_only=True`に固定します。

## 実行順序

```powershell
python tools\chronos2\preflight.py --cache-dir C:\banto-cache\chronos2 --format both
python tools\chronos2\prepare_checkpoint.py --cache-dir C:\banto-cache\chronos2 --accept-apache-2.0
python tools\chronos2\run_smoke.py --cache-dir C:\banto-cache\chronos2 --output artifacts\chronos2\smoke.json
python tools\chronos2\run_benchmark.py --config <repository-relative-config.json> --cache-dir C:\banto-cache\chronos2
python tools\chronos2\run_matrix.py --config examples/configs/benchmark-matrix-chronos2-small.json --cache-dir C:\banto-cache\chronos2
```

`prepare_checkpoint.py`以外はnetworkを使いません。prepareも`--accept-apache-2.0`がない限りdownloadを呼ばず、固定revision、`README.md`／`config.json`／`model.safetensors`だけのallow patterns、実ファイルのサイズとSHA-256を検証します。Windows Xet並列取得でsocket errorが出る場合に備え、prepareは`HF_HUB_DISABLE_XET=1`と`max_workers=1`を固定します。既存artifactを上書きしません。

`run_benchmark.py`のfactoryは全equipmentに対してChronos2Adapterを一つだけ共有します。single-runのquantile policyは`native`と`validation-residual-by-lead`を受け付けます。`native`は公式分位点をそのまま検証し、交差時は補正せず`partial`とします。`validation-residual-by-lead`は公式point-only予測とvalidation residual by lead校正を使う別scenarioです。`run_matrix.py`は`native`限定を維持し、coreの擬似分位点推定へfallbackしません。`run_smoke.py`はmultivariate target、past-only covariate、known-future covariateを一つの決定的requestに含め、予測とbaselineをJSONに保存します。

小規模matrixは、seeds `[17, 42]`×horizons `[1, 3]`×context lengths `[6, 12]`の8 cellsです。base benchmarkのmodel parameter `context_length=12`はChronos backendへ渡す入力上限であり、matrix axisの`context_lengths`は各cellで実際に切り出す入力長です。6と12はいずれもこの上限内です。matrix全体でChronos2Adapterを一つだけ共有し、固定revision、CPU、local-only、検証済み外部cache、固定package versionを要求します。dataset、benchmark、matrixの各出力はChronos専用pathへ分離され、既存出力が一つでもある場合は上書きせず停止します。

このディレクトリはcore CIから直接importされず、`chronos-forecasting`、PyTorch、Transformersなどを通常の`banto-ai`依存に追加しません。checkpointと実行artifactはリポジトリ外cacheまたはGit管理対象外のartifactへ置いてください。

## MetroPT-3限定評価

MetroPT-3公開実データの24時間限定・forecastのみの比較には、専用venv、リポジトリ外cache、固定configを使います。

```powershell
py -3.14 -m venv ..\.venv-banto-ai-chronos2
$chronosPython = '..\.venv-banto-ai-chronos2\Scripts\python.exe'
& $chronosPython -m pip install -r environments\chronos2\requirements-windows-cpu-py314.lock
& $chronosPython tools\chronos2\preflight.py --cache-dir C:\banto-cache\chronos2 --format both
& $chronosPython tools\chronos2\run_benchmark.py `
  --config examples\configs\benchmark-metropt3-chronos2.json `
  --cache-dir C:\banto-cache\chronos2 `
  --manifest examples\manifests\model-license-chronos2.json
```

用途は`commercial-evaluation`に限り、製品採用の根拠にはしません。Banto Hub／PLCへのwriteは行いません。公開データ本体、model weight、実行artifactはGitへ追加しないでください。

native分位点に交差があっても値の並べ替え・clipは行わず、該当model／targetをfail-closedで`partial`として記録します。`benchmark-metropt3-chronos2-point-calibrated.json`は、point予測にvalidation residual by leadの校正を適用する別scenarioです。
