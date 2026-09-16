# ローカル比較の判定差を時点・対象別に表示

2026-09-16 JST。実装savepoint **47f5367b64ef41ef0ef263dbcf0a628fcbd164a0**。
[使い方](../anomaly-v03-local-preview.md#判定差の詳細)。§116の通常権限・単一writer運用を継続。

## 変更と確認

`compare` に、判定または利用可否が異なるsample/targetの詳細を追加した。
UTC時刻、候補別の判定・スコア・残差・phase・mode/recipe・除外理由を表示する。
既定20組、`--details-limit` は0〜100、`--details-offset` で続きを指定できる。詳細はsample順・target名順で、全体の差の組数・表示数・前後の省略数を併記する。
同じ組が複数ペアで異なっても1組にまとめ、利用不能はunavailable/null/n/aで扱う。全体集計は表示範囲にかかわらず維持し、旧detailsなしJSONも描画できる。
保存API・計算式は変更せず、読み取り検証後の表示だけを拡張した。

**関連19件pass / failure・error・skip0 / 11.572秒**。3候補の重複集計防止、判定差と利用可否差、保存済み詳細値との一致、順序、ページ境界、0件/範囲外表示、不正上限、旧JSON、CLI出力を確認した。
独立レビューP0〜P3所見0・進捗poll0、repository safety/diff-check pass。重い評価moduleや専用principal試験は実行していない。

## 保存済み3候補の実CLI確認

前回のC0/C1/C2をそのまま再利用した。入力・候補payloadの新規生成は0。
通常Python 3.14.0のcompare PID25968、UTC00:42:56.153678〜00:43:10.371583、14.218秒、exit0。
前回比較の全体集計は全項目一致し、追加した詳細の数値・判定・除外理由も保存済みscores.jsonlと一致した。

| Sample / UTC | Target | C0 | C1 | C2 |
| --- | --- | --- | --- | --- |
| 7202 / 02:00:02 | motor-01.vibration_feature | 閾値以下 | 閾値以下 | 閾値超過 |
| 7203 / 02:00:03 | motor-01.motor_current | 閾値超過 | 閾値以下 | 閾値以下 |

日付は入力の2026-01-01 UTC。詳細は2組・全件表示、省略0。前回のペア別判定不一致1/2/1を、具体的な2組へ対応付けられた。
代数的な開発用入力の候補間差であり、正解に基づく性能順位や異常イベント数ではない。
公開表 `artifacts/local-comparison-details-2026-09-16/comparison-details.md` は4653 bytes/hash `7d65e23198da9fd6f9a884af3e079c6841aa738935d7dcb3e9e4f9695e5f04c4`。

## 保存・資源・再開点

選抜130 sourceのworkspace/Git blob一致（前回125不変・5変更）、前回公開artifact26件不変。選抜は完全な依存閉包ではない。
input-evidence22799 bytes/hash `fd26747971d304f0bc5b0dca4db0bd2f6545e8e1519fc32d0235314db1e2db16`。
最終manifest26948 bytes/hash `bffef1a360356453ce5ff4f1061aaecceaac2652063d8c1e922a4d44bf638b0a`。自身を除く8 artifacts/論理41857 bytes、manifest込み68805 bytes（約67KiB）。
終了後UTC00:44:16、空きRAM16581005312/C153473536000/D172064628736 bytes（D約160.2GiB）。このturnの開始時D173141708800との差全体を今回の生成物に帰属させず、長期リーク不在も断定しない。
OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00、Windows Update engineering緩和・正式pin不変。
本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は保全・commit除外。

**次は、判定差のある時点前後の保存済み観測値を併記し、入力と残差の対応を追える表示を検討する。** 既存3候補を再利用し、常駐処理や大きなデータ生成を追加しない。
専用principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。§116の保留、旧root閉鎖・jの消費済みguardを維持。
local_comparison_computed=true、今回のlocal publicationは0。formal_permissionと他のnative保証flagはfalse、acceptance_status=not_completed。正式campaign入口・科学的評価条件・受入gateは未変更。
