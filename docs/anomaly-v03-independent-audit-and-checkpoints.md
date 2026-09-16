# 保存結果の独立検算と長時間実行の進行記録

2026-09-16。単一writerの運用改訂を継続する。独立ledger検算は実装済み、全dev/smokeを動かすcampaign controllerは**設計段階・実行未許可**。
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

## 全dev/smokeの進行記録設計

目的は約19時間の処理を、検証済みの単位を残して中断・再開できるようにすること。同じ出力先の単一writerを前提とし、専用principal試験や権限分離の追加試験は再開しない。
新campaign scope/manifestは実装時に別IDで固定し、既存6件用CLIの対象や上限を可変化して代用しない。

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

まずplan builder/validatorとjournalの状態導出を、データ生成なしのfixtureで実装する。切断されたjournal、重複chunk、順序違反、source差分、markerだけの偽完了を検証する。
その後、保存済み6件を読取り専用で参照して検証済みchunkの照合を接続する。既存計算結果を上書き・再生成しない。
consumerのprofile/score導出とruntime inventoryの残件を整え、新scopeのproducer/consumer revisionを固定する。
長時間実行の開始前に、controller・consumerも含む容量/所要時間、1 chunkとcampaign全体の上限、途中停止の境界を確定する。前回概算14.8GiB/19.1時間はbootstrap・独立consumer等を含まず、正式容量保証に使わない。
全dev/smokeの実行開始、上限拡大、holdout実行は今回の設計や部分検算だけでは行わない。
