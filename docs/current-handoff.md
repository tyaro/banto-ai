# 次のタスク用の短い引継ぎ

2026-10-07 JST。branch `codex/preformal-acceptance-scope`、repository `D:\develop\banto-ai`。

## 現在の状態

- 外部program/異常子孫の[残件source監査](results/anomaly-multiseed-v0.3-external-process-acceptance-gaps-2026-10-07.md)を追加。選択15 sourceはworking/6f1270f/343c863 raw一致。裸のGit構文16箇所、実7役は直接supervisor、既存Git Job v7はcandidate profile非接続。次の小さい実装境界と拒否/停止試験を整理し、新native0。raw監査5,938 B / `1624adfb0966372c1e9441d79ab1a625e5990f0cfbdb621f1a4cfcd2049aa3cf`。

- runner由来候補検証器v2を保存: jobごとのimage版、gh log prefix、外部prerelease状態、release/READMEの単一宣言を照合。焦点47件pass・対象11 pin一致、旧CI37498814612/37485069436の保存bytesと全journalはconsistent_candidate。候補は未採択・digest未取得。[証拠索引と受入5残件](results/anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md)。証拠索引JSON26 file/source pinは5,449 B / `9a09fb81414bad36feb91bac6738536961e234e19edc97904178b946cf03ffd9`。

- 最新業務runtime code保存点: `343c8639b0acfb2be535c02b5aaf4288b8f3d43e`（producer/initial-reader在庫・元handle・common接続）。clean同HEAD r7で全7役/14 phase、103 source/全stdlib2,559、exit0/回収・親post-exitを確認。架空1区間22 payload131,144,118 B＋479 metadataから40 cluster/50,000 draw・全文書・5 payload公開まで外側690.576/1,800秒・内側352.931/1,200秒でpass。別runtime checker57 raw/103 source、集計checker4,974 raw/60 source pass。焦点108件/14.067秒・fail0/error0/skip1・対象15 pin一致、safety pass。正式経路・全source/runtime閉包・最終受入は未了。
- 正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0。登録holdout40 seedは未読。実設備・顧客データは対象外。
- 実データ作業は保存済み合成dev8/smoke2、120区間・240 dataset・720評価のengineering読取り・記述報告まで。新native試行は架空入力のみ。
- 追加agent0。全7 worker・sampler/monitor・2 checker・焦点試験は終了。全工程nativeは1試行。集計checker旧rootの残存は保全・別v2で保存証跡だけ再検証。先行3d2ebfbのCI37498814612は全3job成功・両minor各3,051件・10 raw保存/local verifier照合pass、新codeへ代用しない。runner2版の公式release/READMEもpin保存したがVM digest/正式採択なし。10時JSTまでheartbeat banto-10で小さい保存単位を継続し、到達後は新規実行を開始しない。

## 正式評価を始める条件

[凍結計画 §8–9](anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)と[受入範囲整理案 v3](anomaly-v03-s4-acceptance-scope-draft-v3.md)を参照する。v3は未採択の範囲整理で、S4合格や正式許可ではない。

1. **運用契約採択**: 現26H2/build26300/UBR9457、公開保証A/B、root/schema、revision、slice/sidecar、失敗・再登録規則、runner同定を版付き改訂・独立監査へ結ぶ。旧25H2正式pinは不一致のまま。
2. **入力/consumer接続**: 登録40 seed・480区間・960 dataset・2,880評価の保存形式、latest attempt、由来・終了を固定入力で検証し、全分母・slice/sidecar・50,000 draw・全文書へ接続する。
3. **source/runtimeと終了**: 5役＋初期/保存readerの最終clean source、stdlib/拡張/DLL/CRT/外部program inventoryと実行境界、業務workerの元handle・identity・exit/reap、異常時子孫回収を照合する。
4. **最終受入**: 最終revisionでUbuntu24.04/Python3.12・3.14、Windows26H2/Python3.14 native、正式dev8/smoke2全layout/両層/3候補、独立受入を完了する。
5. **共通予算と容量**: 生成→保存reader→50,000 draw全文書→独立audit→staging/writer→fresh readerを同じ外側予算で測り、smokeに基づく正式同形見積りの2倍以上の空きを確認する。

採択後にS5の未使用holdout40 seedを新rootで一回実行し、S6独立再導出、S7結果文書へ進む。実S5成功/実S6完了をS4開始前の前提にしない。

v3では、メモリ内コードの完全認証、conhost等の全補助processの個別exit code、未採用prototypeの全統合、架空480区間完走を追加必須にしない案を提示した。実ロード依存在庫と業務worker終了・子孫回収は維持する。DACL/独立tokenは保証Bなら必要、保証Aへ変更するには版付き改訂・独立監査が必要。旧fixtureのfalse flagは変更しない。

## 最新の実装・証拠

