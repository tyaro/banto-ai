# event-aware anomaly multi-seed evaluation v0.3: 実装前 preregistration

状態: **独立監査合格 / S0 frozen・adopted / plan only**。2026-09-06作成・監査採択。
`SCIENCE_READY=yes`、`FREEZE_READY=yes`、`DOCS_READY=yes`、
`IMPLEMENTATION_READY=yes`、`STACK_READY=yes`。S1以降は未着手である。
計画の基準は `026aa77fe96afd954957acb2fc7d0df9ee3cc938`。初稿S0 commit
`41decf9b6f8d6c876715729516354bf6da49422c`はAstra/max監査でP0/P1 0件・P2 3件となり、
文書同期commit `e92c83df03b2f798d60246e14411d249a0b76202`の上の監査対象revision
`4b02201f95e8ffa3a243be716872d95815a554bd`は独立監査でP0〜P3 0件となり、S0として採択した。
candidate stackはmain未統合。S1 registryは`4b02201...`を科学仕様revisionとしてpinし、
本監査後のstatus/result同期commitもGit historyから解決してprovenanceとして併記する。

2026-09-10追記: 上記はS0採択時点の履歴。ユーザー判断に基づき、§8のWindows受入を
CPython3.14.0に一本化した。Linux3.12/3.14の互換性試験は継続する。
[変更・検証記録](results/anomaly-multiseed-v0.3-s4-b1-acceptance-readiness-2026-09-10.md)を参照。
このplatform受入範囲の改訂は、科学仕様の履歴pinや正式runtime pinを変更せず、S4受入完了を意味しない。

v0.3のconfig、schema、validator、scorer、runner、test、run、結果artifactは**まだ作成・実施していない**。候補の勝者、性能達成、製品昇格も未決定である。本書は、それらの実装を承認する前に、仮説・データ・算法・母数・判定・停止条件を固定する文書であり、run結果ではない。以下の新しい数値、seed数、候補、閾値、実験規模、gateは、既存の実測値と明記したものを除き、すべて**v0.3の設計上の決定**である。

## 1. 根拠と研究の境界

根拠として、[v0.2正式評価](results/anomaly-multiseed-v02-evaluation-2026-09-05.md)、[v0.2 failure diagnostics](results/anomaly-multiseed-v02-failure-diagnostics-2026-09-06.md)、[v0.2凍結計画](anomaly-multiseed-evaluation-plan-v0.2.md)、[diagnostics凍結計画](anomaly-multiseed-failure-diagnostics-plan-v0.1.md)、[研究実装計画](research-implementation-plan.md)を参照する。

実装上の根拠は、[generator](../src/banto_ai/generator.py)、[evaluator](../src/banto_ai/anomaly_evaluation.py)、[matrix validator](../src/banto_ai/anomaly_matrix.py)、[matrix runner](../src/banto_ai/anomaly_matrix_runner.py)、[generator config](../examples/configs/synthetic-anomaly-evaluation-v0.1.json)、[evaluator config](../examples/configs/anomaly-evaluation-v0.1.json)、[v0.2 matrix config](../examples/configs/anomaly-multiseed-v0.2.json)、[analysis config](../examples/configs/anomaly-multiseed-analysis-v0.2.json)である。対応する[generator schema](../schemas/synthetic-generator-config.schema.json)、[evaluator config schema](../schemas/anomaly-evaluation-config.schema.json)、[matrix config schema](../schemas/anomaly-multiseed-matrix-config-v0.2.schema.json)、[matrix result schema](../schemas/anomaly-multiseed-matrix-result-v0.2.schema.json)、[analysis config schema](../schemas/anomaly-multiseed-analysis-config-v0.2.schema.json)の旧identity・120-cell固定契約は変更しない。

| 既存の実測事実 | 本書の事前仮説・設計への接続 |
| --- | --- |
| v0.2 machine recall `0/120`、sensor canonical detection `9/120`。後者9件はすべてevent前のsupportに依存し、canonical onsetを保持したcausal supportは合計`0/240` | onsetだけでなく、onsetを生んだ全persistence点を検証する。旧canonical detectedをprimary numeratorに使わない |
| post-event最大連続超過長は全240件で`<=1`。machineはrun 0が10件・run 1が110件、sensorは120件ともrun 1。固定persistenceは2 | persistenceを1へ緩めず、持続する水準変化を測る残差を有限候補として比較する |
| clean equipment alert 222件。startup 89、cooldown 55。2つのvibration target由来のsignal alertは134/222、mode entry offset 2が66件・3が22件 | 単なるmode別では足りない可能性がある。mode entryからのphase曲線を正常profileに含める |
| temperature availabilityは各`20,460/21,600 = 94.7222%`。mode boundary、event-history overlap、qualityと直前qualityの除外が寄与 | GT event-historyによるscore除外を止め、観測可能なquality・時刻・modeだけでavailabilityを決める。quality層と境界sliceを残す |
| 全5,760 profilesがcalibratedで、各29 calibration points。profile inconclusiveは0 | calibration不足が既に原因と確定したとは言わない。phase推定のための正常期間延長は新たな設計変更として全候補に共通化する |

v0.2は凍結契約下の**正式な過去の評価結果**であり、engineering pass / performance gate全5件failという地位・数値・artifactを変更も格下げもしない。diagnosticsはexploratoryである。両結果をv0.3の設計に用いたため、旧10 seeds、旧artifact、その再score、旧データから選んだ部分集合をv0.3の正式な昇格証拠に再利用しない。歴史的対照の引用と、新しいholdout上のC0評価を区別する。

対象はstdlib中心・外部ML依存なしのdetector改善であり、TimesFM3の性能検証ではない。TimesFM residual、他のfoundation model、モデル重み取得、予測horizon比較は別preregistration・別ID・別output rootの研究trackとする。MITは本repoのcode/docsに適用し、モデル重み・外部データの利用条件を緩和しない。本実験のformal入力は合成データのみ。将来の公開データは出所・再配布条件を別途確認し、同じformal母数に足さない。顧客データ、外部通信、PLC/control write、Banto Hub writeは全工程で対象外である。

## 2. seed登録、開発とholdoutの分離

独立な標本単位として扱うのは**seed cluster**であり、同じseedのequipment、12 layouts、10 test cycles、core/quality-stress、候補は対応のある相関データである。40 clustersは旧10よりseed間変動を観察しやすくする有限の研究規模として選ぶ。eventを19,200個の独立試行とみなすpower計算はしない。PRNG seed間を独立な生成実現とみなす仮定は、実設備間の独立性や一般化の保証ではない。

| role | seed数 | 使用範囲 |
| --- | ---: | --- |
| `dev` | 8 | 開発・tuning用に隔離した探索領域。ただし登録済みv0.3では後述の固定算法の実装検証のみ。閾値・候補・gateを変更する探索は新preregistrationへ移す |
| `smoke` | 2 | 固定実装の再現性・全layout・品質層・容量の検査。正式な性能証拠に算入しない |
| `holdout` | 40 | 全実装とanalysis/audit契約をfreezeした後、1回のformal campaignで使用 |

旧seed集合は `[11,17,23,29,37,42,53,67,79,97]`。新seedは次の手続きで一意に決める。性能値を見た再抽選、都合のよいseedの交換、seed数の追加はしない。

1. roleを`dev`、`smoke`、`holdout`の順、各role内のindex `i`を0から所定数未満の昇順で処理する。`used`は旧10 seedsで初期化する。
2. counter `c=0`から、ASCII/UTF-8文字列 `banto-ai/anomaly-v03/seeds/{role}/{i}/{c}` のSHA-256を計算する。整数は符号なし10進表記、先頭ゼロ・空白・改行なし。
3. digest先頭8 bytesをunsigned big-endian整数にし、bitwise ANDで`2^63-1`を適用した値を候補seedとする。`seed < 1,000,000`または`seed in used`なら`c`を1増やして再計算する。それ以外は採用し、`used`へ追加する。
4. 全整数を正確な整数型で保存する。浮動小数点経由、53-bit丸め、boolの整数代用は禁止。role順の生成とJSON objectのkey sortを混同しない。

照合用のseed-list objectは、keyを`dev`、`smoke`、`holdout`、valueを各roleのseed配列だけとする。`sort_keys=true`、UTF-8、compact separators `,`と`:`、末尾改行なしのcanonical JSONのSHA-256は `fa072f5299132fc22cce471c94ca189ddfc0f3acd27c2c5201bc31a2a9287505`。先頭/末尾はdev `2486912926863618161` / `273561671901354104`、smoke `60100173653660076` / `5917958850568857994`、holdout `2792161106071485543` / `5551010198809690423`。全50新seedsは重複せず、旧10と非重複で、この手続きのretryは0である。これは整数・hashの照合であり、データ生成・score・性能評価ではない。

