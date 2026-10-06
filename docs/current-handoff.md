# 次のタスク用の短い引継ぎ

2026-10-06 JST。branch `codex/preformal-acceptance-scope`、repository `D:\develop\banto-ai`。

## 現在の状態

- 最新code保存点: `b2a6065f84c916bd32191d16ef2d4003b5a9e559`（writer/fresh reader runtime実境界・共通caller接続）。clean同HEADの限定runtime02で75 source・全stdlib2,559 file・実loaded前後・元handle identity・exit0/回収・親post-exit disk照合pass、旧e04の5 payload pin維持、96.187/300秒、別checker40 raw/75 source pass。数値由来02d567fは別欄に保持。固有132件・622.398秒・対象19 pin前後一致・safety pass。旧af3e7a5の算術2役a3、旧02d567fの共通e04、容量・失敗履歴は保全。新4役/全7役native通しは未実施。
- 正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0。登録holdout40 seedは未読。実設備・顧客データは対象外。
- 実データ作業は保存済み合成dev8/smoke2、120区間・240 dataset・720評価のengineering読取り・記述報告まで。新native試行は架空入力のみ。
- 追加agent0。まとめ試験132件・2公開worker・sampler/checkerは終了。生成や50,000 drawの再計算は0、長い全工程は反復していない。runtime01の準備JSON型不備はworker起動0で保全、別runtime02で修正成功。checkerのpayload配置仮定も原失敗を残し別check3で修正。前保存点eebfa80のCI37436807053は全3job成功・両minor各3,026件、10 raw保存/ローカルverifier照合pass。新b2a6065のCIへ代用しない。

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

最新の保存検証済みCIは共通算術profile接続を含む `eebfa8095698f10366563eed9f4f6ba388b81131` の [CI37436807053](https://github.com/tyaro/banto-ai/actions/runs/37436807053)：全3job成功、両minor各3,026件・fail0/error0/skip237、共有29fixture/必須28試験pass。10 rawと両journal・3job logを保存、ローカルverifierとremote回帰結果が一致。[CI診断](results/anomaly-multiseed-v0.3-preformal-ubuntu-ci-triage-2026-10-05.md)。runner版20260927.320.1、digest未取得・正式採択false。新writer/fresh reader code b2a6065へ代用しない。

## 次の着手と履歴

次は今回保存点のCI確認とproducer・初期reader・保存readerのruntime実境界接続を進める。analysis/auditとwriter/fresh readerの候補profileは共通callerへ伝播済みで、各2役nativeは別HEADの限定証拠として保全。新4役/全7役のnative通しは未実施。残る3役・外部program/Git/helper在庫、元handle identity・異常子孫回収、正式consumer/失敗拒否と版付き運用契約・runner同定を結ぶ。最終同revisionのLinux/Windows・正式dev8/smoke2・独立受入と全容量2倍は残る。旧成功/失敗rootを保全し、長い全工程を自動反復しない。

受入までの残件は、今回scopeの共通予算証拠を正式経路へ結ぶ受入、正式同形容量2倍、26H2・保証A/B・runner代替同定の改訂契約候補、正式source/runtime在庫、最終CI/native／正式dev8/smoke2・独立受入、独立raw観測再導出。1区間の架空観測と479区間metadataを同一campaignや全観測確認へ読み替えない。架空480区間の新規生成完走を自動追加の必須にせず、旧pin・由来・上限8 drawは維持する。最終revisionと独立受入の前にS5を開始しない。

詳細な残件と保存点は[受入表](results/anomaly-multiseed-v0.3-session-handoff-and-remaining-acceptance-2026-10-04.md)、過去408行の引継ぎは[保全した旧履歴](current-handoff-history-through-git-job-2026-10-05.md)。旧履歴は各保存時点の状態であり、最新判断は本書とv3を使う。
