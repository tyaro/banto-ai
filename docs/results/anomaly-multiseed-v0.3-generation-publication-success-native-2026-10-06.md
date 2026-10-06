# v0.3 共通外側予算のe04完走と保存照合（2026-10-06）

## 結論とscope

clean `02d567fc23603c661af78329489617916367b155`（codeは`fa33314`のcount検証整理を含む）で、新e04 rootの共通全工程を**1回**実行した。生成→initial reader→保存reader→control読取り／projection→40 cluster・50,000 draw→別process算術監査→全文書／slice→writer→終了後fresh reader→control／元payload／source・runtime最終照合まで、外側528.308/1,800秒、内側288.905/1,200秒で完了。起動7 workerはすべてexit0・回収、各budgetのsampler／monitor終了を確認した。

対象は架空1区間の観測22ファイル / 131,144,119 Bと、479区間の明示的な架空metadata fixture。実観測由来を再読取りしたのは2 dataset・6評価で、全480区間の観測や同一campaignの成功には拡張しない。全体の宣言上のcoverageは40 cluster・12 layout・2,880評価（success2,874／inconclusive6）。全候補・主算術9 table／117 primary／72 paired／180 gateと、1,233主slice／2,835診断row／9診断tableを接続した。

`same_outer_budget_generation_to_fresh_reader_measured=true` はこの限定scopeの実測結果。`full_end_to_end_budget_measured`、正式50,000 draw予算、全観測campaign認証、source/runtime全閉包、独立S6完了はfalseのまま。正式gate `s4_acceptance_not_frozen`、正式許可false・credit0、登録holdout40 seedは未読。[e03失敗](anomaly-multiseed-v0.3-generation-publication-retry-native-2026-10-06.md)と旧／未実行rootは保全した。

## 準備と実機条件

新しい期待出力manifestを独立に準備した（124.727秒、外側時計外）。生成物22ファイルの期待pinを実起動前に固定し、4入力の数値由来は先行の同じrecipeを参照、新しい`operation.source_revision`を今回HEADへ結んだ。旧receiptのrevisionを変更していない。57 selected sourceをworking fileとGitで照合し、新規4 root・既存上限・資源floor・一回試行と停止保存条件を`preparation-plan.json`に保存した。

事前のcommit余裕14,959,091,712 B、空きRAM12,731,203,584 B、disk354,144,206,848 Bは既存floorを満たした。計画JSONのtupleがstrict JSONで拒否された初回はファイル書込み前に停止し、listへ直して概要を保全した。製品codeの変更や上限拡大は実施していない。

実機runtimeはWindows11 Pro 26H2 / build26300 / UBR9457、CPython3.14.0 / AMD64 / MSC v.1944、local NTFS。実行前後一致。26H2改訂契約の正式採択にはまだ結び付けていない。

| worker | PID | supervisor秒 | peak private B | 終了 |
| --- | ---: | ---: | ---: | --- |
| producer | 20156 | 132.579 | 354,209,792 | exit0・回収 |
| initial reader | 32588 | 47.616 | 316,391,424 | exit0・回収 |
| 保存reader | 28440 | 43.256 | 315,650,048 | exit0・回収 |
| analysis | 20620 | 59.704 | 125,337,600 | exit0・回収 |
| audit | 37724 | 128.986 | 29,155,328 | exit0・回収 |
| writer | 568 | 8.841 | 68,407,296 | exit0・回収 |
| fresh reader | 36236 | 4.081 | 66,252,800 | exit0・回収 |

producer local全体184.459/600秒、保存reader local最終46.601/120秒。writer／fresh readerの個別60秒上限を維持した。helper実行は528.315秒、外側budget receiptは528.306秒で、上記528.308秒は外側resultの終了保存直前の値。計測位置の差である。

## 共通予算の終了証拠

外側2,873 sample、checkpointはpreflight1／producer5／保存reader30／subset-read10／publication990／postflight36。stage遷移と全checkpoint観測を保持した。stop reason・observation errorなし、sampler joined、7役の終了と3 mapping outputの記録が揃った。

| 外側観測 | 最大／最小 | 上限／floor |
| --- | ---: | ---: |
| parent peak private | 231,374,848 B | 536,870,912 B |
| 4 root合計logical bytes | 141,917,270 B | 336,592,896 B |
| entries／depth | 104／10 | 672／12 |
| commit余裕最小 | 12,207,534,080 B | 4,294,967,296 B |
| 空きRAM最小 | 10,353,860,608 B | 4,294,967,296 B |
| 空きdisk最小 | 353,997,582,336 B | 10,737,418,240 B |

内側2,007 sample、control-read／control-rereadは各483 checkpoint、計966。内側root最大10,305,128 B・44 entries・depth2、parent peakは外側と同値。内側RAM最小10,335,506,432 B・commit余裕最小12,199,641,088 Bもfloor内。