S1で全seed配列、各counter、算法ID `anomaly-v03-seed-registry-sha256-v1`、canonical/raw hashをconfig savepointへ保存し、**どの新seedも生成に使う前にcommitする**。公開repoのseedと算法は公開・再現可能であり、暗号学的なblind/秘密holdoutとは呼ばない。ここでのholdoutは、結果を見ずに設計・実装を凍結し、その後の変更を認めない手続き上の分離である。holdoutの観測値・score・集計を早期に参照した場合は、参照範囲を記録し、現campaignからの昇格を停止する。

## 3. 共通の生成・時系列分割・quality層

### 3.1 時系列と較正期間

equipment順を`motor-01`、`conveyor-01`、target順を`motor_current`、`motor_temperature`、`conveyor_speed`、`vibration_feature`に固定し、完全修飾8 targetsを扱う。`load_proxy`はtargetにもC2入力にも含めない。開始時刻は`2026-01-01T00:00:00Z`、intervalは1,000 ms、各equipment 9,000 samples。6 modesを`stopped,startup,low_speed,nominal,high_load,cooldown`順に各30 samples、計50 cycles反復する。

| sample半開区間 | 長さ | 使用 |
| --- | ---: | --- |
| `[0,1800)` | 10 cycles | warm-up。温度stateは進めるが、fit/calibration/評価には入れない |
| `[1800,5400)` | 20 cycles | 正常fit。C1のphase曲線、C2のphase曲線・共分散を推定 |
| `[5400,7200)` | 10 cycles | 正常validation calibration。全候補の残差center/MADのみを推定 |
| `[7200,9000)` | 10 cycles | test。1秒ごとの1,800 causal scoring originsを全て使用 |

これは現generatorのchronological 60/20/20 splitと整合する。trainの先頭10 cyclesをwarm-upとして明示的にfitから外す。normal fit/calibrationにenabled event、quality非ok、欠測を置かない。test開始後はprofileも閾値も更新しない。C0のfit段階はno-opだが、利用可能な過去の期間・testの長さは同一である。C0も較正期間を延長するため、過去のv0.2実測との直接的な優劣比較はしない。

生成の物理式、noise分布、equipment順・signal演算順、単一`random.Random(seed)`の消費順は、基準commitの`generator.py`の`_base_values`に固定する。初期温度24.0、現行の温度state更新を保持し、event injectionは観測値へ適用してlatent温度stateや乱数消費を変えない。code/runtime hashをpinして再現性を検証する。v0.3 materializerは50-cycle regimeと下記のoverlay契約を新identityで実装する。旧validatorへoverlapを押し込む、旧schemaを緩める、異なるrandom streamでquality層を再生成することは禁止する。

<a id="v03-quantization"></a>

#### Materialized observationの丸め契約（P2-2）

quantizationは基準commitの`generator.py`の`_finite`と保存直前の呼出しに合わせ、
Python builtinの`round(float(value), 6)`を使う。小数点以下6桁への数値丸めであり、
6桁の文字列書式やdecimal型での再計算ではない。各equipmentの各sampleで次の順を固定する。

1. `_base_values`をbinary64で計算し、返された**未丸めの正常temperature**を次sampleの
   latent stateへ保存する。noise生成、内部積和、latent stateは丸めない。
2. 未丸めの正常signal値のcopyへ、§3.2のmachine → sensor → ignored → qualityの順で
   当該sampleのenabled overlaysを適用する。clampとstuck stateの初回captureもこの段階で行う。
   途中のoverlay間で丸めず、stuckが保持する値もcapture時には未丸めとする。
3. 最終quality maskでnullになった値はnullのまま保存する。それ以外はfiniteを確認して、
   **全5 numeric signals（非targetのload_proxyを含む）に1回だけ**`round(float(value), 6)`を適用する。
   欠測や非finiteを0へ置換しない。Pythonのbinary64に対するties-to-evenの挙動と符号付きzeroを保持する。
4. この値でobservations行を確定し、現行のUTF-8 JSONL（sorted keys、compact separators、
   `ensure_ascii=False`、`allow_nan=False`、各行末LF、equipment順→timestamp順）へ保存する。
   `0.45`を`"0.450000"`へ変換するなどの再書式化はしない。既存のfingerprint/raw hash契約を使う。

fit、validation calibration、test scoring、独立analysis/auditの入力値は、hash検証済みの
**保存済みobservations.jsonlをstrict decodeした6桁丸め後の値だけ**とする。
generator内部の未丸め配列やlatent stateを直接渡さない。再生成は保存bytesの照合にのみ使い、
推定入力を未丸め値へ差し替えない。warm-upも同じ保存規則を適用するが、§3.1どおりfitから外す。
profile、残差、score、CIを追加で6桁丸めすることはなく、既定のbinary64計算を維持する。
seed整数、eventのmagnitude、timestamp、schema/configの数値もこの観測丸めの対象ではない。

次はS2/S3で固定する手計算例であり、この文書改訂でdatasetを生成した結果ではない。

| fixture | 保存直前までの操作 | 期待する保存値・state |
| --- | --- | --- |
| Q1 overlay後の丸め | raw target `1.0000014`へjam magnitude `0.55`を適用 | `round(max(0,1.0000014*(1-0.55)),6)=0.450001`。先にraw値を丸める誤実装の`0.45`とは異なる |
| Q2 temperature state | 正常temperature `24.123456789`へsensor spike `+8.0` | 観測`32.123457`、次sampleのlatent temperatureは未丸めの正常値`24.123456789` |
| Q3 quality最後 | Q2の同じsampleにdropoutを重ねる | 観測null、quality `missing`。latent stateはQ2と同じ正常値 |
| Q4 binary64 tie | binaryで正確な値`0.0078125`と`0.0234375`を保存 | それぞれ`0.007812`と`0.023438` |
| Q5 signed zero | raw値`-0.0000004`を保存 | 数値`-0.0`、JSON tokenも`-0.0`。`0.0`へ正規化しない |

`recipe_step`は各modeの固定名`stop/start/low/run/load/cooldown`とする。cycle番号、event ID、seed、絶対test位置をモデル特徴へ渡さない。phase `u`は直近の観測されたmode entryからの連続1秒sample数（0..29）であり、未来のmode予定表を読むことなく更新する。同mode内のrecipe familyは固定で、未知recipe/mode、gap後にentryを確定できないphaseはunavailableとして記録する。30秒の周期知識を使う合成研究であり、任意のduration・未学習recipeへの一般化は主張しない。

### 3.2 layoutとeventの固定式

layout index `l=0..11`をequipment-major × 上記mode順とする。equipmentは`floor(l/6)`、mode indexは`m=l mod 6`。test cycle `r=0..9`の対象mode開始を `b=7200+180r+30m` とする。class index `k=0,1,2,3`をmachine、sensor、data_quality、ignoredに対応させ、slot配列を**`[0,7,14,21]`**とする。

- machine: 開始`b+slot[(l+0) mod 4]`、duration 3、`jam_or_slip`、magnitude 0.55。motorはcurrent、conveyorはspeedがevent target。現行のload/vibration同時変化も保持する。
- sensor: 開始`b+slot[(l+1) mod 4]`、duration 3、temperatureへの`spike`、magnitude 8.0。
- ignored: 開始`b+slot[(l+3) mod 4]`、duration 3、非target `load_proxy`への`stuck_value`、magnitude 0.0。未検知faultとして数えないが、この区間のalertをprecisionから隠さない。
- data_quality: temperatureへの`dropout`、duration 3、magnitude 0.0。`r=0..8`の開始は`b+slot[(l+2) mod 4]`。`r=9`だけ開始を**sensor開始+1**とし、sensor faultと重ねる。overlay順はmachine、sensor、ignored、最後にquality mask。dropoutは値null、quality `missing`にする。

各eventのraw区間は`[s,s+3)`、評価窓は`[s,s+6)`（grace 3秒）。mode entryそのものを試験するため、旧slots `[2,9,16,23]`から新slots `[0,7,14,21]`へ変更する。全窓は対象30秒modeとtestに収まり、machine/sensorの窓は互いに非重複。許可するevent overlapは`r=9`のsensorとqualityのみで、その他の未登録overlapはengineering errorとして停止する。stopped/cooldownの物理的な故障妥当性を保証せず、難しいlayoutも除外しない。

