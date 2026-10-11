# v0.3 dev layout1 C2 core実評価と3候補比較 — 2026-10-11

## 入力と実計算

同保存合成dev seed2486912926863618161 / layout1 / coreを既存CLI c2-phase-conditional で新ID/1cell実compute_evaluationした。同chunk001 manifest10input pins→新snapshot→fresh fit/calibration→原profiles/scores/source・equipment episodes/events/incidents/metricsを保存した。入力の生成時candidate identityと今回の実評価candidateを別fieldで保持している。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agent・holdout観測読取りは各0。

~~~text
C:/Python314/python.exe tools/evaluator/run_representative_anomaly.py
  --input-manifest C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/001/attempt-0001/result/payload/manifest.json
  --manifest-sha256 72e5a34c662f77c4728583b9e61cc9d2977edd2ecc9e5286194aae0d2c055dbf
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-01-core
  --candidate c2-phase-conditional
  --output artifacts/representative-anomaly-evaluation/dev-layout1-core-c2-20261011
~~~

元manifest75699B。actual文書checkout HEAD390d77e7d8910a0784b6e556147c737153e39558、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actual CPython3.14.0 / Windows / AMD64、elapsed35.68787640007213秒、OS checkpoint peak private205942784B。48profile calibrated / fit_samples各600 / calibration_samples各290。14400score、利用可能13920・不能480、不能は全mode_recipe_or_phase。原不能score/residual=null・threshold_exceeded=false。

CLI exit0 / complete / 1cell successは処理完了であり、正式性能合格・勝者・採択へしない。bootstrap・統計CI推定・正式creditは0。

## 同じ入力での3候補比較

| 同seed/layout1/core候補 | 機械 | sensor | precision | clean誤警報 | 未対応equipment | 利用可能score | 検出delay中央値 |
|---|---:|---:|---:|---:|---:|---:|---:|
| c0-diff-control | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920/14400 | null (count0) |
| c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/14400 | 1.0秒 |
| c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 0 | 13920/14400 | 1.0秒 |

C2の原結果は40source episodes / 20equipment episodes / 20incidents / 40events。20incidentすべてcausal_detected、各candidate_count1、対象sourceと原support2件がmatched equipment episodeに含まれる。検出delay20件は全原1.0秒、中央値・平均・min・max各1.0秒。未検出0、delay補完0。clean_rate原0/3365/value0.0、effective_clean_seconds3255/effective_clean_rate0.0、false_alert_burden原0/20/value0.0。原rateと分母を保持する。

今回C2は同layout1 C0/C1と全10input pins、宣言16calculator sources、候補config・compiled config一致。保存済みC0/C1のモデル再compute0。固定C0threshold4.0/C1・C2threshold6.0、persistence2、first-equipment-onset-no-retry-v1、GTと科学式を変更していない。C2は同一入力でC1と同じ集計指標だったが、source episodesはC1の30に対して40。集計値の一致を原scoreやepisodeの同一性へ読み替えない。

この3候補比較は合成dev1seed/layout1/coreの同条件比較であり、3独立データや新独立seedではない。正式採択・勝者・統計CIの推定を行っていない。

## cycle00の原target onset

cycle00 machineのmotor-01.motor_currentは7237/7238連続超過でstreak1→2、対象source onset7238。selected equipmentには対象current sourceが含まれ、原selected_source_episode_id / support_score_ids2件 / matched_episode_id / causal_detected=true / delay1秒が対応する。

cycle00 sensorのmotor-01.motor_temperatureは7244/7245連続超過でstreak1→2、対象source onset7245。原target source、support2件、matched equipment、causal_detected=true、delay1秒が対応する。全20incidentも対象full_target一致・source onset=event start+1000ms・原support一致を確認した。

| cycle00対象 | sample | C2 score | streak |
|---|---:|---:|---:|
| motor-01.motor_current | 7237 | 35.23134934195178 | 1 |
| motor-01.motor_current | 7238 | 34.61680153186398 | 2 |
| motor-01.motor_temperature | 7244 | 163.57245139513384 | 1 |
| motor-01.motor_temperature | 7245 | 164.14782615474064 | 2 |

全20原event/incident ledgerとcycle00 machine/sensor selected equipment/source、target/vibration window score・residual・streakを新extract rootへ保存した。原score/episodeの対応を確認した範囲で、入力対応・保存・状態分類の実CLI経路不具合は観測しなかった。

## 旧layout0 C2保存指標との比較

同seedの旧layout0 C2保存manifestは機械4/10・sensor10/10・precision14/20・clean誤警報0・未対応equipment6。検出14件delay中央値1.0秒・平均1.2857142857142858秒、未検出6件delaynull。

