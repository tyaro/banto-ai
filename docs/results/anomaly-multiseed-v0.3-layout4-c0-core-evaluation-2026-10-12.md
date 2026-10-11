# dev layout4 C0 core実評価（2026-10-12 JST）

## 入力・設定・原結果

同保存chunk004 manifest75699B/54f358a6b69d9df9b27fd1e5762a2f3c63be0ab6e545df7aca8668d4d7f04fc3/dev seed2486912926863618161/layout4/coreを既存CLI C0 c0-diff-control、新ID dev-layout4-core-c0-20261012で1cell実compute_evaluation。input10pins→新snapshot→fresh calibration→原profiles/scores/episodes/events/incidents/metrics保存。元生成identityと実評価candidateは別field（今回は両C0）。

input manifest: C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\004\attempt-0001\result\payload\manifest.json

dataset anomaly-v03-dev-seed-2486912926863618161-layout-04-core、actual文書checkoutd3b2c610823e532819c5cb94d1cc3d49aeaa1cc7、計算code661b27511826fcc87cb4a02930f276afbb8f95d9不変。actualPython3.14.0 Windows AMD64、elapsed60.69412849994842秒/OScheckpoint privatepeak146173952B。元payload書込み・新dataset生成・replay・production/test変更・類似owner・追加agent・holdout本文読取り0。

CLI exit0/complete/1cell success。処理successを性能合格・勝者・採択・正式受入へしない。機械0/10・sensor0/10・precision0/3・clean誤警報3・全未対応equipment3（全clean）。48calibrated/fit_samples各0/calibration各290、14400scores、利用可能13920・不能480（全mode_recipe_or_phase/score-residual null/thresholdfalse）。mask-observation18000行全対応/non-ok0/欠測0。

source3/equipment3/events40/incidents20、全20no_candidate_in_window/candidate0/causalfalse/matched-source-equipment null/support[]/delaynull。delay count0/min/max/mean/median原null、補完0。clean_rate3/3365原25.676077265973255/effective_clean_seconds3255/effective_clean_rate26.543778801843317、false_alert_burden3/20原15.0は単純確率へ変換0。

## 全20対象窓とphaseの原位置

全20event-incidentとmotor4target窓を新EXTRACT保存。対象event start〜window endのmaxstreakは全20件1、固定persistence2不成立。machine10窓はphase不能各1行、sensor10窓はphase不能0。旧layout3のsensor開始phase不能を今回へ流用0。non-ok0をphase不能0へしない。

cycle00machine7320はphase不能。7321score0.1698103485753881/0・7322score0.4560172135018981/0、7323score54.13003315994726/1→7324score0.1759643090013353/0。sensor7327score162.69856590240173/1→7328score1.333617056287099/0、7330score162.58768959471712/1→7331score0.8773809802423528/0。threshold4の単独超過を2連続へ補わない。

### cycle00 machine motor-01.motor_current

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7320 | False | mode_recipe_or_phase | None | None | False | 0 |
| 7321 | True | None | 0.1698103485753881 | 0.02210100000000015 | False | 0 |
| 7322 | True | None | 0.4560172135018981 | -0.05661100000000019 | False | 0 |
| 7323 | True | None | 54.13003315994726 | 6.808821999999999 | True | 1 |
| 7324 | True | None | 0.1759643090013353 | -0.021387999999999963 | False | 0 |
| 7325 | True | None | 0.32358780154489114 | -0.039954999999999075 | False | 0 |
| 7326 | True | None | 0.4273464366336899 | 0.05449199999999976 | False | 0 |

### cycle00 sensor motor-01.motor_temperature

| sample | available | primary | score | residual | threshold | streak |
| ---: | --- | --- | ---: | ---: | --- | ---: |
| 7327 | True | None | 162.69856590240173 | 8.039563999999999 | True | 1 |
| 7328 | True | None | 1.333617056287099 | 0.10494100000000373 | False | 0 |
| 7329 | True | None | 0.21852923041528705 | 0.050109999999996546 | False | 0 |
| 7330 | True | None | 162.58768959471712 | -7.955382999999998 | True | 1 |
| 7331 | True | None | 0.8773809802423528 | 0.08250699999999966 | False | 0 |
| 7332 | True | None | 0.5581133437163556 | 0.06680800000000175 | False | 0 |
| 7333 | True | None | 0.7196893276769943 | 0.07475299999999763 | False | 0 |


全20対象窓maxstreak/phase件数とcycle00原target score rowsをMAIN original-target-window-proof.jsonに保存。全source-equipment6episode/原clean3/全20incidentはEXTRACTへ保存。GT・threshold4・persistence2・second-exceedance・first-equipment-onset-no-retry-v1・science変更0。入力対応・保存・状態分類の実経路不具合は観測なし。

## 5layout C0 core保存比較

| layout C0 core | machine | sensor | precision | clean | unmatched | available/unavailable | delay |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| 0 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 1 | 0/10 | 0/10 | 0/3 | 2 | 3 | 13920/480 | None |
| 2 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 3 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |
| 4 | 0/10 | 0/10 | 0/3 | 3 | 3 | 13920/480 | None |