[正式受入前の証拠索引・runner v2](results/anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md): 先行CI各jobの実版を公式tagへ結合。20261004.327.1は保存時prerelease=trueを明記。最終revisionのCI/nativeや契約採択を意味しない。最新native文書HEAD21d3866のCI37547050883は索引作成時in_progress。

[全7役runtime・共通予算native](results/anomaly-multiseed-v0.3-seven-role-runtime-common-budget-native-2026-10-07.md): 343c863で同じouter clockに7役・14phaseの在庫と元handle/exitを結び、公開後のcontrol/元22 payload/phase/source再照合までpass。正式source/runtime閉包・契約・入力経路・最終dev/smoke・独立受入・全容量2倍は残る。

[saved-reader runtime native](results/anomaly-multiseed-v0.3-saved-reader-runtime-observation-native-2026-10-07.md): clean799145aで103 source・stdlib2,559 file・loaded各phase324 file/212 module/47 native、元handleと両phase、exit0/回収・親post-exitを照合。旧22 payload131,144,119 B・6評価再導出・行投影pin維持。child59.090/300秒・1 GiB上限、root呼出77.399/120秒。別checker41保存raw・103 source・旧22 payload pass。producer/initial-readerと同revision全7役native、外部program/異常子孫回収・正式受入が残る。

[writer/fresh reader runtime native](results/anomaly-multiseed-v0.3-publication-runtime-observation-native-2026-10-06.md): clean b2a6065で75 source・stdlib2,559 file・loaded各phase332 file/217 module/47 nativeを外部pinへ照合。元handle identityとexit/reap、旧数値source/worker sourceの区別、5旧payload pin一致、2役45.365/19.426秒、共有96.187/300秒を確認。別保存checker40 raw/75 source pass。初回準備とcheckerの仮定違いは保全して限定修正。登録holdout未読・正式flag false。

[算術runtimeの共通予算接続](results/anomaly-multiseed-v0.3-arithmetic-runtime-common-budget-wiring-2026-10-06.md): `dfa61e8`で両roleの外部raw pin・role/root/full revisionをnew root前に保持し、共有時計内で現tuple/選択Git source照合・exclusive保存・実owner/verifierへ伝播・公開後phase再読取りを追加。公開側のchecked欠落・pin差替えは外側もfailed。固有109件pass、正式flagはfalse。producer/3 reader/writerの在庫境界と新接続のnative全工程は残る。

[実analysis/audit runtime在庫接続](results/anomaly-multiseed-v0.3-arithmetic-runtime-observation-native-2026-10-06.md): 実入口の任意profile optionへsource/raw、全stdlib、loaded import/DLL/拡張を結び、役割・operation/root/full SHA・外部pin、親の元handle identityとchild両phase、exit0・回収・親post-exit diskを照合。clean `af3e7a5`のa3は2役67.707/127.653秒、共有214.717/900秒・819 samples・資源pass。71 source、stdlib2,559 file /51,017,552 B、各phase loaded324 file /213 modules /47 nativeで旧calculation/audit pin一致。別stdlib保存checker pass。準備a1の入力pin取り違えとa2の旧v0.1設定Git/raw不一致はworker起動0で停止し、実ロード・実入口・科学pinの71 sourceへ範囲を固定してa3を実行した。原失敗は保全。新全工程callerへのprofile伝播、producer/3 reader/writer、外部program在庫・異常子孫回収、正式契約・最終受入は残る。

[旧smoke容量とruntime接続残件](results/anomaly-multiseed-v0.3-saved-smoke-capacity-and-runtime-scope-2026-10-06.md): 旧smoke24区間全attempt1,294 file /3,326,135,758 Bと共有control・独立監査48報告、計2,856 file /3,339,899,260 Bを実bytes/hash照合。2,862入力のpostflight identityを確認、別checkerもpass。区間119 failed attempt133,130,961 Bも含む。20倍換算62.210 GiB、部分2倍124.421 GiBに対しD空き329.674 GiB。正式analysis・追加audit・staging・診断予約はnullで、正式容量合格は未了。旧25H2の測定で最終26H2 smokeを代用しない。当時e04の57 selected sourceとworking bytes一致を確認（現codeの一致ではない）、7 PID/exitを保存reviewし、実5役＋追加readerへ全stdlib/loaded/外部program在庫を結ぶ箇所を整理した。rawは`artifacts/preformal-smoke-capacity-20261006-a1`（初回hardlink仮定で停止）・`a2`（修正成功）へ保存。

