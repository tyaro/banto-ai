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
