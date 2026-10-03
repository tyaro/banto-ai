# v0.3 全工程予算の測定済み範囲と閉包案 v2（2026-10-04）

状態: **未採択の予算閉包案**。対象はS4受入前に、producerから公開後readerまでを一つの版付き予算へ結ぶ作業である。正式holdoutの観測、S5/S6、性能gate、昇格を実行した記録ではない。基準保存点は `7f85891`。Windows 26H2向けの[運用契約案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)も未採択であり、旧[計画§8–9](../anomaly-multiseed-evaluation-plan-v0.3.md#v03-runtime-acceptance)の25H2正式pinと `s4_acceptance_not_frozen` を変更しない。

追記: 本表は基準保存点当時の計測欄である。後続の[共有予算付き５役・候補profile必須の架空１draw試行](anomaly-multiseed-v0.3-preformal-profile-and-saved-attempt-2026-10-04.md)はproducerから別readerまで連続測定済み。ただし50,000 draw、登録保存reader、完全独立S6、最終正式文書を含まないため、下表の**正式同形全工程予算はなお未閉包**である。

[既存の予算証拠台帳](anomaly-multiseed-v0.3-preformal-budget-evidence-ledger-2026-10-03.md)に対し、[今回の50,000 draw測定](anomaly-multiseed-v0.3-preformal-platform-raw-budget-2026-10-04.md)で埋まった欄と、全工程の停止予算としてなお必要な欄を明示する。「保存済みデータ」は合成dev/smokeの成果物であり、実設備・顧客データではない。

## 数値を使える範囲

| 工程 | 保存された数値 | 予算への使い方と限界 |
| --- | --- | --- |
| 旧producer | 合成dev8/smoke2の120区間・720評価で論理16,081,676,236 bytes、累積活動160,357.174秒。正式規模への単純4倍は約59.91 GiB・178.17時間。[容量・時間調査](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md) | 前者は旧試行・失敗attemptを含む実績、後者は規模シナリオ。物理使用量、連続wall、現26H2/最終revisionでの上限ではない。旧240時間/96 GiB/残空き32 GiB案も未採択。 |
| 保存済みreaderと記述報告 | 合成720評価の要約は別rootの3試行で2,806.091 / 1,243.560 / 1,087.228秒。記述報告・4payload公開・別readerは8.447秒、親peak private 75,059,200 bytes、新directory監視最大11,087,861 bytes。[実適用結果](anomaly-multiseed-v0.3-real-saved-summary-report-2026-10-03.md) | 実保存payloadの再読取りとengineering記述結果の実績。3試行を一つの連続wall予算とみなさず、登録40 seedの実保存readerや正式全payloadへ外挿しない。 |
| 50,000 drawの主算術 | 架空40 cluster、50,000 draw。所有子101.580秒、peak private124,829,696 bytes、出力78,082 bytes、exit0/reaped。[算術測定receipt](../../artifacts/anomaly-v03-preformal-draw-budget-2026-10-04-17873fd-01/receipt.json) | 反復数を満たした算術の資源値。登録観測からのcount導出、完全な文書生成、公開は含まない。 |
| 50,000 drawの別算術監査 | 同じ架空入力で別実装の所有子245.902秒、peak private27,267,072 bytes、出力566 bytes、exit0/reaped。主9表・117絶対推定・72対応差・180 gateが一致。[算術測定結果](anomaly-multiseed-v0.3-preformal-platform-raw-budget-2026-10-04.md) | 推論算術照合だけの実績。raw観測・profile/score/ledger・slice/sidecar・全公開文書を再導出する完全S6ではない。 |
| 算術2子を通した親・環境 | 2子は直列で、子の経過合計は347.482秒。親の最終peak private22,384,640 bytes、最低system commit余裕16,863,948,800 bytes、最低空きRAM10,510,004,224 bytes、最低D空き413,553,844,224 bytes。新rootは10 file・論理241,842 bytes。[同receipt](../../artifacts/anomaly-v03-preformal-draw-budget-2026-10-04-17873fd-01/receipt.json) | 合計は子時間のみで起動・照合・保存等を含む全体wallではない。空き資源は当時の標本で、現在の予約量でもhard quotaでもない。 |
| 架空5payload通常公開 | writer終了後の別readerまで10.801秒。元1,987,587 bytes、公開1,987,592 bytes、親peak61.01 MiB、writer49.89 MiB、reader49.49 MiB、監視directory最大2.84 MiB、commit最低余裕26.27 GiB。[結合公開結果](anomaly-multiseed-v0.3-bound-fixture-publication-2026-10-02.md) | 通常writer・readerの小fixture実績。正式5payload全量、protected DACL/独立token、失敗stage・再公開費用ではない。 |

算術workerの各子には900秒、private 1 GiB、commit/RAM余裕各4 GiB、disk空き10 GiB等の測定専用停止条件があり、今回の両子は停止理由なしだった。これを正式analysis/auditの採択上限に流用しない。旧8 draw worker、文書64 draw fixture、旧48時間/32 GiB engineering制御も正式全工程の上限ではない。上表の異なるrevision、OS、入力、監視root、attemptの時間やbytesを単純加算して正式予算を作らない。

## 全工程予算に残る測定欄

| 順序 | 固定入力で測る対象 | 必須の停止点・保存証拠 | 現状 |
| --- | --- | --- | --- |
| 1. 登録入力とproducer | 最終clean revision・選定OS tuple上の正式dev/smokeと固定fixtureを使い、区間と全attemptの活動時間・wall、通常/失敗attemptの論理bytes、volume空き、controller/子の各peak private、RAM/commit最低余裕を測る | 登録identity・入力source/runtimeの変化、root逸脱、所有子の時間/資源超過では新cellを開始せず、失敗attemptと未開始slotを区別して保全する。元attemptを上書きしない | 旧720評価の実績と外挿のみ。最終v2 runtime/役割profileの同形測定なし |
| 2. 実保存reader・coverage | 最新attempt、全登録slot、元観測→profile/score/ledger→主・条件別summaryの読取bytes・処理時間・peak private・出力/再照合容量を測る | producer終了と外部pinを照合し、欠落/重複/partial/不一致なら次の数値解析を開始しない。元payloadと失敗履歴を保全する | dev/smoke 720件のengineering読取りあり。登録形式の架空raw-byte候補は実保存readerと観測再導出を認証しない |
| 3. 正式同形analysis | 固定した40架空cluster・50,000 drawに、count結合、主表、slice/sidecar、5payload全体の生成・検証・保存を含める。全体wall・各子peak・stdout/stderr・root容量を測る | draw完全性を保ち、時間/容量/commit不足なら所有子を停止・終了確認する。部分文書を完成扱いにしない | 主算術のみ実測。文書全payloadと連続した入口・出口が未測定 |
| 4. 独立audit/S6同形 | 別実装・別rootでraw観測からprofile/score/ledger、support/episode、全母数、50,000 draw/CI/gate/選択、slice/sidecar、公開予定文書を再導出し、全入力走査bytes・時間・peak・root容量を測る | 主結果との不一致、未reap、source/runtime不一致では公開を開始しない。監査失敗receiptを上書きせず保持する | 別算術245.902秒のみ実測。完全S6の時間・容量は空欄 |
| 5. staging・公開 | 正式同形5payloadのstage、検証、no-replace確定、marker、必要ならDACLを同一volumeで測り、一時複写・失敗stage・診断予約の最大bytesと時間を得る | 既存root・markerを上書きしない。stage途中失敗もroot内/外側receiptへ残し、writerのexit/reap前にreaderを始めない | 架空5payloadの通常公開実績のみ。v2で選ぶ保証と正式payload全量は未測定 |
| 6. 公開後reader | writerとは別のfresh processで全inventoryのhash/schema/意味・差分を再読取りし、読取bytes・時間・private・commit余裕とexit/reapを測る | markerだけで成功にしない。read失敗は公開済みbytesを修正せず、外側失敗receiptへ残す | 架空5payload・記述報告4payloadの通常reader実績のみ。正式全payload、必要なら独立tokenの受入なし |
| 7. 統合監視と再開 | 1〜6を同じ外側予算ID・新rootで直列に通し、工程間待機も含むwall、活動時間、通常file見かけの総bytes、entry/depth、volume空き、各process private、RAM/commit最低余裕、監視errorと診断予約を記録する | 同じ上限を工程ごとにリセットしない。超過で新役割を開始せず、所有子停止・wait/reap、監視終了、partial/inconclusive保存を確認する。継続は別attempt/rootと元receipt pinで行う | 小fixtureの共有監視のみ。producerから公開後readerまでの連続測定なし |

全役割はproducer、analysis、audit、writer、readerの事前source/runtime profileと、実行時/終了時の依存・OS・exit/reap照合を要する。現26H2/build26300/UBR9457は[未採択v2契約](../anomaly-v03-formal-operations-contract-proposal-v2.md)の候補値であり、旧25H2測定と同一環境として合算しない。独立token・protected DACLを採る場合はそのnative工程を行5〜6に含める。

## 版付き上限を決める手順

1. 科学条件・50,000 draw・seed登録を変えず、最終実装revision、26H2のexact runtime tuple、5役割profile、公開保証、同じvolume上の新rootと固定入力を記録する。正式holdoutを測定用入力に使わない。
2. 各工程で `wall` と子の活動時間、各process peak private、system commit/RAMの**最低余裕**、volumeの**最低空き**、通常fileの論理bytes・一時stage・失敗attempt・entry/depthを別欄に保存する。開始/終了時のfile pin、監視標本、source/runtime前後値、終了/reapを同じ外側receiptへ結ぶ。未測定欄は0で埋めない。
3. S4の最終dev/smokeを全layout・両層・3候補で走らせた後、smoke全artifact bytesからproducer+analysis+audit+stagingの正式同形規模を算出し、式・入力bytes・失敗保全と診断予約を保存する。計画§9に従い、正式開始時の対象volume空きは**この見積りの2倍以上**を要する。公開後reader等の別rootも同じvolumeを使うなら必要容量へ含める。旧59.91 GiB外挿や96 GiB案だけでは合否を決めない。
4. 工程別および外側共通のwall・容量・private・commit/RAM・disk余裕上限と、標本間超過、停止後診断の予約、未回収owner時の扱いを版付き契約へ記す。samplingと協調checkpointはOS hard quotaではなく、親/子のprivate上限は合計上限でもない。新条件が上限に収まらなければS4で停止し、上限や反復数をその場で変更しない。
5. 条件を固定した新rootで正常完走と、少なくとも子の時間/容量超過、commit余裕低下、公開途中失敗、reader不一致、未終了ownerの停止・保全を確認する。最終clean revision・platform回帰・独立再監査・契約採択まで `formal_permission=false` を維持する。S5成功receiptはS4開始前の前提にしない。

本案は新しい測定・正式評価・契約採択を実施していない。既存の算術receiptを完全S6または全工程予算の合格に昇格しない。