pair IDは`anomaly-v03-{role}-seed-{seed}-layout-{l:02d}`、dataset/cell IDは`{pair_id}-{stratum}`、evaluation IDは`{cell_id}-{candidate_id}`、event IDは`{pair_id}-cycle-{r:02d}-{event_class}`に固定する。seedは正確な10進整数、layout/cycleは2桁ゼロ埋めとする。event IDをcore/stressで意図的に共有し、完全な行identityにはdataset IDも含める。disabled qualityを含む**40行/ datasetの設計event ledger**と、enabled event実体を別にする。cycle/event IDを省略して混同しない。

### 3.3 paired core / quality-stress

`core`では上記quality maskだけをdisabledにし、その他のfault・ignoredと乱数実現を保持する。`quality-stress`では全10 dropoutをenabledにする。candidate間では同じstratumのobservations、event ledger、quality mask、split、origins、target集合のhashが完全一致しなければならない。stratum間ではquality対象座標以外の値、latent生成、fault ledgerが一致する。coreとstressを独立標本として増幅しない。

`r=9`のsensor窓には、qualityと直前quality検査のためoffset 1..4のscoreが利用できず、利用できてもoffset 0と5だけになる。persistence 2のpost-event supportは不可能なので、各stratum 4,800 sensor incidentsのうちstressの480件は構造的に検知機会を失う。**この480件を除外せず、stress sensor recallの上限0.90を明示する**。残り4,320件での機会条件付きrecallは補助診断のみとし、formal denominatorの代わりにしない。

## 4. 登録候補: 3本だけ、組合せ探索なし

候補ID順は`c0-diff-control`、`c1-phase-level`、`c2-phase-conditional`。別々の排他的detector bundleとして全3本を同じholdoutで報告する。ensemble、最良signal別の混成、modeごとの候補切替、事後threshold/persistence sweep、testに基づく再calibrationはしない。C1/C2はphase処理を共有する設計だが、計算・calibration stateは候補ごとに独立して作り、他候補のscore/alertやtest labelを入力しない。

### 4.1 共通契約

detector入力のallowlistは、そのequipmentの当該時刻までのtarget値・quality、timestamp、observed operating mode、固定recipe family、およびfit/calibration済みprofileだけ。GT eventの開始・終了・class・magnitude・ID、layout、testの将来値、quality injection予定、他equipmentの値は渡さない。evaluatorがGTを使うのは生成検証、ledger、matching、slice、分母計算だけである。特に現行`previous_event_overlap`をtest scoreのavailability条件に使わない。

全候補はtargetの現在値と1秒前の値がfinite・quality `ok`で、両時刻のmode/recipeが同じときだけscore可能とする。mode entry `u=0`は全候補でunavailable、mode境界・gap・quality非ok・profile変更でstreak/episodeをresetする。C1も、この共通の1点履歴quality条件を外してavailabilityを有利にしない。C2はさらに同equipmentの4 targets全てにこの条件を要求し、欠測imputationや次元削減fallbackをしない。quality mask自体は共通でも、C2の入力依存による追加unavailabilityは候補差として残す。

profile identityは `(candidate, role, seed, layout, stratum, equipment, full_target, mode, recipe_family, profile_version)`、`profile_version=0.3`。seed/layout/stratum等のidentityは来歴・lookup専用で、scoreの数値特徴にしない。phase曲線全体を1つのmode profile内に持ち、`u`ごとに別profile IDを発行しない。そうしないと同profileでのpersistence 2が成立しない。数値的に同一の正常prefixを持つlayout/stratum間でも、独立にfit/calibrateし来歴を記録する。profile台帳行数を独立な学習データ数と誤認しない。

全候補の最終calibrationは、validation `[5400,7200)`のavailableな残差 `h`に対して `a=median(h)`、`d=1.4826*median(abs(h-a))`、score `z=abs(h-a)/d`。各equipment/target/modeで予定290点（10 cycles × phase 1..29）、最低250点とする。`d<=0`、非finite、点数不足はprofile inconclusive。epsilon、global fallback、test由来scale、別modeへのbackoffは禁止。正常prefix不備は入力契約違反としても別記する。

| 候補 | 入力・fitで固定するもの | calibrationへ渡す残差 `h(t)` | score閾値 / persistence |
| --- | --- | --- | --- |
| C0 差分対照 | target自身の現在・直前値。fitはno-op。正常validationでmode別差分center/MAD | `x_i(t)-x_i(t-1)` | `z>4.0` / 連続2点 |
| C1 phase水準残差 | 正常fitでequipment/target/mode/phaseごとに20 cyclesの中央値 `mu_i,m(u)` | `x_i(t)-mu_i,m(u)` | `z>6.0` / 連続2点 |
| C2 多変量条件付き残差 | C1と同じ定義の独立なphase中央値、4 targetsの正常残差scaleとmode別shrinkage共分散 | 下記の`h_i(t)`。他3信号との通常の関係からのずれをtarget別に計算 | `z>6.0` / 連続2点 |

C0は「v0.2算法の対照」であって旧binaryの同一再実行ではない。新しい共通calibration期間、GT-free availability、causal matching、merge/分母契約を適用する。C1/C2の6.0はskewed vibrationと多数originsのfalse alertを重くみる保守的な設計値であり、正規分布の6 sigma保証ではない。4から6への変更を含むbundle比較なので、改善をphase処理だけの因果効果と断言しない。persistence 2・grace 3は、1点だけの変動を持続検知と呼ばないために保持する。

### 4.2 C1/C2の数値手順

C1/C2の各`mu_i,m(u)`はfitの20同phase値の通常の中央値（偶数個なら中央2値の算術平均）。全30 phasesで20点を必要とする。fitにevent・欠測は予定しない。test/calibrationの現在値をphase基準値へ取り込まない。

C2ではmodeごとにfitのphase 1..29、20 cyclesの580 complete vectorsを使う。`e_i=x_i-mu_i,m(u)`について `b_i=median(e_i)`、`q_i=1.4826*MAD(e_i)`を求め、`r_i=(e_i-b_i)/q_i`とする。`q_i<=0`または非finiteならそのmodeの4 target profilesをinconclusiveとする。`r`の算術平均ベクトル`v`と、分母`579`の通常のsample covariance `S`を計算する。

`Sigma=0.75*S+0.25*diag(S)`、`Omega=inverse(Sigma)`を固定し、`h_i(t)=(Omega*(r(t)-v))_i / sqrt(Omega_ii)`とする。shrinkage係数0.25は唯一の値で、探索しない。固定target順・二重精度・固定ループ順・`math.fsum`による和・Cholesky solveで4×4演算を実装する。非正対角、Cholesky失敗、非finiteはinconclusiveで、追加jitterや係数変更で救済しない。validationでこの`h_i`をtarget/mode別に最終calibrationし、test前に全stateをlockする。

C2は同時刻に観測済みの他信号を使う条件付き異常scoreであり、未来予測でも因果効果推定でもない。faultが複数信号へ及ぶと相関モデルが異常を相殺する可能性、temperature dropoutが全4 scoresを止める可能性も評価対象とする。

### 4.3 signal episodeとequipment merge

targetごとに、availableかつ`z>threshold`の連続runを作る。timestampは正確に1秒間隔、equipment・full signal・mode・recipe・profile IDは同一でなければならない。run長2となった時刻を唯一の**signal onset**とし、その直前1点とonset点の2行を`support_score_ids`として保存する。episodeはonsetから最後の連続超過点+1秒までの半開区間。低score、unavailable、gap、mode/profile変更で終了し、同じrun中に再onsetを作らない。

signal episodesをequipment×mode×同一連続mode visit内で、区間のoverlapまたは隣接（次start <= 現end）により推移的にmergeする。順序はstart、full signal、episode IDの昇順。merged equipment episodeのonsetはsource onsetの最小値、endは最大値とし、全source IDを保持する。別mode、別visit、別datasetをmergeしない。この操作はevent labelを見ずに確定させる。

primary precision/clean false-alertの単位はこのequipment episodeである。machine injectionがcurrent/speedとvibrationを同時に変えるため、同一設備の同時警報を2個の独立な警報としてprecisionを罰しない。一方、merge前のsignal alert数、signal別false alert、merge比率も必ず補助報告し、無制限に長いalarmが数を減らしていないかdurationを監査する。

## 5. primary incidentと分母を先に固定する

### 5.1 post-event causal support

<a id="v03-incident-selection"></a>

