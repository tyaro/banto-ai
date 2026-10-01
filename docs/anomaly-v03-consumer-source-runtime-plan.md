# consumerのsource/runtime固定対象と実行前の残件

2026-10-01現在：最新候補はb6d578e7c577470ecb2fbef228413d6b2abf85bf/fs02。架空sliceの別実装をowned auditへ追加し、選択source15本/Python2file/入力6file、全236依存file（project32/module181/native48）の終了後照合が成功。旧primary-onlyは保持し、新operationはslice入力を元analysisのpinへ結ぶ。[結果](results/anomaly-multiseed-v0.3-fixture-slice-audit-2026-10-01.md)。次は既存5payloadの通常公開・別readerにaudit scopeとwriterの実行記録を接続する。完全closure・正式役割仕様の受入は未完了。正式実行後の成功証拠を開始前に循環要求しない。以下の静的候補表や日付付き追記は履歴。

2026-09-25接続追記：[実観測reader](anomaly-v03-reader-evidence.md)がsource10本・Python2file・実process identity・15入力を外部期待値へ結合。新規13＋既存回帰27種類がpass。source/runtime全閉包は未完了。次は依存source/stdlib/extension/loaded DLLの採取範囲を広げる。[結果](results/anomaly-multiseed-v0.3-reader-observed-evidence-2026-09-25.md)。

2026-09-25実装追記：[役割別実行証拠validator](anomaly-v03-consumer-evidence.md)を追加。16架空試験pass、外部期待値・前後source/runtime・process・全入出力bytesの対応を検査する。実processの採取・正式受入・closureは未完了。次は通常権限readerの実観測との接続。[結果](results/anomaly-multiseed-v0.3-consumer-execution-evidence-2026-09-25.md)。以下の41source候補表はe9826bd時点の記録。

2026-09-25、状態 **proposal / 未freeze**。対象revision `e9826bd0245cf26cf540e1ff470528c001f3cd5f`。[実確認](results/anomaly-multiseed-v0.3-consumer-source-runtime-review-2026-09-25.md)、[運用契約案](anomaly-v03-consumer-io-proposal.md)。現在の実装と保存証拠を整理したもので、正式実行を許可する文書ではない。

## 固定対象の候補

| 役割 | 静的なproject依存候補 | 現在の入口 |
| --- | ---: | --- |
| engineering writer | 23モジュール | 保存済みdev/smokeの記述結果を公開 |
| engineering reader | 25モジュール | writer終了後の別process確認 |
| 架空の推論・文書・slice | 17モジュール | 純粋関数、実IOなし |
| 独立検算の計算部品 | 15モジュール | 生成/score/ledger/seed/sliceの既存部品 |
| 既存inspection inventory候補 | 19モジュール | 実行processの正式受入には未接続 |

重複を除き41本、working source合計566,551bytes。33個の外部top-level importは当該Pythonのstdlib名で、候補位置も解決できた。第三者packageを必要とする静的importは見つからなかった。設定・schema・registry metadata・計画・build/workflow等18fileと、補助CLI2fileも記録した。登録holdoutの観測を読んだものではない。

これは条件付き・未使用importを含む候補一覧。15箇所のnative呼出し・subprocess生成を記録し、readerの文字列bootstrapも手動参照に含めた。完全な呼出し関係、動的依存、DLL/CRT、stdlib内部の全依存を確定したものではない。

### source bytes

41本中39本はworking bytesとGit blobが一致。`generator.py`と`manifest.py`の2本はCRLF/LF差だけで、改行正規化後には一致する。raw一致とは扱わない。元作業コピーは変更しない。

最終実装が決まった段階で、full commitを指定した別clean checkoutを固定元にする。`.gitattributes`は`* text=auto eol=lf`だが、既存working fileの一致を保証するものではない。既存capture_checkout等の全tracked clean・source/configのraw/Git一致・untracked source拒否を利用し、不一致をその場で正規化して受理しない。現在の既存dirty文書も保全する。

