# v0.3 実analysis/auditへのruntime在庫接続（2026-10-06）

**clean `af3e7a598c5fe372a5cb9a5a96ddbcefe4f54f2e`で、実際の50,000 draw analysis/audit childに外部pin付き期待runtime在庫を接続した。両役の前後照合、元handle identity、exit0・回収、親の保存後disk照合がpass。従来e04の数値pinと一致し、共有予算214.717/900秒、別保存checkerもpass。**

これは架空40 clusterの2算術役に限定したengineering試行。producer・初期/保存reader・writer・fresh readerを含む全工程の新試行は行っていない。新評価0、登録holdoutの観測payload読取り0、追加agent0。正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、全source/runtime受入・独立S6未完了を維持する。

## 実装と期待値の結合

新 `anomaly_v03_role_runtime_observation.py` はrole/operation/root/full revision・外部raw pinを検証し、source bytes、stdlib全disk在庫、実ロードしたPython importとDLL/拡張を照合する。期待値はcallerが開始前に保持する候補profileで、acceptanceは`candidate-not-accepted`。in-memory code、途中のload/unload、外部programや正式campaignの認証を主張しない。

実入口 `anomaly_v03_preformal_bound_draw_bridge._child` / `_supervise` に任意の `inventory_profile_pin` を接続した。childは入力decode/検証後、実算術前後のexclusive sidecarを保存する。既存の40 cluster /50,000 draw、独立算術、子900秒/1 GiB/log256 KiBを変更していない。通常呼出しの数値処理と既存report形式を保持し、新CLI optionは`--child`でのみ受け付ける。

親はPopenの元handleからPID/creation time/start tokenを取り、childの両phase・stdout reportと一致を確認する。終了後はsource/stdlibとloaded fileの実disk bytesを外部期待値へ再照合する。失敗時にはbeforeとfailureを保存し、afterや成功reportを作らない。二次的な診断保存失敗で元の例外を置き換えない。

profileの準備は2役共有予算の外側15.813秒。実ロードproject source、算術入口、凍結科学config/schema/計画、CI workflowを合わせた**71 source**を親が各Git tree blobと実bytesで確認し、外部manifest pinに固定した。stdlibは**2,559 file /51,017,552 B**。native候補47 file、既存cache候補137 file。cacheが実際に使用された証明はない。

## native結果

| 項目 | analysis | 独立audit |
| --- | ---: | ---: |
| PID | 14172 | 36968 |
| owned child経過秒 | 67.707 | 127.653 |
| peak private bytes | 129,699,840 | 40,181,760 |
| 終了 | exit0・回収・identity一致 | exit0・回収・identity一致 |
| 前/後のloaded file数 | 324 /324 | 324 /324 |
| 前/後のmodule数 | 213 /213 | 213 /213 |
| 前/後のnative image数 | 47 /47 | 47 /47 |

loaded fileの内訳は各phaseでproject55、stdlib85、native39、extension8、cache候補137。全stdlib disk在庫2,559件とは別の数である。既存dependencyの消失・改変は0、未登録/改変したloaded fileは成功にしない。Windows11 Pro 26H2/build26300/UBR9457、CPython3.14.0の候補tupleを前後で照合した。正式契約採択の代用にはしない。

入力はe04公開結果37,804 B / SHA256 `b0379ab5f978d93ee4b3b5bd2352477fffbe2024bd4ea5ea593f5c54e3e4ee63`から結んだ算術input **155,386 B / `c4ff99b6b59a0668dc9f0716c02e88f188dc2e48bd98da085c6fdcb1ff8ddf6b`**。生成済み観測は今回再読していない。新たに実計算したcalculation 68,225 B / `5526fc0edad2739106e800171d79d4c5e72558d9b56ca9643d89a9455a7a2cd6`、audit 566 B / `23ac0cfed91dceccf4181d91d0c77aec35885da9f3388cc3446aee752b68cec2`は従来e04と一致した。

2役共有時計は**214.716956/900秒**、819 samples、parent peak107,106,304 B/512 MiB。最大root1,624,786 B/64 MiB、19/64 entries、depth0/4。commit最低余裕10,593,374,208 B、RAM最低10,503,299,072 B、disk最低354,013,880,320 B。資源stop・観測errorなし、両child・sampler終了。sampling/checkpoint監視で、OS hard quotaではない。時間はresource-budgetの`summary.wall_seconds`を使う。launcherのtop-level欄を仮定した`sampled_wall_seconds=null`は原記録のまま保全した。

