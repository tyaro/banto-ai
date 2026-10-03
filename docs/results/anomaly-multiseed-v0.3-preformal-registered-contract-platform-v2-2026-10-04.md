# v0.3 登録評価契約・26H2限定fixtureの事前検証（2026-10-04）

基準保存点 `7f85891` から、code保存点 `32ec6e8` で[登録評価契約の候補境界](../../src/banto_ai/anomaly_v03_registered_evaluation_contract.py)、[26H2専用の限定fixture](../../src/banto_ai/anomaly_v03_platform_fixture.py)、[全工程予算の閉包案](anomaly-multiseed-v0.3-preformal-end-to-end-budget-closure-proposal-2026-10-04.md)を追加した。運用契約の[26H2改訂案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)は未採択であり、旧25H2正式pin、旧engineering判定器、`s4_acceptance_not_frozen` は変更しない。正式holdout観測、新評価、bootstrap、S5/S6は実行していない。

## 登録評価契約で実証した範囲

既存の[登録raw-byte候補](../../src/banto_ai/anomaly_v03_registered_saved_summary.py)が外部pin、最新attempt、6枠のidentityと入力hashを照合した後、新境界は評価JSONの完全v0.3 schemaと登録identity、完了status、48 profileの状態を検査する。完了行なら報告されたscoreから別実装のledgerを再構成し、そのmetricsと主summaryの分子・分母、clean exposure、検出遅延histogramを照合する。`not_run` は手製の架空登録identity検体でschemaと非計算状態を確認するための入口だけで、保存候補の成功行には使わない。

[新規試験](../../tests/test_anomaly_v03_registered_evaluation_contract.py)5件はpassした。旧byte境界では、矛盾するstatus/metricsを付けて評価・receipt・reportのpinを選び直した検体が通る。新境界はその検体を拒否した。独立レビューでも、**選択済み行に対する報告score→ledger→primary**の範囲に明白な矛盾通過は見つからなかった。ただし、完成した登録holdout形式の評価をこの新入口が全件受理する肯定試験はまだない。dev/smokeをholdoutへ改名せず、登録holdout観測も生成していない。

観測からのprofile/score再導出、条件別slice再導出、実保存path読取り、producerの出所と実終了証拠は未接続である。返却値は `observation_to_summary_recomputed=false`、`registered_observations_read=false`、`real_saved_chunk_reader_used=false`、`actual_worker_exit_authenticated=false`、`campaign_evaluations_credited=0`、`formal_permission=false` を保持する。schema/ledgerの候補照合を正式2,880評価の実検証へ算入しない。

## 26H2限定fixtureの契約と実機結果

[専用runtime](../../src/banto_ai/anomaly_v03_platform_fixture_runtime.py)は Windows 11 Pro 26H2/build26300/UBR9457、AMD64、local NTFS、CPython 3.14.0とexe/DLL raw SHAをexact tupleで検査する。現ホストのpreflightはこのtupleと一致した。旧engineering validatorは同じ26H2 tupleを拒否し、旧formal gateも拒否した。[新規試験](../../tests/test_anomaly_v03_platform_fixture.py)の純粋契約5件はpass。旧fixture出版のsource/runtime参照を単独orchestrator process内のscopeに限って専用参照へ切り替え、scope終了時に復元する。これは5役割のfull source/runtime閉包や26H2正式採択ではない。

clean code保存点後の最初のWindows実機試行は3件ともskipなしで起動したが、writerの依存照合で `dependency working/Git bytes differ: src/banto_ai/generator.py` により停止した。保存されたplatform結果はすべて `status=failed`、`publication_status=unconfirmed`、`reader_status=not_started`。[代表失敗receipt](../../artifacts/anomaly-v03-engineering-platform-v2/native-19439bd82d425273/platform-result.json)は1,560 bytes / SHA-256 `5b8e94f61a3aae541b3863a3ef82643dc69268ff4a816e6c16d50f45facf2a0c`。比較すると `generator.py` と `manifest.py` の作業ファイルrawはCRLF、HEAD blobはLFで、Gitの通常statusはcleanだった。この5個の初回失敗receiptは元rootに保全し、writer→reader成功へ数えない。

