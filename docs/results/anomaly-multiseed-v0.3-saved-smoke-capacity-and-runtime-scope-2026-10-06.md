# v0.3 保存smokeの容量照合と実行在庫の残件（2026-10-06）

**保存済み合成smoke 24区間の全attemptと共有controlを実bytes/hashで照合した。確認できた部分を正式480区間へ20倍換算すると62.21 GiB、2倍の空き条件は124.42 GiB。D側の観測空き329.67 GiBはこの部分を満たす。正式analysis・追加audit・staging・診断予約は未測定であり、正式容量検査の合格ではない。**

source読取り保存点はclean `7aa9bdd539178e82f72b3e76225ec72c25175b19`。新評価、bootstrap、業務worker、追加agentは0。登録holdoutの観測payloadは読んでいない。正式gate `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0を維持する。

## 照合対象と数え方

外部起点は旧dev8/smoke2の完走保存点8,366 B / SHA256 `ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d`。そこからevidence 2,197,895 B / `18a6749c9a168af3088d9f2729f9ab7a06af45faf7910863f648c6f018268dad`、plan、全保存pinをたどった。旧rootは `C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1`。読取りは区間96–119のsmoke全attempt、旧campaign共有control、過去独立監査の同24区間報告に限定した。devの観測・評価payloadは対象外。

2 smoke seeds、各12 layouts、両層・3候補、計48 datasets /144評価のidentityをplan・最新journal・manifestへ結んだ。区間119はattempt2を採用し、失敗attempt1の133,130,961 Bも容量へ残した。最新24成功attemptは3,193,004,797 B。producer・既存ledger auditの保存終了receiptは全24区間exit0・終了確認済み。新たなprofile/score/ledgerや生成式の再計算は行っていない。

| 既存証拠の内訳 | file数 | 論理bytes |
| --- | ---: | ---: |
| smoke全attempt（生成payload・ledger audit・失敗・marker等） | 1,294 | 3,326,135,758 |
| campaign共有control全量 | 1,514 | 12,403,192 |
| 過去の独立profile/score/ledger監査のsmoke報告 | 24 | 1,222,314 |
| 過去の独立生成監査のsmoke報告 | 24 | 137,996 |
| **今回数えた部分** | **2,856** | **3,339,899,260** |

共有controlは旧dev8/smoke2全体分をsmoke側へ全量割当てて20倍する保守的な数え方。別監査の共有記録、新保存readerの全成果物、正式analysis・公開root等はこの合計に含めていない。通常fileの論理pathごとに加算し、48 hardlink pathも個別に数えた。alternate streams・物理割当量・将来の同時staging peakは未測定。

collectorは1 MiBのstreaming hash、180秒・入力4 GiB・5,000 file・各出力4 MiBの上限で12.025秒。2,862 unique入力file（上表と外部起点・科学pin）を照合し、postflightで全identity/size/mtime/ctime/link countとsmoke treeの欠落・追加を再確認した。科学計画・registryの既存pinは一致した。

## 部分容量と時間の換算

`480/24 = 960/48 = 2880/144 = 20` による換算のみ。未使用holdoutを生成・読取りして規模を確認した結果ではない。

| 項目 | 値 |
| --- | ---: |
| 確認済み部分の正式同形換算 | 66,797,985,200 B（62.210 GiB） |
| 上記の2倍 | 133,595,970,400 B（124.421 GiB） |
| D側空き（読取り前・後） | 353,984,253,952 B（329.674 GiB） |
| C側空き（読取り後） | 134,158,106,624 B（124.944 GiB） |
| 正式analysis・追加audit・staging・診断予約 | **未測定 / null** |
| 正式全工程見積り・正式2倍必要量 | **未確定 / null** |

D側は確認済み部分の2倍を両境界で満たす。C側は部分条件との差が約0.52 GiBしかなく、未測定分を含む全工程容量の根拠にできない。正式開始時は選択した全root/volumeで、採択された全工程見積りと実空きを再照合する。

過去の選択成功attemptに記録された時間の20倍はproducer **81.833時間**、既存ledger audit **13.492時間**、独立profile/score監査 **1.282時間**、独立生成監査 **0.123時間**。これは工程別receiptの外挿であり、外側wall clockではない。failed attempt、親の再照合・待機・monitor・準備・正式analysis/公開時間を含まず、正式予算や完了予想に採択しない。旧runtimeは全smokeで25H2/build26200/UBR9457、Python3.14.0に一致し、現26H2での最終smoke実測へ読み替えない。

## 保存検査と失敗保全

新rootは [a2](../../artifacts/preformal-smoke-capacity-20261006-a2/)。別stdlib checkerは2,856 descriptorを外部起点のpinへ照合し、欠落・重複、attempt別bytes、20倍・2倍、未測定null、正式flagを再検算してpass。checkerは3.3 GBを再hashせず、数値計算・役割再実行・S6も行っていない。

| 保存file | bytes | SHA256 |
| --- | ---: | --- |
| [collector](../../artifacts/preformal-smoke-capacity-20261006-a2/collect.py) | 16,310 | `29468c1432344eaf91cc31557bb95113e0ed98ac44ffc0cef97b6e742b77d08f` |
| [result](../../artifacts/preformal-smoke-capacity-20261006-a2/result.json) | 3,698 | `6ea687c59d53e3804ce8085644c1ebfdeb81c847fe19bbb7cb8bca8f72d20d82` |
| [inventory](../../artifacts/preformal-smoke-capacity-20261006-a2/inventory.json) | 869,697 | `68e6c31b3f8b7d4f71088ae8a0291475d623c46494b3208c267f3d20e761b54d` |
| [saved checker](../../artifacts/preformal-smoke-capacity-20261006-a2/check.json) | 1,787 | `91144454e556ac94a15e5a676b8b308660b491972fd34d62518abe4cf89ccc6f` |
| [runtime scope review](../../artifacts/preformal-smoke-capacity-20261006-a2/runtime-scope-review.json) | 17,926 | `48be345590a06504f79d922657599625c62113625bbed0efd815c28d13ef3504` |

初回[a1](../../artifacts/preformal-smoke-capacity-20261006-a1/)は`.complete`をnlink1に限定したcollectorの仮定により0.5秒以内に停止した。`.complete`と`marker-pending.json`は既存の同一inode/nlink2で、同一bytesを持つ。a1のscript・failureを保持し、a2ではreadonly計測としてnlink≥1と前後identity/links一致を要求した。失敗receipt278 B / `49c1fcd3d5e95d2d9753bfa33d4796a01799ce7971655a5d5bab41914ff4a071`。旧source、marker、失敗attemptは変更していない。この観測はhardlink別主体への改変防止を証明しない。

## source/runtimeの具体的な残り

[共通予算e04](anomaly-multiseed-v0.3-generation-publication-success-native-2026-10-06.md)の57 selected sourceは全て今回のworking bytesと一致し、元のbefore/afterも一致した。7役の保存supervisionとreportを再読して7 distinct PID・exit0・終了を確認した。実測HEADは`02d567f`、今回のsource review HEADは`7aa9bdd`。5役に`process`欄があり、analysis/auditにはない。受入契約で十分な元handle/identity証拠を確定し、存在しない任意receipt欄を自己判断で追加必須にしない。

| 実際の接続箇所 | 再利用できるもの | 残る結合 |
| --- | --- | --- |
| producer / 初期reader：`anomaly_v03_preformal_owned_generated_attempt.worker_main`、保存reader：`anomaly_v03_preformal_saved_row_reread.reader_worker_main` | selected Git/raw source、runtime tuple、元processの保存receipt、入出力pin | 正式登録経路での役割別期待source/runtime pinと実ロード在庫・境界照合 |
| analysis / audit：`anomaly_v03_preformal_bound_draw_bridge._child` | 固定40 cluster /50,000 draw、別算術、親supervision | child内の実source/runtime在庫、外部期待値・元process identityへの結合。現_childに全runtime collectorはない |
| writer / fresh reader：`anomaly_v03_saved_row_document_publication.worker_main` / `_perform` | retained raw・count意味照合、非上書き、終了後別reader、5 payload | 実際の両worker境界で期待runtime/loaded在庫を照合し、保証Aの契約・独立受入へ結ぶ |
| 在庫helper | `_anomaly_v03_inventory.capture_sources/stdlib_paths/native_paths`、`anomaly_v03_engineering_inventory.collect`、`_anomaly_v03_reader_dependencies.collect/verify_pair` | 前者のinspection snapshotと後者のloaded snapshotを実役割へ結ぶ。単独inspectionや過去prototype profileをe04の全在庫に代用しない |

stdlib全disk在庫、実ロード拡張/DLL/CRT、実行した外部program、clean sourceと実行前/中/後の境界、元handle終了・異常時子孫回収が対象。メモリ内codeの完全認証、全conhostの個別exit、利用しないprototype統合を追加必須にしない。今回新runtime collectorやworkerは起動せず、全在庫の合格flagも変更していない。

## 次の順序

1. この在庫helperを正式に使用する5役と追加readerの実境界へ接続し、外部期待pin・入力consumer・失敗拒否を固定入力で確認する。
2. 26H2・保証A/B・runner同定・root/schema・revision・identity・失敗/再登録と資源見積り方法を一つの改訂契約へまとめて独立受入に渡す。
3. 最終revisionのLinux/Windows・正式dev8/smoke2から全artifactとstaging peakを測り、今回の未測定欄を埋めて共通予算・容量2倍・独立受入を採択へ結ぶ。

長い共通全工程fixtureを自動反復しない。S4採択後に未使用holdout40 seedのS5、独立raw再導出のS6、結果文書のS7へ進む。
