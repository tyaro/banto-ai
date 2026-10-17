# v0.3 共通予算接続の実機再試行（2026-10-06）

## 結論

clean `8cac6fae93242747675fa67853a30a5e17ccef06`、修正code `da454ff`を含む新e03試行を1件実行した。前回の終了記録keyword不一致は通過し、生成→2 reader→50,000 draw計算→別process監査→文書・sliceまで完了した。

公開writerは既存60秒上限に達して停止・回収されたため、**試行全体はfailed**。fresh readerは未起動、公開完了markerはない。外側1,290.495843／1,800秒・内側1,023.189275／1,200秒はresource stopなし・sampler joinedだが、全工程成功には数えない。上限を広げて再実行していない。

正式gateは `s4_acceptance_not_frozen`、permission=false、credit0、登録holdout40 seed未読・未使用。観測データがあるのは固定hand-normal recipeの架空1区間／2 dataset／6評価のみ。残り479区間は明示的なmetadata fixtureで、全観測campaign確認ではない。実設備・顧客データを読んでいない。追加agentなし、試行終了時に起動した6 processはすべて終了確認済み。

## 実行と保存範囲

初版e01の失敗と未実行e02は保全し、新root・新外部manifest・新期待4入力を `8cac6fa`で準備した。旧e02 pinsetを新HEADへ読み替えていない。

- outer：`artifacts/anomaly-v03-preformal-generation-publication-20261006-e03/`
- producer：`artifacts/anomaly-v03-preformal-registered-attempt-e03/`
- saved reader：`artifacts/anomaly-v03-preformal-saved-row-reread-20261006-e03/`
- document/publication：`artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261006-03/`
- helper：`artifacts/anomaly-v03-generation-publication-20261006-a3/`

22生成物の期待pinの独立準備は139.500817秒で、外側時計より前。4数値入力は先行の独立照合済み同recipe／同区間fixtureを参照し、operation revisionを今回HEADへ固定した。生成・保存reader・control disk読取り・projection・全算術・監査・mapping・writerは共通外側時計内。各工程の既存local上限も維持した。[実装・上限と初版失敗](anomaly-multiseed-v0.3-generation-publication-budget-native-2026-10-06.md)を参照。

Windows26H2/build26300/UBR9457、CPython3.14.0。観測22 file／131,144,119 Bの期待pin一致、保存readerの観測→profile・score→ledger・summary再導出、初回reader全値との一致、6行保存、全22 fileの終了時再照合を確認。保存readerのlocal全体は63.609882／120秒でpass。

| 子process | PID | 秒数 | 結果 |
| --- | ---: | ---: | --- |
| generator | 23268 | 143.351811 | exit0・回収 |
| initial reader | 17620 | 50.851653 | exit0・回収 |
| saved reader | 32952 | 60.059586 | exit0・回収 |
| analysis | 35328 | 215.673617 | exit0・回収 |
| audit | 20760 | 593.520362 | exit0・回収 |
| writer | 16136 | 60.614018 | time_limit、exit1・回収 |
| fresh reader | — | — | 未起動 |

writer supervisionは `status=failed`、`stop_reason=time_limit`、`worker_exit_confirmed=true`、observation_errors=[]、stdout/stderr各0 B。writer個別上限は60秒／512 MiB／stdout64 KiB。parentの公開状態はunconfirmed、local publication=falseであり、停止したwriterを成功した公開者とは扱わない。

## 完了した成分と未完了部分

今回の6行はすべて正当なinconclusive。区間0だけを置換し、479区間metadataの元pin・由来・失敗履歴を保持した。全4入力は事前pinと一致、全体fixtureはsuccess2,874／inconclusive6、失敗履歴は区間479のattempt1・latest2を保持。

40 cluster・50,000 draw／2,000,000受入indexの計算と別process算術監査は検証済み。9 table／117 primary／72 paired／180 gate、主文書・slice mapping、1,233主slice行／2,835 diagnostic行／9詳細tableまで保存した。calculationとauditのraw SHAは先行の同数値fixtureと同じである。新観測のS6独立再導出や正式結果ではない。

writer停止より後のfresh reader、公開payload／marker照合、元4,800 controlの最後のdisk再読取、外側の公開後22 payload／10 control・source/runtime後照合は実行されていない。全工程のmeasured flagはfalseを維持した。下記の別保存checkerは時計終了後の照合であり、未実行だった工程を予算内完了へ読み替えない。

## 資源観測

外側4,593 sample、parent peak230,551,552 B、4新root合計peak141,847,467 B／93 entries／depth10。外側stop_reasonとobservation_errorはnull、resource `passed=true`・sampler joined。6役の終了記録は揃うが、writerはfailed、fresh readerは欠けるため `all_seven_child_exits_reported=false`。3 mapping pinは外側・内側で一致。

