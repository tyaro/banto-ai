# event-aware anomaly evaluation v0.2 failure diagnostics 結果

- 実施日: 2026-09-06
- replay code revision: `cecc2a0fc057c7d5f43be07a53c88ce97595c1ab`（clean）
- artifact code revision: `15a0f60433703c32a1bfa989f7f779c6828a1096`（clean）

## 結論

v0.2 の正式120-cell artifactに対するfailure diagnosticsをread-only replayし、D2-Bの固定出力へ正式公開した。結果は`status=complete`、`run_status=complete`、`engineering_status=pass`、`performance_status=not_evaluated`、`exploratory_only=true`、`promotion_eligible=false`である。

ここでいうengineering passは、入力artifact、provenance、固定計算、ledger、aggregate、reconciliation、schemaおよび公開物の整合性を通過したことを示す。性能合格を意味しない。diagnosticsはcanonicalな`detected`を保存したまま因果的supportを別に検証し、240件すべてで`event_causal_support_qualified=false`だった。post-hocにthresholdやmodelのwinnerを選ばず、今回の結果は後続v0.3 preregistrationの仮説材料だけに使う。

これはevent-aware anomaly baselineのfailure diagnosticsであり、TimesFM3の性能結果ではない。synthetic offline dataだけを使用し、顧客データ、ネットワーク、PLC／制御システム、Banto Hubへのwrite、checkpoint／weightsは使用していない。

## 実行・CI境界

正式replayにはcleanな`cecc2a0fc057c7d5f43be07a53c88ce97595c1ab`を使用し、入力artifactに記録されたcleanなartifact code revision `15a0f60433703c32a1bfa989f7f779c6828a1096`との固定compatibilityを検証した。

