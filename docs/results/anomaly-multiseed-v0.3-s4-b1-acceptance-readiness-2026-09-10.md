# S4-B1 成功後の受入条件と追加回帰確認

[§136の3区間連続運転](anomaly-multiseed-v0.3-three-chunk-run-2026-09-21.md): clean c01d1c9/r1で新規18評価すべて成功。生成・保存・再計算照合・別process ledger監査・journal確定まで2563.527秒、明示3区間上限で正常閉鎖（journal9/next3/yielded）。205 files/399625685 bytesを照合し、全所有process終了確認済み。実行中に6aff0c1/3d4f91cを保存し、実装変更なし。残り117区間/702評価。独立監査は保存score以降のみ、campaign加算0/正式許可false/完全runtime inventoryとS6未完了。以下の正式受入passは追加しない。続く§135以前の未開始表記は各保存時点の履歴である。

[§135の環境snapshotと起動CLI](anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md): engineeringの実OS値でsource/stdlib/nativeを収集・再読し、prepareと明示max-chunksによるcontinueを接続。c01d1c9/17件pass/6.691秒/独立指摘0。実prepareはclean v03pのr1で成功（67.650秒/inspection37.20MiB、source397/stdlib2559/native48/extension8、7 files/749075 bytes）。journal0/実データ計算未開始。snapshotはinspection processの時点観測でruntime closure/正式freezeではなく、以下の正式受入passは追加しない。

[§134の予算付き継続API](anomaly-multiseed-v0.3-budgeted-run-2026-09-21.md): 48時間/32GiBの候補予算を別requestに保持し、閉鎖記録・外部pin・累積活動時間から区間単位で継続するAPIを追加。実装eee93cf、17件pass/78.522秒/peak63.32MiB、独立指摘修正後0/進捗poll0。境界での協調停止であり全体の強制上限ではない。新規launcher、完全runtime inventory、予算の最終確定と全120区間実行は未完了。小規模mock試験であり、以下の正式受入passは追加しない。

2026-09-16の最新作業方針: [引継書§116](anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md)に基づき、同じ出力先は単一writerとする通常保存経路を優先する。専用principal/起動特権/厳密なP-U分離の追加試験は保留。以下の既存受入条件と未完了の事実は維持し、保留を合格や正式実行許可に読み替えない。[単一writer運用改訂](../anomaly-v03-single-writer-evaluation-proposal.md)を採択し、固定6件のengineering-dev経路を実装。初回6件の計算・保存・両再計算が成功した。旧formal gateを開かず、新scopeの独立consumer/全dev・smoke/受入freezeは今後の工程。

[§117の実装結果](anomaly-multiseed-v0.3-local-publication-2026-09-16.md): 通常保存APIを追加し、27件pass/独立指摘解消、実2ファイル保存・重複拒否・writer終了後の別reader検証に成功。通常開発の保存経路が利用可能になった。次は結果生成側との小さな接続であり、下表の正式受入passを追加したものではない。

[§118の接続結果](anomaly-multiseed-v0.3-local-preview-2026-09-16.md): 保存済み観測からC0/C1/C2の既存計算を呼ぶCLIを追加。30件pass/独立指摘0、変更前後の3候補でprofile/score一致。C0の実CLIで14,410入力行→40 score行を保存し、writer終了後の別CLIで4 payloadの再計算検証に成功した。ローカル計算・保存が利用可能になったが、検出性能評価や下表の正式受入を追加したものではない。

[§119の比較結果](anomaly-multiseed-v0.3-local-comparison-2026-09-16.md): 保存済み2〜3候補を再計算検証してMarkdown/JSON表示するcompareを追加。15件pass/独立指摘0。前回C0を再利用し、同じ入力のC1/C2作成と3候補比較を順次実行して成功。両候補で利用可能な行だけの判定一致と、利用不能の別集計を確認した。判定差の確認であり、検出性能や正式受入のpassではない。