producerの過去実行revision `c01d1c978f78bab51391392d56cdcb7aab5afaab`と新consumerのrevisionは別に持つ。今回の41本を過去producerの実行sourceとして登録し直さない。

### 起動と検索経路

変更前のreaderは`-I -B`。実際のinterpreter-only probeではisolated=1、user site無効、**no_site=0**で、`C:/Python314/Lib/site-packages`が検索対象に残った。今回観測したsitecustomize/usercustomize moduleは0。

提案の`-I -S -B`ではno_site=1、site未import、同site-packages pathが消えた。明示したcheckoutのsrcだけをproject検索先へ追加する方針と組み合わせる。候補レビュー時点では起動probeのみだった。その後readerへ`-S`を適用し、14接続試験と旧条件を検出する対照試験で確認した（[結果](results/anomaly-multiseed-v0.3-consumer-reader-no-site-2026-09-25.md)）。この変更はengineering readerに限り、正式runtime受入ではない。

ここで使うruntimeはCPython3.14.0（v3.14.0:ebf955d、MSC v.1944、64bit）。Python3.12をWindowsの追加必須条件にはしない。repositoryの>=3.12宣言やLinux CIの3.12/3.14 matrixは別の互換性範囲として保持する。

## runtimeの受入方法

1. producer・analysis・audit・readerごとに、full revision、command、PID/終了、CWD、検索経路、起動flag、input anchorとoutputを対応づける。親のruntime値を子の観測値として代用しない。
2. Python exe/DLL・build、stdlib/zip、実際にloadしたextension・Windows DLL/CRT、CPU、実OS build/UBRを開始/終了時に記録する。動的loadとエラー経路を含め、対象fileとidentity・bytesの対応を確認する。
3. 外部programも対象に含める。source確認は現コードで`git`をPATHから解決しているため、実行Gitの絶対path/version/bytesを固定する案とし、helper/DLLの範囲も確認する。今回のGit観測は2.51.2.windows.1で、完全なGit runtime閉包ではない。
4. 既存inspection collectorはproducer/workflowを必須にする設計で、`full_runtime_inventory_complete=false`のinspection scopeを持つ。analysis/audit/readerの正式受入へそのまま転用せず、役割ごとの必要sourceとprocessへの結合を追加する。
5. source snapshotsは信頼した呼出し側が指定revisionから取得する。自己申告のpass、scope/role違い、source不足、process終了未確認、前後runtime差を受入にしない。既存`validate_result_contract`は供給bytesの一致を検査する部品であり、これだけで実行証明にはならない。

ユーザーのWindows更新許容方針を維持し、attemptごとに実値を記録する。実attempt内の変化は停止対象。今回観測はProfessional25H2/build26200/UBR9457。過去の記録と旧正式pin9168は保持し、新しい正式運用契約に更新方針を明記する。OS設定を変更しない。

## 次に行う作業と判断点

| 順序 | 作業 | 完了の根拠 |
| --- | --- | --- |
| 完了（engineering） | readerへ-Sを追加 | 14接続試験pass、起動flag/検索経路と旧条件の検出を確認 |
| 続く実装 | 正式consumerとsource/runtime証拠validatorを接続 | 間違ったrole/source/process・自己申告pass等を拒否、既存入口の制限を維持 |
| 候補確定後 | 別clean checkoutでsource固定、役割別runtime採取 | 全raw bytes、実process前後、正式contractとの対応 |
| 必要な回帰 | 最終revisionで関連純粋・通常権限Windows試験、必要なplatform確認 | 現候補に結び付く試験証拠。保留principal試験を混ぜない |
| 実行前の判断 | 運用契約と完全な資源予算を採択 | 下記2件の未充足を解消してから判断 |

**将来の採択事項は2まとまり。今は採択待ちで作業を止める段階ではない。**

