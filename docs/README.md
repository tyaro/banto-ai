# banto-ai 文書索引・状態台帳

最終更新: 2026-09-06

この索引は、文書の入口と現在状態を示すliving documentです。初稿S0 commitは
`41decf9b6f8d6c876715729516354bf6da49422c`、そのparentはmainの
`026aa77fe96afd954957acb2fc7d0df9ee3cc938`です。文書同期commit
`e92c83df03b2f798d60246e14411d249a0b76202`の上の監査対象
`4b02201f95e8ffa3a243be716872d95815a554bd`でv0.3計画のP2 3件を修正しました。
独立監査はP0〜P3 0件で合格し、S0はfrozen・adoptedです。candidate stackはmain未統合です。
S0監査記録commit `0b40e7295cfa20f32889005ceca2d29d29ca340c`の上でS1を実装し、
S1初回監査（`0368769acf12a0279c84f30c6435e853208386e9`）はP2=6／P3=1件でした。
現在はS1修正候補・独立再監査待ち、S1未承認です。S2以降は未着手です。

## 正本の読み方

同じ成果について記述が異なる場合は、対象と時点を合わせて次の順に読みます。

1. 監査済みの正式result文書と、そこに記録されたartifact hash／provenance
2. この索引、研究roadmap、実装計画末尾の追記などのliving status
3. preregistration／受入計画。実験前に固定した仮説・母数・手順の正本であり、
   「未実施」はfreeze時点の記録
4. tool／environment README。再現手順の正本であり、性能や完了状態の正本ではない

freeze plan、result、ADRの過去時点の本文は、後工程の完了に合わせて機械的に
書き換えません。後日の正式resultが「完了」、古いfreeze planが「未実施」と記す場合、
矛盾ではなく、計画凍結時点と実行完了時点の違いとして扱います。性能値、gate判定、
artifact identityはresult文書を優先し、living文書はその結果への索引を更新します。

初稿v0.3 S0の`freeze-ready`という自己評価に対し、Astra/max監査はP0/P1 0件・P2 3件でした。
監査対象`4b02201...`でその3件を修正し、独立再監査は**P0〜P3 0件で合格**しました。
最初のequipment episodeを固定してsupport失敗後に再探索しないmatchingとM1〜M9、
event/quality適用後の6桁丸め・保存観測だけをfit/calibration/testで読む規則とQ1〜Q5、
Linux Python 3.12/3.14共通試験・Windows native publisher/DACL/AccessCheck・正式唯一runtimeを
計画内に明記しました。正式pinはWindows 11 Pro 25H2 build `10.0.26200.9168`／CPython `3.14.0`です。
S0の監査判定は`SCIENCE_READY=yes`、`FREEZE_READY=yes`、`DOCS_READY=yes`、
`IMPLEMENTATION_READY=yes`、`STACK_READY=yes`です。これはS1実装候補の監査合格を意味しません。
S1では5 config、9 schema、pure semantic validator、seed/bootstrap registryとadversarial testsを追加しました。
S2以降のscorer／runner、Linux／Windows native acceptance、run／artifactは未着手です。
根拠は[v0.3計画監査結果](results/anomaly-multiseed-v0.3-plan-audit-2026-09-06.md)を参照してください。

## 全体の現在地

| research-roadmap | 状態 | 現在の根拠 |
| --- | --- | --- |
| Phase 0 研究基盤と契約 | complete | package、manifest、共通runtime、license／安全境界を実装済み |
| Phase 1 合成データとbaseline | complete | 再現可能generator、quality、rolling-originと統計baselineを実装済み |
| Phase 2 Forecast model benchmark | active / incomplete | TimesFM 3、Chronos-2、Toto 2.0 4Mの初期・matrix・MetroPT-3等は評価済み。条件拡大、resource分離、一般化は未完了 |
| Phase 3 異常とドリフト | active | anomaly v0.1契約、v0.2 formal replay/analysis、failure diagnosticsまで完了。v0.3 S0 frozen、S1修正候補・再監査待ち・未承認、S2以降未着手 |
| Phase 4 自前モデル研究 | not started | 専用の実装・ablationは未着手 |
| Phase 5 Commissioning auto-tuning | not started | 設計文書のみ。profile昇格やshadow実行は未着手 |
| Phase 6 Continual adaptation | not started | frozen model＋profile適応の実験は未着手 |
| Phase 7 Banto Hub pilot境界 | not started | architecture境界のみ。pilot、customer/control writeは未着手 |