[§120の詳細表示](anomaly-multiseed-v0.3-local-comparison-details-2026-09-16.md): sample/targetごとのスコア・残差・判定・除外理由と、件数上限/ページ指定を追加。19件pass/独立指摘0。保存済み3候補を再利用し、2組の判定差を具体化、前回の全体集計と保存済み詳細値の一致を確認した。入力・候補payloadの追加生成なし。正式受入や性能評価の状態は変わらない。

[§121の観測照合](anomaly-multiseed-v0.3-local-observation-context-2026-09-16.md): 各詳細へ前後1秒・同一設備4信号の保存済み観測を追加。22件pass/独立指摘0。既存3候補で24セルを照合し、C0残差と入力差分の一致も確認した。直後の観測は閲覧専用で計算式は不変。通常開発の確認経路が揃ったが、正式受入や性能評価の状態は変わらない。

[§122の接続案](anomaly-multiseed-v0.3-single-writer-route-2026-09-16.md): 旧runnerの未接続、完全dataset・clean sourceの必要性、runtime/受入条件との差を整理。dev576/smoke144枠の設定検証は両方configuration_valid/not_run。新運用方針・固定6件・資源上限を提案し、独立指摘0。旧gate・正式受入・科学的条件は変更していない。

[§123の運用改訂と初回試行](anomaly-multiseed-v0.3-engineering-trial-2026-09-16.md): 実装0086ffe、37件pass/独立2指摘是正後0。clean作業コピーで登録済み固定6件を1回実行し、全保存・公開前再計算・writer終了後readerが成功。572.048秒/peak private321.59MiB/出力126.41MiB、全worker終了確認済み。単一writerの開発評価が動作した証拠であり、以下の旧S4受入passを追加したものではない。

[§124の独立ledger検算](anomaly-multiseed-v0.3-independent-ledger-audit-2026-09-16.md): 保存済み6件のscoreからepisode/matching/metricsを別実装で再構成し、全件一致。18件pass/独立所見0。実読取り92.828秒/177.83MiB、入力46 files不変。profile/score導出・bootstrap等は未検算で、完全S6受入ではない。全dev/smokeの120 chunks/720 evaluationsはmetadata設計のみ。

[§125の進捗復元](anomaly-multiseed-v0.3-checkpoint-metadata-2026-09-16.md): 固定120 chunks/720 evaluationsのmetadata plan/validatorとjournal reader/reducerを実装。21件pass、独立P2修正後0。CLI実演は各1秒未満/最大20.08MiB、失敗監視証拠を残し検証待ち状態を復元。保存済み成果物の再照合・実行再開・追記writerは未接続で、全campaignのcoverage/正式受入を追加しない。

[§126の証拠照合](anomaly-multiseed-v0.3-checkpoint-evidence-binding-2026-09-16.md): 参照journalと旧trialの実ファイル・終了監視・保存auditを結ぶpreflight-trialを追加。39件pass/独立所見0。旧6件のledger再検算と保存auditが一致、116.420秒/185.97MiB、入力46 files不変。旧trial専用の参照検証で、campaign credit=0、resume/全体完了/正式受入は追加しない。

[§127の追記保存](anomaly-multiseed-v0.3-checkpoint-store-2026-09-16.md): metadata専用storeの新規作成・追記・検査、確定後に失われたreceiptの読取り回復を追加。49件pass/独立所見0。9回のCLI実演は合計3.004秒/最大20.67MiBで、二重書込み拒否と元の記録保持を確認。実campaignのattempt出力やcontrollerは未接続で、再開/正式受入の許可を追加しない。

[§128のattempt証拠宣言](anomaly-multiseed-v0.3-attempt-descriptor-2026-09-17.md): 固定pathと4役割の証拠metadataを外部journal/descriptor hashへ結び付けるvalidatorを追加。52件pass/独立所見0。4回のCLI実演は合計0.934秒/最大21.23MiB、別attemptのpathとaudit監視欠落を拒否。成果物本文・実directory構造は未検証で、campaign加算0、再開/正式受入の許可は追加しない。

