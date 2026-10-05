# 次のタスク用の短い引継ぎ

2026-10-06 JST。branch `codex/preformal-acceptance-scope`、repository `D:\develop\banto-ai`。

## 現在の状態

- 最新code保存点: `da454ff7fa6bd161432376ba8e39d7f581c4e205`（共通外側予算・終了記録keyword修正）。修正版を含むclean `8cac6fa`でe03 nativeを1件実行し、生成→2 reader→50,000 draw／監査→文書／sliceまで完了。writerの60秒上限でfailed、fresh reader未起動。本書の証拠追記は測定HEADより後の文書commitに保存する。
- 正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0。登録holdout40 seedは未読。実設備・顧客データは対象外。
- 実データ作業は保存済み合成dev8/smoke2、120区間・240 dataset・720評価のengineering読取り・記述報告まで。新native試行は架空入力のみ。
- 容量への配慮として追加agentを起動していない。今回も実機1試行と記録保存で区切った。チームの実行中agentは本体1体だけと確認。起動した6 worker・準備処理・保存checkerはすべて終了している。

## 正式評価を始める条件

[凍結計画 §8–9](anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)と[受入範囲整理案 v3](anomaly-v03-s4-acceptance-scope-draft-v3.md)を参照する。v3は未採択の範囲整理で、S4合格や正式許可ではない。

1. **運用契約採択**: 現26H2/build26300/UBR9457、公開保証A/B、root/schema、revision、slice/sidecar、失敗・再登録規則、runner同定を版付き改訂・独立監査へ結ぶ。旧25H2正式pinは不一致のまま。
2. **入力/consumer接続**: 登録40 seed・480区間・960 dataset・2,880評価の保存形式、latest attempt、由来・終了を固定入力で検証し、全分母・slice/sidecar・50,000 draw・全文書へ接続する。
3. **source/runtimeと終了**: 5役の最終clean source、stdlib/拡張/DLL/CRT/外部program inventoryと実行境界、業務workerの元handle・identity・exit/reap、異常時子孫回収を照合する。
4. **最終受入**: 最終revisionでUbuntu24.04/Python3.12・3.14、Windows26H2/Python3.14 native、正式dev8/smoke2全layout/両層/3候補、独立受入を完了する。
5. **共通予算と容量**: 生成→保存reader→50,000 draw全文書→独立audit→staging/writer→fresh readerを同じ外側予算で測り、smokeに基づく正式同形見積りの2倍以上の空きを確認する。

採択後にS5の未使用holdout40 seedを新rootで一回実行し、S6独立再導出、S7結果文書へ進む。実S5成功/実S6完了をS4開始前の前提にしない。

v3では、メモリ内コードの完全認証、conhost等の全補助processの個別exit code、未採用prototypeの全統合、架空480区間完走を追加必須にしない案を提示した。実ロード依存在庫と業務worker終了・子孫回収は維持する。DACL/独立tokenは保証Bなら必要、保証Aへ変更するには版付き改訂・独立監査が必要。旧fixtureのfalse flagは変更しない。

## 最新の実装・証拠

[共通予算のe03再試行](results/anomaly-multiseed-v0.3-generation-publication-retry-native-2026-10-06.md): clean `8cac6fa`で前回のkeyword不一致を通過。generator143.352秒、initial reader50.852秒、saved reader60.060秒（local全体63.610/120秒）、analysis215.674秒、audit593.520秒はexit0・回収。4入力pin一致、40 cluster／50,000 drawと算術監査、主文書／sliceの3 mappingまで完了。writerは60.614秒で既存60秒上限により停止・exit1・回収、fresh reader未起動。外側1,290.496/1,800秒・内側1,023.189/1,200秒、resource stopなし・sampler joinedだが全工程failed。4,944 raw／57 sourceの別保存checkerは成分のcount／slice再集計・5成功子と停止writerを含む全6起動子の終了を照合してpass。未実施の公開・終了時再照合を予算内成功へ読み替えない。次は保存入力を使う限定writer時間内訳fixtureで、上限を広げて全工程を反復しない。

[生成から公開までの共通予算接続](results/anomaly-multiseed-v0.3-generation-publication-budget-native-2026-10-06.md): 初版clean `feb32e5`でgenerator343.862秒、initial reader100.999秒、saved reader92.573秒（local全体99.235/120秒）、analysis109.217秒の4子はexit0・回収。22 physical file/131,144,119 B、6行、全体4入力pin一致を確認した後、終了記録のkeyword不一致でfailedを保全。外側773.987/1,800秒、resource stopなし・sampler joinedだが全工程成功ではない。46 raw／57過去Git sourceの失敗記録照合pass。初版56、identity追記後8、keyword修正後13試験は別runでpass。`da454ff`で修正済み・push済み、実機再試行未実施。e02/a2の期待pin準備だけを保存したが、文書commit後の新HEADへそのpinsetを読み替えない。

