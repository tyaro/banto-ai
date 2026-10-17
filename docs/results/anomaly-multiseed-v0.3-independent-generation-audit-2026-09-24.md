# v0.3 保存観測の正常生成・異常重畳・丸めの独立検算（2026-09-24）

全120区間・240データセットで、凍結済みの正常生成式、異常の重ね方、欠損処理、小数丸めから再構成した観測が保存bytesと完全に一致した。前回完了した全720評価のprofile/score/ledger検算とも、同じ入力hash・identity・attemptで結び付いた。

実装・実行revisionは `47dbc165f12fb1ce7608bb57625cb498bc4a4d04`。新しいproducer、追加attempt、holdout、検出器評価は起動していない。ただし今回の検算では、保存済みの登録seedを使って正常値をメモリ内で再構成している。seed計算0という意味ではない。再構成した観測を新しいデータセットとして保存せず、検出器の入力にも渡していない。

## 対象と結果

| 項目 | 結果 |
| --- | --- |
| 区間 / データセット | 120 / 240、重複・欠落なし |
| 内訳 | dev 96区間・192datasets、smoke 24区間・48datasets |
| 保存観測行 / signal cells | 4,320,000行 / 21,600,000 cells、全5 signalsを確認 |
| 欠損cells | 3,600、各quality-stressに30 |
| quality-mask行 | 4,320,000行 |
| 計画event / enabled event | 9,600 / 8,400件、両JSONLを別々に照合 |
| 正常値の再構成 | 120 pairs、既存10 seed、計2,160,000正常行。layoutごとの再構成を含む |
| 前回score検算への接続 | 全720評価、共通入力720 filesのhash/pin一致 |
| 今回の対象入力 | 1,081 files / 3,049,702,210 bytes（重複除外） |
| 所要時間 | 113.560209秒 |
| 保存 | 先頭1区間のpilot保存、6区間ごと19回の中間保存、全120区間の最終保存 |

区間119は監査済みattempt2を選び、失敗attempt1を保全したまま加算しない。input filesはplan、区間別の既存audit report、各datasetのobservations・quality-mask・event-ledger・eventsであり、外部保存点、過去score報告、source等の読取りは別。

## 独立性と検証方法

`anomaly_v03_generation_audit.py`は標準ライブラリだけをimportする。producerの物理式helper、materializer、丸め関数、event inventoryを呼ばず、計画§3.1〜3.3を別実装で検算する。正常式を固定した基準commit `026aa77fe96afd954957acb2fc7d0df9ee3cc938` と実計算sourceの `_base_values` はAST一致も確認した。

1. 外部SHA256を起点に完走保存点、evidence、登録plan、最終verified attempt、選んだ8入力ファイルのbytes/hashを認証する。
2. 単一の `random.Random(seed)` を設備順に使い、5回のGaussian draw順、各設備の初期温度24.0、未丸めの正常温度の引継ぎを復元する。
3. layoutごとのevent時刻・半開区間・最終cycleの重複を独立に作り、machine → sensor → ignored → qualityの順に適用する。stuck値は未丸めで保持し、最終的に全5信号へ一度だけbuiltin roundを適用する。
4. timestamp、設備、mode、recipe、units、値、qualityを含むcanonical UTF-8 JSONLを一行ずつ保存bytesと厳密比較する。許容誤差を設けず、符号付きzero、LF、JSONの数値型や書式も比較する。quality-maskと計画/有効eventも比較する。
5. 前回全720評価の外部pin付き報告を読み、同じ区間・attempt・identityと、各pairの観測/mask/event-ledger計6filesのpin一致を確認する。profile/score/ledgerは再計算しない。

PythonのRandom/gauss、binary64、builtin round、JSON実装は計画で指定された共有primitiveであり、これらの内部アルゴリズムを独立実装したという主張ではない。今回のPython executable/DLL、random.py、moduleの実体をpinした。Windowsの組込み `_random` と `math` はPython DLLに結び付ける。歴史的な実行環境・publication・supervisionは完走保存点を前提とし、今回あらためて受入試験をしたとは扱わない。

保存bytesが規定の再構成と一致することを確認したのであり、過去processの未保存の内部stateを直接観測したわけではない。

## テストと実行上の修正

検算本体・IOの22項目が通過。scripted Gaussianの手計算、設備切替時の温度resetと単一PRNG、全layoutのevent式、overlay順序・clamp・未丸めstuck capture、ties-to-even/signed zero、mask前の不正値、改変した両層と更新hashの拒否、末尾行・CRLF・欠落、外部anchor/attempt/容量上限、CLI失敗を確認した。完全な対照fixtureの乱数seedは未登録の123456のみ。登録seedでのデータ生成をCIへ追加していない。

実行補助6項目も通過。過去報告との接続、attempt/identity/hash取り違え、検証段階/件数/正式許可の偽装、資源下限、UTF-8読取り、Windows組込みmoduleの記録を確認した。

検算前の準備で2回停止した。1回目はgit showのUTF-8をcp932でdecodeしたため、2回目は組込み `_random` に `__file__` がないため。どちらもdataset読取り・seed再構成に入る前で、評価の不一致ではない。原runner/logはOUT直下と`verified-final/`に残し、修正後の成功結果は`verified/`へ別保存した。検算本体の実装変更は不要だった。

## 資源と保存点

処理processのpeak privateは57.41MiB、pair処理後privateは初回29.96MiB、最後32.38MiB、最大33.26MiB。最小空きRAMは14.57GiB、commit余裕は14.84GiB。終了時C/D空きは136.81/315.18GiB。120区間の境界で資源を記録した。新OUTは文書作成前に約2.75MBで、Cドライブ上に保存している。PC全体の容量変動原因や継続的リーク不在は断定しない。

OUTは `artifacts/independent-generation-audit-2026-09-24`。`verified/chunk-000.json`〜`chunk-119.json`、各checkpoint、summary、resourcesを保存。最終文書revisionとファイルpinはOUT直下の`savepoint-evidence.json`に記録する。元データ、過去検算、実計算source、本流、保護対象の既存dirty文書は変更していない。banto-24はPAUSEDを維持。

外部起点は完走保存点 `ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d`、全score検算保存点 `b591663d8026e348b81e427da8a169702625b160a1352cd7e7e2c07c6e43e9c9`、区間0の接続検算保存点 `5a79114f8af267688e942b52763ad0d70b5cb8c55b650b3a1dcdf91ffe94d089`。

## 次の範囲

保存済みdev/smokeでは、正常生成 → overlay/丸め → profile/score → ledger/指標が全240datasets/720評価で結び付いた。既存のC1/C2比較値は変わらない。

次はbootstrap・信頼区間・候補比較の独立実装と手計算fixtureの検証範囲を整理する。凍結計画の正式bootstrapは40 holdout seed・50,000 replicatesを前提とするため、今回のdev/smoke 10 seedを代入して正式CIや採択判定を出さない。holdoutを開かず、まず生成不要の契約・集計検算を進める。

`normal_generation_verified`、`pre_rounding_overlay_verified`、`rounding_verified`は全240datasetsでtrue。完全S6、正式許可、採択許可はfalse、campaign加算0、performanceはnot_evaluatedを維持する。runtime/単一writer運用受入も残り、Phase 2/3全体を完了扱いしない。

指定1区間の読取りCLIは `tools/evaluator/audit_anomaly_v03_generation.py`。必須引数は `--savepoint`、`--savepoint-sha256`、`--run-root`、`--chunk-index`。今回の入力は検証済みなので、理由なく再実行せず保存報告を利用する。