[§129の実ファイル照合](anomaly-multiseed-v0.3-attempt-files-2026-09-21.md): 固定実配置のdescriptor/証拠bytes/hash/payload inventory readerと、最初のdev chunkに限定した既存独立consumer接続を追加。49件pass/独立所見0。小規模実ファイルCLI4回は合計1.441秒/最大21.57MiB、変更・未記録証拠・検証待ちauditを拒否。新しいaudit接続は数値/source処理をmockしたテストで、新配置の実6件実行証拠ではない。全campaign再開・加算・正式受入は未許可。

[§130の全区切り結果形式](anomaly-multiseed-v0.3-chunk-contract-2026-09-21.md): 全120の登録chunkから外部指定した6件の新manifest契約と保存ledger検算APIを追加。70件pass/約16秒/最大50.94MiB、独立所見0。旧6件契約は維持し、実ファイル・監視・CLIは新形式へ未接続。campaign加算0、実行/正式受入未許可。[短い引継ぎ](../current-handoff.md)を再開時の入口とする。

[§131の新形式IO/監視接続](anomaly-multiseed-v0.3-chunk-audit-2026-09-21.md): 全120から選ぶ新結果形式に専用reader/attempt検算CLIを追加し、実ファイル・producer/audit監視・journalを結合。61件pass/約81秒/最大57.92MiB、独立所見0。小規模実ファイルと明示mockでの検証で、実データ/全campaignは未実行。次は単一writer controller。campaign加算0、再開/正式受入未許可。

[§132のproducer/controller/監視](anomaly-multiseed-v0.3-attempt-controller-2026-09-21.md): 選択chunkのproducer、失敗attemptと遷移intentを保持する単一writer controller、所有Windows子process 1個の資源監視を追加。producer/旧経路31件、controller/store/監視41件pass、後者約48秒/最大54.75MiB。独立レビュー修正後0。小規模fixtureとprintのみの実子processで確認し、campaignは未実行。次はworker/audit CLIを結ぶadapterと予算/source/runtime整理。campaign加算0、正式受入のpass追加なし。

[§133のnative接続と実6評価](anomaly-multiseed-v0.3-chunk-execution-2026-09-21.md): producer/auditを別processで監視し、controllerのjournal確定へ接続。関連42件＋path修正後13件pass、独立指摘解消。初回は261文字pathで5保存/1失敗を保持し、計算前のpath長確認と短いcheckoutで再実行。新6評価の生成・両再計算・独立ledger監査・journal確定がすべて成功した。全体16分49秒、producer最大326MiB、成功出力127.15MiB。全120区切りは単純外挿約31.2時間/14.9GiBで、予算・完全runtime inventory・継続入口の整備は残る。campaign加算0、旧正式受入や完全S6のpass追加なし。

日付: 2026-09-10。初回照合の基準HEAD `f9244a735dff982cfce7d1493efda9431bc31b42`。
補完テスト修正savepoint: `cdbc0a1`。Windows3.14.0一本化の実装savepoint: `9fd3490`。
2026-09-11追記: Linux CI固定・unittest記録の実装は `3c69f9e`、Linuxのfakeテスト修正は `9846f52` / `7870362`。
[CI整備・実行記録](anomaly-multiseed-v0.3-s4-b1-ci-evidence-2026-09-11.md)を参照。
共有fixtureの実装036ecb4は[CI34546440692とWindows選抜照合](anomaly-multiseed-v0.3-s4-b1-shared-fixtures-2026-09-11.md)で検証済み。
本流 `889cfc3` は変更なし。

限定Windows engineering controlの成功は[前回結果](anomaly-multiseed-v0.3-s4-b1-operation-context-result-2026-09-10.md)を参照。
今回native controlを追加実行していない。最大3回枠は前回の1回目成功で終了している。

## 現行の受入条件と到達範囲

[計画§8](../anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)、
`_anomaly_v03_runtime.acceptance_requirements()`、CI定義を照合した。
以下はWindows3.14.0への一本化を適用した現行条件。以前のWindows3.12要件を復活させない。