- 正式運用契約：通常権限の単一writer、OS実値記録、本文slice＋補助記録、解析と監査の別出力、正式失敗時のversion/root/未使用seedでの再登録。完全consumer・証拠結合・最終audit接続を仕上げてから対象revisionとともに提示する。科学的な閾値は維持する。
- 正式実行予算：旧案のproducer240時間・出力96GiB・空き32GiB（開始時1copy128GiB、同volume2copy224GiB）は未適用。正式推論と最終独立auditの時間・メモリ枠が未確定のため、現時点で全体予算を確定しない。既存上限を変更しない。

候補レビュー時の54試験は当時のsource pin一致を確認した過去の合格記録。その後readerとその試験の2fileを変更し、reader14試験を新たに実行した。他suiteは再実行していない。旧CI revisionからselected source28本が変わっているため、旧CIを最新全体の回帰合格には用いない。現在のworkflowはLinux3.12/3.14の試験で、今回実行/再検証はしていない。

正式gate/holdout、実データ50,000回bootstrap、principal/UAC/ACL、同時書換え試験、push/mergeは起動していない。banto-24はPAUSED。正式source/runtime受入・S4/S6・Phase2/3全体は未完了。

## reader依存の実観測を拡張（2026-09-25）

実装0b03b91a59c7359e4eb05e3585242b88aa8c8cab、[結果](results/anomaly-multiseed-v0.3-reader-dependency-observation-2026-09-25.md)。opt-inの子processでsource28/stdlib79/cache候補77/extension8/その他native40の232fileを採取し、前後一致と親のdisk/Git照合を確認。別候補checkout743fileのraw/Git一致を確認し、元copyの既知CRLF差を維持した。

新規13試験pass、同工程の不変な既存回帰29種類のpassを再利用。現在の一覧はchild-inventory-crosschecked-by-parent-after-exitであり、独立した事前runtime期待値や全closureではない。既存cache候補を実loadしたbytecodeとは断定しない。reader用の依存一覧を実行結果とは別に保持する期待profileへ落とし込み、import準備の境界と照合手順を定義する。今回の観測一覧をそのまま正式な期待値やfreezeとして採択しない。 正式source/runtime受入・全体予算・analysis/auditへの展開は残る。

## readerの候補を別に保持して照合（2026-09-25）

実装0b2da336d90bcc60e97798d83d17d9f6f7421a34、[API](anomaly-v03-reader-profile.md)、[結果](results/anomaly-multiseed-v0.3-reader-dependency-profile-2026-09-25.md)。prepare_profileで別の成功した依存観測を候補化し、後続readerが起動前から保持するpin/全一覧へ一致するかを検査。採取境界・role/revision/root/runtimeも固定。新規16pass＋同工程の不変な既存26種類を再利用。232fileを別PIDで照合した。

候補は観測由来で、正式承認された完全依存定義ではない。OS更新を記録して新候補を作ることは許容し、旧候補を自動更新しない。解析側（engineering consumer）の実行観測と、別に保持した役割別期待値の接続を、小さな架空入力で具体化する。reader候補をanalysis/auditへ使い回さない。 準備processの観測・正式source/runtime受入・全体予算は残る。

## 保存結果準備のanalysis実観測を接続（2026-09-26）

実装2db441e44a65857f288f800a104ba436339358b9、[API](anomaly-v03-analysis-evidence.md)、[結果](results/anomaly-multiseed-v0.3-analysis-observed-evidence-2026-09-26.md)。既存consumerの7入力認証・4payload準備をanalysis専用の実processへ分離。selected source12/Python2file・元handle・前後入出力を外部期待へ結び、source29/全233fileの補助観測をdisk/Gitと比較した。新規15＋既存32の47試験pass。

数値再計算や公開完了ではない。依存の補助一覧は終了後の観測照合で、事前固定したanalysis依存集合ではない。analysis専用の依存候補profileを別に準備し、後続の小さな保存結果準備が、起動前から保持した全依存一覧に一致するかを検査する。reader profileは使い回さない。 正式consumer・文書provenance・公開/独立auditと全体予算は残る。

