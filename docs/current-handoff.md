# 次のタスク用の短い引継ぎ

更新: 2026-09-25 JST。**consumer入力宣言のI/Oなしvalidatorを実装、22試験すべて通過。次は完了記録からの変換adapter。**

- [API](anomaly-v03-consumer-input.md)、[結果](results/anomaly-multiseed-v0.3-consumer-input-validator-2026-09-25.md)。長い引継書§164。
- 作業先C:/Users/TKent/.codex/worktrees/70b0/banto-ai、branch codex/s4-b1-windows-engineering。実装3fb988292e433311cfd86f00c773b8f17384a750。OUT artifacts/consumer-input-validator-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。

## 今回の成果と次の作業

anomaly_v03_consumer_input.planned_input(mode)とvalidate_input(value, expected_mode=..., expected_sha256=...)を追加。fixtureは独自IDの1区間6評価、engineering-dev-smokeは登録済み120区間720評価。formal/未知modeは対象展開前に拒否。外部canonical metadata hashを要求し、閉じたkey集合・厳密型・全identity/order/coverageを検査する。

同じdatasetの3候補と再試行間で、既知のobservations/events/quality_mask/split/origins/targetsの6種hashが一致することを要求。過去failed attemptを残し、最新だけでcoverage算出。成功/進行中を越すretry、連番欠落、integrity失敗後のretryを拒否。64attempt上限はmetadataサイズ制限であり再試行許可ではない。

profile inconclusiveは完了評価として保持しsuccess/qualifiedにしない。全coverage・writer終了宣言・receipt/markerが揃った場合だけdeclared_complete。公開後supervision failedはmarker保持のまま未完了とする。検査成功でもinput_bytes_verified/source_runtime_accepted/trust/execution/analysis/formal/promotion/S6は全false、performance未実施、selected=null。hash一致はpayloadや実行を認証しない。

22新規試験pass（failure/error/skip0、0.268秒）。架空metadataと720枠の登録metadataのみ。file open/process/bootstrap禁止下の検査を含む。実観測読取・評価・再計算0。peak29.58MiB、最小空きRAM12.93GiB/commit余裕20.23GiB、C/D124.32/294.53GiB。

**次は既存完了記録から入力宣言へ変換するadapterをdecoded metadataだけで実装する。** identity・最終attempt・失敗履歴・6種pinの対応と外部anchorへの束縛を固定する。観測reader・推論・writerは起動せず、既存720評価を再計算しない。元の固定APIやformal拒否を緩めない。今回はT01〜T04前段の実装であり、T02のraw/path/marker認証等と完全接続は未完了。

[前工程の契約案](anomaly-v03-consumer-io-proposal.md)は引き続きdraft。入力7項目・8工程、10consumer/22関数/schema10欄、接続試験12群。主sliceはincident recall＋availability、sidecar全4系列の案（予定1,233/2,835行）は未採択。正式運用方針の候補ID anomaly-v03-single-writer-research-v1も未採択。旧科学config/schema/registry/正式gate、保留principal、banto-24 PAUSEDを維持。

## 前工程の受入残件

[残件表](results/anomaly-multiseed-v0.3-acceptance-gap-review-2026-09-25.md)。freeze前は運用契約、consumer接続、source/runtime固定、公開接続、容量時間予算の5まとまり。今回で全5完了とはしない。11保存点＋3receipt203,543bytesを照合済み、158source等比較中157一致、差分は旧READMEの追記だけ。720評価を再計算しない。

17モジュールの静的候補表にはmanifest.pyのworking CRLF/Git LF差が残る。正規化後同一だがraw不一致なので別clean checkoutでfreeze時に確認。旧Linux CI036ecb4からselected11本が変更/追加、古いpassは最新候補全回帰の代わりにならない。完全runtime/dependency closureは未完了。

本流は別作業でclean6f1285d（旧889cfc3）。temp native/互換試験のmain README記載はGit bytesまで照合し、raw/CI再検証・mergeなし。Windows3.12必須化なし。旧helper.boundariesのmain固定値は古いため、acceptance-gap-review/review.pyのboundary関数を参照。OS直近観測はProfessional25H2/26200/UBR9457、旧engineering9445から更新。formal pin9168と過去runtimeは維持。

## 前工程の記述表

