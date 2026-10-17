# v0.3 dev layout1 C2 quality-stress実評価 — 2026-10-12 JST

## 入力と実行

同保存合成dev seed2486912926863618161 / layout1 / quality-stressを既存CLI c2-phase-conditionalで新ID/1cell実compute_evaluationした。元chunk001 manifest10input pins→新snapshot→fresh fit/calibration→原profiles/scores/source・equipment episodes/events/incidents/metricsを保存。元payload書込み・新dataset生成・replay・production/test変更・類似owner追加・追加agent・holdout観測読取りは各0。

~~~text
C:/Python314/python.exe -B tools/evaluator/run_representative_anomaly.py
  --input-manifest C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/001/attempt-0001/result/payload/manifest.json
  --manifest-sha256 72e5a34c662f77c4728583b9e61cc9d2977edd2ecc9e5286194aae0d2c055dbf
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-01-quality-stress
  --candidate c2-phase-conditional
  --output artifacts/representative-anomaly-evaluation/dev-layout1-quality-c2-20261012
~~~

元manifest75699B。actual文書checkout HEAD01498f4fdbc9d2a2734a1aa98dbfdcdc21b22695、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actual CPython3.14.0 / Windows / AMD64、elapsed27.0898576999316秒、OS checkpoint peak private207319040B。48profile calibrated / fit_samples各600 / calibration_samples各290。実計算UTC2026-10-11、作業日JST2026-10-12。

CLI exit0 / complete / 1cell successは処理完了。正式性能合格・勝者・採択へしない。bootstrap・統計CI推定・正式creditは0。

## 原結果と保存済み比較

| 保存条件 | 機械 | sensor | precision | clean誤警報 | 利用可能score | 検出delay中央値 | source数 |
|---|---:|---:|---:|---:|---:|---:|---:|
| c1-phase-level / layout1 / quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13880/14400 | 1.0秒 | 29 |
| c2-phase-conditional / layout1 / core | 10/10 | 10/10 | 20/20 | 0 | 13920/14400 | 1.0秒 | 40 |
| c2-phase-conditional / layout0 / quality-stress | 4/10 | 9/10 | 13/19 | 0 | 13760/14400 | 1.0秒 | 39 |
| c2-phase-conditional / layout1 / quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13760/14400 | 1.0秒 | 38 |

今回38source episodes / 19equipment episodes / 20incidents / 40events。機械10/10・sensor9/10・precision19/19・clean誤警報0・全未対応equipment0。検出19件だけdelay中央値・平均・min・max各原1.0秒。未検出1件は原delaynullのまま、補完0。clean_rate原0/3365/value0.0、effective_clean_seconds3255/effective_clean_rate0.0、false_alert_burden原0/20/value0.0。原rateと分母を保持する。

同quality C1と全10input raw pinsが一致。C2coreと旧layout0 C2qualityは保存manifest/config指標だけ比較し再compute0。全比較の宣言16calculator sources・candidate config・compiled config一致。固定threshold6/persistence2/first-equipment-onset-no-retry-v1/GT/科学式変更0。C1qualityと今回C2qualityの集計指標は同じだが、source29対38、利用可能13880対13760で原score/episode同一ではない。

## peer入力依存による追加不能120

保存input snapshotのobservations18000行とquality-mask18000行を照合し、motor-01.motor_temperature:missingの30観測だけが非ok。全30mask/observation原recordsをextractへ保存。

14400scoreの利用可能13760・不能640。排他的primaryはmode_recipe_or_phase480 / peer_quality_or_nonfinite120 / current_target_quality30 / previous_target_quality_or_nonfinite10。温度自身は現在欠測30とprevious10で40不能、C2は同motorの残り3targetが各40peer不能、計120に波及する。C2core保存不能480に対する増分160、同quality C1保存不能520に対する増分120を原行数で保持する。peer120は120別観測の欠測ではない。

| full_target | phase不能 | peer不能 |
|---|---:|---:|
| motor-01.motor_current | 60 | 40 |
| motor-01.conveyor_speed | 60 | 40 |
| motor-01.vibration_feature | 60 | 40 |

非排他的current quality30/current nonfinite30/previous quality30は重複するため加算しない。全不能score/residual=null・threshold_exceeded=false。不能をscore0や通常値へ補わない。

## cycle09 sensor未検出と同motor4target window

唯一未検出はmotor-01.motor_temperature / sensor spike / start_sample8864、end_sample8867、window_end_sample8870。8864原temperature score167.45746264075765>6 / streak1。8865–8867 current欠測、8868 previous品質不良でreset。8869で利用可能に戻ってscore1.6808862665066906<6。固定persistence2・second-exceedance onset不成立。

| sample | temperature score | primary reason | streak |
|---|---:|---|---:|
| 8864 | 167.45746264075765 | None | 1 |
| 8865 | null | current_target_quality | 0 |
| 8866 | null | current_target_quality | 0 |
| 8867 | null | current_target_quality | 0 |
| 8868 | null | previous_target_quality_or_nonfinite | 0 |
| 8869 | 1.6808862665066906 | None | 0 |

