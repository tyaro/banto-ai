# 保存結果の独立検算と長時間実行の進行記録

2026-09-16。単一writerの運用改訂を継続する。独立ledger検算、固定plan・journalのmetadata検査/状態復元、旧6件trialとのpreflight証拠照合、metadata専用の追記writerは実装済み。全dev/smokeを動かすcampaign controllerは**未接続・実行未許可**。
科学的な式・seed・layout・候補・母数・bootstrap・性能gateと、旧formal gateを変更しない。

## 独立検算の到達範囲

`anomaly_v03_ledger_audit.py` は標準ライブラリだけを使い、保存scoreの連続区間を分割する別実装で下記を再構成する。
producerのscoring/episode/matching/accounting関数は呼ばない。IO側は既存のstrict JSON/schema、登録event inventory、保存inventory/hash、Git source captureを共用する。

| 検査 | 今回 | 残る条件 |
| --- | --- | --- |
| 保存inventory・外部marker hash・supervision・source | 共通の保存/来歴検査で照合 | 独立した数式検算とは区別する |
| strict閾値、streak、signal episode、equipment merge | 保存scoreから別実装で再構成 | score/phase/availabilityの元となる観測処理は未検算 |
| 最初の候補のclaim、再探索禁止、causal support、context | 別実装で再構成 | 登録eventの定義自体は共通registry検査 |
| recall、precision、clean exposure、burden、availability、delay | 固定母数から別実装で再集計 | availabilityは保存されたavailableの集計。available判定の導出は未検算 |
| 正常生成式・丸め、profile fit/calibration、残差/score導出 | 未実装 | 独立consumerの次の計算範囲 |
| bootstrap、CI、性能gate、全campaign coverage | 未実施 | 現在の6件だけでは実行しない |

整数、ID、時刻、状態、episode/incidentはexact比較。metricの浮動小数だけabs/rel各1e-12で比較し、null・bool・整数母数を取り違えない。
結果の `status=ledger_checks_passed` は表の範囲のみ。`score_derivation_verified=false`、`independent_s6_complete=false`、performance=not_evaluated、formal_permission=falseを維持する。

[初回の実読取り結果](results/anomaly-multiseed-v0.3-independent-ledger-audit-2026-09-16.md)は全6件一致、92.828秒/peak private177.83MiB。入力46 filesは不変、データ生成・producer score再計算は0だった。

### 実行と入力の固定

producerとconsumerの両clean作業コピー・完全40桁revisionを指定する。consumerのCLIはそのconsumerコピーのentrypointから起動する。
入力は既存trialだけ。生成器・scorer・正式campaignを起動せず、入力ファイルを変更しない。出力はstdoutへJSON、失敗はstderr/exit2。

```powershell
C:\Python314\python.exe -B tools/evaluator/audit_anomaly_v03_saved.py `
  --input-root <保存済みtrialの絶対path> `
  --marker-sha256 <外部保存したmarker hash> `
  --supervision-sha256 <外部保存したsupervision.jsonのhash> `
  --producer-root <producerのclean作業コピー> `
  --producer-revision <producerの40桁commit> `
  --consumer-revision <consumerの40桁commit>
```

1ファイル32MiB・payload総量256MiBまで、1評価ずつ読む。これはprocess全体のメモリ上限ではない。
CLI内の時間/private bytes検査は終了時であり、途中で強制停止する監視は未接続。今回の実読取りでは別の所有process監視を付け、10分/1GiB上限・0.25秒間隔で停止/終了確認する。保存・完了の宣言はその監視結果と合わせて行う。

## 全dev/smokeの進行記録

目的は約19時間の処理を、検証済みの単位を残して中断・再開できるようにすること。同じ出力先の単一writerを前提とし、専用principal試験や権限分離の追加試験は再開しない。
metadata用のscopeは `engineering-dev-smoke-checkpoints`、planは `anomaly-v03-checkpoint-plan-v1`、recordは `anomaly-v03-checkpoint-record-v1` に固定した。既存6件用CLIの対象や上限を可変化して代用しない。

### 固定順序と範囲

