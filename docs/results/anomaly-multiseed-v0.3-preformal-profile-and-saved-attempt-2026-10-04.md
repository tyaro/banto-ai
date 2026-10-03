# v0.3 正式評価前の役割profileと架空保存attempt検証（2026-10-04）

状態: **26H2向けの未採択preformal検証**。５役の初回code保存点は `09b4da2291634ee07ff1eacb74d3ca114c1d76b4`、保存済みproducer→50,000 draw算術接続の初回は `cca54e9e1083d92f4cdf85aae65fdef943929bcf`。writer事前再照合と所有materializerを含む再試行はclean `723eaf1d83ba2f1d42abee9dbe54d57da1d2959d`、別reader子のnative試行はclean `e79479077c7f55cf0398d0e5add41b989e9c936b`、５役/50,000 draw再試行はclean `94be9ed2702d2f383acb952ea1cf24b21b9754fc`。固定手作り系列の所有生成子→別reader子はclean `6ad2631c27f39720a461ad203fc5de7b86e81e5a`、同じ２役の共通外側予算はclean `3be274c59ce4ffa0b5b60ba42993e2aa44a57039` で実走した。保存済み50,000 draw算術→架空文書草稿の写像はclean `6e96644b7bf28e287b458648f189247cfc6952ac` で実走した。旧25H2正式gateは `s4_acceptance_not_frozen` のまま。登録holdout観測の生成・読取り、正式評価credit、S5/S6、候補昇格は0である。

## S4採択前の受入見取り図

| 受入事項 | 現在の確定範囲 | 採択前に要る証拠 |
| --- | --- | --- |
| 26H2運用契約・公開保証 | 未採択v2案。writer子の`.complete`前再照合と失敗保全は検証済み | 旧25H2条件との差、marker残存時の扱い、旧§8の保護DACL・独立token条件を保証A/Bのどちらで扱うか版付きで決定・再監査 |
| 登録形式の保存入力 | 固定手作り系列を所有生成子が12 dataset入力payloadへ物理保存・再読取りし、そのbytesから６架空評価を計算。４制御fileと合わせて22 fileを保存し、事前外部pin・完全在庫・生成子exit/reap後の別reader子による再導出を照合 | 実登録holdout観測と登録seedに基づく生成・読取りはS4採択後のS5まで閉じる。役割の完全source/runtime/identity閉包、正式共通予算とS4採択は未了 |
| 数値・文書・全工程予算 | ５役の架空１drawと、保存済みproducerからの50,000 draw２算術子は別々に成功。架空１区間の所有生成子→別reader子は１つの外側予算で完走。保存済み50,000 drawの９主表を、別試行で十項目の架空文書草稿へ写像した（正式証拠５欄は空） | 架空2,880行→40 clusterの入力系譜、50,000 drawの全文書・slice/sidecar・完全別監査・stage/writer・公開後readerまでを共通外側予算で連続測定し、容量２倍条件を判定 |
| 実行環境と依存閉包 | 26H2実機で５役候補profile前後一致。選択source/Gitと観測runtimeのみ | 全役の実ロードsource/runtime/実行identity閉包、対象revisionのLinux CI 3.12/3.14・Windows native・runner digest |
| 最終dev/smoke・S4採択 | 保存済み合成120区間/720評価はengineering参考。現行readerのraw再監査は区間0/119だけ | 改訂契約と最終clean revisionでS1登録済みdev8/smoke2を新rootに完走し、独立照合とsmoke容量見積りを結合してS4採択 |

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

候補は観測されたdisk file集合とnative file集合を２点で比較する。in-memory code、既存`.pyc`候補の実ロード、将来の動的ロード、探索経路全体を証明せず、`source_closure_complete=false`、`runtime_closure_complete=false`、`execution_authenticated=false`を維持する。`068fb44`で[ローカル公開処理](../../src/banto_ai/_anomaly_v03_io.py)に任意の事前再照合を加え、profile必須の[writer子](../../src/banto_ai/anomaly_v03_fixture_publication.py)はpayload rename前後、`.complete`確定前に選択source・入力・invocation・依存snapshot・runtimeを再照合する。子でこの照合が失敗した試験では`marker-pending.json`とpayloadを残し、`.complete`とreaderを作らず、親失敗receiptを保全した。ただし親postflightで初めて失敗すると公開markerは残り得る。marker単独を成功証拠にせず、writer/readerの終了と外側のverified receiptを要求する。この公開保証は正式受入前の残件である。

### 事前再照合後の５役再試行

clean `723eaf1` の同一コードから参照を取り直し、別rootの外部pinsetから候補５件を生成して候補必須で再試行した。旧trial-09/10の候補を流用していない。

| 保存試行 | 独立照合済みの結果 | raw pin |
| --- | --- | --- |
| [trial-13 参照](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-13-precommit-reference/result.json) | ５子がexit 0/reap。事前候補なし | top 7,213 B / `85c48ed0935adfa9ac4f5c11ce02762bc783be84c2ea4cb9cd398aaed0b9fcbf`; [予算](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-13-precommit-reference/resource-budget.json) 4,901 B / `4f78225dca269009653a31d62d786c817ddcab590b3d4cbe63f618565130c245` |
| [外部pinset](../../artifacts/anomaly-v03-preformal-profile-pinsets-26h2/trial-13-reference-pins.json)と[候補set](../../artifacts/anomaly-v03-preformal-role-profiles-26h2/trial-13-precommit-candidates/candidate-set.json) | ５役×５件の参照fileを実bytesで照合し、各役のbefore/after snapshotとruntimeを候補化 | pinset 3,237 B / `09ce4e23ef10972d4dd124bfb486e7aaef69e0d41db413108581ad95a93ed863`; set 2,153 B / `3fff388ef445641d2040e0afff6c533f2d3bc1ba50eb35f6b9abdcb7f031b3e5` |
| [trial-14 候補必須](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-14-precommit-enforced/result.json) | ５子の別PID/開始token/invocation、exit 0/reap。候補pinと実before/after・runtime一致。公開markerと別reader readback一致 | top 7,329 B / `c7557f1dc05fb9024f6cda90b9c8eb46d67c830a343a3a4304a01df3ac08f02d`; [予算](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-14-precommit-enforced/resource-budget.json) 4,895 B / `25f6f6f02f20df6d3914c9ad79915bc14549b7a85e25cdc2098ccb4df7c8236c` |

