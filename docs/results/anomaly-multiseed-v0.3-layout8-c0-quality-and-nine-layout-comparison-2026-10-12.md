# layout8 C0 quality実評価と9 layouts比較（2026-10-12）

同保存dev quality-stressを既存CLI C0で一回fresh評価。exit0/complete/1cell success。機械0/10・sensor0/10・precision0/3・clean誤警報3。処理成功を性能合格、採択、正式受入へしない。

## 入力・計算・原結果の対応

- run dev-layout8-quality-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-08-quality-stress。
- 元input manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\008\attempt-0001\result\payload\manifest.json、pin {"bytes": 75698, "sha256": "c4dfa23be3bca2f563e587f4f83a33e20f5304f9bd518b791dcb6cc7b74b06b4"}。
- seed2486912926863618161/layout8/quality-stress/dev。元生成candidateと実評価candidateは別fieldで保持。同quality C1/C2 input10 pins一致。
- 10pins照合→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics保存。元payload書込み、生成、replay、追加agent0。
- actual checkout 9c65a467f5f282424d2f9bf59cdb870300c0509f、計算code661b27511826fcc87cb4a02930f276afbb8f95d9から不変。declared16/candidate config/compiled config一致はfull loaded runtime/native認証ではない。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 27.445918999961577秒/OS sampled privatepeak 148811776B。
- observations {"bytes": 9600604, "sha256": "9f812738c1fd9805d257a10ca30ded867afc56bc4642437914451a34b5a25d61"}、config {"bytes": 5513, "sha256": "206780a1de33bc4a85d1a77025326e9dd3924741ca201cb5ba61398c12c33281"}、manifest {"bytes": 8065, "sha256": "2782d09a5416e7b3f46f0c29cbe4e71c2da12cb2fc628cf183f9514c6649ac72"}、evaluation {"bytes": 14336630, "sha256": "043c2132f97971d9b045d606abaf585c94b2e3232244e268816f6c9001ad4701"}。
- 48calibrated、原fit samples各0/calibration各290、14400scores。GT/C0 threshold4.0/persistence2/matching/config/science変更0。

## 原指標

| 指標 | 原値 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean_rate | 3/3365、value 25.676077265973255 |
| effective clean | 3255秒、value 26.543778801843317 |
| false_alert_burden | 3/20、value 15.0 |
| detection delay | count0、min/max/mean/median原null |

clean_rateとburdenの原valueを単純確率へしない。全20未検出のdelay nullを保持。3source/3equipmentは全clean・matched_event_id nullで、全未対応3とclean3を別fieldで保持する。

2026-10-12の設定metadata照合で、この報告のC0閾値6表記を4.0へ訂正した。保存済みcandidate/compiled configのC0は4.0、C1/C2は6.0。実計算設定・score・episode・指標は変更せず、旧計算の再実行0。元報告bytesとGit commit35e523bは原保存として保持。照合記録はlayout9 core C0の-save内threshold-declaration-correction labelを参照。

## 未検出20件と利用不能行

全20 incidentはcandidate_count0/no_candidate_in_window/causal_detected false/matched null/delay null。対象窓の最大streakは全1で、固定persistence2が成立しない。
利用可能13880・不能520、排他的primary phase等480/current quality30/previous quality10。全不能score/residual null・threshold_exceeded false。
非排他的tags phase480/current30/current nonfinite30/previous30は重複するため加算しない。phase-quality重複0、18000 observationとmask対応/欠測30。欠測一件だけで全20未検出を説明しない。

### cycle0 machine conveyor-01.conveyor_speed

| sample | available | score | streak | exclusion |
| --- | --- | --- | --- | --- |
| 7260 | False | None | 0 | mode_recipe_or_phase |
| 7261 | True | 0.12267601921717763 | 0 | None |
| 7262 | True | 0.6104700644959261 | 0 | None |
| 7263 | True | 80.07506644738844 | 1 | None |
| 7264 | True | 1.521855583098382 | 0 | None |
| 7265 | True | 2.1409648038772353 | 0 | None |
| 7266 | True | 0.4629678382762895 | 0 | None |

### cycle0 sensor conveyor-01.motor_temperature

| sample | available | score | streak | exclusion |
| --- | --- | --- | --- | --- |
| 7267 | True | 216.98763375414546 | 1 | None |
| 7268 | True | 1.515764244981574 | 0 | None |
| 7269 | True | 1.0962389352673583 | 0 | None |
| 7270 | True | 215.6408479931459 | 1 | None |
| 7271 | True | 0.014407967311507841 | 0 | None |
| 7272 | True | 1.0959407459155477 | 0 | None |
| 7273 | True | 0.6524518555738958 | 0 | None |