positive incidentは全machine/sensor events。availability、score、検知可能性によるeligible集合の
削減はしない。評価窓は`W=[event_start,event_end+3秒)`。選択方針を
**`first-equipment-onset-no-retry-v1`**に固定する。最初の候補がsupport不適格なら当該eventはmissとし、
同じeventについて後続equipment episodeや後続source onsetを探索しない。

次の段階をこの順序で実施し、support条件を候補filterへ繰り上げない。

1. **構造検証**: event inventoryと§4.3のscore→signal episode→equipment mergeの整合性を先に検証する。
   duplicate ID、存在しないsupport行、unavailable点から作ったepisode、不正mergeはengineering failure。
   この場合はmatchingを実行せず、未処理eventをmissとして埋めない。
2. **列挙**: eventを`(開始timestamp,event ID)`順で処理する。各eventについて、同dataset・同equipmentで、
   固定equipment onsetが`W`内にあり、未claimのequipment episodesをすべて列挙する。
   target sourceの有無、supportのevent offset、scoreの大小で先に候補を落とさない。
   timestampはUTC整数milliseconds、同時刻のIDはASCII昇順で比較する。
3. **選択**: 候補を`(equipment onset,equipment episode ID)`順に並べる。
   空なら`causal_detected=false`、`reason=no_candidate_in_window`で終了する。
   空でなければ先頭の1件を`selected_candidate_episode_id`へ固定してclaimする。
   claimはsupport失敗後も解除せず、そのepisodeのonset/end/source集合を変更しない。
4. **support検証**: 選択済みepisodeについてだけ、eventと同じfull target signalで、
   source onsetが固定equipment onset `t`と等しいsourceを調べる。
   該当sourceがなければ`reason=first_candidate_no_target_onset`でmiss。
   同target・同onsetのsourceが複数なら§4.3の構造違反としてengineering failureとする。
   1件なら実際の`support_score_ids`が示す`t-1秒,t`の2点を検査する。
   両点がevent offset `>=0`かつ`W`内であることを要求し、不適格なら
   `reason=first_candidate_noncausal_support`でmissとする。
   両点のavailable、strict threshold超過、連続性、同signal/mode/recipe/profileも再照合する。
   ここで構造不整合が判明した場合もengineering failureであり、性能上のmissへ変換しない。
5. **確定**: 全条件を満たせば`causal_detected=true`とし、当該episodeをmatchedにする。
   support不適格なら`causal_detected=false`、matched IDとdelayはnullのまま確定する。
   **どのfailure branchからも段階2/3へ戻らない。**後続候補はこのeventのtrue positiveにしない。

primary ledgerにはcandidate数と順序付きID列、selected ID、選択されたsource IDと実際のsupport IDs
（存在する場合）、reason、matched ID、`causal_detected`を記録する。
event/episodeの対応は一対一で、claim済みでもsupport失敗のepisodeはunmatchedのまま
全precision分母に残る。後続の未選択episodeも既定のaccountingから除外しない。
v0.3の同equipment positive窓は非重複なので、別eventへの再利用による救済も起きない。
detection delayは`(t-event_start)`秒、最短1秒、mode-entry開始なら最短2秒。
unavailable eventは元のincident分母に残し、検知例条件付きdelayでは未検知を0秒にしない。

#### Matchingの手計算fixture

以下は各々独立したS2/S3用の仕様例。eventはtarget `T`、raw `[0,3)`、`W=[0,6)`で、
時刻はeventからの秒offsetとする。test境界は外にあり、同一equipment・mode・profileとする。
`U`は別のfull target signal。記載した超過点のscoreは7、閾値は6、記載外は0、qualityはok。
したがって、例えば`T:{-1,0}`はsignal episode `[0,1)`、support `{-1,0}`を作る。
E1/E2は§4.3で確定するonset昇順のequipment episodeを指す。M7/M8/M9の明示条件だけを例外とする。

| fixture | score列と確定episode | 候補→選択 | 期待結果 |
| --- | --- | --- | --- |
| M1 最初のsupportがevent前 | `T:{-1,0,3,4}`。E1 `[0,1)`、E2 `[4,5)` | `[E1,E2]`→E1 | miss、`first_candidate_noncausal_support`。E2の`{3,4}`で救済しない。matched 0 / all episodes 2 |
| M2 最短のcausal検知 | `T:{0,1}`。E1 `[1,2)` | `[E1]`→E1 | detected、support `{0,1}`、delay 1秒 |
| M3 終了したpre-event episode | `T:{-2,-1,2,3}`。E1 `[-1,0)`、E2 `[3,4)` | `[E2]`→E2 | detected、support `{2,3}`、delay 3秒。E1はonsetが窓外で候補に入らない |
| M4 半開区間の右端 | `T:{5,6}`。E1 `[6,7)` | `[]`→null | miss、`no_candidate_in_window`。onset 6秒は窓外 |
| M5 最初の警報が別signal | `U:{0,1}`、`T:{3,4}`。E1 `[1,2)`、E2 `[4,5)` | `[E1,E2]`→E1 | miss、`first_candidate_no_target_onset`。Tを持つE2へ進まない |
| M6 merge後に遅いtarget source | `U:{0,1,2}`、`T:{1,2}`。merged E1 `[1,3)`、T source onset 2 | `[E1]`→E1 | miss、`first_candidate_no_target_onset`。group onset 1をT onset 2へ動かさない |
| M7 mode entry | mode entry 0でscore 0はnull/unavailable、`T:{1,2}` | `[E1]`→onset 2のE1 | detected、support `{1,2}`、delay 2秒 |
| M8 閾値と等しい点 | T scoreは0秒に7、1秒に6、他は0 | `[]`→null | miss。`>`条件なので1秒は超過に含めず、episodeを作らない |
| M9 偽装されたsupport | 0秒score 7、1秒null/unavailableなのにsupport `{0,1}`のepisodeを記載 | 構造検証で停止 | engineering failure。candidate選択も正式miss集計も行わない |

v0.2のcanonical detectedは歴史的結果としてのみ引用する。本campaignで互換的なonset-only検知数を監査用に計算する場合も、`secondary_canonical_detected`という別fieldに置き、primary gate、選択、bootstrap numeratorには一切使わない。primary onsetを変更するための後付け探索を禁止する。

### 5.2 precision・clean exposure・availability

`R_class = sum(causal_detected_class) / sum(planned_incidents_class)`。`P = matched_equipment_episodes / all_equipment_episodes`。分母はquality/ignored内、他signalだけの反応、重複、pre-event groupも含む**全equipment episodes**で、suppressed除外はしない。alertゼロならprecisionはnull / inconclusiveであり1にしない。matched / unmatchedは全episodeの完全分割、unmatchedのcontextは複数tagを許しても総数は重複計上しない。

clean false-alert rate用には、候補のavailable時刻からではなく、**共通の予定equipment-time**からclean maskを作る。各datasetの両equipment×全test `[7200,9000)`を出発点とし、event対象equipmentについて§3の4 classの評価窓のunionを除く。coreでもqualityの予定窓を除き、stratum間のclean exposureを同一にする。最初の9 cyclesは24秒ずつ、overlap cycleはunion 19秒で、除外は`9*24+19=235` equipment-seconds。したがって1 datasetのclean exposureは`2*1800-235=3365` equipment-seconds。

`F_clean`はunmatched equipment episodeの**固定onsetがこのclean mask内**にある個数。primary rateは`8*F_clean/(H_clean_seconds/3600)`、単位はalerts / 8 equipment-hours。maskでepisodeを切断・再merge・再onset化しない。mask外のunmatchedもprecision分母と全false-alert burdenには残す。quality区間を除いたclean率だけでformal全体が良いと言わない。

併記する全false-alert burdenは `100*unmatched_equipment_episodes/planned_positive_incidents`（false episodes / 100 incidents）。available score区間のequipment unionから求めたeffective clean hoursとそのrateも補助欄に出すが、primaryの分母・gateには使わない。availabilityを下げてclean exposureやincidentを消すことを防ぐ。

`A_signal = available_score_rows / planned_score_rows`。各full targetの全1,800 originsを候補共通の分母とし、欠測、mode boundary、fault、品質overlapも含む。score欠落行を分母ごと削除しない。signal×mode、quality/mode-boundary/event-overlap sliceでも予定行数とavailable行数を併記する。

core、quality-stress、**formal overall（両層のraw count/exposureの和）**を常に並記する。overallをcoreの別名にせず、ratioの単純平均もしない。2 strataの相関はbootstrapで保持する。生産時のfault prevalenceと異なるため、precisionを実設備の適合率へ外挿しない。

### 5.3 事前件数監査表

