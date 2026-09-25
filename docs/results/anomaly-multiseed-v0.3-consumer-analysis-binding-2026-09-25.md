# consumer集計入力の公開記録への結合（2026-09-25）

[結合API](../anomaly-v03-consumer-analysis-binding.md)を追加し、既存の独立監査済み集計入力が、公開metadataを確認した全120区間/720評価と同じデータ・最終attemptを参照することを確認した。実装revision `c4f04121764c882e1cb885f9fea173e4bc2d6cc3`、OUT `artifacts/consumer-analysis-binding-2026-09-25`。最終文書revisionと証跡pinはsavepoint-evidence.json。

## 確認結果

14新規試験pass、failure/error/skip0、11.189秒。架空の過去保存記録を使い、外部anchor不一致、後からの入力変更、journal不一致、公開報告の欠落/重複/順序変更、pinすり替え、失敗attemptへの逆戻り、履歴欠落、input/evaluation hash不一致、集計値/null変更、seed登録不一致、判定不能数の変更、権限やpayload認証への格上げを拒否した。読取を10固定artifactだけに制限しても通過し、process・生成・集計再計算を呼ばない。

実保存記録は、外部publication保存点7257bytes/SHA256 00b5e1bb5a668e2636091938604492fc486e78b8c83b3fe3ac1c50da738feaba と、analysis保存点7305bytes/SHA256 8527dfe71bcb7544f6276b14eeb8bd853491cd2be87ee4f3e8bec2375b0f876d から認証。10artifact/9,785,474bytesを各1回読取り、0.542秒で結合した。

全120区間/720評価について、公開管理記録960参照、input hash4,320件、evaluation hash720件が旧evidenceと一致。10seed cluster、90seed表、18role表の元集計欄が引き継がれていることも確認。最後の区間119はattempt2、過去失敗1件、分母0等で判定不能だった46指標を保持した。

`analysis-binding.json` に旧入力へのpath/raw pinと全導出参照、`saved-binding-check.json` に確認結果を保存。analysis-inputs.json本体は複製・上書きしない。前工程の公開readerや旧算術試験を再実行せず、その保存点から証跡を引き継いだ。

## 資源・到達範囲

確認中peak47.41MiB、最小空きRAM12.38GiB、commit余裕19.72GiB、C122.79GiB／D268.83GiB。旧実計算checkout c01d1c9、本流clean6f1285d、closedと保存点、開始前dirty guardは不変。banto-24 PAUSED、OS/runtime設定変更・追加controllerなし。

新評価、観測/score payload読取、score/集計再計算、bootstrapは0。今回は集計入力bytesと公開metadataへの導出関係を認証したもので、全payloadを新たに認証したわけではない。集計の数値検証・診断結合は既存保存点の検証履歴を明示的に再利用。trust/analysis/execution/formal/promotion/S6、controllerプロセス自体の終了、source/runtime正式受入はfalseのまま。

次はこの結合receiptから、engineering consumerの入力選択と記述結果までの入口をつなぐ。元データの再計算や正式gate/holdoutを起動せず、旧記述結果の保存・入力認証APIを活用する。正式採択・freeze・Phase 2/3全体は未完了。
