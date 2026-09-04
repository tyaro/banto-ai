# Chronos-2専用隔離環境

このディレクトリは、Banto ecosystem向けにAmazon Chronos-2を評価する専用Python環境の入力・来歴を管理します。`banto-ai`のcore runtimeへ、Chronos、PyTorch、Transformersなどの重い依存を追加しません。

## 固定値

- package: `chronos-forecasting==2.3.1`
- package wheel SHA-256: `d9d00ec9b1621235bfb26685638bf054885f4c000863678f1c775dfab2697496`
- package/code license: Apache-2.0
- checkpoint: `amazon/chronos-2`
- revision: `29ec3766d36d6f73f0696f85560a422f50e8498c`
- checkpoint files: `README.md`, `config.json`, `model.safetensors`だけ
- `model.safetensors`: 477,930,472 bytes / SHA-256 `ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42`
- 現段階の用途: `commercial-evaluation`

依存の宣言は`requirements.in`、来歴と固定ハッシュは`package-provenance.json`にあります。`requirements-windows-cpu-py314.lock`はrepository外の専用venvでpip freezeして作成し、Python 3.14.0、Windows amd64、CPU環境でimport、`torch.version.cuda=None`、`pip check`を2026-09-04に実機検証した完全なversion lockです。distribution hashを含むhash lockではありません。

公式実装の依存範囲は、`torch>=2.2,<3`、`transformers>=4.41,<6`、`accelerate>=1.1,<2`、`numpy>=1.21,<3`、`einops>=0.7,<1`、`pandas>=2,<4`です。これらも専用venvだけに入れます。

## セットアップと境界

cacheは必ずリポジトリ外の既存または作成可能な絶対パスを指定します。顧客データ、weights、予測artifactはGit管理しません。

```powershell
python -m venv .venv-chronos2
.venv-chronos2\Scripts\python.exe -m pip install --upgrade pip
.venv-chronos2\Scripts\python.exe -m pip install -r environments\chronos2\requirements.in
.venv-chronos2\Scripts\python.exe -m pip check
.venv-chronos2\Scripts\python.exe tools\chronos2\preflight.py --cache-dir C:\banto-cache\chronos2 --format both
.venv-chronos2\Scripts\python.exe tools\chronos2\prepare_checkpoint.py --cache-dir C:\banto-cache\chronos2 --accept-apache-2.0
```

`prepare_checkpoint.py`だけがnetworkを使う取得入口です。固定revisionと固定allow patternsで取得し、取得後にファイル集合・サイズ・SHA-256を検証します。WindowsでXetの並列socket取得に失敗する場合に備え、取得時は`HF_HUB_DISABLE_XET=1`と`max_workers=1`を固定しています。受諾オプションなしではcacheの作成やdownloadを行いません。

`run_smoke.py`、`run_benchmark.py`、`run_matrix.py`は、実行中に`HF_HUB_OFFLINE=1`、telemetry無効、`local_files_only=True`を強制します。package version、revision、cache内checkpointの実体を再検証し、失敗時は利用を拒否します。ベンチマークのChronos adapterは全equipmentで1個を共有し、分位点はChronos native outputだけを使用します。

## 最小実行例

```powershell
.venv-chronos2\Scripts\python.exe tools\chronos2\run_smoke.py `
  --cache-dir C:\banto-cache\chronos2 `
  --output artifacts\chronos2\cpu-smoke.json

.venv-chronos2\Scripts\python.exe tools\chronos2\run_benchmark.py `
  --config examples\configs\benchmark-small.json `
  --cache-dir C:\banto-cache\chronos2 `
  --manifest examples\manifests\model-license-chronos2.json
```

smokeは小さなmultivariate target、past-only covariate、known-future covariateを含み、結果をmachine-readable JSONで出力します。これは動作確認であり、実設備の性能や製品採用の根拠ではありません。AI出力からPLCの安全・制御write pathへ接続する機能はありません。
