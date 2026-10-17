# banto-ai Rust crate

Portable AI implementation in the banto-ai repository. Applications such as
banto-industrial and demand/PSI consumers own data acquisition, application DTOs,
job hosting and model activation.

R1 implements the fixed full SmallForecaster inference path on explicit Burn
0.22 Flex CPU. The `training` module holds the R2P artificial training parts:
normalized pinball loss with autodiff, ordered named gradients, global-norm clip
and a Torch-compatible AdamW. `cargo test -p banto-ai --features training-tests
--test r2p_synthetic` checks them against the committed Torch reference in
`tests/fixtures/r2p` under the unchanged R0.1 tolerances. `training::train_step`
and `synthetic_checkpoint` (schema `banto.synthetic-training-checkpoint.v1`)
cover the artificial toy model's eight updates and its save/resume in separate
processes. Training the full SmallForecaster and formal R2 are not implemented yet. The output contains quantiles and context diagnostics; its p50
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

[現在の引継ぎ](../../docs/current-handoff.md)と[復帰計画](../../docs/research/banto-ai-practical-training-return-plan-2026-10-16.md)に沿って進める。Rust推論R1は中間値1点未達で、正式R2実データ学習は停止中。人工データだけのR2P loss/gradient/AdamW/checkpoint実装が次工程である。Python参照は生成済みだが、Rust学習・保存再開は未実装。

現在の公開moduleはcheckpoint/error/input/model。default testは合成入力のunit testだけで、CARE参照のintegration testはreference-testsで明示opt-inする。暗黙のexample探索は無効、公開exampleはpredictのみ。不採用FMA/context/fused-linear拡張と診断exampleは履歴資料へ退避した。旧featureは再定義しない。閉鎖済み証跡と原許容差を維持する。

本整理では検証済みのlock最小案を適用し、manifestにないgemmの直接edgeだけを削除した。package/versionの追加更新は行わない。[整理結果](../../docs/results/research-consolidation-2026-10-17.md)に現在の構成での検証結果を記録する。過去時点のbuild成功をRust学習や数値互換の合格へ読み替えない。
