# 第2dev seed・layout4 coreのC0/C1/C2比較（2026-10-13）

同じ保存済み合成dev入力を3候補でfresh compute。人の「C0/C1/C2合わせてテストしたほうが効率いいなら合わせて大丈夫」に従い、既存CLIの2候補上限を維持してC0+C1、次にC2を順次実行し、解析・文書・Git保存を1単位へ集約した。

## 入力と実行

- dataset anomaly-v03-dev-seed-7466813550306735603-layout-04-core / seed7466813550306735603/layout4/core。同seedの追加layoutで、新独立seedではない。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\016\attempt-0001\result\payload\manifest.json / {"bytes": 75699, "sha256": "45d694bc6600878955dad80cb3ae87fb8333647a839758c7c10ea87af8052c24"}。3候補input10全pin一致、各CLIは新snapshotとfresh calibration/fit。元payload書込み・生成・replay0。
- checkout 4b7cd931fd60179df1d2d2ea7756eb9a50188d0d / 計算code661b27511826fcc87cb4a02930f276afbb8f95d9/source117/calculator16/configs不変。Python3.14.0 Windows AMD64。
- CLI exit0/complete/成功cell2と1は処理状態。性能合格・候補採択・正式受入を意味しない。
- C0 threshold4、C1/C2 threshold6、operator >、persistence2、GT/matching科学不変。全原thresholdflag照合。宣言source pinはfull loaded runtime/native認証ではない。

|CLI group|run ID|elapsed秒|sampled private peak B|
|---|---|---|---|
|c0-diff-control,c1-phase-level|dev-seed7466813550306735603-layout4-core-c0-c1-20261013|32.102043199935|151531520|
|c2-phase-conditional|dev-seed7466813550306735603-layout4-core-c2-20261013|27.422111100051552|210632704|

実CLI時間合計 59.52415429998655秒。単候補との速度比較のための再実行はしていないため、速度向上倍率は推定しない。共有入力チェックと保存作業を集約した。

## 同一入力の原結果

|候補|machine|sensor|precision|clean|unmatched equipment|source / equipment|delay count / mean / median|
|---|---|---|---|---|---|---|---|
|c0-diff-control|0/10|0/10|0/2|1|2|2 / 2|0 / None / None|
|c1-phase-level|10/10|10/10|20/20|0|0|30 / 20|20 / 1.5 / 1.5|
|c2-phase-conditional|10/10|10/10|20/20|0|0|45 / 20|20 / 1.5 / 1.5|

全候補14400scores/利用可13920/不能480（全mode_recipe_or_phase）。全不能score/residual null・thresholdfalse。18000input-mask行対応/nonok0、全48profile calibrated/calibration各290、C0 fit0各・C1/C2 fit600各、C2state48のみC2。
C1/C2の検出20件は機械各2秒、sensor各1秒。delay min1/max2/meanmedian1.5秒。C0全20未検出delaynullを保持し、delay count0/原minmaxmeanmediannull。C1/C2の集計一致は全score/episode一致・勝者の証明ではない（source30対45）。

## C0の未検出と未対応警報

全20対象窓のmax streak1で固定persistence2不成立。機械10窓は6利用可/phase不能1、sensor10窓は7全利用可。原19件no_candidate_in_window/candidate0、cycle09機械1件first_candidate_no_target_onset/candidate1。後者はmotor-01.vibration_featureだけのepisodeで対象motor_currentのonsetなし、causalfalse/matchednull/delaynull。
cycle09 motor_current:8940phase不能→8941 score0.13885628375756548/streak0→8942 score0.022034297648448883/0→8943 score55.34102834697611/1→8944 score1.7369218667118582/0。振動8943–8944のsupport2でepisode成立しても、対象検出へ読み替えない。原event/incident/対象窓/選択equipment/sourceと全source supportを保存。
未対応equipment2はclean1（conveyor-01.motor_temperature onset7712）とgrace1（motor-01.vibration_feature onset8944）。clean1とunmatched2を別々に保持。burden2/20原10.0、clean_rate1/3365原8.558692421991084、effective3255秒rate8.847926267281107を単純確率へしない。
保存済みC0解釈を維持：一次差分は変化端に反応しやすく、連続超過を要求する現設定でこの異常形状を捉えにくい。今回の実入力対応・保存・状態分類の不具合は観測なし。全用途不適合・実装誤りなしの包括証明や、閾値調整による成功の補完はしていない。

## 記録と次工程

- 原profiles/scores/events/incidents/episodes/metricsは各新DATA。全20ledger/対象窓/不能行/全episodesは-analysis、全source support/検出class別delay/唯一C0選択candidateは-save/target-episode-support。
- DATA閉鎖 {"D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout4-core-c0-c1-20261013": {"bytes": 41014881, "files": 22, "manifest_pin": {"bytes": 2582, "sha256": "083051b5e64d2cd465c39a2a3c5cf511e9ce148df3e675a530a7ca7a2524ceb9"}}, "D:\\develop\\banto-ai\\artifacts\\representative-anomaly-evaluation\\dev-seed7466813550306735603-layout4-core-c2-20261013": {"bytes": 37793128, "files": 19, "manifest_pin": {"bytes": 2245, "sha256": "fcf983c01221520ecd51015e6c16ff3c175f486297db90030a0fa7f0539c92c6"}}}。
- 旧96cellは保存manifest/config指標だけ比較、モデル再実行0。第1seed72＋第2seed27＝99boardcells/使用seed2。99独立datasetではない。今回新しい保存入力条件1つを候補3つで比較。
- 原model-summaryのone_independent_dataset=TrueはCLI群が同じ入力条件を共有する意図のmetadata。統計的独立datasetの認証へしない。new_saved_input_conditions1/new_independent_seeds0として限定した。
- 旧492root/443helpers24failed419passed/元execution欠損1と全失敗・審査拒否・原誤記保全。新records/analysis/save/finalを優先、閉鎖root追記0。
- report/handoff/index3docsを同種合成dev結果・ユーザー名入りPC内pathの継続送信承認範囲で一回[skip ci] commit/push。元Git stdout/stderr/exitを判定前に保存。索引はprepare_result_index実使用。
- 次同seed/layout4 quality-stress、C0+C1とC2の2CLIを1単位へ集約。新run IDs ["dev-seed7466813550306735603-layout4-quality-c0-c1-20261013", "dev-seed7466813550306735603-layout4-quality-c2-20261013"]。元manifest/input10 identity metadataのみ選択、次観測本文未読・次model0。
- EvidenceStore全writepreflight/自動part分割/失敗閉鎖reserve維持。実行900秒/2GiB/output1GiB/single32MiB/files32、Git30秒/16entry/512KiB/stdout1MiB/stderr128KiBを維持。checkpointはblocking中断/full runtime/global/allwriter容量証明ではない。
- ACTIVE/automation詳細転記0、新tests/CIquery-download-verifier/追加agent0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件最終受入未完了/create_native早期拒否/全7役reader禁止/元capsunknown owner保持。bootstrap/統計CI/勝者/採択0。Sol容量または人の停止は保全後PAUSED。
