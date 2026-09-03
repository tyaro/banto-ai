# TimesFM-3 実験

このディレクトリは、[`docs/timesfm-notes.md`](../../docs/timesfm-notes.md) に記載した再現可能な TimesFM-3 benchmark 用です。

TimesFM 3.0のpretrained weightsは、2026-09-03時点で非商用・非本番用途に限定されています。この実験は`research-only`とし、結果や派生成果物をBanto製品、顧客PoC、本番shadowへ昇格しません。

予定している内容:

- run manifest
- model adapter code
- baseline runner
- smoke-test fixture
- version 管理対象外の生成レポート

結果を記録する前に、正確なmodel release、code license、weight license、allowed use、runtimeを固定します。checkpointとpredictionは、リポジトリに安全な小さなsynthetic test artifactを除き、Gitの外に置きます。