- role順はdev→smoke。各roleは登録seed順→layout 0..11。
- 1 chunkは1 seed/layoutの2層×全3候補。内部順序はcoreのC0/C1/C2→quality-stressのC0/C1/C2。
- devは96 chunks/576 evaluations、smokeは24 chunks/144 evaluations。全120 chunks/720 evaluationsを開始前に計画へ保存する。
- planにproducer/consumer source revision、runtime方針、scope、全identity、予算、順序のhashを含める。性能の良し悪しで対象を増減・並替えしない。
- 今回の6件trialは受入用の参照証拠。新campaignのcoverageを自動的に6件充足させない。

### 出力と再開の境界

campaign配下へ `plan.json`、番号付きの不変 `journal/000001.json` 等、各chunkの新しいattemptを作る。完了済みpayloadやjournalを上書きしない。
journalの各レコードは前レコードhash、chunk index、attempt ID、保存先、marker hash、supervision hash、audit hash、状態・失敗理由を持つ。最新状態はplanとjournalから導出し、編集可能な集計値だけを再開根拠にしない。

| 停止した位置 | 保持する状態 | 次の起動で行うこと |
| --- | --- | --- |
| chunk未着手 | not_started | 固定順序で次のchunkを選ぶ |
| 計算・保存途中 | interrupted/failed、残る計画・journal・部分成果物 | 完了扱いせず、新attemptが必要。部分evaluationを継ぎ足さない |
| marker作成済み、終了監視/独立検算未確定 | saved_pending_verification | 既存bytesを検証する。markerだけで成功扱いしない |
| source/runtime/hash不整合 | blocked_integrity | 後続を止めて原因確認。自動補正・再生成で隠さない |
| marker・終了監視・必要なconsumer検査が揃い、chunk記録確定 | verified_complete または verified_inconclusive | 毎回hash/来歴を再照合してから次の未完了chunkへ |

再起動時は記録済みchunkのsource/runtime/入力/出力/監視/検算を照合する。旧sourceと違う実行コードで残りだけ継続しない。
Windows更新は各attemptで実値を記録し、そのattempt内の変化を停止条件とする。更新を含む混在runtimeのcampaign受入条件を開始前の方針に明記する。
失敗後の新attemptは旧attemptを削除・除外せず関連付ける。性能値を見て最良attemptを選ばず、事前ルールにより必要検査が初めて揃ったattemptを使う。
全120 chunksがcoverageを満たすまでcampaign完了印を作らない。inconclusiveやfailure履歴はcoverageに残す。途中集計を正式performance passにしない。

### 予算と次の実装

plan builder/validatorとjournalの状態導出を、データ生成なしのfixtureで実装した。切断されたjournal、重複chunk、順序違反、source差分、markerだけの偽完了を拒否する。保存済み6件を読取り専用で参照する証拠照合と、metadata専用追記writerも接続した。次は、新scopeのattempt出力契約をvalidatorへ具体化し、controllerへの接続を準備する。既存計算結果を上書き・再生成せず、旧trialを新campaign coverageへ流用しない。
consumerのprofile/score導出とruntime inventoryの残件を整え、新scopeのproducer/consumer revisionを固定する。
長時間実行の開始前に、controller・consumerも含む容量/所要時間、1 chunkとcampaign全体の上限、途中停止の境界を確定する。前回概算14.8GiB/19.1時間はbootstrap・独立consumer等を含まず、正式容量保証に使わない。
全dev/smokeの実行開始、上限拡大、holdout実行は今回の設計や部分検算だけでは行わない。

### 実装済みのmetadata CLI

`src/banto_ai/anomaly_v03_checkpoints.py` はファイルを開かず、渡されたplanとjournalだけを検査する。CLIの `plan/inspect` も読み取りと標準出力だけで、実行・追記・再開・成果物の書換えを行わない。

```powershell
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py plan `
  --producer-revision <40桁のproducer参照revision> `
  --consumer-revision <40桁のconsumer参照revision>

C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py inspect `
  --plan <plan.jsonの絶対path> --plan-sha256 <外部保持したcanonical plan hash> `
  --journal-dir <journalの絶対path> --record-count <外部保持した件数> `
  --head-sha256 <外部保持した末尾recordのraw hash>