以下は40 holdout seedsでの予定件数であり、観測された成功件数ではない。3候補が同じeventsを3倍の独立incidentとして増やすことはない。

| 項目 | 式 / 正式予定件数 |
| --- | --- |
| datasets / detector evaluations | `40*12*2=960` / `960*3=2,880` |
| full observation rows | `960*9000*2=17,280,000` |
| test score rows | 1 evaluation `1800*8=14,400`、1候補 `13,824,000`、全候補 `41,472,000` |
| planned event ledger | 1 dataset `10*4=40`、両層計`38,400`。enabledはcore `480*30=14,400`、stress `480*40=19,200`、計`33,600` |
| positive incidents | class別・stratum別`40*12*10=4,800`。class別overall `9,600`、全positive overall `19,200` |
| calibration profile ledger | 1 evaluation `2*4*6=48`、1候補 `46,080`、3候補 `138,240`。各最終calibration予定290点 |
| availability分母 | full target別・stratum別`480*1800=864,000`、overall `1,728,000` |
| clean予定exposure | stratum別`480*3365=1,615,200` equipment-seconds = `448 2/3` equipment-hours、overall `897 1/3` equipment-hours |
| 開発・smoke規模 | dev `8*12*2=192` datasets /576 evaluations、smoke `2*12*2=48` datasets /144 evaluations。formal件数には不算入 |

全profilesが成立した場合のavailability ceilingも事前に計算できる。coreは各target `1740/1800=96.6667%`（60 mode entriesを除く）、各層のavailable分子は835,200。stressは当該equipmentがevent対象のlayoutが12中6で、各10 dropoutにつきcurrent 3点+直後1点を失う。ただし最初の9 cyclesではquality slot 0がmode entryと重なるので、二重に引かない。motorはそのlayoutが1個、conveyorは2個である。追加unavailableはseedごとにmotor `6*10*4-9*1=231`、conveyor `6*10*4-9*2=222`となる。

したがってtemperatureのstress ceilingは、全候補でmotor `(835200-40*231)/864000=825960/864000=95.5972%`、conveyor `(835200-40*222)/864000=826320/864000=95.6389%`。C0/C1の他6 targetsは96.6667%で、complete-vector C2の4 targetsは各equipmentのtemperatureと同じ上限を持つ。temperature/C2のoverall ceilingはmotor `(835200+825960)/1728000=96.1319%`、conveyor `(835200+826320)/1728000=96.1528%`。これはnormal profile成立時の構造的上限であり、達成済みavailabilityではない。

## 6. bootstrap、gate、選択と非劣化

### 6.1 固定推論手続き

40 seed clustersから復元抽出で40個を選ぶcluster bootstrapを**50,000 replicates**行う。各drawでそのseedの全12 layouts×10 cycles×2 strata×3候補を一緒に複製する。stratum別/overall、候補差とも同じdraw列を使い、raw numerator/denominator/exposureを合算してratio-of-sumsを再計算する。seed内平均ratioの平均、event bootstrap、候補ごとの独立再標本化は禁止する。

bootstrap seedは`2026090603`、算法IDは`sha256-counter-rejection-v1`。replicate `b=0..49999`、draw position `j=0..39`、counter `c=0`から、文字列 `sha256-counter-rejection-v1:2026090603:{b}:{j}:{c}`（UTF-8、10進、改行なし）のSHA-256全32 bytesをbig-endian整数`v`にする。`v < floor(2^256/40)*40`ならindex `v mod 40`を採用、そうでなければcounterを増やす。indexは§2 holdout配列の登録順を参照する。S1でgolden drawと全2,000,000 accepted indicesを各1 byteで連結したSHA-256をpinし、実行時に照合する。

昇順の50,000 metric値に対し `h=(n-1)*p` の線形補間（type 7）で、`L=q(.025)`、`U=q(.975)`の95% percentile intervalを報告する。displayの丸め前の値で判定し、単位を保持する。precision等が元標本または1つでもreplicateで分母0なら該当CIはinconclusive、null replicatesの数を記録し、除去・再抽選・0/1補完はしない。gateに必要なCIがinconclusiveならその候補は昇格不可。

昇格候補はC1/C2の2本だけ。candidateあたり片側名目alphaを`0.05/2=0.025`とし、候補間はBonferroniで扱う。候補内は、全ての絶対gate・非劣化gate・全strata・全targetを**同時に通る必要のあるintersection-union判定**である。一つでも必要条件が偽なら昇格不可なので、良いendpointを選ぶOR判定をしない。片側97.5% boundで各必要条件を判定し、2候補のどちらかを選ぶ探索性を扱う。補助sliceの有意差探索にはこの枠を流用しない。

これはcluster percentile bootstrapに基づく**名目上の**多重性手続きであり、40の決定的seedから有限標本で厳密なFWER/coverageを保証するものではない。特に全seedで0件または同一値ならCIが退化する。CI `[0,0]`を未知の設備でも真のfalse-alert率0という証拠にしない。power・実設備SLA・将来故障への安全保証は主張せず、CI不十分を理由にholdoutを足さない。

### 6.2 絶対performance promotion gates

下表のpointと対応するboundを**両方**満たすことを要求する。`L`は高い方が良い量の下限、`U`は低い方が良い量の上限。core/stressだけでなくoverallも必須である。

| 指標 | core | quality-stress | formal overall |
| --- | --- | --- | --- |
| causal machine incident recall | point >=0.85、L >=0.80 | point >=0.85、L >=0.80 | point >=0.85、L >=0.80 |
| causal sensor incident recall | point >=0.90、L >=0.85 | point >=0.85、L >=0.80 | point >=0.875、L >=0.825 |
| equipment-incident precision | point >=0.85、L >=0.80 | point >=0.85、L >=0.80 | point >=0.85、L >=0.80 |
| clean false alerts / 8 equipment-hours | point <=1.0、U <=1.5 | point <=1.0、U <=1.5 | point <=1.0、U <=1.5 |
| availability（8 targetsの**各々**） | point >=0.960、L >=0.960 | point >=0.950、L >=0.950 | point >=0.955、L >=0.955 |

値の理由を先に固定する。machineは研究候補として少なくとも85%を検知し、CI下限80%を要求する。単純な8.0 temperature stepのcoreは90%を要求するが、stressは10%の構造的な検知機会喪失を分母に残すため、上限90%に対して85%を要求する。sensor overallは等数の両層からpoint `(0.90+0.85)/2=0.875`、lower `(0.85+0.80)/2=0.825`を決めた。production費用から最適化した値ではない。

precision 85%はおおむね100 true positivesあたり17.65以下のfalse episodesという研究上の上限で、v0.2のpoint 80%より厳しい。clean point 1/8 equipment-hoursは研究実装計画の初期目標を明示的に再採択し、448 2/3時間/層という新exposureに合わせCI上限を旧2.0から1.5へ狭める。point gateは各層で最大56 clean episodes、overallで最大112に相当するが、bootstrap上限も必要である。実設備で1 shiftに1回を許容すると決めたわけではない。

availabilityは§5.3の構造上限から選ぶ。core 96.0%は上限96.6667%より0.6667 percentage points低い。stress 95.0%はtemperature/C2の上限に対しmotorで0.5972 points、conveyorで0.6389 points低い。overall 95.5%は両層の要求の平均である。旧95%を一律に流用したものではなく、score欠測を集計から捨てない契約に対するfloorである。これらの値が厳しすぎて全候補が落ちても、結果を見て緩めない。

### 6.3 C0とのpaired非劣化と選択

C1/C2の各々について、同一raw母数・同一bootstrap drawの候補値 minus C0値を`Delta`とする。以下をcore、stress、overallそれぞれで全て満たす。C0がengineering未完了、profile inconclusive、または必要な比較量を算出できない場合は比較をinconclusiveとし、候補の絶対pointが良くても昇格しない。C0の0-alert precisionだけがundefinedの場合は、下記の固定分母の比較量を使うのでこの例外には該当しない。

- machine/sensor recall各々: point `Delta>=0`、paired CI下限 `>=-0.02`（許容不確かさ2 percentage points）。
- clean false-alert rate: point `Delta<=0`、paired CI上限 `<=0.25` alerts / 8 equipment-hours。
- 全false-alert burden（false equipment episodes / 100 planned positive incidents）: point `Delta<=0`、paired CI上限 `<=1.0`。C0がalertゼロでも定義できる固定分母で、quality窓内の誤警報増を隠さない。
- availability 8 targets各々: pointおよびpaired CI下限 `Delta>=-0.0125`。C2のcomplete-vector依存による最大1.0694 percentage pointsの計画上の損失（mode/quality重複を控除）に0.1806 pointsの余地を置く設計である。絶対floorも必須とする。

