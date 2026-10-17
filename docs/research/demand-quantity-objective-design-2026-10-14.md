# 需要数量の平均・中央値・意思決定分位点（2026-10-14・診断前設計）

## 本unitで決めること

公開Store Salesの過去数量研究では、期待数量のmean、代表値Q50、総量のQ10/Q90を別出力にする方針を整理する。生産/補充のdecision quantityは費用・在庫・納期・期限などから別に決める。実メーカーの費用や欠品/潜在需要は今回の公開データから補わない。

まず式と有限分布の少数例で、目的・損失・集約・分位点の意味を確認する。次に保存済みtrain側診断ledgerだけから、基準に対する残差の平均/中央値と、既存modelの日次MAE＋総量pinballという目的の関係を記述する。2016/17のquantity/予測、モデルforward/fit/旧確認/CIは使わない。第三候補の学習やbias係数補正を始めない。

## 理論と参照資料

点予測の指示対象とスコアを一致させる。二乗誤差は条件付き平均、絶対誤差は中央値、pinballは指定分位点を対象とする。[Gneitingの原論文](https://arxiv.org/abs/0912.0902v2)

同じ情報に条件付けた数量の平均は期間・店舗で加算できる。中央値や任意分位点は一般に加算できない。[FPP3の変換と集約](https://otexts.com/fpp3/toolbox.html#bias-adjustments)

単一期間・線形の不足/余剰費用・制約なしという単純decision modelで、最適分位点はCu/(Cu+Co)。これは費用比と予測分布から決める量で、p90の固定採用やPSI全体の最適方針ではない。[Olivares・Terwiesch・Cassorlaの原論文](https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/8-Structural-Estimation-of-Newsvendor.pdf)

モデルのmeanを過去sample平均と同一視しない。Q10/Q50/Q90の3点だけから平均は特定できない。分位点を平均してmeanとして返す実装は作らない。meanは分位点の範囲外になる場合もある。

## 計算前に固定した確認とtrain記述

- 少数例：非対称分布でmeanとmedianの最適lossが異なること、meanの加算、median/quantileの非加算、同じ3分位点でも異なるmean、費用比に応じるdecision量、費用未知を未定として保持、ゼロと不正値の区別。
- train ledgerは元991共通origin×3店舗。残差actual_total−mean28_totalを、元固定train平均×14で除算する。店舗と長いゼロ区間のlabel/context-only/neitherを分けてmean/median/stdを記述。数値を予測補正係数に使わない。
- 重複窓の影響を明示する補助記述は、2013-02-26+14*k、2015-12-18以下、元eligible originと一致するものだけ。起点列を後から探索しない。欠測で外れた窓を日付をずらして補わない。
- 元train支持ledgerとinputのSHA、原source全文を新rootへ保存。原学習log、checkpoint、model weightsは再計算/読込しない。

## 次の出力設計の条件

期待数量はmean用headと原単位二乗誤差で学習する。日次meanから14日meanを整合的に加算し、総量quantileは別headで直接pinball学習する。日次整合配分pointを日次Q50と呼ばない。meanをQ10–Q90内へclipせず、log量の逆変換中央値をmeanと呼ばない。

mean選択には固定尺度MSE/RMSEを主に使い、Bias/MAE/WAPEは補助、quantileにはpinball/coverage/幅を別に使う。day-specificやtarget-sizeに依存する実績重みを無断追加しない。有限model/少標本で真の平均やbias0が保証されるわけではない。

新学習の前に、構造・loss重み・origin/schedule・validation選択と回顧評価を別設計で固定する。今回は目的整理とtrain記述まで。基準と不採択を維持。

実行900秒2GiB/output1GiB/single32MiB/files32、診断16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files維持。閉鎖root追記・旧unit反復・追加agent0。直接研究ACTIVE/automation PAUSED、formal_permission=false/credit0/native reader禁止/登録holdout未読。独自codeと集約文書だけGitへ保存し、原数量/ledger/fit/重みはlocalのみ。
