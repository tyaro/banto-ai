# v0.3 C2 quality-stress実評価と欠測のpeer波及 — 2026-10-11

## 文書保存の現在状態

評価・CI証拠とこの文書はローカル保存済み。2026-10-11、人の「承認します」により、今回の評価結果・ローカル入力pathを含むこの報告と docs/current-handoff.md を `https://github.com/tyaro/banto-ai.git` へ [skip ci] でcommit/pushする明示承認を受領した。承認待ちは解除した。先行の自動承認審査2回拒否と、その時点のGit helper起動・commit・push0は履歴として保持する。承認後の原Git返値と保存結果は新専用 artifacts/representative-c2-quality-approved-save-20261011-prep に保存し、過去の閉鎖rootへ追加しない。

## 今回の範囲と実行

人の「進めてください」に従い、保存済みfirst dev seed `2486912926863618161` / layout `0` / quality-stressを既存CLIのC2で1件実計算した。入力10fileをpin照合し、新runへsnapshotした後、fresh fit/calibration、scores、source/equipment episodes、matching、metricsの原結果を保存した。新dataset生成、元payload書込み、追加replay、production/test変更、類似owner test追加は各0。完成したC0/C1/C2 core、C1 quality、明示replay、旧4risk tests、旧native/probe/collector/Git37は再実行していない。

```text
C:/Python314/python.exe tools/evaluator/run_representative_anomaly.py
  --input-manifest C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/000/attempt-0001/result/payload/manifest.json
  --manifest-sha256 05ef05b07193af83eea6946051628fb910b6c02ee8bf386a84957d2a3cf5e1bf
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-00-quality-stress
  --candidate c2-phase-conditional
  --output artifacts/representative-anomaly-evaluation/dev-quality-c2-20261011
```

helperはCLIの実mainを同processで一回呼び、原CLI stdout/stderrを判定前に保存した。CLI exit0、run `complete`、1cell `success`。処理完了を性能合格や候補採択へ読み替えない。原payload manifestのdataset identityには元生成時のcandidate `c0-diff-control`が含まれるが、今回の計算candidateはcell・configuration・evaluationへ `c2-phase-conditional`として別に保存されている。元入力identityを変更していない。

## 保存指標の比較

比較元は完成runのmanifest指標だけを読んだ。同じ10input file pins、宣言計算16source bytes、C2 coreとの固定candidate/compiled config一致を確認した。元モデル再計算は0。同じseed/layoutの候補・stratum比較であり、独立した3dataset評価とは数えない。

| 保存cell | 機械異常 | sensor異常 | precision | clean誤警報 | score利用可能 / 不能 |
|---|---:|---:|---:|---:|---:|
| C2 core | 4/10 | 10/10 | 14/20 | 0 | 13,920 / 480 |
| C1 quality-stress | 10/10 | 9/10 | 19/19 | 0 | 13,880 / 520 |
| **今回C2 quality-stress** | **4/10** | **9/10** | **13/19** | **0** | **13,760 / 640** |

今回48profileは全てcalibrated、calibration samplesは各290。14,400score、39source episodes、19equipment episodes、20incidentsを原保存した。未対応equipment episodeは6で、`false_alert_burden`は原numerator6 / denominator20 / value30.0。これらはmachine異常窓内なのでclean誤警報0とは別の指標である。

検出した13件だけのdelayは中央値1秒、平均1.3076923076923077秒、最小1秒、最大2秒。未検出7件のdelayは原nullのままで、補完や検出件数への追加はない。合成dev1seed/layout0の限定観測で、bootstrap、統計的信頼区間推定、勝者判定、候補採択は0。

## 欠測が他の信号へ波及した原結果

quality-mask欠測は30観測行。不能640scoreの排他的primary reasonは以下だった。

| primary reason | score行数 |
|---|---:|
| mode_recipe_or_phase | 480 |
| peer_quality_or_nonfinite | 120 |
| current_target_quality | 30 |
| previous_target_quality_or_nonfinite | 10 |

