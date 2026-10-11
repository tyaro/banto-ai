# v0.3 dev layout1 C1 core実評価 — 2026-10-11

## 入力と実計算

保存済み合成dev seed2486912926863618161 / layout1 / coreを既存CLI c1-phase-level で1cell実compute_evaluationした。同chunk001 manifest10input pins→新input snapshot→fresh fit/calibration→原profiles/scores/source・equipment episodes/events/incidents/metricsを保存した。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agent・holdout観測読取りは各0。同じseedの別layoutであり新しい独立seedではない。

~~~text
C:/Python314/python.exe tools/evaluator/run_representative_anomaly.py
  --input-manifest C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/001/attempt-0001/result/payload/manifest.json
  --manifest-sha256 72e5a34c662f77c4728583b9e61cc9d2977edd2ecc9e5286194aae0d2c055dbf
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-01-core
  --candidate c1-phase-level
  --output artifacts/representative-anomaly-evaluation/dev-layout1-core-c1-20261011-input-pin-correction
~~~

元manifest75699B、actual checkout文書HEAD d2ba11da7e286a361bda867bc63644d6ad7509ea、production/test計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actual CPython3.14.0 / Windows / AMD64。elapsed34.645599599927664秒、OS checkpoint peak private147738624B。48profile calibrated / fit_samples各600 / calibration_samples各290。14400score、利用可能13920・不能480。不能は全mode_recipe_or_phaseで、原score/residual=null・threshold_exceeded=false。

CLI exit0 / complete / 1cell successは処理完了。今回の合成dev結果を正式性能合格・勝者・採択へしない。bootstrap・統計CI推定・formal creditは0。

## 原結果と同条件C0比較

| 同layout1/core候補 | 機械 | sensor | precision | clean誤警報 | 全未対応equipment | 利用可能score |
|---|---:|---:|---:|---:|---:|---:|
| c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920/14400 |
| c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/14400 |

C1は30source episodes / 20equipment episodes / 20incidents / 40events。原20incidentすべてcausal_detected、各candidate_count1、対象source onsetとsupportに対応するmatched episodeを保存。検出遅延20件はすべて原1.0秒、中央値・平均・min・max各1.0秒。未検出0であり、未検出delayの補完は行っていない。clean_rate原0/3365/value0.0、effective_clean_seconds3255/effective_clean_rate0.0、false_alert_burden原0/20/value0.0。原rateと分母を保持する。

同layout1のC0と10input pins・宣言16calculator sources・candidate config・compiled configが一致。候補選択だけC0→C1。設定に固定されたC0 threshold4.0、C1 threshold6.0、persistence2、first-equipment-onset-no-retry-v1を変更していない。前回C0・旧layout0のモデルは再compute0。

旧layout0 C1保存manifestは機械10/10・sensor10/10・precision20/20・clean0、検出delay中央値1.5秒・平均1.5秒。今回layout1の全delay1秒との差を保存summaryだけで比較した。入力layoutが異なり、同seed2layoutを2独立seedへしない。

## cycle00の原対応

machineのmotor-01.motor_currentはsample7237/7238連続超過でstreak1→2、7238で対象source episode成立。選択equipmentはcurrentとvibrationのsourceを含み、対象currentの原selected_source_episode_id・support_score_ids2件・matched_episode_id・causal_detected=true・delay1秒が対応する。C0で観測したvibration-only first candidateの結果を変更して補ったものではない。

sensorのmotor-01.motor_temperatureはsample7244/7245連続超過でstreak1→2、7245で対象source episode成立、原matched episode・support2件・causal_detected=true・delay1秒に対応する。

| cycle00対象 | sample | score | streak |
|---|---:|---:|---:|
| motor-01.motor_current | 7237 | 35.70714299208755 | 1 |
| motor-01.motor_current | 7238 | 35.137715849328224 | 2 |
| motor-01.motor_temperature | 7244 | 178.8190609788078 | 1 |
| motor-01.motor_temperature | 7245 | 179.51564700885191 | 2 |

全20event/incident原ledger、全30source/20equipment episodes、cycle00 machine/sensor対象windowと原selected source/equipment/supportをmetadataへ保存。入力対応・原result保存・状態分類の実CLI経路不具合は観測しなかった。以下の補助script失敗は別に保全する。

## 失敗とmetadata容量の保全

初回補助scriptのc0→c1文字列置換がSHA256内のc0にも作用し、宣言pin末尾がd2c055dbfからd2c155dbfへ変わった。既存CLIはIntegrityError / manifest SHA256 mismatchで入力照合拒否。初回run dev-layout1-core-c1-20261011 はfailed / successful_cells0 / cells[]で保存し、実compute開始0、指標集計へ混ぜない。原helperのAssertionError/failed、stdout/stderr/summary/live/executionを保持した。原scriptを再実行せず、候補・出力・metadata名だけを明示置換し元SHA256文字列を完全一致確認した別script・新IDで、今回1cellの実計算を行った。入力pin拒否を数値モデル失敗や成功へ読み替えない。