同motorのcurrent/conveyor_speed/vibrationも8865–8868で原peer_quality_or_nonfinite、score/residualnull・streak0。原event/incident・同motor全4targetの拡張windowを保存した。原incident no_candidate_in_window / candidate_count0 / causal_detected=false / matched_episode_id=null / selected_source_episode_id=null / delaynull / support[]を保持。閾値/GT/設定/matchingを変えて検出へ補わない。

全20原event/incident ledger、未検出4target window、cycle00検出2件のselected source/equipmentと4target window、全30非ok input recordsを新extractへ保存。実input対応・保存・状態分類の不具合は観測しなかった。旧layout0 C2qualityの機械4/10・sensor9/10・precision13/19・旧未検出7件を今回の成功へ書き換えない。同seed別layout/stratum、新独立seedではない。

## pins・metadata表示制限・保全

| 保存対象 | bytes | SHA256 |
|---|---:|---|
| observations.jsonl | 9600602 | 6b177a9251d5d61bdb23075376e5c167c8f87b5ec1f46dbcac8a74fc4c7a341e |
| configuration.json | 5518 | e852fd11b09b8c08a199e42a85c8f3174710c824726670d02f2a39e611bcbb65 |
| manifest.json | 8039 | a2157815936c182eccc93409dddd4dfa16821ba482417df4d5a2b218b092844a |
| evaluation-0.json | 25190946 | 7de53fc2ee7b52c108bfdde8966cdd0affd5d5bf395c4eebcd07c44e5566eff9 |
| numerical | 25185348 | 413ba87b907beec0705e4d513ff453a52ecfd11dbca0560c9ff76f20938f3c1e |

data root閉鎖19file/38238009B/root-closed2246B/a19e889658e432997f23793cd5e86d6741687fb870fb1da819732ec38be37bd2。EXTRACT artifacts/representative-layout1-quality-c2-extract-20261012-prep閉鎖4file/103821B/root-closed703B/81bd5ee11cd40518e0a3bbf4a6502cf5be26c3bf983e85b3d7f817b3e4b0aaff。MAIN artifacts/representative-layout1-quality-c2-20261012-prep / POST artifacts/representative-layout1-quality-c2-post-20261012-prep のpost-save/owners/root-closedを最終Git保存状態として優先。

補助prepare stdoutの旧roster表示33が残ったが、原prepared-evaluation.jsonと実assertは37closed roots。EXTRACT closureのscope文字列に旧C1表記が残ったが、元records/result pin/candidateは今回C2に対応する。原表示文字列とその限界を保全し、POST補足を優先。閉鎖scopeを書き換え・再発行せず、表示文字列からC1再評価やモデル同一性を補わない。helper/model failureとしては扱わない。

117science-source・旧37root count-byte-closure pin、外部固定C1 MAIN35file226520B、旧C2 cache補足pinは不変。前回failed/capacityfalse/原closure coverage制限を保持し、元root追加・原helper再実行・raw削除移動・上限緩和0。python -B/recursive file count-byte-pin、書込み前script/失敗/終端/closure reserve確認でmetadata512KiB32entry/reserve128KiB/single128KiB維持。

元94helper原9failed85passedに今回モデル/解析2passedを加え96helper原9failed87passed。full saved creation/start_tokenのlive/execution一致・CIM同original不在・repo helper-critical ownerなし。原failed書換え0。foreground準備/docs/closure full creation/全stdioNone、selectedCLI rawはhelper全stdioではない。CIM decimal100ns→microsecond trunc/full token一致、PID単独/native回収claim0。

Git送信は、人のリスク通知後「承認します」による今後同送信先 https://github.com/tyaro/banto-ai.git への同種合成dev結果・ユーザー名を含むPC内入力path報告の継続承認でreport/current-handoff2文書を一回[skip ci] commit/pushする。原先行拒否/元Githelper未起動は歴史保全。heartbeatは詳細結果/PC内pathを含まない文書参照短指示のACTIVE維持、今回automation更新/詳細payload再送0。

## 次工程と正式gate

次は同保存chunk001 manifest72e5pin / devseed2486912926863618161 / layout1 / quality-stressをC0 c0-diff-control、新ID dev-layout1-quality-c0-20261012 / 1cell実評価してlayout1の3候補×2strata比較を完成する。元payload保持・新生成0・1cellずつ。補助表示はcandidateと実roster値から作り旧表示文字列を流用しない。

完成layout1/core3cell・C1/C2quality・layout0全6cell・replay・旧risk tests・CI381385/4130・native/probe/collector/Git37を再実行・再照会しない。旧381365/a54961最後in_progressは履歴保持、doc-only CI追跡0、追加agent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader起動禁止/元caps-unknown原owner-stop維持。engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpointはblocking中断/full loaded runtime閉包/allwriter-global-native容量証明ではない。未完了formal/native全証明を少量dev開始条件に戻さない。ACTIVE継続、Sol容量/人の停止では保全後PAUSED・重複再試行なし。
