# 準備済み報告書のローカル保存・終了後読取り（2026-10-03）

**前回の準備済み報告書4file/3,040,268bytesを、通常のローカル保存とwriter終了後の別readerへ接続した。修正後11項目pass（4.545秒）。保存例は3.722秒で終了し、4ファイルのbytes/SHA256は元と一致した。**

起点8f77c54c4d300b11cb8f8d585b684f8b6e467612、前保存点27,135bytes/SHAed8fe302b63a4f3f5bbee020288013381bc529f5215c582a188ac431f82b0c1a。最終実装8e1ab327d4302741cb0aff7c46b787707de5fc86、clean候補brp2/banto-ai。新module/test2本、旧90code/18data不変、計92code。[API](../anomaly-v03-bound-report-publication.md)。

## 確認結果

| 対象 | 結果 |
| --- | --- |
| 正常接続 | 固定4payloadのwriter終了後reader、元bytes完全一致、原本mtimeも試験で不変 |
| 準備記録 | mode、正式欄null、formal_ready=false、出典一致、元receipt内の3payload pinを確認 |
| 改変 | 内容・pin・欠落・余分なファイル・サイズ超過・marker不一致を拒否 |
| 停止後 | source不正でreader未起動、reader失敗で保存保持、writer応答喪失で未確認扱いとreader未起動 |
| 既存/所有 | 元データとの包含拒否、既存試行を上書きしない、未回収workerの元所有者を保持 |
| 計算省略 | mapper・再集計・要約結合等を禁止したmetadata検査、既存報告書をbyte単位で再利用 |

修正後11試験failure/error/skip0。小さいfixtureは保存契約専用で数値集計を表現しない。保存例では前回の18候補表/234主指標/5,670診断項目、架空データ表示、判定不能1評価/48profile、旧失敗1件、分母ゼロ720件を含む4payloadの一致を確認した。報告内容を再導出していない。

初回b27c0b1/brp1は小さい保存用fixtureの10試験が通ったが、実際の保存済み報告書ではformal_readinessのキーをreadyと誤読してKeyError。writerはexit2で回収済み、publication作成前に停止、reader未起動、原本不変。formal_ready/status/formal_document_emittedを確認するよう修正し、試験も本物のschemaから生成するreadinessへ置換、昇格拒否の回帰試験を追加した。tests-1/verify.py/旧候補と全停止記録をinitial-failure.jsonのpinで保全し、修正後はtests-2/verify-fixed.py/brp2の新しい記録へ保存した。

- [11項目の記録](../../artifacts/bound-report-publication-2026-10-03/tests-2/test-results.json)
- [保存・読取りの結果](../../artifacts/bound-report-publication-2026-10-03/tests-2/retained-report-publication/example.json)
- [保存後の報告書・架空データ](../../artifacts/bound-report-publication-2026-10-03/tests-2/retained-report-publication/published/payload/report.md)
- [保存後の詳細・架空データ](../../artifacts/bound-report-publication-2026-10-03/tests-2/retained-report-publication/published/payload/report.html)
- [外部pin](../../artifacts/bound-report-publication-2026-10-03/tests-2/retained-report-source-anchor.json)
- [最初の停止記録の保全](../../artifacts/bound-report-publication-2026-10-03/initial-failure.json)

writer PID6748、reader PID11444、両方exit0/終了確認済み/観測errorなし。readerはwriterを回収してから起動した。完了marker SHA2b42b57c72c9557558addd9b698bd11dea1fff2b1bed0854272abb06e2c349f0、出典pin 85,738bytes/SHA4e2e245b4ecc04a2ddebbe5c51b1d5433e928cecf6a3048e5c65ef11a36e2e37。各ファイルのpinは外部pinと結果に記録し、前回保存点と一致する。

保存例は前回の「架空データ」と明示された報告書をそのまま再利用した接続確認で、実際の検出性能を示す結果ではない。mapper・再集計・全区間結合・元評価raw読取り・新評価・bootstrap・正式gateは0。数値とschemaの対応検査は過去の記録を再利用し、今回は独立数値監査を行わない。

## 資源と次工程

試験parent peak 34.82MiB。保存例parent peak 29.68MiB、writer peak 40.54MiB、reader peak 36.27MiB。例directory観測最大2.91MiB、commit最小余裕25.84GiB。試験21/例21sample、errorなし、全monitor/workerの終了確認済み、資源pass。 D空きは開始348.26GiB→終了348.26GiB。各worker30秒/512MiB/stdout等64KiB、全体120秒/parent512MiB/32MiB等の上限は緩和しない。短時間の確認から長期メモリリーク不存在を推定しない。

正式null4欄/formal_ready=false、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持。通常のローカル保存と別processの直列実行を確認した範囲であり、principal境界・ソース全依存・実producerの認証ではない。正式40seed・生成導出・契約/役割profile/全工程予算は未受入。Phase2/3全体は未完了。

実計算c01d1c9/main6f1285d/closed/既存dirty文書とbr01/旧候補を保全、banto-24 PAUSED。OS25H2/26200/9457、旧formal9168不変。別Bantoリリース申告・資源停止・D空き減少の履歴は保持し因果未断定。principal/保護root/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。

次は要約・報告準備・保存読取りの完了済みの各工程を、外部pinと既存成果物を受け取る単一の資源制限付き入口へ接続する。実720評価の再実行・正式gateを起動せず、保存済み工程を反復しない。