trial-14の共有監視は74.539秒/277標本pass、最大標本root 26,690,081 B/113 entries、最低commit余裕18,207,379,456 B。最終root 26,702,305 B/115 entriesは48 MiB/256 entries内。独立postcheckは２試行の選択source 93行の作業raw/Git、各役の保存証拠・候補５件・公開payloadに不一致0件。writerの事前再照合時点に専用snapshot receiptはなく、成功receiptとコード経路の照合が証拠の範囲である。１drawの架空試行であり、正式同形の全工程予算・完全閉包・登録実観測には昇格しない。

別reader子の追加後も、clean `94be9ed` で同じ５役の候補を取り直した。これは独立した架空１draw試行であり、前節の登録形式２役や50,000 drawを同じ外側予算に入れたものではない。

| 保存試行 | 結果 | raw pin |
| --- | --- | --- |
| [trial-15 参照](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-15-two-role-reference/result.json) | ５子exit 0/reap、候補なし、65.458秒/240標本pass | top 7,212 B / `7389421cfc850222b73d55da9fdceb9be0e060903280778284d8b5bc94226a92`; [予算](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-15-two-role-reference/resource-budget.json) 4,896 B / `7c3aee2f41a328207335168ef1464fd1b885bfbea74a3d9b726ad84cf9b38573` |
| [外部pinset](../../artifacts/anomaly-v03-preformal-profile-pinsets-26h2/trial-15-two-role-reference-pins.json)と[候補set](../../artifacts/anomaly-v03-preformal-role-profiles-26h2/trial-15-two-role-candidates/candidate-set.json) | 参照５役の保存rawを別rootに固定し、候補５件を新規作成 | pinset 3,236 B / `6dcf644aa71cfe055c54243c0737492c24a5d5c2969a776509ce9b64f65c04ed`; set 2,147 B / `4cbbf0379505f53854e6aa65c7d9773f286b4e6f4fdaa2ab7354557b4b7b2c5e` |
| [trial-16 候補必須](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-16-two-role-enforced/result.json) | ５子exit 0/reap、作業前候補と前後依存・runtime一致、公開後reader照合、73.532秒/274標本pass | top 7,331 B / `b2f0abcc278d11a418de791e184888aeb0812f08abfd49d78eb02b466589c8c1`; [予算](../../artifacts/anomaly-v03-preformal-five-role-26h2/trial-16-two-role-enforced/resource-budget.json) 4,897 B / `42237789e1a5cc2feb6e2cf608645ef8e109f9a361340b18b91c6ca146e551c2` |

独立postcheckは２試行の５つずつの別PID/開始token/invocation、参照raw pin・候補５件・役割profile、33選択source fileのGit/作業bytes、公開marker/payloadとreadbackに不一致0件。trial-16の最大標本rootは26,690,013 B/113 entries、親peak private 103,219,200 B、最低commit余裕18,150,473,728 Bで48 MiB/256 entries内。共有監視は標本・協調停止でありhard quotaではない。`source_closure_complete=false`、`runtime_closure_complete=false`、`execution_authenticated=false`、正式credit0を維持する。

## 架空保存データを読む２つの境界

| 対象 | 今回検証したこと | まだ認証しないこと |
| --- | --- | --- |
| [架空dev１区間のpartial reader](../../src/banto_ai/anomaly_v03_saved_chunk_summary.py) | 固定計画の区間0・２dataset・６評価を実attempt形式のpathから読み、20入力pin、元観測→48 profile/14,400 score→独立ledger→主/sliceを評価ごとに再導出。専用anchorは区間0のみ・next=1を宣言する。[試験](../../tests/test_anomaly_v03_preformal_full_chunk_fixture.py)は偽の120区間完了宣言、改変、最新失敗attemptを拒否。完成reader側も120件すべてのindex/verified statusを要求するようにした | 残り119区間のcoverage、元観測の生成、補助fileの意味、登録holdout、実producer終了。元観測は固定の架空bytesで、６評価は全てinconclusive。 |
| [架空登録形式の保存attempt reader](../../src/banto_ai/anomaly_v03_registered_saved_attempt_fixture.py) | 固定登録identityを**架空データのschema目印**として使い、専用rootの`run/attempts/chunks/.../result/payload`から２dataset・６評価の22 fileを外部pinで読む。登録契約、報告score→ledger/主/slice、元の架空観測→全profile/scoreを照合。[試験](../../tests/test_anomaly_v03_preformal_registered_saved_attempt_fixture.py)は正式mode、最新失敗、file/外部pin改変、再pin済みscore改変を拒否 | 実際の登録holdout観測、実producerのexit/reapとsource/runtime、480区間のcoverage、50,000 draw、完全S6。試験の一時rootは終了後削除する。`actual_registered_observations_read=false`、正式credit0。 |

現環境で純粋profile試験35件、partial reader関連28件、登録attemptと既存score/登録契約/readerの狭い回帰33件がpassした。26H2専用Windows platform fixtureのnative８件もclean `09b4da2` でpassした。旧25H2 engineering publication単独試験は現26H2を`unsupported engineering runtime`で拒否し、これを26H2回帰の失敗や正式runtimeの変更とは扱わない。repository safetyはpass。最終clean revisionのLinux CI 3.12/3.14実行証拠とrunner image digestはまだない。

