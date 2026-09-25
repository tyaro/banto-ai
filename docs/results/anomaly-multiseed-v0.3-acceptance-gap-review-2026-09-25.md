# v0.3 受入証拠とconsumer接続の残件整理

2026-09-26更新：[最新の残件と次の実装](anomaly-multiseed-v0.3-acceptance-gap-update-2026-09-26.md)。実レポートの保存・別readerは完了済み。開始前の準備と実行後の証拠を分け、T01〜T12を更新した。以下は2026-09-25時点の履歴として保持する。

2026-09-25 JST。確認対象は作業版 `ddd0165a45f42e9921e849e150d2cba63714b3a6` と保存済み記録。OUTは `artifacts/acceptance-gap-review-2026-09-25`、成功した確認は `verified/` と `supplement-source-map.json`。最終文書revision・各ファイルのhashは同OUTの `savepoint-evidence.json` に保存する。

**既存720評価の計算・独立検算・記述出力は再実行しない。freeze前の作業を5まとまりに整理した。** これは試験数やPhase 2/3全体の残件数ではない。正式実行と最終独立監査は、この5まとまりの後に別途残る。

## 再利用できる記録

11保存点manifestと3小型receipt、計203,543 bytesを既知の外部hashへ照合した。元評価payloadやCI全ログは再読取りせず、保存時点の検証記録を参照した。hash一致を新しい実行の認証や現在のruntime受入とは扱わない。

| 範囲 | 既存の証拠 | 今回の扱い |
| --- | --- | --- |
| 単一writerの保存 | [通常保存](anomaly-multiseed-v0.3-local-publication-2026-09-16.md)：27試験、実writer/別reader、重複root拒否、中断時の完了印なし | `_anomaly_v03_io.py`は当時の実装から不変。保存機能を作り直したり同じ試験を直ちに繰り返す必要はない |
| Linux・共有手例 | [CI34546440692](anomaly-multiseed-v0.3-s4-b1-shared-fixtures-2026-09-11.md)：当時の各minor 1045 pass/67 skip、29共有payload、Windowsとの58照合 | 当時のrevisionの証拠として保持。今回の全sourceの受入へ読み替えない |
| Windows選抜pure試験 | 2026-09-10の固定Capstone 5.0.7による78/78記録 | pinned receipt一致。全Windows回帰・native受入ではない |
| 完走と独立検算 | 区間0〜119の720評価、生成・profile/score/ledger・seed集計・slice監査 | 各保存点のhash一致。元データの再生成や全payload再検算は不要 |
| 解析算術・出力 | 固定draw、手計算fixture、18記述結果表・5,670診断行 | dev/smokeの記述入力と計算部品は揃った。実40 holdoutのCI/gateと正式full documentは未接続 |

保存点に記録されたselected source等の比較は158件中157件一致。差分1件は通常保存時点の `tools/evaluator/README.md` への文書追記で、保存実装の差ではない。複数保存点で同じファイルを比較しており、158は独立したファイル数ではない。

## freeze前の5まとまり

| 順序 | 必要な作業 | 完了条件・再利用するもの |
| --- | --- | --- |
| 1 | 採択済み単一writer・OS実値記録方針を、正式評価用の運用契約案へ具体化する | 科学式・seed順・母数・閾値・bootstrapを維持し、旧計画との差、対象revision、停止/再試行、公開証拠を明記。旧DACL/principal要件を黙ってpassにせず、新契約として確定する。現時点はengineering採択まで |
| 2 | 独立consumerの正式入出力を接続する | 認証済み入力→40登録clusterの完全性→集計→固定50,000回の推論→表・診断・decision→full schema/意味検査の入口を一貫させる。既存の独立計算部品を再利用し、まず架空入力と拒否例で接続を検証。実holdoutを使って実装を調整しない |
| 3 | source/runtimeの受入対象を確定・固定する | cleanでGit bytesと一致するproducer/consumer、実際の入口と依存source、stdlib/拡張/DLL/CRT・起動条件・OS/CPUを記録し検証。最終候補revisionの必要なplatform回帰と共有fixtureを証拠化。旧CIから変更された部分を古いpassで覆わない |
| 4 | controller→保存→独立readerの公開経路を接続する | 既存LocalPublicationを利用し、同一root非上書き、部分失敗、終了確認、markerと全対象coverage、証拠hashの関連付けを新契約の入口から確認。旧formal gateの削除だけで開通させない |
| 5 | 正式対象の容量・時間・停止予算を固定する | 720件で保存した実測・メモリ診断・失敗/再試行記録を使い、holdout 2,880評価と解析/保持分の資源計画を作る。新規の長時間試験は見積りで不足が分かった箇所に限って判断する |