[部分観測行の全体fixture接続](results/anomaly-multiseed-v0.3-observation-subset-budget-native-2026-10-05.md): clean `ebdd4b9`で先行g02の6行を区間0だけに反映し、479区間は明示的なmetadata fixtureとして両由来・旧pin・失敗履歴を保持。4入力→40 cluster／50,000 draw→監査→文書／slice→writer/fresh reader→元control再照合を271.836/1,200秒で完了。4 worker exit0・回収、4,904 raw／40 sourceの別照合pass。全体fixtureはsuccess2,874・inconclusive6。専用9／接続21／旧projection11件は別runでpass。helper事前指定ミス2件は保全して別rootで修正。観測reader・producer・期待pin準備は時計外で、共通全工程予算・全480区間の観測確認ではない。

[保存attempt終了時照合](results/anomaly-multiseed-v0.3-saved-attempt-final-readback-native-2026-10-05.md): clean `2d4e378`で既存架空g02の22 physical file/131,144,119 Bをfresh owned readerで観測→profile・score→ledger・summaryまで再計算し、6行保存→22ファイル／保存行の終了時再照合を54.576/120秒で完了。reader PID2956・exit0・回収、15 source／53 rawの別照合pass。全6行は正当なinconclusive。焦点13・既存15試験は別runでpass。後段consumer（時計外）は1/480区間・1/12 layoutのpartialを保持し、40 cluster入力への変換を拒否。今回producer未起動、全480区間の観測由来・4入力／全工程予算へはまだ接続していない。

[control disk読取りを含む50,000 draw公開予算](results/anomaly-multiseed-v0.3-saved-control-budget-native-2026-10-05.md): clean `d997020`で架空480区間control4,800 files/129,026,491 Bのdisk読取り→40 cluster→全主算術／別process監査→文書／slice→5 payload公開→終了後fresh reader→disk再照合を共有280.645/1,200秒で完了。4 worker exit0・回収、4,841 raw／39 sourceの別照合pass。全966 control checkpointのsample/probeを維持し履歴を集約、budget receipt6,745 B。初版はreceipt64 KiB超過でfailedを保持。初版41試験・修正後16試験は別runでpass。外部controlは新rootのdirectory測定外・256 MiB input上限内、先行生成/期待pin準備は予算外。実producer/実保存reader、raw観測再導出・共通campaign実行認証・全工程予算・容量2倍は未了。前段[公開のみの証拠](results/anomaly-multiseed-v0.3-saved-row-publication-native-2026-10-05.md)と旧成功/failed rootは保持する。

[専用Git Job実機証拠](results/anomaly-multiseed-v0.3-git-private-job-native-2026-10-05.md): 5役を含む382 Git callの専用Jobは全てactive0。8 manifest、1,244 rawの別照合、Git起動禁止の保存verifierがpass。関連55試験、実Git・CLI子孫の正常/timeout/非zero、Unicode明示環境読戻しを確認。初回helper期待値ミス2件は失敗rawを保持し別rootで確認済み。

5役共有標本予算148.005秒/240秒、Job698 process・active0。この小fixtureは全工程正式同形予算ではない。Gitのloaded依存在庫、source/runtime期待値の固定、正式経路と共通予算の接続が残る。

最新の保存検証済みCIは今回測定と同じ `8cac6fa` の [CI 37340158371](https://github.com/tyaro/banto-ai/actions/runs/37340158371)：全3job成功、両minor各2,988件・fail0/error0/skip237、共有29fixture/必須28試験pass。8rawと全journalを保存・ローカル再検証済み。[CI診断](results/anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)。今回writer timeoutや後続文書commit、正式最終受入の成功には読み替えない。

## 次の着手と履歴

次はe03の保存文書／sliceと期待pinを使い、writerの読取り・source検証・mapping再検証・staging／公開の時間内訳を調べる限定fixtureを用意する。新root・明示した部分scope・同じ個別上限・失敗と終了保存を維持する。原因は未確定で、時間上限の変更や長い生成／50,000 draw再試行を自動追加しない。限定writer試行を共通全工程成功へ読み替えない。旧e01・未実行e02・failed e03を保全する。

受入までの残件は、共通全工程予算の成功証拠、正式同形容量2倍、26H2・保証A/B・runner代替同定の改訂契約候補、正式source/runtime在庫、最終CI/native／正式dev8/smoke2・独立受入、独立raw観測再導出。1区間の架空観測と479区間metadataを同一campaignや全観測確認へ読み替えない。架空480区間の新規生成完走を自動追加の必須にせず、旧pin・由来・上限8 drawは維持する。最終revisionと独立受入の前にS5を開始しない。

詳細な残件と保存点は[受入表](results/anomaly-multiseed-v0.3-session-handoff-and-remaining-acceptance-2026-10-04.md)、過去408行の引継ぎは[保全した旧履歴](current-handoff-history-through-git-job-2026-10-05.md)。旧履歴は各保存時点の状態であり、最新判断は本書とv3を使う。