### 所有子による架空登録形式の物理保存

clean `723eaf1` に[所有materializer](../../src/banto_ai/anomaly_v03_preformal_owned_saved_attempt.py)を追加した。呼出者が別rootで宣言した架空22 file（saved 4＋payload 18）の生bytes/pinを起動前に固定し、所有子が専用の`run/attempts/chunks/000/attempt-0001/result/payload/`へ**コピー**する。子終了後、親が入出力の完全file在庫と22 pinを再照合し、既存の架空登録形式readerを親processから呼ぶ。子のPID/開始token/exit/reapと失敗時の記録を保全する。純粋試験９件、opt-in native１件はpassした。

保持した[native結果](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-01/owned-materializer/result.json)は9,953 B / SHA256 `61688e3f45325df2f251b1d47022e5764ef8a6f9a8b4d30c4946f5f059c6c069`。[外部入力pinset](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-01-external-pins.json) 4,336 B / `3d91b04e51c102d70c2010faeeef03f60fad3ed755f41bfa9cfb0813fda7641a`、[外部結果pin](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-01-external-result-pin.json) 318 B / `bbd6b2983aa8e555c4ea9e0bf2a389520d7728fea3d997f07cc2aaca09baad23`。独立postcheckは入力22 fileと出力22 fileの各126,317,406 B、完全在庫、全raw pin、所有子PID 31828/exit 0/reap、readerの22 file・６契約/行を不一致0で確認した。観測→profile/score→要約は**架空値について**再導出した。

この01のmaterializerは観測を生成せず、readerも別所有子ではない。従って`generation_verified=false`、`actual_registered_producer_executed=false`、`actual_worker_exit_authenticated=false`、`actual_registered_observations_read=false`、正式credit0である。実producer生成から別readerまでの連続した登録保存経路と、役割別source/runtime閉包は残件である。

`ca401d31fa7f8727b1299a23ee6ce89596f421b3`でこの所有コピー子のPython起動を`-I -S -B`に限定した。隔離bootstrapの純粋試験と監督argvの試験を追加し、clean codeの別rootで[native再試行02](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-02/owned-materializer/result.json)を保持した。result 9,953 B / SHA256 `50bb792bd54047a888aac903c4f2c74700f0c4bd085d070cec4d585eb580512d`、[外部pinset](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-02-external-pins.json) 4,336 B / `54d4a5d389306cc4c4524690f924c7cd3b7d234f0a51a9f8cba1369595a55a75`、[外部結果pin](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-02-external-result-pin.json) 318 B / `a16eb2af7e98c1e71d8e47be6878a6405c0e40b8d78d0d5d162a678b71dcc5ce`。独立postcheckは入出力の正確な22 file在庫と各126,317,406 Bの全raw pin、10選択sourceのGit/作業bytes、invocation・監督・子応答に不一致0件。監督argvは隔離３flag、PID 32536の所有子はexit 0/reap、3.561秒/peak private 275,787,776 Bで、親readerは架空22 file・６契約・観測導出を再確認した。起動flagはambientなPython startup経路を狭めるが、全source/runtime閉包や実行identityの正式認証ではない。

### 所有コピー子→別reader子の架空保存２役

clean `e79479077c7f55cf0398d0e5add41b989e9c936b`で、コピー子のexit/reap・出力pinを親が確認した**後**、既存の架空登録形式readerを別の`-I -S -B`所有子で実行する入口にした。reader呼出しはcanonicalな上限256 KiBのpin付きinvocationと、上限64 KiBのcaller宣言source snapshotを使う。親は別PID/開始token/invocation、readerのsource/runtime前後と出力pin、最新attempt・６行・score/ledger/主/slice再計算欄、終了/回収を検査する。各役の監督記録を別directoryに保持し、reader失敗・未回収は成功に変えずコピー子の記録も上書きしない。保存管理fileの外部pinをpayload pinで隠す入力は子起動前に拒否する。焦点試験は16件pass、native opt-in１件は次の別rootで実施した。

[２役native trial-03](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-03/owned-materializer/result.json)のtopは10,436 B / SHA256 `91244967cbd27c0579d72b35081cd2c5ce93604739b09ec899299f4c647a51dd`。[外部pinset](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-03-external-pins.json) 4,336 B / `3d7c6a7c5879afddc295c4682bf5224c737558337967c9403a60301c7e8ca733`、[外部結果pin](../../artifacts/anomaly-v03-preformal-registered-attempt-owned-03-external-result-pin.json) 319 B / `c7903e527aa37938ea1dd294ada5235a806a9f5fbb2fdc17908fc76a76cbc32f`。独立postcheckは入出力各22 file/126,317,406 Bの全raw pin・完全在庫、２役の異なるPID/開始tokenとinvocation・監督・stdout、10選択sourceのGit/作業bytesに不一致0件。コピー子PID 3840はexit 0/reap、3.490秒/peak private 275,959,808 B、reader子PID 25788もexit 0/reap、38.237秒/310,444,032 B。readerは架空22 file・６契約について観測→profile/score→要約を再導出した。reader子の個別上限は300秒/1 GiB/出力1 MiBであり、正式同形の共通外側予算を測った記録ではない。観測生成子は依然なく、`generation_verified=false`、`actual_registered_producer_executed=false`、`actual_registered_observations_read=false`、source/runtime完全閉包・実行認証・正式permission/creditはfalse/0である。

## 保存済み合成dev/smokeとproducer countの追加確認

