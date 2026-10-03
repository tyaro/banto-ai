# v0.3 全工程予算の証拠台帳と不足測定（2026-10-03、案1）

対象は正式開始前の予算受入である。基準となる文書保存点は `03f34908ecfb4894d45670e0359f1617c1b51b1b`。本書は既存の保存記録を工程別に対応づける**未採択の台帳**であり、上限の変更、正式実行の許可、S4/S6の合格を行わない。ここで「実データ」と記す保存済みdev/smokeは合成信号の成果物で、実設備・顧客データではない。[正式評価前の受入表](anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)の「全工程予算」に対応する。

2026-10-04 追記：[架空40 cluster・50,000 drawの別測定](anomaly-multiseed-v0.3-preformal-platform-raw-budget-2026-10-04.md)で、主算術101.580秒・独立算術245.902秒、両子exit 0/回収、9表・117主推定・72対応差・180 gate一致を保存した。これは下表の工程3の**算術部分**と工程4の**推論算術照合部分**の限定測定である。正式入力reader、完全S6、全payload公開、5役割のfull closure、連続した全工程予算は依然として未測定・未採択であり、旧fixture workerの8 draw上限も変わらない。

2026-10-04 再測定：[現行の受入見取り図とraw pin](anomaly-multiseed-v0.3-preformal-profile-and-saved-attempt-2026-10-04.md)に、clean code `94be9ed`の５役trial-15/16と、trial-16保存済み架空producerを外部固定して50,000 drawの主/別監査算術子へ接続したbridge trial-03を保存した。trial-16は架空40 cluster・**1 draw**で５子exit 0/回収、候補profile前後一致、外側73.532秒/274標本pass。bridge trial-03は主52.172秒・監査116.361秒、両子exit 0/回収、外側170.414秒/653標本pass。独立postcheckは全pin、2,000,000 draw hash、117主推定count/point・72対応差point・180 gate参照pointで差異0。quantile区間とgate合否の再計算は保存済み別監査子に依拠する。２試行は別の外側予算であり、保存済み登録形式reader、文書、完全S6、公開/読戻しを含む連続全工程に加算しない。

## 数値の性質と適用範囲

| 区分 | 保存された根拠 | この台帳での扱い |
| --- | --- | --- |
| 旧producer実績 | 合成dev 8 seed・smoke 2 seed、120区間・240 dataset・720評価の完走保存点。7,800 fileのサイズ索引は16,081,676,236 bytes（約14.98 GiB）、累積活動時間160,357.174秒（44.54時間）。失敗attemptやhardlink名を含む論理bytesで、物理割当量ではない。[容量・時間調査](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md) | 実測。呼出し間の休止や外側の一部処理を含まず、正式40 seedの予算ではない |
| 旧producerの単純外挿 | 40 seed・480区間・960 dataset・2,880評価へ4倍すると約59.91 GiB、累積178.17時間。同調査で生成/丸め監査113.560秒→約7.57分、profile/score/ledger監査1,196.096秒→約80.41分も別に外挿した | 固定長・同じ候補数・逐次実行を仮定する**シナリオ**。失敗、負荷、全S6、50,000 draw、公開を含む確定値ではない |
| 旧未採択案 | producer活動240時間、run出力96 GiB、空き32 GiB。開始時空きは1コピー128 GiB、同一volumeの2コピー224 GiBという案。[容量・時間調査](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)、[source/runtime計画](../anomaly-v03-consumer-source-runtime-plan.md) | **未適用・未採択**。producer以外の工程の時間・private memoryを埋める値ではない |
| 既存engineering制御 | `anomaly_v03_budgeted_run.budget()` の48時間/32 GiB、controller private 2 GiB、producer 900秒/2 GiB、audit 600秒/1 GiBなど。[保存結果](anomaly-multiseed-v0.3-budgeted-run-2026-09-21.md)、[実装](../../src/banto_ai/anomaly_v03_budgeted_run.py) | 合成dev/smokeの区間境界での協調的制御。controller/process treeのhard quotaでも正式全工程の上限でもない |
| 小fixture共有制御 | 40架空cluster・4 drawのanalysis→auditは23.623秒、親harness peak 121.75 MiB、子peak 66.09/46.81 MiB、新root最大11.26 MiB/54 entries、commit最小余裕12.85 GiB。共有120秒・親512 MiB・directory32 MiB・子60秒/256 MiB等でpass。[資源停止結果](anomaly-multiseed-v0.3-fixture-resource-budget-2026-10-01.md) | 対象rootと2子の限定試験。正式2,880評価・50,000 drawの測定値ではない |
| 保存済み要約・報告 | 合成dev/smoke全720評価の新reader要約は3試行の全体観測2,806.091/1,243.560/1,087.228秒。別の報告・4payload公開・writer終了後readerは8.447秒、親peak private75,059,200 bytes、新directory最大11,087,861 bytes。[実適用結果](anomaly-multiseed-v0.3-real-saved-summary-report-2026-10-03.md) | 保存済み評価の**再読取りと記述報告**。producer・正式推論・全S6を起動しておらず、3試行を1つの連続予算とみなさない |

