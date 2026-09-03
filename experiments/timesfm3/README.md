# TimesFM-3 実験

このディレクトリは、[`docs/timesfm-notes.md`](../../docs/timesfm-notes.md) に記載した再現可能な TimesFM-3 benchmark 用です。

予定している内容:

- run manifest
- model adapter code
- baseline runner
- smoke-test fixture
- version 管理対象外の生成レポート

結果を記録する前に、正確な model release と runtime を固定します。checkpoint と prediction は、リポジトリに安全な小さな synthetic test artifact を除き、Git の外に置きます。