```

planは120 chunks/720 identities・順序・ID・sourceの参照revision・runtime方針とそのhashを含む。source revisionは宣言値であり、このCLIはGitの実在・clean状態・依存sourceを照合しない。`status=metadata_only`、`execution_authorized=false`、`budgets.status=not_frozen` とし、chunk/campaign/controller・consumer予算はnullで残す。現時点で実行用の凍結planとは扱わない。

番号は `journal/000001.json` から欠番なし。record bytesはsorted/compact/UTF-8のcanonical JSON＋LFに固定し、前recordのraw SHA-256へ連結する。先頭のprevious hashと、空journalのheadはcanonical plan hash。planのファイル整形はhashへ含めないが、読み取り中にplan bytesが変われば拒否する。末尾の削除はchainだけでは検出できないため、件数とheadをjournalの外に保持し、読み込んだ末尾から自動取得しない。これは単一writer運用での整合検査であり、改変者の認証や将来の不変性の証明ではない。

各recordは固定chunk index、1始まりの連番attempt、`chunks/000/attempt-0001` 形式の相対保存先、source/runtime、marker/supervision/auditのhash、状態・理由を持つ。各attemptはrunningから始まり、保存後にsaved_pending_verificationを経る。失敗/中断を記録した場合だけ同じchunkの次attemptへ進め、旧attemptと理由を履歴へ残す。integrity失敗後は後続recordを拒否する。marker単独でverifiedへ進めず、6件すべてのID/状態・終了確認・runtime前後一致・監視と検算hashが必要。inconclusiveはそのまま残す。
公開前に失敗したattemptではmarkerがなくてもsupervision hashを保持できる。再試行後の復元結果にも、各attemptのcontext・証拠hash・理由・対応record番号を残す。

ただし、これらのhashとoutcomeも現段階では宣言値にすぎない。`verified_complete` / `verified_inconclusive` は**journalが宣言している状態**であり、reportは常に `evidence_revalidated=false`、`resume_authorized=false`、`campaign_completed=false`、`independent_s6_complete=false`。120 chunks全部の宣言が揃ってもcoverage宣言を示すだけで、成果物の再照合を要求する。runningで記録が終われば中断状態の確認、markerだけなら保存済みattemptの検証を案内する。

読み取りではplan 1MiB/record 16KiB/journal合計16MiB/最大4096 recordsを検査し、番号付きファイル以外・途中JSON・非canonical record・読み取り中の変更を拒否する。readerは `anomaly_v03_checkpoint_store.py` に共通化した。これはmetadata file上限であり、process全体の資源監視は未接続。CLIはcampaignのmarkerや完了印を作らない。

### 保存済み6件とのpreflight証拠照合

`checkpoint_anomaly_v03.py preflight-trial` は、旧engineering-devの6件を参照する専用の読取り経路。最初のchunk/attempt1についてrunning→saved_pending_verification→verifiedの3 recordsを持つ**参照journal**を使う。これは実行履歴を後付けしてcampaignへ採用する機能ではない。

```powershell
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py preflight-trial `
  --plan <参照planの絶対path> --journal-dir <参照journalの絶対path> `
  --reference <reference.jsonの絶対path> --reference-sha256 <外部保持したreference raw hash> `
  --verifier-revision <今回のclean検証用作業コピーの40桁commit>
```

referenceは `anomaly-v03-checkpoint-preflight-reference-v1` / `purpose=historical-six-cell-trial-only`。
plan/head hashとrecord件数を `journal.expected_plan_sha256/expected_record_count/expected_head_sha256` に格納する。`trial_root/producer_root/consumer_root/audit_path/audit_monitor_path` は明示した絶対pathで、`audit_monitor_sha256` も外部固定する。marker/supervision/audit hashは検証済み宣言recordから得る。consumer_rootは**過去の監査consumer**で、今回のverifierとは個別に固定する。