番号体系は文書間で同一ではありません。[研究roadmap](research-roadmap.md)はPhase 0〜7で、
自前モデル研究を4、continual adaptationを6として独立させています。
[実装計画](research-implementation-plan.md)の全体表はPhase 0〜6で、詳細節は0〜5です。
そこではCommissioningが4、Banto連携PoCが5、Shadow pilot準備が6であり、
roadmapのCommissioning 5／Banto Hub 7とは1対1対応しません。

Phase 3の内訳は次のとおりです。

- anomaly v0.1 single-seed evaluator contract: 完了
- v0.1 multi-seed formal artifact: 生成後監査でintegrity defectを確認し、`REJECT` evidenceとして保全
- v0.2 formal replay＋standalone analysis: 完了、engineering `pass`、performance `fail`、昇格なし
- v0.2 failure diagnostics D2-B: 正式公開・独立read-only監査・result文書まで完了、
  engineering `pass`、performance `not_evaluated`、exploratory、promotion不可
- v0.3 S0初稿commit `41decf9...`へのP2 3件: 監査対象`4b02201...`で解消し、
  独立監査P0〜P3 0件でS0 frozen・adopted。main未統合、S1修正候補は独立再監査待ち・未承認。
  Linux／Windows native acceptance、S2〜S7、formal run／artifactは未実施

## 文書カテゴリ

status語は`current`（living正本）、`frozen`（事前固定）、`historical`（過去時点）、
`formal-result`（正式結果）、`rejected`（昇格証拠に不採用）、`reference`（設計資料）、
`procedure`（実行手順）、`draft`（未採択案）、`audit-result`（監査結果）を使います。

### 現行roadmap、方針、設計資料

| 文書 | status | 用途 |
| --- | --- | --- |
| [研究roadmap](research-roadmap.md) | current | Phase 0〜7と現在状態 |
| [研究実装計画](research-implementation-plan.md) | current + historical sections | 直近工程、gate、savepoint。末尾追記を最新状態として読む |
| [architecture](architecture.md) | current / reference | Banto Hub、AI、PLCの責務境界 |
| [commissioning learning](commissioning-learning.md) | reference | recipe、profile、承認・rollback設計 |
| [時系列model survey](time-series-model-survey.md) | reference | 候補、license、比較軸 |
| [公開dataset survey](public-dataset-survey.md) | current / reference | 公開データ候補と取得境界 |
| [初期Issue案](initial-issues.md) | historical / draft | 研究開始時のIssue草案。現在状態には使わない |

### anomaly契約、凍結計画、相互関係

| 文書 | status | 関係 |
| --- | --- | --- |
| [anomaly evaluator v0.1 contract](anomaly-evaluation-contract.md) | reference / historical | single-seed evaluatorの契約 |
| [multi-seed plan v0.1](anomaly-multiseed-evaluation-plan.md) | frozen / historical / rejected lineage | 最初の正式計画。対応artifactは後のintegrity監査でREJECT。計画本文は時点記録として保持 |
| [multi-seed plan v0.2](anomaly-multiseed-evaluation-plan-v0.2.md) | frozen / executed | integrity修正後の新ID・rootを固定し、formal replay/analysisを実行済み |
| [failure diagnostics plan v0.1](anomaly-multiseed-failure-diagnostics-plan-v0.1.md) | frozen / executed / exploratory | v0.2 artifactを変更しないpost-hoc診断。D2-Bと独立監査まで完了 |
| [multi-seed plan v0.3](anomaly-multiseed-evaluation-plan-v0.3.md) | frozen / adopted | 科学仕様は監査対象`4b02201...`を保持。S1修正候補は独立再監査待ち・未承認、S2〜S7未実施 |

v0.1の計画、artifact、監査は削除しません。v0.1監査がartifactを`REJECT`とし、
修正後の正式証拠を別identityのv0.2計画・resultへ分離しました。v0.2 failure diagnosticsは
性能再判定ではなく、v0.3仮説を作るexploratory evidenceです。v0.3はv0.2の正式結果を
格下げせず、新しい未使用seedで別評価を計画しています。

### model、scenario、ADR

