# 結合済みfixture解析結果の保存・別reader接続（2026-10-02）

**producer結合入力から作成し独立検算した新しい5payloadを、既存の通常writerと別readerへ接続して成功した。** 解析・検算の再実行0、新評価0。新しい本体コード・APIは追加せず、既存経路とclean候補bp03を使った。

## 起点と結果

前工程は[結合入力の解析・独立検算](anomaly-multiseed-v0.3-bound-fixture-pipeline-2026-10-02.md)、文書889bf807c13a7b78845e2eb7dffe053f48be611f、実装9705b7355cdabca189a60bd63a380fc3062b8ec0。前savepoint-evidence.jsonは51,848bytes/SHA256 379b2ea7e190e7e343190eebf2e1697aafff167ea3fc870d55b40cf127a043c8。元のtests-3/owned-example/pipelineから12個の保存済み入力を受け取った。

| 確認 | 今回の結果 |
| --- | --- |
| 解析元 | 架空40cluster/4draw、2,880予定枠に対応する新文書と5payload |
| 保存・読取り | 所有writer 1回→終了確認→別所有reader 1回、全体10.801秒 |
| 元5payload | 1,987,587bytes、前保存点および元analysis resultのpin一致 |
| 公開5payload | 1,987,592bytes、各canonical JSON末尾にLFを1つ足した差だけ |
| 子の終了 | writer PID26636 / reader PID13032、両方exit0/reaped/観測エラー0 |
| ソース・依存 | 選択source13/Python2/入力12＋invocation、各役割の補助依存233file/179module/47native/30project、追加0 |
| 既存証拠の利用 | 82code/18data不変。公開用16試験の合格記録を該当code不変で再利用。今回suite再実行0 |
| 再計算 | 元analysis0、audit0、既存720評価再実行0、新評価0 |

同じ新入力での保存・別readerを今回1回確認した。[旧fixture公開](anomaly-multiseed-v0.3-fixture-publication-2026-10-02.md)の別入力による成功物を今回の結果に代用していない。別readerは保存bytesと構造の照合であり、新しい独立数値検算ではない。主表/sliceの独立検算は前保存点の成功証拠を再利用した。

## producerから公開物までの結合

1. 前保存点に保持されたpipeline result、projection、analysis/audit result/evidence、文書、新5payloadのpinを照合した。結合済みproducer結果13,277,817bytesも保存済みpinと一致し、再集計していない。
2. projectionの4入力pinを元analysisに、主/補助入力pinを元auditに照合した。pipeline/projectionのbound_result_pin、登録/主manifest/補助manifest pin、元失敗履歴1件と判定不能1枠を保持した。登録元の真正性やraw観測導出を新しく認証したわけではない。
3. 既存[公開API](../anomaly-v03-fixture-publication.md)へ12入力を渡し、writer終了後だけreaderを起動した。入力・公開物・各process証跡・markerを既存処理で照合した。
4. 新しい外部結合記録へ、元producer/projection/pipelineのpinと今回のpublication result/binding/marker/writer/reader pinを対応付けた。元科学payload内の過去のpublished=false等は書き換えず、今回の保存実績を外側へ記録した。

- [入力起点の記録](../../artifacts/bound-fixture-publication-2026-10-02/source-anchor.json)
- [公開要求](../../artifacts/bound-fixture-publication-2026-10-02/publication-request.json)
- [元入力から公開物までの結合](../../artifacts/bound-fixture-publication-2026-10-02/bound-publication-binding.json)
- [保存・readerの結果](../../artifacts/bound-fixture-publication-2026-10-02/attempt-1/example-summary.json)
- [資源記録](../../artifacts/bound-fixture-publication-2026-10-02/attempt-1/publication/resource-budget.json)

文書pinは1,943,210bytes/SHA256 b79970a4fbf18af525de01a4a7aa677cc2e6eb6ed603dc36d6499633a2446581。新markerは1,282bytes/SHA256 c22a5ecb49516d4179cd15e9e74545d08460fc33b084ccf9863218182aec77a9。publication-bindingは2,771bytes/SHA256 d31b35bd4680a4acc38f80a79445e31c15fb7033a266480b3ae246bd5c36ef8c。最終保存点へ全成果物pinと文書revisionを記録する。

## 資源・保全・到達範囲

資源監視54sample、観測最大親private61.01MiB、writer49.89MiB、reader49.49MiB。directory観測最大2.84MiB/39entries、system commit最小余裕26.27GiB、RAM最小余裕14.97GiB。120秒/親512MiB/directory32MiB、子60秒/256MiB等を据え置き、資源pass。directory値は監視中の最大であり、最終記録追加後の全保存量ではない。単一の短い実行であり、長期メモリリークの不存在を証明するものではない。

OS25H2/26200/UBR9457を記録し、旧formal9168は変更していない。前工程でユーザーが申告した別Bantoリリースの同時稼働、およびその際の資源停止記録を保全する。今回もその停止原因を断定しない。

bp03と旧候補、実計算c01d1c9、本流clean6f1285d、control000010 closed、既存dirty文書を保全。banto-24はPAUSED。principal/保護root/UAC/ACL/同時書換え試験は保留し、push/mergeなし。

fixtureの「供給されたproducer結合結果→projection→解析→独立主表/slice検算→通常保存→別reader」は保存証拠で接続済み。正式null4欄/ready=false、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持する。実登録観測からの導出・coverageの真正性・正式契約・最終役割profile・全工程予算の受入は残る。Phase2/3全体の完了ではない。

## 次の作業

次は実producerの保存形式と現在の架空入力契約の差分を具体化し、観測・score・ledgerから主/補助要約へ渡す読取り境界を実装する。小さい固定入力で既存の独立監査部品を接続し、登録・coverage・最新attempt・入力pinの食い違いを拒否する。今回の公開/readerや既存720評価を反復せず、正式契約の採択・holdout・50,000反復はまだ開かない。
