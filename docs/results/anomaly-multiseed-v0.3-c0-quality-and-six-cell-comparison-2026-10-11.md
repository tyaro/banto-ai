# v0.3 C0 quality-stress実評価と3候補×2条件の保存比較 — 2026-10-11

## 文書保存の現在状態

**送信リスク通知後の明示承認を受領。** 2026-10-11、人が具体的なC0合成dev評価結果・ユーザー名を含むPC内入力path・2文書・ https://github.com/tyaro/banto-ai.git への送信、および今後の同送信先への同種の合成dev報告の送信を明記した依頼へ「承認します」と回答した。今回の承認待ちは解除した。先行の自動承認審査2回拒否と元Git helper未起動は閉鎖root representative-c0-quality-approved-save-20261011-prep に保持する。新専用 representative-c0-quality-export-approved-save-20261011-prep で指定2文書を一回[skip ci] commit/pushする。保存前の現在時点はGit未実行、保存後の原Git返値・doc-save・owner照合を同新rootで優先する。

先行の明示承認対象だったC2報告と引継ぎ文書は、commit `6549c0ee424cb7df028a6b6af5915907d57799b2` として https://github.com/tyaro/banto-ai.git へ [skip ci] で一回commit/push済み。原Git返値でHEAD/upstream/ls-remote一致・cleanを確認した。原Git保存は artifacts/representative-c2-quality-approved-save-20261011-prep に閉鎖保存済み。

**今後のGit操作・pushと同種の合成dev報告のGitHub送信を承認済み。** 先行の「gitへの操作は今後も承認します」「pushも承認します」に加え、今回の送信リスク通知後の「承認します」を記録した。同じ送信先 https://github.com/tyaro/banto-ai.git への合成dev評価結果・PC内入力pathを含む同種報告について、毎回の確認は求めない。自動審査拒否・過去の閉鎖rootは履歴として保全する。

## 実行と結果

同じ保存済みfirst dev seed `2486912926863618161` / layout `0` / quality-stressを、既存CLI `tools/evaluator/run_representative_anomaly.py` の `c0-diff-control` で1件実compute_evaluationした。原10input file pins照合、新input snapshot、fresh fit/calibration、原profile/score/episode/incident/metrics保存。新dataset生成・元payload書込み・追加replay・production/test変更・類似owner追加・追加agent起動/再活性化は各0。

```text
C:/Python314/python.exe tools/evaluator/run_representative_anomaly.py
  --input-manifest C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/000/attempt-0001/result/payload/manifest.json
  --manifest-sha256 05ef05b07193af83eea6946051628fb910b6c02ee8bf386a84957d2a3cf5e1bf
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-00-quality-stress
  --candidate c0-diff-control
  --output artifacts/representative-anomaly-evaluation/dev-quality-c0-20261011
```

CLI exit0 / run complete / 1cell success。機械0/10、sensor0/10、precision0/3、clean誤警報3。3source episode / 3equipment episode / 20incident / 40event。48profile calibrated、calibration各290、14400scoreの利用可能13880・不能520。全20incidentは原 `no_candidate_in_window` / candidate0 / causal_detected=false / matched=None / delay=null。検出delay count0、median/mean/min/maxは原null。処理successを性能合格や採択へしない。

原clean_rateは3/3365でvalue25.676077265973255、effective_clean_seconds3255/effective_clean_rate26.543778801843317。false_alert_burdenは3/20/value15.0。3episodeはmotor-01 vibration startupのsample7242・8517、conveyor-01 temperature cooldownの7712で、各原context_tags=[clean] / matched_event_id=null。誤警報件数と時間分母を別に保存し、単純な確率へ読み替えない。

実checkoutは承認後の文書版 `6549c0ee424cb7df028a6b6af5915907d57799b2`、production/test計算code `661b27511826fcc87cb4a02930f276afbb8f95d9` 不変。actual CPython3.14.0 / Windows / AMD64。elapsed 17.779066500021145秒、checkpoint OSpeak private 146161664B。engineering900秒/2GiB/output1GiB/single32MiB/files32を維持し、blocking計算の中断や全writer/native容量証明へしない。

## 保存済み6cellの比較

今回以外の5cellは保存manifest指標だけ読み、元モデルを再計算していない。quality-stressの3候補は同じ10input pins、全6cellは同じ宣言16calculator source pins・candidate config・compiled config。条件ごとの設定candidates listやidentityは各runとして保持する。

| 条件 | 候補 | 機械検出 | sensor検出 | precision | clean誤警報 | 利用可能/全score | 検出delay中央値 |
|---|---|---:|---:|---:|---:|---:|---:|
| core | C0 | 0/10 | 0/10 | 0/3 | 3 | 13920/14400 | null |
| core | C1 | 10/10 | 10/10 | 20/20 | 0 | 13920/14400 | 1.5秒 |
| core | C2 | 4/10 | 10/10 | 14/20 | 0 | 13920/14400 | 1.0秒 |
| quality-stress | C0 | 0/10 | 0/10 | 0/3 | 3 | 13880/14400 | null |
| quality-stress | C1 | 10/10 | 9/10 | 19/19 | 0 | 13880/14400 | 2.0秒 |
| quality-stress | C2 | 4/10 | 9/10 | 13/19 | 0 | 13760/14400 | 1.0秒 |

