# v0.3 正式評価前の役割profileと架空保存attempt検証（2026-10-04）

状態: **26H2向けの未採択preformal検証**。code保存点は `09b4da2291634ee07ff1eacb74d3ca114c1d76b4`。旧25H2正式gateは `s4_acceptance_not_frozen` のまま。登録holdout観測の生成・読取り、正式評価credit、S5/S6、候補昇格は0である。

## ５役の作業前候補profile

[5役fixture](../../src/banto_ai/anomaly_v03_platform_five_role_fixture.py)に任意の外部pin付き候補セットを渡せるようにした。渡した場合、producer起動前に参照試行のtop・共有予算・各役のresult、supervision、子応答、依存before/after、親crosscheckの生bytesと、選択sourceの作業raw/Git blob、現在のOS/Python tupleを再照合する。各子はinvocationと必要入力を読んだ後、対象のarchive読取り・数値処理・公開/読戻しを始める前に候補のbefore依存とruntimeを照合し、終了時にafterを照合する。親は子のexit/reap後に保存pinと結果を検査する。候補なしの発見用経路も残した。全て架空40 cluster・1 draw・通常権限の検証である。

| 保存試行 | 結果 | raw file pin | 境界 |
| --- | --- | --- | --- |
| [trial-09 参照](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-09-prework-reference/result.json) | 5子完走、66.118秒。共有予算243標本pass | top 7,214 B / `86f4303551fdf232132b5f4fab4d16898783a053abe949f63873b5e9f69de79f`; [budget](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-09-prework-reference/resource-budget.json) 4,896 B / `01aab1d6c998b7b028b11568daf68faf041e07b9da476e5f39ca21bcf11ce203` | 同一clean revisionの候補作成元。`profile_required=false`、`before_work_profile_enforcement=false`。 |
| [外部pinset](../../artifacts/anomaly-v03-preformal-profile-pinsets-26h2/trial-09-reference-pins.json) → [候補セット](../../artifacts/anomaly-v03-preformal-role-profiles-26h2/trial-09-prework-candidates/candidate-set.json) | ５役×５件の参照raw pinから５候補を別rootへ保存 | pinset 3,235 B / `f357e788ae5b0418954009c726b13d336408d90bcfbf26b415583c74f970e2bf`; set 2,141 B / `c47d7a09e052670e7dbfbbd86691385459b5186159a27f45cbcc7a70f24b5e16` | producer/analysis/audit/writer/readerの２点snapshotとruntime候補。未採択。 |
| [trial-10 候補必須](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-10-prework-enforced/result.json) | 5子完走、72.818秒。共有予算270標本pass | top 7,328 B / `e9b151b885aeac6404d39d9d04dca13d18a2f820f7e63425d3154b9abce7213b`; [budget](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-10-prework-enforced/resource-budget.json) 4,892 B / `23f660bfe78488ba4dfa9a558436a3b09833f4b36d20291e35ae0162ccea9a89` | ５子の別PID/開始識別子、exit 0/reap、invocationと結果の候補pin、実before/after依存・runtimeが候補と一致。`before_work_profile_enforcement=true`。 |
| [trial-11 誤pin](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-11-bad-set-pin/result.json) | preflightで拒否、所有子0 | top 1,600 B / `f704a9c8cdd167f14f8192c3308a6e7112b0150005501558049465c75292d9ec`; budget 2,889 B / `406db8d4c3a211a95bb8ad8163ec0554dbb316e979170167425176dd7b809c17` | 外部候補セットpin不一致をproducer起動前に保全。 |
| [trial-12 15秒停止](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-12-profiled-wall-stop/result.json) | producer中に`pipeline_wall_limit`。子を停止・回収、後続４役未起動 | top 3,105 B / `6519282ce8534b8b581d04fd29d4aa776a75b566862c9001e8a383c057c08d61`; budget 3,243 B / `3b4fd7c52dd9b9b9b3438eaa1f59c17b3d6fed6531221e238e36991f4b4e09c3` | profile必須経路でも共有wall停止と監視終了を確認。 |

trial-10の最終rootは26,702,169 B/115 entries、共有上限48 MiB/256 entries以内だった。最大標本は26,689,949 B/113 entries、親peak private 101,789,696 B、最低commit余裕18,202,013,696 Bである。trial-09の最終rootは25,317,761 B/110 entries。独立postcheckは両試行のpinset・候補・５役の保存記録、選択sourceの作業raw/Git、exit/reapに不一致0件。共有予算は標本と協調停止でありhard quotaではない。以前の外部archive rootはこの予算に含まない。

