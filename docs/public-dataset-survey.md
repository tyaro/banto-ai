# 公開産業時系列データ調査・選定

策定日: 2026-09-04

## 結論

最初の公開実データ候補は、実運用の鉄道車両用空気圧縮機を記録した UCI **MetroPT-3** とする。予測、異常検知、設備別適応の三つを同じデータ境界で検討でき、CC BY 4.0 の再利用条件も確認できるためである。次候補は実油圧試験装置の UCI **Condition monitoring of hydraulic systems** とする。NASA **C-MAPSS** はシミュレーションデータで、公式掲載のライセンスが `License not specified` であるため、Banto の fail-closed 方針では現時点で採用しない。

この選定はモデル採用や実データ評価の完了を意味しない。MetroPT-3の **source pin は実装済み・実archive検証済み** で、検証結果は `status=cached_verified`、`verification_status=verified` である。正本manifestは [`datasets/manifests/metropt3-source.json`](../datasets/manifests/metropt3-source.json)、取得・検証CLIは [`tools/public-data/README.md`](../tools/public-data/README.md) と [`tools/public-data/prepare_metropt3.py`](../tools/public-data/prepare_metropt3.py) に記録する。変換、quality check、rolling benchmark、fault slice、モデル比較は未実施であり、次の保存点で別途実施する。

## 比較

