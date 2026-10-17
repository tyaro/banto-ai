# R2P: Cloud環境でのTorch参照の再生成

2026-10-17 JST。作業環境をMacからCloudへ移すため、人の判断「(b) Cloudで参照を作り直してコミットする」に従い、[R2P固定条件](../research/rust-r2p-synthetic-training-contract-2026-10-16.md)の人工Torch参照を作り直した。2026-10-16の[Mac参照](rust-r2p-lock-and-python-reference-2026-10-16.md)はGit管理外の`artifacts/`にしかなく、Cloudから参照できないため。これは「参照を再生成しない」という従来方針を人の判断で変更したものである。

## 条件

- 入力は同じ固定fixture・protocol・R0.1許容差。SHA256を[runtime](../../crates/banto-ai/tests/fixtures/r2p/runtime.json)に記録し、[整合性試験](../../tests/test_r2p_reference.py)が現行ファイルとの一致を毎回確認する。
- 演算はMac版の生成器と同じ（loss7・clip4・単独AdamW6・人工affineの連続8更新、foreach/fused=false、thread/interop各1、乱数0）。[生成器](../../tools/r2p_reference.py)はMac専用の証跡保存とpin検証を除き、計算部分をそのまま移した。
- 実行環境はLinux x86_64、Python 3.14.6、PyTorch 2.14.1+cpu（git `5c48869`）。Mac版のPython 3.14.8・Torch git `08187d9`とは異なるため、float32の値はbit単位では一致しない可能性がある。Rust側はR0.1の許容差で比較するので、この差は合否の基準を変えない。

## 結果

| 項目 | 結果 |
| --- | --- |
| 独立照合（有理数のloss/勾配、scalarのclip・AdamW・toy更新） | 107件すべてR0.1条件内 |
| 保存tensor / float32値 | 427 / 1,152（Mac版と同数） |
| 参照binary | [reference.f32](../../crates/banto-ai/tests/fixtures/r2p/reference.f32)、sha256 `a7a49143…` |

参照は`crates/banto-ai/tests/fixtures/r2p/`にコミットし、Rustの学習部品（R2P工程2・3）の試験から読む。生成器は出力先が既にあると停止し、保存済み参照を上書きしない。

## 変えていないもの

R0.1許容差、固定fixture/protocol、R1の残1点未達、正式R2実データ学習の停止。Rustの学習・保存再開はまだ実装していない。
