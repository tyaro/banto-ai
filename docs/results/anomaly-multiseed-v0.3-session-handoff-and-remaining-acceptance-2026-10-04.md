# v0.3 次セッション引き継ぎ・正式受入までの残件（2026-10-04）

この文書は、架空登録形式campaignの最新保存証拠と、正式評価のS4採択からS7結果文書までの残件を引き継ぐ。正式評価の許可や受入判定ではない。科学仕様と正式手順の根拠は[凍結計画](../anomaly-multiseed-evaluation-plan-v0.3.md)、受入5群の起点は[2026-10-03の範囲整理](anomaly-multiseed-v0.3-preformal-acceptance-scope-2026-10-03.md)である。

追記: 後続の最新技術保存点は[Windows Job所有と架空campaign `5cd8e989`](anomaly-multiseed-v0.3-campaign-job-ownership-2026-10-04.md)、固定source `a1c8461f7ead4f9867ae2c0b48dca367618401f5`。その前の[子anchor照合campaign `72f754b3`](anomaly-multiseed-v0.3-child-echo-campaign-2026-10-04.md)は固定source `2e10c6723df9f00999c90416954a806329546dde`。以下の `486f28cd` のpinと再検証手順は先行campaignの履歴であり、これらを合算しない。

## 再開位置と保存点

| 項目 | 引き継ぐ値 |
| --- | --- |
| 作業場所・branch | `D:\develop\banto-ai` / `codex/preformal-acceptance-scope` |
| 最新の架空campaignの固定source revision | `e9107d7323ea6eda2bad8baf1ebd432a879ec4b5`。開始時はcleanで、計画内のselected source raw pinと一致 |
| campaign / 区間 | `486f28cd` / slot 0・attempt 1・path code `g001`、架空固定recipe `hand-normal-v1` |
| 完了宣言 | 480区間中1、2,880評価中6。残り479区間は未実行。40 clusterと正式50,000 drawには接続していない |
| 外部terminal checkpoint | `artifacts/anomaly-v03-preformal-campaign-control-486f28cd/checkpoint-000002.json`、record count 2、head `57a8bd4705be06a4e4817bdb2098c2ec01b391c3ed47b32ae11582b0bb0350e1` |
| 権限・認証 | `invented_only=true`、`actual_registered_observations_read=false`、`campaign_coherence_authenticated=false`、`launch_authorized=false`、`resume_authorized=false`、`formal_permission=false`、`campaign_evaluations_credited=0` |
| 正式gate | `s4_acceptance_not_frozen`。26H2の[運用契約案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)は未採択 |

この文書のcommitは固定source revisionより新しいHEADになる。`tools/preformal_campaign_completion_store.py verify`を含むcampaign storeは、計画のsource revisionと**現在のHEADの完全一致**、選定source raw、固定rootを検査する。したがって引き継ぎ文書のHEADで旧campaignを再検証すると拒否される。再検証が必要な場合は、まず引き継ぎcommitを記録し、同じcheckoutを使う別セッションや所有processが動いていないこととclean statusを確認する。その後、**元の `D:\develop\banto-ai` で**cleanな `e9107d7323ea6eda2bad8baf1ebd432a879ec4b5` に一時的に切り替え、保存pinを渡してread-only `verify`を実行し、元branchへ戻す。別pathのworktreeでは計画に固定した絶対pathとroot検査が合わない。source照合や正式flagを緩めて過去の成果を通さない。

`artifacts/` は `.gitignore` の対象で、下記のraw証拠はGit commitには入らない。同じ作業場所でセッションを引き継ぐ。別マシンや別pathへ移る場合、commitだけでは証拠を再現できず、絶対pathを含む計画をそのまま検証できない。

## 最新campaignの保存証拠

次のpinはファイルの**bytes / SHA-256**である。外部control rootは `artifacts/anomaly-v03-preformal-campaign-control-486f28cd/`、campaign rootは `artifacts/anomaly-v03-preformal-campaign-486f28cd/`。証拠は両rootを分け、既存ファイルを上書きせず保持する。