## 試験・保存・失敗保全

焦点試験は2回で31件/25.236秒と39件/20.900秒、合計範囲は重複を除く60件。新規12件は外部pin/role/root/revision/scope不一致、source/stdlib drift、未登録DLL、処理途中失敗、処理後source変更、二次保存失敗、保存metadata/native pin改変、更新したstdout pinによる他processへの差替え、CLI誤用を拒否した。fixture試験をnative受入へ読み替えない。

rawは [a3](../../artifacts/preformal-role-runtime-20261006-a3/) と [準備helper/checker](../../artifacts/preformal-role-runtime-20261006-prep/) に保存。別stdlib checkerは71 sourceを再hashし、保存file pin、2役の元handle由来identity/token、4 phaseの外部profile/input/全stdlib概要とloaded在庫を再検算してpass。stdlib/DLLのraw再hashや50,000 drawの再実行はchecker自身では行っていない。

| raw | bytes | SHA256 |
| --- | ---: | --- |
| [result](../../artifacts/preformal-role-runtime-20261006-a3/result.json) | 2,641 | `1348bff21891c8f9e745198c1bf8964a0028ef33b08d629f0994632e61a4d2f7` |
| [source manifest](../../artifacts/preformal-role-runtime-20261006-a3/source-manifest.json) | 9,856 | `033f0a71f4056a3c81ab2ae1e04eb9fb4b08b3c3ad5bfb2f0ad92614eb69de22` |
| [resource-budget](../../artifacts/preformal-role-runtime-20261006-a3/resource-budget.json) | 3,328 | `6877191aa8d96d0b780dcf4bcf47357d344c7851233171b803811ca123f1f196` |
| [saved-check](../../artifacts/preformal-role-runtime-20261006-a3/saved-check.json) | 3,129 | `f23693a5734e61a3365a6ba73a1de0a01cc420851f625dc5e77c2dfe848d27c6` |
| [launcher](../../artifacts/preformal-role-runtime-20261006-prep/trial3.py) | 8,857 | `a4ee5f9d0356877a1869a638001610a5b13d8bb625f5c122cb64bcc2641feabd` |
| [checker](../../artifacts/preformal-role-runtime-20261006-prep/check.py) | 6,279 | `47be30070b55bbb4bb2942e76989bbdbad5b8893d376743525ab4848b877f588` |

初回[a1](../../artifacts/preformal-role-runtime-20261006-a1/)はfixture inputのpinを算術inputへ取り違えて準備停止。a2はrepo全`_source_path`を走査して旧 `examples/configs/anomaly-evaluation-v0.1.json` のGit/raw不一致を検出し準備停止。両方ともworker起動0、原result/launcherを保全した。a3ではsource範囲を実ロード依存・実入口・科学pinに明示して71件を固定した。旧v0.1設定の不一致自体は修理・消去していない。使うrole/source範囲の独立受入は残る。

## CIと残件

同code revisionの[Ubuntu CI37431372011](https://github.com/tyaro/banto-ai/actions/runs/37431372011)は、今回保存時には両minorのunittestが進行中。job IDは3.12=`112162773216`、3.14=`112162773409`。[小さい進行snapshot](../../artifacts/ci-diagnostic-37431372011/in-progress-snapshot.json)を保存した。全job成功・raw journal再検証は未確認で、過去CIを今回codeの結果に代用しない。

次は同CI完了の保存照合と、producer・初期/保存reader・writer/fresh readerの実境界に期待runtime在庫を接続し、共通外側予算へprofileを伝播する。今回の任意optionは既存全工程callerからまだ渡していない。profile wrapperそのものの採用を必須にせず、実経路での期待値・在庫・元handle・終了・異常時子孫回収を改訂契約へ結ぶ。外部Git/helperの実ロード在庫、正式入力consumer、契約・runner同定、最終dev8/smoke2・全容量2倍・独立受入は未了。e04の限定完走と旧smoke容量は保全し、全工程を自動反復しない。
