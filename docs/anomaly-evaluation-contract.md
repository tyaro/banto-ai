# Event-aware anomaly evaluation v0.1 contract

この文書は、既存のforecast benchmarkとは別に、synthetic datasetの既知eventを使って異常スコアとincident単位の結果を再集計する、stdlib-only評価器の契約です。対象は研究用のoffline artifactに限ります。Totoの性能、実設備の一般性能、production alerting、早期警報のリードタイム、製品昇格、PLC／Banto Hubへのwrite権限はこの評価から導きません。

## 入力と実行

構成例は次の2つです。

- generator: [`examples/configs/synthetic-anomaly-evaluation-v0.1.json`](../examples/configs/synthetic-anomaly-evaluation-v0.1.json)
- evaluator: [`examples/configs/anomaly-evaluation-v0.1.json`](../examples/configs/anomaly-evaluation-v0.1.json)

clean checkoutで、まず専用scenarioを生成し、その後に評価します。

```text
python tools/data-generator/generate.py --root . --config examples/configs/synthetic-anomaly-evaluation-v0.1.json
python tools/evaluator/evaluate_anomalies.py --root . --config examples/configs/anomaly-evaluation-v0.1.json
```

既存の [`_verify_dataset`](../src/banto_ai/event_slices.py) をquality gateとして再利用します。gateがPASSでないdataset、fingerprintが一致しないdataset、UTCでないtimestamp、欠損したmanifest、規則外のJSONLは評価しません。

evaluator configとresultは、それぞれ [`anomaly-evaluation-config.schema.json`](../schemas/anomaly-evaluation-config.schema.json) と [`anomaly-evaluation-result.schema.json`](../schemas/anomaly-evaluation-result.schema.json) で検証します。configのevent classificationは、datasetでenabledになっているevent IDを、`machine_fault`、`sensor_fault`、`data_quality`、`ignored`のいずれかへ一度ずつ割り当てる完全partitionです。unknown、duplicate、missingはfail closedです。

`status=pass`は、profile校正が可能で、eligible incidentが少なくとも1件あり、評価契約を最後まで実行できたことを示します。precision／recallなどの性能目標を満たしたという判定ではありません。`partial`はprofile校正は可能だがeligible incidentがない場合、`inconclusive`は1つ以上のprofileが校正不能（点数不足、MAD=0、非有限値など）の場合です。single-seed sampleはrecall 0でも`pass`になり得ます。

## Causal score

全時刻のscoreは、configured equipment／target signalのtest splitだけに対して計算します。

1. 予測値は作りません。現在の実測値から、同じequipment／signalの直前の1点の実測値を引き、`residual = actual_t - actual_(t-1)` とします。
2. 直前点は未来値ではなく、validationからtestへ跨ぐ直前の履歴点だけは利用できます。
3. 現在点と直前点の両方が`quality=ok`、有限値、サンプリング間隔どおりでなければresidual／scoreはunavailableです。
4. validationだけで、`equipment + full signal + operating mode`ごとにprofileを作ります。centerはresidualのmedian、`MAD = median(abs(residual - center))`、scaleは`1.4826 * MAD`です。currentまたはimmediate-previous timestampがenabled event intervalに入るresidualは校正から除外します。
5. calibration pointが`min_calibration_points`未満、MADが0、またはcenter／MAD／scaleが非有限ならprofileは`inconclusive`です。global fallback、epsilon、別modeの流用、testによる再校正はありません。
6. test scoreは`abs(residual - center) / scale`です。`robust_z_threshold`を超える点を連続`persistence_points`点確認した時刻をalert onsetとします。mode／profile group変更、sampling gap、quality不良、residual／score unavailable、threshold未満でpersistenceはresetします。

test-only modeもprofile台帳には現れますが、validationの校正点がなければinconclusiveとして明示されます。したがって、scenarioがtestで新しいmodeを突然出すことによって、結果を黙って除外することはありません。

## Eventとincident matching

event intervalとdetection windowはすべて`[start,end)`です。positive classはmachine faultとsensor faultだけです。data quality eventはmachine faultへ数えず、そのquality非OK点はscore対象外です。ignored eventもpositive incidentではありません。

