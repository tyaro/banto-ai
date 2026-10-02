# 保存済み要約と全予定枠の結合（2026-10-02）

**保存済み要約を登録・最新attempt・評価/入力hash・全120区間へ結ぶ純粋関数を追加した。新16項目pass（30.515秒）。供給が1区間なら119区間/714評価を未確認として残し、全件宣言から補わない。120区間/720枠の架空要約例は13.504秒で結合成功。719 success/1 inconclusive、旧失敗1件、precision分母ゼロ720件を保持した。**

起点8faf7a8068384a35b397564ebed9e391fff5cb93。前保存点24,801bytes/SHA33af07cbd335dbbb94c8a68e20a5d440055b40e5d6911a4f95aeda349a300c06。最終実装3e596bb0c8eafbc94c09f65ef114e54d6098ecf8、clean候補sc02/banto-ai。新module/test2本のみ、旧84code/18data不変、計86code。[API](../anomaly-v03-summary-coverage.md)。

## 確認したこと

| 検証 | 内容 |
| --- | --- |
| 外部期待値 | metadata/要約/完走保存点/evidenceのpin、要約集合とpin集合の一致 |
| 登録・履歴 | 全120区間、720枠、最新attempt、失敗記録、連番、固定plan、評価/input hash |
| 欠落・混入 | 旧attempt、重複、holdoutへの付替え、別campaign、6枠の順序/欠落、入力や旧auditの変更を拒否 |
| 保存後のcount | 主countと保存済み監査、条件別分割と主count、遅延・判定不能・分母ゼロを照合 |
| 部分供給 | 全件完了のmetadataでも要約0なら未確認720、要約1区間なら未確認714を保持 |
| 副作用 | ファイル・process起動・journal replay・score/ledger再計算を禁止した試験もpass |

初回tests-1は15項目中12pass/3error。JSON保存後のオブジェクト項目順に既存slice比較が依存していた。厳密なshape検査後にschema順へ並べ直す修正と、逆順JSONの回帰試験を追加した。元候補sc01/3be67c9と失敗記録・旧harnessを保全し、修正後sc02で16項目を再確認した。

- [修正後16項目](../../artifacts/summary-coverage-2026-10-02/tests-2/test-results.json)
- [初回の失敗記録](../../artifacts/summary-coverage-2026-10-02/tests-1/test-results.json)
- [全件例の結果](../../artifacts/summary-coverage-2026-10-02/tests-2/invented-full-coverage/result.json)
- [全件例の結合記録](../../artifacts/summary-coverage-2026-10-02/tests-2/invented-full-coverage/binding.json)
- [外部期待pin](../../artifacts/summary-coverage-2026-10-02/tests-2/invented-full-coverage/caller-expectations.json)

要約120fileは17,770,520bytes、metadataを含む供給入力は18,897,079bytes。結合出力は107,125bytes/SHA7ed4094d91eba6377c4fdd1fb105e55f8629a7eedef9ebe221c2c794e59ac761。journal362件相当、attempt121、最後の区間はattempt2。過去失敗の不明slotを成功・未着手に置換していない。全要約がそろったcomplete_summary_bindingは結合範囲の完了で、campaign_evaluations_credited=0と信頼関連falseを維持する。

今回の全件例は1つの手計算テンプレートのcountを複写したメタデータ結合試験で、720種類のlayoutを数値検算した結果ではない。summary内の過去監査を外部pinで固定して照合するだけで、生の観測→score/ledgerの再検算や現在のpayload認証は行わない。実720評価の再読込み/再実行0、新評価0、所有worker/公開process0。

## 資源・保存・次工程

試験peak 64.59MiB、例peak 80.53MiB、例directory観測最大18.14MiB、commit最小余裕26.20GiB。監視は試験93/例55sample、errorなし、終了確認済み、資源pass。120秒/512MiB/32MiB等の上限据置き。 D空きは開始366.76GiB→例終了350.75GiB、約16.01GiB減を観測。今回の保存例はC上の18.14MiBで、D減少の内訳や別処理との因果は未調査。容量不足には達していない。 短時間の確認から長期メモリリークの不存在や正式規模の予算は推定しない。

実計算c01d1c9/main6f1285d/closed/既存dirty文書とsr01/旧候補を保全、banto-24 PAUSED。OS25H2/26200/9457を記録、旧formal9168不変。前工程の別Bantoリリース申告と資源停止記録を保持し、因果は断定しない。principal/保護root/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。

次は結合済みのdev/smoke主count・条件別countを、role/seed/candidate/stratum別の記述集計へ接続する。登録IDを正式40seedや架空40clusterへ変換せず、欠落した要約から全体集計を返さない。固定入力で進め、既存720評価のpayloadは読み直さない。

正式null4欄/ready=false、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持。正式40seed・生成導出・契約/役割profile/全工程予算は未受入。Phase2/3全体は未完了。
