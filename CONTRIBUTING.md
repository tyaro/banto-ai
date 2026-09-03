# 開発手順

## Phase 0の範囲

Phase 0は研究を再現可能にする基盤の実装です。標準ライブラリ中心の共通型、JSON Schema manifest、license gate、合成fixture、last-value baseline、repository safety guardを対象にします。

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
