# Event-aware anomaly evaluation v0.1 multi-seed replay preregistration

策定日: 2026-09-05

## 文書の位置付け

これは実験開始前のpreregistrationである。ここに記す数値、対象範囲、判定規則、再標本化方法は、実行結果を見て変更しない。現時点ではmulti-seed replayを実行しておらず、性能達成、engineering gate通過、model昇格を主張しない。実装前の計画と受入条件を固定する文書であり、実行結果は後続の独立した結果文書へ記録する。

対象は、forecast benchmarkから分離したevent-aware anomaly evaluation v0.1である。現行のsingle-seed契約は [`anomaly-evaluation-contract.md`](anomaly-evaluation-contract.md) にあり、本計画はそのdetector、event accounting、provenance、fail-closed境界をmulti-seed・multi-layoutへ拡張するための正式な次工程である。

## 1. 目的と非目的

目的は、v0.1 robust residual detectorについて、event位置、operating mode、equipment、seedを広げた再現可能なoffline gateを実施できるかを検証することである。主張の対象は、固定したsynthetic条件での契約準拠、再現性、event単位metric、uncertaintyの計算可能性である。

次は目的に含めない。

- robust residual detectorの一般性能、実設備性能、顧客設備への一般化を保証すること
- Banto Hub、PLC、interlock、制御値へのwriteまたはshadow write
- forecast modelやfoundation modelとの比較、model採用、product-candidate昇格
- test結果に基づくthreshold、layout、seed、slice、promotion基準の変更

このrunではstdlib-only detectorだけを使う。TimesFM、Chronos、Toto、TSPulseは混ぜない。モデル比較は、別のpreregistrationで別条件・別のevidenceとして扱う。

## 2. 固定する評価母集団

### 2.1 seed

固定seedは次の10個だけとする。

`[11, 17, 23, 29, 37, 42, 53, 67, 79, 97]`

seedごとにdatasetを独立生成し、観測値のhashとdataset fingerprintを記録する。seed、generator設定、開始code revision、config raw bytesをrun開始前に固定し、実行中または実行後に変更しない。

### 2.2 event layout

6 modeと2 equipmentの直積を、次の12 event-layoutとして固定する。

| layout ID | equipment | operating mode |
| --- | --- | --- |
| `motor-01-stopped` | `motor-01` | `stopped` |
| `motor-01-startup` | `motor-01` | `startup` |
| `motor-01-low-speed` | `motor-01` | `low_speed` |
| `motor-01-nominal` | `motor-01` | `nominal` |
| `motor-01-high-load` | `motor-01` | `high_load` |
| `motor-01-cooldown` | `motor-01` | `cooldown` |
| `conveyor-01-stopped` | `conveyor-01` | `stopped` |
| `conveyor-01-startup` | `conveyor-01` | `startup` |
| `conveyor-01-low-speed` | `conveyor-01` | `low_speed` |
| `conveyor-01-nominal` | `conveyor-01` | `nominal` |
| `conveyor-01-high-load` | `conveyor-01` | `high_load` |
| `conveyor-01-cooldown` | `conveyor-01` | `cooldown` |

各layoutには、`machine_fault`、`sensor_fault`、`data_quality`、`ignored`を各1件ずつ置く。4件は互いに非重複とし、mode境界から十分内側へ配置し、validationを汚染しない。positive eventはtest内のraw intervalに入り、`machine_fault`と`sensor_fault`のpositive eligible incidentとして扱える配置にする。`data_quality`と`ignored`はevent window・suppression検証用であり、positive incidentには数えない。

正確なevent signal、event duration、mode内offset、test splitに対する位置、graceとの関係は、runner実装前にschema/configへ明記して固定する。schema/configのcanonical bytesとhashをpreregistrationの一部として保存し、run開始後にoffsetまたはlayout表を変更しない。実装時にmode長や半開区間の制約と両立しない値が判明した場合は、最小限の実現可能なoffset変更を新versionのpreregistrationとして明示し、同じversionのまま黙って修正しない。

coverage invariantはseedごとに検査する。

- `event_class × equipment × operating_mode` の各組合せが1回ずつ存在する
- 各seedで12 layout、48 eventが存在する
- 各seedでpositive eligible incidentは24件（machine fault 12件、sensor fault 12件）
- 各seedでdata-quality／ignored event windowは24件
- 10 seedの予定値は120 cells、positive eligible incident 240件、data-quality／ignored window 240件

### 2.3 detector設定

全cellで次の値を固定する。test期間で再調整、mode別の後付けthreshold、seed別の例外設定は認めない。

| parameter | fixed value |
| --- | ---: |
| `min_calibration_points` | `10` |
| `robust_z_threshold` | `4.0` |
| `persistence_points` | `2` |
| `detection_grace_points` | `3` |

calibrationはvalidation-only、`equipment + full signal + operating mode`単位のrobust residual profileを使う。quality、gap、mode boundary、persistence、event matching、clean exposureの定義は [`anomaly-evaluation-contract.md`](anomaly-evaluation-contract.md) に従う。

## 3. 記録する指標

主指標は次とする。

- incident precision、incident recall、detection delay
- clean false alerts per 8 equipment-hours
- target signalごとのscore availability

各指標はoverallに加え、class、equipment、modeのsliceで記録する。signal-level false positiveとequipment-level false-alert episodeを混同せず、signal-level precisionの分母・分子とequipment episode集約を別フィールドで保存する。lead timeは評価・集計・promotion判定に使わない。

