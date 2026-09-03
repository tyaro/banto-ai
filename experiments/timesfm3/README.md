# TimesFM-3 実験

このディレクトリは、[`docs/timesfm-notes.md`](../../docs/timesfm-notes.md) に記載した再現可能な TimesFM-3 benchmark 用です。

TimesFM 3.0のpretrained weightsは、2026-09-03時点で非商用・非本番用途に限定されています。この実験は`research-only`とし、結果や派生成果物をBanto製品、顧客PoC、本番shadowへ昇格しません。

実装済みの範囲:

- 共通`Forecaster` adapter境界
- official APIを模したfake backend tests
- package／checkpoint／licenseのfail-closed検証

未実施の範囲:

- 広範なTimesFM依存・pretrained weights評価
- 単一synthetic windowを超える実モデルprediction
- 実設備に対する精度、calibration、他候補との比較
- 他候補との同一hardware比較

package 3.0.0、wheel SHA-256、checkpoint、immutable revision、code license、weight license、allowed useはmanifestと`environments/timesfm3/package-provenance.json`に記録しています。`requirements.in`はtop-level exact pinであり完全lockではありません。対象hardwareはWindows amd64／CPython 3.14.0／CPUとして確定し、CPU用exact-version lockを作成済みです。hash-pinnedなsupply-chain lockは未作成です。checkpointとpredictionはGitの外に置き、adapterは`local_files_only=True`を既定にします。

Windows amd64／CPython 3.14.0向けには、解決日2026-09-03のexact-version記録`environments/timesfm3/requirements-windows-cpu-py314.lock`も保存しています。これはhash未固定の環境記録であり、専用venvで`python -m pip install --requirement environments\\timesfm3\\requirements-windows-cpu-py314.lock`後に`python -m pip check`を実行して確認します。

専用venv内のread-onlyなoffline／非本番shadow評価に限定し、制御write pathを持たせません。CPU smokeは2回実行済みですが、単一synthetic windowのためPhase 2完了や実モデルの一般性能を示すものではありません。

## CPU smoke評価

次の3段階を明示的に実行します。cacheはリポジトリ外に置き、出力だけを`artifacts/`配下へ新規作成します。

1. `preflight.py`でPython、CPU、RAM、空き容量、optional package、指定cacheの状態を確認する。
2. 必要な場合だけ、license承認付きで`prepare_checkpoint.py`を実行する。
3. `run_smoke.py`で固定された小規模多変量入力を評価し、point予測とp10/p50/p90、実測時間、peak RSS、provenanceを記録する。

実モデルを使うrunはresearch-only／non-productionです。`run_smoke.py`はnetwork fallback、Banto Hubへのwrite、PLCへのwriteを持ちません。cache miss時は明確なエラーとして終了します。正式2回の実測値は[`docs/results/timesfm3-cpu-smoke-2026-09-04.md`](../../docs/results/timesfm3-cpu-smoke-2026-09-04.md)に記録しています。

直線入力のpreliminary smokeは推論経路の成立確認として扱い、正式な採用数値からは除外しました。正式2回の非線形case測定値は[`docs/results/timesfm3-cpu-smoke-2026-09-04.md`](../../docs/results/timesfm3-cpu-smoke-2026-09-04.md)に記録しています。単一windowのため、実設備代表性や性能採否を示しません。
