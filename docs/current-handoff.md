# 現在の引継ぎ — 2026-10-17

## 主目的

TimesFM3を参考にした自作モデルの実用性を検証する。保全・点検支援を第一優先に、需要予測・PSIも対象にする。学習・推論・optimizer保存再開をbanto-aiのRustクレートへ実装し、banto-industrialとdenroku-psi-demoから使う。利用側→banto-aiの依存方向を守る。

## 現在地

- [復帰計画](research/banto-ai-practical-training-return-plan-2026-10-16.md)と[実装計画](research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿って進める。
- Rust推論R1は中間値1点未達のまま（合格と扱わない）。R0.2により、正式R2の入口はR1の最終出力と同一入力局所比較になり、中間値は記録する診断になった。
- [R2P固定契約](research/rust-r2p-synthetic-training-contract-2026-10-16.md)と[人工Python参照](results/rust-r2p-lock-and-python-reference-2026-10-16.md)は保存済み。loss7/clip4/AdamW6/小型8更新、独立照合107件pass。2026-10-17にCloud移行のため参照をLinux/Torch2.14.1で作り直し、[`crates/banto-ai/tests/fixtures/r2p`](../crates/banto-ai/tests/fixtures/r2p/runtime.json)へコミットした（[記録](results/rust-r2p-cloud-reference-2026-10-17.md)、107照合pass）。
- 検証済みのCargo.lock案を本整理で適用。gemmの不要な直接edgeだけを除いた。非採用のRust拡張・診断と単発調査（SGEMM/once/FMA/fused等）は削除済みで、保存tagから参照する。R2P工程2（loss/勾配・global clip・互換AdamW）は`crates/banto-ai/src/training.rs`に実装し、CIでCloud参照と照合する（[記録](results/rust-r2p-training-parts-2026-10-17.md)）。工程3（人工affineの連続8更新、checkpoint、別process再開、拒否8・停止3）も通過（[記録](results/rust-r2p-resume-2026-10-17.md)）。
- CIはPython unittest・smoke・safetyとRust fmt/testだけ。旧異常検知トラック（v0.1〜v0.3、Windows native受入、文書を含む）は削除し、保存tag `archive/preformal-research-20261017` から参照する。
- 需要は現役経路（固定重み制約QP系列、StatisticalFeatureMeanのMac再構築とmean28比較、営業状態・定休日）だけを残し、置き換わった過去実験のtool/test/文書は削除した。保存tagから参照する。
- [今回の整理と確認結果](results/research-consolidation-2026-10-17.md)を参照。整理PRでmainへ提案し、mainの自動mergeはしない。

## 次に行うこと

[R0.2](research/rust-r0.2-comparison-amendment-2026-10-17.md)（2026-10-17承認）に沿って進める。R2P工程2〜4は通過済み（[工程4の記録](results/rust-r2p-full-model-2026-10-17.md)）。

1. 正式R2は2026-10-17に1回だけ実行し、**全ケース合格**（[記録](results/rust-r2-formal-2026-10-17.md)）。1更新・8更新・成熟state import・floorのtieがR0.1/R0.2内、保存再開はbytes一致。これ以外の実データ学習は停止のまま。CAREの保存物はgitignoreの`artifacts/`にあり公開しない。
2. 保全の実用性評価：[契約](research/care-maintenance-practical-contract-2026-10-17.md)を固定した。先行時間（0/24/72/168時間）と誤警報は複数で報告し、基準は比較の後で人が決める。TimesFM 3（研究用途）・Chronos-2・Toto 2をzero-shotで比べる。CARE testは開発材料として扱う。Macからlabelとfold1〜4の保存物を受け取ってから実行する。
3. R3（有限の移植比較）とbanto接続は、別の実行仕様を固定してから。2の評価契約と合わせて範囲を決める。

## 維持する条件

ポインタ/once/TLS/PAC/vendor内部追跡は停止。CARE/MetroPTの既読testは凍結し、需要2015の再評価も停止。需要の調整は2014以前だけ、同じ休業仮定のmean28比較、四季平均の過小量・過大量非増加、観測のみ・欠測0仮定の分離を維持する。

各unitは親900秒/子870秒、physical footprint・peak RSS各2GiB、cache+target1.5GiB/jobs1。artifact/EvidenceStore/stdioの元上限、既存変更・失敗・closed rootsの保護を維持。許容差の値は原R0.1のままで、R0.2の追加規則を適用する。heartbeatはPAUSED。下流編集・本番採用・自動mergeは行わない。

## 保存した研究結果

[CARE学習・評価](results/care-macos-learning-evaluation-2026-10-16.md)は検知3/12・未検知9・正常誤警報3。[MetroPT M1](results/metropt-macos-m1-2026-10-16.md)は改善と悪化を両方保存。移植の成功と保全判断の有用性は別に判定する。

## 履歴

- [2026-10-16までの全引継ぎ](history/current-handoff-through-20261016.md)
- 保存地点: `archive/preformal-research-20261017` / `50d69b6`。旧ブランチを削除しない。
