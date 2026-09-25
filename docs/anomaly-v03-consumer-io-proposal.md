# 単一writer方針での解析consumer入出力契約案

最新実装（2026-09-25）：[engineering consumer入口](anomaly-v03-engineering-consumer.md)の16試験と実接続を完了。既存dev/smokeの記述結果を再利用して通常権限で保存・読み戻しする。新しい数値解析や正式評価は起動しない。本契約案の正式採択状態はdraftのまま。

実装追記（2026-09-25）：[入力validator](anomaly-v03-consumer-input.md)・[checkpoint adapter](anomaly-v03-consumer-checkpoints.md)・[公開reader](anomaly-v03-consumer-publication.md)に続き、[監査済み集計入力との結合](anomaly-v03-consumer-analysis-binding.md)を追加。14新規試験と120区間720評価の導出対応を確認し、過去失敗・判定不能を保持。旧算術検証を再利用し、新規解析/全payload認証/正式採択は行わない。全体契約はdraftのまま。

2026-09-25。提案ID `anomaly-v03-consumer-io-proposal-v1`、状態 **draft / 実行許可なし**。基準revision `0b75c1ea89a15e04dbde0963ae2b634648a10201`。[受入残件表](results/anomaly-multiseed-v0.3-acceptance-gap-review-2026-09-25.md)の1「運用契約」と2「consumer接続」を具体化する。これは正式な受入証明やfreezeではない。

目的は、保存された評価から独立に計算し、欠けた入力や途中失敗を合格へ変換せず、解析結果と監査結果を別々に保存できる入口を作ること。単一writerとOS実値記録は[engineeringで採択済み](anomaly-v03-single-writer-evaluation-proposal.md)だが、正式評価の運用契約への適用は未確定である。

## 1. 変更する境界と維持する科学条件

| 対象 | この案 |
| --- | --- |
| 科学条件 | 候補式・生成/丸め・分割・seed順・layout・quality・閾値・persistence・matching・分母・推論・選択規則を維持する。旧config/schema/registryを編集しない |
| 保存の前提 | 同じ出力rootは単一writer。writer終了後にreaderを動かす。既存rootを再使用せず、全payloadと完了印を照合する。敵対的同時書換えに対するprincipal分離の保証を追加しない |
| Windows更新 | 各producer/consumer attemptの開始・終了時の実OS build/UBRと実runtimeを記録。各attempt内の変化は停止。attemptをまたぐ更新の許容範囲は正式化前に登録する。過去のruntimeを現在値で上書きしない |
| 旧正式契約との差 | 旧DACL・独立token要件と固定UBR9168を合格扱いしない。新しい運用契約、wrapper、受入証拠を別に登録する。正式化する際は差分と対象revisionを確定する |
| 実行入口 | 旧 `run_campaign` と `require_campaign_acceptance` を維持。`--force`、環境変数、schema緩和による開通は設けない。新契約が受け付ける入口と出力名は別途実装する |
| 既存720評価 | 開発用8 seed・動作確認用2 seedの証拠として再利用する。正式holdoutの40 seedへ加算しない。既存結果の再生成・改名による正式化はしない |

正式化する運用方針の候補IDは `anomaly-v03-single-writer-research-v1`。これは予約案で、現行validatorが認識するIDではない。採択済み `anomaly-v03-single-writer-v1` のengineering成功を根拠に、正式許可を暗黙に付けない。旧正式出力rootは使わず、承認された方針IDを含む専用rootを実装段階で指定する。

Windowsはこのbranchの採択条件どおりPython3.14.0。Linux互換性検証の3.12/3.14は維持する。本流で追加された3.12.10互換試験を、こちらのWindows必須条件に追加しない。

## 2. 入口が受け取る情報

以下は予定する論理項目であり、既存CLIに追加された引数ではない。実装前に閉じたschemaへ落とし込む。