これらを加算して全工程予算とは呼ばない。特にproducerの44.54時間、要約の3試行、fixtureの4 drawは、入力規模、コード経路、監視root、試行単位が異なる。区間56・82の子は120秒上限で停止して別試行へ進み、失敗成果を採用しなかった。区間56の記録上の経過905.577秒の原因は断定できない。[実適用結果](anomaly-multiseed-v0.3-real-saved-summary-report-2026-10-03.md)

## 工程別の証拠、不足測定、停止条件

下表はS4採択前の架空・最終dev/smokeによる測定と、S5/S6後だけ可能な実holdout照合を区別する。現時点で全項目が実装・採択済みという意味ではない。正式失敗後の別version/root/未使用seedによる再登録規則も[運用契約案](../anomaly-v03-consumer-io-proposal.md)の段階である。既存dev/smokeの別attempt再試行を、正式holdoutの同一seed再試行許可へ読み替えない。

| 工程 | 現在の保存証拠 | S4採択前の測定・停止／S5後の実測境界 |
| --- | --- | --- |
| 1. 登録入力、producer、保存 | 旧合成720評価の14.98 GiB/44.54活動時間。既存workerは900秒/2 GiB、旧区間119 attempt1は時間停止し、system commit余裕約52.73 MiBの標本が残ったが因果は未確定。[容量・時間調査](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)。別の架空22 file/126,317,406 Bは所有**コピー**子→別reader子で保存・照合済みだが、観測生成子の証拠ではない | S4前には固定架空入力と最終dev8/smoke2から、480区間・2,880評価**相当**の1区間/全工程経過、論理bytes・物理/volume空き、controller/子peak private、RAM/system commit余裕、失敗attempt保全量を見積り、式・実測根拠・開始余裕と停止点を固定する。実holdout全件の実消費測定はS5後。source/runtime/入力変化はglobal integrity failureとして後続を開始しない。失敗後は元attemptを上書きせず、採択した規則に従い新version/root/seedを登録する |
| 2. 保存済み入力の認証、coverage、要約 | dev/smoke全120区間・720評価を新readerで再読取り・完全結合し、旧独立監査と照合済み。成功59+26+35区間の3試行、失敗56/82は別記録。[実適用結果](anomaly-multiseed-v0.3-real-saved-summary-report-2026-10-03.md) | 正式40 seedの全slot、最新attempt、登録入力bytes、producer終了記録を最終consumerへ渡す実経路を固定入力で検証し、読み込み時間、逐次/peak private、再照合bytes、出力容量を測る。欠落・重複・混入・source/runtime差があれば結合を停止し、未検証slotを成功へ補完しない。入力変更は新しい登録として扱う |
| 3. 正式推論・50,000 draw | 架空40cluster/4 drawの旧数値workerは文書1,932,543 bytes。旧fixture workerの上限は8 draw。[数値worker結果](anomaly-multiseed-v0.3-fixture-worker-2026-10-01.md)。別経路のtrial-03は保存済み架空producer入力から50,000 draw主算術を52.172秒/子peak private 126,230,528 Bで測定したが、文書・全payload公開を含まない | 最終固定アルゴリズム・40cluster・50,000 drawを**登録holdoutを使わない固定fixture**の文書/公開まで含めて測り、draw数の完全性、elapsed、子/親peak private、system commit、stdout/stderr、全payload容量、失敗時の部分出力を記録する。drawを間引いて正式成功とせず、上限・資源余裕が不足したら所有子を停止/終了確認して失敗を保全する。反復数や科学条件を下げる場合は新しい計画・登録が必要 |
| 4. read-only独立S6監査 | 旧720評価の別生成/丸め監査とprofile/score/ledger監査、架空4 drawの主9表・180 gate別算術検算、架空slice/sidecar検算は保存済み。[容量・時間調査](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)、[主集計監査](anomaly-multiseed-v0.3-fixture-numerical-audit-2026-10-01.md)、[slice監査](anomaly-multiseed-v0.3-fixture-slice-audit-2026-10-01.md)。trial-03の50,000 draw別算術子は116.361秒/peak 29,765,632 Bでexit 0/回収 | S4前には最終独立実装の登録形式を固定架空入力と最終dev/smokeで検証し、profile/score、support/episode、全母数、50,000 draw/CI/gate/選択、slice/sidecar、全文書の再導出時間・peak private・commit・入力走査量・監査root容量を測る。実holdout観測の全件再監査はS5後のS6。解析rootとaudit rootを分け、未照合/未reap/不一致時は公開・trustへ進めず、元結果や旧receiptを修正しない。再開時に監査を再利用するなら対象bytes・scope・source/runtime・外部pinの独立した契約が要る |
| 5. staging、公開、native保護 | 架空5payloadの通常writer→終了→別readerは10.801秒、元1,987,587 bytes、公開1,987,592 bytes、親peak61.01 MiB、writer peak49.89 MiB、観測directory最大2.84 MiB/39 entries、commit最小余裕26.27 GiB。[結合公開結果](anomaly-multiseed-v0.3-bound-fixture-publication-2026-10-02.md) | S4前には固定架空5payloadの正式同形公開と失敗・再公開経路について、stage/receipt/marker/監査結果の最大論理bytes、必要な一時複写とvolume空き、flush・no-replace確定の時間とprivate/commitを測る。DACL工程を維持する案ならその資源も別測定する。既存rootを上書きせず、公開失敗のstage/partial証拠を保全する。旧計画のprotected DACL・独立token AccessCheck等は現通常writerの実測で代替せず、契約改訂とnative受入の対象に残す |
| 6. 公開後の別reader・差分確認 | 上記fixtureの別readerはexit0/reaped、peak49.49 MiB。合成dev/smokeの4payload報告もwriter終了後readerまで通過。[結合公開結果](anomaly-multiseed-v0.3-bound-fixture-publication-2026-10-02.md)、[実適用結果](anomaly-multiseed-v0.3-real-saved-summary-report-2026-10-03.md) | S4前には正式同形の固定架空全payloadを別process/tokenでfreshに全hash・schema・意味/差分照合し、時間、読取bytes、peak private、commit余裕、終了状態を測る。marker単独で成功にせず、読取失敗は公開済みbytesを変更せず外側の失敗receiptへ残す。独立tokenを要求する旧計画との差分を採択するまで正式受入にしない |
| 7. 統合監視、停止、再開 | 小fixtureには共有monitorがある。既存producer側48時間/32 GiBは区間境界の協調制御。[資源停止結果](anomaly-multiseed-v0.3-fixture-resource-budget-2026-10-01.md)、[予算付き継続結果](anomaly-multiseed-v0.3-budgeted-run-2026-09-21.md)。５役trial-16は73.532秒/274標本、50,000 draw２算術子のbridge trial-03は170.414秒/653標本でそれぞれpassしたが、外側予算は別々 | producer→consumer→50,000 draw→独立監査→staging/公開→readerをまたぐ版付き予算を作る。工程別と全体のwall/活動時間、各process peak private、system commit/RAM最低余裕、通常ファイル論理bytes、物理volume空き、entry/depth、診断予約を区別する。監視中の所有子停止・wait/reap、親の協調停止、未閉鎖invocationの照合、停止後の新attemptへの予算継承を試験し、上限を自動拡大しない |

