# 保存済みdev coreのC2実評価（2026-10-11）

## 同じ入力での候補比較

人の「進めてください」に従い、保存済みfirst dev seed **2486912926863618161 / layout 0 / core** をC2（phase-conditional）で1件実計算した。新snapshotの10入力file、宣言計算16source、固定candidate config/compiled configが前回C0/C1の保存runと一致することを確認した。C0/C1は保存済みmanifestの指標だけで比較し、再計算していない。

| core候補 | 機械異常検出 | sensor異常検出 | precision | clean誤警報 | 未対応equipment episode |
| --- | --- | --- | --- | --- | --- |
| C0（前回保存結果） | 0/10 | 0/10 | 0/3 | 3 | 3 |
| C1（前回保存結果） | 10/10 | 10/10 | 20/20 | 0 | 0 |
| C2（今回） | **4/10** | **10/10** | **14/20** | **0** | **6** |

C2 CLI exit0/run complete/1cell success。全48profileはcalibrated、各fit samples600・calibration samples290、C2 stateあり48件。fresh fit/calibration → score → episode → matching → metricsを実行し、14,400scoreの利用可能13,920・不能480（mode/recipe/phase）を保存。全不能score/residualはnull、threshold_exceeded=false。source episode42/equipment episode20/incident20。

処理successは性能合格・候補採択ではない。この合成dev 1 seed/layout/coreではC2の機械検出とprecisionがC1より低かった。bootstrap・信頼区間・勝者選択0。検出した14件だけの遅延は中央値1秒・平均1.2857142857142858秒・最小1秒・最大2秒。未検出6件のdelayはnullで補完しない。

## 6件の未検出理由

未検出はmachine eventの **cycle 01・03・05・06・08・09**。全6件の原matching reasonは `first_candidate_no_target_onset`。candidate episodeは存在するが、異常対象 `motor-01.motor_current` のonsetがなく、`motor-01.vibration_feature` のsource episodeだけだった。原incident causal_detected=false/matched_episode_id=null/delay_seconds=null、元equipment episode matched_event_id=nullを保持した。

cycle 01を例に、保存scoreとstreakは次の通り（閾値6、persistence2）。

| sample | motor_current score / streak | vibration_feature score / streak |
| --- | --- | --- |
| 7380 | phase0のため不能 / 0 | phase0のため不能 / 0 |
| 7381 | 5.256894981711751 / 0 | 68.71491266202072 / 1 |
| 7382 | 6.003541081762852 / 1 | 68.77839859506021 / 2、episode成立 |
| 7383 | 2.9396637855330074 / 0 | 0.5994035079233714 / 0 |

currentの連続2行の超過は成立せず、vibrationだけでepisodeが成立した。固定 `first-equipment-onset-no-retry-v1` のmatchingがそのepisodeを選び、対象onsetなしとして未検出を記録した。全6件のevent/incident/選択episode/source episode/window scoresをmetadataへ抽出保存した。GT・閾値・persistence・matching・科学式を変えて検出成功へ補っていない。

未対応6episodeはmachine異常窓内にあり、clean区間の誤警報は0件だった。precision14/20とfalse_alert_burden6/20（原value30.0）も独立に保存する。clean誤警報0だけで全episodeが正しく対応したことにはしない。今回、入力対応・保存・状態分類の実経路の不具合は観測していない。

## 入力・モデル・設定・結果の対応