| 文書 | status | 用途 |
| --- | --- | --- |
| [TimesFM notes](timesfm-notes.md) | reference / historical | research-only境界と評価契約 |
| [Chronos-2 notes](chronos2-notes.md) | reference | commercial-evaluation境界と実行契約 |
| [Toto 2 notes](toto2-notes.md) | reference | 4M/22M候補と評価境界 |
| [Toto controlled scenarios](toto2-controlled-scenarios.md) | frozen / executed | 4-track acceptanceの事前固定条件 |
| [ADR-0002 fev reassessment](adr-0002-fev-reassessment.md) | historical decision | fev再評価判断 |
| [ADR-0003 TimesFM isolation](adr-0003-timesfm3-isolation.md) | accepted decision | 非商用重みと専用環境の隔離 |
| [ADR-0004 Chronos-2 isolation](adr-0004-chronos2-isolation.md) | accepted decision | optional backendとcacheの隔離 |
| [ADR-0005 public dataset boundary](adr-0005-public-dataset-boundary.md) | accepted decision | raw公開データをGit外に置く境界 |

## 結果文書

`docs/results`には実測で18件あります。すべて結果条件と制約を伴う索引であり、
顧客設備一般の性能保証ではありません。

### Anomaly（4件）

| 文書 | status | 要点 |
| --- | --- | --- |
| [v0.1 integrity audit](results/anomaly-multiseed-v01-integrity-audit-2026-09-05.md) | rejected / audit-result | summary integrity bypassのため正式artifactをREJECT evidenceとして保全 |
| [v0.2 formal evaluation](results/anomaly-multiseed-v02-evaluation-2026-09-05.md) | formal-result / no-promotion | replay/analysisのengineering pass、performance fail、全5 gates fail |
| [v0.2 failure diagnostics](results/anomaly-multiseed-v02-failure-diagnostics-2026-09-06.md) | formal-result / exploratory | D2-B公開・独立監査完了、causal support 0/240、performance未評価、promotion不可 |
| [v0.3 plan audit](results/anomaly-multiseed-v0.3-plan-audit-2026-09-06.md) | audit-result / plan-only | P0〜P3 0件、5 readiness yes。S0 frozen・adopted、S1〜S7とformal runは未実施 |

### TimesFM 3（5件）

| 文書 | status |
| --- | --- |
| [CPU smoke](results/timesfm3-cpu-smoke-2026-09-04.md) | historical result / limited |
| [rolling benchmark](results/timesfm3-rolling-benchmark-2026-09-04.md) | historical result / limited |
| [baseline comparison](results/timesfm3-baselines-comparison-2026-09-04.md) | historical result / limited |
| [multi-condition matrix](results/timesfm3-matrix-2026-09-04.md) | historical result / limited |
| [MetroPT-3 evaluation](results/timesfm3-metropt3-evaluation-2026-09-04.md) | formal research result / research-only model |

### Chronos-2（3件）

| 文書 | status |
| --- | --- |
| [initial evaluation](results/chronos2-initial-evaluation-2026-09-04.md) | historical result / limited |
| [multi-condition matrix](results/chronos2-matrix-2026-09-04.md) | formal research result / limited |
| [MetroPT-3 evaluation](results/chronos2-metropt3-evaluation-2026-09-04.md) | formal research result / native partial + calibrated success |

### Toto 2.0（4件）

| 文書 | status |
| --- | --- |
| [MetroPT-3 evaluation](results/toto2-metropt3-evaluation-2026-09-04.md) | formal research result / limited |
| [multi-condition matrix](results/toto2-matrix-2026-09-04.md) | formal research result / limited |
| [event slices](results/toto2-event-slices-2026-09-04.md) | post-hoc result / limited coverage |
| [controlled evaluation](results/toto2-controlled-evaluation-2026-09-05.md) | formal acceptance result / synthetic 4M CPU only |

### Public data / baseline（2件）

| 文書 | status |
| --- | --- |
| [MetroPT-3 import](results/metropt3-import-2026-09-04.md) | formal data-ingest result |
| [MetroPT-3 statistical baseline](results/metropt3-baseline-evaluation-2026-09-04.md) | formal research result / limited |

## Repository、equipment、tool手順

### Repository運用

| 文書 | status | 用途 |
| --- | --- | --- |
| [repository README](../README.md) | current | 全体入口、直近結果、基本方針 |
| [CONTRIBUTING](../CONTRIBUTING.md) | procedure | 開発、test、data/license方針 |
| [research task issue template](../.github/ISSUE_TEMPLATE/research-task.md) | procedure | 研究Issueの記録項目 |
| [dataset policy](../datasets/README.md) | current / procedure | 合成・公開・顧客データの配置境界 |

### Experiment / model placeholders