旧layout0/1/2/3はmanifest/configの保存指標だけ比較、旧4result本文再展開/再compute0。宣言16calculator source/candidate_config/compiled_candidate_config一致、全10input file名一致/原layout別pin差保持。旧layout1のclean2と全未対応3を別に保持。同seed5layoutのC0coreで新独立seed・bootstrap/統計CI・勝者・採択0。先行layout0–3×3候補×2strataの24cell比較は完成保存のまま反復0、今回C0をその24cellの再評価へしない。

## 原pin・root閉鎖・準備失敗の保全

| 原保存 | bytes | SHA256 |
| --- | ---: | --- |
| observations | 9600454 | f72cfa13f68593cfb180508801ff2b0dd34eb4b25377ce93f36e466556838e42 |
| configuration | 5503 | 0fcd28f3238ad96986fbdc9621554247112db897a4d1a13de6f89283a81ed639 |
| manifest | 8031 | e10c8bc87c37d84acc726c12a7071259a2eaab3b3cddd2f87843f177d67564c5 |
| evaluation | 13899213 | b53c9a7c04c5d8dd69db6c64b5bbfc466c72ba59b0d5882bbfa446732a84d681 |
| numerical | 13893715 | 92280c0fb9da48aa18dd2ecc96bf22b2653da746d07d68ac6c51a5d87d452753 |
| comparison | 18672 | 4634150d725f3d60074ea382f78825a2d992fcc005339bf952a1f17099782d64 |
| target-proof | 8490 | 33dc96d83712fdf971d7de1afca22684eab2940593d23ed57a0dd3e4d4caeaaa |

DATA閉鎖{'bytes': 26939897, 'files': 19, 'manifest_pin': {'bytes': 2249, 'sha256': '04871b97d6627bae5dee1877e42e80f8515e11b9b650c84a072d49735806f0ab'}}、EXTRACT閉鎖{'bytes': 277619, 'files': 7, 'manifest_pin': {'bytes': 1066, 'sha256': 'e15df71c62987841fab681f8c4e0d579fd35fef7d16f27e7cd5803aa029bd21c'}}。MAIN representative-layout4-core-c0-20261012-prep/POST representative-layout4-core-c0-post-20261012-prepの最終post-save/owners/root-closedを優先。

今回開始準備のforeground4失敗を保全：
1. functions.exec guard限定置換対象のcomma-space不一致。nestedtools/process/書込み0。
2. analysis basename参照expected4/actual3の限定チェック拒否。nestedtools/process/書込み0。最終sourceは3個の別contextを限定置換。
3. combined writerがWindows CreateProcessAsUserW206（コマンド長）でSpawnChild前拒否。nested tool1/子process0/書込み0。同巨大command再試行0、小分けの初process書込みだけ実施。
4. owner照合scriptがsessionで未完了の間にprepareへ進み、owners-at-start.json未保存でFileNotFoundError/exit1。Git/モデル開始0、元prepare.pyとselected trace/source pinを保持。owner照合完了後、別prepare-continuation.pyで未実施のprepare/Git preflightを初実行。元prepare再実行0。

元script・各失敗metadataをMAINに保持し、これらをinstrumented helper/model/CI/native/Sol容量failureへしない。foreground fullcreation/全process stdout-stderr None、selected traceのみ。現在model/analysis2helperはpassed、文書前141helpers原11failed130passed/full saved creation-start_token/live-execution一致/CIM同original不在/repo helpercriticalなし。過去の全failed・Git timeout/unknown commit return・lsremote128・各metadata continuation・外部固定容量超過を保持。

117science-source/旧98root count-byte-closurepin/外部固定C1 MAIN35file容量false/旧C2 cache補足不変。新書込み前script/失敗/closure件数bytes確認、metadata512KiB32entry/reserve128KiB/single128KiB/recursive/Python-B/対象文字列限定/hash-seed無限定置換0。閉鎖・外部固定root追記/原raw整理削除移動/上限緩和0。CIMdecimal100ns→microsecond truncation/fulltoken/PID単独0/native回収claim0。selectedCLIを全helperstdioにしない。

## Git承認と次unit

リスク通知後の人の明示継続承認範囲で、同GitHub https://github.com/tyaro/banto-ai.git へ同種合成dev結果・ユーザー名を含むPC内入力pathを記載したreport/current-handoff2を一回[skip ci] commit/push。原Git/API返値・HEAD/upstream/remote ref/clean/docpinsをPOST保存。後追い文書再commit0。Git512KiB16entry/stdout1MiB/累積30秒/preflight別量を維持。

次unitは同保存chunk004/dev seed/layout4/coreをC1 c1-phase-level、新ID dev-layout4-core-c1-20261012で1cell実評価。manifest54f/同core input10pinsを維持。quality pairは保存metadata10pinsだけ/観測本文未読。元payload書込み・生成・replay0/完成C0及び旧24cell反復0。

engineering900秒/2GiB private/output1GiB/single32MiB/files32 checkpointはblocking計算中断/full loaded runtime閉包/allwriter-global-native容量証明ではない。automation詳細結果・PC内path転記/設定更新0、文書参照短指示ACTIVE維持。CI381385/4130success独立verifier保存維持、新query-download-verifier0/doc-onlyCI追跡0。旧381365/a54961最後in_progressは履歴のまま、CI成功≠model性能/native/正式受入。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/create_native早期拒否/全7役reader実起動禁止/元caps-unknown原owner-stop/追加agent禁止。未完了formal/native全証明を少量dev開始条件に戻さない。Sol容量又は人の停止では保全後PAUSED・重複再試行0。
