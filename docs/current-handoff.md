# 現在の引継ぎ — 2026-10-17

## 主目的

TimesFM3を参考にした自作モデルの実用性を検証する。保全・点検支援を第一優先に、需要予測・PSIも対象にする。学習・推論・optimizer保存再開をbanto-aiのRustクレートへ実装し、banto-industrialとdenroku-psi-demoから使う。利用側→banto-aiの依存方向を守る。

## 現在地

- [復帰計画](research/banto-ai-practical-training-return-plan-2026-10-16.md)と[実装計画](research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿って進める。
- Rust推論R1は中間値1点未達。許容差を変えず、正式R2の実データ学習は停止中。最終出力の通過を正式合格へ読み替えない。
- [R2P固定契約](research/rust-r2p-synthetic-training-contract-2026-10-16.md)と[人工Python参照](results/rust-r2p-lock-and-python-reference-2026-10-16.md)は保存済み。loss7/clip4/AdamW6/小型8更新、独立照合107件pass。参照を再生成しない。
- 検証済みのCargo.lock案を本整理で適用。gemmの不要な直接edgeだけを除いた。非採用のRust拡張・診断と単発調査は[履歴](../experiments/archive/rust-r1-20261016/README.md)へ退避。学習エンジンと保存再開のRust実装は未着手。
- CIはPython unittest・smoke・safetyとRust fmt/testだけ。旧異常検知トラック（v0.1〜v0.3、Windows native受入、文書を含む）は削除し、保存tag `archive/preformal-research-20261017` から参照する。
- [今回の整理と確認結果](results/research-consolidation-2026-10-17.md)を参照。整理PRでmainへ提案し、mainの自動mergeはしない。

## 次に行うこと

1. 固定済み条件に従い、feature-gatedな小型loss/autodiff/gradient/clip/互換AdamWを実装する。
2. 同じ人工入力でRust連続8更新と、4更新→別process復元→4更新を検証する。入力拒否6、checkpoint拒否8、writer途中停止3を維持する。
3. 部品通過後、全モデルの人工接続条件を別途固定する。R1とR2Pが通るまで正式R2実データ学習へ移らない。

## 維持する条件

ポインタ/once/TLS/PAC/vendor内部追跡は停止。CARE/MetroPTの既読testは凍結し、需要2015の再評価も停止。需要の調整は2014以前だけ、同じ休業仮定のmean28比較、四季平均の過小量・過大量非増加、観測のみ・欠測0仮定の分離を維持する。

各unitは親900秒/子870秒、physical footprint・peak RSS各2GiB、cache+target1.5GiB/jobs1。artifact/EvidenceStore/stdioの元上限、既存変更・失敗・closed rootsの保護を維持。許容差は原R0.1のまま。heartbeatはPAUSED。下流編集・本番採用・自動mergeは行わない。

## 保存した研究結果

[CARE学習・評価](results/care-macos-learning-evaluation-2026-10-16.md)は検知3/12・未検知9・正常誤警報3。[MetroPT M1](results/metropt-macos-m1-2026-10-16.md)は改善と悪化を両方保存。移植の成功と保全判断の有用性は別に判定する。

## 履歴

- [2026-10-16までの全引継ぎ](history/current-handoff-through-20261016.md)
- [停止済みRust調査の保存先](../experiments/archive/rust-r1-20261016/README.md)
- 保存地点: `archive/preformal-research-20261017` / `50d69b6`。旧ブランチを削除しない。