### cycle9 sensor conveyor-01.motor_temperature

| sample | available | score | streak | exclusion |
| --- | --- | --- | --- | --- |
| 8887 | True | 217.05193422162057 | 1 | None |
| 8888 | False | None | 0 | current_target_quality |
| 8889 | False | None | 0 | current_target_quality |
| 8890 | False | None | 0 | current_target_quality |
| 8891 | False | None | 0 | previous_target_quality_or_nonfinite |
| 8892 | True | 1.4726352214771372 | 0 | None |
| 8893 | True | 0.10709063944345391 | 0 | None |

全20event/incident、全4target窓、原source/equipment episodes、欠測30と不能520を新analysis recordへ保存。原入力対応・保存・状態分類の実経路不具合は観測しなかった。

## 同layoutの3候補×2strata

| stratum | 候補 | machine | sensor | precision | clean | available |
| --- | --- | --- | --- | --- | --- | --- |
| core | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13920 |
| core | c1-phase-level | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| core | c2-phase-conditional | 10/10 | 10/10 | 20/20 | 0 | 13920 |
| quality-stress | c0-diff-control | 0/10 | 0/10 | 0/3 | 3 | 13880 |
| quality-stress | c1-phase-level | 10/10 | 9/10 | 19/19 | 0 | 13880 |
| quality-stress | c2-phase-conditional | 10/10 | 9/10 | 19/19 | 0 | 13760 |

保存manifest指標だけを比較し、旧modelは再計算していない。同layout C1/C2 coreは20件検出、qualityは各19件。C0は両strataで20件未検出。

## C0 qualityの9 layouts保存比較

| layout | machine | sensor | precision | clean |
| --- | --- | --- | --- | --- |
| 0 | 0/10 | 0/10 | 0/3 | 3 |
| 1 | 0/10 | 0/10 | 0/3 | 2 |
| 2 | 0/10 | 0/10 | 0/3 | 3 |
| 3 | 0/10 | 0/10 | 0/3 | 3 |
| 4 | 0/10 | 0/10 | 0/3 | 3 |
| 5 | 0/10 | 0/10 | 0/3 | 3 |
| 6 | 0/10 | 0/10 | 0/3 | 3 |
| 7 | 0/10 | 0/10 | 0/3 | 3 |
| 8 | 0/10 | 0/10 | 0/3 | 3 |

同coreC0＋同qualityC1/C2＋過去8layouts qualityC0＋今回を12セル比較。旧53board＋今回1で54完了、9layouts×2strata×3候補の保存boardが揃った。同合成dev seed1で54独立datasetではない。bootstrap、統計CI推定、勝者、候補採択0。

## 保存と次unit

- model artifacts/representative-layout8-quality-c0-20261012-records、analysis ...-analysis、docs/Git ...-save、最終 ...-final/root-closed.jsonとpost-save labelを優先。
- 対象窓 {"bytes": 978172, "parts": 4}、不能 {"bytes": 520274, "parts": 2}、analysis {"bytes": 385501, "parts": 2}。
- DATA artifacts\representative-anomaly-evaluation\dev-layout8-quality-c0-20261012/root-closed.json、{"bytes": 27384462, "files": 19, "manifest_pin": {"bytes": 2228, "sha256": "7cecaebbc585ff44f32c1c713d35abc13b478b20af8c9ae3b090a4d746b08728"}}。
- 原CLI selected stdout/stderrとfull saved helper creation/executionを保持。helper全process stdioやnative回収の証拠へしない。
- 次は同seed/layout9 core C0、新ID dev-layout9-core-c0-20261012。chunk009 manifest metadataだけ選択、次観測body未読/newmodel0。同seed別layoutで新seedではない。
- 次manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\009\attempt-0001\result\payload\manifest.json、pin {"bytes": 75699, "sha256": "7a71c5434cc8f526ada42d7a3f885bf711cabc256a7ff891c95a8969c6c58e5c"}。

修正済みprepare_result_indexで新報告の索引候補を作り、旧件数/リンクsource置換は使わない。指定handoff/report/index3文書を継続送信承認範囲で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-finalを参照。

実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native制限を維持。新検証16MiB512files/part256KiBと失敗予備枠。閉鎖/外部固定root追記・元raw整理再生成0。
ACTIVE。CI381385/4130は保存済み、新照会/download/verifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED・重複再試行なし。