[現行readerでの区間0再確認](../../artifacts/real-saved-chunk-000-current-reader-2026-10-04/result.json)は、過去の外部savepoint 8,366 B / SHA256 `ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d` を固定し、保存済み合成dev/smokeの選択入力20 file / 132,760,979 B（savepointとevidenceを加え22 file）を読んだ。結果6,608 B / SHA256 `9a02e5bb812e99c07ff6be5700cb2e565f2514a1c39a277be57bd9518aea5f5b`、新要約151,954 B / SHA256 `7c2240316a97e5b31c6a7d97e83b621b7f305efc581eb02077c2be4bd60b3977`。６評価の要約と選択入力pinは[旧pilot](anomaly-multiseed-v0.3-saved-chunk-000-pilot-2026-10-03.md)に一致し、要約全体の差分は`audit.elapsed_seconds`だけだった。現行の全120件目録guardは通ったが、元観測の再読取り・再監査は区間0だけである。所有子PID 512はexit 0/reap、12.292秒、peak private 160,751,616 B、別rootの資源監視51標本pass。新規評価0、登録holdout読取り0、正式credit0。

[区間119の現行reader再確認](../../artifacts/real-saved-chunk-119-current-reader-2026-10-04/result.json)も、同じ外部savepoint/evidenceを固定して保持済みの最新`attempt-0002`の20入力/133,301,078 Bを独立再hashし、20件すべてが保存pinに一致した。過去の失敗`attempt-0001`は採用していない。新result 6,714 B / SHA256 `9add2b8bf21a9aa97c9383b5b1dc9994c8ac2d3d1147f6bb76d9a60a81093c9d`、[新要約](../../artifacts/real-saved-chunk-119-current-reader-2026-10-04/summary.json) 152,141 B / `b3d9c21419b59391cb1c7d81e668bff3ecfb0d3efd54ea35d20453d91973bc58`。旧要約152,141 B / `b739e36e2d7267fb28bead9edaa2f31d0f34ad1ed32320383c0c106eceb0bd17`との差は`audit.elapsed_seconds`１項目のみで、６評価と監査配列は一致した。所有子PID 13004はexit 0/reap、16.304秒、peak private 160,813,056 B、資源監視pass。全120件の順序・状態を示すjournal guardは通るが、他の118区間のrawを今回再監査した証拠ではない。新規評価0、正式credit0。

[架空producer出力→50,000 draw接続](../../src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py)は、上記５役のtrial-10で所有producerが保存したresult 2,923 B / SHA256 `54e9690cd4c42c97c920f8efbd6f68b2fba842f75af6565c4e30738aec05fd5d`、bound 5,148,721 B、４投影fileを外部pinと再投影bytesで確認した。固定の架空40 calibrated clusterを別の主算術子と独立算術監査子へ渡し、50,000 draw hash `e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5`、主９表・117推定・72対応差・180 gateを照合した。

[bridgeの焦点試験](../../tests/test_anomaly_v03_preformal_bound_draw_bridge.py)７件、compileall、repository safetyはpass。コード独立レビューでは重大不具合0件とし、実機結果は次の別rootで判定した。

| 保存試行 | 結果とraw pin | 資源・境界 |
| --- | --- | --- |
| [trial-01 接続測定](../../artifacts/anomaly-v03-preformal-bound-draw-bridge/trial-01-owned-producer-50000/result.json) | top 6,413 B / `fb76cb56d559eb64ca89c0adcf00fc7563c16705def3ee4ac593ed959b0e688f`; input 155,179 B / `29696350e26634ab3dd53d5ec3a90412fbf22e8fe3ac9c7d5e9c60589e82b39c`; 主計算73,071 B / `0f850c0b4284fa7f44b8c631570d8c1ab36aa4f824e36db48e40b4e1d335a5be`; 別監査566 B / `07f405e5d52181ec07839b66ac75e0f7cbb4860f207ce0a09fb8db02e081eeae` | 主子PID 31708: 50.666秒/peak private 126,226,432 B、監査子PID 6440: 114.851秒/29,802,496 B。両子exit 0/reap。外側167.293秒/643標本pass、[予算receipt](../../artifacts/anomaly-v03-preformal-bound-draw-bridge/trial-01-owned-producer-50000/resource-budget.json) 3,518 B / `603adaa707e503592e603763bbaea791b42fd00fbc166b51b0c1e26b75843049`。最大標本root 230,700 B/9 entries（最後の２receiptは予約内）、最低commit余裕17,452,359,680 B。 |
| [trial-02 誤producer pin](../../artifacts/anomaly-v03-preformal-bound-draw-bridge/trial-02-bad-producer-pin/result.json) | preflightで`measurement file pin differs`、子0。top 3,334 B / `738d629c154dcab7a31c20e1e5396c3ad76b7c77e83ffc5af7f76dacbd355054`; [予算receipt](../../artifacts/anomaly-v03-preformal-bound-draw-bridge/trial-02-bad-producer-pin/resource-budget.json) 2,799 B / `821a7e663c85695bc359cb9278cf66ef09e17e43bc182c10cd5d1f4d645cf6af` | 失敗rootを保持。外側予算のpassは入力受入のpassを意味しない。 |
| [trial-03 現保存点から再測定](../../artifacts/anomaly-v03-preformal-bound-draw-bridge/trial-03-two-role-final-50000/result.json) | clean `94be9ed`のtrial-16所有producer result 2,927 B / `49d1d331a3d6bd7500746c791f2a8e1bcfb687c373ed526640201b28412e51d1`を外部固定。top 6,417 B / `2a932142900222f072e4568488f9a55cb79b669700c86201eeceab26d0027c92`; input 155,179 B / `97f225cdbc0286a23f9761b0d25b2279ea26b592eb781b06bc8406a24da2b211`; 主計算73,071 B / `0f850c0b4284fa7f44b8c631570d8c1ab36aa4f824e36db48e40b4e1d335a5be`; 別監査566 B / `07f405e5d52181ec07839b66ac75e0f7cbb4860f207ce0a09fb8db02e081eeae` | 主子PID 25628: 52.172秒/peak private 126,230,528 B、監査子PID 17632: 116.361秒/29,765,632 B。両子exit 0/reap。外側170.414秒/653標本pass、[予算receipt](../../artifacts/anomaly-v03-preformal-bound-draw-bridge/trial-03-two-role-final-50000/resource-budget.json) 3,519 B / `6d165825ddce2915f92ada6bc9a6cafe04e56bf62a4611916a3716ea12fbfa0c`。最大標本root 230,702 B/9 entries、最低commit余裕18,072,039,424 B。 |

