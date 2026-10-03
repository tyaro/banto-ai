# v0.3 26H2受入案・登録raw-byte候補・50,000 draw資源測定（2026-10-04）

基準保存点は `87a8034d5cb65d32a8c494313bdf9698a508574b`。コードと契約案は `e23b7f4`、測定前の追加監査修正は clean `17873fd102ed29cc7c3fb6b1ce3aacab6efc2db5` に保存した。正式40 seedの実観測、S4受入、S5/S6、gate、昇格は起動していない。旧 `s4_acceptance_not_frozen` と25H2正式pinを維持する。

## 26H2と5役割

[運用契約改訂案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)は現実測のProfessional / 26H2 / build26300 / UBR9457を、旧25H2/build26200/UBR9168とは別版で受け入れる場合の条件として記した。現engineering v1もrelease=25H2を固定するため、26H2での旧writer/reader実process試験は起動前に拒否される。案v2は未採択で、旧runtime pin・registry・正式gateを変更しない。Windows native、Linux 2 jobs、最終clean revisionでの正式dev/smoke、独立再監査を受入条件に残す。

[5役割の棚卸し](anomaly-multiseed-v0.3-five-role-source-runtime-gap-2026-10-04.md)では、過去producer、記述analysisとreaderの候補profile、架空数値analysis/audit/writer/readerの選択source・終了後依存観測を分けた。最終producer / 数値analysis / 独立audit / writer / readerの事前profileと動的依存・外部programの完全閉包、各子の開始/終了runtimeとexit/reapは未受入である。

## 登録形式の供給raw bytes境界

[新しい純粋adapter](../../src/banto_ai/anomaly_v03_registered_saved_summary.py)は、1登録chunkの候補receipt・report、2 datasetの入力12個と評価6個の**架空**raw payloadを、呼出し側が別に保持するpinと照合する。凍結holdout identity、最新attempt、評価JSON内のidentity/input hash、主・条件別summaryの形と整合を検査する。失敗した最新attemptの5結果はpartial、0結果は以前の成功へ戻らない。dev/smoke reportとformal modeを拒否する。[新規7試験](../../tests/test_anomaly_v03_registered_saved_summary.py)がpassした。

このadapterは実保存readerを呼ばず、保存点の実bytes、worker終了、観測からのsummary導出を認証しない。独立レビューでは、評価JSONに失敗statusと矛盾するmetricsを加え、payload・receipt・reportを再封印しても、外部pinを同時に選び直せばbyte/identity候補照合は通る反例を確認した。出力は `scope=supplied-registered-format-raw-byte-fixture`、`observation_to_summary_recomputed=false`、`real_saved_chunk_reader_used=false`、`registered_observations_read=false`、`campaign_evaluations_credited=0`、`formal_permission=false` を維持する。正式readerへ進むには、実保存評価schema/status/profiles、元観測からのscore・ledger・summary再導出、独立外部pinと実process/source/runtime/終了証拠が必要である。

## 50,000 drawの別測定

[測定worker](../../src/banto_ai/anomaly_v03_preformal_draw_budget.py)は正式root・旧owned fixture workerと別IDで、固定の架空40 clusterだけを使う。主計算と[別実装のliteral-index監査](../../src/banto_ai/anomaly_v03_preformal_draw_audit.py)を別所有子・新rootで順に実行した。draw indexは2,000,000 bytes / SHA-256 `e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5`。両子は50,000 drawを完走し、主9表、117絶対推定、72対応差、180 gateが一致した。drawを間引いた成功ではない。

| 測定 | 主計算 | 独立監査 |
| --- | ---: | ---: |
| 所有子 | PID 29244、exit 0・回収済み | PID 30196、exit 0・回収済み |
| 経過 | 101.580秒 | 245.902秒 |
| peak private | 124,829,696 bytes | 27,267,072 bytes |
| 出力 | 78,082 bytes / SHA-256 `566a332e8f02b3c8cd478da6784d8aa56308cdc945e1c0e06f20e8d2e1771465` | 566 bytes / SHA-256 `7f43bc3651f6c9b913960c1c3b150dd5f7da3c3952daaff094c345a7dd8daa29` |

両役割を通した最低system commit余裕は16,863,948,800 bytes、最低空きRAMは10,510,004,224 bytes、最低D volume空きは413,553,844,224 bytes。親の最終peak privateは22,384,640 bytes。新rootは10 file・論理241,842 bytes。CIMの資源取得はAccess Deniedで使わず、Windows nativeの資源標本を用いた。各役割の900秒、子private 1 GiB、commit/RAM余裕各4 GiB、空きdisk 10 GiB、出力/親/root上限の中で停止理由なし。samplingによる上限であり、OS hard quotaではない。

[receipt](../../artifacts/anomaly-v03-preformal-draw-budget-2026-10-04-17873fd-01/receipt.json)は5,609 bytes / SHA-256 `1188fe9e68751e280fa7ae497d3792b2cd904d42c7b082ce9a2070c989dfff09`、`status=measured`、`reason=null`。呼出し側保持の9保存file pinと最終inventoryは全件一致し、選択4 source module pinとOS/Python観測は前後一致した。[測定worker試験](../../tests/test_anomaly_v03_preformal_draw_budget.py)11件と旧正式入口の拒否試験1件がpass。未回収ownerを失わない緊急CLI回復loopはkill不能時にwall上限を超えて待ち得るが、今回の正常測定では未発動。回復時は元receiptを失敗・終了未確認のまま保全し、別追記に元receipt pinを結ぶ。

この測定は架空countの**主算術と別算術監査の資源値**に限る。登録実保存reader、正式文書全payload、完全S6、5役割の全source/runtime閉包、producerから公開後readerまでの連続予算、現26H2の正式受入には加算しない。既存fixture worker 8 draw・文書fixture 64 draw・独立fixture audit 8 drawの上限を変更していない。`formal_permission=false`、`independent_s6_complete=false`、`performance_status=not_evaluated`を維持する。
