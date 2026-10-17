# v0.3 dev layout1 C1 quality-stress実評価 — 2026-10-12 JST

## 入力と実行

保存済み合成dev seed2486912926863618161 / layout1 / quality-stressを既存CLI c1-phase-levelで新ID/1cell実compute_evaluationした。元chunk001 manifest10input pins→新snapshot→fresh fit/calibration→原profiles/scores/source・equipment episodes/events/incidents/metricsを保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agent・holdout観測読取りは各0。run IDは前工程の予定名を使用し、作業日はJST2026-10-12、実計算UTC2026-10-11として保持する。

~~~text
C:/Python314/python.exe -B tools/evaluator/run_representative_anomaly.py
  --input-manifest C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/001/attempt-0001/result/payload/manifest.json
  --manifest-sha256 72e5a34c662f77c4728583b9e61cc9d2977edd2ecc9e5286194aae0d2c055dbf
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-01-quality-stress
  --candidate c1-phase-level
  --output artifacts/representative-anomaly-evaluation/dev-layout1-quality-c1-20261011
~~~

元manifest75699B。actual文書checkout HEADf4bef749ce52e808fcab006a0ffdc86e5bdf063e、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actual CPython3.14.0 / Windows / AMD64、elapsed18.798073199926876秒、OS checkpoint peak private148037632B。48profile calibrated / fit_samples各600 / calibration_samples各290。

CLI exit0 / complete / 1cell successは処理完了。正式性能合格・勝者・採択へしない。bootstrap・統計CI推定・正式creditは0。

## 原結果と保存済み比較

| C1保存条件 | 機械 | sensor | precision | clean誤警報 | 利用可能score | 検出delay中央値 |
|---|---:|---:|---:|---:|---:|---:|
| layout1 / core | 10/10 | 10/10 | 20/20 | 0 | 13920/14400 | 1.0秒 |
| layout0 / quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880/14400 | 2.0秒 |
| layout1 / quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880/14400 | 1.0秒 |

今回29source episodes / 19equipment episodes / 20incidents / 40events。機械10/10・sensor9/10・precision19/19・clean誤警報0・全未対応equipment0。検出19件だけdelay中央値・平均・min・max各原1.0秒。未検出1件は原delaynullのまま、補完0。clean_rate原0/3365/value0.0、effective_clean_seconds3255/effective_clean_rate0.0、false_alert_burden原0/20/value0.0。分母と原rateを保持する。

coreと今回quality、旧layout0 qualityの宣言16calculator sources・candidate config・compiled config一致。旧モデル再compute0。core/qualityは同seed/layoutの2strataで入力10logical filenamesは同じだが、file pinが異なる対象は dataset-manifest.json, event-ledger.jsonl, events.jsonl, fingerprint.json, generator-config.json, observations.jsonl, quality-mask.jsonl。全10raw pinsが同一だとはしない。旧layout0も同seedの別layoutであり、新独立seedではない。

## 欠測30観測と不能520score

今回保存input snapshotのobservations18000行とquality-mask18000行を対応照合。非okはmotor-01.motor_temperature:missingの30観測だけ、うち原signal value nullは30観測。全30mask/observation原recordsをextractへ保存した。

14400scoreの利用可能13880・不能520。排他的primary reasonはmode_recipe_or_phase480 / current_target_quality30 / previous_target_quality_or_nonfinite10。非排他的tagsはphase480 / current quality30 / current nonfinite30 / previous quality-or-nonfinite30で重複する。quality関連tagsの和90を90独立不能scoreへしない。全不能score/residual=null・threshold_exceeded=false。core保存13920/480に対する追加不能40は現在欠測30と、排他的に数えたprevious10に対応する。

## cycle09 sensorの未検出

原eventはmotor-01.motor_temperature / sensor spike / start_sample8864、end_sample8867、window_end_sample8870。8864だけscore183.1363688464011>固定threshold6、streak1。8865–8867はcurrent欠測でreset、8868はprevious品質不良でreset、8869で利用可能に戻ってscore1.8487126384105506<6。固定persistence2・second-exceedance onsetが成立せず、source/equipment候補は原0。

| sample | available | score | primary reason | streak |
|---|---|---:|---|---:|
| 8864 | True | 183.1363688464011 | None | 1 |
| 8865 | False | null | current_target_quality | 0 |
| 8866 | False | null | current_target_quality | 0 |
| 8867 | False | null | current_target_quality | 0 |
| 8868 | False | null | previous_target_quality_or_nonfinite | 0 |
| 8869 | True | 1.8487126384105506 | None | 0 |

