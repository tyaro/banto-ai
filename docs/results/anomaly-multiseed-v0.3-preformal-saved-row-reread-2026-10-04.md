# 架空保存rawの再読取りから６行投影までの共通予算（2026-10-04）

## 目的と境界

前の[部分行由来](anomaly-multiseed-v0.3-preformal-saved-row-lineage-2026-10-04.md)は、保存済みg02 reader resultとreportを新しいconsumerが再照合したが、今回のconsumer自身は131 MBのpayloadを再読取りしなかった。今回はg02の架空保存rootを外部pinで固定し、**新しい所有reader子が保存raw22件を再読取り・観測→profile/score→ledger→主/sliceを再導出してから、その結果を親の６行投影に結ぶ**。readerと投影は新rootの同じ外側予算・停止probeに置く。実登録holdout観測は扱わない。

対象は架空登録形式の１区間６評価だけである。g02の既存入力131,144,119 Bと起動前pinsetは**新rootの容量集計外**、読取りwall時間と子privateは今回の監督範囲に入る。前のg02生成子→reader２役184.919秒と今回の時間を合算して全工程予算とはしない。正式gate `s4_acceptance_not_frozen`、正式評価credit０を維持する。

## 保存試行

clean code保存点 `a80c87b46ca32b0cb9971d3ee397a8546114ff82` から、[新しい入口](../../src/banto_ai/anomaly_v03_preformal_saved_row_reread.py)と[CLI](../../tools/preformal_saved_row_reread_trial.py)で`r01`を実行した。外部入力はg02の[起動前pinset](../../artifacts/anomaly-v03-preformal-generated-pinsets-g02/pins.json)72,149 B / SHA256 `22ee6888d731c827162b09ef1332cb61fe6a5542372e3e499ea0088fd214f1ef`、旧[２役result](../../artifacts/anomaly-v03-preformal-registered-attempt-g02/owned-generator/result.json)10,528 B / SHA256 `354c8ae043486c8f5ee2a99780ea5ee5a9395ed92daaca790187e8e9ab7c1179`。過去のg02 source revisionは`3be274c59ce4ffa0b5b60ba42993e2aa44a57039`、今回のreader/投影は上記の新しいclean revisionであり、別の実行として記録した。

| 新root `artifacts/anomaly-v03-preformal-saved-row-reread-r01` | bytes | SHA256 |
|---|---:|---|
| [６行の部分投影](../../artifacts/anomaly-v03-preformal-saved-row-reread-r01/rows.json) | 116,085 | `134dc17e98dd5ef3ac24431e463436cbcc73a4f869b5262a5428d998d45d66d9` |
| [最上位result](../../artifacts/anomaly-v03-preformal-saved-row-reread-r01/result.json) | 8,449 | `d676de043e22226d0fa6e547d2ad77703931056c9b7b9ad0d36ca2154c7453f4` |
| [共有予算receipt](../../artifacts/anomaly-v03-preformal-saved-row-reread-r01/resource-budget.json) | 1,705 | `185af694e21513903563dd55e95995aef756df060bb6a2c453240142a28e3843` |
| [別rootの独立postcheck](../../artifacts/anomaly-v03-preformal-saved-row-reread-postcheck-r01/postcheck-result.json) | 1,707 | `61fa4a220c4d4d11d6f57fa19c9e6a1bc680222d4bc096323840d9582bac2b8a` |

所有reader子PID 27424は別開始tokenでexit 0/回収、92.572秒、peak private 315,613,184 B。前g02のreader resultと**全dict一致**し、保存payloadの再照合後に親が同じ予算で６行を投影した。外側の標本予算は120秒/親512 MiB/新root32 MiB/256 entries、最低commit/RAM各２GiB・disk５GiBで、97.319秒/373標本pass。親peak private最大31,948,800 B、監視中の新root最大202,627 B、commit最小余裕15,883,526,144 B、RAM最小余裕17,358,401,536 B、disk最小空き367,711,268,864 B。終了後のrootは７file/212,781 B。これは標本と子supervisorの協調停止であり、OS hard quotaではない。

`rows.json`は純粋投影の再利用可能な出力で、`saved_payload_bytes_rechecked=false`と`reader_execution_authenticated_here=false`を保持する。今回の実際の再読取り・終了確認は最上位resultの`fresh_saved_payload_bytes_rechecked_this_run=true`、`fresh_owned_reader_exit_confirmed_here=true`と新しい監督・stdout pinで表す。こうして投影関数単独の主張と今回の所有processの証拠を区別した。40 cluster/診断/slice sourceは`null`、正式評価credit０、`source_closure_complete=false`、`runtime_closure_complete=false`、`execution_authenticated=false`を維持する。

[４試験](../../tests/test_anomaly_v03_preformal_saved_row_reread.py)は子失敗、新旧reader不一致、予算停止時に`rows.json`を出さないことを確認。前の行境界と合わせて９試験pass。[別実装postcheck](../../tools/preformal_saved_row_reread_postcheck.py)は131 MBのpayloadを再読取りせず、保存された子invocation・監督・stdout、全reader結果、６行、予算receiptと外部pinを再照合して不一致０。repository safetyもpass。

## 次の受入事項

この１区間が同じ予算で検証できても、残り479区間と40 clusterは成立しない。現g02のsavepointは区間番号と個別`run_root`を含むため、480件のsavepoint SHAを同一にする設計は誤りである。40 clusterへ進むには、区間別の外部pin・最新attempt・６行・凍結identityを検証する結合契約に加え、**区間間で共有するproducer/campaign由来anchor**が必要である。現在の登録registry pinや同じsource revisionだけでは、全区間が同一の実行から来たと証明できない。

S4前は架空の固定入力経路と最終dev8/smoke2で受入を行い、実holdout 480区間の成功を開始条件として要求しない。S4採択後のS5で未使用40 seedを実行し、S6で全件を独立再監査する。26H2運用契約、５役source/runtime完全閉包、Linux必須jobとrunner image、producerから公開後readerまでの単一外側予算も残る。
