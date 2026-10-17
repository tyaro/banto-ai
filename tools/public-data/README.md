## 現在の実行範囲（2026-10-17）

[現在の引継ぎ](../../docs/current-handoff.md)と[整理結果](../../docs/results/research-consolidation-2026-10-17.md)を優先する。停止したRust内部調査・不採用拡張・単発の報告生成はテキスト資料へ退避した。ポインタ追跡を再開しない。

rust_r1_compare.py / rust_r1_python_reference.py / rust_r1_metadata.py / rust_r1_publish_preparation.pyは既存比較とR2Pから使うため残している。後者のvalidate_rootは閉鎖検証の共通helperであり、旧publicationのmainを再走する指示ではない。旧R1/R2Pのphase toolは当時のsource pinsとfresh rootを前提とし、現在のlockや退避後の構成で同じrunを再生成しない。固定Python参照は保存済みbytesを使う。

以下の取得・準備は完了済みの手順記録である。新取得や既存closed rootへの反復実行は現在の整理作業に含めない。

---

## Macの産業データ準備（2026-10-16）

[取得・準備結果](../../docs/results/industrial-data-macos-intake-2026-10-16.md)と[原本index](../../datasets/manifests/industrial-macos-source-index-20261016.json)が現在の入口。原本は同workspaceのrepository外cache、新入力はartifacts/public-datasetsに保管。既存closed rootへの再実行・上書きは禁止。

- MetroPTは既存importerとmodels/mini-transformer/data.py::load_fixed_dayへ接続済み。
- 油圧はindustrial_data.py::hydraulic_window(root, cycle, origin, context=128, horizon=32, split=...)を使う。rootはartifacts/public-datasets/hydraulic-macos-20261016。cycle境界・splitを検査し、条件labelを入力へ入れない。
- XJTUの完成rootはartifacts/public-datasets/xjtu-sy-macos-20261016-7zip。全原本・member一覧と、3軸受の8特徴量JSONLがある。raw波形は連続結合しない。macos_industrial_prepare.pyのlibarchive版XJTUモードは失敗を保持した履歴で、今後はmacos_xjtu_7zip_prepare.pyの公式7-Zip経路を参照する。
- macos_industrial_fetch.pyはHTTPS取得/source pin、macos_industrial_run.pyとv2はfresh stdio/exit記録、macos_industrial_readback.pyは保存値の確認用。これらの完了済み処理を同じrootへ反復しない。

この準備は学習・予測・性能採点を実行しない。以下は従来MetroPT取込仕様。

---

# MetroPT-3 公開データ取込

MetroPT-3の取得元と再配布可能性を固定し、取得済みarchiveを検証するための最小ツールです。sourceのraw archiveはGitへ追加せず、repository外のcacheで管理します。core importは標準ライブラリだけで、外部通信は明示的な準備コマンドを実行した場合に限ります。

## 準備

`--accept-cc-by-4.0` を付けない限り、cache作成・ネットワークアクセス・ダウンロードは開始しません。cacheには利用者が用意した repository 外の `<external-cache>` を指定します。

```text
python tools/public-data/prepare_metropt3.py --cache-dir <external-cache>\public\metropt3 --accept-cc-by-4.0
```

既定manifestは[`datasets/manifests/metropt3-source.json`](../../datasets/manifests/metropt3-source.json)です。source URL、archive filename、archive size/SHA-256、ZIPの全member、member size/SHA-256、UCIのdataset facts、CC-BY-4.0、attribution、source revision、`verified_at`を固定しています。URLやfilenameをCLIから差し替えることはできません。実archiveは `status=cached_verified`、`verification_status=verified` で検証済みです。

## 検証と安全境界

- cacheはrepository外の既存または作成可能な通常directoryだけを受け付けます。
- archiveが存在する場合は、symlinkやdirectoryを拒否し、archive全体、ZIP CRC、member集合、member size、member SHA-256を検証します。
- archiveがない場合は同じ外部cache内のunique temporary fileへstreamし、検証完了後に既存targetを置換しないatomic publishを行います。途中失敗時は自分のtemporaryだけを削除し、partial archiveは公開しません。
- 既存archiveの検証失敗時に再ダウンロードして上書きすることはありません。修正は別cacheまたは明示的な手動退避後に行います。
- ZIPのduplicate member、extra/missing member、path traversal、壊れたCRC、member hash不一致はfail closedです。展開処理は行いません。
- 出力JSONは実行時のarchive pathを含みますが、tracked manifestにはローカル絶対pathを記録しません。

## 取込の出力境界

標準化済み dataset は repository 内の `artifacts/public-datasets/<dataset-id>/` に生成します。このディレクトリは Git 管理外です。raw archive本体とderived data本体はGitへ置かず、追跡対象はsource manifest、transform config、schema、code、tests、quality／result文書などの再現情報だけです。顧客設備データは禁止です。

importer の実装は `tools/public-data/import_metropt3.py`、必須引数は `--cache-dir` と `--accept-cc-by-4.0`、任意引数は `--config` です。固定設定の出力先は `artifacts/public-datasets/metropt3-public-2020-02-21` です。

## MetroPT-3 変換契約

- 対象は one compressor、14 signals。`Caudal_impulses` は集約の意味論が未確定のため除外する。
- source timezone は不明だが、研究上は対象区間 `2020-02-21` の連続24時間を UTC と解釈する。これは分析上の仮定であり、実際の設備 timezone を主張しない。
- 60秒の半開区間 `[start, end)` に集約し、output timestamp は bin end とする。analog は mean、digital は last とする。
- 補間はしない。欠損、空bin、時刻逆行、nonfinite値は fail closed とする。
- `mode` は `unknown` とする。未来のactual、failure report、RULを known-future として渡さない。
- chronological split は 864 / 288 / 288 samples（train / validation / test）とする。

deterministic output は次の7ファイルとする。

```text
source-manifest.json
transform-config.json
observations.jsonl
split-manifest.json
dataset-manifest.json
quality-report.json
fingerprint.json
```

## Public-only quality gate

既存 synthetic quality gate と分離した Public-only gateを実装し、実データでPASSを確認しました。schema、UTC timestamp、60秒 `[start, end)` interval、14 signal／path、split 864/288/288、archive／member hash、license／attribution、timezone assumption、実測cadence、nonfinite／missing／empty-bin、no-label leakageを検査し、失敗時はstandardized datasetをpublishしません。取込結果は [`../../docs/results/metropt3-import-2026-09-04.md`](../../docs/results/metropt3-import-2026-09-04.md) に記録し、モデルbenchmarkは次savepointです。