| 論理入力 | 内容と検証 |
| --- | --- |
| `mode` | `fixture`、`engineering-dev-smoke`、将来の登録済み正式modeを明示。架空入力・開発データから正式modeへの推定/昇格を禁止する。現在は正式modeを拒否する |
| `contract` | 方針ID・版・科学契約のraw hash・登録された対象一覧・受入証拠への参照。結果自身が記した `accepted=true` やhashだけでは実行許可にならない |
| `input_anchor` | 呼出し側から渡す完了receiptと外部SHA-256、明示したproducer root。root内の自己申告hashのみで認証しない |
| `source_snapshots` | 信頼された呼出し側が指定revisionから取得したproducer/analysis/auditの正確なsource bytes。役割ごとにrevisionと全依存を確定し、実行時のsourceと結び付ける |
| `runtime_evidence` | 実行した各役割のPython/stdlib/拡張/DLL/CRT、OS/CPU・起動条件・検索経路方針・前後同一性。既存のinspection snapshotや静的import表を完全受入へ読み替えない |
| `output` | 新規の解析rootと別の監査root。producer root、互いのroot、既存出力、保護rootと重ねない。名前・相対path・通常ファイル条件は既存I/Oの制約を維持 |
| `budget` | bytes、時間、process private、system commit余裕、ディスク余裕の登録上限。上限超過で所有processだけを止め、自動で上限を拡大しない |

正式対象は **40 seed × 12 layouts × 2層 = 960 datasets、各3候補で2,880評価**。候補表はcore/quality-stress/overallの9表。全identity・順序を開始前に固定し、candidate間の入力hash一致、core/stressの正常系列の対応、全layoutの所属を検証する。登録済みseed番号の照合と、holdout観測の読取りは区別する。

失敗・部分結果・未開始がある場合も予定2,880枠を残し、成功分だけの集計を正式性能にしない。正常に処理されたprofile inconclusiveやquality unavailableはsoftware failureと分け、所定のnull・miss・availability低下として保持する。

## 3. 読取り・解析・保存の順序

1. **入口検査**：mode、契約、外部anchor、source/runtime受入、上限、出力先指定を検査する。現在の実装段階では正式modeをここで拒否し、producerデータや出力rootを開かない。
2. **入力を認証**：明示したrootの完了印と全inventory、raw/canonical hash、サイズ・行数・JSONの厳密性、identity、全予定枠と状態を順次照合する。producerの終了確認も要求する。markerだけで解析を始めない。
3. **独立に検算**：生成/丸め、profile/score、support、episode/matching、母数を観測から確認する。1dataset/評価単位で大きなオブジェクトを解放し、監査報告を元bytes・identity・source/runtimeへ結び付ける。producerの判定関数をそのまま正解として呼ぶ経路にしない。
4. **clusterへ統合**：12 layouts・両層・全候補をseed単位にまとめ、raw counts/exposureを合算する。overallは層のraw合算。遅延は検出例の度数を合算し、medianの平均を使わない。
5. **固定推論と表作成**：同じ40-seed draw列を全候補・層・paired差に使い、50,000 replicates、2,000,000 index bytesの登録hash、type-7区間を照合する。分母0を除外・再抽選・0/1補完しない。丸め前の値で全gateを判定し、C1優先の固定選択を行う。
6. **解析を保存**：全schemaと意味検査、input/source/runtimeの終了時確認を通してから、LocalPublicationを用いる新契約のwriterで全JSON payloadを保存・再読取りし、最後にmarkerを作る。正式用の運用adapterは未実装であり、旧正式名を通常保存APIへ直接渡さない。
7. **別readerと独立audit**：writer終了後に別processが解析marker・全payload・意味を確認する。auditはproducerとanalysisをread-onlyで受け取り、生成/scoreだけでなくCI/gate/選択も独立に照合し、別audit rootへ公開する。analysis側の同じ判定関数を再度呼ぶだけで独立監査済みにしない。
8. **表示を作成**：監査済みartifact外へ要約Markdown/HTMLを出す。表示の訂正で解析・監査の確定payloadを書き換えない。研究上qualifiedでも製品利用・PLC書込み許可は与えない。

別のconsumerが公開物を読み始める際は、旧計画どおり全inventoryを新たにhash照合する。**数値計算の再実行とbytes照合は別**である。既存720評価の保存済み監査をこの設計作業で繰り返す必要はない。将来、解析の再開で監査報告を再利用する場合は、入力全hash・契約・source/runtime・対象範囲・報告hashの同一性を確認する独立の再開契約が必要で、今回の案だけでキャッシュ再利用を正式許可しない。

正式holdoutの途中失敗に、engineeringの同一区間attempt再試行をそのまま適用しない。旧計画S5の別version/root/未使用seedによる再登録規則を維持し、変更する場合は正式開始前に明記する。途中の性能を見て対象や条件を変更しない。

## 4. 保存物と正式schemaへの対応

新wrapperの予定payloadは `execution.json`（方針・source/runtime・入力inventoryと段階状態）、`coverage.json`（全予定枠と失敗を含む状態）、`analysis.json`、`diagnostics.json`、`verification.json`（検査範囲と結果）。markerの在庫は全payloadを含む。wrapper内にmarker自身のhashを埋めて循環参照にせず、外部receiptがmarker hashを保持する。audit側は独立したrootとreceiptを持つ。

