# v0.3 判定不能の独立検算と保存済み監査の接続（2026-09-24）

元観測から正常profile・scoreを検算し、その同じ評価結果の警報・イベント照合・集計まで確認する入口を追加した。保存済み1区間（6評価）で全段が一致した。新しい実験は起動していない。

実装保存点は `2505fed6527a00891b9991720421b504a678899f`（先行保存点 `26296b8110c909428ebf975521350f57e288d314`）。記録は `artifacts/connected-observation-audit-2026-09-24`、最終成功結果は `verified-final/` 配下。文書を含む最終保存点・file pinsは同OUTの `savepoint-evidence.json`。

## 判定不能の扱い

独立数値検算器は、正常prefixが健全で完全なdev/smoke観測について、ゼロMADや非有限演算でprofileが判定不能になる理由と保存状態も復元する。部分capture、正常prefixの欠損・品質不良、holdoutへの対応は含まない。一般的な入力不足を成功として受け入れるものではない。

- 全値一定のC0/C1/C2では48 profilesが`zero_scale`となり、利用可能scoreは0となることを確認。
- C1では該当信号、C2では同じ設備・運転段階の全4信号への影響を照合。
- 校正途中の演算overflowでは、計算を終えたsample番号だけを残し、center/scaleはnullのままとなることを照合。
- 各偏差の非有限値を確認し、中央値が有限でも途中のoverflowを見落とさない。空集合・特異行列の理由コードも単体試験する。
- 全値一定の例は、手で数えた検出0件・利用可能時間0・precision未定義のledgerまで同じ結果で確認。

`evaluation_outcome=inconclusive`と「保存結果との照合が通った」は別の状態として報告する。保存済みのsuccess/inconclusiveと復元した結果が異なれば停止する。Gauss-JordanとproducerのCholeskyが数値境界で違う結果を返す場合も、不一致として停止する。全ての浮動小数境界で両方式が同じ理由を返す保証は主張しない。

## 接続した入口

`tools/evaluator/audit_anomaly_v03_observations.py` と `banto_ai.anomaly_v03_observation_audit.audit_completed_chunk` が入口。外部で保持した完走savepointのSHA256を起点に、次の順で1区間だけを読む。

1. savepoint→evidence→固定計画・最終監査済みattemptの結び付きを照合する。
2. 2 datasetsの観測・イベント台帳・品質mask・origins・split・targetsと6評価のbytes/SHA256を照合する。
3. 登録済みidentity、予定event inventory、評価のinput hashesを確認する。
4. 元観測から全profile/scoreを独立復元する。
5. 同じ評価のstreak・source/equipment episodes・incident選択・指標を既存の独立ledger監査へ渡す。

失敗した過去attemptは加算しない。最新attemptが失敗しているのに古い成功へ戻すことも拒否する。入力は1評価ずつ処理し、観測は1 dataset分だけ保持する。評価32MiB、datasetファイル16MiB、evidence8MiBなどの読取り上限を設ける。通常file/祖先を確認し、symlink・junction・複数hardlink・範囲外pathを拒否する。悪意ある同時書換えへの隔離保証ではない。

固定計画・登録identity/event・path検査は既存metadata helperを共有する。profile/scoreとledgerの数値検算器はproducerの数値関数を呼ばない。既存controller/監査CLIと旧audit reportは変更しない。過去のpublication・source・runtime・supervisionの確認は外部pin付き保存点の記録を前提とし、この入口が全campaignを再検証したとは扱わない。

候補作業コピーをカレントにした実行例:

```powershell
C:/Python314/python.exe -B tools/evaluator/audit_anomaly_v03_observations.py `
  --savepoint artifacts/chunk-119-retry-2026-09-24/savepoint-evidence.json `
  --savepoint-sha256 ca976322e0bb9e7b033b94948497a41acc79900668d01edbeebfc3fea8b22c8d `
  --run-root C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1 `
  --chunk-index 0
```

stdoutはJSON報告、失敗はstderrとexit2。ファイルを作成・更新する機能はない。報告を保存する呼出側は、新しい出力先を使う。

## 検証結果

関連40試験が120.120秒で通過。実データ接続時に新しい入口が`input_hashes.events`を`events.jsonl`に誤って結び付けていることを検出し、数値検算前に停止した。正しくは無効な予定イベントも含む`event-ledger.jsonl`である。初回記録・実装を保全した上で修正し、二つのeventファイルを異なる内容で置く回帰試験を追加した。修正後の入口13試験は13.510秒で通過。重複を除く試験項目は41件。入力破損や既存計算の誤りを示すものではない。

最終実装の保存結果照合:

| 項目 | 結果 |
| --- | --- |
| 対象 | chunk0 / attempt1、最初のdev seed・layout0、3候補×core/quality-stress |
| 評価 | 6件一致 |
| 正常profile | 288件一致 |
| score | 86,400行一致 |
| source / equipment episodes | 146 / 84件一致 |
| incidents | 120件一致、集計指標も一致 |
| 読取り | 選択した20 files、132,760,979 bytes（savepoint/evidenceは別） |
| 所要時間 | 10.061610秒 |
| 検証processのpeak private bytes | 159,862,784 bytes、約152.46MiB |

前回score単体検算した12評価のうち6件と重複する。**元観測からprofile/scoreを照合した実データのユニーク数は12のまま**、今回の接続入口を全段通したのは6件。全720評価に広げたと誤記しない。

終了時RAM空き約16.79GiB、commit余裕約15.73GiB、C/D空き約138.31/332.30GiB。今回10秒の前後でD空きは同じ356,809,076,736 bytes。継続的なメモリリーク不在の証明や、PC全体の長期的な容量変動原因の特定ではない。

## 保存と残件

本流 `889cfc3` と固定実計算source `c01d1c9` はcleanのまま。完走・比較・原因調査・前回score検算のmanifest、最終closed、既存dirty guardのpin不変を前後確認した。`banto-24` はPAUSED。旧artifactの更新、追加producer/controller/holdout、push/mergeは行っていない。

今回対象のprofile/score/ledger derivationは検証済みだが、`independent_s6_complete`、`formal_permission`、`promotion_allowed`はfalse、`campaign_evaluations_credited=0`。performanceはnot_evaluatedを維持する。

次は、接続入口による保存済み全120区間/720評価の確認を、重複を数えず区切って進める範囲と保存方法を決める。正常生成式・overlay・丸め前の値、bootstrap/CI/gate、runtime/運用受入は引き続き別の残件。
