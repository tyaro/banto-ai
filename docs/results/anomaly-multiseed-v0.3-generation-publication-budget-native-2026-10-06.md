# v0.3 生成から文書公開までの外側予算接続（2026-10-06）

## 保存状態

初版code `feb32e511bba6611567b95f01e98818e07fbe5d4` のWindows試行は **failed**。生成、初回reader、保存データreader、算術子の4 processはexit0・回収済みだが、算術子の終了記録を渡す接続部で引数名が一致しなかった。監査、文書・slice生成、writer、fresh readerは未実行。全工程予算の成功には数えない。

修正codeは `da454ff7fa6bd161432376ba8e39d7f581c4e205`。`LinkedBudget.record_role` が呼出し側の `result_pin`／`worker_pid` keywordを受けるよう修正し、同じkeyword形式の試験を追加した。修正版の実機再試行は **未実施**。ユーザーの「キャパ超えないように」という追加指示を受け、今回は修正・証拠・引継ぎの保存で区切った。追加agentは起動していない。

正式gateは `s4_acceptance_not_frozen`、`formal_permission=false`、credit0。登録holdout40 seedは未読・未使用。実設備・顧客データは読んでいない。今回の2 dataset／6評価は固定 `hand-normal-v1` による架空観測で、登録identityは形式上の識別子としてのみ使用した。

## 接続した範囲

[外側予算実装](../../src/banto_ai/anomaly_v03_preformal_generation_publication_budget.py)は、次の7子processを一つの外側時計へ接続する。

1. owned generator：架空2 datasetと6評価、22保存ファイルを新rootへ生成。
2. initial reader：生成されたphysical payloadから観測→profile・score→ledger・summaryを再導出。
3. saved reader：別processで同じ保存attemptを再読取し、初回reader全値との一致、6行保存、22ファイルの終了時再照合。
4. analysis：40 cluster・50,000 drawの全算術。
5. audit：別processで算術を監査。
6. writer：文書・sliceの5 payloadを新しい公開rootへ保存。
7. fresh reader：writer回収後に公開payloadとmarkerを読む。

各工程の既存local sampler・上限・receiptを維持し、[接続部](../../src/banto_ai/_anomaly_v03_outer_budget_link.py)が外側の停止通知、終了記録、3 mapping出力pinを中継する。local samplerは各工程が閉じ、外側samplerは全工程のcallerだけが閉じる。sampleとcheckpoint、owned child supervisorのprobeによる協調停止であり、hard quotaではない。

新しい外側scopeは **1区間の架空観測＋479区間の明示的metadata fixture**。新readerの10 control pinは、所有した工程の出力pinから時計内に捕捉する。22生成物の期待pin、4数値入力の期待pin、source snapshotの事前準備は時計外。数値入力の参照は先行の独立照合済み同recipe／同区間fixtureで、今回の実入力との一致を要求する。全480区間の観測campaign確認、共通campaign由来の認証、正式評価へ読み替えない。

## 予算とroot

外側の既定上限は1,800秒、parent private512 MiB、4新root合計321 MiB／672 entries／depth12、commit・RAM余裕各4 GiB、disk空き10 GiB。callerは上限を厳しくする変更だけ可能。

| 測定root | logical bytes上限 | entries | depth |
| --- | ---: | ---: | ---: |
| outer receipt | 1 MiB | 32 | 2 |
| producer | 192 MiB | 256 | 12 |
| saved reader | 32 MiB | 256 | 8 |
| document/publication | 96 MiB | 128 | 5 |

4rootは固定された互いに包含しない新pathのみ。root identity、unsafe link/reparse、消失、個別上限、合計上限をsampleする。公開markerの既知2 hardlinkだけは既存規則に従う。外部manifestと事前pin、元metadata controlは新rootのdirectory合計に含めない。元4,800 controlは時計内で読取り・再照合し、既存256 MiB input上限を維持する。

初版rootは次のとおり。raw artifactはローカルのignored証拠で、文書commitと一緒にpushされるファイルではない。

- outer：`artifacts/anomaly-v03-preformal-generation-publication-20261006-e01/`
- producer：`artifacts/anomaly-v03-preformal-registered-attempt-e01/`
- saved reader：`artifacts/anomaly-v03-preformal-saved-row-reread-20261006-e01/`
- publication：`artifacts/anomaly-v03-preformal-saved-row-document-budget/trial-20261006-01/`
- helper：`artifacts/anomaly-v03-generation-publication-20261006-a1/`

## 初版実機の結果

Windows26H2/build26300/UBR9457、CPython3.14.0。選択sourceを実行前にworking/Git rawで照合。全source closure、ロード済みstdlib・拡張・DLL・CRT・外部program inventory、正式runner同定の採択は未完了。

| 工程 | PID | 子の秒数 | 終了 |
| --- | ---: | ---: | --- |
| generator | 9228 | 343.861758 | exit0・回収 |
| initial reader | 38084 | 100.999180 | exit0・回収 |
| saved reader | 1448 | 92.572751 | exit0・回収 |
| analysis | 2096 | 109.216876 | exit0・回収 |

