# 少量の代表データによるC0/C1実評価と再実行

2026-10-11 JST。「進めてください」に従い、保存済みdev入力からモデル計算・検出・指標計算を実行した。類似ownerテストを追加せず、正式campaign/native入口の許可条件も変更していない。

## 今回の結果

コード版 **661b27511826fcc87cb4a02930f276afbb8f95d9**。最初のdev seed `2486912926863618161`、layout 0、coreの1 dataset（2設備・18,000観測行）をC0/C1で共用。各候補を正常prefixから新しくfit/calibrationし、既存 `compute_evaluation` でscore・episode・incident・指標を計算した。既存結果を今回の結果として転記していない。

| 候補 | 機械異常検出 | センサー異常検出 | Precision | clean区間の誤警報episode | 検出遅延中央値 |
| --- | ---: | ---: | ---: | ---: | ---: |
| C0 diff control | 0/10 | 0/10 | 0/3 | 3 | null（検出0件） |
| C1 phase level | 10/10 | 10/10 | 20/20 | 0 | 1.5秒 |

両候補とも48 profile、14,400 score行。各候補で利用可能13,920行・利用不能480行を区別し、利用不能を正常判定に補完しない。C0の処理が完了したことは検出性能の合格ではない。C1の良い値もこの合成dev 1条件に限る。bootstrap/CI・全条件の性能評価・候補採択は行っていない。

初回 `dev-core-20261011` は40.0236526秒、同条件の明示再実行 `dev-core-20261011-replay` は37.6347623秒、いずれもexit0/complete/2 cell成功。再実行は元runを残して新run IDへ保存。入力・設定・計算sourceを照合し、全profile/score/episode/incident/metricsの数値hashが一致した。この同code版での2 evaluation JSONは原bytesのhashも一致した。

## 対応関係と失敗

- `manifest.json`: run ID、入力identity/全10file pin、モデルID、設定pin、seed、コード版、計算source pin、実Python/runtime、各cellの成否と結果pin。
- `configuration.json`: 保存されたcandidate設定と既存計算のcompiled設定、seed/layout/stratum/候補順。
- `input/`: 今回使用した元dataset bytesのsnapshot。元の入力rootは変更しない。
- `evaluation-0.json` / `evaluation-1.json`: 実profile、全score、episode、incident、指標。推論/評価の元数値を保存する。
- `started.json` / `planned.json` / `cell-*-started.json` / `cell-*-done.json`: 未実施と途中と完了を区別する。

入力/モデルの取り違え、計算失敗、資源checkpoint拒否、保存失敗、再実行差分はfailedとして保存し、実行を停止する。未着手cellはnot_started、profile不足はinconclusive。result保存とdone記録が完了する前に成功件数へ加えない。failed runは成功runの集計に混ぜない。既存run IDの上書き・自動再試行はない。

確認は計算失敗/後続停止・重複run拒否、完了journal保存失敗、再実行入力改変、holdout早期拒否の4種。初回3件0.228秒pass、資源API返値形をsourceで確認して訂正した影響1件＋新journal失敗1件0.679秒pass。4 distinct/5 bodiesの複数source/runで、最終source単一4件successと宣言しない。owner差替えの類似ケース追加0。実評価/replay各2件はこの確定code版で完了した。

## 実行と再実行

既存のclean checkoutとPython3.14を使う。出力親directoryを先に用意し、`--output` には毎回存在しない新run IDを指定する。候補は1〜2個まで、入力は保存済みdev/smoke 1 datasetだけ。holdoutは観測読取り前に拒否する。

今回の入口：

```powershell
C:\Python314\python.exe -B tools/evaluator/run_representative_anomaly.py `
  --input-manifest C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/attempts/chunks/000/attempt-0001/result/payload/manifest.json `
  --manifest-sha256 05ef05b07193af83eea6946051628fb910b6c02ee8bf386a84957d2a3cf5e1bf `
  --dataset-id anomaly-v03-dev-seed-2486912926863618161-layout-00-core `
  --output artifacts/representative-anomaly-evaluation/NEW-RUN-ID
```

同条件の再実行は保存したsnapshotから行う。元runのmanifest SHA256を明示する：

```powershell
C:\Python314\python.exe -B tools/evaluator/run_representative_anomaly.py `
  --replay artifacts/representative-anomaly-evaluation/dev-core-20261011 `
  --manifest-sha256 0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094 `
  --output artifacts/representative-anomaly-evaluation/NEW-REPLAY-ID
```

再実行では保存入力/元結果pinと計算source bytesを照合する。sourceが変われば同条件replayとして拒否する。文書だけのcode revision差は記録し、数値比較からprovenanceだけを除く。その他のprofile/score/検出/指標/状態は全て比較する。CLI exit0だけで性能合格を宣言しない。

## 証拠と範囲

出力は `artifacts/representative-anomaly-evaluation/`。初回/replayとも22 files、41,016,279 / 41,016,106 bytes（root-closedを含む）。初回manifest 11,019B / `0898a0ee0eb0a5a15af8e52d320832abe06220e30cb8cad0d02f7f774a01e094`、replay manifest 10,929B / `7896da1027c74e8b435328b4bcde9d47b6fc7f0ba716795f72249db1d42db5de`。

各root-closed pinは初回2,540B / `b6304bbb81d7b0fbe5f009a41965c543842c1df0db79f1a3215855160103be6d`、replay2,540B / `a28904b8f8ae8e9f8b4d890ce06c7a8a50d67086c04055d2226e7e0bcb373491`。閉鎖後追加・同保存・完成core/replay反復はしない。metadataは `artifacts/representative-evaluation-20261011-prep/` のcomponents/post-save/owners-after-save/root-closedを参照。

観測SHA256 `3bc5708c1650ac975ea7c4bf66eddf660474d3214325b8c76eb5e434a328d091`、9,600,623B。元payload manifestのpinから指定dataset全fileへ照合し、今回snapshotへliteral保存・readbackした。正常生成や新dataset生成0。CPython3.14.0/Windows/AMD64実値を記録。選択processのOS peak private値は146,644,992 / 147,546,112B。既存engineeringの900秒/2GiB/出力1GiBをcheckpointで確認し、単一file32MiB/32filesにも制限した。blocking計算の即時中断、全loaded runtime閉包、native/all-writer/global coupled capacityの証明ではない。

前115source-science不変、CLI1＋test1の追加2pathだけcode unitを一回commit/push。117 working pinと変更2path Git exactを保存。既存数式/config/科学schema・create_native早期拒否・全7役reader実起動禁止を維持。CI照会/完成focus/native/probe/collector/Git37反復0。新code CI selectionは未実施、前a54961/run38136585791の最後観測in_progressを保持し、終端を補わない。

初回sandbox CIM読取りはAccess deniedで、許可済みread-only照合により51元helperのcreation/start_tokenと終了を確認。広すぎたrg inventoryは旧保護rootのAccess deniedとholdoutのpath名だけを返した。holdout観測本文は読んでいない。不存在source selectorは実名へ訂正した。これらforeground tool excerptはprocess全logs/native/CI/Sol容量失敗の証拠ではない。

formal gate=s4_acceptance_not_frozen、formal_permission=false、credit0、holdout観測未読、正式5残件・最終受入未完了を維持。今回成功は少量の実計算と保存・再実行の成功であり、正式受入やモデル採択ではない。

## 次の評価

次は同じ保存済みfirst dev seed/layout0のquality-stressをC1で1件実行し、欠測に対する利用不能行とセンサー検出の変化を見る。coreと明示replay、既存ownerテストは反復しない。実評価で困った部分を補強し、類似ownerケースを評価開始条件に戻さない。