- run ID: `dev-core-c2-20261011`
- dataset: `anomaly-v03-dev-seed-2486912926863618161-layout-00-core`
- candidate: `c2-phase-conditional`、version0.3。phase-median/shrinkage covariance、固定covariance=0.75*S+0.25*diag(S)、jitterなし、閾値6・persistence2。
- 原payload manifest SHA256: `05ef05b07193af83eea6946051628fb910b6c02ee8bf386a84957d2a3cf5e1bf`
- 観測18,000行: 9600623B / `3bc5708c1650ac975ea7c4bf66eddf660474d3214325b8c76eb5e434a328d091`（C0/C1と同じ10file pins）。
- 実checkout HEAD: `03f846a9184c703b2c032e2982f3dad11c1f93e3`（文書版）。計算sourceはcode `661b27511826fcc87cb4a02930f276afbb8f95d9`から不変。宣言16sourceのworking/Git原bytes又は明示CRLF→LF一致を当該runへ保存。
- configuration: 5508B / `5ed2952af7fa92cb11baac197e850ca8e84c5a8c57b5cf38f9e8f80b0767b3d9`
- run manifest: 8015B / `d70767ce2d8f174804565838011b709b0adced933787124cd5e02ee4285a96c9`
- evaluation JSON: 24748345B / `57faebe906f88c0784ec1e7e8ecd572dd33b0ee687bfd3d923af44cd3e52ffa0`
- numerical pin: 24742847B / `156232f57ee690c6d98ffabefe850f324e799c731ce0990e2de9a837f0e17c9e`
- elapsed **34.01857670000754秒**、checkpoint OS peak private bytes **205426688B**。
- actual runtime: Python3.14.0 / Windows / AMD64 / `C:/Python314/python.exe`。

```powershell
& 'C:/Python314/python.exe' tools/evaluator/run_representative_anomaly.py `
  --input-manifest 'C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/000/attempt-0001/result/payload/manifest.json' `
  --manifest-sha256 05ef05b07193af83eea6946051628fb910b6c02ee8bf386a84957d2a3cf5e1bf `
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-00-core `
  --candidate c2-phase-conditional `
  --output artifacts/representative-anomaly-evaluation/<新しいrun-ID>
```

実行にはclean tracked checkoutと未使用output名が必要。placeholderは説明用。今回replay0・新dataset生成0・元payload書込み0・production/test変更0・旧完成risk/owner test反復0。前回の2候補に今回C2を加えた同一coreの3候補評価で、3独立データ評価として数えない。profile-score-episode-incident-metricsの原JSONを保存し、出力rootは閉鎖19file/37788928B、root-closed2224B/`7ca662f9956ec1f6382742cac9f5e05e23868a73982dc21c4f45b657e9a2278c`。閉鎖後の追加・同保存・同run-ID再実行禁止。

## CIと境界

CI38138556456/fullSHA661b275のcompact APIを今回一度だけ確認。原run/stdio/exit0を判定前に保存し、attempt1/push/Phase1CI/.github/workflows/ci.yml/workflow349172377/**in_progress**へ固定。jobs/終端/journal/countは未観測、待機・反復0。旧38136585791/fulla54961の最後in_progressを履歴として保持し今回は再照会0。完成旧CI・doc-only CI照会0。

原CLI stdout/stderr/exitと元helper creation/start_token/live/execution、117science-source working pins、7旧閉鎖rootのcount-byte-closure pins不変を専用metadataへ保存。metadata rootsは `artifacts/representative-c2-core-20261011-prep/` と `representative-c2-core-post-20261011-prep/`。各512KiB32entry/reserve128KiB/single128KiB。selected CLI出力はhelper全process stdioではない。開始Git user-global ignore警告はexit0 tool excerpt/full foreground identity・process logsNoneとして保存。

engineering900秒/2GiB/output1GiB/single32MiB/files32 checkpoint上限維持。blocking計算中断/full runtime closure/全writer-global-coupled/native容量証明ではない。create_native早期拒否/全7役whole.run限定reader実起動禁止/元caps-unknown原owner-stop保持。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読、正式5残件・最終受入未完了。追加agent起動・再活性化禁止。

## 次工程

同じ保存済みfirst dev/layout0の **quality-stressをC2で1件**実評価する。C2のpeer入力依存下で欠測が利用不能行・検出へどう波及するかを原結果から確認し、C1 quality-stressと今回C2 coreの保存指標と比較する。完成C0/C1/C2 core・C1 quality・明示replay・旧risk/owner testsを反復せず、観測した不具合だけ補強。CI38138556456は次heartbeat compact一回、未終端なら待機・反復なしで小評価へ進む。
