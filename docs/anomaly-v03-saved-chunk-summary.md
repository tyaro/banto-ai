# 保存済み1区間から検算済み主・条件別要約を取り出す

2026-10-02。[実装](../src/banto_ai/anomaly_v03_saved_chunk_summary.py)、[試験](../tests/test_anomaly_v03_saved_chunk_summary.py)、[結果](results/anomaly-multiseed-v0.3-saved-chunk-summary-2026-10-02.md)。

`read_chunk_summaries(savepoint, savepoint_sha256, run_root, chunk_index, *, expected_mode)` は、外部SHAで固定した完走保存点から最新の検証済み1区間を選び、6評価を順に読み取る。expected_modeはfixtureまたはengineeringのみ。formal/未知modeはファイル読取り前に拒否する。fixtureは呼出し側が架空入力を渡す宣言であり、bytesの生成元を認証する機能ではない。

既存の`audit_completed_chunk(..., include_summaries=False)`へ厳密なboolのオプションを追加した。既定の戻り値とCLIは従来どおり。trueの場合だけ、各評価の独立profile/score・ledger検算直後に要約を作る。新しい公開関数はこの経路を呼び、監査結果と要約の順序・identity・outcomeを結ぶ。

## 読取りと導出

- 保存点、evidence、固定plan、最新attempt、終了宣言、6slot、過去auditの選択bindingを既存の読取り処理で照合する。失敗した最新attemptから古い成功へ戻らない。
- 1区間では保存点2file＋計画/過去audit2file＋2dataset×6入力＋6評価＝22fileを読み、評価payloadを二度読まない。入力には有効イベントだけのevents.jsonlではなく、無効条件も含むevent-ledger.jsonlを使う。
- 要約時はfull event-ledgerのcanonical LF bytesと評価内eventsの一致も確認する。hashを再保存しただけの不一致を拒否する。
- 観測から既存の別実装でprofile/scoreを再構成し、別のledger実装でepisode/incident/metricsを検算する。続けて整数の分子/分母・有効時間・遅延度数と条件別countを導出し、主集計との一致を確認する。
- メモリには原則1評価と1datasetの観測を保持し、終了した評価は小さい要約に置き換える。途中失敗時は部分結果を成功として返さず、呼出し側へ例外を返す。入力ファイルや旧保存点には書き込まない。

戻り値はanomaly-v03-saved-chunk-summary-v1。6要約にidentity、評価pin、入力hash、outcome、primary、slices、判定不能profile、ゼロ分母指標を保持し、元auditの外部anchor・読取りpin・attempt選択も残す。`_summarize`は内部用で、信頼済み監査の自己申告を認証する入口ではない。

## 架空入力契約との違いと限界

| 項目 | 以前の架空producer結合 | 今回の保存形式読取り |
| --- | --- | --- |
| 登録 | invented-00等の固定40cluster | 固定dev/smoke planのrole/seed/layout/stratum/candidate |
| 生入力 | 小さいplaceholder bytes | 保存された観測JSONLと評価JSON、補助入力6種のpin |
| count | 外部から渡された要約を照合 | 観測→score→ledgerの独立検算後に導出 |
| 範囲 | 40cluster/480区間の架空結合 | 完走dev/smokeの選択1区間/6評価。全campaignは再読取りしない |
| 出力 | 架空registration形式の主/補助集計 | 実保存形式のidentityを維持する評価単位要約 |

正式40seedの読取り、全campaign coverageの新規認証、登録観測の生成/丸め/overlayの証明、正式50,000反復、公開、source/runtime受入は行わない。origins/quality-mask/split/targetsはbytesをpinで照合するが、その生成を独立導出した扱いにはしない。過去process/終了宣言は信頼する保存点に由来し、現在の実行認証とは区別する。

時間・メモリ・容量は呼出し側の予算管理が必要。本APIだけでは長時間処理の強制停止や任意の同時書換えを防がない。今回の検証は120秒/512MiB/32MiBの既存fixture監視内で行った。formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを保持する。

次は今回の1区間分の小さい要約を、呼出し側が保持する登録・attempt・入力pin・全予定枠へ結ぶ。dev/smokeの識別子を40seedの正式集団や架空登録へ付け替えず、欠落・重複・異なる試行の混入を拒否する。固定データで接続を進め、既存720評価や公開/readerを反復しない。