C0 precisionがalertゼロでundefinedとなる場合に任意の値を代入しないため、relative precision gateの代わりに固定分母の全false-alert burdenを使う。絶対precision gateは免除しない。以上のmarginも新しい設計判断であり、実設備リスクの同等性を保証しない。

engineering gateは、全960 datasetsと2,880 evaluationsの予定inventory・全score/ledger行・paired inputs・provenance・strict/semantic validation・consumer auditが完了し、software failure/partial/not_startedが0であることを要求する。定義どおり記録されたprofile inconclusiveはsoftware failureとは分けるが、その候補はqualifiedになれない。

engineering監査合格かつ全絶対・非劣化gate合格の候補だけをqualifiedとする。C1がqualifiedならC1、そうでなくC2だけqualifiedならC2を研究上の次候補として選ぶ。両方qualifiedのtie-breakはC1（入力依存・演算が少ないため）で固定し、最高pointや最小p値を見て切り替えない。**どちらも通らなければno promotion**。C0は登録済み対照として残し、C1/C2が落ちたからC0を自動昇格しない。qualifiedであっても製品利用・PLC書込みを許可するものではない。

## 7. sliceと失敗の完全報告

primary tableは各3候補×core/stress/overallを欠かさず示す。raw counts、予定/実際row counts、precision denominator、clean scheduled/effective hours、全false-alert burden、8 availability、全gateとpaired Delta、CI状態を併記する。

補助incident slicesはpositive class、equipment、mode、およびpositive class×equipment×modeの24組、test cycle、event開始phaseを固定する。slot別は各positive class/層で4 slots各1,200 incidents、positive class×equipment×modeは各400 incidents/層となる。delayのcount/median/mean/min/maxと検知例条件付けを明記する。class別precisionは、classを持たないclean警報を恣意的に配分しないためnot applicableとし、recallを報告する。

availability/alert診断では、8 full signals、48 signal×mode、mode-entry phase `0,1,2,3,4..6,7..13,14..20,21..29`、event offset `-2,-1,0,1,2,3,4,5`、raw event/grace/clean、quality current/previous、fault-quality overlap有無、profile statusを記録する。各sliceは分子と予定分母を持つ。event offsetはevent-relativeで同じscoreを複数eventが参照し得るので、全score行の排他的分割とは呼ばない。負offsetは補助のみでprimary supportに入れない。

全scoreには一意ID、timestamp、phase、full signal、profile ID、依存した観測時刻/quality、残差、scoreまたはnull、availability、exclusion reason、threshold超過、streak、source episode IDを保持する。exclusiveな主除外reasonはcurrent target quality、current nonfinite、no previous/gap、previous target quality/nonfinite、mode/recipe/phase、C2 peer quality/nonfinite、profile inconclusive、nonfinite scoreの順で決め、別のmulti-tag欄に全該当条件を残す。mode boundaryとqualityが重なっても二重にavailability分母を引かない。

software例外、schema/hash/来歴不一致、行欠落、生成不整合は**engineering failure**であり、性能0とは異なる。全2,880 evaluation slotsを事前ledgerに作り、success/partial/inconclusive/failed/not_started、failure stage、safe reason、取得済み証跡hashを記録する。失敗cellを成功cellだけの正式集計から除外せず、planned母数とcoverageを表示し、必要データ未完了ならcampaign性能はnot_evaluated/inconclusive・昇格不可とする。

一方、定義どおり処理されたquality由来のunavailableは観測結果であり、該当incidentのmissとavailability低下として数える。正常な入力でMAD/共分散が成立しない算法上のprofile inconclusiveも、例外や成功へ偽装せず候補inconclusiveとして残す。部分的な診断値を表示してよいが、未処理eventを0件の検知として埋めて正式recallを作らない。重要sliceの母数0はnull/not applicableであり、近隣sliceへの併合で救済しない。

## 8. identity、provenance、non-overwrite publication

下記は**次工程で新規に作る予定の名前**であり、本savepointではファイルもrootも作成しない。旧v0.1/v0.2 config/schema/moduleの意味・ID・output rootを上書きしない。

| 契約 | 登録名 |
| --- | --- |
| plan / matrix / analyzer / analysis / audit ID | `anomaly-multiseed-plan-v03` / `anomaly-multiseed-v03` / `event-aware-anomaly-v03` / `anomaly-multiseed-analysis-v03` / `anomaly-multiseed-audit-v03` |
| 新materializer identity | generator ID `synthetic-anomaly-v03`、generator version `0.3.0`。基準commitの正常生成式を保持し、overlay/manifest契約だけを旧generatorから分離 |
| 新config | `examples/configs/synthetic-anomaly-v0.3.json`、`anomaly-candidates-v0.3.json`、`anomaly-multiseed-v0.3.json`、`anomaly-multiseed-analysis-v0.3.json`、`anomaly-v03-freeze-registry.json`（後4件も同directory） |
| 新schema | `schemas/synthetic-anomaly-config-v0.3.schema.json`、`anomaly-candidates-config-v0.3.schema.json`、`anomaly-multiseed-matrix-config-v0.3.schema.json`、`anomaly-multiseed-analysis-config-v0.3.schema.json`、`anomaly-v03-freeze-registry.schema.json` |
| 新result/ledger schema | `schemas/anomaly-evaluation-result-v0.3.schema.json`、`anomaly-multiseed-matrix-result-v0.3.schema.json`、`anomaly-multiseed-analysis-result-v0.3.schema.json`、`anomaly-multiseed-audit-result-v0.3.schema.json`。score/profile/episode/event等はevaluator result schemaの厳密なdefsとして定義 |
| 新output roots | `artifacts/anomaly-multiseed-v03-dev`、`artifacts/anomaly-multiseed-v03-smoke`、`artifacts/anomaly-multiseed-v03-holdout`、`artifacts/anomaly-multiseed-v03-analysis`、`artifacts/anomaly-multiseed-v03-audit` |

schema versionは新契約で`0.3`、candidate IDsは§4の3個、stratumは2個、roleは3個に限定する。strict JSON/schemaではadditional properties、duplicate keys、NaN/Infinity、整数代用bool、未知ID、未知status、絶対/traversal/UNC/drive-qualified path、symlink/junction/reparse traversalを拒否する。counts、pairing、時刻、support、分割、hashだけを揃えた改竄までsemantic validatorで検査し、syntax合格をrun成功と呼ばない。

S1 freeze registryは本書のcommit/raw hash、seed registry、generator/candidate/matrix/analysis configsとschemasのcanonical/raw hashesをpinする。自己hashを同じJSON内部に入れる循環pinは作らず、registry自体は外部のcommit/raw hashでpinする。S4までにrun実装、独立analysis/audit実装、テスト、bootstrap golden、generator source/runtimeのsource inventoryをcommitして、formal producer revisionとconsumer revisionを明示する。異なるrevisionのproducer/consumerも、各full SHAと実際のsource bytesの対応を検証し、「同じHEADだから同じ」と推測しない。

formal実行はtracked clean revisionのみ。開始時・cell境界・公開直前にHEAD、tracked diff、入力source/runtimeのhashを照合する。ignored/untrackedの旧artifactや残留物をclean化のために削除・移動・copy・normalizeせず、正式入力を列挙したallowlistで限定する。新rootの実体pathと権限、親directoryの包含を確認し、存在するrootはmarkerなしでも上書きしない。dev/smokeを再試験する場合も新しい明示attempt ID/rootと全attempt来歴を登録し、最良runだけを残さない。

正式runnerはseed登録順×layout index×`core,quality-stress`×C0,C1,C2順の固定inventoryで処理する。通常cellの失敗は記録して安全に独立な後続cellへ進み、入力変化、root逸脱、pair不一致などglobal integrity failureなら停止して後続をnot_startedとする。engineeringとperformanceのstatusを別fieldにし、runnerはperformanceを決めない。

publicationは新root内の排他的staging、write/flush、strict再読込・hash/row-count/semantic再検証、no-replace確定、最後のatomic completion markerの順にする。markerはpayload inventoryとそのhashを含み、marker自体の自己参照hashを要求しない。markerが存在するだけで信頼せず、consumerは毎回全inventoryを再検証する。公開失敗時の新規staging/partial evidenceは保全し、既存formal/ignored rootの回収やACL変更を自動で行わない。