[GitHub Actions run 33997236009](https://github.com/tyaro/banto-ai/actions/runs/33997236009)はPython 3.12が6分44秒、Python 3.14が7分4秒で成功した。これはコードの検証であり、CIが正式artifactを生成したことを意味しない。正式artifactのreplay、診断結果生成、公開および独立監査は固定したローカル境界で実施した。

## 入出力artifact

### 入力

`artifacts/anomaly-multiseed-v02`をread-onlyで検証した。

- regular files: 1,443
- directories: 245
- total file bytes: 205,890,449
- reparse points: なし
- inventory SHA-256: `2a4a62332c1c15c48b077aa59dbbccae01559558df162d5d1484aa1ae345af0e`

### 出力

`artifacts/anomaly-multiseed-v02-diagnostics-v01`には、次の3つのregular non-reparse filesだけが存在する。staging残置は0件だった。

| file | bytes | SHA-256 |
| --- | ---: | --- |
| `result.json` | 7,536,175 | `308b85af70e611e1817b36782c3baa2b7a43d39e24ab6cd3dacb9019bb1a87cb` |
| `summary.md` | 919 | `dd3ca61a94f5061d306c3e16ec254826ab5bd1d96e9aa149e7988460eb6f3a73` |
| `.complete` | 256 | `4c99708781e0bee8e59d723c53a8f8470843eb1127c031a77b4f9d56fb0679a8` |

## 固定件数

| 項目 | 件数 |
| --- | ---: |
| cells | 120 |
| seed clusters | 10 |
| eligible incident windows | 240 |
| incident points | 1,680 |
| score availability source points | 172,800 |
| availability rows | 5,760 |
| calibration rows | 5,760 |
| clean source alert episodes | 222 |
| clean equipment alert episodes | 222 |

## incident diagnostics

machine faultは120件中0件、sensor faultは120件中9件がcanonicalに`detected=true`だった。ただしsensor faultの9件はすべて`pre_event_support=true`であり、event開始後だけでpersistence条件を満たした検知ではない。`event_causal_support_qualified`はmachine／sensorを合わせた240件すべてで0件だった。

固定thresholdを超えるevent window内の最大連続数は全件1以下で、detectorの`persistence=2`に届かなかった。

| event class | run 0 | run 1 | run 2以上 |
| --- | ---: | ---: | ---: |
| machine fault | 10 | 110 | 0 |
| sensor fault | 0 | 120 | 0 |

offset 0ではmachine faultが110/120、sensor faultが120/120でthresholdを超えたが、offset 1では両classとも0/120だった。sensor faultのcanonical detection 9件は、offset -1とoffset 0の連続に依存する。offset 3は両classとも120/120が`previous_event_overlap`で除外された。したがってcanonicalな9 detectionsは記録として保持する一方、event開始後の因果的検知根拠とは扱わない。

## clean false alert diagnostics

clean source alert episodesとclean equipment alert episodesはそれぞれ222件だった。source alertをmode別に集計すると次のとおりである。

| mode | source alerts |
| --- | ---: |
| startup | 89 |
| cooldown | 55 |
| high_load | 33 |
| stopped | 23 |
| nominal | 22 |

2つのvibration signalが合計134/222件を占めた。mode entryからのoffsetでは、offset 2が66件、offset 3が22件だった。この偏りはmode-entry／phase条件を後続比較候補に含める根拠にはなるが、ここでは変更方式やwinnerを採用決定しない。

## availability diagnostics

温度2 signalはそれぞれ20,460/21,600、すなわち94.7222%だった。他の6 signalはそれぞれ20,640/21,600、すなわち95.5556%だった。

各温度signalの除外内訳は`mode_boundary=720`、`previous_event_overlap=180`、`quality_non_ok=180`、`previous_quality_non_ok=60`である。全signal／modeで`profile_inconclusive=0`だった。availability低下は単一原因ではなく、固定したmode境界、event overlap、quality stressの重なりとして扱う。

## calibration diagnostics

5,760/5,760 profilesが`calibrated`で、各profileのcalibration point countは29だった。したがって今回の検知失敗を、単純な未校正やprofile inconclusiveとして説明することはできない。現行のequipment×signal×operating-mode profileは成立しており、そのうえで感度と誤警報の問題を別候補として比較する必要がある。

## 解釈とv0.3候補

今回のengineering passからperformance passを導かない。canonical detectionを改変せず保存しつつ、因果的supportが0/240であることを診断結果として固定する。threshold緩和やmodel winnerのpost-hoc選択は行わない。

v0.3では新しいpreregistrationを作り、次を比較候補として事前固定する。

- mode-entry、phase、recipe-step、conditional level
- longer clean calibration
- multivariate residual
- machine fault sensitivity
- false-alert reduction
- quality stressをcore detectionから分離した評価

これらは候補であり、本結果文書では採用を決定しない。

## 公開物の保護とconsumer要件

公開時にはprotected DACLと、通常のwrite／deleteを拒否する状態をread-only `AccessCheck`で確認した。ただし、この確認はsecurity sandboxや永続的なimmutabilityを保証しない。ownerによるACL変更、特権操作、公開後の変更防止、directory metadataの電源断耐性は保証範囲外である。

consumerは利用のたびに、固定公開先にexact 3 regular non-reparse filesだけがあること、`.complete` markerのtype／version／exact fields、およびmarkerが示す`result.json`／`summary.md`のraw SHA-256を検証しなければならない。

## 独立監査

独立したAstra/max監査ではP0–P3の指摘は0件で、`RESULT_TRUSTED=yes`と判定された。これはexploratory artifactとしての信頼判定であり、performance promotionの承認ではない。監査はread-onlyで行い、再publishは実施していない。

事前契約は[`anomaly-multiseed-failure-diagnostics-plan-v0.1.md`](../anomaly-multiseed-failure-diagnostics-plan-v0.1.md)、元となるv0.2評価は[`anomaly-multiseed-v02-evaluation-2026-09-05.md`](anomaly-multiseed-v02-evaluation-2026-09-05.md)を参照。
