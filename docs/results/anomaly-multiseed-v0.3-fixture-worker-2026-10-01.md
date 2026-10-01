# 架空入力の数値workerと所有実行記録（2026-10-01）

小さい架空入力を実際に数値計算する別processを実装し、起動前の親保持期待値・元process handle・source/runtime・4入力・計算出力を結合した。既存の5payload adapterまで接続し、新規15試験と保存例が成功した。[API](../anomaly-v03-fixture-worker.md)、[現在の引継ぎ](../current-handoff.md)。

## 実装と保存先

- 開始revision `045bea45964585b003ac0fdf41b1dcde264230e8`。
- 実装revision `4d3c08b4eb5e235e681ed0f0cafdde3c4f9ddde7`。新module/testの2本だけを追加し、旧64code/18dataのpinを維持した。
- clean実行候補 `C:/Users/TKent/.codex/worktrees/fw01/banto-ai`。旧pc01などの候補を保全し、CRLF差を持つ旧作業版を実行候補へ混在させない。
- OUT `artifacts/fixture-numerical-worker-2026-10-01`、成功試験/保存例は `tests-1/`。最終文書revision・全artifact/pin・資源は最上位savepoint-evidence.jsonとsave-checks.json。
- 前保存点24493bytes/SHA-256 `8c96fb2649059b3a7500f20c2327435c95c193a7faa7199151329007a5f07046` を外部起点とした。

## 数値計算と照合の結果

40個の架空clusterと4draw、12layout×2層×3候補の2880宣言枠を使用した。親は前工程の既知文書pinを保持し、子が計算した文書と照合した。親は保存例の期待値を新たに数値計算していない。これは架空の宣言と小さい手例であり、2880件の新評価を行った意味ではない。

| 項目 | 観測結果 |
| --- | --- |
| 新規試験 | 15 pass、failure/error/skip 0、54.015秒 |
| 保存例全体 | 14.678秒 |
| 子process監視時間 | 4.056秒 |
| 子PID・終了 | 18588、exit0、reaped、観測error0 |
| 計算文書 | 1,932,543bytes、既知pinと一致 |
| wrapper | 5file、1,976,761bytes、保存後pin一致 |
| selected source / Python runtime / 入力 | 21 / 2 / 4 files |
| 補助依存照合 | project37、全245files、188modules、native48、前後追加0 |
| 子peak private | 64.95MiB |
| 試験・保存harness peak private | 126.41MiB |

文書SHA-256は `2c20d80e63bf53e662ee722ba48f723285cf08182178036a2410a78d6033c6b1`。既存文書/slice接続を用い、本文1233行・補助2835行・詳細9表を保持する。子の実行証拠10083bytes、応答255810bytes、stderr0bytes。親の元Popen handleと子自身のPID・生成FILETIME/start_tokenが一致した。

source/runtimeのselected bytesは実行前後で一致、子が採取した補助依存245filesは親が終了後にdisk/Gitへ照合した。新役割の事前受入済みdependency profileや、メモリ内コードの完全固定を主張するものではない。

## 試験範囲と上限

親側の推論関数を禁止しても実子の計算が成功することを確認した。非fixture mode・role/operation違い・過大入力・リンク数・入力改変・9draw・不完全coverage・revision不一致を拒否。既知出力pinの不一致、再封印したrole/生成時刻、親保持期待ファイルの改変も成功扱いしない。失敗supervisionでは出力を組み立てず、未終了ownerは診断保存失敗時も保持する。既存attempt/inputへ上書きしない。

子には60秒/private256MiB/stdoutとstderr合計1MiBを適用。架空drawは最大8、入力合計10MiB、文書4MiB、5payload合計8MiB。既存supervisorを再利用した。今回の失敗supervision試験は模擬停止応答であり、新しい実メモリ枯渇・実timeout負荷試験は行っていない。

全工程のdirectory総量・system commitの連続停止条件は未接続。実行前後の資源を記録し、保存例後は空きRAM8.32GiB、commit余裕12.92GiB、C/D空き114.10/387.12GiB。OSは25H2、build26200、UBR9457。OS実値を記録し、旧formal pin9168は変更しない。最終保存時の値はsave-checks.jsonを正とする。

## 到達範囲と次工程

status=verified、fixture_inference_performed=true。既存numerical_analysis_performed、formal/promotion/S6/trust/execution_authenticated/full closureはfalse。正式null4欄とready=falseを維持した。writer/reader/audit・公開markerは今回起動/生成していない。

既知文書も同じ計算実装に由来するため、今回の一致は独立した数値検算ではない。次は保持入力とanalysis出力に対し、別実装による小さい数値auditを接続する。その後に全工程の資源停止予算を揃える。正式受入の5作業群全体、正式50,000反復、holdout、Phase2/3全体の完了は残る。

既存720評価の再実行0、新評価0、登録データ読込み0。旧実計算c01d1c9、本流6f1285d、closed、既存dirty文書/CRLF差、旧候補・保存点を保全した。banto-24 PAUSED。principal/保護root/UAC/ACL、正式gate/freeze、push/mergeは対象外。