[共通外側予算e04の完走](results/anomaly-multiseed-v0.3-generation-publication-success-native-2026-10-06.md): clean `02d567f`で架空1区間22 payload / 131,144,119 Bの生成→2 reader→479架空metadataを含むcontrol入力→40 cluster・50,000 draw→算術監査→文書／slice→writer→fresh reader→control／元22 payload／subset10 control／57 source・runtime最終照合を外側528.308/1,800秒・内側288.905/1,200秒で完了。全7 worker exit0・回収、sampler／monitor終了、資源stopなし。4,950 raw／57 sourceの別checkerもpass。初回checkerのcreation token欄の仮定違いは保全・修正し、7 PID／終了と5役のtokenを確認。analysis/auditにはtoken receipt欄がなく、正式契約でidentity証拠の受入範囲を確定する。正式容量2倍・全在庫・契約採択・最終dev/smoke／独立受入は未了。全480区間の観測確認ではない。

[writer count検証の整理と再測定](results/anomaly-multiseed-v0.3-writer-count-optimization-native-2026-10-06.md): clean `fa33314`で生count→記述表→生countの往復と監査内の重複集計・hashを整理した。固定inventory・分母・partition・欠測・joint対応・全導出結果・4回の境界検証を維持し、別監査は計算側関数に依存しない。writer限定9.681/60秒・exit0・回収、slice mapping計3.810秒・count監査計2.053秒、上限余裕50.319秒。旧入力・5 payload pinとmarker一致、171 raw／43 sourceの別checker pass。焦点21件は改変がno-opだったテスト1件を修正し、legacy/raw30件と最終raw3件は別runでpass。負荷が同一でないので全時間差をcode効果とは断定しない。今回CI37419094201は全3job成功・保存再検証完了（下記）。owned fresh reader・共通外側予算は今回未実施。

[保存済み入力のwriter限定時間計測](results/anomaly-multiseed-v0.3-writer-timing-native-2026-10-06.md): clean `a8df865`で元e03の11入力pinと数値由来`8cac6fa`を維持し、writerだけを既存60秒上限で56.561秒・exit0・回収・5 payload公開。4回のslice mapping計28.509秒、独立count監査計11.966秒、上限余裕3.439秒。171 raw／43 sourceの別保存checkerがpass。初版のruntime引数漏れはworker起動0件でfailedを保全し、23 raw／43過去sourceを照合した。焦点試験は固有22件（重複を含む28実行）pass、修正後2件は別runでpass。owned fresh reader・共通外側予算・生成／draw再計算は未実施。前回timeoutの原因は断定しない。同HEADのCI37398623472は今回保存再検証まで完了（下記）。

[共通予算のe03再試行](results/anomaly-multiseed-v0.3-generation-publication-retry-native-2026-10-06.md): clean `8cac6fa`で前回のkeyword不一致を通過。generator143.352秒、initial reader50.852秒、saved reader60.060秒（local全体63.610/120秒）、analysis215.674秒、audit593.520秒はexit0・回収。4入力pin一致、40 cluster／50,000 drawと算術監査、主文書／sliceの3 mappingまで完了。writerは60.614秒で既存60秒上限により停止・exit1・回収、fresh reader未起動。外側1,290.496/1,800秒・内側1,023.189/1,200秒、resource stopなし・sampler joinedだが全工程failed。4,944 raw／57 sourceの別保存checkerは成分のcount／slice再集計・5成功子と停止writerを含む全6起動子の終了を照合してpass。未実施の公開・終了時再照合を予算内成功へ読み替えない。writer時間内訳は上記の限定fixtureで保存した。上限を広げて全工程を反復しない。

[生成から公開までの共通予算接続](results/anomaly-multiseed-v0.3-generation-publication-budget-native-2026-10-06.md): 初版clean `feb32e5`でgenerator343.862秒、initial reader100.999秒、saved reader92.573秒（local全体99.235/120秒）、analysis109.217秒の4子はexit0・回収。22 physical file/131,144,119 B、6行、全体4入力pin一致を確認した後、終了記録のkeyword不一致でfailedを保全。外側773.987/1,800秒、resource stopなし・sampler joinedだが全工程成功ではない。46 raw／57過去Git sourceの失敗記録照合pass。初版56、identity追記後8、keyword修正後13試験は別runでpass。`da454ff`で修正済み・push済み、実機再試行未実施。e02/a2の期待pin準備だけを保存したが、文書commit後の新HEADへそのpinsetを読み替えない。

[部分観測行の全体fixture接続](results/anomaly-multiseed-v0.3-observation-subset-budget-native-2026-10-05.md): clean `ebdd4b9`で先行g02の6行を区間0だけに反映し、479区間は明示的なmetadata fixtureとして両由来・旧pin・失敗履歴を保持。4入力→40 cluster／50,000 draw→監査→文書／slice→writer/fresh reader→元control再照合を271.836/1,200秒で完了。4 worker exit0・回収、4,904 raw／40 sourceの別照合pass。全体fixtureはsuccess2,874・inconclusive6。専用9／接続21／旧projection11件は別runでpass。helper事前指定ミス2件は保全して別rootで修正。観測reader・producer・期待pin準備は時計外で、共通全工程予算・全480区間の観測確認ではない。

