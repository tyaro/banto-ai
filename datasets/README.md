# データポリシーと配置

## Git に置いてよいもの

- リポジトリの tools で生成した synthetic data。
- license が再配布を許可する public dataset と、その source／license の記録。
- テストに必要な、顧客情報を含まない小さな fixture。
- 観測値を埋め込まず、データを識別する metadata-only manifest。

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
