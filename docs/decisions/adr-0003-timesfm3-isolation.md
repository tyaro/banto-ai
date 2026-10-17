# ADR-0003: TimesFM 3の依存・実行隔離

## 状態

採用。adapter境界とfake backend testsを実装し、専用Windows CPU環境で2回の実モデルsmokeを完了しています。

## 決定

TimesFM 3.0はcore runtimeへ組み込まず、専用venvに隔離したoptional backendとして扱います。`banto_ai` coreは標準ライブラリのみを維持し、`numpy`、`timesfm3`、`torch`はofficial backendが実際に呼ばれた時だけ遅延importします。

TimesFM 3.0のsource codeはApache-2.0ですが、pretrained weightsは`timesfm-non-commercial-license-v1.0`です。このため用途を`research-only`かつnon-productionに限定し、製品artifact、顧客PoC、本番系へ昇格しません。実行する場合もread-onlyのoffline評価または非本番shadow評価に限り、PLC、Banto Hub、recipe、control parameterへのwrite pathを設けません。

packageは`timesfm[torch]==3.0.0`をtop-levelで固定し、wheel SHA-256、checkpoint、immutable revisionを来歴として検証します。この入力は完全なtransitive lockとは呼びません。Windows amd64／CPython 3.14.0／CPUのexact-version lockを作成済みですが、hash-pinnedなsupply-chain lockは未作成です。Torch／CUDAとplatform固有依存の衝突をcoreから隔離し、checkpointとmodel cacheはGit外に保存します。adapterの既定は`local_files_only=True`とします。

## 理由

- coreのclean checkout、CI、baseline評価をML依存なしで維持できる。
- TimesFM固有APIを共通`Forecaster`境界内へ閉じ込め、fake backendだけで入力整列、quantile、出力形状、license gateを検証できる。
- Torch／CUDA等の大きな依存とplatform差を、他modelやcoreの依存解決から分離できる。
- 非商用weightsが制御系または製品経路へ混入することをfail-closedにできる。

## 現在の実測状況

adapter境界、official API wrapper、manifest検証、fake backend testsに加え、専用Windows CPU環境で2回の実モデルsmokeを実行済みです。latency、Peak RSS、単一synthetic window上の指標を記録しましたが、実設備性能、広範な精度、calibration、throughputは未評価です。詳細は`docs/results/timesfm3-cpu-smoke-2026-09-04.md`を参照してください。

## 継続事項

TimesFM 3.0だけを採用候補とせず、Chronos-2、Toto 2.0、Granite TTM、TimesFM 2.5、統計baselineなど商用利用可能な代替候補との比較を継続します。Phase 2の完了は、同じdataset、window、horizon、metric、hardware記録で必要な候補を実測比較し、gate条件を満たした時だけ判断します。
