# 保存形式から主・条件別要約への接続（2026-10-02）

**既存の保存済み区間readerへ、独立検算直後に主集計・条件別集計を取り出す経路を追加した。新規12＋既存13の25項目がすべてpass。** 実際の120区間/720評価は読み直していない。

起点はd96344803a97e3dafec69f2a0eb5f15d36edfb8b。前保存点33,823bytes/SHA256 27634dfcccca272ec4409f9130f1a0db7e64c8531a1807b58dd7c19a8979f80b。実装c8e3bd1cbc9a672096f4f4dac57bc09d0d64ef1e、clean候補sr01/banto-ai。既存82codeのうちreader1本を変更、81本は不変、新module/test2本で84code。18dataは不変。[API](../anomaly-v03-saved-chunk-summary.md)。

## 確認したこと

| 検証 | 結果と範囲 |
| --- | --- |
| 機能試験 | 新12＋既存reader13＝25pass、5.061秒、failure/error/skip0 |
| 6slot接続 | 小さい保存形式fixtureで登録plan/6slot/最新attempt/入力pinを確認。数値計算と要約はこのI/O試験では代替関数を使い、呼出し順と結合を検査 |
| 改変検出 | mode、欠落、入力差替え、最新失敗から旧成功への後退、再封印したevent不一致、ledger/要約失敗を拒否 |
| 主/補助の実処理 | 手計算で決めた判定記録から整数count・条件別内訳を導出し、ゼロ分母、遅延、availability、欠落/ラベル違いを確認 |
| 数値接続例 | 定数の手式観測1評価を保存し、実際の独立score/ledger検算→要約を1回実行、5.644秒 |

数値接続例は18,000観測行/14,400score行/48profile。参照scoreの構成1回、別実装の数値検算1回、ledger検算1回、要約1回。全48profileがzero_scaleによる判定不能、全score利用不可、有効clean時間0、precision0/0とnull診断を保持した。6評価すべてを実数値で通した試験ではなく、6slotの読取り結合と1評価の実数値接続を分けた証拠である。生成モデル・実登録seedの観測を実行したものではない。

- [25項目の記録](../../artifacts/saved-chunk-summary-2026-10-02/tests-1/test-results.json)
- [固定1評価の接続結果](../../artifacts/saved-chunk-summary-2026-10-02/tests-1/one-invented-evaluation/result.json)
- [独立検算結果](../../artifacts/saved-chunk-summary-2026-10-02/tests-1/one-invented-evaluation/audit.json)
- [得られた小さい要約](../../artifacts/saved-chunk-summary-2026-10-02/tests-1/one-invented-evaluation/summary.json)

保存例の観測は9,510,000bytes/SHAde392734fe26e0025a9e72c6088a178d41c96340374daa9957bb43cedfa815e0、評価JSONは13,961,930bytes/SHAfd7c60e7b3af79b6d123a43395101bac5d9323860acc80d8c4431d5ac738bbb5。要約は44,370bytes/SHAee6c2d0ed1e896962ece62d61ac8a1013c5868a1dac11bf383c19c2a98c55a53。保存例は観測と評価2fileの接続であり、他のdataset補助ファイルが実数値例で検証済みとはしない。

## 資源と保全

試験は20sample/親peak75.22MiB、例は19sample/親peak107.60MiB、例directory観測最大22.44MiB、commit最小余裕26.23GiB。いずれも資源pass、120秒/512MiB/32MiB等は据置き。今回の短い実行から長期メモリリークの不存在や正式規模の予算を推定しない。

新しい所有worker・公開process起動0。既存720評価の読取り/再実行0、正式登録評価0、正式holdout/50,000反復0。固定fixtureのscore構成と独立検算は実際に1回ずつ行った。bp03と旧保存点・全候補を保持し、新しいsource/runtime正式受入とはしない。

実計算c01d1c9、本流clean6f1285d、closed、既存dirty文書、banto-24 PAUSEDを維持。OS25H2/26200/UBR9457を記録、旧formal9168は不変。前工程の別Bantoリリース申告と資源停止記録も保持する。principal/保護root/UAC/ACL/同時書換え保留、push/mergeなし。

## 次の作業

次は今回の1区間分の小さい要約を、呼出し側が保持する登録・attempt・入力pin・全予定枠へ結ぶ。dev/smokeの識別子を40seedの正式集団や架空登録へ付け替えず、欠落・重複・異なる試行の混入を拒否する。固定データで接続を進め、既存720評価や公開/readerを反復しない。

この完了は実保存形式の選択1区間から評価単位の要約へ渡す境界まで。正式40seedの集団、全coverage、生成導出、契約・最終役割profile・正式全工程予算は未受入。正式null4欄/ready=falseとformal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持。Phase2/3全体は未完了。
