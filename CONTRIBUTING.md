# 開発手順

## Savepoint 0〜2の範囲

Savepoint 0/1は研究を再現可能にする基盤、Savepoint 2は標準ライブラリだけの共通benchmark runnerと統計baselineの実装です。共通型、JSON Schema manifest、license gate、合成fixture、rolling-origin、validation-only分位点校正、repository safety guardを対象にします。

次は対象外です。

- TimesFM、Chronos、Toto、TTMなどのML packageやcheckpointの導入
- 顧客データ、credential、PLC接続
- AIからPLC／Banto Hubへのwrite path
- 本番SLAや自動promotion

## Windowsでの実行

PowerShellでrepository rootに移動して実行します。Phase 0のsmoke testは外部packageをinstallせずに動作します。

```powershell
python --version
python tools/smoke.py
python tools/safety_check.py
python -m compileall -q src tests tools
python -m unittest discover -s tests -t . -v
```

Phase 1のsynthetic datasetを確認する場合は、次を実行します。

```powershell
python tools/data-generator/generate.py --config examples/configs/synthetic-motor-small.json --output artifacts/generated/synthetic-motor-small
python tools/data-generator/check_quality.py --dataset artifacts/generated/synthetic-motor-small
python tools/evaluator/run_benchmark.py --config examples/configs/benchmark-small.json
```

これはsrc layoutのclean checkoutから実行する標準手順です。`python -m banto_ai ...` を使う場合だけ、先に `python -m pip install -e . --no-deps` を実行してください。

generatorはseedとconfigからcanonicalなJSON／JSONLを生成します。JSONはUTF-8、sorted keys、compact separators、非有限値なし、JSONLはequipment設定順・timestamp順です。同じseed／configの出力はbyte-for-byte同一になります。event intervalの境界は `[start,end)` で、timestampはUTCかつequipmentごとにstrictly increasingです。

`check-quality` はduplicate／out-of-order timestamp、catalog値に対するsampling interval不一致、unit mismatch、quality key/status不正、non-finite value、eventの範囲・重複・参照不正、chronological splitのtrain／validation／test完全被覆・連続性・record_count、cross-equipment splitの重複・漏れ・record_count、generator configとのtimestamp／regime／event／summaryのsemantic consistency、fingerprint改変・欠落・未知entry、future leakageの最小条件を検査します。検査順序は観測・split・event構造、generator config照合の後にfingerprintとし、原因が分かるエラーで停止します。

benchmark runnerはdatasetを最初に`check_dataset`へ通し、split境界を越えないrolling-originでbaselineを比較します。出力の`result.json`、`predictions.jsonl`、`summary.md`は新規ディレクトリへatomic作成し、既存出力を上書きしません。合成データの結果は実設備性能を示しません。

生成物は既定でGit無視領域に置かれ、既存出力の上書きは拒否されます。観測値とground-truth eventは別ファイルです。合成データは実設備を代表するものではなく、顧客データを入力・commitしてはいけません。

Python 3.12以上が対象です。ローカルのPython 3.14でも同じコマンドを実行してください。

packageとして使う場合だけ、外部依存なしのeditable installを行えます。

```powershell
python -m pip install -e . --no-deps
python -m banto_ai smoke
```

## Planned model environments

core runtimeの依存は標準ライブラリのみです。Phase 0ではinstallableなmodel extraを定義しません。モデルごとの環境はadapter実装時に分離します。

| 環境 | planned package | 方針 |
| --- | --- | --- |
| Chronos-2 | chronos-forecasting | 商用候補。固定version／checkpoint／license manifestを必須にする |
| TimesFM 3.0 | timesfm | `research-only`。product-candidateへ昇格しない |
| Toto 2.0 | toto-models | 小型版からhardware実測する |
| Granite TTM／TSPulse | granite-tsfm | edge／異常検知候補として別環境で評価する |
| 評価補助 | fev | 採用判断後に追加する |

外部packageのdownload／installは、明示的な研究作業として個別に行い、Phase 0 CIでは実行しません。最初のadapter実装時にpackage／checkpointのversion pinとmodel environmentごとのlockを必須にします。モデルを追加するときは、まずadapter、manifest、license gate、再現手順を更新してください。

core外部依存がゼロのため、現時点ではdependency lockを作成しません。外部依存を導入する時点で、coreへ混ぜずmodel environmentごとにlockを管理します。

formatter／linterもPhase 0では導入しません。core外部依存ゼロを優先し、標準ライブラリの`compileall`、`unittest`、安全検査をCIで実行します。最初のdevelopment dependencyを導入するPhaseでformatter／linterをversion pinし、model environmentと同様にlockへ固定します。

## データと安全

顧客データはrepositoryへ追加しません。公開データを使う場合も、再配布条件と出所をmanifestに記録します。checkpoint、credential、production／customer pathはsafety guardで拒否されます。

実験コードはread-only／shadowを前提とし、PLC値、interlock、recipe、安全上限を書き込む経路を作りません。