| ファイル | bytes | SHA-256 |
| --- | ---: | --- |
| campaign `plan.json` | 95,584 | `88ccc0d87c773b7dd14c95f4fe4522c979824b9b1a17cc21490ace31b2fa8183` |
| control `checkpoint.json` | 348 | `a71d5f1fce08cbee963bf7a69f7a4b9b84b9aafcbfc5f11a7ce97d8485db7c0f` |
| control `preflight-intention.json` | 1,598 | `c87db0fd95cce1fa00da4f228425126a7a25e4bc4bf58c323e4d2ae9cd8ebbcc` |
| `artifacts/anomaly-v03-preformal-campaign-prepare-486f28cd/receipt.json` | 2,179 | `af2ff24736052d7ab21aaa528a2d7876218238ad7780b8f3e2ad165430fddf14` |
| `artifacts/anomaly-v03-preformal-generated-pinsets-g001/pins.json` | 72,150 | `dfafb87bd6f40c59ab202dc37ae7a2245bc50f50ae1ab727a22073ffc38af26d` |
| campaign `journal/000001.json` (`started`) | 1,244 | `5e1102a23282dcbc48972662f61ddc306edeacb1590eb773768e4376ef20324a` |
| control `checkpoint-000001.json` | 839 | `4d6fba71c3076f12e7c81519e1bf51be968cee1e6e0adf0d5da80f52823d5d6d` |
| campaign `intents/0001-run-budget.json` | 1,540 | `9fe726f12112cdcf452cbf6a1fd47d50a5dd44dfa271d7c8dd6328c5714300d6` |
| `artifacts/anomaly-v03-preformal-campaign-run-intent-486f28cd/request-pin.json` | 1,661 | `a9974b714adeecfc2785fc57c3732fced939ef465b6cca571750913c007095b3` |
| campaign `control/000-1/run-budget/receipt.json` | 6,928 | `3a10f795c6540c927509ffbde564bd42cc82d14e9b6c15ebf692c044f235205f` |
| campaign `intents/0001-saved-reread.json` | 1,854 | `aa93848e4f84a4bdc0437426e3cbd34610528af5fdc40448ab131e5d9e717eba` |
| `artifacts/anomaly-v03-preformal-campaign-reread-intent-486f28cd/request-pin.json` | 2,119 | `3910d9901c828f757aec9075d1f3fff16a91b29ef7cd88239a7e0f8b248073e5` |
| campaign `control/000-1/saved-reread/receipt.json` | 2,470 | `d67777f8677a92674cef979534549944e8f4afdafe4bcd5dd84006c5d75eaa96` |
| `artifacts/anomaly-v03-preformal-saved-row-reread-g001/rows.json` | 116,085 | `8d03146c324bd534dc07633c835a1cb49e7c330e222932e111a8f3aa1c41aba5` |
| campaign `journal/000002.json` (`completed`) | 6,641 | `57a8bd4705be06a4e4817bdb2098c2ec01b391c3ed47b32ae11582b0bb0350e1` |
| control `checkpoint-000002.json` | 1,190 | `06fec99585e7721aca882f13d192dbf9e533d73336a54a348484f5cad6ad87f0` |

独立read-only監査でmanifestの22保存raw、合計131,144,120 Bを実ファイルから再hashし、22/22一致した。両owner receiptは`verified`で、保存された監督証拠内の直接CLI 2件と内側3 processのPID・開始token・exit 0も整合した。生成側の共有予算は193.594秒・752標本・最大root 131,337,574 Bで上限内、fresh再読取り側も6行・共有予算内である。ただし両者は**別予算**で、prepare、40 cluster/50,000 draw、独立監査、公開まで含む単一外側予算の合格ではない。子孫全体の強制停止・wait/reapも未証明である。`journal/000002.json`の保存raw pinは、後続の照合元とする。

先行campaign `ba59beff` はprepareのみ、`61ac0ac8` は`started`とrun-budget verifiedまでで`completed`がない。失敗した`0d3648ed`、別系譜の`c001/c011`も保持する。どれも`486f28cd`へ足さず、共通campaignのcoverageに算入しない。固定source `e9107d7`で関連統合77試験とrepository safetyがPASSした。文書更新後にその試験を新revisionの受入証拠へ読み替えない。

## 正式受入までの残件

