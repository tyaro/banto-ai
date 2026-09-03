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

sample configでは`load_proxy`をpast-onlyにしています。将来値をknown-futureとして渡す場合は、本番で計画値としてorigin時点に確実に取得可能であることを別のデータ契約と実験記録で確認してください。
