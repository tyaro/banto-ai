# event-aware anomaly multi-seed evaluation v0.3 S2監査結果

状態: **S2完了 / 独立監査合格 / formal run未実施**
監査日: 2026-09-06
対象候補commit: `5bc312924f17160c3126d3010094d561309d145d`
parent: `2428a677fd0a2721cc336e51ecb67b1b56709dd9`

## 結論

S2の純粋なscoring、episode、causal matching、固定分母accountingと境界試験を監査した。P0〜P3はすべて0件で、S2を完了と判定する。

| 判定 | 結果 |
| --- | --- |
| `SCORING_CORRECT` | yes |
| `CAUSALITY_SAFE` | yes |
| `EPISODE_MATCHING_CORRECT` | yes |
| `TESTS_ADEQUATE` | yes |
| `LEGACY_PROVENANCE_PRESERVED` | yes |
| `S2_READY` | yes |
| `INTEGRATION_READY` | yes |
| P0 / P1 / P2 / P3 | 0 / 0 / 0 / 0 |

この判定はS2実装とその純粋試験に対するものであり、性能達成、candidateのwinner、promotion、実設備一般化を意味しない。

## 対象と変更範囲

S2では次の責務をstdlib-only、filesystem／network／environment I/Oなしで実装した。

- 保存済みobservation JSONLのstrict decode、6桁量子化境界、4 target allowlist、qualityと時系列の検証
- 観測されたmode entryからのphase state、gap／recipe変更／未知labelの停止境界
- C0差分、C1 phase-level、C2 phase-conditionalのprofile fit・median/MAD・縮約共分散・Cholesky solve・score
- threshold超過からの2点support、signal episode、推移的equipment episode merge
- first-equipment-onset-no-retry-v1のevent matching、causal support、delay、固定incident分母
- equipment-hour clean mask、availability、0-alert precisionのnull/inconclusive扱い

変更は10 files、`+1577/-21`。新規moduleは `_anomaly_v03_numeric.py`、`anomaly_v03_scoring.py`、`anomaly_v03_episodes.py`、新規試験は2 filesである。legacy provenanceのcurrent-onlyは24 pathsへ明示追加した。v0.3の5 config、9 schema、freeze registry、seed/bootstrap、plan、S1 module、過去artifactとformal pinsは変更していない。

## 監査方法

S2専用試験は67/67 pass。Q1〜Q5、M1〜M9、profile成立、calibration最小点数、MAD zero、singular covariance、NaN/Infinity/bool、duplicate/reversed timestamp、current/previous/peer quality、future invariance、transitive merge、pre-event後発target、dropout denominator、0-alert precisionを含む。

独立oracleでは、次を照合した。

- DecimalとGauss-Jordanによる数値oracle: 3,936比較一致
- interval graphによるepisode merge oracle: 512 patterns一致
- matching oracle: 64 cases一致
- historical 88 pathsのGit blob/mode、formal pins、current-only 24 pathsを照合

回帰を含むlocal full suiteは、Windows CPython 3.14.0で `618 tests / 1262.397s`、616 pass、既存Toto artifact不足による2 skip、failure/error 0だった。独立targeted確認は147 pass。CI [run 34017895359](https://github.com/tyaro/banto-ai/actions/runs/34017895359) はsuccessで、CPython 3.14（9m27s）と3.12（10m16s）のcompile、unittest、manifest＋smoke、synthetic＋quality、benchmark、safetyが通過した。

## 保持した境界と未実施項目

Q1〜Q5の試験は量子化境界を検査したが、実overlay、未丸めlatent temperatureのcarry、paired materializationはS3に残る。S2は登録済みseedからデータを生成しておらず、formal observation／score artifactも作成していない。

未実施は次のとおり。

- S3 deterministic runner、materializer、publisher、atomic/non-overwrite output
- S4以降のdev/smoke/holdout campaign、formal artifacts、独立consumer、bootstrap CI、gates
- 実際の性能評価、candidate promotion、winner選択、実設備一般化
- Linux formal pin受入、Windows native/DACL/AccessCheck受入
- TimesFM residual、Banto Hub write、PLC/control write

次のsavepointはS3 deterministic runnerである。S2の通過を、formal run開始や性能判定の許可へ読み替えない。

## 来歴

この文書はS2完了後のliving audit recordである。凍結planおよびS0/S1の過去result本文は遡及修正していない。候補commitはmainへ統合済みで、S2 docs-only同期のcommitがこの文書とliving indexを更新する。
