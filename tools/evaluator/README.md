# benchmark runner

`tools/data-generator/generate.py`で合成データを作成し、`check_quality.py`で品質gateを通した後、次の順で評価します。

```text
python tools/data-generator/generate.py --config examples/configs/synthetic-motor-small.json --output artifacts/generated/synthetic-motor-small
python tools/data-generator/check_quality.py --dataset artifacts/generated/synthetic-motor-small
python tools/evaluator/run_benchmark.py --config examples/configs/benchmark-small.json
```

出力は新規ディレクトリへatomic作成され、`result.json`、`predictions.jsonl`、`summary.md`を含みます。既存出力は上書きしません。合成データの結果は実設備性能を示しません。fevは現段階では導入せず、自前runnerを安全性・再現性の基準にします。

`runtime.model_state_bytes`は各baselineのmodel名・immutable parameters・空のlearned stateをcanonical JSONへUTF-8直列化したbyte数です。stateless baselineの決定的な保存量を表し、Python objectの実メモリ量や出力file sizeではありません。`output_size_bytes_excluding_result`は`predictions.jsonl`と`summary.md`の合計で、model stateとは別です。

chronological split、point／interval metric、residual anomaly metric、calibration check、report generation の共通 utility 用です。

単一の aggregate score が運用上の失敗を隠さないよう、metric は signal、horizon、operating mode、event type 別の slice を保持します。