外部control4,800ファイル / 129,026,491 Bとindexを含む入力は既存256 MiB上限内で、外側4 rootのdirectory量とは別の入力scope。終了時にはこのcontrol pinを再照合し、生成元22 payload / 131,144,119 Bとsubsetの10 controlも再読取りした。最終source57・runtime一致を外側時計内で確認した。今回の空き容量観測は、正式smokeによる同形見積りの2倍以上という受入条件の完了証拠ではない。

## 別保存checkerとidentityの限界

stdlibのみの保存checkerで**4,950 raw／57 selected Git source**を照合し、各成分のcount・histogram・全sliceを再集計、全文書・5公開payload・marker、controlの読取り／終了時照合、全7 workerの終了・外側／内側予算・scopeを検証してpass。profile／score／bootstrap CIをchecker自身が再計算したという主張ではない。science planとfreeze registryの既存hash一致も別checkpointで確認した。

checker初回は、全7役に`start_token`があると仮定した集計でKeyErrorになった。analysis／auditの現receiptにはPID・元Popenによるsupervision・終了があり、creation token欄はない。初回scriptを`postcheck-initial.py`へ保全し、7 PID／終了と、記録のある5役のcreation tokenを確認する形へ修正した。製品code・実機試行は繰り返していない。2役のcreation token未保存という事実を保持し、正式契約で必要なidentity証拠の受入範囲を確定する。完全な実行認証へ読み替えない。

保存rootは `artifacts/anomaly-v03-preformal-generation-publication-20261006-e04/`、`...registered-attempt-e04/`、`...saved-row-reread-20261006-e04/`、`...saved-row-document-budget/trial-20261006-04/`。helperは `artifacts/anomaly-v03-generation-publication-20261006-a4/`。rawはignoredのローカル保存で、Git pushには含めない。

| raw | bytes | SHA-256 |
| --- | ---: | --- |
| outer `result.json` | 23,978 | `b190a91f3ed47d45c719071d861f609f1e0a4fe1c4680adfcf6a97c966f58eab` |
| outer `resource-budget.json` | 7,020 | `f150594aad0be35c35625dafcb6417127d35599dcc89ed3d3613f6a45072aaf6` |
| publication `result.json` | 37,804 | `b0379ab5f978d93ee4b3b5bd2352477fffbe2024bd4ea5ea593f5c54e3e4ee63` |
| publication `resource-budget.json` | 7,107 | `02269aefdb4f073c75643169bd1e1661035808ed22d5ecbab571597821f8345d` |
| generator manifest `pins.json` | 75,734 | `d9c0e611a4ea295da5b3139d786cf749b38bc433f1548be18806377ac981d079` |
| helper `request.json` | 2,020 | `1e4ea4f396430f19a7d1470d33bbd0be66dc28fe10de319d0c50eca72999b8e1` |
| helper `execution.json` | 542 | `914dd83fda5a6b4714668195b24a23f7bc96b24d41c2b9b0ba1298421eccf957` |
| helper `postcheck.json` | 864,545 | `d4520982288a295b89858d3872a0cb9c570209389cf80d605f8ed485eae426d4` |

calculation68,225 B / `5526fc0edad2739106e800171d79d4c5e72558d9b56ca9643d89a9455a7a2cd6`、算術audit566 B / `23ac0cfed91dceccf4181d91d0c77aec35885da9f3388cc3446aee752b68cec2` は同じ数値recipeのe03と一致し、今回は新しい2 workerで再計算・監査した。文書・sliceのpinは今回revisionへのbindingを含む新規結果。marker SHAは `b6a4a860eb53682b007801c5770f6203e5bb3fd1749452c8e4b8ed8ea27ff4a8`。

## CIと正式受入の残り

改善code `fa33314` の [CI37419094201](https://github.com/tyaro/banto-ai/actions/runs/37419094201) は全3job成功。両minor各3,001件・fail0/error0/skip237、共有29 fixture一致・必須28試験pass。外部HEAD/workflow/run/attemptを固定した全journalの保存再検証もpass。完了時9 rawと先行Python3.14 partial2 rawを保全した。[CI診断](anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)。CIのfull HEADは`fa33314`、今回nativeのfull HEADは文書commit後の`02d567f`として区別する。

次は正式smokeに基づく容量2倍の根拠、source/runtime全在庫と元handle identityの受入範囲、改訂運用契約／保証A・runner同定の採択候補を整える。その後に最終revisionのLinux/Windows・正式dev8/smoke2・独立受入へ結ぶ。今回の限定完走だけでS4採択やS5開始を許可しない。追加agentなし、実機試行1件、全worker・sampler・保存checkerは終了済み。
