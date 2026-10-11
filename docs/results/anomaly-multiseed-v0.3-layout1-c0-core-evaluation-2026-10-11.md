# v0.3 dev layout1 C0 core実評価 — 2026-10-11

## 入力と実行

保存済み合成dev seed2486912926863618161 / layout1 / coreを既存CLIの c0-diff-control で1件実compute_evaluationした。前回と同じseedの別layoutであり、新しい独立seedではない。元manifest10input pins→新snapshot→fresh fit/calibration→原profiles/scores/source・equipment episodes/events/incidents/metricsを保存した。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agentは各0。

~~~text
C:/Python314/python.exe tools/evaluator/run_representative_anomaly.py
  --input-manifest C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/001/attempt-0001/result/payload/manifest.json
  --manifest-sha256 72e5a34c662f77c4728583b9e61cc9d2977edd2ecc9e5286194aae0d2c055dbf
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-01-core
  --candidate c0-diff-control
  --output artifacts/representative-anomaly-evaluation/dev-layout1-core-c0-20261011
~~~

元manifest75699B。実checkout文書HEAD bfe07a2566fa56c7534262c2161b21383dd333b8、production/test計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actual CPython3.14.0 / Windows / AMD64、elapsed17.74478760000784秒、OS checkpoint peak private145911808B。48profile calibrated、保存fit_samples各0（C0 controlの原値）、calibration_samples各290。14400scoreの利用可能13920、不能480は全 mode_recipe_or_phase。原不能score/residual null・threshold_exceeded=false。処理successを性能合格・採択へしない。

## 原結果と保存済みlayout0比較

CLI exit0 / run complete / 1cell success。機械0/10・sensor0/10、precision0/3、clean誤警報2。3source episodes / 3equipment episodes / 20incidents / 40events。全20未検出delayは原null、検出delay count0、中央値・平均・最小・最大null。bootstrap・統計CI・勝者・正式採択は0。

| core条件 | C0機械検出 | sensor検出 | precision | clean誤警報 | 全未対応equipment | 利用可能score |
|---|---:|---:|---:|---:|---:|---:|
| layout0 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/14400 |
| layout1 | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920/14400 |

旧layout0 C0は保存manifest指標だけ参照し再compute0。宣言16calculator sources・candidate config・compiled candidate config一致を確認。入力はlayout差で異なる。同seedの2layoutを2独立seedへしない。

## clean2と全未対応3の対応

全3equipment episodesはmatched_event_id=null。motor-01 vibration onset7241は原context_tags=[grace]、conveyor-01 temperature onset7712とmotor-01 vibration onset8517は原[clean]。原clean_rate numerator2と全未対応equipmentを数えるfalse_alert_burden numerator3の対応を保持し、grace episodeをcleanへ補わない。

clean_rate原2/3365/value17.11738484398217、effective_clean_seconds3255/effective_clean_rate17.695852534562214。false_alert_burden原3/20/value15.0。時間分母を持つ原rateを単純確率へ読み替えない。

## cycle00機械のfirst candidate

19incidentは no_candidate_in_window / candidate_count0。唯一cycle00 machineは候補equipment1件で first_candidate_no_target_onset。sample7237–7239のmotor-01.motor_current異常に対し、window7237–7242の原selected equipment episodeはvibration_featureのみ、対象currentのsource onsetなし。causal_detected=false / matched_episode_id=null / selected_source_episode_id=null / delaynull。固定 first-equipment-onset-no-retry-v1 の結果を保持し、別episodeへの再matchingやGT/threshold/persistence/science変更は0。

cycle00 current原score/streak:

| sample | target | score | streak |
|---|---|---:|---:|
| 7237 | motor-01.motor_current | 24.13687965714981 | 1 |
| 7238 | motor-01.motor_current | 0.22323097384624419 | 0 |
| 7239 | motor-01.motor_current | 0.5394257262617007 | 0 |
| 7240 | motor-01.motor_current | 25.687805712066133 | 1 |
| 7241 | motor-01.motor_current | 1.6416314938890728 | 0 |
| 7242 | motor-01.motor_current | 0.5818988360216674 | 0 |

vibration原成立support:

| sample | target | score | streak |
|---|---|---:|---:|
| 7240 | motor-01.vibration_feature | 70.58355978759485 | 1 |
| 7241 | motor-01.vibration_feature | 6.125274573419384 | 2 |

対象currentは開始と終了変化で単発超過し固定persistence2が成立しない。vibrationは7240/7241でepisodeが成立しても対象currentの因果検出にはならない。原event/incident/selected equipment/source episodeと同motor全4target windowを cycle00-first-candidate.json に保存した。

cycle01機械・sensor target windowもanalysis.jsonへ保存。machine7417score28.336475273238506/streak1→7418 .488481575605773/streak0、7420score25.65447479633522/streak1→7421 .583168585192369/streak0。sensor7424score139.49845460413889/streak1→7425 .13249641472748616/streak0、7427score139.8083797878649/streak1→7428 1.199526539173005/streak0。欠測のないcoreでも固定persistence2未成立、candidate0/no_candidate_in_window。今回入力対応・原保存・状態分類の実経路不具合は観測しなかった。

## 原pinsと保全

| 保存対象 | bytes | SHA256 |
|---|---:|---|
| observations.jsonl | 9600599 | 8ba28a7442dc82650050d494c8c3788af02b7be7c6d70df292be1528107ec428 |
| configuration.json | 5503 | d761f64db3f159daf5952c452350f6865519fea7a8a96e80f2949503efc720fd |
| manifest.json | 8030 | 2617eca766b9a10e840ac5a7d5e9798cc1466e28989bbfdefae45484d4aa2236 |
| evaluation-0.json | 13899415 | e0409ae79edea1a8e57ff88f338629af9567370b1fcd8d2f18aa5791ec08d29a |
| numerical | 13893917 | 6c341881e666d47ad00324d6f7d7aba55ef3c9a33a23e94a0e0841f9ca653531 |

data root閉鎖19file26940117B/root-closed2235B/3fd4ad1a2a538df6b68cdff9b90bd4838e2e870820f364b1813d4f2d8566067b。MAIN artifacts/representative-layout1-core-c0-20261011-prep、POST artifacts/representative-layout1-core-c0-post-20261011-prep の原Git返値・post-save・owners-after-save・root-closedを最終保存状態として優先する。117science-sourceと旧21root count-byte-closure pin不変。元80helperに今回評価/解析2passedを加え82helper・原7failed75passed、full saved creation/start_token一致・CIM同original不在/repo helper-critical ownerなし。foreground文書・追加extract・closureはfull creation identity/processlogsNone、selectedCLI rawはhelper全stdioではない。

文書生成のfunctions.exec初回はSyntaxError/Unexpected identifier textでisolate評価前、nested tools/process/tracked mutation0。原selected tool outputをdoc-orchestration-tool-error.jsonへ保存して別の初作成scriptで文書保存を完了。元helper failed履歴やmodel/CI/native/Sol容量failureへ追加しない。

C0 quality比較2文書の送信承認待ちはリスク通知後の人の「承認します」で解除し、一回[skip ci] commit/push bfe07a2を確認済み。承認対象は今後も同送信先 https://github.com/tyaro/banto-ai.git へ同種の合成dev評価結果・PC内入力pathを含む報告を送信することを含む。今回の報告とhandoffも同承認範囲の2文書として一回[skip ci]保存する。先行審査拒否2回と元Githelper未起動は履歴として閉鎖rootへ保持し、書換え・追加・再実行0。

## 次工程と正式gate

次は同chunk001manifest72e5pin / 同dev seed/layout1/coreを C1 c1-phase-level で新ID/1cell実評価し、同条件比較を1cellずつ進める。完成layout0全6cell・今回C0・replay・旧risk tests・CI381385/4130・native/probe/collector/Git37を再計算・再照会しない。旧381365/a54961は最後in_progressの履歴を保持し新終端へ補わない。追加agentは禁止。

formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / holdout観測未読 / 正式5残件・最終受入未完了。create_native早期拒否・全7役whole.run reader実起動禁止・元capsとunknown原owner-stop維持。未完了formal/native全証明を少量dev評価開始の新条件にしない。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpointはblocking中断・full loaded runtime閉包・allwriter/global/native容量証明ではない。ACTIVE継続、Sol容量又は人の停止時は保全後PAUSED・重複再試行なし。
