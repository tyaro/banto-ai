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

CLI内の資源観測は既存audit部分の開始/終了検査で、監視process自体の起動機能はない。実データの読取りでは所有processの外側監視を付ける。この接続確認は小規模fixtureとmockを明示したテストまでで、新配置の実6件や全120 chunksの実行証拠ではない。全120区切りに対応する別scopeの結果契約と専用reader/consumerは次節を参照する。

### 全120区切りの結果形式とpayload検算API

`anomaly_v03_chunk_contract.py` は、外部campaign planとchunk index（0〜119）、attempt番号（1〜4096）を受け取る。`chunk_plan` / `new_manifest` / `validate_manifest` で、選択した登録6件だけの結果を構築・照合する。dev96区切りの後にsmoke24区切りが続き、holdoutや任意のidentity指定は許可しない。plan formatは `anomaly-v03-dev-smoke-chunk-plan-v1`、manifest formatは `anomaly-v03-dev-smoke-chunk-result-v1`、scopeは `engineering-dev-smoke-chunk`。旧engineering-devのpublic APIと形式は維持し、chunk 0でも新旧形式を相互に受け付けない。

manifest内planの `binding` は外部campaignのcanonical hash、chunk/attempt番号、role/seed/layout、6件のidentity hashを持つ。source/runtime方針もcampaignとexactに対応し、実source revisionはproducer pinと一致必須。publication名 `attempt_id` は固定 `result`。2 dataset/6 slotの順序、候補間の同一input hash、逐次処理、failure/未着手/判定保留、coverageとresource accountingを共通validatorで検査する。OS build/UBRのengineering緩和を維持し、Pythonや科学条件のpinは変えない。

旧6件の上限は `limits_status=provisional_validation_caps` として構造検証だけに適用する。新campaignの実行予算は未確定のまま。`result_trusted/execution_authorized/budgets_frozen/formal_permission=false`、`campaign_evaluations_credited=0` で、宣言検査を実行証拠にはしない。

`audit_chunk_payloads(files, producer, campaign, chunk_index, attempt)` は、保存bytesのmappingから新形式を照合し、既存の保存score以降の独立ledger検算へ6件を順に渡す。planned/context、dataset/evaluationのhash/サイズ、identity/input/event/source、profile状態、開始/終了journal、exact payload inventoryを検査する。profile/score導出そのものの独立性は追加しない。

このAPIはファイル読取りや監視processを起動しない。外部planの信頼性、入力サイズ制限、公開marker、clean source capture、consumer revision、process監視、campaign journal/descriptorとの対応は呼出側の責務。**現行 `attempt-audit` CLIは旧形式のchunk 0専用のまま**。新形式の読取りは次節の専用CLIに接続した。全120区切りの実データ実行を完了したものではない。

### 新形式の区切りを実ファイルから検算する

`anomaly_v03_chunk_audit.py` / `audit_anomaly_v03_chunk.py` は、新形式の保存済み6件を検算する。1MiB以下のplanを外部canonical hashと固定campaign仕様へ照合し、対象のchunk index/attempt番号を必須にする。publication名は `result`、producer監視は固定の兄弟 `producer-control/supervision.json`。入力は512 files・1 file32MiB・合計256MiB以内。producer revisionはplanから、今回consumer/verifier revisionは明示引数から取得し、各clean checkoutのsourceと実runtimeを確認する。

```powershell
C:\Python314\python.exe -B tools/evaluator/audit_anomaly_v03_chunk.py `
  --input-root <選択attemptのresult> --marker-sha256 <外部marker hash> `
  --supervision-sha256 <外部producer監視hash> --producer-root <clean producer checkout> `
  --consumer-revision <今回consumerのfull revision> `
  --plan <plan.json> --plan-sha256 <外部canonical plan hash> --chunk-index <0〜119> --attempt <試行番号>
```

producer監視の新formatは `anomaly-v03-chunk-supervision-v1`。policy_idは単一writer方針、scopeは `engineering-dev-smoke-chunk`、attempt_idは `result`。manifestと同じ `binding`、正常終了・worker終了確認・停止理由なし・観測エラー空、全workerの資源観測を必須にする。`runtime` と `runtime_after` の一致を確認し、試行中のWindows更新は許容しない。異なる試行や後日のaudit間では実OS値を個別に記録できる。

