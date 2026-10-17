# v0.3 メモリ診断の追加と短い確認

2026-09-23 JST。[原因調査](anomaly-multiseed-v0.3-memory-error-diagnosis-2026-09-23.md)で不足していた記録を、外部helperとして追加した。**診断12件と既存launcher16件の選抜試験、Windows APIを使う短い実機確認、固定sourceからの読取り専用再開確認が合格。** 新しい評価・完了済み区間の再照合は実行していない。

## 追加した記録

`tools/evaluator/anomaly_v03_memory_diagnostics.py` の `Diagnostics` を、固定sourceの外側から明示的に読み込む。Bantoの実装をimportしたり評価を起動したりする機能はhelper単体にはない。実計算sourceは引き続きclean c01d1c9である。

- OS全体のコミット量・現在の上限・差分、物理RAM、ページファイルの確保量・使用量をUTC/経過時間/PIDとともにJSONLへ記録する。
- 保存区間の監査の開始・終了と、chunk index / attempt / journal sequence / statusを記録する。controllerがRun.run内で作り直されるため、一時的にクラスの `_verify` を観測し、context終了時に元へ戻す。元の引数・戻り値・例外をそのまま引き継ぐ。
- `observe_launcher` は `open_run` / `continue_run` の例外も、元CLIが捕捉する前に記録する。tracebackはfile/function/lineのみ、各32frame・4例外まで。payloadやframeのlocalsは保存しない。
- 例外の位置を先に書き、その後にOS情報を採取する。記録やOS照会の失敗で元の評価例外を置き換えない。未終了workerの所有権を示す `UnreapedWorker` は追加の例外時IOをせず元launcherへ渡す。
- 記録ファイルは新規作成専用、上限16MiB。書込み失敗後の追記は止め、エラー数・欠落数・無効状態を返す。新たな監視threadは作らず、既存wrapperの60秒間隔の観測から `sample()` を呼ぶ。ctypesの型とAPI定義は再利用する。

コミットの指標は [GetPerformanceInfoの構造体](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-performance_information)、ページファイル量は [EnumPageFilesW](https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-enumpagefilesw) と [ページ数の定義](https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-enum_page_file_information) に従い、page sizeを掛けてbytesへ変換する。pagefileの内容やOS設定は変更しない。異なるAPIの値は同一瞬間のatomic snapshotではない。

## 確認結果

`tests/test_anomaly_v03_memory_diagnostics.py` の12件は6.237秒で合格。例外の同一性・発生区間と位置・監視対象の作り直し・復元・disk書込み失敗・OS照会失敗・記録上限・既存ファイル拒否・例外chain・未終了workerの返却を確認した。既存 `tests.test_anomaly_v03_campaign_launcher` の16件も合格した（初回の計27件/6.994秒に含む）。

小規模な実ファイルIOの確認では、保存済みfixture区間の再照合へMemoryErrorを注入した。失敗closedが作られ、旧区間のファイル・journal確定数・次区間番号が保たれ、新規producer/auditや新attemptが始まらないことを確認した。この試験の数値処理・native worker・runtimeはfixture/mockであり、実81区間の再計算とは区別する。

実機 `--self-check-output` はWindows APIをmockせず実行し、3392 bytesのイベント記録を保存した。MemoryErrorは明示的に注入したもの。巨大な割当や実際のメモリ枯渇は発生させていない。記録欠落0/観測エラー0、同じ例外を返却、監視methodの復元を確認した。真のメモリ枯渇・電源断などでも必ず記録できる保証ではない。

続いて実計算worktreeのc01d1c9のlauncherを読み、最新failed closed000006のpinを `open_run` で確認した。**1.251秒、source/runtime/native mockなし。continue/runは呼んでいない。** journal243、next chunk81、累積活動97603.864249秒、verified再照合済み集合は空のまま。closed原本のbytesとcontrol配下の一覧が不変で、新invocationは作られていない。probe自体のpeak privateは28291072 bytes（約26.98MiB）。

実機probe時刻UTC2026-09-23T10:51:58（JST19:51）。空きRAM15302311936/C155439927296/D51483475968 bytes（約14.25/144.77/47.95GiB）。Windows26200.9457/CPython3.14.0・exe/DLL hashは以前と同じ。詳細なcommit/pagefile値は `read-only-resume.jsonl` に保存した。

## 次回wrapperへの組込み

固定実計算sourceの `src` を先にimportし、helperは候補worktreeの保存済み絶対pathから `importlib.util.spec_from_file_location` で読む。外部helper自体のhashと保存commitを新しい起動証拠へ記録する。helperを固定worktreeへコピーしたり、旧成果物を変更したりしない。

1. 新しい診断ファイルを開き、起動前の `sample()` が成功していることを確認する。
2. 既存の所有process/receipt保存を維持したwrapperで、`with log.observe_launcher(launcher): code = launcher.main(argv)` とする。
3. 既存の60秒監視に `log.sample()` を加える。監視threadの終了を確認してからlogを閉じ、`log.summary()` と記録hashを最終報告へ残す。上限や書込み失敗による診断欠落を合格と扱わない。
4. 再開pinはfailed closed000006、SHA-256 `18af12a119e3acc0600594d8eaf6263607f5f7c85d68ff3acbda31931d4b9e4c`。次の新規invocation番号は000007。累積活動と残り候補活動75196.135751秒を引き継ぐ。旧000005や失敗時folderを再使用しない。

この保存点は診断の準備と短い確認まで。診断を組み込んだ長時間の再試行は未開始で、heartbeat banto-24はPAUSEDを維持する。今回の補助コードはsource/runtimeの完全closure証明を追加するものではない。正式許可false/campaign加算0、累計81区間/486評価を維持する。

証拠は候補 `artifacts/memory-diagnostics-validation-2026-09-23/`。tests.log、windows-self-check/、read_only_resume_probe.py、read-only-resume.jsonl、read-only-resume-report.json、最終 `savepoint-evidence.json`。以前の失敗manifestと原因調査manifestは不変。既存dirty親policy文書は保全・commit除外。本流と実計算worktreeは変更せず、push/merge/OS設定変更なし。
