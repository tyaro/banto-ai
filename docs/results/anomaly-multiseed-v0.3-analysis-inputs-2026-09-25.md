# 認証済み解析入力への統合（2026-09-25）

保存済み720評価の件数、検出遅延、条件別内訳、予定/有効clean時間、profile診断を一つの解析入力へまとめた。seed別90表と用途別18表を対応させ、2条件からoverallへの30組、seedから用途別への18組の加算を照合した。元の大きな評価JSONを読まず、認証済み集計6ファイル・5,453,594 bytesを利用した。関連39試験通過。

## 何が使えるようになったか

`analysis-inputs.json`の`seed_clusters`は開発用8、動作確認用2の登録順で、12 layouts×2条件×3候補の固定評価IDを保持する。各candidate/stratumに整数counts・profile状態・有効clean秒・正確な遅延度数/要約を結合した。`by_seed`/`by_role`には予定母数、各指標の点、全条件別表、設備警報のcontext、元の診断を保持する。dev/smokeを一つの推測統計集団に混ぜない。

統合時に検出件数と遅延度数、警報と未対応件数、8対象のavailability、予定露出とscoreのcontextを相互照合した。incidentの6分類とscoreの9分類のセルを欠落なく扱い、排他的分類では分子/分母の全体合計も検査する。event-offsetだけは複数eventからの参照を許し、対象外/試験外を別記する。遅延中央値や率を平均して全体値を作らず、度数と整数分子/分母の加算を確認する。

警報0件の適合率が定まらない46評価の記録は残る。これはprofile不成立やsoftware failureと別であり、その評価をrecall・予定母数から除かない。未検出のdelayを0秒に置き換えず、検出0件の遅延要約はnullのまま。

## 認証入口と適用範囲

実装保存点`1db34dc3502552feb0869da2cec68508736f1b8d`。`anomaly_v03_analysis_inputs.authenticate_analysis_inputs(savepoints, root_sha256, schema_path)`は、明示した`savepoints`の`slices/seeds/adapter`三保存点を受け取る。外部SHAを起点に共通のcounts pinを確認し、固定名の小さな集計2ファイルと凍結analysis schemaを読む。利用する旧集計・算術・registryのsource pinも照合する。報告内の任意pathや元payloadへはたどらない。

今回の信頼起点は前回slice保存点（34,314 bytes、SHA256 `03585b7389987fa21bfbf8fcb45f2eca6baeef74e9ba3687a473959880e50f79`）。履歴上認証された保存済み結果の再利用であり、今日の全payloadの不変を改めて確認した意味ではない。純関数`join_inputs`単独にはbytes認証機能がない。

## 正式判定に残る条件

凍結schemaの必須トップレベル10項目を`readiness.json`で全て対応づけた。schemaの版やresult_typeは既知だが、この入力には独自formatを使い、正式analysis文書として出力しない。

| 項目 | 今あるもの | 残るもの |
| --- | --- | --- |
| candidate_tables | dev/smokeのcounts・露出・delay | 正式holdout 40 seed、50,000回のbootstrap、CI・全gate |
| slices | 6分類の異常事例・9分類のscore診断 | 正式schemaの単一metric行への対応と意味の検証。複数の診断値やoffsetの除外理由を黙って削らない |
| provenance / analysis_consumer | 過去の入力pin、実装revision、集計の信頼連結 | 正式producer/consumerのsource inventory・runtime受入・freeze・公開証拠の組立てと確認 |
| status / selected_candidate / decision | 集計統合の完了、選択null | engineering/performance受入・正式採択判断 |

正式holdoutは開いておらず、現在の10 seedを40 seedの代わりにしない。source/runtime欄が未受入なのは、この工程で正式な受入証拠を組み立てていないという意味で、旧dev/smoke実行証拠が存在しないという意味ではない。保留中のprincipal/UAC/ACL試験は再開しない。

## 検証・資源・保存

新規7＋既存seed集計12＋slice9＋analysis adapter11＝39試験通過。登録順、欠落/重複、誤ったrole、formal/CIの混入、件数/度数/率/露出の不一致、診断の二重計上、hash不一致を拒否し、元入力を変更せず必要なcompactファイルだけ読むことを確認した。最初の試験では内部tupleをstrict JSON比較へ渡した不備を検出し、JSON配列で比較するよう修正した。初回ログを保全、実データ適用は修正後に1回だけ成功している。

処理3.176秒、process peak private 53.00MiB、前後観測の最小空きRAM 10.68GiB/commit余裕 15.14GiB、終了時C/D空き 126.79/298.91GiB。 RAM/commit値は前後のスナップショットで、長時間のリーク不在を示す値ではない。新観測・新評価・score再計算・実CIは0、banto-24はPAUSED。旧保存点・本流・実source・既存dirty guardを保全した。

OUT `artifacts/independent-analysis-inputs-2026-09-25`に統合入力、readiness、実行/試験/資源記録を保存。最終文書revisionとpinは`savepoint-evidence.json`。formal/promotion/S6=false、performance=not_evaluated、selected_candidate=null。Phase 2/3全体は未完了。

次は統合済み入力から、dev/smoke別の記述結果表と診断表を出力する。正式schemaとの列対応を確認し、event-offsetの対象外/試験外参照やavailability・閾値超過・警報開始数を落とさない。
