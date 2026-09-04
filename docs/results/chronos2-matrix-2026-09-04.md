# Chronos-2 8条件matrix初期評価

評価日: 2026-09-04
評価状態: `8/8 success`、失敗 `0`
用途判断: `commercial-evaluation`継続。`product-candidate`へは昇格しない。

## 結論

今回の小規模matrixでは、Chronos-2は`motor_temperature`の確率予測で有望でした。温度のWISは4条件すべて6モデル中1位で、MAEもcontext 6のhorizon 1／3では1位でした。一方、`motor_current`のMAEは4条件すべてmoving-averageが最良で、Chronos-2は3位または4位でした。したがって、Chronos-2を総合的な製品候補とは判断せず、target別の価値と校正を追加検証します。

context 12がcontext 6を常に改善するわけでもありません。今回のcurrentではhorizon 1／3ともcontext 12のMAEが悪化し、temperatureでもhorizon 3のMAEが悪化しました。長いcontextを既定の改善策とは扱いません。

## 正本と再現条件

正本はGit管理対象外の次のmatrix resultです。

`artifacts/chronos2/matrix/benchmark-matrix-chronos2-small/result.json`

- 固定実行HEAD: `3f57c8500f2a746dd0fce1d02bb9eba566d47748`、clean worktree
- 軸: seeds `[17, 42]` × horizons `[1, 3]` × context lengths `[6, 12]`
- データ: `synthetic-motor-small`、2 equipment、各seed 120 observation records
- seed 17 fingerprint: `b0ce7e603eb44deb8ec11fb63bbc88869ab7c91eef0403009d2c8092e08e6c29`
- seed 42 fingerprint: `f5601fe7038a936ea5a8e4aa0c69c137e3a7e7552fd7be7410accf7350c16d29`
- 対象: `motor_current`（A）、`motor_temperature`（degC）
- 比較: Chronos-2 + 5単純baseline、合計6 models
- split: equipmentごとにvalidation 2 origins、test 2 origins
- quantile: Chronos-2はnative p10／p50／p90。p50は公式APIのpoint契約
- scenario: past-only。未来の実績値を共変量として渡していない

表の値は各seed cellのmacro summaryであり、raw predictionを全件poolして再集計した値ではありません。AとdegCを混合したaggregateの順位で採否を決めず、target別の結果を主に判断します。

## Chronos-2の正確な指標と相対順位

順位は同一target・horizon・contextにおける6 models中の順位です。MAE／WISとも小さいほど良い値です。coverageのnominal水準は80%です。

| target | horizon | context | MAE順位 | WIS順位 | MAE | RMSE | MASE | coverage | width | WIS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| motor_current | 1 | 6 | 3/6 | 4/6 | 0.09357873712348952 | 0.10366430201608005 | 0.3534070930983338 | 0.75 | 1.1584290564060211 | 0.12421927928034474 |
| motor_current | 1 | 12 | 4/6 | 4/6 | 0.1389435288047789 | 0.15302166472794693 | 0.4870236770473669 | 1 | 1.4375754594802856 | 0.14215287356694534 |
| motor_current | 3 | 6 | 3/6 | 4/6 | 0.08927573903020222 | 0.10250296270074057 | 0.3260111526742636 | 0.875 | 1.734719435373942 | 0.15183507704204982 |
| motor_current | 3 | 12 | 4/6 | 4/6 | 0.12088567491340627 | 0.14817696864360164 | 0.3978531006703799 | 1 | 1.9990430970986686 | 0.17356476477771332 |
| motor_temperature | 1 | 6 | 1/6 | 1/6 | 0.047065349975586646 | 0.05413021329178111 | 0.25863565965148216 | 1 | 0.9669468402862549 | 0.08015157267761254 |
| motor_temperature | 1 | 12 | 3/6 | 1/6 | 0.18173534655761747 | 0.21066746206583667 | 0.8543536954007667 | 1 | 0.929009199142456 | 0.12251239546203624 |
| motor_temperature | 3 | 6 | 1/6 | 1/6 | 0.14721594184366876 | 0.2157029943144696 | 0.8230665642862898 | 1 | 1.2872313658396402 | 0.13488740500386565 |
| motor_temperature | 3 | 12 | 2/6 | 1/6 | 0.3063958502044678 | 0.38368115372439704 | 1.5567673061703509 | 0.75 | 1.474074125289917 | 0.22480601783582904 |

