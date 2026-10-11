# 保存済みdev quality-stressのC1実評価（2026-10-11）

## 結果

保存済みfirst dev seed **2486912926863618161 / layout 0** のquality-stressを、既存C1（phase-level）で1件実計算した。入力10fileを外部manifest SHA256へ照合して新snapshotへ保存し、fresh fit/calibration → score → episode → matching → metricsを実行した。生成データ追加0、元payloadへの書込み0。

| C1条件 | 機械異常検出 | sensor異常検出 | precision | clean誤警報 | score利用可能 / 全行 | 検出遅延中央値 |
| --- | --- | --- | --- | --- | --- | --- |
| core（前回の保存結果） | 10/10 | 10/10 | 20/20 | 0 | 13,920 / 14,400 | 1.5秒 |
| quality-stress（今回） | 10/10 | 9/10 | 19/19 | 0 | 13,880 / 14,400 | 2.0秒 |

coreは保存済みsummaryだけで比較し、再計算していない。今回CLI exit **0**、run **complete**、1 cell **success**。これは処理完了であり、性能採択・正式合格ではない。合成devの1 seed / layoutに限る記述結果で、bootstrap・信頼区間・勝者選択0。遅延は検出した19件のみ（平均1.5263157894736843秒、最小1秒・最大2秒）。未検出1件のdelayはnullで、補完しない。

## 欠測と未検出の対応

全48profileはcalibrated。利用不能はcoreの480行から **520行**へ増えた。primary reasonはmode/recipe/phase 480、current target quality 30、previous target quality/nonfinite 10。非排他的tagのcurrent quality 30・current nonfinite 30・previous quality/nonfinite 30は重複するため、90行として加算しない。quality-maskの欠測観測は30行。全利用不能score/residualはnull、threshold_exceeded=falseの原結果を確認した。

未検出は **cycle 09 / motor-01.motor_temperature / sensor spike**（sample 8827–8829）。保存結果で次の対応を確認した。

| sample | 利用可否 | score / 状態 |
| --- | --- | --- |
| 8827 | 可 | 192.62635987390755、閾値6を超過 |
| 8828–8830 | 不可 | current target欠測、score=null |
| 8831 | 不可 | previous target欠測、score=null |
| 8832 | 可 | 0.05515233491377427、閾値以下 |

固定設定はpersistence=2・episode onset=second-exceedance・quality reset。最初の超過後に欠測が入り、連続2行のepisodeが成立しなかった。matching原結果はcandidate_count=0、reason=no_candidate_in_window、causal_detected=false、delay_seconds=null。設定・閾値・GT・科学式を変更して検出を成功へ補っていない。この欠測は既存依存・episode方針に沿った評価結果で、今回実経路で発見した入力対応や保存の不具合はない。

## 再実行可能な入力・モデル・設定・結果

- run ID: `dev-quality-c1-20261011`
- dataset: `anomaly-v03-dev-seed-2486912926863618161-layout-00-quality-stress`
- candidate: `c1-phase-level`、固定設定version 0.3、保存configuration pin 5512B / `d6caee52714a28d574d5788ad153d3708daa3bc6caad4cbd02a80cf8edd1bc39`
- 実checkout HEAD: `5ddbc5dd36c83c66e38fa5fa16ea9e0cff576902`（文書版）。計算sourceは前回code `661b27511826fcc87cb4a02930f276afbb8f95d9`から不変。宣言16sourceのworking/Git原bytes又は明示CRLF→LFだけの一致を当該runへ保存。
- 元payload manifest SHA256: `05ef05b07193af83eea6946051628fb910b6c02ee8bf386a84957d2a3cf5e1bf`
- 観測18,000行: 9600624B / `7965d24417c902ba23565227b3b57adec0704ea456a458c0a380630dcb83057e`
- run manifest: 8042B / `3042be397642799af8c5ac6d0d2fb82c8f92f0a3d66a8fe983f8cc1b8e4431d3`
- 原evaluation JSON: 14508215B / `8fe79fd49c003da217ffbcc91756177accddaeff47fb4887017e1cdf2f10735c`
- numerical pin: 14502617B / `236c485f6e9183b96026c3e765fac1e630f8ec5fa18e6efb90a41294562e6786`
- elapsed: **32.100969000020996秒**、checkpoint OS peak private bytes **148582400B**。
- actual runtime: CPython3.14.0 / Windows / AMD64 / `C:/Python314/python.exe`。full runtime closure/native認証ではない。

```powershell
& 'C:/Python314/python.exe' tools/evaluator/run_representative_anomaly.py `
  --input-manifest 'C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/000/attempt-0001/result/payload/manifest.json' `
  --manifest-sha256 05ef05b07193af83eea6946051628fb910b6c02ee8bf386a84957d2a3cf5e1bf `
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-00-quality-stress `
  --candidate c1-phase-level `
  --output artifacts/representative-anomaly-evaluation/<新しいrun-ID>
```

実行にはclean tracked checkoutと未使用output名が必要。上の新run-IDは説明用placeholder。今回追加replay0、既存core/明示replay/4risk tests/類似ownerケース反復0。failed/inconclusiveの扱いは既存CLIのまま。出力rootは閉鎖 **19file / 27555137B**、root-closed 2224B / `72b5589455351a4b40ee564d522cae92a0d714c5cd62061e2402abee5c2b1f21`。閉鎖後の追加・同保存・同run-ID再実行禁止。

## 保存・CI・境界

原CLI stdout/stderr/exit、helper creation identity/start_token/live/execution、compact比較・未検出windowの原ledger抽出を `artifacts/representative-quality-stress-20261011-prep/`へ保存。全117 source-science working pinは前回から不変。旧core/replay/metadata4rootのcount/bytes/closure pin不変。selected CLI出力はhelper全process stdout/stderrではない。開始foreground Gitのuser-global ignore Permission denied警告はexit0のtool excerptとして保存し、CI/native失敗へ補わない。

実code fullSHA `661b27511826fcc87cb4a02930f276afbb8f95d9` のCI selectionは今回一度だけ。run **38138556456** / push / Phase 1 CI / **in_progress**。原stdout・stderr・exit0を判定前に保存し、attempt/jobs/終端/journal/countは未観測。旧38136585791/fulla54961の最後in_progressも履歴として保持、今回は再照会0。CI待機・反復を実評価の開始条件にしていない。完成旧CI・doc-only CI照会0。

既存engineering900秒/2GiB/output1GiB・single32MiB/files32のcheckpoint上限を使用。blocking計算中断・全writer/global memory/coupled/native容量の証明ではない。create_native早期拒否・全7役whole.run限定reader実起動禁止・元caps/unknown原owner-stopを維持。formal gate=s4_acceptance_not_frozen、formal_permission=false、credit0、holdout観測未読、正式5残件と最終受入未完了。

## 次工程

元payload manifestには同じdev seed/layoutのcore・quality-stressのpairだけが保存されている（manifest metadataのみ確認）。次はこの保存済みcoreを **C2で1件**実評価し、候補の実挙動を比較する。完成C1 quality/core/replayや類似ownerテストは反復せず、実評価で観測した不具合だけ補強する。現在コードのCI38138556456は次heartbeat compact一回、未終端なら待機・反復なしで実評価へ進む。候補採択やholdoutへの拡張は行わない。
