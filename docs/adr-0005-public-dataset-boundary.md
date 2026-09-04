# ADR-0005: 公開産業データの選定と境界

- Status: Accepted for research intake
- Date: 2026-09-04
- Scope: public dataset source pin、変換、評価準備

## Context

合成データだけでは、実設備の timestamp の揺らぎ、欠損、運転モード、故障報告との時間関係を検証できない。一方、公開データを無条件に Git へ取り込むと、ライセンス、サイズ、再配布条件、未来情報の漏洩を見落とす。Banto-ai は顧客データを扱わず、モデル評価結果を製品採用の根拠へ自動昇格させない必要がある。

## Decision

1. 第一候補を [UCI MetroPT-3](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset) とする。実運用 APU の多変量センサーで、1,516,948 records／15 signals、CC BY 4.0、DOI [10.24432/C5VW3R](https://doi.org/10.24432/C5VW3R) を確認できる。
2. 次候補を [UCI Condition monitoring of hydraulic systems](https://archive.ics.uci.edu/dataset/447/condition%2Bmonitoring%2Bof%2Bhydraulic%2Bsystems) とする。実油圧試験装置で2,205の60秒 cycleと状態severityを持つが、現行のrolling forecastへ変換する設計が必要である。CC BY 4.0、DOI [10.24432/C5CW21](https://doi.org/10.24432/C5CW21) を確認できる。
3. [NASA C-MAPSS](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data) はシミュレーションで、公式ページの license が `License not specified` のため採用しない。ライセンスが確定できるまで非公式mirrorも使わない。
4. MIMIIは音響異常検知の条件付き候補、AI4Iは timestamp のない合成データの補助 fixture とし、MetroPT-3の代替とはしない。

## Source pin 契約

source pin は次の順序で行い、どれか一つでも不明なら fail closed とする。

1. 公式URL、DOI、ライセンス、帰属表示、変更表示、商用利用の可否を記録し、利用条件を明示的に受け入れる。
2. 取得URL、source revision、verified_at、観測 byte size、SHA-256 を固定する。MetroPT-3は実取得アーカイブ **218,381,995 bytes**、SHA-256 **`aab991a970e58210de853bb8078ce0e63abb4d9412fdc5c79792dae3d8e1721a`** を確認済みとする。
3. ZIP等の member name、member size、member hash を検証し、source manifestへ記録する。
4. raw archive は repository 外の external cache に置き、標準化済み derived data は repository 内の Git 管理外 `artifacts/public-datasets/` に置く。Gitには source manifest、transform config、schema、code、tests、結果要約文書など再現情報だけを置く。

MetroPT-3の source pin は実装済みで、実archiveを外部cacheからCLI検証済みである。検証結果は `status=cached_verified`、`verification_status=verified` とする。正本は [`datasets/manifests/metropt3-source.json`](../datasets/manifests/metropt3-source.json)、手順は [`tools/public-data/README.md`](../tools/public-data/README.md) と [`tools/public-data/prepare_metropt3.py`](../tools/public-data/prepare_metropt3.py) とする。この download／verify に続く標準化取込とPublic-only quality gateも実データで完了したが、benchmark、モデル評価は未実施である。結果は [`docs/results/metropt3-import-2026-09-04.md`](results/metropt3-import-2026-09-04.md) に記録する。

## Data contract

MetroPT-3の公式説明には1 Hzと0.1 Hzのsampling記載があり一致しない。raw timestamp を正本として実測deltaを記録し、sampling intervalを設定へ決め打ちしない。source timezoneも未指定で実timezoneは主張しないが、研究上は `2020-02-21` の連続24時間をUTCと解釈し、`timezone_assumption` をprovenanceに必須化する。

初期変換は、標準ライブラリの streaming importer、60秒の半開区間 `[start, end)`、output timestamp=bin end、analog mean、digital last、補間なし fail closed とする。14 signalsを対象とし、`Caudal_impulses`は除外、one compressor、`mode=unknown`とする。`2020-02-21` の連続24時間を研究上UTCとして扱い、chronological splitを864 / 288 / 288 samplesで作成済みである。欠損、空bin、時刻逆行、nonfinite値は停止し、未来のactual、failure report、RULはorigin時点で利用可能な known-future ではない。標準化済み本体は `artifacts/public-datasets/<dataset-id>/` に生成しGit管理しない。

出力は source-manifest、transform-config、observations、split-manifest、dataset-manifest、quality-report、fingerprint の7つのdeterministic filesとする。Public-only quality gateはschema、UTC、interval、split、path、hash、license、timezone assumption、実測cadence、no-label leakageを検査し、既存synthetic gateとは分離する。実データの取込結果は [`docs/results/metropt3-import-2026-09-04.md`](results/metropt3-import-2026-09-04.md) に記録する。

## Consequences

公開データの再現性とライセンス判断を説明しやすくなる。rawをGitに入れないため、初回取得には外部cacheと利用者側のライセンス確認が必要になる。MetroPT-3のメタデータ不一致を明示する分、最初の評価までに importer／quality gate の作業が増えるが、暗黙の補間や時間漏洩を防げる。

モデル比較は同一データ契約の同一条件に限定する。合成結果と公開実データ結果を数値で直結しない。Banto Hubはread-only／shadowのままで、AIからPLCや安全制御へのwrite pathは作らない。Chronos-2の用途は引き続き `commercial-evaluation`、TimesFM 3.0は `research-only` とする。

## References

- [UCI MetroPT-3](https://archive.ics.uci.edu/dataset/791/metropt%2B3%2Bdataset)
- [UCI Hydraulic Systems](https://archive.ics.uci.edu/dataset/447/condition%2Bmonitoring%2Bof%2Bhydraulic%2Bsystems)
- [NASA C-MAPSS](https://data.nasa.gov/dataset/cmapss-jet-engine-simulated-data)
- [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