処理は参照journal検査→各証拠hash/旧consumer source照合→既存readerによる全payload検証と6件ledger再検算→保存済みauditの安定項目との比較→journal・参照/証拠の再読取り。この間、新たな観測生成やproducer score計算は行わない。参照revision・runtime・6件のIDとsuccess/inconclusive・監視の正常終了/上限/呼出し先・auditの入出力を結び付け、相違があればexit2で止まる。

結果の `preflight_evidence_revalidated=true` は旧trialとの参照照合だけを示す。`campaign_evaluations_credited=0`、`campaign_attempt_roots_verified=false`、`resume_authorized=false`、`campaign_completed=false` を維持する。journalの仮想attempt_rootと旧trialの実rootを分けて報告し、実campaignへのroot対応機能には使わない。profile/score導出の独立検算と完全S6受入も未完了のまま。

source照合には旧producer・旧consumer・今回verifierのclean作業コピーを使う。Windows更新があれば過去のproducer/consumerと今回verifierの実値を別々に保持し、過去の値を書き換えない。各実行内のruntime変化は既存readerの停止条件。今回verifierの資源欄は既存audit処理部分の値で、全CLIの実測/停止監視は外側の所有process監視に記録する。実読取りは10分/1GiB/ログ8MiBの範囲で行う。

### metadataを上書きせず保存・追記する

`anomaly_v03_checkpoint_store.py` とCLIの `store-*` は、単一writerでmetadataだけを保存する。既存のexclusive write・flush・読戻し・置換禁止renameを再利用し、専用principalや権限分離を追加しない。rootは `plan.json` / `journal/` / `pending/` のexact構成とし、実データやattemptは作らない。

```powershell
# 新しい専用rootを作る。既存rootは空でも拒否する。
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py store-init `
  --parent <既存の親directory> --name <新しい保存名> `
  --plan <入力plan.json> --plan-sha256 <外部保持したcanonical plan hash>

# 前回receiptと次recordのbytesを外部に保持してから、1件だけ追記する。
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py store-append `
  --root <metadata root> --receipt <前回receipt.json> --receipt-sha256 <そのraw hash> `
  --record <次record.json> --record-sha256 <そのraw hash>

# 保持した最新receiptを使い、保存済みmetadataを再検査する。
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py store-inspect `
  --root <metadata root> --receipt <最新receipt.json> --receipt-sha256 <そのraw hash>
