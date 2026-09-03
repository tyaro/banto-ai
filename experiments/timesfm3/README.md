# TimesFM-3 実験

このディレクトリは、[`docs/timesfm-notes.md`](../../docs/timesfm-notes.md) に記載した再現可能な TimesFM-3 benchmark 用です。

TimesFM 3.0のpretrained weightsは、2026-09-03時点で非商用・非本番用途に限定されています。この実験は`research-only`とし、結果や派生成果物をBanto製品、顧客PoC、本番shadowへ昇格しません。

実装済みの範囲:

- 共通`Forecaster` adapter境界
- official APIを模したfake backend tests
- package／checkpoint／licenseのfail-closed検証

未実施の範囲:

- TimesFM依存とpretrained weightsの導入
- 実モデルによるprediction
- 精度、calibration、速度、peak memory、artifact sizeの測定
- 他候補との同一hardware比較

package 3.0.0、wheel SHA-256、checkpoint、immutable revision、code license、weight license、allowed useはmanifestと`environments/timesfm3/package-provenance.json`に記録しています。`requirements.in`はtop-level exact pinであり完全lockではありません。対象hardware決定後にCPU／CUDA別lockを生成・検証します。checkpointとpredictionはGitの外に置き、adapterは`local_files_only=True`を既定にします。

実行する場合も専用venv内のread-onlyなoffline／非本番shadow評価に限定し、制御write pathを持たせません。現状はadapter契約の実装段階であり、Phase 2完了や実モデル性能を示すものではありません。