| 順序 | 残る受入・作業 | 完了を判定する証拠 |
| --- | --- | --- |
| S4-1 契約採択 | 旧25H2/build26200/UBR9168の§8–9に対し、現26H2/build26300/UBR9457のOS/Python exact tuple、root/schema、source revision、失敗・再登録、slice/sidecar mappingを版付きで決定。通常単一writer保証Aか、旧protected DACL/独立tokenを保つ保証Bかを選び、独立再監査する | 改訂した計画と運用契約、選択保証のWindows native試験、旧contractとの差分と独立監査。v2 proposalのままでは不合格 |
| S4-2 登録入力・consumer | 凍結した40 seed/480区間/2,880枠の入力と実保存readerを、観測→profile/score/ledger→全slice/sidecar→50,000 draw→正式文書へ、架空の固定入力で接続する。実holdout成功receiptはこの段階で要求しない | 予定/実行identity、最新attempt、保存rawと終了、全分母・全条件別在庫、文書の固定経路と失敗拒否を照合 |
| S4-3 5役割の閉包 | producer/analysis/audit/writer/readerの最終clean source、動的load・外部programを含むruntime依存、起動前/中/終了証拠、異常時の子孫停止・回収を固定する | 最終revisionの外部pin、各役の実process証拠と独立再照合。現campaignのselected source pinや親の子申告だけでは全閉包にならない |
| S4-4 対象環境・最終回帰 | 最終revisionでUbuntu 24.04 x86_64のPython 3.12/3.14両job、選択保証に応じたWindows 26H2/CPython 3.14 native、正式dev 8 seed・smoke 2 seedの全layout/両層/3候補を受け入れる | CIのpass/fail/skipとrunnerの版付き同定。未取得の`runner_image_digest`は取得するか、計画で同等の同定方法に改訂する。Windows 3.12は追加必須条件ではない |
| S4-5 全工程予算・容量 | producer→登録形式保存reader→40架空cluster/50,000 draw全文書→完全S6同形audit→staging/writer→別readerを、一つの外側予算と停止・回収で測る。工程別内訳と計画所定の容量2倍検査を採択する | wall/容量/private memory/system commit、失敗停止、全process終了、公開後fresh readを含む実測。独立の部分予算を加算して代用しない |
| S5 正式実行 | **S4採択後のみ**、未使用の登録holdout 40 seedを凍結clean revision・新rootで一度実行。性能を見た条件変更や既存root/seedの再利用をしない | 480区間・960 dataset・2,880評価の実bytes、全attempt、環境・終了・保存pin、欠落0。失敗は保全し再登録規則に従う |
| S6–S7 独立監査・報告 | S6で保存raw観測からprofile/score/episode/ledger、全分母、50,000回CI、gate/選択とsliceをread-onlyで独立再導出し、別rootへ公開してfresh reader照合。S7で3候補×core/stress/overall、全gate、失敗・制約、producer/analysis/auditのSHA・hash、昇格なしの場合も監査に沿って結果文書へ記す | 独立数値一致、全payload/sidecar/receipt/reader一致、結果文書とS6 pinの対応 |

S4前の追加技術作業として、[campaign controller案](../anomaly-v03-preformal-campaign-controller-next-v1.md)にある子へのanchor echoと子孫の所有回収、登録行から40 clusterへの由来、全工程予算を詰める。ただし**架空480区間の完走を新たなS4必須条件に自動追加しない**。現campaignの`resume_authorized=false`は次区間の自動続行権限を意味しない。次の小試行が必要なら、範囲と固定sourceを決めた新しい非上書きrootで扱う。

## 実データの境界と次の着手

保存済みの「実データ」は合成信号を実際に生成したengineering dev 8 seed・smoke 2 seed、120区間・240 dataset・720評価であり、[新readerからの要約・記述報告](anomaly-multiseed-v0.3-real-saved-summary-report-2026-10-03.md)まで実適用済み。実設備・顧客データではない。今回の`g001`は架空recipeの技術試行で、ファイル名にholdout seed identityがあっても**登録holdout観測ではない**。未使用40 seedの実観測はS4採択前に読まず、正式creditは0。正式文書のnull欄を「残り4試験」と数えない。

次セッションはまず `git status --short --branch`、引き継ぎcommit、terminal checkpointのcount/headと上記pinを確認する。その後、S4採択の最短経路として26H2契約と保証A/Bの決定、5役割と全工程予算の不足証拠の整備、最終revisionでの環境・dev/smoke受入を進める。旧gateと旧artifactを変更せず、S4の独立判定を得てからS5へ進む。
