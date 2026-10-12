# layout10 C0 core実評価・差分とpersistenceの設計確認（2026-10-12）

同保存dev layout10 coreを既存CLI C0で一回fresh評価。機械0/10・sensor0/10・precision0/3・clean誤警報3。全20未検出、delayは原null。CLI exit0/complete/1cell successを性能合格へしない。
人のC0設計への質問に合わせ、現在コードの定義・episode条件・異常生成を読取り、今回の原score13920行の差分と正規化式を独立に照合した。元モデル・旧試験/CI・score/episode APIsの再実行0。

## C0の組み方について

**確認した範囲で、差分計算の実装は定義どおり。ただし、差分スコアと連続2点超過の組合せは今回の異常形状に合っていない。**

C0はresidual=x(t)-x(t-1)、score=abs(residual-center)/scale。centerはcalibration residualのmedian、scaleは1.4826*MAD。fitは定義上no-opなのでfit_samples0は学習処理の脱落を意味しない。calibrationは各profile290点、48profile calibrated。
保存candidate definitionはC0 threshold4.0/persistence2/second-exceedance。scoringとepisode builderもその閾値と連続条件を使う。利用可能13920行について、原dependenciesの現在値−直前値がresidualへ一致し、保存profile center/scaleからのscoreが原scoreへ一致した。全14400scoreのthreshold_exceededも実4.0へ照合。calibration全経路や一般的な実装無欠陥の証明ではない。
生成のsensor spikeは名前に反して単点だけではなく、start_sample <= sample < end_sample の3観測へ一定magnitudeを加算する。一定加算Aは隣接する異常点同士の差分で相殺され、開始と終了の応答は3秒離れる。normal変動・量子化を除いた構造の説明例：

| 観測位置 | 直前正常 | 異常1 | 異常2 | 異常3 | 復帰 |
| --- | --- | --- | --- | --- | --- |
| 加算成分 | 0 | A | A | A | 0 |
| 加算成分の一次差分 | — | +A | 0 | 0 | -A |

大きなスコアを出しても二つの超過が連続しなければepisodeは成立しない。今回の全20対象窓は利用可能7行・maxstreak1で、欠測やphase不能を理由にした未検出ではない。machineの乗算異常は同じ式で厳密に一定加算と同一にはならないが、今回の原窓でも連続超過は成立していない。
候補として再設計するなら、単発超過と別の誤警報抑制、短窓での差分証拠蓄積、又は水準・phase残差を検出するC1のような方式を比較する。C0の名前のまま設定を変更して過去結果へ混ぜず、別候補/別設定としてdevで検証する必要がある。これら代替案は未実装・未評価。

### 生成区間のmetadata訂正

analysis-continuationのC0-design-reviewは一つのfieldでsensorをfour-sampleと誤記していた。overlay_sampleのend-exclusive条件と原eventのend-start=3を照合し、この-save/C0-design-reviewで3点へ訂正。旧rawとpinを別labelに保持、閉鎖rootへ書換え0。実モデルの入力・残差・score・指標変更0。今後の参照は-saveの訂正版を優先。

## 入力と結果の対応