Windowsでは新しいv0.3成果物だけに、公開後のprotected DACL・独立read-only監査tokenでの実効AccessCheckを検証する別publisher工程を設ける。旧v0.2/D2-BのACLやartifactを変更しない。rename/marker/DACLは所有者・管理者の改変、privileged writer、電源断耐久性まで保証しない。fresh consumer hash検証と差分監査を必須にする。

独立analysisはformal holdoutを**read-only**に検証・読取り、別analysis rootへ集計を公開する。独立auditはproducerとanalysisをread-onlyに取り、別audit rootへ証跡を出す。少なくともraw観測からの候補profile/score、support-to-onset、event/episode一対一、全母数、bootstrap draw/CI/gate/選択を、producerの出力を真と仮定せず再計算する。producerと同じ「誤った判定関数」を呼ぶだけの監査を独立と称しない。summary/markerだけ更新する改竄も検出し、result docは監査済みartifact外で作る。

<a id="v03-runtime-acceptance"></a>

### Runtime/platform acceptance（P2-3）

CIの互換性試験と正式campaignのruntimeを次のとおり固定する。
これはS1以降に実装・検証する受入条件であり、本改訂で各platformの試験を実行したとは扱わない。

2026-09-10のplatform受入改訂でWindows3.12の実機試験要件を外した。
Windows運用を既存の3.14.0に限定し、同じPCで別projectの連続稼働試験が進む中で
追加runtimeの導入・保守・実機試験を省くユーザー判断による。正式な性能結果に基づく選択ではない。
Windowsで必要なpublisher・DACL・独立token/process・競合・失敗証跡の各検査はすべて維持する。

| 境界 | 必須platform/runtime | S4までに通す条件 |
| --- | --- | --- |
| 共通契約のLinux CI | Ubuntu 24.04 x86_64、CPython 3.12系と3.14系の2 jobs | 同じstrict/pure validator、Q1〜Q5、M1〜M9、profile/score/merge/母数、seed hash、bootstrap golden、fake runner・独立consumer試験を両minorでpass |
| Windows native受入 | 下記Windows 11 AMD64/NTFS、正式pinのCPython 3.14.0 | 共通試験に加えて実Win32 publisher、protected DACL、別process/tokenのAccessCheck、競合・非上書き・失敗時証跡保持をこのruntimeでpass |
| S4 smokeとS5/S6 formal | 下記の唯一のWindows/CPython組合せ | Windowsで生成する同じ保存観測を全候補へ渡し、producer/analysis/auditの厳密な再計算・hash照合を実施 |

Linux jobsのPython 3.12/3.14のpatch/build・CI image digestと、Windows 3.14.0の実build/hash、
OS/kernel、architecture、実行source SHA、各testのpass/fail/skipをS4の受入証跡へ保存する。
各jobでは既存stdlib回帰suiteとrepository safetyも必須とし、v0.3専用fixtureだけのpassで代用しない。
既存CIの`ubuntu-latest`やminor labelだけをformal runtime pinの代わりにしない。
共有fixtureのID、件数、selection/reason、availability、閾値判定、quantized JSON bytes、
seed/整数bootstrap goldenは全platformでexact一致を要求する。
手計算の非整数profile/Cholesky/score値の近似照合だけは`rel_tol=1e-12, abs_tol=1e-12`を固定し、
判定やhashの不一致にこの許容差を使わない。正式producer/consumer間のcanonical exact比較も緩めない。

正式runは**Windows 11 Pro 25H2 / AMD64 / OS build `10.0.26200.9168` / local NTFS**と、
**通常GIL buildのCPython `3.14.0`、64-bit AMD64、MSC v.1944、source tag
`v3.14.0:ebf955d`**の1組だけを許可する。選定根拠は本修正時に確認したローカルruntimeであり、
新seedや候補の性能を比較した選択ではない。OS照合にはmajor/minor、CurrentBuildNumber、UBRを使い、
互換用の`ProductName`文字列だけには依存しない。

- `python.exe` raw SHA-256: `467014615a5255aca450ae88100dd2caf887da87657f00e3c2171ec44a685aec`
- `python314.dll` raw SHA-256: `f1722bd369d79fecbc85f3ed2790c30c330b9413fd74332f95b086e60dfacc2a`

S1 registryはこの選定値を保存し、S4ではstdlib・ロードした拡張/DLL・CRT・CPU/OS情報を含む
完全なruntime inventoryを追加でhash pinする。配置pathそのものは同一性の代用にしない。
S4の承認対象revisionでLinux 2 jobsとWindows native 1 runtime（3.14.0）の受入を完了してから、
正式pin上のdev/smokeを検証し、全inventoryをcommitして初めてS5へ進む。
S2/S3時点でも同じ共通試験を継続し、Windows受入をS5実行後まで延期しない。

Windowsのnative試験はmockによるWin32成功値の代用では完了しない。
将来の試験時に新規の専用fixture領域だけを使い、公開物のfile write/delete、directory add-child/
delete-child/write/deleteの通常権限が独立reader process/tokenで拒否されることをAccessCheckで確認する。
Windows 3.14.0の受入はこのfixture用publisher部品に限定し、この受入経路にformal rootsへの公開入口は持たせない。
既存のowner/privilege限界を保持し、repositoryや旧artifactのACLは変更しない。
Linux CIでWindows専用項目を明示skipすることは許すが、Windows受入で必要項目がskip・未実行・失敗なら
S4不合格とする。CIからformal holdoutの生成・採用判定は行わない。

非Windows（WSLを含む）、非NTFS、Windowsのbuild/architecture差、Python patch/build/hash差では
formal run/publishを`unsupported_runtime`として、生成・staging・output claim・ACL操作より前に拒否する。
Linuxのvalidate-only、pure/独立read-only再計算、fake publisherの試験は互換性検証として利用できるが、
Windows native受入や正式campaignに読み替えない。CPython 3.12をformalのfallbackにしない。
正式pinが利用できない場合は停止し、変更理由を記した計画改訂・独立再監査・受入試験を先に行う。
S5開始後のruntime/OS更新やsource変化はglobal integrity failureとして扱い、既定の再登録規則に従う。

## 9. 小さなsavepointと停止・再登録条件

各savepointを別commitでレビューし、前段合格だけで次段の実行権限まで得たとみなさない。本savepointの完了範囲はS0だけである。

| savepoint | 成果・検証 | 停止 / 再登録条件 |
| --- | --- | --- |
| S0 plan freeze | 本書、最小限のREADME/roadmap link。式・件数・seed hash・scope・local links・diff/safetyを検査 | 科学的選択が未定、因果support/母数/閾値が曖昧ならdraftのまま停止。採択されたplan commitを次工程へ渡す |
| S1 config/schema/pure validator | 新identity、全seed表、layout/overlap/件数、候補式、strict schemas、I/Oなしsemantic validator、bootstrap goldenをcommit。validationはnot_run/not_evaluated | 登録値と不一致ならrunしない。科学的仕様変更が必要なら新plan/versionへ。既存schemaを緩めて通さない |
| S2 scoring + unit/adversarial | 3候補、観測allowlist、phase state、support/merge/matching。Q1〜Q5/M1〜M9、中央値/MAD/共分散、未来値不変、GT非依存をLinux 3.12/3.14等の共通試験で検証 | pre-event support、候補再探索、profile跨ぎ、丸め順序差、未知phase fallback、event漏洩があれば停止。dev性能に合わせる変更は再登録 |
| S3 deterministic runner | 共通paired materialization、960 datasets/2,880 slots、失敗完全ledger、provenance、nonoverwrite/atomic publisher。fake攻撃試験とWindows native受入を準備 | count欠落、partialをsuccess化、hashだけ偽装したledger、summary+marker改竄、root/ACL越境、candidate間で別入力なら停止 |
| S4 dry/smoke + consumer freeze | §8のLinux/Windows必須受入を完了。正式pin上の新8 dev/2 smoke seedsで全layout/層、独立consumerを検証し、全source/runtimeをcommit | 必須job/実機試験の未実施・失敗、正式pin不一致、再現/golden不一致、source dirty、容量不足で停止。条件削減は新登録 |
| S5 formal holdout | clean frozen revisionから新40 clustersを一回実行。進捗は完了数/工程状態のみ、途中性能による停止・変更はしない | integrity failure、holdoutを見た設計変更、欠けたcellだけの都合よい再抽選で昇格不可。失敗証跡を保全し、repair/replayは別version/root/未使用seedsで再登録 |
| S6 independent analysis / audit | 全inventory照合、read-only再計算、CI・全gate・固定選択。別rootsへ公開しconsumer hashを再検証 | producer/consumer不一致、未知分母、bootstrap null、未完了工程はfail/inconclusive。解析ロジックの科学的変更は同holdoutで正式再判定しない |
| S7 result doc | 全候補・両層・overall、失敗/制約、producer/analysis/audit SHA・hash、全gate、no promotionを含む結果文書。READMEの状態だけ追記 | 数値と監査artifact不一致なら文書公開を止める。文章・リンク訂正以外の結果変更は来歴を分け、凍結artifactを上書きしない |

