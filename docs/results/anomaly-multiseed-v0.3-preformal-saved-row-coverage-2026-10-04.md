# 架空保存行の区間別coverageと未充足のcampaign由来（2026-10-04）

## 今回の範囲

g02の架空登録形式保存attemptと、r01で所有reader子が保存rawを再読取りした結果を、区間別の外部pin・最新attempt・凍結identity順で結ぶ純粋なcoverage collectorを追加した。入口は各区間の10 control rawと事前指定のbytes/SHA256を受け、区間番号の重複・逆順、保存savepoint/receipt/report/manifest、再読取りresult/予算/監督/stdoutの不一致を拒否する。１回の入力は最大480区間・合計256 MiBとした。今回の実行は**保存済み区間0だけ**で、元の131,144,119 Bの観測/評価payloadを新たに開かず、新しい所有readerや資源計測も起動しない。

このcollectorは各区間の保存済み証拠を照合する入口であり、区間をまたぐ同一producer/campaign由来を認証しない。480区間の形だけを満たしても、共有anchorと所有journalがなければ40 cluster、診断、slice sourceを出さない。g02の`hand-normal-v1`は登録seedを消費しない固定手作り系列であり、実登録holdoutの性能証拠にならない。

## 保存した証拠

使用した10 control file（合計348,447 B）のpathとraw pinを、別rootの[入力pinset](../../artifacts/anomaly-v03-preformal-saved-row-coverage-pins-01/pins.json)に保存した。pinsetは2,078 B / SHA256 `7e98a4b8e4c2a2475252ddc41f2327f7fac8aadf346f42eef23dd95fa2c5a013`。このpinは実行CLIへ明示してから読んだ。主な入力はg02の22-file [manifest](../../artifacts/anomaly-v03-preformal-generated-pinsets-g02/pins.json)72,149 B / `22ee6888d731c827162b09ef1332cb61fe6a5542372e3e499ea0088fd214f1ef`と、r01の[再読取りresult](../../artifacts/anomaly-v03-preformal-saved-row-reread-r01/result.json)8,449 B / `d676de043e22226d0fa6e547d2ad77703931056c9b7b9ad0d36ca2154c7453f4`、[６行](../../artifacts/anomaly-v03-preformal-saved-row-reread-r01/rows.json)116,085 B / `134dc17e98dd5ef3ac24431e463436cbcc73a4f869b5262a5428d998d45d66d9`。残り７点と正確なpinは入力pinsetに列挙した。

[成功result](../../artifacts/anomaly-v03-preformal-saved-row-coverage-02/result.json)は3,565 B / SHA256 `f1fa3755f73431f51cf894bf151c94b2086fc3569b743dcefdade4033367d186`。`status=partial_coverage_unanchored`、`bound_chunks=1/480`、`bound_evaluations=6/2880`、`chunk_indices=[0]`、`missing_chunk_indices=[1..479]`である。区間0は登録seed index 0、layout 0、最新attempt 1。６行は２層×３候補の順序で、r01の行投影を保存済みg02のreceipt/report/reader resultから再計算した値に照合した。`producer_campaign_anchor=null`、`campaign_coherence_authenticated=false`、`clusters/diagnostics/slice_source=null`、正式credit 0、formal/analysis/promotion/S6はfalseのままである。

初回`coverage-01`は同じ3,565 Bのresultを書いた後、CLI返却要約が`verified_chunks`という存在しないキーを参照してexit 1になった。結果rootと入力は上書きせず、要約キーを`bound_chunks`へ修正して新root `coverage-02`でexit 0を確認した。両resultのraw pinは同じであり、成功判定には`coverage-02`を使う。

[純粋collector](../../src/banto_ai/anomaly_v03_preformal_saved_row_coverage.py)、[保存trial CLI](../../tools/preformal_saved_row_coverage_trial.py)、[焦点試験](../../tests/test_anomaly_v03_preformal_saved_row_coverage.py)を追加した。新８試験と既存の保存行由来・r01再読取りを合わせた17試験、repository safetyはpass。[別実装postcheck](../../tools/preformal_saved_row_coverage_postcheck.py)は新collectorをimportせず、入力pinset、10 raw、結果pin、６identity、欠番479、g02/r01の主要リンク、正式false/nullを再照合した。[postcheck結果](../../artifacts/anomaly-v03-preformal-saved-row-coverage-postcheck-01/postcheck-result.json)は1,808 B / SHA256 `3ea90b59d369f26c01d0f207be315b674155c998920e315834e6790949640733`、不一致０。この照合も元131 MBのpayloadを再読取りしていない。

## 正式評価前の残件と実データ範囲

| 時点 | 必要な受入証拠・作業 | 今回の結果で扱えた範囲 |
| --- | --- | --- |
| S4採択前、架空固定入力 | [未採択campaign anchor案](../anomaly-v03-preformal-campaign-anchor-proposal-v1.md)に沿う480計画hash・外部pin・所有controller/journal・区間別最新attemptを固定し、同一由来の2,880行から40 clusterを導く。その後、50,000 draw→全文書/slice→完全別監査→公開後readerまでの単一外側予算を測る | 区間別のcontrol raw/pinと最新６行を検査する入口、および欠番一覧だけ。実producer campaignは未着手 |
| S4採択前、運用・環境 | 26H2運用契約、公開保証、５役の完全source/runtime/identity閉包、最終revisionのLinux必須jobとrunner image、Windows nativeを受入れる | g02/r01の選定source・観測runtimeへの保存リンクを照合。完全閉包の証明ではない |
| S4の最終dev/smoke | S1登録済みdev８・smoke２ seedを改訂契約と最終clean revisionで新rootに完走し、独立再監査とsmoke実測から容量２倍条件を判定する | 保存済み合成720評価はengineering参考のまま。今回、dev/smokeを再実行していない |
| S4採択後のS5/S6 | 未使用holdout 40 seedの480区間・2,880評価を登録順で一回実行し、S6で全件を独立再監査する | 実登録観測の生成・読取り０。S5/S6開始権限、性能値、正式評価creditを与えない |

旧gate `s4_acceptance_not_frozen`を維持する。次に必要なのは共有campaign anchorとjournalの契約採択・所有実行、続いて架空入力での40 cluster導出と全工程予算である。別系譜のtrial-16の40 cluster・50,000 drawや既存合成dev/smokeを、この１区間の不足分へ補填しない。
