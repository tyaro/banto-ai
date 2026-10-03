# v0.3 登録枠の固定入力確認と正式受入案（2026-10-03）

基準保存点は `03f34908ecfb4894d45670e0359f1617c1b51b1b`。保存済み合成dev/smoke全720評価のengineering報告後、正式評価前の[5まとまり](anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)のうち、登録枠の形と運用・予算の判断材料を進めた。S4受入、S5/S6、正式40 seedの評価、50,000回bootstrap、gate、昇格は実行していない。

## 固定架空入力による登録枠の確認

[登録入力fixture adapter](../../src/banto_ai/anomaly_v03_registered_fixture.py)を新設した。凍結registryのraw bytesを呼出し側のSHA-256と既知のfreeze pinで照合し、公開済みのholdout seed登録から40 seed・480区間・960 dataset・2,880評価のidentityを順序付きで展開する。これは登録表の参照だけで、holdout観測値やscoreを生成・読取りしない。

`planned_fixture`は全枠を未開始として作る。`validate_fixture`は呼出し側が保持するmanifest pin、全chunk/slotのidentityと順序、架空と決定できるinput/evaluation hash marker、attempt列と失敗履歴、候補間の入力pin一致、最新attemptから導いたcoverage、worker終了**宣言**を検査する。欠落・入替・異seed・不正marker・integrity failure後の再試行・未終了の成功宣言を拒否する。供給されたmanifest/registry bytesの一致を確認する純粋関数であり、producerの実process/実入力bytesの認証ではない。外部pinを元のmanifestと独立に保持しなければ、履歴を丸ごと作り直す攻撃は検出できない。

完全な架空宣言は3,985,054 bytes / SHA-256 `e95e2ae3ade4c62e1feb608892fe5dc32415a9a3e0bb0c98cb773daa081697cd`。照合に使うfreeze registry rawは10,679 bytes / SHA-256 `61af9100f8daa96d8200a0d2ab23aa7209cab52f0dd5543f9e35797de7332a70`。これらの値は固定fixtureの再生成・照合用で、正式入力や実観測のpinではない。戻り値は `registered_observations_read=false`、`registered_input_bytes_verified=false`、`actual_worker_exit_authenticated=false`、`campaign_evaluations_credited=0`、`analysis_authorized=false`、`formal_permission=false`を明示する。

[新規試験](../../tests/test_anomaly_v03_registered_fixture.py)8件と、既存consumer入力・S4受入試験を同じコマンドで実行し、計61件が7.862秒でpassした（failure/error/skip 0）。試験は架空hashと登録metadataだけを使う。既存正式入口の `require_campaign_acceptance()` は引き続き `s4_acceptance_not_frozen` を返す。今回の新moduleは旧registry、正式runtime probe、正式runner、出力rootを変更しない。

## 運用契約と全工程予算

[正式運用契約・受入改訂案 v1](../anomaly-v03-formal-operations-contract-proposal-v1.md)に、旧§8のprotected DACL・独立token保証を維持する案と、通常権限の単一writerへ版付きで改訂する推奨案を並べた。旧Windows正式pinはbuild 26200 / UBR 9168、後続の観測はUBR 9457。観測値だけで旧pinを通過させず、attempt内の変化停止、S5前の新UBRをexact tupleとして再受入する条件、S5後の環境変化時の再登録を提案した。ID `anomaly-v03-single-writer-research-v1` は予約案で採択していない。

[全工程予算の証拠台帳](anomaly-multiseed-v0.3-preformal-budget-evidence-ledger-2026-10-03.md)では、producerの実績14.98 GiB・44.54活動時間、正式規模への単純外挿約59.91 GiB・178.17時間、旧240時間/96 GiB/空き32 GiB案を分けた。登録入力/要約、50,000 draw、独立S6、staging/公開、別reader、統合監視の時間・容量・private memory・system commitと停止証拠は不足している。旧案を正式全工程の採択上限にはしない。

## 次の受入作業と実データ境界

開始前には、採択する運用保証とOS更新範囲を版付きで決め、最終consumerを固定入力で検証し、producer/analysis/audit/writer/readerのclean source・全runtime依存・起動前後・終了証拠を対象revisionへ結ぶ。50,000 drawの固定fixtureと独立監査を含む全工程予算、Linux 2 jobsと選択したWindows native試験、最終pin上のdev/smokeを受け入れてからS5を開く。今回の登録metadata fixtureは、そのうち全枠の形と失敗を隠さない境界だけを確認した。

正式40 seedの**実bytes・成功receipt・独立数値監査結果**はS5/S6で取得・照合するもので、開始前に成功を要求しない。保存済みdev/smokeの720評価を正式40 seedへ加算しない。部分失敗後に同じseedを都合よく再試行せず、採択された別version/root/未使用seed規則で再登録する。正式文書のnull欄、`formal_ready=false`、formal/promotion/S6/trust/execution_authenticated/full closure/analysis_authorized=falseを維持する。