motor-01の温度欠測により、温度自身がcurrent30＋previous10の40score不能となる。C2はpeer入力にも依存するため、同equipmentのmotor_current、conveyor_speed、vibration_featureも各40score不能となった。C2 coreとの差160のうち120がこのpeer波及であり、C1 qualityとの差も120。conveyor-01の各targetはphase等の60行だけで、今回の温度欠測のpeer除外はない。

非排他的tagsはphase480 / peer120 / current quality30 / current nonfinite30 / previous quality30である。タグは重なるため独立行数へ加算しない。全不能score/residualは原null、threshold_exceededはfalseで、不能を正常数値や成功検出へ補っていない。

## 未検出7件の対応

機械6件はcycle01/03/05/06/08/09で、全て `first_candidate_no_target_onset`。今回の原選択equipment episodeにはvibration_feature source episodeだけがあり、異常対象motor_currentのonsetはない。C2 coreと同じ固定 `first-equipment-onset-no-retry-v1` のmatchingでcausal_detected=false、matched_episode_id=null、delay=nullとなった。原event/incident/window scores/選択source・equipment episodeをanalysis.jsonへ抽出保存した。

追加のsensor未検出はcycle09 / motor-01.motor_temperature / spike。sample8827では温度score195.37278851156927、current11.285439511980204、vibration7.016905124006623が閾値6を超えたが、いずれもstreak1。8828–8830では温度current欠測、他3targetはpeer除外、8831では温度previous欠測と他3targetのpeer除外が続き、streakは0にresetされる。8832で温度score0.07764945127889936となり、persistence2のepisodeは成立しなかった。原incidentはcandidate_count0 / `no_candidate_in_window` / causal_detected=false / delay=null。C1 qualityのsensor未検出と同じeventである。閾値、persistence、matching、GT、科学式を変えて成功へ補っていない。

入力対応、結果保存、状態分類の実経路不具合は今回観測していない。peer欠測除外と未検出は原計算結果として保持する。

## 実行対応・資源と原pin

実checkoutは文書版 `c7a3cb6df57bdd5c46b042087de2a917ea21d05d`。production/test code `661b27511826fcc87cb4a02930f276afbb8f95d9`、117working source-scienceと宣言16calculator source bytesは不変。Git working literal又は明示CRLF一致の宣言source照合であり、full loaded runtime/native閉包の認証ではない。

実Pythonは3.14.0 / Windows / AMD64 / C:/Python314/python.exe。elapsedは41.15029919997323秒、checkpoint OSpeak privateは207,228,928B。既存engineering900秒 / 2GiB / output1GiB / single32MiB / files32のcheckpoint上限を維持する。blocking計算中断、全writer同時保持、全経路wall、global coupled memory/native容量の全証明ではない。

| 原file | bytes / SHA256 |
|---|---|
| observations | 9600624B / `7965d24417c902ba23565227b3b57adec0704ea456a458c0a380630dcb83057e` |
| configuration | 5518B / `3c8a3034a2798a08463ba4d94c0e5f4616f04ca48e15b286037bbfdc35e39c3a` |
| manifest | 8062B / `ef6829dbb07862056362ec19dc3934e5d94de6fc2c50fedc755a44d1e4751286` |
| evaluation | 25187507B / `12d2471dd71263192b5a99ecacf497e7829a1686f902192dd5e1d781ce83e047` |
| numerical | 25181909B / `0d7709daa8849cd35b100056fea8cb5521262ebb79ecbdad32e39b5646d5e698` |

data root `artifacts/representative-anomaly-evaluation/dev-quality-c2-20261011` は19file / 38,234,488Bで閉鎖。root-closed.jsonは 2224B / `7e9a42390e962f9e9dc3b47de2fc0692bed087f16ca7d84f48a08b50d79702ab`。追加、同保存、今回モデル再実行を禁止する。

## 現在コードCIの終端保存

run `38138556456` / fullHEAD `661b27511826fcc87cb4a02930f276afbb8f95d9` / attempt1 / push / Phase 1 CI / workflow349172377 / .github/workflows/ci.ymlをcompact一回でcompleted-successへ固定した。元run rawはMAINに保持し、CI rootへ再取得・copyしていない。未保存jobs/artifacts/2logs/2ZIPを各一度取得し、原stdout/stderr/exitを判定前保存した。job114467417613 test(3.14)、job114473705188 verify-python314-journalは両completed-success。