独立postcheckではtrial-01の11出力fileと外部producerのresult/bound/４投影pinが全一致した。50,000×40 draw bytesを別に再生成して同じhashを得て、117主推定・72対応差のpoint/countを入力から再計算して差異0。全CI/gateの一致は監査子の別実装結果に依拠する。４投影の大きさは36,607 / 252,899 / 175 / 4,336,841 B、外部producer入力の論理合計は9,778,166 B。新しい２子だけの連続監視であり、過去producerの実行時間を足さず、登録保存reader・文書・writer/reader・完全S6を含む正式同形全工程予算とはしない。`formal_50000_draw_budget_measured=false`、`full_end_to_end_budget_measured=false`、`registered_data_read=false`、全source/runtime閉包・実行認証falseを維持する。

trial-03の独立postcheckでも11出力file、外部producerのresult/bound/４投影fileと10選択sourceのraw pinに不一致0件。50,000×40 draw bytesを独立再生成したhashは同じ`e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5`で、117主推定のcount/point・72対応差point・180 gate参照pointは差異0。quantile区間とgate合否そのものは今回のpostcheckで別計算しておらず、保存済み別監査子の結果に依拠する。外部producer６fileの論理合計は9,778,170 B。前のtrial-16 producer実行や登録形式２役をこの170秒に加算せず、正式同形の連続予算としない。

### 保存済み50,000 draw算術から架空文書草稿への写像

clean `6e96644b7bf28e287b458648f189247cfc6952ac` に[保存済み算術→文書ブリッジ](../../src/banto_ai/anomaly_v03_preformal_bound_document_bridge.py)と[純粋表写像](../../src/banto_ai/anomaly_v03_analysis_adapter.py)を保存した。別rootの新試行では、trial-03の[算術result](../../artifacts/anomaly-v03-preformal-bound-draw-bridge/trial-03-two-role-final-50000/result.json) 6,417 B / SHA256 `2a932142900222f072e4568488f9a55cb79b669700c86201eeceab26d0027c92`を外部指定pinとして再読取りし、既存予算receipt、主/別監査子の監督記録と終了、input・calculation・auditのraw pinを照合した。trial-16 producerのresult/bound/４投影fileも再投影・再照合し、`fixture/input.json` 252,899 B / SHA256 `1a7ed4256a5e867ce17e864ca7c857dcce16690543e222ccf550bb231dd083c1`の40架空clusterと診断を主算術inputに結んだ。投影側の旧drawは**１回**であり、50,000 drawは前の別算術試行の保存結果に限る。g02の１区間６評価とは別の入力系譜である。

[架空文書草稿](../../artifacts/anomaly-v03-preformal-bound-document-bridge/trial-01-saved-50000-document/document.json)は132,038 B / SHA256 `e6afff56cc71b284af81eac1850aa8ab11f03779e3d9a1cc251d2d610141b735`、[最上位result](../../artifacts/anomaly-v03-preformal-bound-document-bridge/trial-01-saved-50000-document/result.json)は6,001 B / SHA256 `11a2c209c1252a53d9af0ba1ab10ca9a5754729f23c49b4525c09e0b0c15aa03`。主９表・117主metric・72対応差gateを十項目下書きの表へ写し、計180 gateを保持して診断入力から有効稼働秒数と検出遅延を付けた。`status/provenance/analysis_consumer/bootstrap/slices`の５欄は`null`で、正式文書のschema受入・公開・完全S6は行わない。現在のclean revisionの選択source raw/Gitと26H2候補runtimeを前後で検査した。保存済み外部pinの検査を含む文書写像は2.068秒で、120秒は工程境界checkpointだけである。標本監視の外側予算でも、前回の170.414秒の算術と合算した共通予算でもない。

[独立postcheck v2](../../artifacts/anomaly-v03-preformal-bound-document-postcheck-01/postcheck-result-v2.json)は1,013 B / SHA256 `e0dab82b8f0104def6147139405ac19647c20edea9cf6ec710e8859be7d6c567`、[照合script](../../artifacts/anomaly-v03-preformal-bound-document-postcheck-01/postcheck.py)は23,467 B / SHA256 `7fc2688a098014fd8b767f6f89055865a25acf4f870465c320dea4876d314001`。外部pin鎖、2,000,000 indexの独立再生成hash、９表/180 gate/117主metric/72対応差参照、480診断cellと77,760検出遅延の文書集約に不一致0。CI分位点自体は今回のpostcheckで別計算せず、保存済み別算術監査子に依拠する。関連30試験と周辺67試験、repository safetyはpass。旧25H2専用の公開fixture native８試験は現26H2では既存`unsupported engineering runtime`で停止し、この旧runtime拒否は文書ブリッジを通さず直接再現した。今回の出力は`formal_document_validated=false`、`current_document_outer_budget_measured=false`、`full_end_to_end_budget_measured=false`、`independent_s6_complete=false`、正式credit 0を維持する。

## S4採択と実データ作業の残件

