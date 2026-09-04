# データポリシーと配置

顧客データを扱わず、合成データと利用条件を確認した公開データで研究する。公開データの選定理由と取得・変換境界は [`docs/public-dataset-survey.md`](../docs/public-dataset-survey.md) と [`docs/adr-0005-public-dataset-boundary.md`](../docs/adr-0005-public-dataset-boundary.md) を正本とする。

## Git に置いてよいもの

- リポジトリの tools で生成した synthetic data。
- license が再配布を許可する public dataset と、その source／license の記録。
- テストに必要な、顧客情報を含まない小さな fixture。
- 観測値を埋め込まず、データを識別する metadata-only manifest。

公開データを採用する場合も、Gitに置くのは source URL、DOI、license、source revision、verified_at、観測サイズ、SHA-256、アーカイブ member 情報、品質結果などの metadata に限る。raw archive、変換済み大規模データ、benchmark artifact はリポジトリ外の external cache／artifact 領域に置く。

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

顧客案件では、承認された外部 storage boundary 内にデータを置き、匿名化した `dataset_id` だけを参照します。run manifest には、出所、単位、sampling、quality flag、変換、split 境界を記録します。

## 公開データ source pin

第一候補は UCI MetroPT-3 です。source pin toolによる実archive検証は完了し、正本は [`manifests/metropt3-source.json`](manifests/metropt3-source.json)、手順は [`../tools/public-data/README.md`](../tools/public-data/README.md) です。アーカイブは 218,381,995 bytes、SHA-256固定済みです。公式 metadata の sampling 記載が 1 Hz／0.1 Hz で競合し、source timezone も未指定なので、raw timestamp の delta と gap を測定し、UTCや固定周期を暗黙に仮定しません。

初期の次保存点では `2020-02-21` の連続24時間を再検証し、1分 bin（analog=mean、digital=last）へ変換する streaming importerを作ります。空bin、異常gap、timestamp逆行は補間せず fail closed とします。source pinは取得・ハッシュ検証まで完了していますが、変換・quality check・rolling benchmark・モデル評価は未実施です。