```

receiptは標準出力の `anomaly-v03-checkpoint-metadata-receipt-v1`。root絶対pathと `journal.expected_plan_sha256/expected_record_count/expected_head_sha256` を含み、root外へ履歴ごと保持する。既存receiptを上書きしたり、directoryから最新headを自動推定したりしない。record入力はcanonical JSON＋LFで、既存 `make_record` の出力を使う。receiptのscopeはmetadata-only、execution_authorized/resume_authorized/campaign_completed/formal_permissionはfalse。

追記は全prefixと次recordの状態遷移・上限を検査→`pending/000001.json` 等へ排他的保存→flush/読戻し→prefix再検査→置換禁止renameで `journal/000001.json` へ確定→新receiptを返す順。renameが1件の確定点で、既存plan/recordは変更しない。旧receiptで同じ追記を繰り返すと、追加済みの末尾を検出して拒否する。

| 中断位置 | 状態と対応 |
| --- | --- |
| 初期化・record書込み途中、flush/rename前 | 部分rootやpendingをそのまま残して停止。再使用や自動cleanup・自動公開はしない |
| plan確定後、最初のreceipt受領前 | `store-recover-init --root ... --plan-sha256 ...` で、完全な空storeだけを読取り確認してreceiptを再取得 |
| record確定後、receipt受領前 | `store-recover-append` に直前receiptと同じrecordのpath/raw hashを渡す。旧prefix＋厳密に1件の一致だけを読取り確認してreceiptを再取得 |
| 意図したrecordと不一致・余分な末尾・pendingあり | 回復せず止める。途中のevaluationを継ぎ足さない |

`store-recover-append` の引数は `store-append` と同じ。回復コマンドは書込みを行わない。recordのrunning/verified等は依然として宣言で、writerがデータ処理を実行した証拠にはならない。process停止の境界を小さなfixtureで検査する段階で、実campaignの再開や受入には接続していない。

### attemptの保存先と証拠metadataを検査する

`anomaly_v03_attempt_descriptor.py` は `anomaly-v03-attempt-descriptor-v1` / scope `engineering-dev-smoke-attempt-metadata` のpure builder/validator。外部に保持したplan hash・journal件数・head hashから最後のrecordを選び、そのchunk/attempt/state、6件のidentity、source/runtime、outcomeをexactに結び付ける。新campaignの出力契約であり、metadata専用storeのexact構成にattemptや実データを混在させない。

基点はjournalの固定 `chunks/000/attempt-0001` 等。以下の相対pathを固定し、別chunk/attempt、役割の混同、絶対path、別separator、`..` を拒否する。

| 役割 | attempt基点からのpath |
| --- | --- |
| descriptor宣言 | `descriptors/<journal sequence 6桁>.json` |
| result / payload | `result` / `result/payload` |
| marker | `result/.complete` |
| producerの終了監視 | `producer-control/supervision.json` |
| 独立検算結果 | `audit/report.json` |
| 検算processの終了監視 | `audit/supervision.json` |

descriptorの `artifacts` は4役割それぞれに `{path, bytes, sha256}` または未取得を示す `null` を持つ。hashやサイズを代入したfixtureは実ファイルの証拠にならない。marker/producer監視/auditのhashはjournalと一致必須。audit監視を含むdescriptor全体はCLI引数の外部raw hashで固定する。`new_descriptor` は明示されたmetadataのみを束ね、存在しない証拠のhash/サイズを生成しない。

runningは全証拠未取得。途中失敗ではmarkerなしのproducer監視や、report/runtime取得前に終了したauditの監視だけも保持できる。verified_complete/inconclusiveの宣言には4証拠とaudit runtimeのbefore/afterが必要。audit前後の変化はblocked_integrity/runtime_changedだけで保持し、verifiedでは拒否する。producerと後日のauditのWindows build/UBRは異なってよく、それぞれの実値を保持する。

```powershell
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py attempt-layout `
  --plan <plan.json> --plan-sha256 <外部canonical plan hash> `
  --journal-dir <journal directory> --record-count <外部件数> --head-sha256 <外部head hash>

C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py attempt-validate `
  --plan <plan.json> --plan-sha256 <外部canonical plan hash> `
  --journal-dir <journal directory> --record-count <外部件数> --head-sha256 <外部head hash> `
  --descriptor <descriptor.json> --descriptor-sha256 <外部raw hash>
```

`attempt-layout` は固定pathと必要な証拠を表示する。`attempt-validate` は64KiB以下のdescriptorを読み、検証後にjournal/descriptorを再照合する。入力descriptorの実際の保存場所はこのmetadata CLIでは自由で、宣言された `descriptor_path` に存在する証明ではない。成果物のbytes/hash再計算、directory topology、sourceのclean確認、監視/検算結果本文は次の読取り処理で検証する。

成功表示は `attempt_descriptor_metadata_valid`。`artifact_bytes_verified/filesystem_containment_verified/execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false`、`campaign_evaluations_credited=0` を維持する。attempt directory、監視process、独立consumerは起動しない。全120 chunksの順序、旧試行の非流用、失敗attempt保持を維持し、実行開始前に予算、source/consumer freeze、runtime inventory、残る独立計算検算を整える。

### attemptの実ファイルを読取り照合する

`anomaly_v03_attempt_files.py` / `attempt-files` は、明示したattempt tree rootから、最後のjournal recordが指定する固定位置のdescriptorを読む。任意のdescriptor pathや別名から代用しない。metadata専用storeは従来どおり別rootに置く。

```powershell
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py attempt-files `
  --root <attempt tree root> --descriptor-sha256 <外部raw hash> `
  --plan <plan.json> --plan-sha256 <外部canonical plan hash> `
  --journal-dir <journal directory> --record-count <外部件数> --head-sha256 <外部head hash>