これらは依存する作業のまとまりであり、順序3の最終freezeは2/4の実装確定後に行う。計画・schema等を変更する必要がある場合は差分を先に提示する。現在のformal gate、正式holdout、実CI/gate計算は開かない。

**次の作業は1と2の接点：単一writer方針でconsumerが何を受け取り、何を検証し、何を保存するかを具体的な契約案にする。** 10個の既存consumer入口と正式schemaの不足欄を対応づけ、既存試験で済む部分と新しい接続試験を指定する。正式化の判断は、その案がレビュー可能になってから行う。

## 実装上の根拠

- `anomaly_v03_runner.run_campaign` はruntime検査と `require_campaign_acceptance()` の後にpublisherを接続していない。受入関数は無条件に `s4_acceptance_not_frozen` を返す。旧gateを外すだけではcampaignは走らない。
- `anomaly_v03_generation_audit.coordinate`、`anomaly_v03_seed_aggregate.aggregate_evaluations`、保存観測のreaderはdev/smokeを前提とする。`anomaly_v03_analysis_adapter.compute_fixture_packet` は手例用で、実登録holdoutの受入入口ではない。
- `anomaly_v03_descriptive_report` は用途別の記述出力とschema部品検査まで。認証、算術部品、全正式documentの受入を分けて接続する必要がある。
- `anomaly_v03_engineering_inventory` のsnapshotはinspection processの時点観測で、`full_runtime_inventory_complete=false`。S4 inspection receiptも `closure_verified=false` / `acceptance_status=not_completed` を固定する。既存snapshotを完全runtime受入へ読み替えない。

10個のconsumer入口から静的import候補17モジュールを記録し、全working bytesとGit blobを比較した。`src/banto_ai/manifest.py` のみCRLF/LFの差がある。正規化後は一致するが、raw一致とは記録せず、既存sourceを変更していない。正式freeze用の別clean checkoutでraw一致を確認する必要がある。

旧Linux CI revision `036ecb474dc8fd975263e0ddbb387f5763750109` から現在のselected 17モジュール中11本が変更/追加されている。src/tests/tools/workflow全体では159 pathに差分がある。これは必要試験数ではない。最新候補に必要な回帰確認は残るが、未完成の入口に対して全試験を今繰り返す理由にはしない。

静的import表は、条件付き・未使用importも含む候補表であり、動的load・data/config依存・native/stdlibの全内容や呼出し関係を証明しない。完全なdependency closureとは扱わない。`verified/source-map.json` とseed集計入口を加えた `supplement-source-map.json` を合わせて読む。

## 本流の別作業とWindows更新

旧保存点の本流HEAD `889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e` から、本流がclean `6f1285d28a37edf486ba5c49b8dac3708c7f3067` へ進んでいた。4 commit、5 pathの更新で、temp専用native fixture、handle経由DACL、workflow、説明が含まれる。今回merge/pushや本流変更はしていない。

本流のtracked `docs/README.md` は、Windows3.14.0の関連46件、3.12.10の互換19件、Windows Server CI36054996701の両minor各19件passを記載する。**今回照合したのはREADMEのGit bytesまで**であり、その試験rawやCIを独立再確認していない。本流側も正式受入未完了と記載する。この別作業を本branchへの自動統合や保留principal試験の再開、Windows3.12必須条件の復活とは扱わない。

今回観測OSはWindows Professional 25H2 / build26200 / **UBR9457**。旧engineering記録9445からの更新を記録した。正式pin9168とは異なる。既存720評価のruntimeは過去のまま保持し、現在値で書き換えない。工程1の契約案では採択済み更新方針を反映する。

初回は旧main HEAD固定guard、次はworking/Git raw差guardで停止した。どちらも評価・試験を開始していない。停止記録と実行scriptをOUT直下に残し、確認対象を正しく記録する成功結果を `verified/` へ分けた。過去の証拠を修正して整合させていない。

## 資源と保存範囲

主確認2.450秒、前後標本のprocess peak private26.82MiB、空きRAM最小11.49GiB、commit余裕最小19.98GiB、終了時C126.24/D293.31GiB。点の観測でメモリリーク有無は断定しない。

新観測・評価・score再計算・bootstrap・試験実行はすべて0。元評価payload読取0。実計算checkout `c01d1c9`、完走closed、旧保存点と既存dirty guardは不変。banto-24はPAUSED。保護root・専用account・ACL・UACへ触れていない。Phase 2/3全体、正式source/runtime受入、完全S6は未完了のまま。
