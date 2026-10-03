# v0.3 正式評価前の役割profileと架空保存attempt検証（2026-10-04）

状態: **26H2向けの未採択preformal検証**。５役の初回code保存点は `09b4da2291634ee07ff1eacb74d3ca114c1d76b4`、保存済みproducer→50,000 draw算術接続の初回は `cca54e9e1083d92f4cdf85aae65fdef943929bcf`。writer事前再照合と所有materializerを含む再試行はclean `723eaf1d83ba2f1d42abee9dbe54d57da1d2959d`、別reader子のnative試行はclean `e79479077c7f55cf0398d0e5add41b989e9c936b`、５役/50,000 draw再試行はclean `94be9ed2702d2f383acb952ea1cf24b21b9754fc`。旧25H2正式gateは `s4_acceptance_not_frozen` のまま。登録holdout観測の生成・読取り、正式評価credit、S5/S6、候補昇格は0である。

## S4採択前の受入見取り図

| 受入事項 | 現在の確定範囲 | 採択前に要る証拠 |
| --- | --- | --- |
| 26H2運用契約・公開保証 | 未採択v2案。writer子の`.complete`前再照合と失敗保全は検証済み | 旧25H2条件との差、marker残存時の扱い、旧§8の保護DACL・独立token条件を保証A/Bのどちらで扱うか版付きで決定・再監査 |
| 登録形式の保存入力 | 外部pin付き架空22 fileを所有コピー子→別reader子で照合。６架空評価の観測導出は一致 | 固定架空入力を**生成する**所有producerから、最新attempt・完全在庫・別readerまで連続して実証。実登録観測はS5まで閉じる |
| 数値・文書・全工程予算 | ５役の架空１drawと、保存済みproducerからの50,000 draw２算術子は別々に成功 | producer→登録reader→全表/文書→完全別監査→stage/writer→別readerを共通外側予算で連続測定し、容量２倍条件を判定 |
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

## S4採択と実データ作業の残件

1. [運用契約26H2案v2](../anomaly-v03-formal-operations-contract-proposal-v2.md)と旧25H2計画との差、公開marker/失敗時保証、役割別完全source/runtime閉包、実行identityを版付きで受入れる。旧§8のprotected DACL・独立read-only token/AccessCheckは、保証Aを採るなら計画改訂・独立再監査で扱いを変更し、保証Bを採るなら26H2実機で再受入れる。今回の候補profile一致を完全閉包へ昇格しない。
2. 登録形式の実保存attemptについて、**固定した架空入力を生成する所有producer**の終了証拠・外部pinを今回のreaderへ渡し、全評価の観測導出、最新attempt/失敗保全、完全な条件別在庫を同じ入口で検証する。今回の一時fixtureは実producerの証拠ではない。
3. producer→登録reader→40 cluster/50,000 drawの全表・文書→別実装の完全監査→stage/writer→別readerを、最終clean revision・同一外側予算IDと監視下の工程別rootで測る。現在の５役は１draw、今回の50,000 draw接続は保存済みproducer countから２算術子のみで、時間やbytesを足して正式予算にしない。旧計画§9の空き容量２倍条件は最終smokeから判定する。
4. 対象revisionのLinux CI 3.12/3.14、Windows native、stdlib/repository回帰と独立再監査を照合する。既存CI workflowの定義は実行結果ではない。runner image digestの採取元は未確定。
5. 既存の保存済み合成dev/smoke 120区間・720評価はengineering参考証拠として保持する。上記をS4条件として確定後、S1登録済みdev 8 seed・smoke 2 seedを最終clean revision/26H2 exact tupleの新attempt/rootで全layout・両層・３候補について受入れる。未使用40 seed・480区間・2,880評価の登録holdoutはS4採択後のS5でのみ扱う。既存720評価をholdoutへ改名・加算しない。

### 次の限定実装単位：架空入力の所有生成

既存の22 fileコピー子は試験履歴として残し、別版のengineering専用生成子を新rootで作る。親が子起動前に固定レシピID、chunk 0/attempt 1、22**出力**fileの外部pin、選択source/rawとruntime候補を宣言する。子には完成した観測・評価bytesを渡さず、固定した手作り正常系列から２層のdatasetを組み立て、保存して読み戻したbytesから６候補の評価を計算する案を検証する。`materialize_pair`と`normal_stream(seed)`は呼ばず、登録seed由来の観測生成を閉じる。登録identityと予定eventは形式検査用のmarkerに限り、`invented_only=true`と正式credit 0を維持する。この案の生成bytes・容量・評価契約への適合は未測定である。

受入は、子のPID/開始token/終了・回収、source/runtime前後、保存４制御fileと18 payloadの完全在庫・全外部pin、最新attemptの選択を親が確認してから、現行の別所有readerで観測→profile/score→ledger→主/sliceを再導出すること。制御fileを親から供給する場合は入力pinと生成**出力**pinを区別し、receipt/report内のhash主張も生成物に結び直す。pin欠落・誤pin、レシピ変更、余分なfile、最新失敗attempt、子の時間超過、reader失敗を成功へ変えない焦点試験と、clean revisionの別root native１試行を要する。現行fixtureの架空source名を実際の生成・採点sourceの選択証拠へ改める一方、完全source/runtime閉包を証明した扱いにはしない。既存fixtureの総量126,317,406 Bは128 MiB上限に近いため、生成時の最大file、合計bytes、保持memoryを先に測る。

## データ別の次の作業境界

| データ・時点 | 許される次の作業と完了証拠 | この段階の境界 |
| --- | --- | --- |
| 固定した架空入力、S4採択前 | 登録形式の物理attemptを所有producerで保存し、そのexit/reap、外部pin、最新attempt、観測→profile/score→ledger→主/sliceを別readerで照合する。40架空clusterの50,000 drawから完全な表・文書・別実装監査・公開後読戻しまでを工程別rootの共通予算で通す | 架空identityや登録seedの文字列を使っても、登録holdoutの観測値は生成・読取りしない。架空試験は性能証拠ではない |
| 保存済み合成dev/smoke、S4採択前 | 既存120区間・720評価と旧独立監査、全件engineering報告は参照証拠として保持する。必要な境界だけ外部pin付きで再確認し、元attemptを上書きしない | 今回の現行reader再確認は区間0と119の各６評価だけ。他の118区間のrawを今回再監査しておらず、旧データを新revisionのnative受入や正式holdoutへ付け替えない |
| S4の最終dev/smoke | S1登録済みdev 8 seed・smoke 2 seedの全12 layout×２層×３候補を、改訂済み契約・最終clean revision・採択したWindows tupleで新rootに実行し、全在庫、独立再監査、CI/nativeを同じ受入記録へ結ぶ。smoke全artifact実測から正式同形のproducer+analysis+audit+staging必要量を見積り、式・実測bytes・予想時間を保存し、正式開始時の対象volume空きが見積りの２倍以上と確認する | 受入に失敗したらS5を開かない。科学条件・seed数・予算を途中で緩めない |
| S4採択後のS5/S6 | 未使用holdout 40 seedの480区間・960 dataset・2,880評価を登録順で一回実行し、次段階でread-only独立再計算、50,000 draw、全gate・選択・別readerを照合する | 途中性能で停止・修正・seed追加をしない。S5成功結果をS4開始前の前提にしない。実設備・顧客データは本計画の対象外 |

`formal_permission=false`、`promotion_allowed=false`、`independent_s6_complete=false`、`selected_candidate=null`を維持する。本書は受入範囲と次の実データ作業を限定する記録であり、正式評価の開始許可ではない。
