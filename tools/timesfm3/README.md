# TimesFM 3専用実行入口

このディレクトリはTimesFM 3の研究専用実行入口です。通常の`banto-ai`依存へ`timesfm`、`torch`、`numpy`を追加しません。

## rolling-origin benchmark

checkpointを`prepare_checkpoint.py`でリポジトリ外cacheへ準備した後、専用venvから次を実行します。

```powershell
python tools/timesfm3/run_benchmark.py `
  --config examples/configs/benchmark-timesfm3-small.json `
  --cache-dir C:\banto-cache\timesfm3 `
  --accept-research-only-license
```

このentrypointは、固定revisionのcheckpoint manifest、許可された4ファイル、`model.safetensors`のサイズ／SHA-256、`timesfm==3.0.0`を確認します。benchmarkへは`TimesFM3Adapter`をfactoryとして注入し、実行中は`HF_HUB_OFFLINE=1`と`HF_HUB_DISABLE_TELEMETRY=1`を強制します。outputはcore runnerのatomic publishとoverwrite拒否に従います。

`benchmark-timesfm3-baselines-past-only.json`は、load_proxyをpast-onlyとして扱う比較です。`benchmark-timesfm3-known-load.json`は、load_proxyの計画値が実設備で確実に取得できる場合を模した、synthetic known-future／oracle-styleの別scenarioです。後者を実績値の先読みとして扱わず、origin時点で計画値が利用可能であることをデータ契約と実験記録で確認してください。どちらもknown-futureはcontext+horizonちょうどで、split境界を越えません。

## benchmark matrix

複数seed／horizon／context lengthの小規模matrixは、同じresearch-only license gate、外部cache、固定revision、offline／package／checkpoint検証を通して実行します。

```powershell
python tools/timesfm3/run_matrix.py `
  --config examples/configs/benchmark-matrix-timesfm3-small.json `
  --cache-dir C:\banto-cache\timesfm3 `
  --accept-research-only-license
```

sampleはpast-onlyの2 seeds×2 horizons×2 context lengthsです。TimesFM adapterのfactoryはmatrix全体で共有され、可能な限りmodelのcold-start重複を避けます。そのため最初のcell以外のcell別latencyは同一process内のwarmな共有instanceを含み、cold-start latencyやmodel単独memoryを表しません。結果は単位別のseed間cell-macro summaryで、Phase 2完了や製品採用の根拠にはなりません。

## MetroPT-3限定比較（実行例）

MetroPT-3の24時間・1設備・3 targetをChronos-2と同一条件で比較する固定configです。TimesFM専用venv、固定lock、リポジトリ外の絶対cacheを使い、必要な場合だけcheckpointを準備します。

```powershell
$timesfmPython = 'environments\timesfm3\.venv\Scripts\python.exe'
& $timesfmPython -m pip install --requirement environments\timesfm3\requirements-windows-cpu-py314.lock
& $timesfmPython tools\timesfm3\preflight.py --cache-dir C:\banto-cache\timesfm3 --format both
# cacheが未準備の場合だけ、次の1行を実行します。
& $timesfmPython tools\timesfm3\prepare_checkpoint.py --cache-dir C:\banto-cache\timesfm3 --accept-research-only-license
& $timesfmPython tools\timesfm3\run_benchmark.py `
  --config examples\configs\benchmark-metropt3-timesfm3.json `
  --cache-dir C:\banto-cache\timesfm3 `
  --manifest examples\manifests\model-license-timesfm3.json `
  --accept-research-only-license
```

`prepare_checkpoint.py`は未準備時だけ実行します。用途は`research-only`かつnon-productionで、公開データ、weights、prediction／実行artifactはGitへ追加しません。Banto Hub／PLCへのwriteは行いません。native quantileに交差があってもsort、clip、fallbackはせず、fail-closedで`partial`として記録します。