解析helperは原source episodeに存在しないonset_sampleを参照してKeyError / failed、metadata書込みとdata閉鎖前。原script/live/execution/first errorを保持。別metadata-only continuationで原incident.selected_source_episode_idにより原source episodeを抽出し、未完了metadata/data閉鎖だけ完成。原時刻fieldはonset_msのまま、モデル再計算0。foreground Python -c のPowerShell quote構成SyntaxErrorと依存する未存在script起動もselected tool traceへ保存した。両はinstrumented helper/source評価前、model/tracked mutation0、full creation/全stdio未保存None。

MAIN artifacts/representative-layout1-core-c1-20261011-prep は失敗証拠・script増加で35file / 226520B、metadata entry cap32を3超過した。容量成功とはしない。byte/single-file capは超えていない。上限変更・raw削除・移動は0。その35fileを別rootのmain-frozen-manifest.jsonへ全pin固定し、MAIN追記を停止した。MAIN内部root-closed.jsonは未発行。以降は独立metadata continuation rootで事前entry/byteチェックを行う。この件数管理不足を保存上限が全経路で守られた証拠へしない。

元83helper原7failed76passedに、今回の入力拒否/評価/解析/metadata continuation4helperを加え、87helper原9failed78passed。全full saved creation/start_tokenのlive/execution一致・CIM同original不在・repo helper-critical ownerなし。foreground文書/closureのfull creation/stdioはNone。selectedCLIrawはhelper全stdioではない。新モデル実計算1cell、入力拒否run0cell、旧モデル/replay/CI/native反復0。

## pinsと閉鎖保存

| 保存対象 | bytes | SHA256 |
|---|---:|---|
| observations.jsonl | 9600599 | 8ba28a7442dc82650050d494c8c3788af02b7be7c6d70df292be1528107ec428 |
| configuration.json | 5502 | 3b28cd9320104cc3727aad8adb4784e38221e4fc1c27ddbe1624dafceefb0c82 |
| manifest.json | 8024 | f1b3ebc59a9a4c0c762a1b1a6ead0bfdb2b8df1fac5d8e4731da9df68c0e2acd |
| evaluation-0.json | 14071971 | b669f90b9da5d103c85636b802faae6d2f2d7eceb44a4595dfcb59d197f68dc4 |
| numerical | 14066473 | 882ae14037ffb9a7e6bf861b6634cd004a228b30b3358786a16c4db9c0f407f6 |

完成data root 19file/27112678B/root-closed2235B/a3de22f0107407c4d37994bc555c3c55b42eb492e6bebf45ad37f4198a74a060。初回failed data root 3file/951B/root-closed401B/b5489524b06bbbaee496fbab2966274dbc90be0f17d501ed520a3426f9bcfeab。閉鎖済みdataへ追加・再実行0。MAINは上記外部manifestの固定prefixを優先し、内部閉鎖成功と呼ばない。metadata continuation artifacts/representative-layout1-core-c1-metadata-continuation-20261011-prep とPOST artifacts/representative-layout1-core-c1-post-20261011-prep のpost-save/owners/root-closedを最終Git保存状態として優先する。117science-source・旧24root count-byte-closure pinは不変。

## Git承認と次工程

人のリスク通知後の「承認します」は、評価結果とユーザー名を含むPC内入力pathを同送信先 https://github.com/tyaro/banto-ai.git へ今回及び今後同種の合成dev報告として送信する承認を含む。今回reportとcurrent-handoffの2文書を同継続承認範囲で一回[skip ci] commit/pushする。先行自動審査拒否2回・元helper未起動は歴史のまま保持。実Git返値と最新headはPOSTを優先する。

次は同chunk001manifest72e5pin / 同dev seed2486912926863618161 / layout1 / coreをC2 c2-phase-conditionalで新ID/1cell実評価し、同条件3候補比較を完成する。今回C1/C0、完成layout0全6cell、replay、旧risk tests、CI381385/4130、native/probe/collector/Git37を再実行・再照会しない。旧381365/a54961最後in_progressは履歴保持、doc-only CI追跡0、追加agent0。

formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / holdout観測未読 / 正式5残件・最終受入未完了。create_native早期拒否・全7役whole.run reader起動禁止・元caps/unknown原owner-stop維持。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpointはblocking中断/full loaded runtime閉包/allwriter-global-native容量証明ではない。未完了formal/native全証明を少量dev評価開始の新条件に戻さない。ACTIVE継続、Sol容量又は人の停止時は保全後PAUSED・重複再試行なし。