incident precision／recallはmachine faultとsensor faultのevent単位matchingから計算する。`data_quality`と`ignored`はsuppressed event-window alertとして別記録し、positive incidentまたはclean false alertへ再分類しない。clean exposureはtest内のavailable intervalからevent windowを差し引き、zero denominatorやzero availabilityはundefined／inconclusiveとして保持する。

## 4. 不確実性

seedをclusterとして扱い、各seedの12 layoutをblockとして再標本化するhierarchical bootstrapを固定する。event row単位の独立resamplingはしない。各resampleではlayout block内の4 event classの関係を保ち、seed clusterのまとまりも保つ。

- bootstrap seed: `20260905`
- resamples: `10,000`
- interval: 95% percentile CI
- 対象: overallおよび事前登録したclass／equipment／mode slice

sample不足、分母0、undefined metric、必要なclusterが欠けるsliceは数値を補完せず`inconclusive`とする。追加で探索するslice、threshold別診断、個別eventの例示は探索的結果として、事前登録指標と分離して報告する。CIが計算できない場合にpromotion gateを緩和しない。

## 5. engineering gate

engineering gateは性能promotion gateと独立に判定する。次をすべて満たす場合だけ、runのengineering statusを`complete`とする。

- 120/120 cellsが`success`
- `partial`、`failed`、`inconclusive`が0件
- 10 seedすべてでcoverage invariantが一致
- seedごとのdataset fingerprintとobservation hashがseed間でdistinct
- config、schema、result、provenance、code revision、seed、layout hashが記録される
- resultとsummaryのschema validation、hash検証、atomic publish、non-overwriteが通る
- repository safety検査とduplicate／non-finite／path／timestampのfail-closed検査が通る
- customer data、credential、checkpoint、raw public data、model weightsが入力・Git・artifactの管理境界へ混入していない

失敗、欠測、partial、inconclusive、監査不能なcellは隠さず、cell単位の証跡とともに結果文書へ残す。engineering gate未達でも、研究結果としての記録は可能だが、performance promotion gateへ進めない。

## 6. performance promotion gate

promotion gateはrun completionの後にのみ評価し、engineering gateと同時に成功したことを意味しない。次のpoint estimateと95% CI境界を固定する。

| metric | point gate | CI gate |
| --- | ---: | ---: |
| overall incident precision | `>= 0.80` | lower `>= 0.60` |
| machine-fault recall | `>= 0.80` | lower `>= 0.60` |
| sensor-fault recall | `>= 0.90` | lower `>= 0.75` |
| clean false alerts per 8 equipment-hours | `<= 1.0` | upper `<= 2.0` |
| each target score availability | `>= 0.95` | — |

各 `class × equipment × mode` sliceは`n=10`（10 seed）を満たすことを確認し、point recallを報告する。ただしslice単独でpromotion判定を行わず、sliceのundefinedやCI不能を隠さない。

promotion gate未達は研究結果として完了できるが、昇格不可とする。現行single-seed sampleのprecision／recallは0であり、今回のgate未達が予想され得る。この事前情報を理由にthreshold、layout、seed、CI方法、promotion基準を結果後に変更しない。

## 7. 実装savepointと変更管理

実装は次の順序で分離する。

| savepoint | 内容 | 完了条件 |
| --- | --- | --- |
| A | schema/config/layout validator | 12 layout、offset、class partition、coverage invariant、fixed parametersを実行前に検証できる |
| B | deterministic matrix runner + atomic aggregate | 10 seed × 12 layoutのcell identity、seed hash、provenance、atomic non-overwriteを固定できる |
| C | fake/unit tests | matching、suppression、grace、availability、bootstrap、fail-closed境界をartifactなしで検証できる |
| D | clean 120-cell run | clean revision上で全cellを実行し、engineering gateの証跡を生成する |
| E | 独立監査・結果doc | code/config/schema/hash/metric/CIを再確認し、promotion判定と限界を記録する |

このpreregistrationの後に、runner実装、clean run、独立監査の順で進める。runの再実行、seed変更、layout／offset変更、detector parameter変更、metric／CI変更は同じpreregistrationの更新として扱わず、新versionと新preregistrationを作成する。結果文書には使用したpreregistration version、config hash、code revisionを記録する。

## 8. 安全、ライセンス、保存境界

本runはstdlib-only detectorのoffline replayに限定し、制御write、Banto Hub write、customer data、credential、checkpoint、model weightsを扱わない。TimesFM、Chronos、Toto、TSPulseを同じrunへ追加しない。forecast model比較は別preregistrationとし、異なる結果をこのgateへ混ぜない。

Gitで管理するのはsource、schema、config、tests、docs、hashや結果の小さな要約だけとする。生成されたobservations、raw public data、weights、大型artifact、実行cacheはGit管理外の明示された境界へ置く。atomic publish、non-overwrite、path safety、repository safetyをrun前後に検査し、既存complete outputを置換しない。

## 9. 次の判断

本計画はmulti-seed replayの開始許可そのものではない。まずSavepoint A〜Cで計画の構造、validator、fake/unit testを確定し、その後にclean 120-cell runを別途承認する。D完了後も、promotion gateの未達、CI不能、coverage欠落、engineering failureを研究上の事実として保持する。Banto Hubや実設備のshadow／control境界へ進む判断は、このrunの成功だけでは行わない。
