# 正式受入の残件更新（2026-09-26）

**保存済みレポートの解析準備→通常公開→別process読取は完了。次は、予定する5出力と役割別証拠の結合を架空入力で実装する。** [旧5まとまり](anomaly-multiseed-v0.3-acceptance-gap-review-2026-09-25.md)は正式化の作業分類として維持するが、済んだ保存・読取接続を未完了へ戻さない。

対象実装は `f8f20bcf4ac7ade2f20e96f37bc1567328d88a48`、文書の開始revisionは `56bb9a3698e80c082b698b2a45be4adf94064e31`。OUTは `artifacts/acceptance-gap-update-2026-09-26`。文書保存revision・参照pin・資源は同OUTの `savepoint-evidence.json` に保存する。今回は文書整理と静的照合のみで、source変更・試験suite・評価・数値再計算・新しいprocess実行証拠の採取は0。

## 今回の確認範囲

- [実レポート接続](anomaly-multiseed-v0.3-saved-report-publication-2026-09-26.md)の保存点：26,548bytes、SHA256 `53a0c1be44cb21114ada147e32d35346948d9664737bde9b9c41054dc362853a`。62code/18dataのpin不変、11小型receipt計20,083bytesと祖先の保存点を照合した。
- 実装13fileを静的に読み、cleanなpc01のworking bytes・Git blob・作業版bytesの一致を確認した。正式入口は `run_campaign` → `require_campaign_acceptance` で引き続き閉じている。
- 保存済みの架空slice文書は9表・本文1233行・補助2835行。3,162,172bytes、SHA256 `1673653d73b9666fada8d3e7857ca2532846029912b84241784c80d3cfacce56`。残るnullは `status`、`provenance`、`analysis_consumer`、`bootstrap` の4欄で、正式readyはfalse。

既存720評価の元payload・全ログを再読取りせず、保存した検証記録を再利用した。実レポート接続の4payload/2,755,533bytes、子のexit0・終了確認・観測error0は前工程の記録であり、今回の新しい試験結果ではない。前工程43試験も再実行していない。

## 実行前と実行後を分けた5まとまり

| 作業群 | 完了済みで再利用する範囲 | 正式開始前に残るもの | 正式実行後に確認するもの |
| --- | --- | --- | --- |
| 1. 運用契約 | 単一writer、writer終了後のreader、OS実値記録のengineering方針 | 科学条件を維持した正式契約差分、slice対応、更新の許容範囲、失敗時の再登録規則、対象revision | 実attemptが採択条件を守った記録 |
| 2. consumer入出力 | 720評価の監査済み記述入力、40架空clusterの算術・9表180gate・slice草稿 | 登録40cluster/480区間/2880枠のadapter、固定推論の接続、full documentを検査する入口を架空入力で完成 | 実40clusterの全入力・50,000反復・推論結果・正式本文 |
| 3. source/runtime受入 | analysis準備・readerの実process対応、事前依存候補、selected source照合 | 数値analysis/audit/writerを含む役割分担・依存範囲・期待値・必要なplatform回帰を最終候補で確定 | 各実processの前後観測、入出力pin、終了と採取欠落の検査 |
| 4. 公開と読取・監査 | 実レポート4payloadの通常公開、終了後の別reader、応答喪失/reader失敗時の保全 | 予定5payloadのwrapper、外部receipt、全inventory、独立数値audit用の別入口/rootへの接続 | 実5payloadの公開・reader確認、別計算による最終数値監査 |
| 5. 容量・時間・停止予算 | 既存実績と外挿、process別上限、資源診断 | 正式推論/独立auditを含む全体予算、system commit・出力容量の監視/停止条件と所有worker処理 | 消費量・停止有無・終了処理・保存量の実測 |

この5群は試験本数でも、Phase2/3全体の残件数でもない。**実行後の正式結果を、実行開始の前提に要求しない。** 開始前に必要なのは結果を作成・検査・保存する実装と、その受入記録・契約・予算である。実データの成功receiptは開始後に得る。

## T01〜T12の現在地

[初期対応表](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)の件数区分は当時の履歴として保持し、現在の残件判断には下表を使う。

| ID | 接続・確認済み | 残る正式接続 |
| --- | --- | --- |
| T01 | fixture/engineeringを区別し正式modeを拒否 | 採択済み契約・受入と正式入口の結合 |
| T02 | 外部pin・path・inventory、保存7入力の認証 | 正式producerの全payloadと終了証拠 |
| T03 | dev/smoke120区間720枠・順序・候補入力対応 | 登録40seed/480区間2880枠の完全性adapter |
| T04 | 過去失敗と最終attemptを保持し、inconclusiveを成功へ変換しない | 正式失敗時の別version/root/未使用seedによる再登録規則 |
| T05 | 720評価の独立観測/score/ledger・生成検算を再利用 | 新しい正式観測から独立auditへ渡す経路 |
| T06 | raw count/null・層/layout対応と40架空clusterのratio-of-sums接続 | 登録clusterの認証・完全性と推論入力の結合 |
| T07 | 最大64反復のfixture、共通draw算術・9表180gateの文書adapter | 固定50,000反復の正式入口・実行receipt・full document |
| T08 | 架空sliceの本文1233行・補助2835行・詳細9表 | mappingの正式採択と実観測からの導出対応 |
| T09 | analysis準備/readerのsource/runtime・依存候補・実process対応 | 数値analysis/audit/writerの証拠、正式本文provenance、受入範囲と完全な依存固定 |
| T10 | 認証済み4payload→単一writer公開まで接続 | execution/coverage/analysis/diagnostics/verificationの5payload wrapper |
| T11 | 部分書込み・応答喪失はunconfirmed、公開後reader失敗でも公開物を保全 | 正式段階状態・外部receipt回復規則との結合 |
| T12 | writer終了後の別observed readerを実2.76MBレポートで確認 | analysisとは別の計算でCI/gate/選択を検算する入口・別rootと最終監査 |

