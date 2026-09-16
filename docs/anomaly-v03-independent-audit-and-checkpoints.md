# 保存結果の独立検算と長時間実行の進行記録

2026-09-16。単一writerの運用改訂を継続する。独立ledger検算、固定plan・journalのmetadata検査/状態復元、旧6件trialとのpreflight証拠照合は実装済み。全dev/smokeを動かすcampaign controllerは**未接続・実行未許可**。
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

plan builder/validatorとjournalの状態導出を、データ生成なしのfixtureで実装した。切断されたjournal、重複chunk、順序違反、source差分、markerだけの偽完了を拒否する。保存済み6件を読取り専用で参照する証拠照合も接続した。次は、追記writerと新scopeのattempt出力契約を整える。既存計算結果を上書き・再生成せず、旧trialを新campaign coverageへ流用しない。
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

読み取りではplan 1MiB/record 16KiB/journal合計16MiB/最大4096 recordsを検査し、番号付きファイル以外・途中JSON・非canonical record・読み取り中の変更を拒否する。これはmetadata file上限であり、process全体の資源監視は未接続。一般のsingle-writer保存APIを使う追記writerも次工程。CLIは独自にmarkerや完了印を作らない。

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