| データセット | 実体・規模 | ラベル／時系列の特徴 | ライセンス | Banto 判断 |
| --- | --- | --- | --- | --- |
| [UCI MetroPT-3](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset) | 実運用の鉄道車両 APU／空気圧縮機、1,516,948 records、15 signals | 多変量センサー、故障報告の時間区間、incremental training の余地。公式ページ内で 1 Hz と 0.1 Hz の記載が競合 | CC BY 4.0、[DOI 10.24432/C5VW3R](https://doi.org/10.24432/C5VW3R) | **第一候補**。生の時刻を保持して変換契約を先に固定 |
| [UCI Condition monitoring of hydraulic systems](https://archive.ics.uci.edu/dataset/447/condition%2Bmonitoring%2Bof%2Bhydraulic%2Bsystems) | 実油圧試験装置、2,205 cycles、各 60 秒 | 圧力・流量・温度等の cycle array。部品状態とseverityがあり異常検知向きだが、現行 rolling forecast へ変換が必要 | CC BY 4.0、[DOI 10.24432/C5CW21](https://doi.org/10.24432/C5CW21) | **次候補**。source pin 後に cycle-to-window 設計 |
| [NASA C-MAPSS](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data) | NASAのジェットエンジン**シミュレーション**、複数engine trajectory | train/test、operating settings、sensor、RUL。現実の設備観測ではなく、公式掲載は `License not specified` | 公式公開ページで許諾条件を確定できない | **採用見送り**。非公式mirrorを使わない |
| [MIMII](https://zenodo.org/records/3384388) | 工場背景音を含む valve／pump／fan／slide rail、100.2 GB | 8ch音響、正常／異常。音響異常検知の補助候補だが、常時TSFM入力ではない | CC BY-SA 4.0 | 条件付き研究候補。容量・share-alike・プライバシーを別審査 |
| [UCI AI4I 2020](https://archive.ics.uci.edu/dataset/601/ai4i%2B2020%2Bpredictive%2Bmaintenance%2Bda) | 10,000 recordsの合成 predictive maintenance データ | sensorとfailure modeはあるが timestamp がなく、real forecasting の主データにはしない | CC BY 4.0 | 合成 fixture の比較用。公開実時系列の代替にはしない |

ライセンスの判断はデータセットごとに行う。[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) は商用を含む共有・改変を許すが、帰属表示、ライセンスリンク、変更表示を要求する。[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) は同じく商用利用を許す一方、改変物にも同一ライセンス条件が及ぶ。Banto の MIT License が外部データやモデルの条件を上書きすることはない。

## MetroPT-3 の確認事項

### source pin の証跡

主データの公式表示は CSV 208.2 MB である。実取得・検証済みアーカイブは **218,381,995 bytes**、SHA-256 は **`aab991a970e58210de853bb8078ce0e63abb4d9412fdc5c79792dae3d8e1721a`** である。memberも固定し、`Data Description_Metro.pdf` は SHA-256 `b00fac0e8899854078309bef4adaa480d82ecf14dc81c5097c3646973e824127`、`MetroPT3(AirCompressor).csv` は SHA-256 `db30ccb4ea402e3c8bf2c99db06e288d4f2a772f6928f9dbe26a920d69793e24` である。source revision、license、verified_atを [`datasets/manifests/metropt3-source.json`](../datasets/manifests/metropt3-source.json) に固定し、未知の値は fail closed とする。

取得した raw CSV の観測は次のとおりである。

- 行数: 1,516,948
- timestamp: `2020-02-01 00:00:00` ～ `2020-09-01 03:59:50`
- timestamp は単調増加
- 主な差分: 10 秒 1,337,521、9 秒 128,277、12 秒 38,321
- 最大 gap: 172,918 秒、20 秒超の gap: 351
- 欠損セル: 0

公式ページは sampling を一方で 1 Hz、variable information で 0.1 Hz と説明している。この不一致を理由に、1 Hzへ決め打ちしたり、欠損区間を暗黙に補間したりしない。source の timestamp を正本とし、delta、gap、欠損を quality report に残す。

source が timezone を指定していないため、UTC と断定しない。Banto の設定では `source_timezone: unspecified` と `timezone_assumption` を明示し、UTCへ変換する場合は変換者、変換規則、実行時刻、入力 hash を provenance に保存する。

### 初期変換の設計

次の保存点で、標準ライブラリの streaming importer を使って小さい連続区間を検証する。

1. `2020-02-21` の連続 24 時間候補を raw timestamp から再検証する。
2. 1 分 bin の終端 timestampへ集約する。analog は mean、digital は last とし、bin幅と境界を設定へ固定する。
3. 観測のない bin、異常な gap、timestamp の逆行は補間せず fail closed とする。
4. 時系列順の train／validation／test を作り、origin より未来の actual、failure report、RUL を known-future covariate にしない。
5. source manifest、quality report、変換設定、入力／出力 hash のみを追跡し、raw archive と大きな derived data は外部 cache／artifact 領域に置く。

この保存点では importer と quality check の受入れまでを対象とし、Chronos-2、TimesFM 3.0その他のモデル評価完了とは扱わない。モデルを比較するときは、同じ window、origin、horizon、target、hardware、metric の結果だけを比較する。今回の合成データ結果と MetroPT-3 の数値を直接比較しない。

## 研究・運用境界

- 顧客設備、Banto Hub、PLC からの raw export は公開データであってもこのリポジトリへ入れない。
- raw archive、変換済み大規模データ、checkpoint、benchmark artifact は repository 外の明示的な cache／artifact boundary に置く。
- Banto Hub 連携は read-only または shadow とし、AIからPLC値、interlock、非常停止、PIDへ書き込まない。
- MetroPT-3 の failure report は事後情報である。評価時点で利用可能だったかを分け、未来の故障区間を入力特徴量へ漏洩させない。
- 小標本、単一データ源、synthetic fixture との非同値性を結果に併記する。Chronos-2 は引き続き `commercial-evaluation`、TimesFM 3.0 は `research-only` とする。

## 参照

- [UCI MetroPT-3 Dataset](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)
- [UCI Condition monitoring of hydraulic systems](https://archive.ics.uci.edu/dataset/447/condition%2Bmonitoring%2Bof%2Bhydraulic%2Bsystems)
- [NASA C-MAPSS Jet Engine Simulated Data](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data)
- [MIMII Dataset (Zenodo)](https://zenodo.org/records/3384388)
- [UCI AI4I 2020 Predictive Maintenance Dataset](https://archive.ics.uci.edu/dataset/601/ai4i%2B2020%2Bpredictive%2Bmaintenance%2Bda)
- [Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
- [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
