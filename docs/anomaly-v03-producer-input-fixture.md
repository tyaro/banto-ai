# 架空producer記録からconsumer入力への結合

2026-10-02。登録・全予定枠・各試行・入力bytes・結果要約・終了記録を結び、最新試行の主集計をconsumerへ渡す純粋関数。実producer形式や正式登録の受入ではなく、架空の登録とplaceholder入力を使う試作である。

[実装](../src/banto_ai/anomaly_v03_producer_input_fixture.py)、[23項目の試験](../tests/test_anomaly_v03_producer_input_fixture.py)、[保存結果](results/anomaly-multiseed-v0.3-producer-input-boundary-2026-10-02.md)。

## 呼出しと信頼範囲

```python
bind_producer_inputs(
    manifest_raw, snapshots,
    expected_mode="fixture",
    expected_manifest_pin=caller_manifest_pin,
    expected_registration_pin=caller_registration_pin,
)
```

`snapshots` は論理相対pathからraw bytesへの辞書。呼出し側が保持するmanifest/registrationのbytes数とSHA-256を必須とし、受取データ自身から期待値を補わない。固定期待値への改変と、期待値を更新しても残る意味上の不整合を別々に検査する。外部期待値を選ぶ呼出し側は信頼境界であり、期待値ごと正しく整合させた架空データの差替えを実行認証で検出する機能ではない。

modeを最初に検査し、fixture以外をdecode前に拒否する。ファイル読取り、process起動、実seed registry読込み、推論、公開は行わない。`input_bytes_verified=true` は供給された架空bytesの一致のみを指す。

## 結合する記録

| 記録 | 検査内容 |
| --- | --- |
| registration.json | `plan(1..40)` の固定架空ID/seed・12 layout・2層・3候補と外部pinの一致 |
| manifest | 全予定区間の順序、各attempt数、供給payloadの完全な一覧とpin |
| 区間のattempt | 予定6評価のidentity、連番、状態、failure、入力hash、結果hash、終了記録 |
| placeholder入力 | dataset/kind、raw hash、候補間・再試行間の同一性。観測値の代用であることを明示 |
| 評価要約 | identity/attempt/登録/input hash/profile、13指標の整数count、正常時間・検出delay histogram |
| producer/completion.json | 最新attempt pinの順序付き一覧、全体状態、終了確認、failure |
| 参照されたfailure evidence | raw hash、scope、stage/reasonの一致。参照なしの失敗は欠落として履歴に残す |

40 clusterなら480区間、1区間6評価で2,880枠。候補間では同一datasetの6種入力を共有する。全JSONをcanonical bytesとして検査し、未参照payload、欠落、同数の差替え、順序違いも拒否する。論理pathはファイルを開く用途に使わない。

## 状態と集計

正常完了の記録は終了確認済み・exit0・観測errorなしを要求する。これは供給された記録の整合性検査であり、実processを観測した証明ではない。再試行前のattemptはfailedのみ許し、hash/source/runtime等のintegrity failure後の再試行は拒否する。

最新attemptだけを集計し、旧失敗は `failed_attempt_history` に残す。最新attemptまたはproducer全体が未完了/失敗なら `complete_for_aggregation=false`、`clusters/diagnostics=null`。予定枠、状態、failure、最新pinを保持し、以前の成功への差戻しや成功分だけの集計はしない。

完了時はcluster・候補・層ごとに12 layoutの分子/分母と有効正常時間を加算し、検出済みdelayだけを展開する。recall/availability等の分母、precisionのmatched/unmatched分割、clean false alertの部分集合、delay総数も検査する。profile inconclusiveは完了した判定不能として保持し、precisionの0/0も値を補わない。inconclusiveがあれば `all_profiles_calibrated=false`。

`clusters` は既存document fixtureの入力、`diagnostics` はanalysis adapterの診断、`wrapper_coverage` はwrapperの全予定枠の形式に対応する。率/CI/gate/候補選択・draw生成は行わず、slice/sidecarの要約は今回の入力に含めない。正式文書のready/null欄も変更しない。

## 上限

1..40 cluster、attemptは各0..4、20,000 payload以下、manifest 4MiB以下、payload各128KiB以下、manifest込み32MiB以下。attempt数はparserの境界であり、追加再試行の許可ではない。

純粋関数の上限は入力bytes/件数に対する検査。試験/保存ハーネスでは既存の120秒・親private512MiB・成果物32MiB/256entries・RAM/commit余裕2GiB・disk余裕5GiBを併用し、採取とcheckpointで停止する。hard quotaや正式全体予算の受入ではない。

## 保存例と未完了範囲

保存例は40架空cluster・480区間・2,880最新枠に、旧失敗1回、判定不能1枠、precision0/0を含む。9,123論理payloadのraw bytesは1本のJSONLに保存し、各pathとbytesをmanifestへ再照合できる。9,123個の実ファイルや実評価を生成した意味ではない。

raw観測からcount/episode/matchingを導いた正しさ、実登録seed・coverageの真正性、過去の実process/source/runtimeは検証していない。`registered_data_read`、`raw_observation_derivation_checked`、`producer_execution_authenticated`、`analysis_authorized`、`numerical_inference_performed` はfalse。正式許可・昇格・S6・完全closureもfalseを維持する。

次は架空producerのslice/sidecar用要約を同じ登録・入力pin・最新attemptへ結合する。主集計と補助集計の対応を検査し、既存720評価や保存済み解析・公開を再実行しない。