生成は343.9／360秒で上限に近い。保存readerのlocal工程全体は99.234740／120秒でpass。22 physical file／131,144,119 Bを確認し、全6行は正当なinconclusive。区間0だけを置換し、479区間の元metadataと失敗履歴を保持。4入力は事前pinと一致し、全体fixtureはsuccess2,874・inconclusive6。

analysis子の終了後、親の `record_role(..., result_pin=..., worker_pid=...)` が `TypeError` を起こした。算術結果の親側最終検証より前の失敗であり、全算術・監査完了は主張しない。外側receiptに記録された子は先行3役のみで `all_seven_child_exits_reported=false`。failed result・算術出力・各supervisionを保全した。

外側時計773.987111秒、parent peak199,696,384 B、合計peak137,560,507 B／72 entries／depth10、最小commit余裕9,730,191,360 B、RAM9,249,714,176 B、disk402,622,545,920 B。resource stopなし・sampler joinedで、resourceの `passed=true` と工程全体の `status=failed` を区別する。空きdiskの大きさだけで正式同形容量2倍の確認済みとはしない。

## 試験・保存照合

- 初版：外側予算・既存生成budget・保存reader・document・disk controlの56試験pass（61.456秒）。
- root identity固定追記後：専用8試験pass（1.066秒）。
- keyword修正後：専用8＋既存生成budget5の13試験pass（1.694秒）。別runの結果であり、件数は合算しない。
- [失敗記録checker](../../artifacts/anomaly-v03-generation-publication-20261006-a1/check-failure.py)：product import／reader・数値replayなし。46 raw、22 physical payload、4役exit0・回収記録、57件の**過去Git blob**のpinを照合してpass。修正後のworking sourceを初版sourceと同一とは主張しない。
- diff check、計画・registryの凍結raw SHAは維持。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| e01 outer result | 15,139 | `d476d641a25bfeb542b012cded517d27c7cb79105c4445e35dc942f353090a5c` |
| e01 outer budget | 5,699 | `d639504567ea57ce5e2be62dce165462d2a105c67391ba4af95657d7fb39ac82` |
| trial-01 failed result | 12,826 | `49f1b553c71595beb2a8993dba44b1d2deeb0748b6a40057bfe789287aa84ed3` |
| trial-01 local budget | 4,225 | `d25b9a45ef087eee5a994d8e2340a1548d5866750b5ccbd641cdcd4c2211e3e3` |
| analysis supervision | 519 | `ca606103dbf859186274f0d7f0a1a6ad3a1e2f39147623d1722895552d20b211` |
| a1 failure note | 1,600 | `15a2a1477523d925cf7db7b4deacc2cfffed0b3baa094d6debeb8f0e9619f614` |
| a1 failure check | 11,295 | `cec4881a7df066d4719b51739308175aaa894df905130e08d3f123e1d455412a` |
| e01 external manifest | 75,734 | `cd4815552117017ed6369e5b62f8f1d1718e207691f9ef421ff6a7a0d486b613` |
| a1 request | 2,020 | `51e6bee81e99d25a6cc608aff58fece4d759ceb4e23ae4339972493ffab80b5a` |
| a1 execution | 570 | `8d87274d548e8c2b84496627130d62d38a8d9f6518bc3a1cb4002539e5ee3220` |

## 次の有限作業単位

修正版 `da454ff` に対するe02 manifestとa2 helperの期待4入力までは準備したが、e02 producer／reader／publicationは起動していない。e02 manifestは75,734 B／`a4a816837ffc4d9ad66e6d43db85a3760a156bf30fe4c5ee4b22e095f728b2f6`、a2 requestは2,019 B／`1c87f977dab7ebd4a41a0869affb44133ee9a79c943dde8cc2cbcd4ec5c92f4c`。[deferred.json](../../artifacts/anomaly-v03-generation-publication-20261006-a2/deferred.json)は1,613 B／`caf37435c22a5528cd42f7f4906da51d2f5b3ec9fe136947c6dc0446916c223d`。全helper pinは同ファイルへ保存した。

文書commit後のHEADは `da454ff` と異なる。**e02 pinsetを新HEADへ読み替えない**。次回はその時点のclean HEADで新root／新pinset（例e03、trial-03、a3）を作り、a2 helperのroot・revisionを明示的に更新して同じ実機試行を1件だけ実行する。成功時は7役と3 mapping、公開payload／marker、最終22 payload／10 control、source/runtime前後を保存checkerで照合する。a2の長い全工程checkerは構文準備のみで、実データに対して未実行。

その後に正式同形のsmoke見積りと2倍空き、26H2・公開保証A/B・runner同定の版付き契約採択、source/runtime全在庫、最終revisionのUbuntu両minor・Windows／正式dev8/smoke2・独立受入が残る。架空480区間を新規生成することを追加必須にはしない。正式評価・holdout実行は許可していない。
