# 第2dev seed・layout4 quality-stressの3候補とcore比較（2026-10-13）

同じ保存済み合成dev quality-stressをC0+C1、次にC2の順次CLIでfresh compute。人の3候補集約許可に従い、既存CLI2候補上限を維持して解析・文書・Gitを1単位にまとめた。処理successを性能保証・勝者採択・正式受入へしない。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-04-quality-stress。元生成C0と評価C0/C1/C2を別fieldに保存。同seed7466813550306735603/layout4のquality-stress、独立した新seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\016\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "45d694bc6600878955dad80cb3ae87fb8333647a839758c7c10ea87af8052c24"}。候補3つinput10全pin一致→各CLI新snapshot/fresh fit/calibration。元payload書込み・生成・replay0。
- checkout bb7c1be15641eacef2b8a76827591867cf60d388 / 計算661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/candidatecompiled不変。Python3.14.0 Windows AMD64。
- 閾値C0 4/C1C2 6/operator>/persistence2/GT/matching不変。全原thresholdflag照合。宣言pin≠full loaded runtime/native認証。

|CLI group|run|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout4-quality-c0-c1-20261013|32.465041199931875|151670784|
|c2-phase-conditional|dev-seed7466813550306735603-layout4-quality-c2-20261013|28.042759699979797|214605824|

2CLI exit0/complete/成功cell2と1。実CLI時間合計 60.50780089991167秒。単候補との速度比較の再実行0・速度向上倍率は推定しない。

## 同一入力の原結果

|候補|machine|sensor|precision|clean / unmatched|source / equipment|available / unavailable|delay count / mean / median|
|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/2|1 / 2|2 / 2|13880 / 520|0 / None / None|
|c1-phase-level|10/10|9/10|19/19|0 / 0|29 / 19|13880 / 520|19 / 1.5263157894736843 / 2.0|
|c2-phase-conditional|10/10|9/10|19/19|0 / 0|43 / 19|13760 / 640|19 / 1.5263157894736843 / 2.0|

C1/C2の検出19だけ機械10各2秒/sensor9各1秒、min1/max2/mean1.5263157894736843/median2秒。唯一未検出delaynull保持。C0全20未検出delaynull/count0・minmaxmeanmediannull。C1/C2の検出指標一致は全score/episode一致や勝者の証明ではない（source29対43）。
全14400score/48calibrated/calibration各290。C0 fit0各、C1/C2 fit600各、C2のみC2state48。18000input-mask行対応nonok30。全不能score/residualnull・thresholdfalse。
C0/C1排他的phase480/currentquality30/previousquality10＝520。C2はpeer120追加で640、温度quality不能40sampleにmotor_current/conveyor_speed/vibration各40peer不能。原sample集合一致とphase overlap0を保存。非排他的tagsを独立行として加算しない。

## cycle09温度の未検出

sensor spike[8947,8950)、matching window8947–8953。先頭8947は全候補利用可/閾値超過/streak1。その後8948–8950 current quality不能でreset、8951 previous quality不能、8952–8953閾値未満/streak0。3利用可4不能/maxstreak1でpersistence2不成立、candidate0/no_candidate_in_window/causalfalse/matchednull/delaynull。

|sample|C0 score|C1 score|C2 score|reason|
|---|---|---|---|---|
|8947|164.98820228649342|190.68577818895042|195.98165875781154|None|
|8948|None|None|None|current_target_quality|
|8949|None|None|None|current_target_quality|
|8950|None|None|None|current_target_quality|
|8951|None|None|None|previous_target_quality_or_nonfinite|
|8952|0.5159024445618668|1.011068373806973|1.0382108803894223|None|
|8953|0.18857846319206129|1.1937856835350873|1.3497434306757459|None|

原3候補event/incident/対象7行を-save/cycle09-sensor-missへ保存。欠測なし等の反実仮想再compute0、GT/閾値/persistence/matching変更0。

## C0その他の未検出と警報

全20対象窓maxstreak1。機械10窓は6利用可/phase不能1、sensor9窓7全利用可・cycle09は上記3利用可4不能。19件candidate0/no_candidate_in_window、cycle09machine1件candidate1/first_candidate_no_target_onset。motor_current対象onsetなし/vibration-only equipment、delaynull保持。
clean温度onset7712とgrace振動onset8944の未対応equipment2/source2。clean1とunmatched2を別に保存。burden2/20原10.0・clean_rate1/3365原8.558692421991084・effective3255秒rate8.847926267281107を単純確率へしない。
C0一次差分とpersistence2の現設定では対象窓の連続超過が成立していない。欠測1窓だけで全20missを説明しない。実入力対応・保存・状態分類の不具合は観測なし、全用途不適合や包括的実装認証へしない。

## coreとの保存指標比較

|候補|core machine / sensor / clean|quality machine / sensor / clean|不能増|
|---|---|---|---|
|c0-diff-control|0/10 / 0/10 / 1|0/10 / 0/10 / 1|40|
|c1-phase-level|10/10 / 10/10 / 0|10/10 / 9/10 / 0|40|
|c2-phase-conditional|10/10 / 10/10 / 0|10/10 / 9/10 / 0|160|

core旧3cellはmanifest/config指標のみ参照・再compute0、同seed/layout別stratum。観測quality等のinput pinは異なるため欠測だけの反実仮想全差証明へしない。layout4全6cell比較完成。第1seed72＋第2seed30＝102boardcells/使用seed2、102独立datasetではない。bootstrap/統計CI/勝者採択0。

## 記録・次工程・正式状態

- 新 representative-seed2-layout4-quality-three-candidates-20261013-records/analysis/save/final。原全ledger/score窓/不能行/episodesとsource support/検出class別delay/未検出windowを保存。DATA2閉鎖 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout4-quality-c0-c1-20261013": {"bytes": 41896654, "files": 22, "manifest_pin": {"bytes": 2592, "sha256": "ba2143ce9187c2b54da6e37f2ec468ac5508c2ad5d608c53e82748272576e26b"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout4-quality-c2-20261013": {"bytes": 38240375, "files": 19, "manifest_pin": {"bytes": 2255, "sha256": "8d48ad7e7b6cd6aff20c24643d8a98c357cb4841cb9c1710418ff2398468163a"}}}。
- 旧498root/447helpers24failed423passedmissingexecution1と全旧失敗/原誤記/審査拒否保全、閉鎖root追記0。今回新helperfailure0。fullstdio/PID単独/native回収claim0。
- report/handoff/index3docs一回[skip ci] commit/push、prepare_result_index実使用。人の具体的通知後の同送信先・同種合成dev結果とユーザー名入りPC内path送信の継続承認を保持。
- 次同seed/layout5 core。保存chunk017 manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\017\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "16c4319322e2e6ecc5228c513240d1a935cb1047e2bf15c78c3f83741e501746"}、identity/input10metadataのみ選択・本文未読・model0。groups [["c0-diff-control", "c1-phase-level"], ["c2-phase-conditional"]] / IDs ["dev-seed7466813550306735603-layout5-core-c0-c1-20261013", "dev-seed7466813550306735603-layout5-core-c2-20261013"]。
- EvidenceStore全writepreflight/自動分割/失敗閉鎖reserve維持。実行900秒2GiBoutput1GiBsingle32MiBfiles32、Git30秒16entry512KiBstdout1MiBstderr128KiB/nativeprotocol caps維持。checkpoint≠blocking中断/fullruntime/allwriter/global容量認証。
- ACTIVE/automation詳細転記0/新testCIagent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。Sol容量人停止は保全後PAUSED。