- run dev-layout10-core-c0-20261012、dataset anomaly-v03-dev-seed-2486912926863618161-layout-10-core。
- 元manifest C:\Users\TKent\.codex\worktrees\v03p\banto-ai\artifacts\v03-runs\r1\run\attempts\chunks\010\attempt-0001\result\payload\manifest.json、pin {"bytes": 75715, "sha256": "1ede2721456af4d88ae82d606decb08b3e8fb2121295e9aea89ffddeda0b0c63"}。
- seed2486912926863618161/layout10/core/dev。input10 pins→新snapshot→fresh fit/calibration→原profiles/scores/episodes/events/incidents/metrics。元生成C0/実評価C0は別field。
- actual checkout 76b68e690c38bc73e0494bd8803dff46f396391f、計算661b27511826fcc87cb4a02930f276afbb8f95d9不変。元payload書込み/生成/replay/追加agent0。
- runtime {"executable": "C:\\Python314\\python.exe", "machine": "AMD64", "python": "3.14.0 (tags/v3.14.0:ebf955d, Oct  7 2025, 10:15:03) [MSC v.1944 64 bit (AMD64)]", "system": "Windows"}、elapsed 16.05946290004067秒/privatepeak 149454848B。
- observations {"bytes": 9600481, "sha256": "65d7034a0abc408d7d8e20f589f5fc1e6dd9b8693c325e431b636b31118ad762"}、configuration {"bytes": 5504, "sha256": "73ca5f95c0877fdf0735dd7e97c0a661d0bf8116572f33aab6a0f47d5d1787ca"}、manifest {"bytes": 8033, "sha256": "b069a96dcfa2540a327ad0dde0fa895ce229c1b07fe72bfd8fb2431e101bf51e"}、evaluation {"bytes": 13899411, "sha256": "de2e1b1982455dad5fe38fbb29fd2be86f04c0fbcb8403fcca9afb6032f4ea00"}。
- 閾値 {"c0-diff-control": 4.0, "c1-phase-level": 6.0, "c2-phase-conditional": 6.0}、operator>/persistence2。科学式・GT・matching・設定変更0。declared16/science117 pin一致はfull loaded runtime/native認証ではない。

## 原指標・availability

| 指標 | 原値 |
| --- | --- |
| machine recall | 0/10 |
| sensor recall | 0/10 |
| precision | 0/3 |
| clean_rate | 3/3365、原value 25.676077265973255 |
| effective clean | 3254秒、原value 26.551936078672405 |
| burden | 3/20、原value 15.0 |
| detected delay | count0、min/max/mean/median原null |

48calibrated/fit各0/cal290/14400score、13920利用可480phase不能/null residual-score/thresholdfalse。18000observations-mask対応、欠測0。source3/equipment3/events40/incidents20、全equipment3 clean/未対応/matchednull。source内訳 {"conveyor-01.motor_temperature": 1, "motor-01.vibration_feature": 2}。clean-rate/burdenの原valueは単純確率へ変換しない。
全20no_candidate_in_window/candidate0/causalfalse/matchednull/delaynull、全target窓7rows利用可/maxstreak1/phase不能0。原全20event/incident・四target窓・全episodes・不能480を新analysis-continuationへ保存。入力対応・保存・状態分類不具合観測なし。

## 原対象窓の抜粋

### cycle0 machine conveyor-01.conveyor_speed

| sample | residual | score | streak |
| --- | --- | --- | --- |
| 7334 | -0.7139829999999999 | 134.1567757011945 | 1 |
| 7335 | -0.0004469999999999752 | 0.09732206501640103 | 0 |
| 7336 | -0.002342999999999984 | 0.45354336862854516 | 0 |
| 7337 | 0.71523 | 134.3643835812005 | 1 |
| 7338 | -0.0016979999999999773 | 0.33236048844403343 | 0 |
| 7339 | 0.0007799999999997809 | 0.13320722798571494 | 0 |
| 7340 | -0.0020779999999998022 | 0.4037550535139447 | 0 |

### cycle0 sensor conveyor-01.motor_temperature

| sample | residual | score | streak |
| --- | --- | --- | --- |
| 7341 | 8.033731999999997 | 200.07145157058935 | 1 |
| 7342 | 0.047253000000004874 | 0.29744180759662947 | 0 |
| 7343 | -0.026451000000001557 | 1.5461921161353323 | 0 |
| 7344 | -8.013463999999999 | 201.3335593701093 | 1 |
| 7345 | -0.020545000000002034 | 1.3984592664452322 | 0 |
| 7346 | -0.019465000000000288 | 1.3714441161462856 | 0 |
| 7347 | -0.01324899999999829 | 1.2159569177592162 | 0 |

### cycle9 machine conveyor-01.conveyor_speed

