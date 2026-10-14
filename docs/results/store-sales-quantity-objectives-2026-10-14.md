# 需要予測の平均・中央値・分位点の使い分け（2026-10-14）

## 今回の結論

**集約する数量見込にはmean、典型値と絶対誤差の評価にはQ50、欠品/余剰の意思決定には目的に応じたquantileを分けて使う。** 次の独自モデルはmeanと総量quantileを別出力にする。[次候補の具体設計](../research/demand-mean-and-quantile-model-design-2026-10-14.md)

今回の公開データで実装するのは期待販売数量と不確実性の研究。実メーカーの最適生産量や潜在需要の推定とは区別する。実務条件が未確定でも、公開数量研究を止める条件にはしない。

## 使い分け

| 用途 | 使う量 | 合う評価/学習 | 注意 |
| --- | --- | --- | --- |
| 月/週/14日の販売・出荷見込、資材/能力の平均的な見込 | 条件付きmean | 原単位MSE/RMSE、Biasを併記 | 計画する対象・単位・知識締めを一致させる |
| 典型的なケースの代表値、同じ大きさの過不足を絶対誤差で比較 | Q50/median | MAE、Q50 pinball | 集計平均数量と同じではない |
| 不足と余剰の負担が異なる補充判断 | 目的に応じるquantile | 対応するpinballまたは意思決定費用 | p90等を固定で採用しない |
| 予測の不確実性を示す | 14日総量Q10/Q90等 | pinball、coverage、幅、interval score | 費用を付けたdecision量とは別 |