| 境界 | 必須条件 | 現在の証拠・残件 |
| --- | --- | --- |
| B1 engineering control | 子のruntime/source/token、実AccessCheck、全操作、置換証跡、所有物cleanup/teardown | 実装 `0b30e63` / 実行HEAD `f15af39` / Windows 26200.9445 / Python 3.14.0で限定成功。全48期待値、9対象削除、残存0。全S4受入とは別 |
| Linux共通契約 | Ubuntu 24.04 x86_64、Python 3.12/3.14、共通契約と既存stdlib全回帰、safety、実patch/build・image・source・各test結果の記録 | 候補036ecb4のCI34546440692は両試験jobと比較job成功。実Python3.12.14/3.14.7、各1112 methods中1045 pass/67 skip、failure/error0。smoke/quality/benchmark/safetyもpass。前回1099 methodsの順序・結果・skipを保持し追加13全pass。skipはWindows固有49/optional Capstone16/Toto2 artifact不存在2。VM image digestは未収集で、S4完全受入とは別 |
| 選択した共有手計算fixture | Q1〜Q5、M1〜M9、registry/bootstrap/accounting、C0〜C2 profile/scoreの29 payload | Linux両minorの29件、およびWindows3.14.0選抜19 methodsからの同29件を比較し全raw bytes一致。23件exact、数値6件は所定1e-12許容差で判定。CI receiptと手元再計算も一致。選択範囲外のfixtureやWindows全回帰/native受入を代替しない |
| Windows native受入 | 正式3.14.0の1 runtime。共通回帰、publisher、DACL、独立token/process、競合・非上書き・失敗証跡 | Windows3.12要件を削除済み。各必須検査自体は維持し、全native受入は未完了 |
| B2 publisher/marker | 新規fixtureで公開・非上書き・競合・marker・失敗証跡を検証 | [i診断](anomaly-multiseed-v0.3-s4-b2-principal-setup-i-2026-09-16.md)で最終DACL/auto flags差を確認。[j準備](anomaly-multiseed-v0.3-s4-b2-principal-setup-j-2026-09-16.md)は最終D:PAIを明示し、厳密policy・receipt・特権復元・全close/watchdogまでexit0。78件pass/独立0。P SID末尾1010/無効/Usersのみを維持、専用環境の準備完了。旧9 root閉鎖、j guard消費済み。[次段階](anomaly-multiseed-v0.3-s4-b2-worker-lifecycle-2026-09-16.md)の終了管理model/読み取りdiagnosticは88件pass/独立0。linked B tokenにSeAssignPrimaryTokenPrivilegeなし、起動条件未成立。P-U起動/IPC/干渉/全publisher/正式B2-S4受入は未完了 |
| S4全体 | 必須platform受入、完全runtime inventory、producer/consumer revision凍結、正式pin上のdev/smoke | 未完了。`require_campaign_acceptance()` は `s4_acceptance_not_frozen` を無条件に返す |
| 正式OS pin | 現行計画・registry・S3 runtimeは26200.9168。正式Pythonは3.14.0 | B1 engineeringではユーザー了承によりUBRを記録する方式へ緩和済み。9445での限定成功を正式pinの更新と扱わない。正式段階へ進む前に計画・実装・registryの整合と独立監査・受入が必要 |

Windowsで必須native試験をskip・未実行・失敗のまま受入passにしない。
Linuxの明示的なWindows項目skipは現行計画の許容範囲だが、Windows受入の代替ではない。
直近293件は `test_anomaly_v03_debug_*`、child diagnostics、startup events/preflight、
`PureWindowsControls` の選抜群であり、全repository回帰・全pure/fakeを網羅する数ではない。

## 追加検証と修正

既存選抜に含まれていなかった次の5クラスだけを明示して実行した。
隣接する `NativeReplacementTraceTests` / `NativeWindowsControls` は実行していない。

