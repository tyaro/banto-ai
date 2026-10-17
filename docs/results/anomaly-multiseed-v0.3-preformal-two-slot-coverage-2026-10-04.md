# 架空２区間の保存行coverage（2026-10-04）

状態: **未認証の部分coverage / 正式評価credit 0 / S4未採択**。

## 実行と保存証拠

[区間別native小試行](anomaly-multiseed-v0.3-preformal-two-slot-native-smoke-2026-10-04.md)で保存した`c001`（区間0）と`c011`（区間1）を、clean HEAD `14f1f44762e1fb9ac86af858682ccdfe580b3b80`の[２区間adapter](../../tools/preformal_saved_row_coverage_pair.py)に渡した。各区間の再読取り結果・６行・予算・監督・stdout、生成時manifest・receipt・report・savepoint・所有生成resultの計10 control rawを、区間ごとに固定したpathから読み、収集時に別rootへ保存したbytes/SHA256で照合した。pinsetはnative小試行**後**の固定であり、その実行前pinではない。今回、約131 MB/区間の保存payload本体は再読取りせず、新しい所有子や実登録観測を起動しなかった。

| 証拠 | 保存先 | bytes / SHA256 |
| --- | --- | --- |
| 20 control rawの収集時外部pinset | [pins.json](../../artifacts/anomaly-v03-preformal-saved-row-coverage-pins-c01/pins.json) | 4,079 / `9af50430de87c2a2e080d5b60bd74a0844a28157572221cbaee857dfcbb720b9` |
| 部分coverage | [result.json](../../artifacts/anomaly-v03-preformal-saved-row-coverage-c01/result.json) | 4,294 / `689cb1213999d6cb70fb027100dcc273fb59e8861d5b7c11c2325df6f2d83832` |
| 別実装read-only照合 | [postcheck-result.json](../../artifacts/anomaly-v03-preformal-saved-row-coverage-pair-postcheck-c01/postcheck-result.json) | 2,841 / `0f7310500451d755594a1664d95c9cce3d6798ca3c036bfc33cab5f08aca1275` |

外部pinsetのsidecarとraw SHA256は一致した。20 control rawは区間0が348,456 B、区間1が348,457 B、計696,913 B。`run`は明示したpinset pinを再照合してexit 0、独立postcheckも同じ20件、固定された12行identity、receipt/report/再読取りの参照pin、欠番、正式欄を再照合してexit 0だった。関連16試験、repository safety、`git diff --check`はPASS。

## 確認できた範囲

`status=partial_coverage_unanchored`、`chunk_indices=[0,1]`、保存行slotは**2/480区間・12/2,880行**、欠番は2～479の478区間。両区間は登録seed index 0のlayout 0と1、最新attempt 1で、共通の履歴source revision `7c9be9dc328480985dd6c6721af1db8071a93544`、`hand-normal-v1`、registry pin、sourceとsnapshot宣言値を区間間で比較した。区間別の保存rawと再読取り証拠を結んだ範囲であり、単一のproducer campaignで連続生成した証明ではない。

`producer_campaign_anchor=null`、`campaign_coherence_authenticated=false`、`reader_execution_authenticated_here=false`、`clusters/diagnostics/slice_source=null`を維持する。40 clusterの入力完成、50,000 draw以降との結合、単一全工程予算、完全S6は示さない。固定手作り系列は未使用の実登録holdoutを消費せず、`actual_registered_observations_read=false`、`formal_permission=false`、`analysis_authorized=false`、`promotion_allowed=false`、`independent_s6_complete=false`、`campaign_evaluations_credited=0`である。旧gate `s4_acceptance_not_frozen`は維持し、S5はS4採択後に限る。

次は未採択の共通campaign anchor/journalを所有実行に結び、追加の架空区間について同じ保存raw境界を積み上げる。その後、同一由来の2,880行から40 clusterを導く契約、全工程予算とS4の運用・環境・最終dev/smoke受入を検証する。今回の12行や別系譜の40 clusterで不足478区間を補完しない。
