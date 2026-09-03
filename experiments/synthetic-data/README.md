# Synthetic industrial data 実験

seed 再現可能な motor、conveyor、process-like signal の生成を扱います。Phase 1 savepoint 1では標準ライブラリだけで、motor／conveyorを複数設備生成し、6つのregimeと6種類のfault/eventをJSON／JSONLへ出力します。generatorにはregime、相関したsignal、drift、欠損、ground-truth eventを持たせ、物理的な仮定を明示します。

```text
python tools/data-generator/generate.py --config examples/configs/synthetic-motor-small.json --output artifacts/generated/synthetic-motor-small
python tools/data-generator/check_quality.py --dataset artifacts/generated/synthetic-motor-small
```

上記はsrc layoutのclean checkoutから実行する標準手順です。`python -m banto_ai ...` を使う場合は、先に `python -m pip install -e . --no-deps` を実行してください。

出力には `observations.jsonl`、`events.jsonl`、`generator-config.json`、`dataset-manifest.json`、`split-manifest.json`、`fingerprint.json`、`summary.json` が含まれます。chronological splitとcross-equipment splitを同時に作成し、split境界は `[start,end)` です。複数equipmentのためtimestampのstrict increasingはequipmentごとに検査します。quality checkerはcatalogを正としたsampling interval、unit、quality、event、split完全被覆・record_count、generator configとのtimestamp／regime／event／summaryのsemantic consistency、SHA-256 fingerprintを検査します。

生成したdataset本体は、原則としてGitの外に置きます。commitするのはgenerator parameter、schema、安全な小型fixtureだけです。これは合成データであり、実設備を代表すると主張しません。顧客データは入力にもrepositoryにも含めません。
