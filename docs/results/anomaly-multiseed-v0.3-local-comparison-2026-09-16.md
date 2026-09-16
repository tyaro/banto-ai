# 保存済み候補のローカル比較

2026-09-16 JST。§116の単一writer運用を継続し、保存済みスコアの比較・表示へ進めた。
実装savepoint **204e8e8e9397e3276441a682a3283ff78bf3a0a8**。
[使い方](../anomaly-v03-local-preview.md#保存済み候補の比較)。

## 変更したこと

`preview_anomaly_v03.py compare` に、保存先とmarker hashの組を `--result` で2〜3組渡す。
各候補を順番に再計算検証し、同一入力の異なる候補だけをMarkdown/JSONで比較表示する。
既存の保存API・数式は変更せず、比較中は結果を書き換えない。入力・候補重複・score keyの不一致や内容検証失敗では結果を表示しない。

候補別/target別の件数、normal-prefix不足、除外タグを表示する。
判定一致/不一致は両候補で利用可能な行だけを数え、片側のみ利用可能・両側不能は分ける。
部分入力はinconclusiveのまま表示し、候補固有の生スコアを大小で順位付けしない。

## 検証

新規比較7件＋既存preview8件＝**15件pass / failure・error・skip0 / 6.929秒**。
部分入力、全availability組合せ、2/3候補の表示順、入力相違、重複候補、不正marker、内容変更、CLIのMarkdown/JSONと失敗出力を確認した。
初回新規7件はテスト側の引数切出しが余分な `--result` を残して1 errorとなり、切出し修正後に上記15件を完走。初回をpassには数えない。
独立レビューは読み取りのみでP0〜P3所見0、進捗poll0。repository safety/diff-check pass。広い評価moduleや専用principal試験は実施していない。

## 実CLIの比較

前回のC0結果と保存済み入力（14,410行・7,664,634 bytes）を再利用し、同じ入力からC1・C2を新しい実行名へ順次保存した。
入力SHA256 `e104d67861c37870af170a3e74aed987f3ba402a04181cf80af9cf1bf252dbc0`。
代数的fixtureのmotor-01/sample7202に一時的な加算を行った開発用入力であり、実設備データや性能評価ではない。
公開成果物は `artifacts/local-comparison-2026-09-16`。比較JSONから同じrendererで `comparison.md` を保存した。

| CLI | PID | 時間 | 終了 |
| --- | ---: | ---: | --- |
| C1 run | 31080 | 16.569秒 | exit0 |
| C2 run | 18640 | 24.510秒 | exit0 |
| 3候補 compare | 16436 | 20.037秒 | exit0 |

UTC00:05:18〜00:06:19に順次実行し、3候補すべてcomputed・48/48 profiles calibrated・40 score行（利用可能32/不能8）。
瞬間的な閾値超過はC0=2、C1=1、C2=2。共通32行の判定不一致はC0–C1=1、C0–C2=2、C1–C2=1。
両側不能8行は一致件数に含めず、片側のみ利用可能は各ペア0行。C2はmotor_currentのほかmotor-01.vibration_featureにも超過が1行あり、単なる超過総数の一致では判定内容の一致にならないことを表で確認できた。
これらは候補間の判定差であり、正解ラベルに基づく優劣・異常イベント数・検出性能を表さない。
比較表3193 bytes / SHA256 `989ec54ad6b9b64416cbf93081fc074ddc101843abba28e1fec8fc11e5b20ec2`。

## 保存と再開点

選抜130 sourceのworkspace/Git blob一致。前回128のうち125不変、preview/guide/READMEの3変更、新規選抜2。選抜は完全な依存閉包ではない。前回公開artifact18件不変。
input-evidence22866 bytes / SHA256 `cb5e5c788162053bd1616c5129fbb9962895afab460482de5162f3800857d718`。
最終manifest38826 bytes / SHA256 `3ea72ca950f2aa67d161b2a03c26e566f3a1018c26f2ea6985e620adf8024487`。
自身を除く26 artifacts / 論理15,437,207 bytes（約14.7MiB）。前回の入力原本・C0出力は複製せず再利用した。
実行後UTC00:06:44、空きRAM12,520,452,096 / C154,338,992,128 / D197,797,593,088 bytes（D約184.2GiB）。
OS26200.9445、bootは **2026-09-16T08:46:30.5000000+09:00** に変わっているため記録。再起動理由は未確認。Windows Update engineering緩和・正式pin不変。
PC全体の容量変動をこの処理だけの影響とせず、短い実行から長期リーク不在は判定しない。

本流889cfc3/cleanを維持し、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は保全・commit除外。
専用principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。§116の保留と旧root閉鎖・jの消費済みguardを維持する。
local_publication_performed/local_comparison_computed=true。formal_permissionおよび他のnative保証flagはfalse、acceptance_status=not_completed。正式campaign入口・科学的評価条件・受入gateは未変更。

**次は、比較で判定が分かれたsample/targetを具体的に追える表示を検討する。** 既存の保存済み観測・スコアを使い、性能順位やイベント数へ読み替えない。保存APIや厳密な分離試験の作り直しは不要。対象試験を絞り、常駐処理や大きなデータ生成を追加しない。
