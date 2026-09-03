# Data generator tools

seed 再現可能なsynthetic industrial signalとmetadataを作成するutilityです。clean checkoutでは、リポジトリルートから次のCLIを実行します。

```text
python tools/data-generator/generate.py --config examples/configs/synthetic-motor-small.json --output artifacts/generated/synthetic-motor-small
python tools/data-generator/check_quality.py --dataset artifacts/generated/synthetic-motor-small
```

これはpackageをinstallしないclean checkout向けの標準手順です。`python -m banto_ai ...` を使う場合は、先に `python -m pip install -e . --no-deps` を実行してください。

generatorはmotor／conveyorの複数equipment、motor current、motor temperature、conveyor speed、load proxy、vibration feature、operating mode／recipe stepを扱います。regimeは `stopped`、`startup`、`low_speed`、`nominal`、`high_load`、`cooldown`、eventは `sensor_drift`、`spike`、`dropout`、`overheating_trend`、`jam_or_slip`、`stuck_value` です。event intervalは `[start,end)` で、無効eventは観測へ適用せずground-truthにも出力しません。

観測値とevent labelは別fileです。出力はcanonical JSON／JSONLで、同じseed／configならbyte-for-byte同一です。既存出力は上書きせず、既定出力はGit無視領域の `artifacts/generated/<dataset_id>` です。quality checkerはsampling interval、unit、quality、event、split、record_count、generator configとのsemantic consistency、fingerprintをfail closedで確認します。合成データは実設備を代表するものではなく、顧客データは扱いません。
