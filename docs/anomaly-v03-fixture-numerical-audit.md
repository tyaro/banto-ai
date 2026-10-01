# 架空入力の主集計を別実装で検算する

`anomaly_v03_fixture_numeric_audit` は、40個の架空cluster・最大8drawの入力から、9個の主集計表を別実装で検算する。`anomaly_v03_fixture_audit_worker` は、その検算を所有する子processで実行し、呼出し側が保持した入力・既存analysis結果・実行期待値へ証拠を結ぶ。[算術実装](../src/banto_ai/anomaly_v03_fixture_numeric_audit.py)、[worker](../src/banto_ai/anomaly_v03_fixture_audit_worker.py)、[試験](../tests/test_anomaly_v03_fixture_numeric_audit.py)、[実行試験](../tests/test_anomaly_v03_fixture_audit_worker.py)、[保存結果](results/anomaly-multiseed-v0.3-fixture-numerical-audit-2026-10-01.md)。

前工程の[数値worker](anomaly-v03-fixture-worker.md)と同じ期待文書を生成し直す処理ではなく、保持した入力から主集計の値を導出して比較する。算術moduleは標準ライブラリのみをimportし、既存のinference/adapter/gate/slice関数を使わない。正式解析・独立S6の完了を示す入口ではない。

## 検算範囲

計算側のdraw頻度による重み付けとは別に、auditはdrawの40個の番号を順に展開して整数countを加算する。同じdrawをcontrol/候補・両層へ適用し、ratio-of-sumsと対応のある候補差を計算する。凍結したbinary64の演算順序とtype-7分位点の定義は維持する。

| 検算する対象 | 数・内容 |
| --- | --- |
| 主集計表 | 3候補×core/quality-stress/overall、9表 |
| 絶対推定 | 13指標×9表、117推定のcount・point・CI・null回数 |
| 対応のある差 | 12指標×2候補×3層、72推定 |
| gate | absolute/pairedの180判定、閾値の等号を含む |
| 付随数値 | scheduled/effective exposure、実効警報率、検出済みdelayの和集合からの要約 |
| 判断・対応 | profile/readiness、候補適格性、C1優先選択、decision、packetと本文の主表一致 |

ゼロ分母のdrawを削除・再抽出せず、null回数とinconclusiveを残す。profile不成立とゼロ分母を区別する。入力は固定のinvented ID、正確な整数counts、12layoutの分母、検出済み件数に対応する整数秒delayを検査する。

**slice/診断sidecarの導出、全coverage枠、producer観測、登録データの推論は今回の独立検算対象外。** 結果の `not_checked` に明示する。これらが未検算なのに文書全体やS6が検算済みとは扱わない。本文の正式null4欄・外側の閉じたフラグも確認する。

## 入力と既存analysisの結合

`audit_with_evidence(request, *, expected_revision, receipt_parent, receipt_name)` を使う。requestはformat=`anomaly-v03-fixture-audit-request-v1`、mode=fixture、role=audit、operation=`audit-invented-primary-numerics-v1`、inputs、analysis_referenceを持つ。非fixture mode・役割/operation違いはファイルアクセス前に拒否する。

| 固定入力名 | 内容 | 上限 |
| --- | --- | --- |
| fixture/input.json | 元の架空数値入力 | 1MiB |
| fixture/document.json | 保持済みanalysisの文書 | 4MiB |
| analysis/result.json | 前工程のverified analysis receipt | 64KiB |
| analysis/evidence.json | そのanalysisの実行記録 | 64KiB |
| fixture/audit-operation.json | operation、audit revision、analysis_reference | 4096bytes |

各入力に絶対path、外部保持pin、links=1を要求し、合計6MiB以内とする。fixtureの3入力はcanonical JSON。analysis_referenceには呼出し側が保持したresult_pin、evidence_pin、analysisのsource_revisionを置く。実行記録が指す数値入力pin・文書pin・role・source revision・PID/完了状態と保持結果を照合する。

元analysisの起動・全source/runtime照合を再実行する処理ではない。今回の保存例では前工程の外部savepointとファイルpinを起点にverified receiptを受け取り、元のanalysis workerを起動せず、元の4ファイルも変更しない。呼出し側の外部期待値の由来は必須であり、任意に再封印した自己申告receiptだけで元analysisを認証するものではない。

## auditの実行記録

親は13本のselected source、Python本体/DLL、5入力、ランダムinvocation IDと固定argvを保持する。新しいclean checkoutでGit/raw bytes一致を要求する。親が事前に作るのは対象範囲・入力digest・次元を持つ固定の成功要約だけで、主集計の再計算はしない。成功要約のpinも起動前に保持する。

子は数値の一致を確認した場合だけ、限定した成功要約を `payload/primary-audit.json` に保存する。元Popen handleと子自身のPID/生成時刻、role=audit、input/output、source/runtime前後一致を既存evidence validatorへ結ぶ。補助依存fileは終了後にdisk/Gitへ照合する。成功要約だけの一致を数値実行の証明とはせず、所有した子の終了・実行記録とともに確認する。

子の上限は60秒、private256MiB、stdout+stderr合計1MiB。新しいreceipt directoryのみを使う。失敗時は再試行せず記録を残し、未終了ownerは診断保存の失敗でも呼出し側へ再送出する。全工程directory総量/system commitの連続停止は別の残件である。

## 結果の読み方

成功はstatus=verified、fixture_numerical_audit_performed=true。primary-audit.jsonはstatus=primary_numerics_matched、検算した9表/117推定/72差/180gateと対象外範囲を記録する。監査receipt、source/runtime、input/output pinsを元analysis referenceとは別に保存する。

formal/promotion/independent_s6_complete/execution_authenticated/full closureはfalse。これは別の算術実装による小さい手例の一致であり、独立組織による監査、登録データの正式数値検証、全依存の受入、公開完了を意味しない。旧analysis文書や5payloadを書き換えず、wrapperのaudit段階も遡って成功へ変更しない。

次は、限定したfixture工程のdirectory総量・system commit余裕を含む資源停止条件を接続する。正式受入時は、このprimary-onlyの検算範囲とslice/sidecarを含む残件を明示して評価する。