同じ合成devの1seed/layoutのcore/quality pairを3候補で評価した比較であり、6独立datasetではない。初回の明示replay2cellも独立dataset数へ加算しない。この保存pairではC1の機械検出が10/10、C2が4/10、C0が0/10。C1/C2はquality-stressでsensorが10/10から9/10へ減少した。C0は両条件で検出0/10・clean誤警報3。bootstrap/統計CI/候補採択/勝者宣言は実施していない。

## 欠測と未検出の原対応

quality-mask欠測30観測行。排他的primary不能はmode_recipe_or_phase480、current_target_quality30、previous_target_quality_or_nonfinite10で合計520。非排他的tagsはphase480/current quality30/current nonfinite30/previous quality30で重複するため独立行へ加算しない。全不能score/residualは原null、threshold_exceeded=false。温度の追加40不能はC0/C1に共通、C2では同motorの他3信号各40peer不能も加わり合計640。今回C0では他信号のpeer除外は発生していない。

sensor cycle09/sample8827の温度scoreは143.3797607427507で閾値6超過・streak1。8828–8830 current欠測、8831 previous欠測でreset、8832 score0.29384988466414763で閾値未満。固定persistence2でepisode不成立。motor_current/speed/vibrationはこの欠測期間にも利用可能で、C2のpeer除外とは状態が異なる。

欠測のないsensor cycle01の原target windowも保存した。score/streak列は `[(7387, 144.1168344306277, 1), (7388, 0.8382586606863115, 0), (7389, 0.4866238418421488, 0), (7390, 146.17946306719261, 1), (7391, 0.8917090432694901, 0), (7392, 0.4263217781185114, 0)]`。このwindowにも候補episodeはなく、原matching=no_candidate_in_window。欠測1件だけでC0の全20未検出を説明しない。全20のevent/incidentと3episode、cycle01 machine/sensor target window、cycle09全motor target windowをmetadataへ保持した。閾値・persistence・matching・GT・科学式を変更して検出を補わない。入力対応・保存・状態分類の実経路不具合は観測なし。

## 原保存pinsと閉鎖

| 対象 | bytes | SHA256 |
|---|---:|---|
| 観測 | 9600624 | 7965d24417c902ba23565227b3b57adec0704ea456a458c0a380630dcb83057e |
| configuration | 5513 | 288952068561f45aaa10d38ac60d5e01093d4dd1507a20a5fe8aad59adc56919 |
| manifest | 8057 | 15db2aeafb313691c8601220d3950580fa30ad7a16d543c5414700b16a9950ac |
| evaluation | 14336389 | 718d1efc42922e5b96c117c839c8a66b3a71b3450e650c64a16cf9bdd1f44c22 |
| numerical | 14330791 | db28018914a18d150d6907222f4635121d504e05b11fc39e1022df6eb12b5446 |

data artifacts/representative-anomaly-evaluation/dev-quality-c0-20261011 は閉鎖19file27383348B/root-closed2228B/d64c4e7ac55e2e90bcf9cf3b134bf75dc1f73db7d40733495286fc3c3b292edd。新metadata artifacts/representative-c0-quality-20261011-prep と post専用rootの最終post-save/owners-after-save/root-closedを優先。各metadata512KiB32entry/reserve128KiB/single128KiB。旧16root count-byte-closure pin不変、117science-source不変。declared16/Git pinsはfull loaded runtime/native閉包の証明ではない。selected CLI/metadataはhelper全process stdioではなく、foreground docs編集/閉鎖のfull creation identity/full stdioはNone。

原76helperからC0評価・解析の2helperを追加し、文書前78helper full saved creation-start_token/live-execution一致、CIM同original不在、原7failed71passedを保持。新2helperはpassed。PID単独/native回収claim0。旧完成CI38138556456/4130は再照会/download/verifier0、旧381365/a54961は最後in_progressの履歴のまま、doc-only新CI追跡0。

## 次工程と正式gate

次の保存済みdev pairをmetadataだけで特定済み。元chunk000 manifestには完成first pairの2datasetだけがあり、別pairも含むと仮定したforeground selectorはAssertionError/exit1、model/観測body読取り/Git変更0。原script/selected tool traceを保持し再実行しない。未読のsibling chunk001 manifestを一度だけ読んだ別metadata continuationで、同dev seed2486912926863618161/layout1のcore・quality pairを選択した。manifest75699B/72e5a34c662f77c4728583b9e61cc9d2977edd2ecc9e5286194aae0d2c055dbf、次dataset anomaly-v03-dev-seed-2486912926863618161-layout-01-core/candidate C0。新seedではなくlayout差、観測body未読/新評価0/生成0/元payload書込み0/holdout観測未読。Git送信の明示承認が得られた後に、新metadata rootでまず文書保存し、clean checkoutからこのC0 core一件へ進む。

今回のfirst dev pair比較は完了した。追加engineering評価では次の保存済みdev pairをmanifest metadataで特定し、新ID/1cellずつC0 coreから進める。元5cell・今回C0・明示replay・旧4risk tests・類似owner/native/probe/collector/Git37・完成CIを反復しない。文書差分が残る間はclean checkout必須のCLIを起動しない。Git保存は新専用metadata rootを使い、今回の閉鎖rootへ追加しない。

formal gate=s4_acceptance_not_frozen / formal_permission=false / credit0 / holdout観測未読 / 正式5残件・最終受入未完了。create_native早期拒否・全7役whole.run限定reader実起動禁止・元caps/unknown原owner-stop・追加agent禁止を維持。ACTIVEを維持し、継続承認済みのGit操作・pushについて毎回の確認を求めない。Sol容量エラー又は人の停止割込みでは保全後PAUSED・重複再試行なし。