予算監視はsamplingと工程境界であり、OSのhard quotaや任意のnative callの即時中断ではない。親と子のprivate上限は別々で合計上限ではない。directoryの見かけのbytesにはalternate streams、物理割当量、別rootの総容量が含まれない。[監視仕様](../anomaly-v03-fixture-resource-budget.md)の限界を全工程案でも明示し、最終診断保存の余裕とowner未回収時の扱いを契約へ含める。

## 役割別source/runtimeと予算の結合

予算は最終processの実行範囲を定めてから固定する。producer、analysis、audit、writer、readerの各役割で、実行**前**にfull revisionとclean Git/raw source、選択source・動的依存・外部program、Python exe/DLL/stdlib・ロード対象のextension/DLL/CRT、CPU/OS build・UBR、起動flags・検索経路、input anchorと出力root、親保持の予算・期待profileを版付きで保持する。実行**中と後**には元handleのPID/生成時刻、各processの開始/終了runtimeとsource、実load一覧、入出力bytes、経過・private・commit・disk標本、exit/reap/監視errorを照合する。役割やrevision、前後値、未終了ownerが違えば成功にしない。[source/runtime固定方法](../anomaly-v03-consumer-source-runtime-plan.md)、[実行証拠validator](../anomaly-v03-consumer-evidence.md)。