| クラス | 件数 | 性質 |
| --- | ---: | --- |
| `CleanupEvidenceTests` | 15 | pure evidence/cleanupモデル |
| `CleanupAdapterTests` | 13 | in-memory Win32モデルによるfake adapter。ファイル名のnativeは実機実行を意味しない |
| `ReplacementTraceTests` | 15 | fake trace、child wrapperの注入失敗、resource優先処理 |
| `OfflineSymbolTests` | 8 | 合成PDB bytes |
| `OfflineUnwindTests` | 16 | 合成PE/stack bytes、Capstone使用 |

初回67件は66 pass / 1 fail / skip0、0.343576秒。
`test_child_import_memory_failure_uses_resource_exit_before_classifier_is_available` が、
旧汎用exit1を期待していた。現行の固定bootstrap診断ではImportErrorは97である。
テストの期待値を97へ更新し、不在確認を既に使用しない `_resource_stop` から
実際の共有classifier `_child_failure_exit` へ変更した。MemoryErrorのexit80を維持する。
runtime・child wrapper・token・ACL・正式入口には変更がない。

修正後は上記67件＋既存 `ChildDiagnostics` 10件＋D2 current-only/historical exact inventory 1件の
計78件を実行し、全pass / failure0 / error0 / skip0 / expected failure0 / unexpected success0。
D2の1件はGit上のhistorical 88 pathsとcurrent-only 32 pathsの読み取り照合であり、
正式artifactへのアクセスやD2/S3の全長期回帰ではない。

最初の修正後78件は実環境Capstone 5.0.9で9.677579秒。
`pyproject.toml` のoptional extra固定5.0.7と差があったため、固定環境の受入証拠には数えなかった。
PyPIの5.0.7 Windows AMD64 wheelを専用ignoredフォルダーへ展開し、import元と版を確認して
同じ78件を再実行。**固定5.0.7で78/78 pass、10.504489秒**を今回の最終結果とする。
テスト時のPythonは既存3.14.0、base HEADはf9244a7、未commit差分はこのテスト修正1ファイルだけ。
検証したファイルのraw SHA-256は
`6b2816678d25aae0024edff293eac2e7de0a2a2ee2d3a7c1dcca4b1f0e409235`。
その差分を `cdbc0a1` へ保存した。

