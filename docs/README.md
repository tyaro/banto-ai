# Banto AI 文書の入口

最終更新: 2026-10-14

## 現在の状態

- 菓子の需要予測・PSIの研究設計を作成しました。自動実行のheartbeat banto-10は **PAUSED** を維持しています。
- 最新成果、停止状態、正式受入の残件は [current-handoff.md](current-handoff.md) を参照してください。
- 評価報告は [結果の索引](results/README.md) から参照できます。最新状態はcurrent-handoff.mdを優先します。
- 正式gateは s4_acceptance_not_frozen、formal_permission=false、credit=0。正式受入と候補採択は未完了です。

## 分野別の入口

| フォルダ | 内容 |
| --- | --- |
| [overview/](overview/README.md) | 全体構成、Banto Hubとの責務、試運転方針 |
| [research/](research/README.md) | 研究roadmap、モデル・公開データ調査 |
| [models/](models/README.md) | TimesFM、Chronos-2、Totoの評価契約 |
| [decisions/](decisions/README.md) | 設計判断と理由（ADR） |
| [anomaly/](anomaly/README.md) | 異常評価の計画、検算、実行、正式受入、Windows実装 |
| [results/](results/README.md) | 実測・監査・実行報告の分野別索引 |
| [history/](history/README.md) | 過去の引継ぎ・索引・初期Issue案 |

## 固定パスを保持する文書

v0.3計画はコード・schema・freeze registryがパスとbytesを固定しています。
計画と、その本文から直接参照する次の文書は直下の既存パスを維持します。分野別索引からも参照できます。

- [v0.3凍結計画](anomaly-multiseed-evaluation-plan-v0.3.md)
- [v0.2評価計画](anomaly-multiseed-evaluation-plan-v0.2.md)
- [failure diagnostics計画](anomaly-multiseed-failure-diagnostics-plan-v0.1.md)
- [研究実装計画](research-implementation-plan.md)

## 文書を読む順序

1. 現在の作業状態は current-handoff.md。
2. 実測値・失敗・適用範囲は、対象時点の結果報告と原artifact。
3. 仮説・母数・手順は凍結計画、採択済みの設計判断はADR。
4. 実行手順は各tool/environmentのREADME。

過去報告の「未実施」「失敗」などは当時の記録です。後日の成功を過去の結果へ適用しません。
設計文書の存在や処理の成功は、正式受入・モデル性能・本番利用許可を意味しません。

## 文書追加時の配置

研究はresearch/、モデル固有の契約はmodels/、判断はdecisions/、異常評価の設計はanomaly/内の該当分野へ置きます。
実施日を伴う結果報告はresults/へ追加し、その目次とcurrent-handoff.mdから参照します。
閉鎖済みartifactと過去の原証拠は、その保存状態を保持します。