現reader/analysisには観測由来の事前候補profileがあり、26H2の５役trial-16は各子の作業前後に候補pinと観測runtimeを照合したが、全役割の採択済み完全閉包ではない。架空analysis/auditの補助依存245/235file、writer/readerの各233fileは2026-10-02の**旧保存例**であり、現trial-16の数値ではない。いずれも未実行分岐、一時load/unload、memory内code、Git helper/DLLの完全性を証明しない。[reader候補](../anomaly-v03-reader-profile.md)、[架空解析・監査接続](anomaly-multiseed-v0.3-bound-fixture-pipeline-2026-10-02.md)、[結合公開結果](anomaly-multiseed-v0.3-bound-fixture-publication-2026-10-02.md)。旧正式OS pinは25H2/build26200/UBR9168、現在の実測は26H2/build26300/UBR9457。両者を同一の正式環境として扱わず、版付き[26H2運用契約案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)と独立再監査・native受入を要する。attempt内の環境変化は停止する。限定B1 engineering controlでは子tokenとAccessCheckを通過し、B2専用環境の準備も成功したが、P/U独立起動・干渉・全publisher・正式B2/S4受入は未完了である。[Windows受入準備](anomaly-multiseed-v0.3-s4-b1-acceptance-readiness-2026-09-10.md)、[B2準備](anomaly-multiseed-v0.3-s4-b2-principal-setup-j-2026-09-16.md)。旧Windowsのprotected DACL/独立token要件を観測済みの通常writer成功で通過扱いにしない。[計画§8](../anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)。

## 受入へ渡す版付き成果

1. 最終対象revision・役割profile・OS更新方針と運用契約に対応した、工程ごとの測定receiptを外部pin付きで揃える。今回の架空50,000 draw算術測定を正式analysisや完全独立S6の予算に流用せず、なお残る**未測定欄を数値0で埋めない**。
2. 全工程と工程別の上限・最低余裕、測定条件、対象root、停止点、診断予約、失敗時の別version/root/未使用seed再登録を一つの候補契約にまとめ、必要な固定fixtureとnative/platform受入で検証する。正式実行後にしか得られない実holdout成功receiptを開始前の前提へ循環して要求しない。
3. 採択された版と対象revisionを固定してからS5へ進む。実消費・停止・保存・終了・独立監査の照合は実行後に行う。現時点では旧48時間/32 GiBも240時間/96 GiB案も正式上限として採択しない。

本台帳は登録holdoutの新評価、50,000 drawを含む正式同形の連続全工程、正式gate、26H2でのprotected DACL/独立token受入、完全S6監査を実行した記録ではない。`formal_permission`、`independent_s6_complete`、`execution_authenticated`、`source_closure_complete`、`runtime_closure_complete`をtrueにしない。