S4の容量検査はsmokeの全artifact bytesからformal同形規模へ線形換算し、producer+analysis+audit+staging見積りの2倍以上の空き容量を要求する。見積り方法・実測bytes・予想所要時間を保存する。50,000 bootstrapと独立再計算を含む資源を用意できなければformal前に止める。これも性能依存のsample-size変更を正当化しない。

S2/S3では追加で、同phase20点不足、MAD zero、singular covariance、timestamp重複/逆順、recipe変更、NaN/Infinity/bool、current/previous peer quality、episodeの推移merge、pre-event groupに後発targetを足す攻撃、dropout overlap除外による分母改竄、0-alert precision、CI replicateの分母0、signal数で設備時間を4倍する攻撃を固定fixtureで検査する。これらは実装時の検査項目であって、本書で実装済みとするものではない。

誤字・リンクなど科学的意味を変えない修正はappend-onlyの訂正来歴と新commitで可能。seed、layout、quality overlay、scoring、calibration、threshold、persistence、matching、merge、eligibility/denominator、gate、選択、CI、正式入力を変える場合は新preregistrationが必要である。formal dataを見た後は同じseedsを新しい正式な昇格証拠として使わず、新domainの未使用seedsと別rootを採用する。旧結果の再解釈はexploratoryとしてのみ併記する。

## 10. commissioningへの接続と今回の完了定義

phase/recipe/time-since-mode-entryを含むversioned normal profileは、将来のcommissioning recipeで正常運転を繰り返し、設備別envelopeをfit/calibrateしてlockする検証契約へ接続できる。ただし本計画の30秒cycle・20 fit repeats・mode既知という条件を、そのまま実設備のレシピや校正量とみなさない。将来は入力mode/recipeの信頼性、未学習phase、異なるduration、profile更新承認、shadow検証を別計画で扱う。

本計画から発行できるのは研究候補のqualified / no promotion / inconclusiveだけ。Commissioning Profileの製品登録、閾値自動書込み、PLCのPID・interlock・安全上限・運転許可変更、Banto Hub連携の実行、production中のonline learningは行わない。

監査対象revision `4b02201f95e8ffa3a243be716872d95815a554bd`はP0〜P3 0件で独立監査に合格し、
S0としてfrozen・adoptedとなった。監査結果は
[v0.3計画監査結果](results/anomaly-multiseed-v0.3-plan-audit-2026-09-06.md)に記録する。
`SCIENCE_READY=yes`、`FREEZE_READY=yes`、`DOCS_READY=yes`、
`IMPLEMENTATION_READY=yes`、`STACK_READY=yes`である。
**S1以降およびv0.3 config/schema/code/test/run/artifact、winner、性能達成は未実施・未確定**である。

## 11. 科学監査P2への対応記録

初稿`41decf9...`のP2 3件について、下表の修正文と仕様fixtureを監査対象`4b02201...`で追加し、
独立監査でP0〜P3 0件として解消を確認した。`4b02201...`をS0の科学仕様revisionとして採択し、
この新commitはpost-audit status/result同期だけを行う。自己参照hashを本文へ埋め込まず、S1 registryで
`4b02201...`と本同期commitの確定hashをそれぞれ科学仕様・provenanceとしてpinする。
採択後の変更は§9の再登録規則に従う。監査対象でseed、layout、母数、閾値、bootstrap、gate、
候補間の優先順、既存のhash計算契約は変更していない。

| 監査項目 | 修正文 | 反例・次工程の確認 | 現在状態 |
| --- | --- | --- | --- |
| P2-1 最初の候補のsupport失敗後の探索が曖昧 | [§5.1 列挙→選択→検証→確定](#v03-incident-selection) | M1/M5は後続に適格episodeがあってもmiss。M3は窓外episodeを候補から除外。M9はengineering failure | 解消、独立監査合格 |
| P2-2 旧6桁丸めと各split入力が未固定 | [§3.1 観測丸め](#v03-quantization) | Q1のoverlay順序、Q2/Q3のlatent state、Q4/Q5のbinary64/JSON値。全splitは保存観測のみ | 解消、独立監査合格 |
| P2-3 共通CI、Windows native受入、formal pinが未固定 | [§8 runtime/platform](#v03-runtime-acceptance) | Linux 3.12/3.14、Windows実API・DACL/AccessCheck、唯一の正式OS/Python、非対応環境での事前拒否 | 解消、独立監査合格 |

## 12. 実装後のliving status（2026-09-07）

本書は実装前に凍結したpreregistrationであり、上記の「未実施」は凍結時点の記録として保持する。実装後の進捗は、別の結果文書とliving文書で同期する。

S3 deterministic runnerは、実装commit `bdd59c5`、`2a01146`、`bb42d37`、`dc52266`を経てmainへ統合され、独立監査P0〜P3 0件、`S3_READY=yes`、`INTEGRATION_READY=yes`となった。固定inventory、paired materialization、全枠ledger、安全停止、確認済み証拠保持、provenance、non-overwrite publicationの土台を確認したが、性能結果・winner・promotion・本番利用許可は示さない。顧客データは対象外で、formal output rootはS4受入まで閉鎖する。

CI run [34044283016](https://github.com/tyaro/banto-ai/actions/runs/34044283016)はPython 3.12/3.14の全工程greenだった。ローカル全体探索は`Ran 686 / 3667.360s / FAILED (errors=1, skipped=2)`で、`SavedEvaluationTests.setUpClass`の`compute_evaluation`中`copy.deepcopy(scores)`にMemoryErrorが発生し、同classの5試験は未実行だった。単独再実行は5/5 PASSだが、ローカルの根本原因、peak memory、commit limitは未解決であり、S4前の容量確認・同一revision再確認事項として残す。詳細は[S3監査結果](results/anomaly-multiseed-v0.3-s3-audit-2026-09-07.md)を参照する。

次段階はS4のplatform/runtime/native Windows acceptance、dry/smoke、独立consumer freezeである。S4受入が完了するまでformal dev/smoke/holdoutの実行権限は付与しない。

## 13. S4-A engineering inspection status note（2026-09-07）

本節は科学仕様本文を変更しない実装後status noteである。S4-Aはreceipt schema、pure semantic validator、
read-onlyのsource/runtime inventory、resource guardを`8befc5bb6cf1c7c424b6024c90b94fb149a9e4f9`と
監査修正`e61d14c4b31ed3c4711157e4a94446513e390422`の2commitで実装・mainへ統合した。初回独立監査の
P2（実行Python imageのreceipt内部照合不足）とP3（argparse入力反射）は後者で修正し、再監査はP0〜P3 0件、
`PREVIOUS_P2/P3_RESOLVED=yes`、`S4_A_READY=yes`、`INTEGRATION_READY=yes`となった。

local検証はA `27/27 pass`（統合後独立再実行 `27/27`、1.441秒）、D2関連 `6/6 pass`（34.077秒）、
S3 specialized `73/73 pass`（438.462秒）、in-memory compile 116 files、repository safety、diff-checkである。
修正候補のfull local suiteは未実施であり、旧候補の714件結果を転用しない。CI [run 34057314195](https://github.com/tyaro/banto-ai/actions/runs/34057314195)
はmain `e61d14c4`上でPython 3.12が15m10s、3.14が15m43s、compile/unittest/manifests+smoke/
synthetic data/benchmark/safety全成功だった。

acceptance statusは常に`not_completed`、`S4_ACCEPTED=no`、`FORMAL_PERMISSION=no`である。Windows exact
runtime基本pinは一致するが、current checkoutのworkflow working bytesがGit blobと異なるため、実receipt
収集はfail-closedした。これは受入証拠ではなく、byte-identical管理checkoutでS4-Bで再確認する残課題である。
artifactは617 entries / 461 files / 36,352,494 bytesでbefore/after差0、formal v0.3の5 rootsは未作成、
科学5 config・9 schema・historical 88・D2 current-only 31は保全した。MemoryErrorはglobal stopへ強化したが、
実OOM根因やcommit limitの解明は主張しない。次はS4-Bのtemp-only native publisher/DACL/restricted-token/
race harnessであり、S4全体、dev 8 / smoke 2、formal acceptance、S5 holdoutは未実施である。
