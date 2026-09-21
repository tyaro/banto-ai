# 新形式の区切り結果と実ファイル・監視・journalの接続

2026-09-21 JST。実装savepoint **04630e436d7b99a97005944fe7cf7b8ec4687701**。
[仕様とCLI](../anomaly-v03-independent-audit-and-checkpoints.md#新形式の区切りを実ファイルから検算する) / [再開用引継ぎ](../current-handoff.md)。

## 到達範囲

`audit_anomaly_v03_chunk.py` を追加し、外部plan hash・chunk/attempt指定から新形式の保存済み6件を読み、公開inventory、producer監視、clean source、runtime、保存score以降のledgerを照合できるようにした。publication名と監視位置を固定し、planは1MiB、payloadは512 files/1 file32MiB/合計256MiB以内。読取り後にplan/source/監視を再照合する。

`checkpoint_anomaly_v03.py attempt-chunk-audit` は、最新のverified宣言を選び、固定位置のdescriptorと実証拠を読み、上記の新検算をjournal outcome・保存audit・監視と照合する。全120区切りから対象を選べる。旧 `attempt-audit` は旧形式のchunk 0専用を維持し、新旧を自動変換しない。

producer監視は新format、manifestと同じbinding、全workerの資源観測、正常終了、runtime/runtime_after一致が必須。audit監視は保存reportのraw hash/サイズ、正常終了、stderr空、600秒/1GiB/8MiB以内の上限・実測、専用CLIのexact argvとruntime_before/afterを必須にする。argvにはplan絶対path/hash、chunk/attempt、marker/producer監視hash、保存時consumer/producerを含める。過去consumerと今回verifierのsource/runtimeは別々に保持する。

共通IOと証拠本文照合だけを内部関数へ抽出し、旧public APIの契約は維持した。成功時の新statusは `attempt_chunk_ledgers_verified`、evidence_body_bindings_verified/saved_ledgers_revalidated/source_checkouts_verified=true、evaluations_checked=6。budgets_frozen/execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false、campaign加算0。

## 検証

新規12件は初回pass/56.731秒。単独readerにも既存のpayload件数/サイズ上限を適用し、source capture前の拒否テストを追加。最終は新規13＋chunk契約14＋旧saved-audit6＋attempt-files16＋checkpoint-evidence12＝**61件pass、failure/error/skip0**。safety/diff-check pass。

小規模な実ファイルを公開し、dev/smoke境界（0/95/96/119）、再試行、判定保留、plan/試行/monitor argvの取り違え、監視失敗・上限、runtime変化、保存結果の不一致、読取り中・読取り後の変更、CLI入口と終了時journal再照合を確認した。**source capture/runtime/schema/数値処理は明示したmock**。ファイルの公開・hash・inventory・本文結合を実際に通す検査で、登録dataset生成や実6件の数値再計算成功を追加したものではない。CLIはテスト内で入口関数を呼び、別processの実データ実演は繰り返していない。

独立レビューは差分読取りのみ、P0〜P3所見0/進捗poll0。レビュー後の単独reader入力上限追加1行とそのテストは親側で確認し、最終61件に含めた。広い重い数値moduleや専用principal/同時writer試験は実行していない。

最終PID30140/exit0、**80.642秒、peak private60731392 bytes（57.92MiB）**。UTC2026-09-21T10:21:18.662914の終了観測で空きRAM **13440172032** / C **170884177920** / D **119514456064 bytes（D約111.3GiB）**。D空きは着手時と同値。Windows **26200.9457** / boot **2026-09-19T03:46:06.5+09:00** / CPython **3.14.0**、exe/DLL hashと試験前後runtime一致。Windows Update engineering緩和を適用し、正式pin不変。短時間の終了観測で長期リーク不在は未評価。

## 保全と次工程

本流 **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** はclean。既存dirtyの親policy結果書8461 bytes/SHA-256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621** は変更せずcommitから除外した。前回chunk-contract証拠7 filesは全pin一致。今回のログ/runtime/resource/review/最終保全manifestは候補内 `artifacts/chunk-audit-2026-09-21` に保存する。

次は、1区切りのproducer実行→保存→独立audit→終了監視→journal確定を結ぶ単一writer controllerと、失敗attemptを残して次の試行へ進む処理を実装する。まず小規模fixtureで接続し、全体予算・producer/consumer freeze・runtime inventoryを整えてから実データ実行を判断する。profile/score導出の独立検算、全dev/smoke/holdout、性能評価は残件。今回の読取りCLIは監視processを起動せず、controllerの実行・再開許可も与えない。

§116の専用principal試験保留、保護root参照禁止、j/診断guard消費済みを維持。principal/SAM/保護root参照、UAC/ACL変更、service/task追加、新worktree、push/merge/CIなし。本件は研究ロードマップPhase 3の全条件実行に向けた読取り側接続の完了であり、Phase 2/3全体の完了を追加したものではない。