| 文書 | status | 用途 |
| --- | --- | --- |
| [TimesFM experiment](../experiments/timesfm3/README.md) | reference | 実験directoryの責務 |
| [synthetic-data experiment](../experiments/synthetic-data/README.md) | reference | 合成データ実験の責務 |
| [online-learning experiment](../experiments/online-learning/README.md) | draft / reference | 将来の適応実験境界 |
| [mini-transformer model](../models/mini-transformer/README.md) | draft / reference | 将来自前モデルの配置 |
| [industrial-tsfm model](../models/industrial-tsfm/README.md) | draft / reference | 将来モデル研究の配置 |

### Environment / tool procedures

| 文書 | status | 用途 |
| --- | --- | --- |
| [TimesFM environment](../environments/timesfm3/README.md) | procedure | 専用環境、重み、offline境界 |
| [Chronos-2 environment](../environments/chronos2/README.md) | procedure | 専用環境、cache、offline境界 |
| [data generator](../tools/data-generator/README.md) | procedure | 合成dataset生成 |
| [evaluator](../tools/evaluator/README.md) | procedure | benchmark/anomaly評価 |
| [public-data](../tools/public-data/README.md) | procedure | 公開データ取得・検証 |
| [TimesFM tool](../tools/timesfm3/README.md) | procedure | TimesFM実行 |
| [Chronos-2 tool](../tools/chronos2/README.md) | procedure | Chronos-2実行 |
| [Toto 2 tool](../tools/toto2/README.md) | procedure | Toto実行とcontrolled analysis |

## データ、artifact、license境界

Git管理する正式な文書には、目的、条件、hash、provenance、結果、制約を記録します。
大きなrun artifact、raw公開データ、model cache、顧客データは通常Git管理外です。
result文書はartifact本体の代替ではなく、固定hashとprovenanceへ到達するための索引です。
consumerは文書の数値だけでなく対象artifactのhashとschemaを再検証します。

顧客データはこのrepositoryへ置きません。合成データ、またはlicenseと出所を確認した公開データだけを
研究対象にします。repoのcode/docsはMITですが、外部dataset、model code、学習済みweightsは
それぞれのlicenseが優先されます。文書索引の追加によって利用条件やcontrol権限は変わりません。

## 同期時に確認したこと

棚卸しの対象は、指示どおり`rg --files -g '*.md'`で見えるMarkdownです。
基準commitには53件あり、本索引追加後は54件、今回の監査result追加後は55件です。
Git管理対象にはhiddenな`.github/ISSUE_TEMPLATE/research-task.md`がもう1件あり、
最終的なtracked Markdownは56件です。
`artifacts/`以下に存在するignored summary 7件は正式artifact／残留物として変更せず、
棚卸し数・到達性link graphから除外しました。

- `docs`直下は本索引を含め21件、`docs/results`は18件
- tracked Markdownのlocal file links: 283件（pathを持つtargetの存在を検査）
- fragment-only links: 3件（v0.3計画のP2対応表から明示anchorへの参照）
- missing local links: 0件
- 到達性: root READMEを起点とし、本索引のcategory表を辺としてtracked Markdown 56件を対象にする
- docs配下の到達性: 39/39件（100%）
- orphan: 0件（tracked Markdown 56件すべてroot READMEから到達可能）
- 競合していたliving status: roadmapのfailure diagnostics「実行・公開未実施」を正式D2-B完了へ同期
- 意図的に保持した古い表記: frozen plan、historical savepoint、result監査時点の「未実施」
- v0.3 S0: 監査対象`4b02201...`のP2 3件解消と独立監査合格を記録し、frozen・adoptedへ同期
- v0.3 S1: 初回監査P2=6／P3=1への契約検査・出典・遅延集計・境界試験の修正候補。再監査待ち・未承認、S2以降は未着手

## 更新手順

1. preregistrationを実装前に別version／IDで固定し、実行後も本文を遡及変更しない。
2. 正式実行後は新しいresult文書を追加し、artifact hash、provenance、失敗、制約を記録する。
3. 独立監査完了後に、この索引、research-roadmap、root READMEのliving statusを更新する。
4. freeze planには必要な場合だけappend-onlyの実施後記録を追加し、当時の未実施表記を残す。
5. `rg --files -g '*.md'`、tracked inventory、全local link、docs配下coverage、orphanを再検査する。
6. result値や過去のgateを新計画に合わせて書き換えず、訂正は理由・時点・正本hashを残す。
