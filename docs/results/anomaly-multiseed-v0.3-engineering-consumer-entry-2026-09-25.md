# engineering consumer入口の接続結果（2026-09-25）

認証済み集計入力の選択から記述レポートの保存・読み戻しまでを1つの[API/CLI](../anomaly-v03-engineering-consumer.md)へ接続した。実装 `6567a857455847baf225f552abf5ff9df6644c08`、OUT `artifacts/engineering-consumer-entry-2026-09-25`。最終文書revisionとartifact pinはOUTのsavepoint-evidence.json。

- 16新規試験pass、failure/error/skip 0、0.560秒。2つの外部anchor、入力改変/取り違え、campaign違い、formalへの格上げ、サイズ上限、上書き拒否、途中書込失敗の保全、CLIを検証。
- 実保存7ファイル/7,896,608bytesを認証し、約2.055秒で出力・読み戻しを確認。実接続は同一processでCLI mainを呼び、資源計測に含めた。
- 全120区間/720評価、dev8/smoke2、18表・234主指標・5,670診断行を保持。区間119 attempt2、過去失敗1件、判定不能46指標を保持。
- 観測/score読取、集計/比率/score再計算、新評価、bootstrapは0。旧数値・schema・公開metadataの検証を再利用した。

[閲覧用要約](../../artifacts/engineering-consumer-entry-2026-09-25/published-success/payload/report.md) / [詳細HTML](../../artifacts/engineering-consumer-entry-2026-09-25/published-success/payload/report.html)。JSONはdecoded値が元と完全一致。Markdownはraw一致、HTMLは末尾LFの1byte追加のみ。JSONのcanonical化と末尾LFはwriterの保存形式への変換で、数値や本文の再生成ではない。

成功保存はpublished-success。marker SHA256 `97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e`、consumer receipt 11,507bytes/SHA256 `e2ac5bb2b36d5121062dd8bdc790556cd767cd22a7168ec0579d5aab6570cf3a`。4payloadを読み戻し、local_verified=true。native_acceptanceはnot_completed、formal/promotion/S6=false。

初回単体試験ではJSON比較にtupleを渡した誤りを検出してlistへ修正した。次の実接続では元HTMLの末尾LF欠落により保存が止まり、最小の形式補正と回帰試験を追加した。test-attempt-1/2と未完了publishedを保全。最終16試験と成功出力だけを完了証拠とする。旧試験群を再実行していない。

最終試験/実接続のpeak private 37.25MiB、最小空きRAM12.53GiB/commit余裕19.81GiB、C/D空き122.78/268.83GiB。OS実値はos-state.jsonへ保存。短時間の接続検証であり長期メモリリーク試験ではない。旧保存点・実計算clean c01d1c9・本流clean6f1285d・closed・既存dirty guardは不変。banto-24 PAUSED。

次は今回の入口を契約案T01〜T12へ対応付け、未接続項目と容量・所要時間の見積もりを整理する。既存720評価や旧監査の再実行は不要。正式契約採択、source/runtime freeze、正式gate/holdout、S4/S6、Phase2/3全体は未完了。