### baselineとの勝者

- `motor_current`: 4条件すべてMAEはmoving-averageが1位。Chronos-2はMAE 3位／4位、WISは4位。
- `motor_temperature`: h1 c6とh3 c6はChronos-2がMAE 1位、h1 c12とh3 c12はHolt linearがMAE 1位。WISは4条件すべてChronos-2が1位。
- intervalはtemperature h3 c12でcoverage `0.75`、current h1 c6で`0.75`となり、nominal 80%を下回るcellがある。WIS首位だけで校正済みとは判断しない。

## Chronos-2のCPU runtime

各cellのChronos-2 warm test callにおける`p50`／`p95`です。初回loadを含むcold実行時間とは別の値です。

| seed | horizon | context | p50 (ms) | p95 (ms) | cell total (s) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 17 | 1 | 6 | 216.49309998610988 | 339.3444000030285 | 78.77301149998675 |
| 17 | 1 | 12 | 297.7221000037389 | 445.4214099911041 | 2.0782471999991685 |
| 17 | 3 | 6 | 378.507150002406 | 593.6139350043959 | 2.886316399992211 |
| 17 | 3 | 12 | 135.22414999897592 | 226.88605001603713 | 1.3796977000019979 |
| 42 | 1 | 6 | 162.44659999210853 | 259.59654001635494 | 1.7836678000167012 |
| 42 | 1 | 12 | 166.41804999380838 | 213.09418500895842 | 1.3655998000176623 |
| 42 | 3 | 6 | 124.68759999319445 | 144.60700498893857 | 1.370085000002291 |
| 42 | 3 | 12 | 228.86730000027455 | 425.1521099984529 | 2.209348400007002 |

- p50 mean `213.79575624632707 ms`、最小 `124.68759999319445 ms`、最大 `378.507150002406 ms`
- p95 mean `330.96445437840885 ms`
- process peak memory最大 `1,064,873,984 bytes`（`os.process_peak_working_set`）。これはprocess全体のhigh-water markであり、Chronos-2単独の増分メモリではない。
- seed 17／h1／c6のtotal `78.77301149998675秒`はvalidationとmodel load／初回実行を含む。残りのcell totalは`1.3655998000176623`〜`2.886316399992211秒`であり、単純合算を代表値として扱わない。

## 判断と制約

この結果は、2 seed、単一の合成generator、2 equipment、各equipmentのvalidation／test各2 origins、CPUのみの小標本です。一般性能、実設備性能、製品採用の根拠ではありません。今回のmatrixはpast-onlyであり、known-future計画値の有無による差を検証していません。

Chronos-2は固定package／checkpoint／provenanceとApache-2.0の記録を維持しますが、Bantoでの用途は`commercial-evaluation`に留めます。TimesFM 3.0のresearch-only境界も変更しません。Banto Hubへ接続する場合はread-only／shadowに限定し、PLC安全制御への自動書き込みは行いません。

## 次のゲート

1. 公開実データまたは再配布可能な実データで、単位・欠損・stale・regime・fault sliceを追加する。
2. seed、origin、horizon、contextを拡張し、context長探索を行う。
3. origin時点で確定したplanned-loadだけを使うknown-future条件とpast-only条件を同一契約で比較する。
4. p10／p50／p90のcoverage、width、WISをtarget／horizon／regime別に校正評価する。
5. 拡張した評価条件をclean savepointから再実行し、固定revision、外部cache、provenanceを再確認する。

## 参照

- [Chronos-2初期rolling benchmark](chronos2-initial-evaluation-2026-09-04.md)
- [Chronos-2評価ノート](../chronos2-notes.md)
- ローカル生成物: `artifacts/chronos2/matrix/benchmark-matrix-chronos2-small/result.json`（Git管理対象外）