結果は `anomaly-v03-chunk-ledger-audit-v1` / scope `saved-dev-smoke-chunk-ledgers`。inputに絶対plan pathとbinding、result rootとmarker/監視hashを保存する。公開inventory・6件のledger・保存source・runtimeを検査し、終了前にsource、producer監視、planのbytesを再照合する。監視process自体は起動しない。内部の資源検査は開始/終了時で、旧consumerと同じ900秒/2GiBの検査上限を共用する。実データ読取り時の外側監視は別途必要で、campaign全体の予算freezeとは別。

`checkpoint_anomaly_v03.py attempt-chunk-audit` は、上記検算を外部journal/descriptorと結ぶ。引数は既存 `attempt-audit` と同じ。最後のrecordがverified_complete/verified_inconclusiveであることを要求し、固定保存先の全証拠を `attempt-files` と同じ方法で読む。旧formatへの自動fallbackや新旧の再ラベル化は行わない。

```powershell
C:\Python314\python.exe -B tools/evaluator/checkpoint_anomaly_v03.py attempt-chunk-audit `
  --root <attempt tree root> --descriptor-sha256 <外部descriptor raw hash> `
  --plan <plan.json> --plan-sha256 <外部canonical plan hash> `
  --journal-dir <journal directory> --record-count <外部件数> --head-sha256 <外部head hash> `
  --producer-root <保存時producer checkout> --consumer-root <保存時audit checkout> `
  --verifier-revision <今回verifierのfull revision>
```

保存auditと新検算は6 identities・ledger・来歴・入力・安定した結論を照合し、過去と現在のconsumer revision/runtimeは別々に記録する。audit監視は出力raw hash/サイズ・正常終了・stderr空・固定600秒/1GiB/8MiB以内の実測値と上限・専用CLIのexact argvを照合する。argvには保存時consumer/producer、plan絶対path/hash、chunk/attempt、marker/producer監視hashを含める。監視の `runtime_before/runtime_after` は保存auditのconsumer_runtimeおよびdescriptorと一致必須。読取り後にcontrol・payload・source・plan・journalを再照合する。

成功は `attempt_chunk_ledgers_verified`。evidence_body_bindings_verified/saved_ledgers_revalidated/source_checkouts_verified=true、evaluations_checked=6。budgets_frozen/execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false、campaign_evaluations_credited=0。成功したファイル照合をcontrollerの再開許可にはしない。profile/score導出の独立性は追加しない。

接続検証は小規模な実ファイルで行い、source/runtime/schema/数値処理のmockを明示する。登録dataset生成や新campaign実行の証拠にはしない。

### producer・単一writer controller・所有process監視

`anomaly_v03_chunk_producer.execute_chunk` は外部campaign/chunk/attemptとsource/runtimeを検査してから、既存の逐次producer・公開・再計算を新形式の6件へ適用する。`verify_payloads` も同じ区切り契約を先に検査する。旧固定6件のpublic APIとCLIは維持する。storeの割当てやprocess起動は呼出し側が担う。

`anomaly_v03_attempt_controller.Controller` はmetadata root、最新receipt、別のattempt tree root、producer/consumer root、verifier revisionを明示して構築する。verified履歴があれば、各verified sequenceをkeyとする外部保持のdescriptor raw hash map `descriptor_pins` も必須。保存treeから信頼するpinを自動採取しない。

通常は `run_next(observed, produce=..., inspect_audit=...)` が、最初の未完了chunkの新attemptを排他的に確保し、running→producer保存→saved_pending_verification→独立audit→fresh照合→verifiedの順で進める。callbackは同期で、所有workerの終了を確認してから戻る必要がある。controller自身はprocessを起動しない。分割呼出しは `start` / `producer_saved` / `finish` / `fail`。戻り値のreceiptとdescriptor pinsをroot外で保持する。再起動後は過去のverified証拠を再照合してから次へ進み、同じcontroller session内で検証済みの区切りは繰り返し再計算しない。

各遷移は `controller/<sequence 6桁>/intent.json` と固定位置のdescriptorを先に排他的保存し、実証拠照合、journal追記、同じstepの `receipt.json` 保存へ進む。失敗attemptと部分出力は保持し、正常に記録できたfailed/interruptedからは別attemptへ進む。runtimeや証拠の不整合は停止する。失敗記録自体の保存エラーも元の停止例外を隠さず、可能な範囲で `last_stop` / `failure-recording.json` に残す。

intent保存後の処理が完了しなければ `TransitionIncomplete`。journal確定後にreceiptだけ失った場合は `recover_committed_transition` に外部保存のintent path/raw hashを渡し、意図した1件が確定済みで実証拠も一致する場合だけreceiptを読取り回復する。未確定intentを公開・上書き・再利用しない。照合で拒否されたverified intentも自動的に失敗recordへ置き換えず、そのまま調査対象にする。

`anomaly_v03_process_supervisor.supervise` は、明示argv/cwd、新しいcontrol directory、wall/private/output上限で**所有するWindows子process 1個**を監視する。stdout/stderr合計を監視し、上限・中断・観測失敗時は停止と終了確認を試みる。終了後のhash読取りも上限内に限定する。終了を確認できない場合はログを走査せず、`UnreapedWorker.process` に元の所有handleを保持して返す。子孫processの管理はこのAPIの範囲外。実行権限、sourceの選定、全体予算は呼出し側で確定する。

監視はgeneric観測reportを返すだけで、producer/audit専用の `supervision.json` は保存しない。下記adapterが専用formatへ結び付けて保存する。component単体試験は小規模fixtureとprintのみの実子processに限定し、campaign加算0、formal_permission=falseを維持する。

### 新しい6評価を別processの監査まで通す

`anomaly_v03_chunk_execution.NativeCallbacks` は、controllerの固定保存先でproducer worker→保存確定→別processのaudit CLI→fresh照合→journal確定を順次実行する。producer/consumerはplanで固定したclean checkoutを検査する。fresh検証を行うcontroller自身はconsumerと同じcheckout/revisionで起動する。各監視を `producer-control/supervision.json` / `audit/supervision.json` へ排他的保存し、停止理由を保存障害で置き換えない。終了未確認workerがあればjournalを失敗・再試行可能へ進めず、元のownerを保持する。

```powershell
C:\Python314\python.exe -B tools/evaluator/run_anomaly_v03_chunk.py trial `
  --root <このentrypointを置いたclean checkoutの絶対path> `
  --expected-head <固定した40桁revision> --name <未使用の試行名>
