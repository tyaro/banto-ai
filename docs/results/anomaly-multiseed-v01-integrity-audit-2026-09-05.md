# Anomaly multi-seed v0.1 integrity audit — 2026-09-05

## 判定

正式 artifact `artifacts/anomaly-multiseed-v01` は、内容を変更せず保全したまま `REJECT` とする。120/120 cell、`engineering_status=pass` と記録されているが、旧 runner の evaluator validation に summary integrity bypass があり、この artifact を performance promotion の根拠には使わない。

この監査では正式 artifactの移動、上書き、削除、再実行を行っていない。既存artifactはreject evidenceとして元の場所に保持する。

## 発見した問題

旧 `_validate_evaluation` は evaluator の `result.json` と `summary.md` を初期snapshotから読み、`.complete` の result／summary hashが一致すれば受理していた。したがって、semanticな `result.json` はそのままでも、`summary.md` を任意文へ置換し、markerのsummary hashだけを更新した1 cellを受理できた。120 cellを処理したmatrixでは、この bypass を使って `engineering_status=pass` を維持できるため、summaryを含むevidence integrity gateは満たされていなかった。

## 修正した境界

- evaluatorのsummary rendererは、dict／nested mapping／listをUTF-8、`sort_keys=true`、compact separators、`allow_nan=false`で描画し、入力dictの挿入順に依存しない。
- runnerは初期captured dataset／split／configからpure replayしたsemantic payloadだけを使って期待summary bytesを生成し、captured `summary.md` とbyte exact比較する。captured resultやmarker hashは期待値生成に使わない。
- arbitrary summaryと更新済みmarkerの1-cell攻撃は、対象cellを`validate_evaluation` failureとして記録し、残り119 cellを継続し、matrix engineering gateをfailにする回帰testで固定した。

## 再実行の扱い

旧v0.1のpreregistrationとartifactを同じversionのまま再利用しない。summary integrity fixによりcode revisionと受入境界が変わるため、修正監査後の正式runには、新しい `v0.2` preregistration、別の `matrix_id`、別の `output_root` が必要である。v0.2ではseed、layout、detector parameter、bootstrap、promotion gateは維持し、変更理由としてこのsummary integrity fixを明記する。

修正後の正式120-cell runと、その後の独立analysis／promotion判定はこのsavepointの作業範囲外であり、未実施である。

## 監査で固定した観測値

source revisionは `2d2a7095cd74425699c02091c4be8ad9b0278fb2`、matrix config canonical SHA-256は `1c014476f9e9a3112b60323453b7e00359b1e45a831a43ab52d1c4e11d3341db` である。aggregateのSHA-256は次のとおりである。

- `result.json`: `082f67454caf53c597e15fd1a65b81a62f4b0db1b8a04acc51d66acf579c5d94`
- `summary.md`: `e132b3ea14e06be94b4df0cd4b052b1f270797744ca532fb333f1d0e94e289f9`
- `.complete`: `0015556733180220001dd43d8ecc49e8d4eba599a663791f37a2cf08b387d038`

source treeは1,443 files、合計205,897,399 bytes、記録上の120/120 cellはsuccessである。旧artifactを変更せず初期captured inputsから全120 cellをpure replayした監査では、現行summary rendererでのsummary再生成bytesも全120 cellで一致した。ただしこれは正規状態の再現確認であり、旧runnerがsummary差し替え攻撃を防げたことを意味しないため、framework上の判定は `REJECT` のまま維持する。

### audit-only point estimates

bootstrap未実施の監査用集計であり、performance_statusは `not_evaluated` とする。

- incident precision: `9/235 = 0.0382978723`
- overall incident recall: `9/240 = 0.0375`
- machine-fault recall: `0/120 = 0`
- sensor-fault recall: `9/120 = 0.075`
- detected incident delay: 9件すべて `0` seconds
- clean false-alert equipment episodes: `222 / 10.8` equipment-hours = `164.44444444444446` per 8 hours
- fully qualified signal availability: `motor-01.motor_temperature` と `conveyor-01.motor_temperature` は各 `20460/21600 = 0.9472222222222222`、残る6 signalは各 `20640/21600 = 0.9555555555555556`、全体は `164760/172800 = 0.9534722222222223`

したがってtemperatureの2 signalはpoint gate `0.95` 未達である。ただし、このv0.1 artifactではbootstrap／promotion analysisを実施していないため、これらはaudit-only point estimatesであり、performance gateの完了判定ではない。

## 手順逸脱とv0.2の解釈上の限界

preregistrationはA〜C後にD（clean 120-cell run）、その後E（独立analysis）を行う順序を定めていた。実際にはstandalone bootstrap implementation／testsが未完了のままDが先行した。run前に固定したseed、layout、detector parameter、統計plan、promotion thresholdは変更していないが、順序逸脱とP2 integrity defectがあるためv0.1はpromotion evidenceにならない。v0.2ではsummary integrity fixを変更理由として明記し、同じ統計条件を引き継ぐ場合も新しいpreregistration、別matrix_id、別output_rootを要求する。
