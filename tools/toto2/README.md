# Toto 2.0 4M の隔離実行

この入口は Datadog の `toto-2==2.0.0`（umbrella package `toto-models==1.0.0`）と、HF の固定 revision `8306a9801cf98c0f5ffe4b2dcc8f496e616d84d9` による CPU 評価専用です。コード／重みはいずれも Apache-2.0 ですが、利用区分は `commercial-evaluation` に固定し、本番制御や Banto Hub／PLC write は行いません。

専用環境は [`environments/toto2/requirements.in`](../../environments/toto2/requirements.in) と、実際に解決・検証した [`requirements-windows-cpu-py314.lock`](../../environments/toto2/requirements-windows-cpu-py314.lock) を使います。モデル重みとデータは repository 外に置きます。

```powershell
py -3.14 -m venv ..\.venv-banto-ai-toto2
$totoPython = '..\.venv-banto-ai-toto2\Scripts\python.exe'
& $totoPython -m pip install --upgrade pip
& $totoPython -m pip install -r environments\toto2\requirements-windows-cpu-py314.lock
& $totoPython tools\toto2\preflight.py --cache-dir C:\banto-cache\toto2 --format both
& $totoPython tools\toto2\prepare_checkpoint.py --cache-dir C:\banto-cache\toto2 --accept-apache-2.0
& $totoPython tools\toto2\run_smoke.py --cache-dir C:\banto-cache\toto2 --output artifacts\toto2\cpu-smoke.json
& $totoPython tools\toto2\run_benchmark.py --config examples\configs\benchmark-metropt3-toto2-4m.json --cache-dir C:\banto-cache\toto2
```

実行開始後は network を禁止し、cache snapshot の sibling set、revision、`model.safetensors` の exact size/SHA-256、package version、license を検証します。短い horizon の公式推奨どおり `decode_block_size=None`、CPU、batch=1 を固定します。Toto 2.0 は current 2.0 で fine-tuning／exogenous variable をサポートしないため、known-future covariate request は fail closed です。MetroPT-3 の context=120 は変えず、patch_size=32 に合わせて adapter 内で先頭8点を未観測 padding し、effective model input length=128 とします。target／past-only contextでは、missingは`value=null`、staleは有限値＋quality flagとして受け付け、両方を0-fillして`target_mask=false`とし、paddingまたは内部missing／staleがあれば`has_missing_values=true`を渡します。invalid／out_of_order、value／quality不整合はfail closedです。syntheticの`stale_value`はsource ageやtransport freshnessの証拠ではありません。

この初回追加では4MのCPU smokeとMetroPT-3 benchmarkを実行済みです。結果は[`docs/results/toto2-metropt3-evaluation-2026-09-04.md`](../../docs/results/toto2-metropt3-evaluation-2026-09-04.md)を参照してください。22M、fine-tuning、seed拡大、fault slice、実設備一般化は対象外です。

## 小規模 benchmark matrix（既存 small matrix）

Toto 2.0 4M向けに、合成motor／conveyorデータを使う小規模matrixの実行基盤を追加しました。設定は [`examples/configs/benchmark-matrix-toto2-small.json`](../../examples/configs/benchmark-matrix-toto2-small.json) で、seed 17／42、horizon 15／30、context 64／120の8条件をseed→horizon→contextの順に展開します。

```powershell
& $totoPython tools\toto2\run_matrix.py --config examples/configs/benchmark-matrix-toto2-small.json --cache-dir C:\banto-cache\toto2
```

各seedで合成データを一度だけ生成し、同じ共有Toto adapterを8セルで再利用します。context=64はpaddingなし、context=120はpatch_size=32に合わせて128点入力（先頭8点は未観測padding）です。known-future covariateは空、device=cpu、batch=1、local_files_only=true、固定revision、native quantileを維持します。外部cache、offline実行、license／checkpoint／package検証、既存出力の上書き拒否も単一benchmark入口と同じです。

## controlled scenario 定義

以下の controlled commands は、この README 冒頭で setup した `$totoPython` を使います。

generator → quality gate → benchmark → Toto adapter の受入契約を固定する4 track（control、target fault、target quality、covariate quality）を [`docs/toto2-controlled-scenarios.md`](../../docs/toto2-controlled-scenarios.md) に定義しています。2026-09-05にreal modelのcontrolled runを完了し、4 matrix各20/20 success、acceptance `pass`となりました。各 matrix は seed 17／29／42／73／101、horizon 15／30、context 64／120、test origin 384、5 baselines＋Toto native を共有します。

```powershell
& $totoPython tools\toto2\run_matrix.py --config examples\configs\benchmark-matrix-toto2-controlled-control.json --cache-dir C:\banto-cache\toto2
& $totoPython tools\toto2\run_matrix.py --config examples\configs\benchmark-matrix-toto2-controlled-target-fault.json --cache-dir C:\banto-cache\toto2
& $totoPython tools\toto2\run_matrix.py --config examples\configs\benchmark-matrix-toto2-controlled-target-quality.json --cache-dir C:\banto-cache\toto2
& $totoPython tools\toto2\run_matrix.py --config examples\configs\benchmark-matrix-toto2-controlled-covariate-quality.json --cache-dir C:\banto-cache\toto2
```

4本のreal matrixを実行した後、同じrepository rootからcross-matrix acceptance analyzerを実行します。実行順は **4 matrix → analyzer** です。analyzerはcell／prediction／truth／quality／provenanceを再検証し、既存outputを上書きせずに結果をpublishします。正式結果は[`docs/results/toto2-controlled-evaluation-2026-09-05.md`](../../docs/results/toto2-controlled-evaluation-2026-09-05.md)に記録しています。

```powershell
& $totoPython tools\toto2\analyze_controlled_acceptance.py --config examples\configs\toto2-controlled-acceptance.json
```

既存の small matrix は2026-09-04に実行済みで、8/8 cell success、partial 0、failed 0でした。正本と数値は[`docs/results/toto2-matrix-2026-09-04.md`](../../docs/results/toto2-matrix-2026-09-04.md)に記録しています。この実測値は既存 small matrix のもので、下記 controlled scenario の結果ではありません。合成データの結果は実設備性能や製品採用を示さず、22M、fine-tuning、seed拡大、fault slice、実設備一般化は次のgateです。
