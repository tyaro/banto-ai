# v0.3 保存観測からのprofile・score独立検算（2026-09-24）

続報: [判定不能の独立検算と保存済み監査の接続](anomaly-multiseed-v0.3-connected-observation-audit-2026-09-24.md)を完了した。以下は最初のcalibrated限定実装の記録であり、最新の対応範囲・入口は続報を参照する。

保存された正常profileやscoreを正しいと仮定せず、元の観測JSONLから計算し直す検算器を追加した。C0/C1/C2の正常profile、残差、score、phase、availability、依存値を別実装で照合する。生産側の検知方式や実験条件は変えていない。

## 実装した範囲

新しい`src/banto_ai/anomaly_v03_score_audit.py`は標準ライブラリだけに依存し、producerの数値関数・scorer・生成器・契約定数をimportしない。計算の定義は登録計画§3～4に従う。

| 範囲 | 検算する内容 |
| --- | --- |
| 観測の読取り | 外部指定SHA256、canonical JSONL、18,000行、時刻・設備順序・重複、値の有限性と保存精度、quality |
| phaseと判定可否 | 観測された運転段階の切替からphaseを復元。現在/直前のquality、境界、C2の他信号依存を確認 |
| C0 | 正常validationの差分からcenter/MADを復元 |
| C1 | 正常fitのphase別中央値、validationの残差center/MADを復元 |
| C2 | 正常fitの標準化・580ベクトルの共分散・shrinkage・逆行列、validationのcenter/MADを復元 |
| test score | 復元したprofileから全14,400点の残差・score・null・availability・閾値超過・依存値を照合 |

C2の逆行列はproducerのCholesky実装を呼ばず、pivot付きGauss-Jordan法で求める。profile・残差・scoreの浮動小数値は絶対/相対各`1e-12`以内で比較する。ID・整数・状態・判定フラグは厳密に比較し、元観測から作る依存値もexact比較する。

閾値判定は許容誤差で緩めない。再計算した判定との一致に加え、保存score自身が保存された超過フラグと整合するかも検査する。閾値直前・同値・直後、負score、bool/NaN/Infinityをテストした。逆行列の別方式による丸め差が判定を変える場合は不一致として停止する。

## 現時点の入力制約

対象は**完全なdev/smoke観測、正常prefixに欠損がなく、全profileがcalibratedとなる評価**。holdout、部分capture、ゼロMADなどの判定不能profileは、現段階ではpassを返さず拒否する。次の実装で判定不能の理由や状態を独立に照合する範囲を追加する。

この関数だけでは、渡されたidentityや評価JSONの出所を認証しない。呼出側が外部の固定保存点から入力hashと登録identityを確認する。今回は完走時の保存点→evidence→plan→選択した元ファイルという既存のpinに結び付けた。

正常な生成式、overlayの適用、丸め前のlatent値は再生成していない。保存値が6桁精度であることの確認を、生成・丸め契約全体の独立検算とは呼ばない。streak/episode/matching/metricは既存ledger監査の担当で、新モジュール単独の検算範囲に含めない。

## テストと保存結果の照合

12テストが21.716秒で通過。合成式による固定fixtureを使用し、新しい登録seedの系列生成は行っていない。

- 手計算できるmedian/MAD、共分散shrinkageの解析解、逆行列、ゼロscale・特異行列の拒否。
- 全3方式のproducerとの比較。consumer実行中はproducer関数の呼出しを禁止し、stdlibのみのimportも確認。
- 運転段階の切替とgap、現在/直前quality、C2だけに生じるpeer欠損の影響。
- profile、score、phase、availability、閾値、依存値の改変、重複profile・欠落score・identity/hash不一致の拒否。
- 不正JSON・NaN・観測の欠落/順序、test値を変えても正常profileが変わらないこと、正常prefixの異常の拒否。

保存結果は、最初のdev seed `2486912926863618161` の停止2 layouts（0、6）×3方式×2条件を対象とした。**12評価、576 profiles、172,800 score行が一致**した。元入力は16ファイル・252,536,767 bytesで、4つのobservationsを方式間で再利用し、評価結果は1件ずつ読んだ。元のproducer・controllerは起動していない。

初回の数値照合は実装保存点`f3c1992`で成功した。その後、保存scoreと超過フラグ自身の整合チェックを補強し、`14e6c33`の最終実装で12評価をもう一度照合した。初回結果も保持し、最終結果は別の`verified-final`ディレクトリへ保存した。この2回を24個の独立評価として加算しない。

保存先：`artifacts/independent-score-audit-2026-09-24`。最終実行のconsumer revision、各評価の結果、入力pin、時間、前後のRAM/commit/ディスク空きは`verified-final/start.json`、`evaluation-01.json`～`evaluation-12.json`、`input-pins.json`、`summary.json`に保持する。前後観測のみなのでpeak使用量やリーク不在は主張しない。コード・テスト・文書・artifactの最終pinは`savepoint-evidence.json`に残す。

## APIと次の作業

```python
from banto_ai.anomaly_v03_score_audit import audit_score_derivation

# resultとobservation_bytesは呼出側で固定保存点・identity・hashを照合済みとする。
report = audit_score_derivation(
    result, observation_bytes,
    expected_observation_sha256=trusted_observation_sha256,
)
```

成功した対象には`profile_derivation_verified=true`、`score_derivation_verified=true`を返す。ただし`independent_s6_complete=false`、`formal_permission=false`、`promotion_allowed=false`を維持する。

既存のcontroller/監査CLIへ自動接続せず、保存済み720評価の古いaudit reportを書き換えない。今回新たに導出を検算したのは選択した12評価だけで、全720評価への適用は未完了。

次は判定不能profileの扱いと、外部pin・登録identity・既存ledger監査を結ぶconsumerの入口を整える。その後、既存720評価への必要な適用範囲を確定する。正常生成・overlay・丸め、bootstrap/CI/gate、単一writer受入・runtime inventory・資源見積りも残る。新しいデータ生成や正式holdoutは今回の作業に含まない。

関連：[登録計画](../anomaly-multiseed-evaluation-plan-v0.3.md)、[前段の原因調査](anomaly-multiseed-v0.3-failure-analysis-2026-09-24.md)、[独立監査と進行記録](../anomaly-v03-independent-audit-and-checkpoints.md)。