今回はlayout1で機械10/10・sensor10/10となった。旧layout0は保存manifestの指標と同設定/source pinだけを参照し、旧raw model再compute0・旧未検出の再matching0。入力layout差を保持し、旧6未検出を新結果で成功へ書き換えない。旧layout0 C2のvibration-only first candidate結果と、今回の対象current source onsetを別source/input/runの原結果として保持する。同seed2layoutを2独立seedへしない。

## 原pinsと保全

| 保存対象 | bytes | SHA256 |
|---|---:|---|
| observations.jsonl | 9600599 | 8ba28a7442dc82650050d494c8c3788af02b7be7c6d70df292be1528107ec428 |
| configuration.json | 5508 | 01ac864fb301cedde3ea634f0dae996a8d6345018af8ccb7f802b07bd7bc72c7 |
| manifest.json | 8008 | 8005819bdc77823a6caddfb96dc33c49a6487186eaa69d4b48f5b37f020dde97 |
| evaluation-0.json | 24750341 | 9d78f4e57f199291b2c1dffcc98d58647e90c68f5ff21f50c735e8630d0a7515 |
| numerical | 24744843 | 6fb9aaf74da973fcbac17c6a5d042cbc44962f20fa910e38a4402facbb618bd2 |

新data root閉鎖19file/37791014B/root-closed2235B/1292bff382cb849efcece7c46260d55f60b4f9c671c1f9144355095cbb298aa2。新extract root artifacts/representative-layout1-core-c2-extract-20261011-prep 閉鎖3file/51074B/root-closed565B/4daa9936469110286170e0edd6f29dee03b083dbc68f7f17814e7c0332f70a09。MAIN artifacts/representative-layout1-core-c2-20261011-prep、POST artifacts/representative-layout1-core-c2-post-20261011-prep のpost-save/owners/root-closedを最終Git保存状態として優先する。

117science-source・旧29内部閉鎖rootのcount-byte-closure pinと、前回C1 MAIN外部固定35file226520Bが不変。前回C1の初回pin拒否/解析KeyError/foreground tool errors/metadata32entry超過3件は原failed/capacity-success=falseのまま保持し、再実行・削除・移動・内部root-closed作成0。今回metadataは新書込み前にscript・終端/失敗・閉鎖分を含むentry/bytesを確認し、原抽出を別rootの64KiB以下partへ保存した。512KiB32entry/reserve128KiB/single128KiBを維持し、capを緩和しない。

元88helper原9failed79passedに今回の評価/解析2passedを加え90helper原9failed81passed。full saved creation/start_tokenのlive/execution一致・CIM同original不在・repo helper-critical ownerなし。原failedを今回successへしない。foreground準備・文書・closureはfull creation/全stdioNone。selectedCLI rawはhelper全process stdout-stderrではない。CIM decimal100ns→microsecond trunc/full token一致、PID単独判定/native回収claim0。

人のリスク通知後「承認します」は、今後も同GitHub送信先 https://github.com/tyaro/banto-ai.git へ同種の合成dev結果とユーザー名を含むPC内入力path報告を送信する承認を含む。今回report/current-handoffの2文書を同継続承認範囲で一回[skip ci] commit/pushする。先行審査拒否/元helper未起動は歴史保全、Git原返値と新headはPOSTを優先。詳細payloadのautomation設定保存拒否は前回保全済みで、heartbeatは詳細結果/PC内入力pathを含めない短い文書参照指示のACTIVEを維持し、今回同詳細payloadの再送・automation更新0。

## 次工程と正式gate

同layout1/coreのC0/C1/C2比較は保存済みで完成。次は同chunk001 manifest72e5pin / 同seed2486912926863618161 / layout1の保存済みquality-stressをC1 c1-phase-levelで新ID/1cell実評価する。次dataset anomaly-v03-dev-seed-2486912926863618161-layout-01-quality-stress、次output dev-layout1-quality-c1-20261011。次入力identity/file pinsは既存選択metadataのみから確認し、quality観測本文・新モデルは今回未読/未開始。元payload保持・新生成0・1cellずつ比較する。

完成layout1/core3cell・layout0全6cell・replay・旧risk tests・CI381385/4130・native/probe/collector/Git37を再実行・再照会しない。旧381365/a54961最後in_progressは履歴保持、doc-only CI追跡0、追加agent0。

formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / holdout観測未読 / 正式5残件・最終受入未完了。create_native早期拒否・全7役whole.run reader起動禁止・元caps/unknown原owner-stop維持。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpointはblocking中断/full loaded runtime閉包/allwriter-global-native容量証明ではない。未完了formal/native全証明を少量dev評価開始の新条件に戻さない。ACTIVE継続、Sol容量又は人の停止時は保全後PAUSED・重複再試行なし。
