# 架空producerの補助集計入力を試行記録へ結合

2026-10-02。各評価のincident/score/context内訳を、主入力と同じ登録・入力bytes・結果要約・試行記録へ結び付ける。最新の試行だけをcluster単位へ合算し、既存slice adapterへ渡す純粋関数である。

[実装](../src/banto_ai/anomaly_v03_producer_slice_fixture.py)、[試験](../tests/test_anomaly_v03_producer_slice_fixture.py)、[保存結果](results/anomaly-multiseed-v0.3-producer-slice-boundary-2026-10-02.md)。[主入力v1](anomaly-v03-producer-input-fixture.md)の形式と実装は変更しない。

## 呼出しと供給物

```python
bind_producer_slices(
    primary_input, slice_manifest_raw, slice_snapshots,
    expected_mode="fixture",
    expected_manifest_pin=caller_slice_manifest_pin,
)
```

位置引数の `slice_manifest_raw` はAPIの `manifest_raw`、`slice_snapshots` は `snapshots` に対応する。主入力のraw manifest・snapshot辞書・外部manifest/registration pinを `primary_input` へ渡す。補助側にも別の外部manifest pinを必須とし、供給側の自己申告から期待値を作らない。呼出し側が保持する期待値が信頼境界で、過去の実processの真正性を証明する仕組みではない。

補助manifestは主manifest pin・登録pin・固定encoding・全補助payloadのpinを保持する。各補助payloadは主manifest/登録/attempt receipt/summaryのpin、identity、attempt番号、6種入力hashと内訳を持つ。両側のcanonical bytes、全inventory、参照先を照合する。

旧attemptを含め、主記録に結果summaryがある全評価の補助記録を要求する。未開始・未完了でsummaryがない枠の補助記録や、その他の未参照データは受け付けない。主入力の成功枠数だけを見て欠落を補うことはしない。

## 内訳の形式と照合

内訳は既存sliceの全dimension/keyを固定順序で並べた整数配列。manifestのencodingへその順序と列名を完全に記録し、実装の定義と一致させる。行・列の省略、余分な項目、bool/負数/非整数/上限超過を拒否する。JSON field名の繰返しを減らすための表現で、検証対象の内訳を省略するものではない。

| 内訳 | 主な検査 |
| --- | --- |
| incident | 予定数・検出数・delay histogram、各分類の分割合計、class/equipment/modeのjointとmarginalの一致 |
| score | 全target/mode/phase/context/quality/profile等の予定・観測・利用可能・閾値超過・onset、部分集合と各分類合計 |
| event-offset | 予定参照数＝観測＋対象外signal＋試験範囲外。省略理由を分けて残す |
| equipment context | 正常時間・episode・unmatched、score contextとの露出時間の対応 |
| 主集計との対応 | recall/precision/false alert/clean rate/availability、delay分布、profile状態の一致 |

各補助記録は1評価。判定不能数は0か1、calibrated評価にinconclusive scoreを混ぜない。inconclusive評価では該当score枠を残す。raw観測を再生して分類先・score・episode/matchingの正しさを再導出する機能ではなく、供給された要約同士の整合性を検査する。

## 履歴と出力

主adapterを呼び、全予定枠・連番・終了状態・失敗を同じ規則で検査する。再試行前のsummaryも照合して履歴件数に数えるが、合算は最新attemptだけ。最新失敗またはproducer全体の未完了では、主結果のcoverage/失敗履歴を保持し `slice_source=null` とする。

完了時は `slice_source` に既存 `anomaly-v03-slice-fixture-input-v1` 形式を返す。40 clusterなら3候補×2層で240セル、各セル12 layoutの内訳。整数countとhistogramを加算し、ゼロセル・判定不能・省略理由を保持する。`primary` に検証済み主結果、`latest_slice_pins` に最新補助記録のpinを残す。

CI/draw/gate/候補選択、実データ評価、process起動、文書生成、公開は行わない。補助内訳の分割チェックでは既存の記述統計validatorを使うが、正式推論や独立S6の完了を意味しない。

## 上限と残件

補助manifestは4MiB、補助payloadは各32KiB、最大11,520件。両側のmanifestと全payloadの合計は32MiB以内。主側の既存上限も併用する。件数はparser上限で、再試行の実行許可ではない。資源ハーネスの時間・メモリ・容量予算も維持する。

`registered_data_read`、`analysis_authorized`、`producer_execution_authenticated`、`raw_observation_derivation_checked`、`numerical_inference_performed` はfalse。実登録seed/coverage、raw観測導出、実行source/runtime、正式契約の受入は未完了。

次は今回の主入力・補助入力を、既存の限定fixture解析/audit経路へ外部pin付きで接続する。実holdoutや既存720評価の再実行、正式50,000反復は含めない。