原journalは4,246,566B / `916a859779381766be7ab06aa6b5bc6b7387b0882cfda05b12a4a51ed258e645`、remote verificationは37,192B / `8072d8a9cef61dcc07c0cfe110eaa0355d87613d75c95ec7ae82ea17f143fd59`。両ZIPは単一member / decoded8MiB以内 / artifact digest一致。ZIPdigestはrunner image digestではない。

現独立3.14 verifierをexternal fullHEAD / workflow SHA256 `71f0e56eb9b0bb11a6e181e860a64ba45a6a4004cde7d4a5bf35d2b42cbf65a7` / run / attemptへ一回結び、exit0 / passed。**実summary取得後**にdiscovered/tests_run4,130 / failure0 / error0 / skip237（Windows native213、non-S4 optional24）/ source_unchanged=true / shared29complete / 必須28passedを固定した。算術予定から実件数を作っていない。cross_python_comparison_performed=false。

実Ubuntu24.04 / x86_64 / GCC13.3.0 / kernel6.17.0-1022-azure / Python3.14.8 / SOABIcpython-314-x86_64-linux-gnu / runner20261004.327.1。image digest未取得、runner候補未採択。CLI7は実行前working-Git pinを保存、6exactとskip IDsの既知CRLFだけ。local37,193Bとremote37,192Bは末尾CRLF/LF差1byteでraw_equal=false、JSON全field一致、CRLF-only=trueを両rawで保持した。verification-saveは4,054B / `916022678e136163ff74dbee3765386f41b4397f29baf3554cabf806b8f735b2`。

この4,130件は当該661b source/runの単一CI保存であり、実Windows native、モデル性能合格、正式S4、旧local複数source-run/旧CI/過去failedへ読み替えない。完成381349/4112、379685/4097、379656/4081success、379634/4081failure、379582/4062failure等の旧CIは再照会・download・verifier0。旧38136585791/a54961は最後in_progressの履歴で今回query0、終端を補っていない。doc-only新CI追跡0。

## 保全・次工程

開始元69helper、文書保存前元74helperはfull saved creation-start_token/live-execution一致、read-only CIMで同original不在、元7failedを保持し、repository helper-critical ownerなし。CIM decimal100ns→microsecond truncationで比較し、PID単独やnative回収claimを用いていない。開始foreground Git ignore Permission deniedはexit0のtool excerptで、元foreground full identity/process logsはNone。selected CLI output、CI raw、Git pinsをhelper全process stdout/stderrへ読み替えない。foreground docs編集・root閉鎖のfull process logsもNoneとして記録する。

今回MAIN `representative-c2-quality-20261011-prep`、CIprep `representative-cli-ci-terminal-20261011-prep`、CI raw `ci-diagnostic-38138556456`、POST `representative-c2-quality-post-20261011-prep` は最終post-save/owners-after-save/root-closedを優先する。metadata capsは512KiB / 32entry / reserve128KiB / single128KiB、CI rawは16MiB / 256entry / single8MiB。閉鎖後は追加・同保存・原helper再実行を禁止する。

次の小評価は同じ保存first dev seed/layout0のquality-stressをC0で1件だけ計算し、保存済みcore/qualityの3候補比較を完成する。元payload manifest/path/pinを使用し、新output IDへ一回実CLIを呼ぶ。類似owner/native証明追加を開始条件に戻さず、観測した実経路の不具合だけ補強する。今回完成したC2 quality/CI4130を次heartbeatで再計算・再照会・再download・再verifierしない。

formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / 登録holdout観測未読 / 正式5残件・最終受入未完了を維持する。create_native437B早期拒否、全7役whole.run限定reader実起動禁止、元capsとunknown原owner-stopは保持。追加agent起動・再活性化禁止、人の明示再開によるACTIVEを維持。Sol容量エラー又は人の停止割込みでは保全後PAUSED、重複再試行なし。