1. [運用契約26H2案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)と旧25H2計画との差、公開marker/失敗時保証、役割別完全source/runtime閉包、実行identityを版付きで受入れる。旧§8のprotected DACL・独立read-only token/AccessCheckは、保証Aを採るなら計画改訂・独立再監査で扱いを変更し、保証Bを採るなら26H2実機で再受入れる。今回の候補profile一致を完全閉包へ昇格しない。
2. 登録形式の架空保存attemptについて、**固定した架空入力を生成する所有子**の終了証拠・起動前外部pin・完全在庫を別readerへ渡し、最新attemptと６評価の観測導出まで確認した。実登録holdout観測のproducer証拠にはならない。今後は改訂S4の最終dev/smokeを受入れてから、S5の実登録入力へ進む。
3. producer→登録reader→40 cluster/50,000 drawの全表・文書→別実装の完全監査→stage/writer→別readerを、最終clean revision・同一外側予算IDと監視下の工程別rootで測る。現５役は１draw、50,000 drawは保存済みproducer countから２算術子を実走し、その保存結果から９主表の架空文書草稿を**別試行**で写像しただけである。g02の共通予算は架空生成１区間の２役のみ。別試行の時間やbytesを足して正式予算にしない。旧計画§9の空き容量２倍条件は最終smokeから判定する。
4. 対象revisionのLinux CI 3.12/3.14、Windows native、stdlib/repository回帰と独立再監査を照合する。既存CI workflowの定義は実行結果ではない。runner image digestの採取元は未確定。
5. 既存の保存済み合成dev/smoke 120区間・720評価はengineering参考証拠として保持する。上記をS4条件として確定後、S1登録済みdev 8 seed・smoke 2 seedを最終clean revision/26H2 exact tupleの新attempt/rootで全layout・両層・３候補について受入れる。未使用40 seed・480区間・2,880評価の登録holdoutはS4採択後のS5でのみ扱う。既存720評価をholdoutへ改名・加算しない。

### 架空入力の所有生成：実施前の計画

次の段落は実施前の計画を保持したもの。結果は後続の所有生成子native試行に記す。

既存の22 fileコピー子は試験履歴として残し、別版のengineering専用生成子を新rootで作る。親が子起動前に固定レシピID、chunk 0/attempt 1、22**出力**fileの外部pin、選択source/rawとruntime候補を宣言する。子には完成した観測・評価bytesを渡さず、固定した手作り正常系列から２層のdatasetを組み立て、保存して読み戻したbytesから６候補の評価を計算する案を検証する。`materialize_pair`と`normal_stream(seed)`は呼ばず、登録seed由来の観測生成を閉じる。登録identityと予定eventは形式検査用のmarkerに限り、`invented_only=true`と正式credit 0を維持する。この案の生成bytes・容量・評価契約への適合は未測定である。

受入は、子のPID/開始token/終了・回収、source/runtime前後、保存４制御fileと18 payloadの完全在庫・全外部pin、最新attemptの選択を親が確認してから、現行の別所有readerで観測→profile/score→ledger→主/sliceを再導出すること。制御fileを親から供給する場合は入力pinと生成**出力**pinを区別し、receipt/report内のhash主張も生成物に結び直す。pin欠落・誤pin、レシピ変更、余分なfile、最新失敗attempt、子の時間超過、reader失敗を成功へ変えない焦点試験と、clean revisionの別root native１試行を要する。現行fixtureの架空source名を実際の生成・採点sourceの選択証拠へ改める一方、完全source/runtime閉包を証明した扱いにはしない。既存fixtureの総量126,317,406 Bは128 MiB上限に近いため、生成時の最大file、合計bytes、保持memoryを先に測る。

### 手作り系列による生成の実現性試験

clean `58ca05a`（source treeは`94be9ed`と同じ）で、登録seedの`normal_stream`/`materialize_pair`を呼ばず、固定した５信号×18,000座標の手作り正常系列を`_build_pair`へ渡した。２層のdatasetを保存bytesとして扱い、`compute_evaluation`で架空６評価を計算し、純粋な登録契約・score監査と既存保存readerを通した。[成功result](../../artifacts/anomaly-v03-preformal-registered-attempt-gded7/result.json)は3,044 B / SHA256 `cef018bc7fd9d01744076cacbd4ed1db30d80836b479598089d367cfbc69713a`。22 fileは131,143,089 Bで128 MiB上限まで3,074,639 B、最大単fileは24,794,427 B。６評価はいずれもinconclusive、readerは`latest_chunk_saved_bytes_bound`かつ観測→score再導出true。全体216.656秒/764標本、private最大432,431,104 B、OS peak pagefile 449,949,696 B。別の独立raw走査で22 fileの完全在庫とreport内の18 payload pin・３制御pinに不一致0件を確認した。

[先行失敗result](../../artifacts/anomaly-v03-preformal-registered-attempt-hand-normal-probe-e2ddb044/result.json)は3,802 B / SHA256 `e41e0c66feb8ba421ea57082f1118b7afee160048f8c503356d6359dbb513bbd`。同じ純粋契約を通した後、最長266文字のWindows物理pathで`FileNotFoundError`となり、別readerは未実行。部分保存14 file/64,983,744 Bを保持した。成功rootの最長pathは245文字であり、当時は次の所有生成子に対象rootと全出力pathの起動前照合を課した。この２試行は**単一Python process**内で生成・読取りを行った実現性確認であり、全工程inline scriptは保存していない。当時未確認だった版付き再現手順、所有子exit/reap、起動前外部出力pinは次節の試行で確認した。全source/runtime閉包と正式同形の共通予算は残る。`registered_seed_consumed=false`、実登録観測の読取りfalse、正式credit 0、S4/S5/S6未開始を維持する。

### 所有生成子→別reader子の架空登録形式native試行