## analysis専用の事前保持依存候補（2026-09-26）

[API](anomaly-v03-analysis-evidence.md)、[結果](results/anomaly-multiseed-v0.3-analysis-dependency-profile-2026-09-26.md)。実装140e91de93e2cc43c45fab9efb9a7cbc6ece43c7、OUT artifacts/analysis-dependency-profile-2026-09-26。analysis専用のprepare_profileを追加し、別の成功した未profile化referenceと外部result pinから新規候補を保存する。format/role/operation/採取境界を固定し、reader候補の流用を拒否する。後続analysisは親が起動前から保持した候補のraw bytes/pinと依存集合へ前後一致を要求する。

全43試験pass（新規20＋既存analysis15＋reader候補の純粋検査8）、failure/error/skip0、145.715秒。誤pin、file hash改変、module欠落、子の再封印、保存copy差し替え、reference payload改変、候補の自動更新を拒否。source13/Python2file、候補を含む10入力を証拠へ結ぶ。依存source30/全234file/179modules/48images、47,606,116bytesが前後一致した。

保存例reference PID24184→後続PID8184は別process、双方exit0/reaped。後続監視2.123秒。候補111843bytes/SHA6502078885a3f42c7a356f0057a23f45ad24c384719380980cc4c4b0302b78ab。4payload/5237bytesはreferenceと後続で一致。原本の架空入力はcleanup済み、両実行のpayload/期待値/観測/監視と候補を保持する。試験harnessのpeak private 52.97MiB、保存例childのpeak 37.61MiB。資料作成前の空きRAM 9.77GiB、commit余裕 17.74GiB、C/D空き 125.89/346.17GiB。最終値はsave-checks.json。

ap01候補はclean 140e91de93e2cc43c45fab9efb9a7cbc6ece43c7、754tracked files/8,535,094bytesのGit/raw一致を検査。旧ao01/rp01/rd01、実計算checkout/本流/closed、元70b0の既知CRLF差と既存dirty文書を保全。banto-24 PAUSED。数値再計算・新評価・登録データ読取・実bootstrap・正式gate/holdout/freeze・principal/UAC/ACL・push/mergeなし。

candidate-not-acceptedであり、正式source/runtime固定やmemory codeの証明ではない。analysisの対象は保存済み記述結果の認証・準備だけ。numerical_analysis_performed/published/formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。次は、照合済みの4payloadを既存のsingle-writer公開処理へ接続し、writer終了後の別readerまでを小さな架空入力で通す。公開時に解析証拠と保持pinを結合し、数値再計算や正式採択へ範囲を広げない。 正式consumer/文書provenance/独立数値audit/完全資源予算は残る。

## 解析証拠から通常公開・別readerへ（2026-09-26）

[API](anomaly-v03-analysis-publication.md)、[結果](results/anomaly-multiseed-v0.3-analysis-publication-chain-2026-09-26.md)。実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48、OUT artifacts/analysis-publication-chain-2026-09-26。新module/test2本のみ追加し、既存analysis/profile/reader/collector/consumer/LocalPublicationを変更しない。外部result pinで選択したprofile付きanalysisの成功記録・4payloadを再認証し、保存原本との意味・bytes一致を確認して既存single-writer公開へ渡す。writerを閉じた後だけ、別のobserved readerを起動する。

公開物は従来どおり4payload。別directoryのpublication-binding.jsonが解析result/evidence/profile/binding pin、payload pin、公開root/marker、revisionと接続module pinを結ぶ。そのpinとreader result/evidence pinを最終chain resultへ保存し、呼出し側がresult_pinを保持する。公開marker単体は解析証拠の結合を証明しない。

