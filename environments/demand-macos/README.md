# Mac用の独自需要モデル研究環境

2026-10-14、`codex/preformal-acceptance-scope` の `93836ad13154bd185e1d6a9d6dea2f7187b02f97` を基準に準備。
[Macへの引継ぎ](../../docs/research/pc-handoff-2026-10-14.md)と[current-handoff最上段](../../docs/current-handoff.md)を優先する。

2026-10-15追記: 主用途「既存店舗の将来需要予測・PSI」に対して[既存10店2015の固定評価](../../docs/results/demand-existing-stores-2015-2026-10-15.md)を一回完了。時間選択3328のjointはmean28比0.758848%改善だが暫定2%目安未達、MAE/WAPE悪化、採用0。新学習なし、評価rootは`artifacts/macos-demand-existing-stores-2015-20261015/`。

2026-10-15追記: 人の新規生成指示により、Windowsの旧artifactをコピーせず原本から入力/profile/stateを作成した。[Mac新規生成結果](../../docs/results/demand-macos-rebuild-2026-10-15.md)を優先する。新模型rootは`artifacts/macos-demand-rebuild-20261015/`。以下の旧証拠コピー案は旧Windows履歴を別途受領する場合の手順であり、現在のMac新rootを使うための必須工程ではない。

## 準備済みの範囲

- macOS 27.0.1 / Apple Silicon arm64、通常のCPython 3.14.8。
- PyTorch 2.14.0のMac arm64 wheel。CPU / float32を使用する。
- runtime依存10 packageのexact versionとMac wheel SHA-256を[lock](requirements-macos-arm64-py314.lock)に固定。各SHAはPyPIの公開metadataと照合済み。[取得元とwheel情報](wheel-provenance.json)も保存した。
- 最新模型`StatisticalFeatureMean`の架空入力1件、自己生成tensor stateの保存・`weights_only=True, map_location='cpu'`による読取りとstrict loadを確認。
- 元の需要runner、Windows memory helper、旧launcher、閉鎖済み研究artifactは変更しない。

これは新環境の接続確認である。元の研究データ・stateの転送、歴史的な評価の再実行、学習再開、研究性能の評価は含まない。

## 環境の利用

repository rootで実行する。既存`.venv`は作り直さず、そのまま使用する。

```sh
source environments/demand-macos/.venv/bin/activate
python --version
python -m pip check
python -m banto_ai smoke
```

別の新規checkoutで再構築する場合だけ、通常のCPython 3.14.8で新規venvを作り、Mac専用lockを使用する。

```sh
uv venv --python 3.14.8 --seed environments/demand-macos/.venv
py=environments/demand-macos/.venv/bin/python
"$py" -m pip install --only-binary=:all: --require-hashes -r environments/demand-macos/requirements-macos-arm64-py314.lock
"$py" -m pip install --no-build-isolation --no-deps .
"$py" -m pip check
```

このMacではeditable installの`.pth`へhidden属性が再付与され、CPythonが読み飛ばす状態を確認した。共通runtimeは通常wheelとしてinstallする方式へ変更し、`python -m banto_ai smoke`の接続を確認した。coreのsourceを変更した場合は通常wheelを再installする。研究用scriptはrepositoryのmodels/toolsからsourceを直接importする。
lockのTorchはMacの`2.14.0`で、元Windowsの`2.14.0+cpu`と同じbuildではない。数値結果や性能の一致は未検証。
NumPyはこのtensor専用環境には導入していない。Torch importのNumPy初期化警告をログへ残した。現在の接続確認はNumPy変換を使わない。

## 新しいMac用接続確認と資源計測

[check_demand_macos.py](../../tools/check_demand_macos.py)は新規rootだけを受け付け、失敗もclosure付きで残す。今回の接続結果は`artifacts/macos-demand-setup-20261014/`に閉鎖保存済み。
同じrootへ再実行しない。必要な新確認には目的を決めてfresh rootを指定する。

```sh
python tools/check_demand_macos.py --output artifacts/macos-demand-setup-NEW
```

[macos_demand_runtime.py](../../tools/macos_demand_runtime.py)はAppleの[resource.hのrusage_info_v0定義](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/resource.h)に従う`proc_pid_rusage`でcurrent physical footprintとresident sizeを取得し、Darwinの`ru_maxrss`をpeak RSS bytesとして別記する。新確認は60秒、各memory指標2GiB以下のsample checkpointを使用する。これはOSのhard capでも、Windows private bytesと同等な指標でもない。

旧`store_sales_final.private_memory()`へ代入して旧学習を再実行する経路は用意していない。新研究unitのlauncherではこのMac計測を明示的に使用し、資源契約にmetric名と上限を記録する。GPU/MPS、公式TimesFM weightsは使用しない。

## Windowsの旧研究証拠を転送する場合

元PCの`D:/develop/banto-ai`からコピーし、元PCには原証拠を残す。Windowsの`.venv`はコピーしない。

宛先repositoryはこのREADMEの2階層上。`data/`はdirectory全体を同じ相対位置へコピーする。
`artifacts/`には今回のMac確認rootが既にあるため、元PCの各rootを相対位置を維持してコピーし、同名rootがある場合はmerge・上書きを止める。
少なくとも以下の全rootと、引継ぎ書が指定する関連prep/recordsを受領する。

- `artifacts/representative-demand-training-adequacy-20261014/`
- `artifacts/representative-demand-selected-series-20261014/`
- `artifacts/representative-demand-group-selection-20261014/`
- `artifacts/representative-demand-group-selection-*`の関連prep/records。
- `artifacts/representative-demand-correction-decomposition-*`、`artifacts/representative-demand-astra-methodology-review-*`。

コピー後の読取り照合には[verify_demand_transfer.py](../../tools/verify_demand_transfer.py)を使う。模型closureはexact file set・byte数・SHAを検査し、EvidenceStoreは既存`verify_record`へ渡す。failedという原statusも維持する。自動探索・再学習・再評価・修復・cleanupはしない。

```sh
python tools/verify_demand_transfer.py artifacts/representative-demand-training-adequacy-20261014
python tools/verify_demand_transfer.py artifacts/representative-demand-selected-series-20261014
python tools/verify_demand_transfer.py artifacts/representative-demand-group-selection-20261014
```

recordsの`post-save`はその閉鎖rootを明示して検査する。元PCで記録した`root-closed.json`のSHAがある場合は、`--expected-closure-sha256`を指定してコピー元の外部pinへも照合する。指定しない場合は内部整合性の検査であり、元PCとの一致を認証しない。
旧絶対path・hash・seedは書き換えない。2017・予約31–54は移転しただけで読取り対象へ追加しない。CAREは手動取得待ちを維持する。

原データとstateはこのMacへまだコピーされていないため、研究証拠の受領と外部pin照合は未完了。次の研究は「既存店舗の将来予測」か「未学習店舗への移行」かを決め、新契約・fresh rootで進める。学習条件のgrid/seed/split追加は自動では行わない。
Windows DACL/AccessCheck/native受入は未実施、formal_permission=falseを維持する。automationは再開していない。