旧analysis schemaにはruntimeや運用方針の欄がないため、これらを新wrapperへ明示する。旧schemaを通ることと、新方針の受入を通ることは別である。`analysis.json` の科学identityを使う場合も、旧runtime/DACL条件で実行したかのような主張を加えない。

| 正式schema必須欄 | 供給元・不足する接続 |
| --- | --- |
| `schema_version` | 凍結schemaの `0.3`。wrapperには別のformat/方針IDを持つ |
| `status` | run/engineering/performanceを別々に導出。保存完了だけでengineering passにしない |
| `provenance` | 科学revision、producer revision/source、registry hash、認証済みinput inventory。実行根拠とsource bytesを信頼された呼出し側から受ける |
| `result_type` | 凍結済み科学identity。fixture/engineeringの成果物は独自formatを維持し、正式identityへ変換しない |
| `analysis_consumer` | clean revisionと依存sourceのraw bytes。現在の17モジュール候補表だけでは完全freezeにならない |
| `bootstrap` | 登録literalと実行receiptを対応させる。固定値を記載しただけで実行済みとしない |
| `candidate_tables` | 40 clusterからの9表、固定順の全180 gates、CI/null/profile状態。現在のfixture adapterはこの入口を代替しない |
| `slices` | 下記の単一指標への対応と全sliceの在庫検査。分母や対象外参照を補完・削除しない |
| `selected_candidate` | 全条件を満たす場合のみC1優先、次にC2。C0は自動昇格しない。不完全入力ではnull |
| `decision` | 所定のnot_evaluated/qualified/no_promotion/inconclusive。artifactがあるという理由でqualifiedにしない |

`validate_result_contract` のsource検査へ、呼出し側がrevisionに結び付けたbytesを渡す必要がある。自己申告sourceとhashの一致だけでは実行者の認証や独立性を証明しない。

### 診断表の提案

凍結slice schemaは `(candidate_id, stratum, dimension, key)` が一意で、`metric` は1個、系列ID欄がない。利用可能率・閾値超過率・警報開始率の3行を同じkeyで並べると意味検査に反する。

提案は **analysis.slicesにincident recallとscore availabilityを格納し、diagnostics.jsonに4系列全部を名前付きで保存する** 方法。既存schemaへ新列を追加せず、各系列の意味とsidecarの在庫・値を新wrapperの検査で保証する。正式なmappingの採択はまだ行っていない。

- incident：6次元48 cells/表。分子は検出件数、分母は全予定positive incidents。class precisionはnot applicable。遅延の度数と検出例への条件付けを保存する。
- score：9次元89 cells/表。availability、threshold-exceedance、signal-onsetの分子を分ける。分母は試験内のscore対象行で、unavailable行も含む。`actual_count`はその系列の分子、`planned_count`は予定参照数。
- event-offsetは同一行を複数eventが参照し得る。対象外signalと試験外offsetをsidecarに残し、全scoreの排他的分割としない。qualityのcurrent/previous依存とfaultとの重複も保持する。
- 9表で主documentのslice行は `9×(48+89)=1,233`、全4系列のsidecarは `9×(48+3×89)=2,835` が予定在庫。これはholdoutの実測件数ではない。
- 補助sliceは記述値として保存し、CIはnot_evaluated（分母0はnot_applicable）。補助sliceに有意差探索や採択gateを追加しない。主指標のCI・180 gatesは省略しない。

## 5. 失敗と完了の意味

| 状態 | 保存/外側の扱い | 性能への影響 |
| --- | --- | --- |
| 入力・契約・hash・source/runtimeの不一致 | consumerを止め、原因と確認済み範囲を別の失敗記録へ。元入力を修復しない | not_evaluated、selected=null |
| 入力coverageがpartial/failed/not_started | 全予定枠と既存証拠を保全。成功したcellだけを正式集計しない | not_evaluated/inconclusive、昇格不可 |
| profile inconclusive / 必要CIの分母0 | 定義どおりの結果として残す。欠落と区別する | 候補はqualified不可。null replicateの削除・再抽選なし |
| 完了印前の保存失敗 | 失敗したwriter/rootは再使用せず、完了印を作らない | 成功扱いしない |
| marker作成後の応答消失 | markerを消さず、writerを再開しない。外部に保持した期待情報で別readerが照合。根拠が足りなければ未確認のまま | markerだけで工程成功にしない |
| 公開後のreader/audit不一致 | 解析payloadを書き換えず、外側の監査/監視記録をfailedにする | trust/昇格を閉じる。別の監査結果と失敗を保持 |