clean `6ad2631c27f39720a461ad203fc5de7b86e81e5a` に[所有生成子](../../src/banto_ai/anomaly_v03_preformal_owned_generated_attempt.py)と[prepare/run入口](../../tools/preformal_owned_generated_trial.py)を保存した。`prepare`は対象rootに書かず、同じ固定レシピから22出力bytesを親processでも先行計算し、[別rootの外部pinset](../../artifacts/anomaly-v03-preformal-generated-pinsets-g01/pins.json)へ起動前に固定する。manifestは69,701 B / SHA256 `d00d9ac900f2ddcf38a6b4534c3bd8d0b2f349801b79f598b77dc8c3b5a8dc11`で、同値のsidecarと呼出者指定SHAを`run`が照合した。これはレシピ再現用の事前期待値であり、独立した実観測oracleではない。子には完成した観測・評価bytesを渡さず、`-I -S -B`で固定５信号×18,000座標を再生成した。登録seedの`normal_stream`/`materialize_pair`は呼ばない。子は２層のdataset入力12 fileを物理保存・外部pinで再読取りし、そのreadbackを使って６評価を計算した。dataset関連のその他metadataを全て物理保存したという証拠ではない。

[native結果](../../artifacts/anomaly-v03-preformal-registered-attempt-g01/owned-generator/result.json)は10,528 B / SHA256 `fa479aa87b747ddb93f732b9aeb8c7bf65a3f446966910ae43184a6761716e38`。２子の間に親が全出力pin、最新attempt、生成子exit/reapを検査した。最終的にdataset入力12＋評価６＋保存制御４＝22 file / 131,144,119 Bを保持し、別reader子は最新attemptの６行と22 fileを読んで架空観測→profile/score→ledger→主/sliceを再導出した。生成子PID 29348、133.259秒、peak private 354,639,872 B、reader PID 19700、43.369秒、315,109,376 B。両子とも異なる開始token、exit 0/reap、invocationとstdout pin、source/runtime前後を確認した。役割別の上限は生成子360秒/768 MiB、reader300秒/1 GiBで、共通外側予算ではない。

[独立postcheck](../../artifacts/anomaly-v03-preformal-generated-pinsets-g01/postcheck-result.json)は1,527 B / SHA256 `e4e790b2567d6303b4af56c9849693a1798b0a8ea0ddd95675b839b8edc0033f`、[照合script](../../artifacts/anomaly-v03-preformal-generated-pinsets-g01/postcheck.py)は18,690 B / SHA256 `97d715aa0e4a8a39ad167e612986491a6e98196e65df3b40d70f2a2a57dcb06d`。manifest SHA/sidecar、物理22 fileの完全在庫・全raw pin、選択18 sourceの作業raw/Git、generator/materializerの２ raw snapshot、２子のPID/開始token/exit/reap/監督・応答、reader意味欄を別手順で照合し、不一致0。関連回帰は28件実行、27件pass・従来のopt-in native１件skip、repository safetyもpass。実登録観測生成・読取りと正式creditは0、S4未採択・S5/S6未開始。`source_closure_complete=false`、`runtime_closure_complete=false`、`execution_authenticated=false`を維持する。

### 同じ架空生成２役の共通外側予算 native 試行

clean `3be274c59ce4ffa0b5b60ba42993e2aa44a57039` に[２役専用の外側監視](../../src/banto_ai/anomaly_v03_preformal_generated_chain_budget.py)と[run-budget入口](../../tools/preformal_owned_generated_trial.py)を保存した。新root `g02` の起動前に、対象root外で同じ固定レシピの[外部pinset](../../artifacts/anomaly-v03-preformal-generated-pinsets-g02/pins.json)を準備した（72,149 B / SHA256 `22ee6888d731c827162b09ef1332cb61fe6a5542372e3e499ea0088fd214f1ef`）。sidecarと呼出者指定SHAを起動前に照合した。この準備時間・別rootの容量は今回の予算に含まない。pinは事前期待値で、実登録観測の独立oracleではない。登録seedの`normal_stream(seed)`と`materialize_pair`は呼ばず、固定手作り系列の６架空評価だけを生成した。

[最上位結果](../../artifacts/anomaly-v03-preformal-registered-attempt-g02/budgeted-result.json)は1,654 B / SHA256 `d1a8c738e61fd0ad48d99675ca12cb2aea937152bafca29a543398061e9ceda7`、[内側２役結果](../../artifacts/anomaly-v03-preformal-registered-attempt-g02/owned-generator/result.json)は10,528 B / SHA256 `354c8ae043486c8f5ee2a99780ea5ee5a9395ed92daaca790187e8e9ab7c1179`。[共有予算receipt](../../artifacts/anomaly-v03-preformal-registered-attempt-g02/resource-budget.json)は3,618 B / SHA256 `c1dd3e838930cd318ee8c51634d7d54faaacfcae7d70d3065f8e15a3878a72a2`、184.919秒・709標本でpass。600秒wall、親512 MiB、対象root192 MiB/256 entries/depth12、最低commit/RAM各2 GiB・空きdisk5 GiBの標本・協調停止であり、OSのhard quotaではない。最大標本rootは131,337,566 B/48 entries/depth10、親peak private50,749,440 B、最低commit余裕17,660,342,272 B、最低RAM空き15,535,783,936 B、最低disk空き411,696,873,472 B。最終receipt２件を加えたrootは33 file/50 entries/131,342,838 B。対象外のpinset容量をこれらの数字へ足していない。

