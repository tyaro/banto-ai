# ADR-0002: benchmark runnerとfevの再評価

## 状態

採用（Savepoint 2）。

## 決定

現段階では`fev`を導入せず、標準ライブラリだけで実装する自前runnerを比較基準にする。baselineのadapter境界、fail-closedな入力検査、validation-only校正、再現可能なprovenanceを先に固定する。

## 理由

- 外部ML packageやcheckpointを増やさず、clean checkoutとCIを同じ条件で再現できる。
- Bantoの設備データを外部サービスへ送らず、データ境界とライセンス検査を維持できる。
- `fev`併用時も、同一dataset fingerprint・split・metric定義との比較を検証できる。

## Savepoint 2で固定した評価契約

- datasetは、品質gateを通過した`dataset-manifest.json`と、そのmanifestが指す検証済み`fingerprint.json`の`dataset_fingerprint`を唯一の識別値として結果へ記録する。runnerが独自に再hashして置き換えることはしない。
- splitは`split-manifest.json`のchronological `[start,end)`を唯一の基準とし、設備ごとにtimestampをindexへ解決する。contextはoriginより前、actualは同じsplit内だけに限定する。既知未来共変量もoriginからhorizon末までしかrequestへ渡さない。
- MASEのscale historyはtrain splitだけとする。scaleが0または不足の場合は`mase_status`を付けて評価不能とし、数値を捏造しない。
- WISは、medianを0.5重み、各対称central intervalを`alpha/2 * ((upper-lower) + 2/alpha * outside_distance)`として、分母を`K+0.5`とする標準定義を使用する。区間外penaltyを含むinterval score全体へ`alpha/2`を掛ける。quantile crossing、非有限値、長さ不一致はfail closedする。
- 分位点校正はvalidation residualをlead time別に使い、test値を混ぜない。sliceは`model|target|equipment|actual timestampのmode|lead`でraw prediction pointを集計し、aggregateも全prediction pointを同じ重みで再計算する。RMSEはpointごとのRMSEを平均せず、全二乗誤差の平均の平方根とする。
- `runtime.model_state_bytes`は、baselineごとの`model_name`、immutableな`parameters`、空の`learned_state`をsorted-key・compact JSONとしてUTF-8直列化したbyte数である。現在のbaselineは永続的な学習stateを持たないため、これは設定と空stateの決定的な保存量であり、Python objectの実メモリ量や予測出力file sizeではない。出力fileは別の`output_size_bytes_excluding_result`として記録する。
- `success`は予測があり失敗がない状態、`partial`は予測があり一部のmodel/equipment/targetが`failed`または`inconclusive`の状態とする。validationで失敗した単位はtestで再実行しない。全単位失敗または予測0件はrunner失敗とし、成功resultを生成しない。

合成データでの数値は、generatorのシナリオに対する実装検証用であり、実設備の精度・安全性・導入可否を示すものではない。

## 見直し条件

Phase 2でadapter数、実験管理、metric互換性、依存管理の費用対効果を評価し、fev導入による再現性・保守性の改善が確認できた場合に併用を再評価する。
