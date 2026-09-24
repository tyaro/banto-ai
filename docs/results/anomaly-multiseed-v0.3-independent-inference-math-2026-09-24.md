# v0.3 信頼区間・候補比較の独立計算層（2026-09-24）

信頼区間・候補比較を再計算する独立した算術を実装し、手計算例21試験と凍結済み全200万個の抽出番号で検証した。今回は計算部分の検証であり、実データの信頼区間、正式holdout評価、候補の採択は実施していない。

実装/実行revision: `4dd9795c347fc5d00a38c4dfb42379ffc1f8337d`。標準ライブラリのみの `src/banto_ai/anomaly_v03_inference_audit.py` と `tests/test_anomaly_v03_inference_audit.py` を追加した。既存v0.3のS1は報告されたCI・gateの整合性を検査するが、CIを独立に導出しない。新モジュールはproducer、registry、既存analysis数値helperをimportせず、凍結計画§6の算術を独立に計算する。

## 完了した範囲

| 項目 | 結果 |
| --- | --- |
| 固定bootstrap抽出 | 40 cluster indices × 50,000 replicates = 2,000,000 bytesを順次検証 |
| 全抽出番号のSHA-256 | `e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5`、凍結値と一致 |
| golden draw | replicate 0 / 1 / 24,999 / 49,999の4行一致 |
| 計算・入力拒否の単体試験 | 21項目通過 |
| 保存した手計算ケース | 7ケース、各2 cluster / 4 replicates、9個の候補×層テーブル / 180 gate checks |
| 保存した基本算術の例 | 件数加算、同じ系列との差、分母0の3例 |
| 実データのseed集計 / CI | 0 / 0、未接続 |
| 観測生成 / holdout / 新評価 | 0 / 未起動 / 0 |

全200万個の番号はbootstrapの**抽出位置を表す固定metadata**であり、観測生成用seedを走らせた結果ではない。SHA-256、binary64、JSONは共有する標準primitive。今回は正式40 seedの観測や実測値を読み込まず、全50,000 replicatesの実性能CIを計算したという意味ではない。手計算例は別の小さな抽出表を使う。

## 算術と確認した失敗条件

- cluster内の12 layouts・両層・候補が一緒に抽出される前提で、渡されたcluster別raw countsを同じweightで合算する。core/stressからoverallを先にraw合算し、割合の平均にしない。実際の12-layout coverageを認証する入口は次工程。
- 分子・分母・秒数は整数で保持する。clean rateは8 equipment-hours、false-alert burdenは100 planned positive incidentsへ換算する。C0との差は同じdrawでそれぞれratio-of-sumsを求めてから引く。
- type-7線形補間で2.5% / 97.5%点を計算する。元標本が未定義、または1つでも分母0のreplicateがあればCIはinconclusive。null数を残し、削除・再抽出・値の埋合せをしない。
- pointとCI boundの両方を、丸め前の値で判定する。閾値ぴったりの値は通し、1 ULPだけ不利な値は落とす。core/stress/overallと全8 targetsの条件を全て要求する。
- C1/C2の差の分布にも共通drawを使う。C0のprofileがinconclusiveなら候補を合格にしない。C0が警報0でprecisionだけ未定義の場合は、固定分母の非劣化比較を継続する。
- 両方通ればC1、C2のみならC2、両方不合格ならno promotion。engineering未完了なら合格にしない。この判断は`fixture_*`欄だけに出し、実際のselected_candidateはnull、formal/promotionはfalseのまま。
- 不完全な候補/層/8-target inventory、重複cluster ID、候補間の予定母数違い、件数の分割矛盾、負数・整数代用bool・非有限値、不正なdrawを拒否する。

例えばcluster Aが1/1、Bが0/9ならpointは1/10=0.1で、平均0.5にはしない。抽出をAA/AB/BBの3回とした手例の95% CIは約[0.005, 0.955]。同じ系列を対照にすればpaired差とCIは正確に0。precisionが0/0になるclusterを含む例では4回中1回がnullになり、CIはinconclusiveとなった。これらは計算例であってBanto実性能の値ではない。

初回の単体試験では、十進手答え0.75とbinary64補間の0.7500000000000001を完全一致にしたassertが1件失敗した。手答えとの比較だけに明示的な許容差を設けた。計算式や実際のgateの丸め前比較は変更せず、1 ULP境界試験も通過している。

## 証拠・資源

OUT: `artifacts/independent-inference-math-2026-09-24`。`draws.json`に全列hashとgolden、`rules.json`に凍結閾値の照合、`fixture-*.json`に手入力と計算結果、`hand-answers.json`に基本算術、`test-results.json`に試験記録を保存した。`checkpoint-draws.json`が抽出番号検算後の中間保存、`summary.json`が全体集計。最終文書revision/各pinは`savepoint-evidence.json`。

config raw SHA-256 `109e726c58e6b57ad884a54db6e7f9688933aef76fcb380234e6a9e4b6deb4d6`、freeze registry raw SHA-256 `61af9100f8daa96d8200a0d2ab23aa7209cab52f0dd5543f9e35797de7332a70`を外部起点にし、registryのconfig pinとも一致を確認した。閾値、Bonferroniのcandidate alpha、判定条件のAND、選択順、単位は凍結configと一致した。

検証実行は3.632928秒、peak private 29.26MiB。最小空きRAM 17.71GiB / commit余裕 21.68GiB、終了時C/D空き 131.04/298.63GiB。開始・抽出検証後・各手例・終了時に資源を記録。新OUTは約1MB以内でCドライブに保存する。前工程と比べシステムpagefileの割当量は増えているが、今回その設定は変更していない。PC全体の容量変動原因や継続的なリーク不在は断定しない。

生成検算保存点SHA `322a7fe20b23febcb4467ba16034ab9bae5c209777590150c61bccbae09c90f8`、旧完走/score検算、実計算source、本流、既存dirty guardを保全。banto-24はPAUSED維持。新しい観測・score・実データのCIは算出していない。

## 残る工程

次は監査済みの保存結果からseed単位のraw countsを認証・集計する入口を作る。登録順、全12 layouts、両層、3候補、profile状態、重複/欠落、予定母数を確認し、この算術への対応を固定する。現在の8 dev + 2 smoke seedには正式40 holdout用bootstrapを代入しない。dev/smokeはroleを区別した記述集計までとし、実性能CI・採択は未評価を維持する。

正式analysis/result schemaへの接続、実データCI/全gate/選択の独立照合、slice/delay報告、runtime/単一writer受入も残る。完全S6、formal_permission、promotion_allowedはfalse、performance_statusはnot_evaluated。Phase 2/3全体は未完了。