原incident no_candidate_in_window / candidate_count0 / causal_detected=false / matched_episode_id=null / selected_source_episode_id=null / delaynull / support[]を保持。threshold・persistence・GT・matching・科学式を変更して検出へ補わない。

同layout1/coreの保存済み対応event/incidentは同start_sample8864・同target、causal_detected=true / delay1秒 / 原support2件だった。今回qualityでresetした8865を含むcore原support IDsを未検出との比較として保存し、coreを再計算しない。原coreとqualityの状態を別run/stratumの結果として保持する。

全20原event/incident ledger、唯一未検出のtarget window、cycle00正常検出2件のselected source/equipment/target window、全30非ok input recordsを新extract rootへ保存。原input対応・保存・状態分類の実CLI経路不具合は観測しなかった。

## pinsと保全

| 保存対象 | bytes | SHA256 |
|---|---:|---|
| observations.jsonl | 9600602 | 6b177a9251d5d61bdb23075376e5c167c8f87b5ec1f46dbcac8a74fc4c7a341e |
| configuration.json | 5512 | 9bd62653586a5aa12079a47a8376306b48674f3c480ff8e12d2bcaddd09acacd |
| manifest.json | 8035 | 399af646470a861c738d4c6726772927936a4408aa445523e7440050a7a2cb54 |
| evaluation-0.json | 14510373 | 7922a2ac2160e8474238087fe4efc8f9384f861fce6429796f8087a3df080824 |
| numerical | 14504775 | db53508f7d037ed87b0a48d5a30f73d9d612314c45b6d049c2ac4bf430463299 |

data root閉鎖19file/27557408B/root-closed2246B/aa01cbb68f077097dcc610da2009519d1b650e1d83ab409acd6f2161b3f5cd11。EXTRACT artifacts/representative-layout1-quality-c1-extract-20261012-prep 閉鎖4file/74841B/root-closed702B/6fa954ff7ba74e5aae087c17e3bdaca783ffc52c21600f09cfd29fefe7a85584。MAIN artifacts/representative-layout1-quality-c1-20261012-prep / POST artifacts/representative-layout1-quality-c1-post-20261012-prep のpost-save/owners/root-closedを最終Git保存状態として優先する。

117science-source・旧33内部閉鎖root count-byte-closure pin、外部固定C1 MAIN35file226520B、C2 helper cache補足pinは不変。前回failed/capacityfalse/原closure coverage制限を保持し、元root追加・原helper再実行・raw削除移動・上限緩和0。今回はpython -Bとrecursive file count/byte/pin閉鎖を用い、新cache書込み0。metadataのscript/失敗/終端/closure分を事前計上し、512KiB32entry/reserve128KiB/single128KiB維持。

元91helper原9failed82passedに今回モデル/解析2passedを加え93helper原9failed84passed。full saved creation/start_tokenのlive/execution一致・CIM同original不在・repo helper-critical ownerなし。foreground旧解析script selector path missは未存在path読取りだけで原source/旧helper起動0、selected tool excerptへ保存。model/CI/native/Sol容量failureへしない。foreground準備/docs/closure full creation/全stdioNone、selectedCLI rawはhelper全stdioではない。CIM decimal100ns→microsecond trunc/full token一致、PID単独/native回収claim0。

Git送信は、人のリスク通知後「承認します」による今後同送信先 https://github.com/tyaro/banto-ai.git への同種合成dev結果・ユーザー名を含むPC内入力path報告の継続承認で、今回report/current-handoff2文書を一回[skip ci] commit/pushする。原先行拒否/元Githelper未起動は歴史保全。heartbeatは詳細結果やPC内pathを含まない文書参照短指示のACTIVEを維持し、今回automation更新/詳細payload再送0。

## 次工程と正式gate

次は同保存chunk001 manifest72e5pin / devseed2486912926863618161 / layout1 / quality-stressをC2 c2-phase-conditionalで新ID dev-layout1-quality-c2-20261012 / 1cell実評価。元payload保持・新生成0・1cellずつ比較。完成layout1/core3cell・今回C1quality・layout0全6cell・replay・旧risk tests・CI381385/4130・native/probe/collector/Git37を再実行・再照会しない。旧381365/a54961最後in_progressは履歴保持、doc-only CI追跡0、追加agent0。

formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / holdout観測未読 / 正式5残件・最終受入未完了。create_native早期拒否・全7役whole.run reader起動禁止・元caps/unknown原owner-stop維持。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpointはblocking中断/full loaded runtime閉包/allwriter-global-native容量証明ではない。未完了formal/native全証明を少量dev評価開始の新条件に戻さない。ACTIVE継続、Sol容量又は人の停止時は保全後PAUSED・重複再試行なし。