2ファイルをHEAD blobのLF raw bytesに揃えた（generator 21,556→21,229 bytes、manifest 7,109→6,960 bytes）。両rawがHEADと一致し、実行時の作業ツリーもcleanであることを確認して、別の保存点 `9c846e2`・新receipt名で再試行した。`BANTO_PLATFORM_FIXTURE_NATIVE=1` の実機3試験は **pass 3 / skip 0、58.908秒**。成功例は[platform receipt](../../artifacts/anomaly-v03-engineering-platform-v2/native-12cdf40762b57d7d/platform-result.json) 1,916 bytes / SHA-256 `7bf0e1bef7a53d9c6d07cea7e5f788d9f637f70aaf380632847c272da3d9d5a2`。外側13.929秒、writer 4.215秒・exit0/reapedの後、別reader 2.549秒・exit0/reaped。5 payloadの保存、監視・子報告・依存一覧の3種類のpin、非上書き、source 15 fileとPython runtime 2 fileの限定照合が通った。`formal_permission=false`、`registered_data_read=false` を保持する。

改変試験は公開済みbytesを修正せず失敗receiptを残した。writerの `supervision.json`、`worker/report.json`、`dependencies.json` をそれぞれ変えた3例は、公開済みでも `publication_status=unconfirmed`、`reader_status=not_started` で停止した。各[receipt 1](../../artifacts/anomaly-v03-engineering-platform-v2/native-290f7d44cd6a917b-supervision-json/platform-result.json) / [2](../../artifacts/anomaly-v03-engineering-platform-v2/native-290f7d44cd6a917b-worker-report-json/platform-result.json) / [3](../../artifacts/anomaly-v03-engineering-platform-v2/native-290f7d44cd6a917b-dependencies-json/platform-result.json)のSHA-256は順に `fa93ca91942e3744e6e5a6fec72f9c9d7fd51f00eb823ceb8415c94ebaa2dfd4`、`30557cfdf5ac8bf46314801dc0895d5c4aff5d18f424b93d1b5b15f606202f6e`、`fa9ba90dc99478ae168be6cf43555f7c7c4f2fea13719341e0692d0b871fc163`。公開payloadをwriter終了後に改変した[別例](../../artifacts/anomaly-v03-engineering-platform-v2/native-fc31e4e53f41a994/platform-result.json)は1,525 bytes / SHA-256 `7a9964bafd308f3fc9e848ffb78fbc34a936bff358ac7f4fc09c464e1ffcdbd0`、`publication_status=completed`、`reader_status=unconfirmed` で失敗した。

この成功は通常権限・単一orchestrator process内の架空5payloadに限る。scope内で共有module参照を一時切替するため、同じprocessで旧fixture publicationと並列起動しない。protected DACL/独立token、正式全payload、5役割全依存、最終OS契約採択、Linux必須jobは別の受入事項である。

## S4前の残件

| 受入事項 | 今回の位置 | 次に必要な証拠 |
| --- | --- | --- |
| 版付き運用・26H2 platform | v2案と限定fixtureの契約試験。初回nativeの依存raw不一致を保全し、raw修正後のwriter→別readerと改変拒否を実機確認 | 最終clean revisionのLinux 2 job・選ぶwriter保証の採択、全platform native回帰と独立再監査 |
| 登録入力とconsumer | 登録形式のbyte/identityとschema・報告ledgerの候補境界 | 保存済み登録評価の肯定経路、観測→profile/score、slice、最新attempt、独立終了証拠を固定入力で実証。S5前に実holdout成功結果は要求しない |
| 5役割source/runtime | 2つのPython raw pinと選択sourceを限定照合 | producer/analysis/audit/writer/readerの全依存と外部期待値、実行前後の閉包 |
| 公開・別reader・独立audit | 過去の架空fixtureと合成dev/smoke保存報告の接続実績、26H2限定nativeの5payload writer→別reader | 正式同形の全payload・独立数値監査、最終役割profileと改訂契約の採択 |
| 全工程予算 | 50,000 drawの主・別算術2子の実測と[7工程の不足台帳](anomaly-multiseed-v0.3-preformal-end-to-end-budget-closure-proposal-2026-10-04.md) | producer→reader連続wall、全root bytes、private/commit/RAM/空き、失敗保全、S4容量2倍の版付き上限 |

この文書の5行は受入のまとまりであり、残り試験数ではない。正式null欄、`formal_ready=false`、`formal_permission=false`、`independent_s6_complete=false`、`promotion_allowed=false` を維持する。