```

descriptorの実配置・外部hashと、宣言した各証拠のサイズ/hash・JSON objectを確認する。nullの役割に実ファイルがある場合も拒否し、新しい記録での確認を求める。祖先のreparse/symlink、通常ファイルのhardlink別名を拒否し、markerの2つの既知hardlinkだけは既存publisher契約に従う。選択attemptのdirectoryを保持して読取り後に同一性を確認する。別chunk/過去attemptへ再帰探索しない。

markerがあれば既存storage readerでpayloadのexact inventory、framing、hashを照合する。descriptor64KiB、marker/各監視1MiB、audit report8MiB、payload512 files・1 file32MiB・合計256MiBまで。これらはファイル入力上限であり、process全体のメモリ保証ではない。記録済み証拠とその不在を処理後に再確認し、CLIはjournalも再照合する。途中終了のpartial payloadはmarkerなしでは検証済みとしない。

成功表示は `attempt_files_verified`。`artifact_bytes_verified/filesystem_containment_verified=true` は選択した通常pathの読取り時点での照合を意味し、将来の不変性や敵対的な同時writerへの保証ではない。markerがあれば `payload_inventory_verified=true`。このコマンドでは `evidence_body_bindings_verified/saved_ledgers_revalidated/source_checkouts_verified=false` のまま。ファイルが一致しても計算・来歴の検証成功とは扱わない。

### 固定保存先から最初の6件を再検算する

`attempt-audit` は `attempt-files` の全検査に加え、既存の保存score以降の独立consumerを呼ぶ。**現時点ではchunk 0のverified_complete/inconclusiveだけ**を対象とする。retryのattempt番号は外部journalに従う。chunk 1以降やsmokeは既存6件用の計算契約を広げず拒否する。

```powershell
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py attempt-audit `
  --root <attempt tree root> --descriptor-sha256 <外部raw hash> `
  --plan <plan.json> --plan-sha256 <外部canonical plan hash> `
  --journal-dir <journal directory> --record-count <外部件数> --head-sha256 <外部head hash> `
  --producer-root <保存時producerのclean checkout> `
  --consumer-root <保存時auditのclean checkout> --verifier-revision <今回verifierのfull revision>
```

producerと過去consumerのrevisionはplanで固定、今回verifierのrevisionは別引数で固定する。既存 `audit_saved` のsource照合・数値検算を再利用し、manifestの6件とjournal outcome、source/runtime、producer監視、保存auditと再検算の安定項目、audit監視の正常終了・出力hash/サイズ・上限・呼出し先を照合する。descriptorのaudit runtime前後は保存auditのconsumer runtimeと一致必須。過去と今回のWindows実値を別々に保持する。処理後に全証拠、payload inventory、source、journalを再確認する。

新配置ではpublication root名は `result`、manifest/producer監視のattempt_idもその名前とする。chunk/attempt番号との対応はdescriptorの固定pathとauditの入力絶対pathで照合する。既存 `audit_anomaly_v03_saved.py` には `--supervision-path <resultの兄弟producer-control/supervision.json>` を追加した。この固定位置のみ許可し、未指定時の旧 `<result名>-control/supervision.json` は不変。新配置のaudit監視argvには、この引数を末尾へ含める。

成功表示は `attempt_saved_ledgers_verified`、`evidence_body_bindings_verified/saved_ledgers_revalidated/source_checkouts_verified=true`。scopeは保存score以降の独立検算のままで、profile/score導出の独立性や完全S6は未完了。campaign credit=0、execution/resume/campaign_completed/formal_permission=false。旧trialを新campaignの実行履歴としてコピー・再ラベル化しない。

CLI内の資源観測は既存audit部分の開始/終了検査で、監視process自体の起動機能はない。実データの読取りでは所有processの外側監視を付ける。今回の接続確認は小規模fixtureとmockを明示したテストまでで、新配置の実6件や全120 chunksの実行証拠ではない。次は登録inventoryの1 chunkを引数として扱う新scopeの結果契約を整え、旧6件契約を変更せずreader/consumerを全120へ接続する。