点予測の統計的対象と評価スコアを一致させるという根拠は[Gneitingの原論文](https://arxiv.org/abs/0912.0902v2)。二乗誤差と絶対誤差では求める代表値が変わる。

meanは平均的な数量見込であって、在庫を無視してそのまま発注する数量ではない。既存在庫・確定注文・予定入庫を同じ範囲で照合し、供給制約を入れた判断は別に行う。

## 数点の例で確認できること

数量20が確率0.8、100が0.2なら、mean36、Q50は20。

| 予測する量 | 期待絶対誤差 | 期待二乗誤差 | 期待Bias（予測−実績） |
| --- | ---: | ---: | ---: |
| median20 | 16 | 1280 | −16 |
| mean36 | 25.6 | 1024 | 0 |

medianがMAEで良くても、平均数量には不足することがある。今回のモデルの負Biasがこの理由だけで生じたとは断定しない。

### 集約

同じ情報・単位・対象に条件付けたmeanは加算でき、独立性は不要。medianとquantileは一般には加算できない。[FPP3の集約説明](https://otexts.com/fpp3/toolbox.html#bias-adjustments)

- 日次20/100が確率0.6/0.4、2日独立なら、日次medianの和40に対し2日総量medianは120。各日のmean52の和104は総量mean104と一致。
- 日次20/100が確率0.8/0.2なら、日次Q90の和200に対し2日総量Q90は120。

そのため、日次meanから14日meanを加算し、総量quantileは総量を直接学習する設計を採る。旧候補の日次pointは総量Q50の整合配分で、各日の周辺Q50ではなかった。この既存解釈は変更しない。

### 3分位点だけではmeanを作れない

数量20/40/60/80の確率が0.20/0.35/0.40/0.05ならmean46、Q10/Q50/Q90は20/40/60。最後の数量80を800へ変えると、3分位点は同じだがmean82になる。

平均がQ90より大きくなることもある。meanを3分位点の平均にしたり、区間内にclipしたりしない。mean専用のhead/目的を用意する。

## 意思決定分位点は実務条件から選ぶ

単一期間、1単位ごとの不足費用Cuと余剰費用Co、制約なしの単純modelでは、選ぶ分位点は `Cu/(Cu+Co)`。費用非対称性と最適分位点の関係は[Olivares・Terwiesch・Cassorlaの原論文](https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/8-Structural-Estimation-of-Newsvendor.pdf)で確認した。

上の20/100例で仮の費用Cu=Co=1ならQ50→20、Cu=9/Co=1ならQ90→100になる。費用不明なら量と分位点をnull、理由 `unknown_underage_or_overage_cost` として保存した。実企業の費用をこの仮例から推定しない。

賞味期限・ロット・能力・複数period・入庫遅延・代替品等のある菓子PSIでは、この単純式だけで最適判断にはならない。また総量80%予測区間を、欠品確率80%やfill rateと同一視しない。まず予測の分布と意思決定の契約を別にする。

## 保存trainだけでの記述

[診断前設計](../research/demand-quantity-objective-design-2026-10-14.md)に従い、2013–15の保存train ledger2973行と固定尺度を読んだ。新予測や係数fitは0。残差の符号は `actual_total−mean28_total` で、過去のBias欄とは逆。

| 店舗 | 元重複991窓の残差mean / median | 固定非重複71窓のmean / median |
| --- | ---: | ---: |
| 5 | 0.030 / −67.006 | −4.513 / −90.300 |
| 11 | −9.494 / −55.000 | −6.026 / −53.500 |
| 12 | −2.805 / −34.000 | 1.998 / 0.000 |

固定非重複は2013-02-26+14*kでeligible起点と一致するもののみ。欠測の窓は日付をずらして補わない。71窓も時系列・店舗で依存があり、独立した71年の試行や未見評価ではない。

店舗12の内訳では、ゼロ区間label接触73窓のmean−568.123/median−446、contextだけ接触56窓はmean444.661/median−158.25、非接触862窓はmean16.001/median−28.5。区間や状態によりmeanとmedianの差が変わる。

これは無条件のtrain記述で、条件付き予測分布や将来に使える固定補正係数ではない。モデルの過小Biasの原因も未特定。2016/17 quantityや原predictionを読み直してRMSEを探索する処理は行っていない。

## 次のモデルで変えること

現在の候補は `daily_point=total_Q50*shares`、lossは日次MAEと総量pinballの等重み。mean用出力はない。現在のpointに「平均」という表示を付けて対応済みにしない。

次は独立mean headで `daily_mean` と `total_mean` を出し、原単位二乗誤差で学習する。meanの同じ出力へMAEを重ねず、quantileは別head。meanのcheckpoint選択はvalidation MSE、量の評価はRMSE/Biasを主にし、MAE/WAPEを補助欄へ分ける。

有限model・共通backbone・少標本では真の平均へ到達する保証はない。MSEは極端値にも影響されるため、データ意味と状態別内訳を保持する。今回testのBiasを足してmeanと呼ぶ処理、Huberや実績依存重みへの無断置換はしない。新候補の実装と少数機構確認は次unitで、一回学習は設計/確認後に別に固定する。

## 元失敗と保全

新6目的確認は一回all passed。初回集計scriptのoperation label `quantity-purpose-and-train-description` が32文字上限を超え、`ValueError: unsafe operation label` で数量集計前に停止した。

原script/失敗root/全stdout・stderr・exitを閉鎖保存し、passed6を反復していない。別continuationでoperation labelと新record rootの2文字列だけを変更し、未開始の集計だけを完了した。元failedをpassedへ書き換えていない。実行側上限やEvidenceStoreの制限は緩和していない。参照URLのMIT OCW読取りはweb Internal Errorで断念し、著者公開の原論文へ変更。これはmodel/helperの実行失敗とは別。

文書helperの実行前にラベル長の誤記37を実測38へ訂正する際、foreground読取りが既定cp932で `UnicodeDecodeError: 'cp932' codec can't decode byte 0x94 in position 1085: illegal multibyte sequence` となった。元tool excerptを保持し、UTF-8を明示した新prepで訂正。元prepは未実行・不変、エラー前の新root/文書変更は0。このexcerptは原process全stdio/identityではなく、診断・モデル・新6確認の失敗に加えない。

continuation0.070380秒/OS peak private/pagefile26,816,512B。主要保存先（全閉鎖・追記/再実行禁止）：

- `artifacts/representative-store-sales-quantity-objectives-20261014-records`：集計前の原failed。
- `...-quantity-objectives-launch-20261014-records`：新6確認exit0、元集計exit1と全stdio/原failure。
- `...-quantity-objectives-continuation-20261014-records`：有限例・train記述・source/pin。
- `...-quantity-objectives-continuation-launch-20261014-records`：未開始部分だけexit0、元failedのcount/bytes保持。
- 文書 `...-quantity-objectives-doc-20261014-records`、Git後 `...-quantity-objectives-git-20261014-records` post-saveを優先。

新model/forward/fit/weights読込/旧確認/CI反復0。正式gate/credit0/native reader禁止/登録holdout未読は不変。実行900秒2GiB/output1GiB/single32MiB/files32、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16filesを維持。生ledgerはlocal、Gitは独自codeと集約文書のみ。

基準を維持し、メーカーPSI採択/校正保証/TimesFM同等再現を補わない。直接研究ACTIVE/automation PAUSED、追加agent0、CARE手動報告待ち。