[保存attempt終了時照合](results/anomaly-multiseed-v0.3-saved-attempt-final-readback-native-2026-10-05.md): clean `2d4e378`で既存架空g02の22 physical file/131,144,119 Bをfresh owned readerで観測→profile・score→ledger・summaryまで再計算し、6行保存→22ファイル／保存行の終了時再照合を54.576/120秒で完了。reader PID2956・exit0・回収、15 source／53 rawの別照合pass。全6行は正当なinconclusive。焦点13・既存15試験は別runでpass。後段consumer（時計外）は1/480区間・1/12 layoutのpartialを保持し、40 cluster入力への変換を拒否。今回producer未起動、全480区間の観測由来・4入力／全工程予算へはまだ接続していない。

[control disk読取りを含む50,000 draw公開予算](results/anomaly-multiseed-v0.3-saved-control-budget-native-2026-10-05.md): clean `d997020`で架空480区間control4,800 files/129,026,491 Bのdisk読取り→40 cluster→全主算術／別process監査→文書／slice→5 payload公開→終了後fresh reader→disk再照合を共有280.645/1,200秒で完了。4 worker exit0・回収、4,841 raw／39 sourceの別照合pass。全966 control checkpointのsample/probeを維持し履歴を集約、budget receipt6,745 B。初版はreceipt64 KiB超過でfailedを保持。初版41試験・修正後16試験は別runでpass。外部controlは新rootのdirectory測定外・256 MiB input上限内、先行生成/期待pin準備は予算外。実producer/実保存reader、raw観測再導出・共通campaign実行認証・全工程予算・容量2倍は未了。前段[公開のみの証拠](results/anomaly-multiseed-v0.3-saved-row-publication-native-2026-10-05.md)と旧成功/failed rootは保持する。

[専用Git Job実機証拠](results/anomaly-multiseed-v0.3-git-private-job-native-2026-10-05.md): 5役を含む382 Git callの専用Jobは全てactive0。8 manifest、1,244 rawの別照合、Git起動禁止の保存verifierがpass。関連55試験、実Git・CLI子孫の正常/timeout/非zero、Unicode明示環境読戻しを確認。初回helper期待値ミス2件は失敗rawを保持し別rootで確認済み。

5役共有標本予算148.005秒/240秒、Job698 process・active0。この小fixtureは全工程正式同形予算ではない。Gitのloaded依存在庫、source/runtime期待値の固定、正式経路と共通予算の接続が残る。

過去履歴（先行共通算術profile接続CI）は `eebfa8095698f10366563eed9f4f6ba388b81131` の [CI37436807053](https://github.com/tyaro/banto-ai/actions/runs/37436807053)：全3job成功、両minor各3,026件・fail0/error0/skip237、共有29fixture/必須28試験pass。10 rawと両journal・3job logを保存、ローカルverifierとremote回帰結果が一致。[CI診断](results/anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)。runner版20260927.320.1、digest未取得・正式採択false。新writer/fresh reader code b2a6065へ代用しない。

## 次の着手と履歴

次はnative文書HEAD21d3866のCI37547050883とrunner v2 code HEAD6f1270fのCI37548282365の完成rawを保存し、各外部HEAD/workflow/run/attempt・全journalとrunner v2を照合する。文書のみの追補はCI起動を抑え、この2件を追跡する。producer/initial/saved readerを含む同revision全7役nativeは343c863で終了済みなので反復しない。次の実装残件は外部program/Git/helper在庫・異常子孫回収、正式登録入力consumer、版付き契約・runner代替同定の採択。最終同revisionのLinux/Windows・正式dev8/smoke2・独立受入と全容量2倍は残る。旧成功/失敗rootを保全する。追加agent・旧agent再活性化0、10時以降は新規実行0。

受入までの残件は、今回scopeの共通予算証拠を正式経路へ結ぶ受入、正式同形容量2倍、26H2・保証A/B・runner代替同定の改訂契約候補、正式source/runtime在庫、最終CI/native／正式dev8/smoke2・独立受入、独立raw観測再導出。1区間の架空観測と479区間metadataを同一campaignや全観測確認へ読み替えない。架空480区間の新規生成完走を自動追加の必須にせず、旧pin・由来・上限8 drawは維持する。最終revisionと独立受入の前にS5を開始しない。

詳細な残件と保存点は[受入表](results/anomaly-multiseed-v0.3-session-handoff-and-remaining-acceptance-2026-10-04.md)、過去408行の引継ぎは[保全した旧履歴](current-handoff-history-through-git-job-2026-10-05.md)。旧履歴は各保存時点の状態であり、最新判断は本書とv3を使う。