[結果表・診断表](results/anomaly-multiseed-v0.3-descriptive-report-2026-09-25.md)、[閲覧用要約](../artifacts/descriptive-report-2026-09-25/report.md)。実装e0753ba4e1518706002cb3a51f9b5a3c891a4e7c。dev/smoke別18表・234主指標・5,670診断行を元入力とschema部分形式へ照合、27試験pass。manifest7932bytes/SHA25679364b641f8f7a047298ca73d46fcdc49b1931c23394a043cb8802255392af39。gate/CI/採択なし、formal/promotion/S6=false、selected=null、performance=not_evaluated。入力のreadinessは作成時点の文脈として保持。

## 前工程のseed集計

全120区間/720評価を5保存点のhashと全報告のidentity/最終attempt/入力pinで認証済み。seed90表・role18表の1404 counts、候補差12表144点が旧集計と一致。dev8/smoke2は各12layouts×両層×3候補。警報0の適合率46評価はnull診断を保持し、予定母数から除外していない。実装d48ecb4、文書c02e7b0、OUT artifacts/independent-seed-aggregation-2026-09-24、成功verified/。manifest7935bytes/SHA2563d03cdef2852e8432b7d1ca9de7cab25ff9b994fefa9819cb290263145426bb5。counts533126bytes/SHA256e6f3012a0a6fe622b5fc7d6365a7a1f2afadec16517f1bbe2cc423253ae68b2e。保存時点の監査連結であり、今日の全payload再検査ではない。

## 前工程の到達範囲

全120区間・240datasetsの正常生成/overlay/丸めは4,320,000保存観測行で完全一致。全720評価のprofile/score/ledger検算と入力pinで接続済み。旧C1/C2の記述統計は変わらない。生成検算の実装47dbc165f12fb1ce7608bb57625cb498bc4a4d04、文書31b73008828a52681f2ae9a887d88ddedecb516f、OUT artifacts/independent-generation-audit-2026-09-24、成功はverified/、manifest 29473bytes/SHA256322a7fe20b23febcb4467ba16034ab9bae5c209777590150c61bccbae09c90f8。

生成検算工程は既存10 seedを120 pairs分メモリ内で再構成し、新dataset/新評価は0だった。その次の算術検証は固定bootstrap indexと手例だけを計算した。前工程のseed集計は保存済み監査報告を読み、観測seed再構成/score再計算/bootstrapを行っていない。旧観測/score検算は不要に繰り返さない。

## 完走証拠と保全

起点は完走保存点0e02d04b0a5a2151664cda6e8518bf412ff70aab。`artifacts/chunk-119-retry-2026-09-24/savepoint-evidence.json`は8366bytes/SHA256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d。前回全件score検算保存点は26529bytes/SHA256 b591663d8026e348b81e427da8a169702625b160a1352cd7e7e2c07c6e43e9c9（文書commit64fa36c）。これら旧OUTは変更禁止。失敗chunk119/attempt1は保全し、verified attempt2だけを使用。

実計算sourceはC:/Users/TKent/.codex/worktrees/v03p/banto-ai / clean c01d1c978f78bab51391392d56cdcb7aab5afaab、出力artifacts/v03-runs/r1。本流D:/develop/banto-aiは別作業でclean 6f1285d28a37edf486ba5c49b8dac3708c7f3067へ更新（旧保存点889cfc3）。今回merge/pushなし。既存dirty docs/results/anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.mdは8461bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。

control000010は終了済み。journal362、全120区間/720評価、status=completed/next=null。closed SHA256 a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a。controller/所有worker終了確認済み、banto-24 PAUSED。旧保存点・元payloadを理由なく再計算しない。

## 継続する制約

- ユーザーは適度なsavepointを伴う自走を許可済み。必要な判断のみ相談する。独立レビュー委譲も許可済みで、依頼後の進捗ポーリングはしない。通常は自分で進め、委譲する場合も差分に限定する。
- 同じ出力先は単一writer。**専用principal/起動特権/P-U分離試験は§116で保留**。「続けて」から再開を推定しない。UAC/ACL/service/task/VMの変更、SAM/account照会・変更を行わない。
- **保護rootは参照も禁止**: `C:\ProgramData\BantoAI-S4B2-principal-20260915` と末尾b/c/d/e/f、`...-20260916g/h/i/j`。存在確認・列挙・hashも行わない。jと診断guardは消費済み。専用account `BantoS4Publisher` / SID末尾1010に触れない。
- 旧正式gateを開かず、停止済みcontrol000008を再使用せず、追加invocation/holdoutを自動起動しない。push/merge/CIはこの工程では行わない。