| システム観測（B） | 最初 | 最小 | 最後 |
| --- | ---: | ---: | ---: |
| commit余裕 | 15,471,321,088 | 4,437,069,824 | 8,799,739,904 |
| free RAM | 12,008,464,384 | 5,096,292,352 | 7,594,332,160 |
| free disk | 336,360,554,496 | 336,228,904,960 | 365,859,049,472 |

commit余裕の最小値は4 GiB floorより142,102,528 B大きい。システム資源の変動と各工程の所要時間を記録したが、writer timeoutの原因や因果関係は未確定。空きdiskの値だけで正式同形容量2倍を確認したとはしない。

## 保存checkerとCI

[failure-check.py](../../artifacts/anomaly-v03-generation-publication-20261006-a3/failure-check.py)はproduct import・reader／50,000 drawのreplayを行わないstdlib checker。元4,800 controlと今回6行から全240 seed/candidate/layer cellのcount・delay・slice・coverageを再集計し、主文書／slice mapping、22 physical payload、source working/Git57 file、5成功子のexit0、停止writerを含む6起動子の終了を照合した。**4,944 raw／57 sourceがpass**。公開完了とfresh reader開始はfalse、source/runtime完全在庫・in-memory code認証・S6完了は主張しない。

今回測定と同じ `8cac6fa` の [Ubuntu CI 37340158371](https://github.com/tyaro/banto-ai/actions/runs/37340158371) は全3job成功。Python3.12／3.14各2,988件・fail0/error0/skip237、共有29 fixture一致、必須28試験pass。外部HEAD/workflow/run/attemptを固定した全journalローカル再検証もpass。8 rawは `artifacts/ci-diagnostic-37340158371/complete/` とその親rootへ保全。新しい文書commitや正式最終受入の成功へ読み替えない。

raw artifactはローカルignored証拠で、文書commitと一緒にpushされない。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| outer result | 15,139 | `ffebb6798fb8072db653aba1bcb8b97a43f3e21585f3dbbd10fd69921a875d7f` |
| outer budget | 6,698 | `aab620b4f978c1d7a260be2c981e1a1068e0932187b73c8c9cb4fbac22d97c7d` |
| publication failed result | 14,000 | `c5f4b877b86579b3b05ffda3929faa7039662e9ffeda60fbaec92a5a6568ddae` |
| publication local budget | 6,360 | `0d7d2bac7261c5169bd76d812acbded6692f8547fa9e79f100753b7bd67fa67c` |
| external manifest | 75,734 | `88b1d3f080c88f17224668c866532f01ac3c32b96c699807126d54750a82a325` |
| request | 2,020 | `7f8228dc712f1ef2c6c010fa2d781d15d497f3a7ae79c4a55abac4fbc98490f9` |
| preparation record | 352 | `3b1bf02381166e50dd6c18efb86312dcb84c6d64e4ab61b068d3f22224e21479` |
| writer supervision | 2,198 | `e692f66b11850d2456be6e104b6392383fec5298bdeef4a3a7f00733f3e4fc49` |
| calculation | 68,225 | `5526fc0edad2739106e800171d79d4c5e72558d9b56ca9643d89a9455a7a2cd6` |
| arithmetic audit | 566 | `23ac0cfed91dceccf4181d91d0c77aec35885da9f3388cc3446aee752b68cec2` |
| document | 128,090 | `9b50abf72dde80705c751749aee960244501c2d9773b0a4d4a2fd989f4ae9c12` |
| slices | 1,972,118 | `810495ef0cf87ab95047e43a9de651d8ea77fb04490999bda38d47969c3e183b` |
| count audit | 1,244 | `1e9e1e5bcbbda641fbb4687a791f6fe16f6b72b74b5a5d57489626a1545006dd` |
| failed component checker | 24,708 | `6e7126f1072605e5d9f8056c2877c6d6a65a0c688d1e931140f44e92f6424572` |
| failure check report | 862,957 | `ec002fae91ac9a82ff9610e7be05116813aa459df5196a596275b788775cd02b` |
| CI summary | 3,827 | `3a9cf7f5fd0782014f94be8e8b596316d8c9b5bd5932679b95de74fcce669d26` |

## 次の有限作業単位と受入残件

次は保存済みの期待pin・文書／sliceを使い、**writerの所要時間を工程ごとに調べる限定fixture**を用意する。生成・50,000 drawを繰り返す前に、読取り／source検証／mapping再検証／staging・公開のどこで時間を使ったか確認する。新しいroot、明示した部分scope、同じ個別上限、終了・失敗保存を維持し、既存e03を上書きしない。限定writer試行を共通全工程予算の成功とは数えない。

writer・fresh readerを含む共通予算成功証拠、正式同形smoke見積りと2倍空き、26H2／公開保証A/B／runner同定の版付き契約採択、source/runtime全在庫、最終revisionのCI/native・正式dev8/smoke2全layout／層／候補・独立受入が残る。架空480区間の新規生成完走を追加必須にはせず、正式S5・holdout実行の許可は出していない。
