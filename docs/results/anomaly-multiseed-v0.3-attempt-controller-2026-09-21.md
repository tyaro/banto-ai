# 区切りproducer・単一writer実行管理・所有process監視

2026-09-21 JST。producer保存点 **8a38a134653d237c2cdbffdd1d6dbf59caa6f3e6**、controller/監視保存点 **bc5f18bb3347fe5f14e60b5381c98d63d5fa6072**。
[API仕様](../anomaly-v03-independent-audit-and-checkpoints.md#producer単一writer-controller所有process監視) / [短い引継ぎ](../current-handoff.md)。

## 今回できるようになったこと

全120区切りから選択した新形式6件へ、既存producerの逐次計算・公開・再計算を接続した。旧固定6件API/CLIは維持する。controllerは新attempt確保、producer保存、独立audit、fresh照合、journal確定を順番に扱い、失敗出力を残して別attemptへ進める。過去のverified descriptor hashは外部保持を必須とし、再起動後に証拠を再照合する。同じsessionで確認済みの区切りは繰り返し検算しない。

各遷移はintent/descriptor→実証拠検査→journal追記→receiptの順で排他的に保存する。確定後のreceipt喪失は、外部保存したintent hashを使って読取り回復できる。未確定intentは自動公開・再使用せず、部分出力とともに保持する。失敗記録自体が書けない場合も、元の資源停止・中断・実行例外を隠さない。

所有するWindows子process 1個の監視APIを追加した。時間・private bytes・stdout/stderr合計の上限で停止し、終了確認後に最終観測とhandle解放を行う。終了未確認時はログを読まず、元のprocessを例外に保持する。終了済みログのhash読取りも有界。子孫processの管理や、producer/audit専用監視形式への変換は次工程。

## 検証とレビュー

producer接続＋旧engineeringの選抜は **31件pass/20.300秒**。controller/store/監視の最終選抜は **41件pass/47.925秒、failure/error/skip0**。safety/diff-check pass。dev/smoke境界、再試行、判定保留、失敗後の保存、外部pin、確定後のreceipt回復、一次例外保持、資源停止・中断・終了不明・ログ上限を確認した。

小規模な実ファイルIOを使用し、controller側のsource/runtime/schema/数値処理は明示mock。監視試験はfake processに加えて、**printのみの実Windows子process 1個**を起動・終了確認した。Linuxはfake試験のdiscovery互換修正のみで、Linux上の実行結果を追加したものではない。登録dataset生成、実6件の再実演、全dev/smoke実行は行っていない。

独立レビューの一次例外保持の指摘を修正し、追加レビューで見つかった診断中のMemoryError、cleanup中断、終了未確認/過大ログ読取り、Linux discoveryの4点も修正した。限定再レビューの残存指摘0、進捗poll0。担当は読取りのみ。修正前の22件・38件の成功も途中記録として保持し、最終コードの根拠には41件を使う。初回22件はimportしたTestCase由来の既存13件を含んだため、module importへ直して不要な重複実行を解消した。

最終PID17900/exit0、peak private **57409536 bytes（54.75MiB）**。UTC **2026-09-21T11:21:01.302150+00:00** の試験終了観測で、空きRAM **13312098304** / C **174401413120** / D **119514165248 bytes（約111.3GiB）**。Windows **26200.9457** / CPython **3.14.0**、exe/DLL hashと試験前後runtime一致。bootの既存観測は2026-09-19T03:46:06.5+09:00。Windows Updateのengineering緩和と旧正式pin不変を維持する。短時間検証で長期リーク不在は未評価。

## 保全と次工程

ローカル証拠は `artifacts/attempt-controller-2026-09-21`。前回chunk-auditのmanifestと4証拠を照合する。本流 **889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e** / clean、既存dirtyの親policy結果書8461 bytes/SHA-256 **443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621** を保持し、commitから除外する。

次はproducer workerと独立audit CLIを監視/controllerへ結ぶadapter。全体予算・source/consumer freeze・runtime inventoryを整えてから実データ実行を判断する。現在のcontrollerは同期callbackを受け取るcoreで、campaign起動CLIはない。profile/score導出等の独立検算、全dev/smoke/holdout、性能評価は残件。

専用principal試験の保留、保護root参照禁止、j/診断guard消費済みを維持。principal/SAM/保護root参照、UAC/ACL変更、service/task追加、push/merge/CIなし。研究ロードマップPhase 3の実行接続を進めた段階で、Phase 2/3全体の完了は追加しない。budgets_frozen/execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false、campaign_evaluations_credited=0。
