# TimesFM 3 隔離環境

このディレクトリはTimesFM 3.0を研究比較するための専用Python環境の入力と来歴を管理します。core runtimeへML依存を追加する場所ではありません。

## 固定している範囲

- top-level requirementは`timesfm[torch]==3.0.0`です。
- Windows amd64／CPython 3.14.0で解決したexact-version入力は`requirements-windows-cpu-py314.lock`です。
- PyPI wheelの確認済みSHA-256とcheckpointのimmutable revisionは`package-provenance.json`に記録します。
- adapterは`local_files_only=True`を既定とし、暗黙のcheckpoint downloadやfallbackを許可しません。
- official `ModelConfig`には明示cache_dirを渡し、predict設定は`make_positive=False`、`use_znorm=False`、`univariate=False`を固定します。
- checkpointとmodel cacheはGit外に置きます。weights、prediction、実測artifactをこのリポジトリへcommitしません。

`requirements.in`はtop-level packageのexact pinであり、完全なtransitive lockではありません。対象hardwareはWindows amd64／CPython 3.14.0／CPUとして確定し、CPU用のexact-version lockを作成済みです。hash-pinnedなsupply-chain lockは未作成です。CUDA用lockは今回の対象外です。

`requirements-windows-cpu-py314.lock`は2026-09-03に解決したWindows amd64／CPython 3.14.0／CPU-only環境の記録です。versionはexactですが、package hashは未固定です。専用venvを有効化した後、次で再現性と依存整合性を確認します。

```powershell
python -m pip install --requirement environments\timesfm3\requirements-windows-cpu-py314.lock
python -m pip check
```

このlockの導入自体は実評価の必須操作ではなく、親agentが明示的に実行する環境準備です。

## 実行境界

実行時はcore用環境と共有せず、TimesFM専用venvを使用します。weights licenseにより用途は`research-only`かつnon-productionです。Banto HubやPLCへの制御write pathは持たせず、read-onlyのoffline評価または非本番shadow評価に限定します。

専用のWindows CPU環境で実モデルsmokeを2回実行済みです。速度とPeak RSS、および単一synthetic window上の指標は結果文書に記録していますが、実設備性能や一般性能を示すものではありません。

## CPU smoke評価の実行境界

cache pathは毎回、リポジトリ外の絶対パスで明示します。preflightは指定されたcache pathだけを確認し、リポジトリや顧客データを探索しません。

```powershell
python tools/timesfm3/preflight.py --cache-dir C:\banto-cache\timesfm3 --format both
python tools/timesfm3/prepare_checkpoint.py --cache-dir C:\banto-cache\timesfm3 --accept-research-only-license
python tools/timesfm3/run_smoke.py --cache-dir C:\banto-cache\timesfm3 --output artifacts\timesfm3\cpu-smoke.json
```

`prepare_checkpoint.py`だけが明示的なdownload入口です。`run_smoke.py`は`local_files_only=True`で動作し、cache miss時にnetwork fallbackしません。実行artifactは新規JSONとしてatomicに公開し、既存ファイルの上書きを拒否します。正式2回のCPU smoke実測値は結果文書に記録済みです。

checkpoint準備は`snapshot_download`の対象を`config.json`、`model.safetensors`、`LICENSE`、`README.md`に固定し、取得後に`model.safetensors`のサイズ1,322,898,824 bytesとSHA-256を検証します。期待値は`package-provenance.json`で管理します。