生成子PID 24516は136.148秒・peak private359,686,144 B、reader PID 29512は43.789秒・316,575,744 B。両者の開始tokenは別で、exit 0/回収、保存supervision・stdout・応答pinを最上位resultと突合した。生成子が物理保存・再読取りしたdataset入力12 fileと評価６・制御４の計22 file/131,144,119 Bは外部pinと一致し、別readerは最新attemptの６評価を観測→profile/score→ledger→主/sliceまで再導出した。[独立postcheck](../../artifacts/anomaly-v03-preformal-generated-pinsets-g02/postcheck-result.json)は2,229 B / SHA256 `c96ff1fd3080d009989ce6e43eb52f448222e6bd9ac874f9de597b9da895712f`、[照合script](../../artifacts/anomaly-v03-preformal-generated-pinsets-g02/postcheck.py)は28,481 B / SHA256 `2652f5d99e2ca222c88e164e714a8ede4186fb50ca21b854969a54d8d5d7fff0`。全22 raw pinと完全在庫、選択20 sourceの作業raw/Git、２ raw snapshot、各子の監督記録、予算標本/最終ツリーに不一致0。関連回帰は58件中57件pass・従来のopt-in native１件skip、repository safetyはpass。

この予算のscopeは`invented-generated-two-role-only`。登録形式readerの１区間６評価を40架空cluster/50,000 drawの入力へつなぐ導出・pin契約はなく、全表/文書・完全別監査・stage/writer・公開後readerも今回の監視外である。`full_end_to_end_budget_measured=false`、`formal_50000_draw_budget_measured=false`、`formal_permission=false`、正式credit 0を維持する。全source/runtime閉包と実行identity認証も未採択のまま。

### 共通外側予算への接続順

g01は生成子とreaderに個別の停止上限を設けた試行だった。g02ではこの２役に１つの外側予算を通したが、準備工程・後続の40 cluster/50,000 draw・全文書・完全別監査・公開までの共通測定にはまだ届かない。g02の131,144,119 Bの出力は監視対象rootに含め、別rootの起動前pinset準備は明示的に除外した。正式同形の全工程では外部入力の準備範囲と容量を受入契約で固定する。

現行[５役予算](../../src/banto_ai/anomaly_v03_preformal_chain_budget.py)は５役・240秒・48 MiBに限定され、保存形式２役のコピー前入力と出力はそれぞれ126,317,406 B（約120.5 MiB）ある。[保存形式２役](../../src/banto_ai/anomaly_v03_preformal_owned_saved_attempt.py)、[５役](../../src/banto_ai/anomaly_v03_platform_five_role_fixture.py)、[50,000 draw接続](../../src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py)は別々のrootと外側監視を所有する。[下位予算の祖先接続](../../src/banto_ai/_anomaly_v03_fixture_budget.py)と今回の２役probeを利用できても、現公開入口を直列に呼ぶだけでは同一予算・同一入力系譜にならない。全工程用の版付き外側監視と各工程のcaller所有target/budget入口を作り、子監督へ停止probeを伝え、終了・回収後だけ次工程を起動する。

登録形式readerの６架空評価だけでは40 clusterを作れない。別の架空40 cluster入力から保存済み50,000 drawの主９表を文書草稿へ写す限定試験はできたが、正式同形の全工程接続には架空2,880行から40 clusterを導出するpin契約が要る。slice/sidecarを含む全文書、完全な別実装監査、stage→writer→別readerも必要である。現行[文書fixture](../../src/banto_ai/anomaly_v03_document_fixture.py)の最大64 drawや保存済み算術結果の写像を、正式同形の50,000 draw全文書・完全S6へ読み替えない。共通監視開始→架空生成→別reader→全表/文書→別監査→公開/読戻しの順に新rootで失敗・未回収・容量超過を含めて測り、監視終了後に全体receiptを固定する。

## データ別の次の作業境界

| データ・時点 | 許される次の作業と完了証拠 | この段階の境界 |
| --- | --- | --- |
| 固定した架空入力、S4採択前 | 登録形式の１区間は所有生成子のexit/reap、外部pin、最新attempt、別readerでの観測→profile/score→ledger→主/slice照合まで完了し、この２役を１つの外側予算でも測った。この６評価から40 clusterは導出できない。別の架空40 clusterの保存済み50,000 drawから主９表の十項目文書草稿までを限定照合した。次はslice/sidecar・完全文書監査・公開を接続する。正式同形の全工程には架空2,880行から40 clusterを導出するpin契約が別途必要 | 架空identityや登録seedの文字列を使っても、登録holdoutの観測値は生成・読取りしない。架空試験は性能証拠ではない |
| 保存済み合成dev/smoke、S4採択前 | 既存120区間・720評価と旧独立監査、全件engineering報告は参照証拠として保持する。必要な境界だけ外部pin付きで再確認し、元attemptを上書きしない | 今回の現行reader再確認は区間0と119の各６評価だけ。他の118区間のrawを今回再監査しておらず、旧データを新revisionのnative受入や正式holdoutへ付け替えない |
| S4の最終dev/smoke | S1登録済みdev 8 seed・smoke 2 seedの全12 layout×２層×３候補を、改訂済み契約・最終clean revision・採択したWindows tupleで新rootに実行し、全在庫、独立再監査、CI/nativeを同じ受入記録へ結ぶ。smoke全artifact実測から正式同形のproducer+analysis+audit+staging必要量を見積り、式・実測bytes・予想時間を保存し、正式開始時の対象volume空きが見積りの２倍以上と確認する | 受入に失敗したらS5を開かない。科学条件・seed数・予算を途中で緩めない |
| S4採択後のS5/S6 | 未使用holdout 40 seedの480区間・960 dataset・2,880評価を登録順で一回実行し、次段階でread-only独立再計算、50,000 draw、全gate・選択・別readerを照合する | 途中性能で停止・修正・seed追加をしない。S5成功結果をS4開始前の前提にしない。実設備・顧客データは本計画の対象外 |

`formal_permission=false`、`promotion_allowed=false`、`independent_s6_complete=false`、`selected_candidate=null`を維持する。本書は受入範囲と次の実データ作業を限定する記録であり、正式評価の開始許可ではない。