`marker作成済み`、`writer終了済み`、`reader検証済み`、`独立audit完了`を別に記録する。解析保存時点でaudit未了の `independent_s6_complete=true` を書かない。最終trustはproducer・analysis・auditの各receiptを結び付けた後に判断し、既存の確定ファイルへ追記しない。

## 6. 再利用する入口と必要な接続試験

モジュール名は `src/banto_ai/anomaly_v03_` 以下。正確な関数名・行番号・raw hashは `artifacts/consumer-io-contract-2026-09-25/contract-map.json` に保存した。

| 既存モジュール | 再利用する処理 / 追加する接続 |
| --- | --- |
| `observation_audit` | byte認証・paired入力対応 / 現行120区間・720評価固定の外側を新しい入力adapterで分離 |
| `generation_audit` | 独立生成/overlay/丸め / coordinateのdev/smoke制約を残して別の登録済み正式入口を設ける |
| `score_audit` | profile/score再構成 / 認証済み観測への結合 |
| `ledger_audit` | support/episode/matching/母数 / 全予定枠との結合 |
| `seed_aggregate` | raw集計、監査報告の認証 / 現行720固定の契約を壊さず40-cluster入口を追加 |
| `inference_audit` | draw、ratio-of-sums、type-7、gate算術 / 正式集団と実行receiptへの結合 |
| `analysis_adapter` | 表形式と手例検査 / full documentとsource/statusの結合 |
| `analysis_inputs` | counts/exposure/delay/slice統合 / 正式集団の認証と完全性検査 |
| `slices` | 条件別counts・度数・対象外参照 / 2系統の保存先への完全な対応 |
| `descriptive_report` | 表/診断の対応と閲覧表示 / 正式結果とengineering表示の入口を分ける |

必要な接続試験を12群に限定して記述した。**12件を新たに実行したという意味ではない**。詳細な既存test methodへの対応はcontract-mapにある。

| ID | 確認する接続 | 既存試験との関係 |
| --- | --- | --- |
| T01 | fixture/dev/smokeの正式mode混入、未受入時にread/write前で拒否 | role/scope拒否を再利用し、新入口だけ追加 |
| T02 | 外部digest、root/path、重複JSON、marker/receipt不一致 | 既存の認証部品を使う呼出し順を確認 |
| T03 | 予定枠の欠落・重複・順序・候補間の入力違い | 既存inventory検査を正式adapterへ接続 |
| T04 | failure履歴、partial、profile inconclusiveの区別 | 失敗cellの脱落・success化を防ぐ外側状態を追加 |
| T05 | 独立検算へ認証済み観測を渡しproducer判定を信頼しない | 独立算術の既存証拠を再利用し、呼出し経路を確認 |
| T06 | ratio-of-sums、null、両層・全layoutが同一cluster | 算術手例を繰り返さず正式入力への対応を確認 |
| T07 | 全候補共通draw・固定gate・選択、inconclusive制御 | 既存算術/goldenを使い登録metadataと出力を結合 |
| T08 | 主sliceと4系列sidecarの全在庫・値、offset除外 | 新たな保存対応だけを小さな固定入力で検査 |
| T09 | source/runtime証拠とfull schema/意味検査 | 存在するだけのreceipt・自己申告passを拒否 |
| T10 | consumer意味検査失敗でmarkerなし、既存root非上書き | LocalPublicationの合格済み試験を再利用しcallback接続を追加 |
| T11 | 応答消失と公開後失敗の外側状態 | 保存APIの試験を再利用、既存markerを撤回しない |
| T12 | 別readerによる再hashと意味検査、再封印した不整合の検出 | 同時書換え試験ではなく、順次作る架空の不整合結果を使う |

最初の実装単位は **T01〜T04の前段にあたる入力契約validator**。I/Oなしの純検査から始め、fixture/engineeringを明示し、formal modeは拒否する。観測読取り・推論・writerをまだ接続しない。これなら正式運用方針の採択や長時間試験を待たずに進められる。

正式化へ進む判断材料は、この契約差分、slice対応、source/runtime受入範囲、正式失敗時の再登録規則、容量・時間予算を揃えたものとする。正式入口を実際に開く前にレビュー可能な実装・検証記録まで準備する。本案の完成だけでfreezeやS4/S6完了にはしない。
