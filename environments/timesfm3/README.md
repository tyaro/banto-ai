# TimesFM 3 隔離環境

このディレクトリはTimesFM 3.0を研究比較するための専用Python環境の入力と来歴を管理します。core runtimeへML依存を追加する場所ではありません。

## 固定している範囲

- top-level requirementは`timesfm[torch]==3.0.0`です。
- PyPI wheelの確認済みSHA-256とcheckpointのimmutable revisionは`package-provenance.json`に記録します。
- adapterは`local_files_only=True`を既定とし、暗黙のcheckpoint downloadやfallbackを許可しません。
- checkpointとmodel cacheはGit外に置きます。weights、prediction、実測artifactをこのリポジトリへcommitしません。

`requirements.in`はtop-level packageのexact pinであり、完全なtransitive lockではありません。Torch、CUDA、platform固有wheelを含む完全lockは、対象hardwareを確定した後にCPU用とCUDA用を分けて生成し、それぞれの環境で検証します。

## 実行境界

実行時はcore用環境と共有せず、TimesFM専用venvを使用します。weights licenseにより用途は`research-only`かつnon-productionです。Banto HubやPLCへの制御write pathは持たせず、read-onlyのoffline評価または非本番shadow評価に限定します。

現時点では依存もmodel weightsも導入しておらず、実モデルは実行していません。精度、速度、peak memory、artifact sizeは未測定です。