別readerによるbytes/構造確認は、独立した数値検算の完了を意味しない。既存の保存失敗・別reader試験を同じ条件で繰り返す作業は残件に含めない。

## 草稿のnull 4欄の扱い

| 欄 | 開始前に作る接続 | 実行後に必要な根拠 |
| --- | --- | --- |
| `status` | planned/running/failed等の外側状態と、科学的なnot_evaluated/inconclusiveの対応 | 実coverageと最終状態。保存成功だけで性能合格にしない |
| `provenance` | producerのsource/runtime/input/exitから本文へ結ぶ契約 | 実producer全体の証拠と外部期待値への照合 |
| `analysis_consumer` | 数値解析側のsource・revision・証拠の供給口と検査 | 正式解析を実行した役割の証拠。既存の保存結果準備役割では代用しない |
| `bootstrap` | 登録drawと固定反復数を実行・照合する入口 | 50,000反復・2,000,000 index bytesと対象40clusterの対応 |

4欄は4本の新規試験やプロジェクト全体の残件数ではない。固定値を埋めただけの文書や、validatorへ渡した申告値だけを実行証拠にしない。現在の草稿・正式ready=falseをそのまま保持する。

## 予算・監視の未充足

既存実績からの約59.91GiB・178.17時間、仮案の240時間・96GiB・空き32GiB・開始128GiB/2コピー224GiBは[前回見積り](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)のまま未適用。失敗attemptやhardlink名を含む論理量の外挿であり、物理ディスクの走査結果や完了日時の保証ではない。正式推論・最終独立auditの時間/メモリ/出力分が未確定。

現行controllerの48時間/32GiBとprivate 2GiB、空きRAM4GiB/空きdisk20GiBはengineering用。全体上限の検査は呼出し・区間境界で、所有workerには別の時間/private/output上限がある。process supervisorのoutput上限はstdout/stderrを対象とし、全成果物ディレクトリの連続した容量上限ではない。起動前の資源検査とsystem commitの診断記録は、実行中のcommit不足に対する強制停止を代替しない。

正式準備では、親・子・監査・公開・保全を含めた対象、検査頻度、停止時に所有processと既存出力をどう扱うかを先に定義する。今回閾値を引き上げたり新しい数値を採択したりしない。前工程の26.528秒/69.38MiBは保存レポート準備の実績で、正式50,000反復の予算へ外挿できない。

調査開始時の空きRAM10.85GiB、commit余裕19.36GiB、C/D空き133.12/367.39GiB。最終値はsave-checks.jsonへ記録する。単時点の値からリークの有無や他作業の消費原因は判定しない。

## 次に実装する単位

**I/Oを持たない、架空入力専用の5出力wrapper/証拠結合adapterを1単位として実装する。** 既存の文書・slice・証拠validatorを再利用し、正式入口は閉じたままにする。[契約案§4](../anomaly-v03-consumer-io-proposal.md#4-保存物と正式schemaへの対応)を以下まで具体化する。

1. 入力は架空文書/診断、予定coverageと段階状態、役割別の供給証拠、呼出し側が保持する期待pin。証拠自身から期待値を作らず、role/mode/operation/revision/入出力の対応を検査する。
2. 戻り値は5つの予定payloadと不足一覧。fixture専用formatを使い、正式schemaや正式identityへ昇格しない。本文のnullと未充足を保つ。将来の公開markerはpayloadの外、marker pinを保持するreceiptはさらに外へ置き、循環参照を作らない。
3. 保存結果準備役割を正式数値解析として流用する例、欠落・役割違い・入力pin違い・coverage不整合・失敗を成功にする例を拒否する。意味が正しい小さい架空例で対応を確認し、既存保存/readerの同じ試験や実データ推論を繰り返さない。
4. 完了条件は仕様・pure adapter・対象を絞った試験・保存点。新しい観測/評価/公開processの起動、50,000回実行、正式状態の穴埋めはこの単位に含めない。

その後に数値解析/auditの実行入口・役割証拠と資源停止条件を接続し、最終候補の回帰と契約/予算判断へ進む。正式採択時に必要な判断材料は、(a)具体的な契約差分・候補revision・受入記録、(b)全工程の予算・停止/再登録条件。今回は未完成なので採択確認を求めず、許可済みのengineering実装を進める。

## 保存境界

実計算checkout `c01d1c978f78bab51391392d56cdcb7aab5afaab`、本流 `6f1285d28a37edf486ba5c49b8dac3708c7f3067`、closed・既存dirty文書・既知CRLF差・旧候補を保全。`banto-24`はPAUSED。正式許可・promotion・独立S6・trust・execution_authenticated・完全依存固定はfalse、Phase2/3全体は未完了。principal/UAC/ACL、旧保護root、push/mergeを今回の対象へ戻さない。
