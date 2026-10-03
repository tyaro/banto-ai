# v0.3 正式評価前の受入残件と保存済みデータの作業範囲（2026-10-03）

基準commitは `da0f6770ebb56d0e7cf3db54348cad472bc47bc0`。これは[10月1日の受入残件表](anomaly-multiseed-v0.3-acceptance-gap-update-2026-10-01.md)を、以後の保存証拠に合わせて読み直した文書である。既存の結果文書とsourceを確認した範囲であり、本書の作成によって保存artifactの再hash、評価、監査、受入試験を実施したとは扱わない。完了した接続工程の試験数を異なるrevision間で合算しない。

実施追記：[区間0の保存済みデータへの限定適用](anomaly-multiseed-v0.3-saved-chunk-000-pilot-2026-10-03.md)は、本書の範囲整理後に別の作業単位として完了した。以下の1区間pilot手順は実施前に定めた境界を示す。残り119区間・714評価は新しい要約経路では未確認である。

## 現在の到達点と用語

[単一の保存済み報告入口](anomaly-multiseed-v0.3-saved-report-pipeline-2026-10-03.md)は、要約・集計表・報告書・保存完了記録の四つを開始位置にでき、別試行の続行requestを残す。23項目の確認は架空入力とengineering modeの接続であり、正式modeを拒否する。`publication`からの再利用例では、新しい集計・報告・保存の呼出しも所有process起動も0回だった。

以下で「保存済み実データ」と呼ぶのは、合成信号から実際に生成・保存した**dev 8 seed / smoke 2 seed、120区間・240 dataset・720評価**の成果物である。実設備・顧客データではない。保存済み全件の[生成・重畳・丸めの独立検算](anomaly-multiseed-v0.3-independent-generation-audit-2026-09-24.md)と[profile・score・ledgerの独立検算](anomaly-multiseed-v0.3-full-connected-audit-2026-09-24.md)は完了している。新しい保存形式readerから要約、記述表、報告へつなぐ経路は架空入力で検証し、保存済みデータでは区間0の6評価だけに適用した。全720評価の新経路による要約・報告は未確認である。過去の監査を新しい経路の実適用と読み替えない。

正式holdoutは未使用40 seed、480区間・960 dataset・2,880評価の別集団である。既存dev/smokeをholdoutへ加算・改名しない。50,000回bootstrap、正式gate、S6、候補昇格、実設備性能は未評価。[凍結計画](../anomaly-multiseed-evaluation-plan-v0.3.md)の科学的な候補、seed、分母、閾値、選択規則は本書で変更しない。

## 正式開始前に揃える5まとまり

| 受入事項 | 完了として保持する証拠 | S5開始前に揃えるもの | 実行後の照合 |
| --- | --- | --- | --- |
| 1. 運用契約 | engineeringの単一writer、終了後reader、非上書きと保存点。架空5payloadの通常公開も接続済み | 正式方針ID、対象revision、slice/sidecar mapping、OS更新の扱い、失敗時の別version/root/未使用seedでの再登録を版付きで採択。旧S4-A receiptをpassへ書き換えない | 採択契約とattempt、環境、終了状態の一致 |
| 2. 登録入力とconsumer | 旧dev/smoke全件の独立監査、架空40clusterの全枠・最新attempt・主/補助count結合、限定した推論・文書・報告接続 | 登録40 seedの全slot・入力bytes・終了証拠から正式consumerへ渡す入口を固定入力で検証。50,000 draw、完全な正式文書、全条件別在庫まで結ぶ | S5の実登録入力・全coverage・反復数・文書を照合。実行前に成功receiptを要求しない |
| 3. source/runtimeと役割 | engineering reader、架空analysis/audit、writerの選択sourceと実行観測 | producer/analysis/audit/writer/readerの最終役割profile、clean Git/raw source、動的依存・外部program、起動条件とattempt間のOS更新許容範囲を先に固定。Linux必須jobとWindows受入の対象revisionを確定 | 各実processの開始・終了時のOS build/UBRとsource/runtime、入力・出力、exit/reapを外部期待値と照合。attempt内の環境変化は停止 |
| 4. 公開・読取り・独立監査 | 架空入力の主表・slice別算術監査→5payload保存→writer終了後reader、保存済みdev/smokeの旧4payload公開 | 登録入力由来の同一結果を別analysis/audit root、公開receipt、別reader、独立数値監査へ結ぶ正式経路と失敗状態を検証 | S5/S6で実結果の全payload、全inference/gate/slice、独立再計算、別readerを照合 |
| 5. 全工程予算 | 小さいfixtureの共有監視・資源停止・所有worker回収。旧720評価の保存量・時間の実績 | producer、50,000 draw、独立監査、staging/公開/readerを含む時間・容量・private memory・system commitの上限と停止・再登録を採択。smoke実測から計画所定の容量検査を行う | 実消費量、停止条件、証拠保全、全process終了を確認 |

正式運用ID `anomaly-v03-single-writer-research-v1` は[契約案](../anomaly-v03-consumer-io-proposal.md)の予約名で、採択済みではない。旧計画の正式Windows pinは build `10.0.26200.9168` / CPython `3.14.0`、後続の観測OSは `10.0.26200.9457`。旧pinやDACL・独立tokenの受入を観測値だけで通過扱いせず、運用差分、計画改訂、独立再監査と対象revisionの受入を先に確定する。Windows 3.12を追加の正式必須条件にはしない。

