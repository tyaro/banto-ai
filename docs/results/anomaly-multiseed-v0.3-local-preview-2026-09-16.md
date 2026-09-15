# 保存済み観測データからのローカルスコア計算

2026-09-16 JST。引継書§116の単一writer方針を継続し、通常保存APIに既存S2計算を接続した。
実装savepoint **8f42c9e18e533e85afb5e2be0b7b5aede17dcc9f**。
[CLIの使い方](../anomaly-v03-local-preview.md) / [通常保存API](../anomaly-v03-local-publication.md)。

## 実装と確認

`tools/evaluator/preview_anomaly_v03.py run` は入力snapshotから1候補のprofile/scoreを計算し、観測・集計JSON・score JSONL・summaryの4ファイルを新規実行名へ保存する。
`verify` は完了印のhashを受け取り、保存済み観測から再計算して全payload bytesを照合する。
重複した実行名は入力読取り・計算前に拒否し、途中失敗では完了扱いにしない。
既存のC0/C1/C2数式を共用し、ローカル出力にはcampaign identityを付与しない。入力不足は `inconclusive` と除外理由を残す。

新規8件（4.406秒）＋通常保存12件・既存QuantizationAndCaptureTests 10件（1.562秒）、**計30件pass**。失敗・error・skipなし。
CLIの実subprocess、入力変更後のsnapshot再現、重複拒否、内容変更、入力上限、部分入力を確認した。独立レビューP0〜P3指摘0、進捗poll0。safety/diff-check pass。
前回中断した広い評価module試験は再実行していない。

変更前2f5a147のscoringをGit blobからメモリ内に読み、代数的な14,410行の入力で変更後と比較した。
**3候補すべてで48 profileの全ledgerと40行の全score dictionaryが完全一致**し、ローカル出力への射影も一致。計32.230秒。
登録seedやデータ生成器を使った性能評価ではない。比較記録1330 bytes / SHA256 `bb524732923eda2f391b3637fad81b88782b61c72ba20230805dd6ee7041c231`。

## 実CLIでの計算・保存・再検証

公開出力は `artifacts/local-preview-2026-09-16/results/demo-c0-01`。
代数的な `saved_row` で2設備×sample0〜7204の14,410行を用意し、motor-01/sample7202のmotor_currentだけ15を加えた。
入力7,664,634 bytes / SHA256 `e104d67861c37870af170a3e74aed987f3ba402a04181cf80af9cf1bf252dbc0`。
通常Python 3.14.0でC0を実行し、writer終了後に別CLI processから再検証した。

| 確認 | 結果 |
| --- | --- |
| run | PID8720、UTC16:59:06〜16:59:23、17.546秒、exit0 |
| verify | PID13064、UTC16:59:23〜16:59:30、6.467秒、exit0 |
| 計算状態 | computed、48/48 profiles calibrated、normal-prefix issuesなし |
| score | 40行、利用可能32・利用不能8、瞬間的な閾値超過2 |
| 保存・再計算 | local_verified=true、4 payload、run/verifyの集計一致 |

marker SHA256 `0dd554fe9f6800dc6bd13f2abb96f1d2dac5d89c4c4b14e45c05ea5b704ddf4f`。
閾値超過2件は異常イベント数ではない。score区間の先頭5時点だけの計算確認であり、全test区間の網羅や検出性能を表さない。

## 保存と再開点

選抜128 sourceのworkspace/Git blob一致。前回117のうち116不変、README変更1、新規選抜11。完全な依存閉包ではない。前回公開artifact8件不変。
input-evidence22421 bytes / SHA256 `a9a400edb41c1f8026e6ee7d3a0ccdbbc5ccd834a2a73bd50c4de93dd304a6ad`。
最終manifest31342 bytes / SHA256 `93afbcfbd61ab3222addda92812a6dc671fc03b2056694df72c9e244386c908d`。
自身を除く18 artifacts / 論理15,394,076 bytes（約14.7MiB）。今回の公開directoryのみの量。

実行後UTC16:59:57、空きRAM6,084,988,928 / C149,202,980,864 / D198,223,626,240 bytes。D約184.6GiB。
入力上限16MiB・18000行はprocess全体のメモリ上限ではなく、この短い確認から長期リーク不在は判定しない。
OS26200.9445 / boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和・正式pin不変。
本流889cfc3/cleanを維持し、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は保全・commit除外。

**次は、このCLIの出力を使う小さな開発用比較・表示を進める。** 入力は既存decoderの固定時刻・設備・canonical形式に限定され、任意の実設備データをそのまま受け付けるものではない。保存APIや分離試験を作り直さず、必要な対象試験だけを選ぶ。
専用principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。§116の保留・旧root閉鎖・jの消費済みguardを継続。
local_publication_performed/local_preview_computed=true。formal_permissionとその他native保証flagはfalse、acceptance_status=not_completed。正式campaign entry・科学的評価条件・受入gateは未変更。