| sample | residual | score | streak |
| --- | --- | --- | --- |
| 8954 | -0.711838 | 133.7537721694181 | 1 |
| 8955 | -0.0028040000000000287 | 0.5401562488844595 | 0 |
| 8956 | 0.0009010000000000407 | 0.15594076054750913 | 0 |
| 8957 | 0.7144459999999999 | 134.21708532063514 | 1 |
| 8958 | -0.0023940000000000072 | 0.4631252707826736 | 0 |
| 8959 | 0.0072190000000000865 | 1.3429693450525368 | 0 |
| 8960 | -0.002607000000000026 | 0.5031438033087248 | 0 |

### cycle9 sensor conveyor-01.motor_temperature

| sample | residual | score | streak |
| --- | --- | --- | --- |
| 8961 | 7.977434000000002 | 198.663211819175 | 1 |
| 8962 | 0.05262400000000156 | 0.43179215227747975 | 0 |
| 8963 | -0.047682999999999254 | 2.0772899597892636 | 0 |
| 8964 | -8.033891000000004 | 201.8445209211795 | 1 |
| 8965 | -0.02400300000000044 | 1.484957775457791 | 0 |
| 8966 | 0.00873600000000252 | 0.6660235109801386 | 0 |
| 8967 | 0.03831299999999871 | 0.07381639678888953 | 0 |

## 保存済みC0 core比較

| layout | machine | sensor | precision | clean | delay count |
| --- | --- | --- | --- | --- | --- |
| 0 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 1 | 0/10 | 0/10 | 0/3 | 2 | 0 |
| 2 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 3 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 4 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 5 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 6 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 7 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 8 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 9 | 0/10 | 0/10 | 0/3 | 3 | 0 |
| 10 | 0/10 | 0/10 | 0/3 | 3 | 0 |

旧60board＋新1=61、C0 core11layouts。layout0–9の60組完成は保持、layout10はC0core1件だけ。同合成dev seed1/61独立datasetではない。旧保存manifest/config指標だけ比較、旧model再計算/replay/試験/CI反復0、bootstrap/統計CI/勝者/採択0。

## 補助script失敗保全・次unit

初回analysisは設計要約が未定義factsを参照しNameError/failed。原script/live/execution/failure/tracebackを閉鎖保持。別analysis-continuationで参照先を後続保存analysis labelへ限定訂正し未保存分析を完成。元モデル/原script再実行0、failed書換え0。model/CI/native/Sol容量failureへしない。
- model artifacts/representative-layout10-core-c0-20261012-records、原failed ...-analysis、分析 ...-analysis-continuation、docs/Git ...-save、最終 ...-final/root-closed.json post-save label優先。
- 設計確認の訂正版は-save/C0-design-review、旧duration rawは-save/original-design-review-before-duration-correction。helper failureは-continuation/prior-analysis-failure。
- DATA artifacts/representative-anomaly-evaluation/dev-layout10-core-c0-20261012/root-closed.json、{"bytes": 26940796, "files": 19, "manifest_pin": {"bytes": 2226, "sha256": "3dea06812394dc4220bea65af92329cdea3092b9ba49bfdafb9285e4c6a61257"}}。
- 次は同chunk010/layout10 core C1、新ID dev-layout10-core-c1-20261012。同manifest1ede/input10、本文C0読取済み/次model未実行。

prepare_result_indexを実使用し、handoff/report/index3文書を継続送信承認内で一回[skip ci] Git保存。原返値/pins/HEAD-upstream-remote-cleanは-save/-final保持。旧failedと今回analysisfailed1を別に保持。
実行900秒2GiB/output1GiB/single32MiB/files32、Git30秒16entry512KiB/stdout1MiBstderr128KiB、protocol/native不変。新検証16MiB512files/part256KiB/失敗予備枠維持。closed/frozen root追記整理0/fullstdio-native回収claim0。
ACTIVE/automation詳細転記0。CI381385/4130再照会downloadverifier0。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読/正式5残件・最終受入未完了/create_native早期拒否/7役reader禁止/追加agent禁止/caps-unknown原owner保持。未完了formal/nativeをdev開始条件へ戻さない。Sol容量/人停止は原保全後PAUSED、重複再試行なし。
