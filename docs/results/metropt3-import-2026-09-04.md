# MetroPT-3 取込・品質ゲート結果（2026-09-04）

## 結論

UCI MetroPT-3 の固定済みアーカイブから、`2020-02-21` の連続24時間候補を標準化し、Public-only quality gate を通過させた。これは取込基盤の検証結果であり、rolling benchmark、モデル性能、実設備への一般化を示す結果ではない。

取得元は [UCI MetroPT-3](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)、DOI は [10.24432/C5VW3R](https://doi.org/10.24432/C5VW3R) である。リポジトリは MIT、データセットは UCI が示す CC BY 4.0 であり、別のライセンスとして扱う。

## 再現方法

raw archive はリポジトリ外のキャッシュに置く。利用条件の受入れを明示して次を実行する。

```powershell
python tools/public-data/prepare_metropt3.py --cache-dir <external-cache>\metropt3 --accept-cc-by-4.0
python tools/public-data/import_metropt3.py --cache-dir <external-cache>\metropt3 --accept-cc-by-4.0
python tools/data-generator/check_quality.py --dataset artifacts/public-datasets/metropt3-public-2020-02-21
```

importer は固定 URL、アーカイブ hash、ZIP member hash、CSV header を検証し、ZIPを展開せず streaming 読込する。標準化済み本体は `artifacts/public-datasets/metropt3-public-2020-02-21/` に生成されるが、raw／derived data 本体は Git 管理しない。

## 入力と変換契約

| 項目 | 実績 |
| --- | --- |
| アーカイブ | 218,381,995 bytes |
| アーカイブ SHA-256 | `aab991a970e58210de853bb8078ce0e63abb4d9412fdc5c79792dae3d8e1721a` |
| raw window | `[2020-02-21 00:00:00, 2020-02-22 00:00:00)` |
| timezone | source は不明。研究上 UTC と解釈し、実 timezone は主張しない |
| 入力行 → 出力行 | 8,716 → 1,440 |
| 設備・信号 | compressor 1台、14 signals（`Caudal_impulses` は除外） |
| resampling | 60秒 `[start,end)`、出力時刻は bin end |
| 集約 | analog=mean、digital=last、補間なし |
| known-future | なし。failure report／label は入力にしない |

source timestamp は元の naive 値を使った。対象 window の実測 cadence は、先頭 `2020-02-21 00:00:03`、末尾 `2020-02-21 23:59:53`、delta 最小9,000 ms、最大10,000 ms、9,000 ms が760回、10,000 ms が7,955回だった。各 bin の入力行数は6〜7件である。UCI公式ページ内の1 Hz／0.1 Hz記載の競合は解消と断定せず、この window の測定結果として保存した。

## 出力と品質

出力時刻は `2020-02-21T00:01:00Z` から `2020-02-22T00:00:00Z` までで、split は次の通りである。benchmark の行indexも実際に検証した。

| split | 半開区間 | 行数 | benchmark index |
| --- | --- | ---: | --- |
| train | `[00:01, 14:25)` | 864 | `(0, 864)` |
| validation | `[14:25, 19:13)` | 288 | `(864, 1152)` |
| test | `[19:13, 翌日00:01)` | 288 | `(1152, 1440)` |

Public-only quality gate は PASS。empty bin、missing cell、nonfinite value、60秒超の大きなgapはいずれも0で、UTC timestamp、60秒間隔、signal role／unit、split coverage、source/config identity、license、path、fingerprint、label／known-future leakageを検査した。

成果物の dataset fingerprint は `e6210e4e48e05c025fc8895ddeddf0c53a49dc53fd1c2f49e8c3272a3c7b37b0`、`observations.jsonl` の SHA-256 は `d74b53979a051270f045265ccce3a582f3164500f8c7d3a8cf6940ce9a1a5077`、`quality-report.json` の SHA-256 は `27639496534ef921b1efecd3e37bef15935d4bb72568e4de794d4b06a441bfcd` である。

## 限界と次の工程

今回は normal 候補の24時間を対象にした取込・品質検証であり、故障 slice、欠損／stale slice、長期 incremental training、モデル性能、実設備全体の代表性を評価していない。次は同じ dataset fingerprint、同じ split、同じ target／horizon 契約で、統計 baseline、Chronos-2、TimesFM 3.0を比較する。TimesFM 3.0のライセンス境界と Chronos-2 の評価区分は既存のモデル文書に従い、数値を合成データ結果と直接比較しない。
