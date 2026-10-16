# banto-ai Rust crate

Portable AI implementation in the banto-ai repository. Applications such as
banto-industrial and demand/PSI consumers own data acquisition, application DTOs,
job hosting and model activation.

R1 implements the fixed full SmallForecaster inference path on explicit Burn
0.22 Flex CPU. Training, optimizer updates and restart belong to R2 and are not
implemented yet. The output contains quantiles and context diagnostics; its p50
and context_center are not expected future demand.

Current verification: locked offline CPU build and all three tests pass on
native Rust 1.95.0/macOS. Same-input normalization and attention diagnostics pass.
LayerNorm now multiplies by one row inverse standard deviation, matching the
reference CPU evaluation order; fixed seven-case confirmation resolves the old
mismatch but reveals one different intermediate element beyond the unchanged
tolerance. Final normalized and physical quantiles pass all seven cases.
R1 as a whole remains failed; training is not started. Preserve all results and
avoid arithmetic searches aimed at individual elements. The build cache/target
ceiling is 1.5 GiB; memory stays at 2 GiB.

The pinned neutral-reference integration test is opt-in via the reference-tests
feature and BANTO_R1_REPO. Default unit tests use no saved model or datasets.

The current loader imports a pinned CARE neutral reference. Trusted manifest
digests are required. It validates shape, tensor identity, dtype, offsets, padding,
finite values and causal mask. Production model-package and training-checkpoint
support will be completed separately. The crate includes no research datasets,
customer source, saved weights, Tauri, PLC access or application dependencies.

The predict example consumes fixed R1 inputs and emits diagnostic tensors into a
new directory. It never reads target quantities or runs training. Follow the
repository research plan and R0.1 numerical contract for comparison and budgets.

Dependency resolution currently retains the official Burn v0.22.0 lock as its
seed. An inactive LibTorch dependency has a yanked zip version, which prevents a
fresh unlocked resolution. It is absent from the active Flex graph. Unlocked
downstream integration remains a distribution issue to resolve before release.

## 現在の研究順序

[実用性とRust学習へ戻る計画](../../docs/research/banto-ai-practical-training-return-plan-2026-10-16.md)を優先する。OS/vendor内部のpointer追跡は停止。原R1は1点未達のまま、人工データだけのloss/gradient/AdamW/保存再開をR2Pとして独立準備する。正式R2実データ学習は原R1通過まで開始しない。今回の計画改訂でコードや学習は実行していない。

上のbuild/test結果と下の拡張は各保存時点の構成に対する記録である。現Cargo manifestにはこれらの研究用feature定義がないため、sourceが存在するだけで現在利用できるとはしない。manifest/lock/sourceの整合を先に確認し、他作業の変更を保護する。原許容差は維持する。

## 研究用FMA拡張

非defaultの `fma-extension` featureで公開Burn backend extensionのfinite f32 FMAと幅64のreference-order LayerNormを利用できる。人工forwardとgraph参加、局所49入力のbit一致は確認済み。backwardはコードをcompileしただけで未検証。SmallForecasterへの一律接続は元R1基準で中間3点が未達となり取り消したため、featureを有効にしても現在のSmallForecasterは従来のnormを使う。[採否と保存結果](../../docs/results/banto-ai-rust-r1-fma-extension-2026-10-16.md)を参照。FMAはshape/dtype/device-context不一致をError、非有限入力/結果をkernel panicで拒否する研究APIである。

## 研究用context正規化

非defaultの `reference-normalization` featureで `context::reference_context` と診断exampleを公開する。固定幅128のCPU参照順f32 meanと独立f64 Welford stdをtensor graph内で計算し、固定7caseのplain/Autodiff forwardは参照bits一致。backward/gradientは未検証。SmallForecasterへのcontext+LayerNorm接続候補は元R1全体で1点未達となり取り消したため、このfeatureで現在のSmallForecasterの算術は切り替わらない。[採否](../../docs/results/banto-ai-rust-r1-context-normalization-2026-10-16.md)を参照。

## 研究用GEMM bias初期化

非defaultの `fused-linear-extension` は既存pure-Rust gemm0.19.0を使うfinite_fused_linearを公開する。人工8caseのplain/Autodiff forward・graph・13拒否条件は確認済み。backwardはcompileのみで未検証。保存済み154linearは現行とbytes同一で改善しなかったため、SmallForecasterへ接続していない。[採否](../../docs/results/banto-ai-rust-r1-fused-linear-2026-10-16.md)と[安全性](../../docs/research/rust-fused-linear-safety-2026-10-16.md)を参照。metadata不一致はError、非有限/負stride/primitive範囲不正はkernel panicで拒否する研究API。