初回の候補必須[trial-08](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-08-prework-enforced/result.json)は、親がprofile生bytesをJSON比較に渡した型誤りでanalysis起動前に停止した。producerのみexit 0/reap、後続と公開markerは未生成、失敗receiptを保全した。[修正](../../src/banto_ai/anomaly_v03_platform_four_role_fixture.py)を `09b4da2` に保存し、trial-09から新しい参照・候補を取り直した。trial-07/08の旧revision候補を新revisionの事前期待値として流用していない。

候補は観測されたdisk file集合とnative file集合を２点で比較する。in-memory code、既存`.pyc`候補の実ロード、将来の動的ロード、探索経路全体を証明せず、`source_closure_complete=false`、`runtime_closure_complete=false`、`execution_authenticated=false`を維持する。writerは公開markerを確定した後に終了時profileを照合するため、その照合失敗ではmarkerが残り得る。marker単独を成功証拠にせず、writer/readerの終了と外側のverified receiptを要求する。この公開保証は正式受入前の残件である。

## 架空保存データを読む２つの境界

| 対象 | 今回検証したこと | まだ認証しないこと |
| --- | --- | --- |
| [架空dev１区間のpartial reader](../../src/banto_ai/anomaly_v03_saved_chunk_summary.py) | 固定計画の区間0・２dataset・６評価を実attempt形式のpathから読み、20入力pin、元観測→48 profile/14,400 score→独立ledger→主/sliceを評価ごとに再導出。専用anchorは区間0のみ・next=1を宣言する。[試験](../../tests/test_anomaly_v03_preformal_full_chunk_fixture.py)は偽の120区間完了宣言、改変、最新失敗attemptを拒否。完成reader側も120件すべてのindex/verified statusを要求するようにした | 残り119区間のcoverage、元観測の生成、補助fileの意味、登録holdout、実producer終了。元観測は固定の架空bytesで、６評価は全てinconclusive。 |
| [架空登録形式の保存attempt reader](../../src/banto_ai/anomaly_v03_registered_saved_attempt_fixture.py) | 固定登録identityを**架空データのschema目印**として使い、専用rootの`run/attempts/chunks/.../result/payload`から２dataset・６評価の22 fileを外部pinで読む。登録契約、報告score→ledger/主/slice、元の架空観測→全profile/scoreを照合。[試験](../../tests/test_anomaly_v03_preformal_registered_saved_attempt_fixture.py)は正式mode、最新失敗、file/外部pin改変、再pin済みscore改変を拒否 | 実際の登録holdout観測、実producerのexit/reapとsource/runtime、480区間のcoverage、50,000 draw、完全S6。試験の一時rootは終了後削除する。`actual_registered_observations_read=false`、正式credit0。 |

現環境で純粋profile試験35件、partial reader関連28件、登録attemptと既存score/登録契約/readerの狭い回帰33件がpassした。26H2専用Windows platform fixtureのnative８件もclean `09b4da2` でpassした。旧25H2 engineering publication単独試験は現26H2を`unsupported engineering runtime`で拒否し、これを26H2回帰の失敗や正式runtimeの変更とは扱わない。repository safetyはpass。最終clean revisionのLinux CI 3.12/3.14実行証拠とrunner image digestはまだない。

## S4採択と実データ作業の残件

1. [運用契約26H2案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)と旧25H2計画との差、公開marker/失敗時保証、役割別完全source/runtime閉包、実行identityを版付きで受入れる。今回の候補profile一致を完全閉包へ昇格しない。
2. 登録形式の実保存attemptについて、**固定した架空入力を生成する所有producer**の終了証拠・外部pinを今回のreaderへ渡し、全評価の観測導出、最新attempt/失敗保全、完全な条件別在庫を同じ入口で検証する。今回の一時fixtureは実producerの証拠ではない。
3. producer→登録reader→40 cluster/50,000 drawの全表・文書→別実装の完全監査→stage/writer→別readerを、最終clean revision・同一外側wall/root/資源予算で測る。現在の５役は１draw、別保存点の50,000 drawは算術のみで、時間やbytesを足して正式予算にしない。旧計画§9の空き容量２倍条件は最終smokeから判定する。
4. 対象revisionのLinux CI 3.12/3.14、Windows native、stdlib/repository回帰と独立再監査を照合する。既存CI workflowの定義は実行結果ではない。runner image digestの採取元は未確定。
5. 既存の保存済み合成dev/smoke 120区間・720評価はengineering参考証拠として保持する。上記をS4条件として確定後に新版dev/smokeで受入を行い、未使用40 seed・480区間・2,880評価の登録holdoutはS4採択後のS5でのみ扱う。既存720評価をholdoutへ改名・加算しない。

`formal_permission=false`、`promotion_allowed=false`、`independent_s6_complete=false`、`selected_candidate=null`を維持する。本書は受入範囲と次の実データ作業を限定する記録であり、正式評価の開始許可ではない。