eventがtest splitと重なり、かつconfigured equipment／full target signalに一致する場合だけeligibleです。eligibleでないeventもincident rowとして残し、`eligible=false`と理由（split外、class、またはunconfigured signal等）を記録します。

eligible eventのdetection windowは次です。

```text
[max(event.start, test.start), event.end + detection_grace_points * sampling_interval)
```

同じequipment／signalのeligible windowが重なる場合は、曖昧なone-to-one matchingを避けるため評価全体をfail closedにします。alert episodeは同じequipment／signalのeventへ最大一度だけ対応させます。alert onsetがevent開始前ならcreditしません。`detection_delay_seconds`は観測されたalert onsetからevent開始までの非負秒数だけであり、負のlead timeは出力しません。

## Metrics

resultには、raw score row、alert episode、全eventのincident rowを保存します。

- overallと`machine_fault`／`sensor_fault`別に、eligible、detected、missed、incident recall、detection delay summaryを出します。
- `matched_eligible_alert_episodes`と`unmatched_eligible_alert_episodes`をone-to-one matchingの結果として出します。
- 全signal-level alert episodeは`alert_episode_accounting`へ一度だけ記録し、`matched_eligible`、`unmatched_eligible_same_signal`、`clean_false_alert`、`suppressed_event_window`の4 partitionの合計がtotalと一致します。suppressedの理由は`positive_nonmatching_signal`、`data_quality`、`ignored`に分けます。
- incident precisionはsignal-levelで単位を統一し、matched true-positive signal episode数を、matched episode＋unmatched eligible-window episode＋clean false-alert signal episodeの合計で割ります。equipment-levelへdeduplicateしたclean countをprecisionの分母へ混ぜません。suppressed event-window alertは、同一signalのeligible incident alertでもclean exposureでもないためprecision分母から除外し、partitionと理由別countには残します。
- test中の全enabled event（data quality／ignoredを含む）とgrace区間をclean exposureから除外します。clean false alertはequipment-level episodeへ集約します。
- clean equipment hours、false alerts per 8 equipment-hours、可能な範囲でtarget signalごとのclean hoursを出します。
- 同じequipmentで複数signalのclean alert intervalが重なると、一つのequipment episodeへdeduplicateします。source signal episode IDは結果に残します。

resultの`clean_false_alert_signal_episode_count`はprecision用のsignal-level FP、`clean_false_alert_equipment_episode_count`（互換aliasとしての`clean_false_alert_episode_count`を含む）は運用false-alert rate用のequipment-level deduplicated countです。`suppressed_event_window_alert_episode_count`はclean exposureから除外したもののprecision分母へ入れないalertの総数で、旧`suppressed_ineligible_event_window_alert_episode_count`互換aliasと、positive／data-quality／ignored別のcountを併記します。`metrics.alert_episode_partition`と`alert_episode_accounting`で、suppressedを含む全alert episodeの厳密な総和を監査できます。

## Provenanceとpublish

resultにはconfig／schemaのsha256、dataset path／ID／fingerprint、dataset-manifest hash、PASSしたquality gate、開始code revision、threshold／persistence／grace／target、profileのcenter／MAD／scaleと点数、calibration／scoring／event exclusion、raw row counts、制約を記録します。

`output_dir`はrepository内の`artifacts`直下の新規directoryに限定します。config、dataset、manifest経路のsymlinkとpath traversalは拒否し、dataset file inventory／hash、config、両schema、code revisionを評価前後に再確認します。既存outputのoverwriteはしません。

resultとsummaryは一時directoryへfsyncしてから新規output directoryをclaimし、`result.json`、`summary.md`、最後に`.complete`をexclusiveに配置します。`.complete`がないdirectoryは完了artifactではありません。publish後も顧客データ、credentials、checkpoint、control writeは生成しません。

## 解釈上の制約

これはsingle-seed synthetic scenarioの契約検証です。event injectionがscoreへ寄与すること、特定のfaultが検知できること、実設備での誤警報率やlead timeを保証するものではありません。複数seed、event位置・mode・設備の拡大、正式な不確実性評価、実設備データへの一般化は別の研究工程です。