全43試験pass（新14＋既存consumer16＋observed reader13）、failure/error/skip0、75.509秒。誤anchor・payload/evidence改変・reader role・未profile化・入力/出力重複・部分書き込み・writer応答喪失・reader失敗・結合記録改変・未終了ownerの保持を検査。正常時は二度目の公開を拒否し、元入力/公開物を保持する。

保存例reference PID11136→profile付きanalysis PID10040→通常writer PID39840→reader PID16652。全ての子はexit0/reaped。analysisはsource13/Python2file/10入力と依存234fileの事前候補一致、readerはsource10/Python2file/15入力と依存232fileの終了後照合。readerへanalysis候補は流用しない。4payload/5237bytes、marker SHA3837efdce90f6c7070ad0da8b1befa4c306ced1d6afcdebe2d976793e6fa997b。reader監視2.409秒。公開物/両analysis証拠/reader証拠/chain記録を保存し、架空原本だけtemp cleanup済み。

試験harness peak private 53.32MiB、保存例analysis child 37.66MiB、reader child 36.26MiB。資料作成前の空きRAM 10.13GiB、commit余裕 18.56GiB、C/D空き 133.21/345.91GiB。最終値はsave-checks.json。

pc01候補はclean f8f20bcf4ac7ade2f20e96f37bc1567328d88a48、757tracked files/8,567,147bytesのGit/raw一致。旧60code/18data pinとap01/旧候補、実計算checkout/本流/closed、既知CRLF差/既存dirty文書は不変、banto-24 PAUSED。新評価/数値再計算/登録データ読取/実bootstrap/正式gate/holdout/freeze/principal/UAC/ACL/push/mergeなし。

公開成功は架空engineering記述結果の通常公開で、正式文書や独立数値auditではない。formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。接続moduleのGit/raw一致は確認したが、writer全processの実行証拠や全依存固定を完了したとは扱わない。次は、既存dev/smokeの保存済み記述レポートへこの一連の処理を適用し、外部anchor・解析証拠・公開marker・別reader結果を保存する。720評価は再実行せず、数値の正式受入やholdoutへ範囲を広げない。 正式consumer/文書provenance/独立数値audit/完全資源予算は残る。

## 既存dev/smoke記述結果への適用（2026-09-26）

実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48のpc01と事前保持analysis候補を再利用し、原本7file/7,896,608bytes→4payload/2,755,533bytesの通常公開と別reader確認に成功した。原本7file/旧公開6fileは不変、新公開は旧公開とbytes一致。[結果](results/anomaly-multiseed-v0.3-saved-report-publication-2026-09-26.md)。今回source変更0、suite再実行0、旧43試験の合格記録をcode pin不変で再利用。analysis依存234fileの事前一致とreader依存232fileの終了後照合を確認した。

engineeringの保存結果接続は実レポートまで進んだ。正式数値consumer/document_draft/独立audit、writer全実行証拠、source/runtime正式受入と全体予算は未完了。次は受入残件表を現在の実装・保存結果に合わせて更新し、正式consumer/本文provenance、独立数値audit、writer実行証拠、完全資源予算の未充足を具体化する。既存720評価は再実行しない。

## 残件の再整理（2026-09-26）

[更新表](results/anomaly-multiseed-v0.3-acceptance-gap-update-2026-09-26.md)で工程ごとの開始前/実行後を分離した。analysis準備の234file、readerの232fileは役割限定の記録であり、数値analysis・独立audit・writer全実行の正式証拠ではない。writer PIDと接続sourceのpinだけでwriter全processを認証しない。報告値のschema検査だけで正式50,000反復の実行を認定しない。

正式候補のsource/runtime期待値・起動条件・検査範囲・必要な回帰は開始前に準備し、実processの前後/入力/出力/終了証拠は実行時に採取する。system commit診断は停止制御と別で、現行supervisorは時間/private/stdout・stderr容量を制限する。全成果物の連続容量監視やcommit不足の強制停止は未接続。数値解析/独立auditを含む予算と停止処理を具体化してから正式採択資料を揃える。今回sourceや上限設定を変更していない。