```

`trial` は接続確認専用で、常に新しい `artifacts/anomaly-v03-chunk-trials/<name>` と最初のdev chunk/attempt 1だけを作る。実行前にplan hash・revision・対象数1区切り・上限・実runtimeを `request.json` に固定する。metadata/attempt/外部receipt保存先を分け、running/saved/verifiedの戻り値を順番に `receipts/` へ保存する。既存試行の再開や全120区切りの起動はできない。producerとconsumerは同じ固定revisionでも別process・別計算経路で、検算の範囲は保存score以降のledger。

実行前に登録dataset/evaluationのstage/payload保存先を組み立て、UTF-16で248文字未満を要求する。Windowsの長いpath設定は変更せず、上限を超えるcheckout/試行名は計算前に拒否する。短いcheckout名を使う。初回実試行で261文字のC2出力が保存できなかったため追加した境界で、途中失敗の出力はそのまま保持する。

producerは900秒/2GiB、payloadは書込み前の既存1GiB上限、stdout/stderrは合計1MiB。auditは600秒/1GiB/ログ8MiB。controller内のfresh ledger検証は既存readerの開始・終了資源検査で、controller自体を強制停止する外側process上限や全campaign予算はまだ設けていない。開始時は空きRAM4GiB・volume20GiBを要求する。trial成功は `connection_trial_verified` / `verified_evaluations=6` で、campaign加算0・正式許可false。全dev/smoke予算、完全runtime inventory、profile/score導出等の独立検算と正式受入は別途残る。

source照合では同期の読取り用Git subprocessを呼ぶ。専用の計算workerを増やすことはないが、監視のprivate bytesは直接所有するPython processの値であり、Gitを含むprocess tree全体の合計ではない。

終了不明時のCLIは新しい仕事を始めず、元の子processに停止・終了確認を繰り返す。ログを繰り返し走査したり、PIDから別processを探したりしない。途中出力/intent/監視を残し、自動cleanupは行わない。

### 閉鎖記録からの予算付き継続API（2026-09-21）

`anomaly_v03_budgeted_run.py` は新規run専用の `prepare` / `Run` を提供する。固定planや旧trialへ予算を後付けせず、別requestへ48時間/32GiBの候補上限を記録する。全体CLI・全120区間の実行・完全runtime inventory・予算の最終確定は未完了。詳しい適用範囲は[結果記録](results/anomaly-multiseed-v0.3-budgeted-run-2026-09-21.md)を参照する。

`prepare(parent, name, plan, observed)` は全120の保存pathを先に検査し、新しいmetadata/attempts/controlと初期closed記録を作る。返されたrequestとstateのpath/hashを外部に保持する。`Run(root, request_hash, state_path, state_hash, producer_root, consumer_root, verifier_revision)` はこの外部pin、全closed履歴、receipt、descriptor hash mapを照合する。`run(observed, max_chunks=...)` は既存native callbacksを逐次呼び、新しいclosed state pinを返す。エラー時に安全なclosed記録を保存できた場合は `last_closed` にそのpinを保持する。

累積時間は各 `run` 呼出しの活動時間を加算する。準備、休止、最終closed書込みは対象外。残り2460秒または出力1GiB＋32MiBの余裕がない場合に次区間を開始しない。controller private2GiB/空きRAM4GiB/空きdisk20GiBを境界で確認し、所有workerの個別監視は維持する。全体の時間/容量上限やcontroller/process treeを強制停止する仕組みではない。再開時の過去verified証拠の再照合中にはwrapperの途中検査は入らない。

`control/NNNNNN/stop.request` を区間の境界で読み、新規control番号にclosed記録を残す。古いclosed状態、未閉鎖呼出し、未確定transitionを自動再使用しない。未終了workerは出力walk/closed書込みをせず元の `UnreapedWorker` を返し、呼出元によるowner保持・終了確認を必要とする。旧trialのcoverage転用、campaign加算、正式gate変更は行わない。

### engineeringの実行環境snapshotと起動CLI（2026-09-21）

`anomaly_v03_engineering_inventory.py` はWindows更新の実値を記録する別formatで、source/stdlib/loaded native/extension/CPU/起動条件を収集・再読する。従来正式collector/schema/pinは不変。snapshotはinspection processの時点観測で、worker/auditorのwarmupやruntime closureではない。`full_runtime_inventory_complete=false`を維持する。

`tools/evaluator/run_anomaly_v03_campaign.py prepare --root <clean checkout> --expected-head <full SHA> --name <new name>` は、短いpathの新規rootにsnapshotと固定plan/空journal/初期closed記録を作る。所有inspection processは300秒/private512MiB/log16MiB。stdoutへ返すpreparedとclosedのpath/raw hashを外部保持する。実データ計算は行わない。

`continue` は同じroot/revision/nameと、`--prepared-sha256`、`--state-path`、`--state-sha256`、**明示した`--max-chunks`（1〜120）**を必須にする。外部pinを照合し、Run.run活動時間内で新しいinspectionと基本runtime一致を確認してから既存NativeCallbacksへ接続する。終了不明のownerは元handleで保持し、終了確認まで新しい仕事へ進まない。固定source選定は同一revisionをproducer/consumer/controllerに使うengineering構成である。

実prepareはc01d1c9/clean `v03p/banto-ai` の`r1`で成功した。source397/stdlib2559/native48/extension8、7 files/749075 bytes、journal0/next chunk0。完全runtime inventory、受入freeze、全120実行、独立S6の完了は追加しない。[結果と操作手順](results/anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)を参照する。

初回は同じc01d1c9/r1で実CLI `continue --max-chunks 3` が3区間/18評価を2563.527秒で完走した。journal9/next chunk3/yielded、監査は各区間`ledger_checks_passed`、全所有process正常終了確認済み。当時のclosedは`run/control/000001/closed.json`、205 files/399625685 logical bytesを照合し、初期7ファイルは不変。[3区間の最終結果](results/anomaly-multiseed-v0.3-three-chunk-run-2026-09-21.md)はこの初回保存時点の記録である。campaign加算0/正式許可false、独立監査は保存score以降のみである。

さらに2026-09-22 JST、実CLI `continue --max-chunks 6` でchunk3〜8/36評価が成功し、累計9区間/54評価となった。その保存時点のclosedは **`run/control/000002/closed.json`**、journal27/next chunk9/yielded。595 files/1196786729 logical bytesを照合し、既存205ファイルは不変。[6区間の最終結果](results/anomaly-multiseed-v0.3-six-chunk-continuation-2026-09-21.md)の外部pinを使う。短い区間数での再開を繰り返すと既存verified再照合の費用が累積するため、次の区間上限候補を24とし、途中保存は同じinvocation内で続ける。試算は保証ではなく、次回以降の実行や全体予算の正式freezeは追加していない。

### 24区間継続の完了記録（2026-09-22 JST）

同じclean c01d1c9/r1で`continue --max-chunks 24`がchunk9〜32/144評価をすべて成功で完了し、累計33区間/198評価となった。20851.249秒（約5時間48分）、累積活動28855.997764秒、journal99/next33/yielded、全所有process終了済み。2137 files/4384532669 logical bytesを照合し、既存595ファイルは不変。終了後はIO/hash照合のみで、数値再計算は行っていない。

当時のclosedは **`run/control/000003/closed.json`** / raw SHA-256 **af04684d25c99f69e64a2ac5aacffd92be930d6325ceddd5d9a0ee254f5fa7a0**。[区間9〜32の結果](results/anomaly-multiseed-v0.3-twenty-four-chunk-continuation-2026-09-22.md)とそのsavepoint-evidenceに保持する。この節は累計33区間時点の履歴で、最新の再開pinは末尾の完了記録を使う。

### 区間33〜56継続の完了記録（2026-09-22 JST）

同じclean c01d1c9/r1の`continue --max-chunks 24`でchunk33〜56の新規144評価がすべて成功し、累計57区間/342評価となった。27346.369秒（約7時間36分）、累積活動56201.874418秒、journal171/next57/yielded。各監査は`ledger_checks_passed`、controllerと全所有process終了済み。3679 files/7572651569 logical bytesを照合し、開始前2137ファイルはすべて不変。終了後のcollectorは553.670秒のIO/hash照合のみで、数値計算は繰り返していない。

当時のclosedは **`run/control/000004/closed.json`** / raw SHA-256 **f21ca40084af17fc0d961c529963c984ccd80d2b0cfea7803fab30c1ce7382a6**。[区間33〜56の結果](results/anomaly-multiseed-v0.3-chunks-33-56-continuation-2026-09-22.md)とそのsavepoint-evidenceに保持する。この節は累計57区間時点の履歴で、最新の再開pinは次節000005を使う。

### 区間57〜80継続の完了記録（2026-09-23 JST）

同じclean c01d1c9/r1の`continue --max-chunks 24`でchunk57〜80の新規144評価がすべて成功し、累計81区間/486評価となった。30205.374秒（約8時間23分）、累積活動86406.475041秒、journal243/next81/yielded。各監査は`ledger_checks_passed`、controllerと全所有process終了済み。5221 files/10761163678 logical bytesを照合し、開始前3679ファイルはすべて不変。終了後のcollectorは522.586秒のIO/hash照合のみで、数値計算は繰り返していない。

その成功保存時点のclosedは **`run/control/000005/closed.json`** / raw SHA-256 **a6b8fd6160b496d9a7dea83cef3ec22814c8b12676df273eb591fb5368384758**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。旧000004以前のclosedや中間receiptは再開pinに使わない。 [今回の最終結果](results/anomaly-multiseed-v0.3-chunks-57-80-continuation-2026-09-22.md)と候補`artifacts/chunks-57-80-continuation-2026-09-22/savepoint-evidence.json`へ保存する。残り39区間/234評価、48時間候補予算の残り活動時間86393.524959秒（約24.00時間）。次回は完了済み81区間の再照合費用も含めて明示上限を判断する。今回のheartbeat banto-24は最終保存後に停止し、追加invocationは起動しない。 監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory、profile/score導出・bootstrapの独立検算、全dev/smoke/holdout、性能評価、Phase 2/3全体は未完了。

### 区間81〜104呼出しの異常終了（2026-09-23 JST）

区間81〜104を対象に起動したcontrol000006は、既存区間の再照合中とみられる段階でMemoryErrorによりexit2で終了した。新規区間の開始記録・確定は0、journal243/前回checkpointと完全一致。累計81区間/486評価、残り39区間/234評価を維持する。今回の24区間成功は追加しない。

失敗時の最新closedは **`run/control/000006/closed.json`** / raw SHA-256 **18af12a119e3acc0600594d8eaf6263607f5f7c85d68ff3acbda31931d4b9e4c**、status=failed/stop_reason=exception。直前000005は開始pinとして保持し、現在の再開pinとして使い回さない。 [停止記録](results/anomaly-multiseed-v0.3-chunks-81-104-continuation-2026-09-23.md)。次の判断点はMemoryError原因の切り分けと再開条件の見直し。今回のheartbeat banto-24はPAUSEDに変更済み。追加区間や同じinvocationを自動再起動しない。 campaign加算0/正式許可false、監査は保存score以降のみ。Phase 2/3、完全runtime inventory/独立S6、全120/holdout/性能評価は未完了。実装変更・追加agent・push/merge/CI・OS/権限設定変更なし。
