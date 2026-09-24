# 用途別の記述結果表・診断表（2026-09-25）

開発用dev 8 seed/576評価と動作確認用smoke 2 seed/144評価について、9候補・条件表ずつ、計18結果表を作成した。主指標234セルと診断5,670行を認証済み解析入力へ照合し、凍結schemaの表・metric・slice・delayの部分形式も検証した。関連27試験通過。正式40 holdoutの性能判定ではない。

## 成果物

- [用途別の要約](../../artifacts/descriptive-report-2026-09-25/report.md)：候補の意味、18結果表、検出率・警報正解率・誤警報率・遅延。
- [展開式の全条件別表](../../artifacts/descriptive-report-2026-09-25/report.html)：用途/候補/条件ごとに18セクションを展開できる静的HTML。外部通信やJavaScriptは使わない。
- [全数値JSON](../../artifacts/descriptive-report-2026-09-25/report.json)：正確な分子/分母、4種類の診断表、予定参照・対象外/試験外、profile診断、遅延度数を保持する。

表はC0＝差分基準、C1＝運転段階別正常値、C2＝運転段階別の条件付き正常値。coreとquality-stressに加え両条件のoverallを表示する。overallを追加評価数に加えない。百分率は表示だけ丸め、JSONの値を変更しない。

開発用overallのC1は機械検出91.67%、センサー検出95.00%、警報正解率95.73%。C2は89.48%/95.00%/94.60%。動作確認用では両候補とも91.67%/95.00%/95.73%だった。これらは用途別の記述値で、候補採択や優劣の統計判定ではない。C1/C2の検出成功時の遅延中央値は1秒。検出できなかった事例を0秒としていない。

## 列の対応と情報の保全

正式slice schemaにはmetricが1つだけあるため、独自の記述reportで次の4系列を分ける。同じslice keyを無名の複数行として混ぜない。

| 系列 | 分子 | 比率の分母 | 行数（両用途計） |
| --- | --- | --- | ---: |
| incident-recall | 因果条件を満たした検出事例 | 予定の正例事例 | 864 |
| score-availability | 利用可能なscore行 | 試験内の予定score行 | 1,602 |
| score-threshold-exceedance | 閾値を超えた時刻数 | 試験内の予定score行 | 1,602 |
| score-signal-onset | 連続条件が成立した信号警報開始数 | 試験内の予定score行 | 1,602 |

この記述出力の`actual_count`は当該系列の分子、`planned_count`は予定の事例/参照数と明示する。通常のscore分類は全予定行を分母とし、利用不能・低scoreも含む。event-offsetだけは対象外target・試験外時刻を別記し、分母を残る試験内の予定score行とする。予定参照数＝試験内行数＋対象外＋試験外を保持し、元の1,602行の参照内訳をsidecarへ格納する。同じscoreへの重複event参照があるので排他的分割とは呼ばない。

incident6分類の864行には正確な遅延度数も別保存する。score9分類は当該targetのqualityや正例窓のoverlapという前工程の定義を維持する。設備context、profile診断、警報0件による適合率未定義の46記録を保持する。class別precisionはnot_applicable。分母0の補助sliceはnull/not_applicable、主指標の分母0はnullでCI未実施を保持する。

正式schemaの部分形式と意味検査を、実際のdev96/smoke24 datasets/条件の母数で実施した。full documentの固定480 datasets/条件に偽装しない。全gateは空、qualified=false、selected=null、decision/performance=not_evaluated。入力時点のreadinessは文脈としてそのまま保存し、今回の検証結果は`validation.json`と`summary.json`に記録する。

## 実装・検証・保存

実装保存点`e0753ba4e1518706002cb3a51f9b5a3c891a4e7c`。`anomaly_v03_descriptive_report.authenticate_report(input_savepoint, root_sha256, schema_path)`は外部hash付き入力保存点と固定名のanalysis-inputs.json・凍結schemaを読む。必要な旧source pinも確認する。`build_report`は純変換で、認証機能は持たない。`validate_report`は出力全セルを元入力に対応づけ、元の母数/度数/診断とschema部分形式を照合する。

入力の信頼起点は7,305 bytes/SHA256 `8527dfe71bcb7544f6276b14eeb8bd853491cd2be87ee4f3e8bec2375b0f876d`。3入力5,171,731 bytesのみを認証し、元観測・評価JSONは読み直していない。過去の認証済み集計を使った記述出力であり、現在の全元payloadの不変を再確認したものではない。

新規9＋統合入口7＋既存analysis adapter11＝27試験通過。欠落・重複・行順違反・分母や率の取り違え・sidecar欠落・formal/gate混入・hash不一致を拒否した。分母0、単位変換の手例、入力不変、JSON往復、HTML escape、18展開セクション/54表/2,610行の構造も確認した。

処理1.625秒、process peak private 44.18MiB、前後観測の最小空きRAM 14.70GiB/commit余裕 21.44GiB、終了時C/D空き 126.09/293.77GiB。 長期のリーク不在の証明ではない。Markdown/HTML/JSONの成果物合計は2,744,025 bytes。新観測・評価・score再計算・実CIは0。旧保存点/source/本流/dirty guardを保全し、banto-24 PAUSED維持。

OUT `artifacts/descriptive-report-2026-09-25`。最終文書revision/pinは`savepoint-evidence.json`。formal/promotion/S6=false、full schema・source/runtime受入は未完了。Phase 2/3全体は未完了。

次は既存のsource/runtime・単一writer受入記録と独立consumerの接続状況を調べ、freeze前に必要な実装・証拠の残件を確定する。既存合格試験を繰り返す必要があるかを先に判断し、保留principalや正式holdoutは起動しない。