旧formal入口は `require_campaign_acceptance()` で `s4_acceptance_not_frozen` を返し、保存済み報告入口もformal modeを拒否する。正式文書草稿の `status / provenance / analysis_consumer / bootstrap` はnull、`formal_ready=false`を維持する。この4欄は「残り4試験」という意味ではない。`formal_permission`、`promotion_allowed`、`independent_s6_complete`、`trust`、`execution_authenticated`、`full_runtime_inventory_complete`、`analysis_authorized`を本書でtrueにしない。

### 10月1日のT01〜T12表から進んだ部分

| 対応 | 追加された接続証拠 | 引き続き残る境界 |
| --- | --- | --- |
| T02〜T06 | 架空producerの主/補助入力結合、保存形式1区間のreader、全120区間の要約coverage結合、dev/smoke記述表と報告準備。後続の区間0 pilotは6評価を実適用 | 登録正式入力の実bytes・実行者・終了状態、残り119区間/714評価への新経路の適用要否と予算 |
| T08・T12 | 架空40clusterの主9表に加え、本文1,233 slice行・補助2,835行・詳細9表を別実装で検算 | 正式mapping採択、登録観測からの導出、50,000 drawと完全S6 |
| T09〜T11 | 架空5payloadの通常writer/別reader、保存済み報告の4payload公開・別reader、続行checkpointと限定資源停止 | 最終役割profile・完全source/runtime、正式結果の公開/監査receipt、全工程予算 |

各追加証拠は[架空入力の結合公開](anomaly-multiseed-v0.3-bound-fixture-publication-2026-10-02.md)、[保存形式1区間の接続](anomaly-multiseed-v0.3-saved-chunk-summary-2026-10-02.md)、[全枠要約の結合](anomaly-multiseed-v0.3-summary-coverage-2026-10-02.md)、[記述表](anomaly-multiseed-v0.3-bound-summary-tables-2026-10-03.md)、[報告](anomaly-multiseed-v0.3-bound-summary-report-2026-10-03.md)、[単一入口](anomaly-multiseed-v0.3-saved-report-pipeline-2026-10-03.md)の保存時点に限定する。T01の正式入口、T07の正式50,000 draw、正式T08〜T12は未受入である。

## 区間0 pilotの事前範囲（実施済み）

この作業単位では、正式評価を開かず、既存成果物から**1区間・6評価の要約を新readerで導出し、過去の独立監査と照合する**ことを定めた。区間0の入力22 fileの存在・サイズと外部保存点pinを確認し、固定plan、保存された2 dataset・6評価、過去監査報告を読み、別の新規出力rootだけに結果と資源/失敗記録を残した。区間119の失敗attempt1と検証済みattempt2の選択は別の境界確認とし、このpilotだけで履歴選択の全条件を実証した扱いにしない。空き資源は実行直前に確認した。実測と照合結果は[区間0の結果](anomaly-multiseed-v0.3-saved-chunk-000-pilot-2026-10-03.md)に記録した。

`read_chunk_summaries(..., chunk_index=0, expected_mode="engineering")` は現行契約どおり1区間の22 fileを検証し、観測→score→ledgerから主・条件別countを導出する。照合対象は6 identity、入力/評価hash、最新attempt、生成・score/ledgerの既存監査pin、整数の分子/分母、判定不能と分母ゼロ、条件別在庫とする。既存の生成監査pinとの突合せと全体の資源監視はAPI単体の保証ではなく、pilotの呼出し側で別に行う。過去の報告を新計算の正解として無条件に信頼せず、不一致は停止して両記録を保全する。`run_campaign`、新producer評価、bootstrap、正式gate、公開済みrootの変更はこの単位に含めない。

1区間の資源・結果を確認してから、全120区間へ一度だけ順に適用する必要性と予算を判断する。全件を行う場合は、小要約を外部pin付きで保存し、[coverage結合](../anomaly-v03-summary-coverage.md)で欠落を欠落として残す。120要約が揃った場合に限り既存の[保存済み報告入口](../anomaly-v03-saved-report-pipeline.md)へ渡し、engineeringの記述結果として出す。旧720評価を再生成・再評価せず、既存全件監査を理由なく繰り返さない。新しいreaderによる再読取りが必要な範囲と、過去監査の再利用範囲を別々に記録する。

正式規模の単純外挿は旧720評価の約14.98GiB・累積44.54時間から約59.91GiB・178.17時間で、[予算調査](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)に記録された**未採択シナリオ**である。240時間/96GiB/空き32GiB案も未採択。50,000 drawと最終独立監査の時間・メモリがないため全工程予算に代用しない。pilotも既存の時間・private・RAM/commit/disk余裕を超える場合は停止し、上限を自動で上げない。

## 順序と完了判定

1. 本書の受入表を契約・実装・保存証拠の対応表として使い、保存済みdev/smokeの区間0適用を独立の作業単位で記録した。
2. その実測と既存監査を用いて全120区間への適用要否・上限を決める。実行する場合もengineeringの記述結果とし、正式40 seedへ加算しない。
3. 正式運用契約、最終consumer/source/runtime、全工程予算を版付きで確定する。旧DACL・独立token条件の扱いを計画改訂と独立再監査で定め、改訂後のS4 platform/native受入条件と最終pin上のdev/smokeを完了する。
4. その後にだけS5の未使用40 seedを実行し、S6のread-only独立解析・監査、S7結果文書へ進む。

本書の完了判定は、残件と次の保存済みデータ適用範囲が相互に矛盾せず、既存の成功を過少評価せず、未受入事項を成功扱いしないことである。S4受入、正式許可、S5/S6、性能gate、製品利用許可を付与する文書ではない。
