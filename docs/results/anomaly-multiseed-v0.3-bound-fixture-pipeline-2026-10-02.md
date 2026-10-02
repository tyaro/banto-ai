# 結合済み架空入力を所有解析・独立検算へ接続

2026-10-02 JST。[API](../anomaly-v03-bound-fixture-pipeline.md)。producer主/補助結合結果の外部pinから4worker入力へ写し、所有analysisと主表/sliceの独立auditを順に実行した。

開始627ddc5f89980335ea20f1bc8cf912e383f0276f、初回568562f65889d7afa3e1d4909fc1033901a23cbf/bp01、最終実装9705b7355cdabca189a60bd63a380fc3062b8ec0/bp03。新module/test2本、旧80code/18data不変、現在82code。旧workerや独立算術は変更しない。新pipelineはanalysis成功後にauditが失敗してもfixture_inference_performed=trueを保持し、pipeline全体はfailedとする。OUT artifacts/bound-fixture-pipeline-2026-10-02、tests-3/owned-example。文書revision/全pinはsavepoint-evidence.json。

## 検証と保存例

最終tests-3は13項目すべてpass、10.390秒、failure/error/skip0。初回tests-1は12pass/1failure（9.254秒）。元から0のdelayセルを0へ置換していた試験を0→1へ直し、tests-2の修正1件でpassした。その後、後段失敗でも前段の完了実績を残す実装修正を加えたため、最終候補で13件と接続例を再確認した。 初回/中間candidate、ログ、verify-initial.py/verify-focused.pyを保全。全試験の資源監視はpass。中間bp02の接続例24.652秒も保全する。[初回結果](../../artifacts/bound-fixture-pipeline-2026-10-02/tests-1/test-results.json)、[再利用根拠](../../artifacts/bound-fixture-pipeline-2026-10-02/tests-2/reuse.json)、[最終13件](../../artifacts/bound-fixture-pipeline-2026-10-02/tests-3/test-results.json)。外部pin・mode・全予定枠・draw/入力上限・count/profile/delay・失敗後のaudit抑止・未終了ownerの保全を確認した。

保存済み40架空cluster/2,880枠の主・補助結合結果を4drawへ接続。参照文書の同一実装による事前作成1回、所有analysis1回、別実装audit1回で、全体26.370秒。主9表/117絶対推定/72対応差/180gate、本文1,233行・補助2,835行・詳細9表が一致した。 [工程結果](../../artifacts/bound-fixture-pipeline-2026-10-02/tests-3/owned-example/result.json)、[projection](../../artifacts/bound-fixture-pipeline-2026-10-02/tests-3/owned-example/pipeline/projection.json)、[独立検算結果](../../artifacts/bound-fixture-pipeline-2026-10-02/tests-3/owned-example/pipeline/audit/payload/primary-and-slices-audit.json)。元の旧失敗attempt1件、判定不能1枠、precision0/0は引き継いでいる。

| 外部起点・出力 | bytes | SHA-256 |
| --- | ---: | --- |
| 元bound-slices.json | 13,277,817 | a3e98c14fb800cc835976ddff7798efa5126df9968bfcd48860a0ca432834d48 |
| 参照および所有analysisのdocument.json | 1,943,210 | b79970a4fbf18af525de01a4a7aa677cc2e6eb6ed603dc36d6499633a2446581 |

前保存点producer-slice-boundary-2026-10-02/savepoint-evidence.jsonは24,824bytes/SHA9291c79fce30cde30132e8f1d5b2fc733eccaa1efab2afafd8bffaaa82553389。そこに保持した結合結果のpinを信頼起点とし、上流の2,880補助記録/旧実観測を再読込み・再集計していない。元の結合結果は不変。

既存workerは起動前の文書pinを必須にするため、新しい入力に対応する参照文書を同じ計算実装で1回構成した。これだけでは独立検算にならず、別auditが数値の正しさを検査する。参照作成と子analysisを区別して記録し、pipeline関数自身や親の実行証拠validatorは推論を再計算しない。

## 実行記録と資源

analysis PID40180、子監視3.796秒、audit PID1156、子監視2.811秒。両子exit0/終了確認済み/観測error0。analysisの4入力pinとauditの主入力/slice pinをprojectionへ結合した。既存5payloadは1,987,587bytesで保存されたが、通常公開は今回行わない。

analysisはselected source22/Python2/input4、補助依存project38/全245file/module189/native47。auditはselected15/Python2/input6、補助依存project32/全235file/module181/native47。両方の前後追加file/moduleは0。終了後のdisk/Git照合であり、全依存の事前受入や完全実行認証ではない。

[共有資源監視](../../artifacts/bound-fixture-pipeline-2026-10-02/tests-3/owned-example/resource-budget.json)は92sample、errorなし/終了確認済み/pass。親peak private127.18MiB、子analysis/audit 66.19/66.24MiB、directory最大10.99MiB/56entries、commit最小余裕26.70GiB。120秒/512MiB/32MiB等の上限は据置き。前工程の別release同時稼働・commit余裕停止記録は保全し、今回の成功で上書きしない。

例後RAM空き15.76GiB、C/D空き115.54/365.89GiB。最終値とOSはsave-checks.json。OS25H2/26200/9457を観測、旧formal9168は維持。短い観測でリークの有無は断定しない。

## 範囲と次工程

fixture_inference_performed / fixture_numerical_audit_performed / fixture_slice_audit_performed=true。既存720評価の再実行・新評価・登録観測読込み・正式50,000反復・公開processは0。正式null4欄/ready=false、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持。raw観測導出・登録seed/coverageの真正性・正式契約/役割profile/全体予算の受入は残る。 Phase2/3全体は未完了。

次は今回の結合入力から生成・独立検算した新しい5payloadを、既存の通常writer/別readerへ接続する。元producer結合結果とprojectionのpinを維持し、今回のanalysis/auditを再実行しない。 既存公開経路の単なる反復ではなく、今回初めてproducer結合入力につながった結果と公開物の対応を閉じる工程になる。

実計算c01d1c9/main6f1285d/closed/既存dirty文書・旧候補/成果物不変。banto-24 PAUSED、principal/保護root/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。
