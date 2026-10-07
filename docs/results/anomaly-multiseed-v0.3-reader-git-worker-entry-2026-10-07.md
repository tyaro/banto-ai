# v0.3 initial-reader Git worker入口の保存（2026-10-07）

code `202b1c3081f34592e4a79188cda7f15cc9f4ec5f`。gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。実データは保存済み合成dev8/smoke2のengineering読取り・記述報告のみ。

## 接続した範囲

- reader_worker_mainのopt-in worker_git_entryを追加。caller保持channel request/policy/inventory pin、revision/repository、budget root identityを読取り、binding待機後に元Actorを作る。新runtime profile pinを必須とし、profile読取り/観測/元_read_attemptを終了guard内へ渡してから既存JSON報告へ進む。既定経路はcallback-freeを保持。
- _source/_read_attemptへ明示source_filesを渡し、Git identity/blob callbackを実ソース読取りへ接続。新16 helperを含む選択30 source/phase、head/status＋30blobの各phase32要求、予定全64 Git Jobを固定。source_names/phase/operation/外部pin不一致は拒否し、bare Git fallbackを使わない。64は準備した在庫数で、native終了数や全Git閉包ではない。
- prepare_entryはcaller-held inventoryを測定channel内の固定worker-inventory.jsonへexclusive保存・readbackし、別clockを始めない。Child checkpointは元shared clockとouter leaf identity/1MiB/32entry/depth2/reserve128KiBを同期確認し、IO/clock/root異常をlatchして新Jobを止める。
- parentの全4root sampler/321MiB/672entry、worker memory/元Job上限はこのcheckpointでは代用しない。実generate_and_readのParent.create/on_started bind/stop_fenceとcaller-held verifier、全体budgetへの受渡しは次段階。新native0・追加agent0・全helper終了・critical ownerなし。

## 焦点試験と失敗保全

初回12件/5.246441秒は8pass/4fail。invocation fixtureにio.json_bytesの末尾改行を使い、既存CLIの改行なしcanonical_json検証で入口到達前に止まった。fixtureだけcanonical_jsonへ訂正。4失敗と、同じ誤理由でpassしていたprofile必須拒否1件の計5件だけ再確認し、4pass/1fail/1.587366秒。残るResourceStop期待は既存CLIがfailure JSON/exit2へ変換する仕様に対するtestの誤りだった。guardへ元ResourceStopが渡り、success/fallbackにならない期待へ訂正し、その1件だけ0.365724秒pass。他7件反復0、旧actor/terminal等のsuite反復0。distinct12を最終source単一12success runへ読み替えない。

各runで28 source/science pin前後不変、変更test以外の27pinは全3run一致。変更3file safety、最終unique12 discovery、clean code-save28 working/Git一致を確認。helper41364/creation134358431412133142、43536/134358432553043237、1752/134358433386239156の元tokenは各live rawへ保持し、exit1/1/0とCIM残存なしを照合。

raw: artifacts/preformal-reader-git-worker-20261007-prep/。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json（初回8pass/4fail） | 10754 | `59cf92bd08f9e7b0b75ce90d353b4da13f593d7d6c06b2bf339cf06c1b191058` |
| corrected-five.json（4pass/1fail） | 9861 | `6ae6c0f90f74cff132adb5ed2415b4bbb9a2f3a182d499b78749eea1a6d6472f` |
| stop-one.json | 9306 | `66b42f08ae1a09bc2383dd2209d9192e0c4203263d2d25d436c6bae6944d574f` |
| focused-components-final.json | 6813 | `6b37afcfb4fb348a6f331d78ea78fd2eed117483bf380fae5a19968d0abcbebe` |
| code-save-checkpoint.json | 541 | `d7b4d70e0d4f046d659ffb5a3f8b378ba28caa817a8298dd0aaa1b62b2979b8a` |

fake Kernel/executable/creation/checkpoint、entry/runtime observer/actor-call spyによるprotocol確認で、実exe/Win ABI/native認証/容量合格ではない。runtime profileはまだ新revisionで準備していない。30 selected sourceも完全なsource/runtime閉包ではない。

## 次の保存単位

実callerはanomaly_v03_preformal_owned_generated_attempt.generate_and_readのreader_started/on_startedとreader supervisor。ここへParent channelのbind/fenceをopt-inで渡し、caller-held raw resolver/verifierと元Popen・creation identityを結ぶ。worker kill/waitやmarker不在/root exitを子Git回収済みへ読み替えない。元keeper/raw/partial archiveを失わず、未回収時は後続Git/workerを拒否する。

新source/runtime inventory/profileを新revisionで準備し、旧14/14や古いpinを流用しない。producer非対称pre26/post24を親111/111へ渡さない。archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、既存outer/全体root上限・cleanup30秒/poll0.25秒を維持し、control完成4+pending4/inventory-manifest/proof-pending/archive/inflight失敗rawを計上。実親接続/拒否/停止保全とexclusive準備が完成するまで新nativeを開始しない。

CI37602415125（外部HEADf0ecd89）は各minor3276/fail0/error0/skip237/source不変・全3job success、10raw/14pin/local-remote一致/共有29/必須28/runner v2 consistent_candidate/保存後照合まで完了。未保存は37604591211（13ac6a1/3286予定）、37605468456（e1b8924/3287予定）、新37609649219（202b1c3/3299予定）。digest未取得・候補未採択、正式採択/最終受入/正式5残件は未完了。
