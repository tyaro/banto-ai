# Anomaly multi-seed v0.1 integrity audit — 2026-09-05

## 判定

正式 artifact `D:\develop\banto-ai\artifacts\anomaly-multiseed-v01` は、内容を変更せず保全したまま `REJECT` とする。120/120 cell、`engineering_status=pass` と記録されているが、旧 runner の evaluator validation に summary integrity bypass があり、この artifact を performance promotion の根拠には使わない。

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