共有環境のCapstone 5.0.9は変更していない。wheelの追加依存取得・pip実行・PATH/registry変更なし。
取得元は[PyPI 5.0.7 metadata](https://pypi.org/pypi/capstone/5.0.7/json)。
wheel `capstone-5.0.7-py3-none-win_amd64.whl` は1,272,204 bytes、SHA-256
`4ab8bcb7da8f221ff45926ca168ca33e76f7237d06fbf3c10780002faa2670e1` を照合した。
展開前に件数・総サイズ・各pathの専用root内包を検査し、63 members / 8,409,204展開bytes。
取得wheel自体はメモリ内で検査し、展開物だけを保存した。

小さな実行記録は `artifacts/context-offline-2026-09-10/` に保存する。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| `acceptance-supplement-pure.json`（初回失敗） | 9734 | `1b75437afe36147120cb030dfe28e302eec086dde9156e415c4ff355500a9b24` |
| `acceptance-supplement-pure-fixed.json`（5.0.9） | 11157 | `da2fadc191637327fe716804770d6e3b432d5ef48a6afb1f33781b8000d88b52` |
| `acceptance-supplement-pure-pinned.json`（5.0.7最終） | 11269 | `e3ae54870d12bda5c218c40352dce8069c995cc75e89ea8e3cfaee98622ee334` |

各記録に正確なtest ID・選抜クラス・Python・source条件・pass/fail/skip・所要時間を保存した。
`acceptance-capstone-pin.json` は取得元・wheel hash・展開量の記録である。
これらは選抜回帰の証拠であり、全回帰・Windows native・完全runtime inventoryの代替ではない。
独立差分レビューは新規P0〜P3=0、レビュー担当の試験/native/API呼出/編集なし。進捗ポーリングなし。
repository safety / diff-check pass。

## Windows 3.14.0への一本化を採択

ユーザー「3.12必要？」に対し、現在の3.14.0での動作に追加3.12は不要と回答し、
Windows受入を3.14.0に一本化してLinuxの3.12/3.14 CIを維持する案を提示した。
その後の「続けてください」をこの方針への了承として受領し、実装を `9fd3490` へ保存した。
現在のWindows運用と同じPCの別project連続稼働を踏まえたplatform範囲の判断であり、
正式な性能結果に基づく事後選択ではない。3.12の導入・起動・source buildは行わない。

計画§8と `acceptance_requirements().windows_python` を `["3.14.0"]` にそろえた。
Linuxの2 jobs、`requires-python >=3.12`、科学config/schema/registryと歴史的な科学・status revision、
正式3.14.0のruntime/hash判定、正式OS pin9168、未受入を拒否する入口は維持する。
改訂した現行planはcandidate source inventoryに含め、過去の科学plan snapshotを上書きしない。

S4-A inspectionの要件・schema・pure validator・collectorにもWindows3.12が残っていたため同期した。
新しいreceipt revisionは **`s4-a.2`**。engineering schemaの既存pathはD2 current-onlyのexact pathsを保つため維持する。
旧`s4-a.1`や`windows-3.12`を含むreceiptは現validatorで拒否し、過去の記録を新形式へ自動変換しない。
新形式でも全項目は`not_completed`、formal permissionはfalseである。
collectorはWindows3.12および3.14.1などを対象path検査・source収集・native inventoryより前に拒否する。
Linux3.12/3.14のcompatibility-only観測は継続し、正式実行へ読み替えない。
Windows3.14.0では従来と同じ正式基本pin照合を要求する。B1の9445での限定成功はその受入証拠ではない。

関連25件をPython3.14.0で実行し、**25/25 pass、10.286753秒、failure/error/skip0**。
内訳はAcceptanceContractTests15、選抜ReadOnlyCollectorTests4、publication要件1、
runner拒否境界1、科学・歴史plan pin検証3、D2 exact inventory1。
旧receipt/旧要件拒否、Windows3.12拒否の順序、両Linux minorの継続、fresh collector結果、
科学pinと全未受入状態を確認した。full suite・native control・campaignは実行していない。
通常の小さなテスト用temp領域だけを作成・終了時清掃し、B1の既存失敗fixtureは操作していない。

実行時base HEADは `56f6a69`、検証対象は保存した8ファイルの差分。
`windows314-acceptance-tests.json` にtest IDs・各source hash・差分hash・各結果を保存した。
記録6268 bytes、SHA-256 `dbcc0b679aebae32423d5fe83cef65f3506ea2d6fbb685f804ad34c82da8c0c5`。
検証したstaged diff SHA-256は `ff6f998e990b37f27d1142e5071cc21384f4f9b4bde799b21692c61e7a7c4100`。
独立差分レビュー新規P0〜P3=0、担当の試験/native/編集なし。進捗ポーリングなし。
repository safety/diff-check pass。今回の一本化は必須native検査・B2/S4残件の完了ではない。

## 資源と保全

| 観測UTC | 空きRAM GiB | C空き GiB | D空き GiB |
| --- | ---: | ---: | ---: |
| 10:10:49 | 8.28 | 108.16 | 75.36 |
| 10:18:24 | 7.82 | 107.66 | 75.36 |
| 10:25:02 | 8.33 | 107.66 | 75.36 |
| 11:07:49（一本化作業前） | 8.60 | 107.64 | 75.36 |
| 11:17:01（一本化検証後） | 7.64 | 107.63 | 75.36 |

Windows build26200 / UBR9445、boot `2026-09-09T10:43:08.5000000+09:00` を記録する。
点の資源値の変化をこの作業のリークと断定しない。今回のPython検証processは終了を確認している。
一本化作業後の観測は`windows314-resources-final.json`へ保存した。
別project、既存失敗fixture、旧artifactへの操作なし。本流の変更・push/merge・formal実行なし。
