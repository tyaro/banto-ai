# データポリシーと配置

顧客データを扱わず、合成データと利用条件を確認した公開データで研究する。公開データの選定理由と取得・変換境界は [`docs/public-dataset-survey.md`](../docs/public-dataset-survey.md) と [`docs/adr-0005-public-dataset-boundary.md`](../docs/adr-0005-public-dataset-boundary.md) を正本とする。

## Git に置いてよいもの

- リポジトリの tools で生成した synthetic data。
- license が再配布を許可する public dataset と、その source／license の記録。
- テストに必要な、顧客情報を含まない小さな fixture。
- 観測値を埋め込まず、データを識別する metadata-only manifest。

公開データを採用する場合も、Gitに置くのは source URL、DOI、license、source revision、verified_at、観測サイズ、SHA-256、アーカイブ member 情報、結果要約文書などの再現情報に限る。生成された quality report／fingerprint と raw archive、標準化済みdataset本体はGit管理外とし、raw archive はリポジトリ外の external cache、derived本体は `artifacts/public-datasets/<dataset-id>/` に置く。

## commit してはいけないもの

- 顧客または plant のデータ。
- Banto Hub または PLC からの raw export。
- credential、connection string、設備を特定できる metadata、未加工の log。
- 生成した checkpoint または大きな experiment output。

リポジトリの `.gitignore` は、よくあるデータと artifact の拡張子を backstop として除外します。ただし、レビューの代わりにはなりません。

## ローカル限定の配置

```text
datasets/
  README.md
  manifests/       versioned metadata-only manifests
  fixtures/         小さく安全な test fixture
  local/            ignore 対象の local／public data
```

顧客案件では、承認された外部 storage boundary 内にデータを置き、匿名化した `dataset_id` だけを参照します。run manifest には、出所、単位、sampling、quality flag、変換、split 境界を記録します。公開データでも raw／derivedデータ本体はGit管理せず、manifest、config、results、docsだけを追跡します。

## 公開データ source pin

第一候補は UCI MetroPT-3 です。source pin toolによる実archive検証は完了し、正本は [`manifests/metropt3-source.json`](manifests/metropt3-source.json)、手順は [`../tools/public-data/README.md`](../tools/public-data/README.md) です。アーカイブは 218,381,995 bytes、SHA-256固定済みです。公式 metadata の sampling 記載が 1 Hz／0.1 Hz で競合し、source timezone も未指定です。実timezoneは主張せず、`2020-02-21` の連続24時間は研究上UTCとして解釈します。

初期取込は完了しています。60秒の半開区間 `[start, end)`、output timestamp=bin end、analog=mean、digital=lastで、one compressorの14 signalsへ変換します。`Caudal_impulses`は除外し、`mode=unknown`とします。欠損、空bin、異常gap、timestamp逆行、nonfinite値は補間せず fail closed とし、864 / 288 / 288 samplesのchronological splitを作ります。標準化dataset生成とPublic-only quality gateは実データで合格済みですが、rolling benchmark、モデル評価は未実施です。結果は [`../docs/results/metropt3-import-2026-09-04.md`](../docs/results/metropt3-import-2026-09-04.md) を参照してください。

標準化済みdatasetの deterministic output は `source-manifest.json`、`transform-config.json`、`observations.jsonl`、`split-manifest.json`、`dataset-manifest.json`、`quality-report.json`、`fingerprint.json` の7ファイルです。Public-only quality gateはschema、UTC、interval、split、path、hash、license、timezone assumption、no-label leakageを検査し、synthetic gateとは分離します。
