# Banto AI 文書の入口

最終更新: 2026-10-17

## 現在の状態

主目的はTimesFM3を参考にした自作モデルの実用性検証です。保全・点検支援を第一優先とし、需要予測・PSIも扱います。学習を含むRust移植のAI本体はbanto-ai、利用側はbanto-industrialとdenroku-psi-demoです。

- 現在の結果・停止条件・次工程は [短い引継ぎ](current-handoff.md) を優先します。
- [Rust実装計画](research/banto-ai-rust-implementation-plan-2026-10-16.md)に沿い、人工R2Pの学習・保存再開部品へ進みます。R1の中間値1点は未達で、正式R2実データ学習は停止しています。
- [整理結果](results/research-consolidation-2026-10-17.md)を参照。停止済みのRust R1調査（SGEMM/once/FMA/fused等）は削除済みで、保存tagから参照できます。
- 旧異常検知トラック（v0.1〜v0.3、Windows native受入）はコード・文書とも削除しました。保存tag `archive/preformal-research-20261017` から参照できます。main取り込み時点の[状態記録](history/main-document-status-20260925.md)は過去時点の記録です。
- 評価報告は [結果の索引](results/README.md)、過去の長い引継ぎは [履歴](history/current-handoff-through-20261016.md) を参照してください。

## 分野別の入口

| フォルダ | 内容 |
| --- | --- |
| [overview/](overview/README.md) | 全体構成、Banto Hubとの責務、試運転方針 |
| [research/](research/README.md) | 研究roadmap、モデル・公開データ調査 |
| [models/](models/README.md) | TimesFM、Chronos-2、Totoの評価契約 |
| [decisions/](decisions/README.md) | 設計判断と理由（ADR） |
| [results/](results/README.md) | 実測・監査・実行報告の分野別索引 |
| [history/](history/README.md) | 過去の引継ぎ・索引・初期Issue案 |

## その他

- [研究実装計画](research-implementation-plan.md)

## 文書を読む順序

1. 現在の作業状態は current-handoff.md。
2. 実測値・失敗・適用範囲は、対象時点の結果報告と原artifact。
3. 仮説・母数・手順は凍結計画、採択済みの設計判断はADR。
4. 実行手順は各tool/environmentのREADME。

過去報告の「未実施」「失敗」などは当時の記録です。後日の成功を過去の結果へ適用しません。
設計文書の存在や処理の成功は、正式受入・モデル性能・本番利用許可を意味しません。

## 文書追加時の配置

研究はresearch/、モデル固有の契約はmodels/、判断はdecisions/へ置きます。
実施日を伴う結果報告はresults/へ追加し、その目次とcurrent-handoff.mdから参照します。
閉鎖済みartifactと過去の原証拠は、その保存状態を保持します。
