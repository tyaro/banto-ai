# 保存された8週補正の診断条件（2026-10-14）

[前の一回結果](../results/store-sales-weekly-ridge-cohort-2026-10-14.md)の主MSE悪化を、原因の候補と未回答へ分解する。本条件を診断計算前に固定する。新fit/forecast/旧scoreの再集計・方式選択・再実行を行わない。

## 原入力と対象

閉鎖weekly-ridge-readinessのfit feature-label ledger、閉鎖weekly-ridge-cohortのdevelopment ledgerとsummaryをpin照合して読む。正尺度15店のfit630行と、各24採点可能の2015保存出力を対応させる。尺度0の3店は元の役割と原summaryだけを引継ぎ、別店尺度で正規化しない。archive/新quantity/2016/2017/予約群を読まない。

## 数式による誤差の分解

Bは保存基準総量、Pは保存8週候補、Aは保存actual、uは保存fit尺度。e=(A−B)/(14u)は必要だった補正、c=(P−B)/(14u)は発行された補正とする。

`(P−A)^2/(14u)^2 − (B−A)^2/(14u)^2 = c² − 2ce`

新診断はE[c²]（補正量の二乗）と2E[ce]（必要補正との整合）を各店と店macroで保存。差を原summaryのMSE差と照合する。元MSEを再計算せず、別方式の予測を作らない。この恒等式の照合は独立評価や因果実験ではない。

非ゼロcの向き一致/逆向き/必要補正e=0、|c|>2|e|の件数を記述する。c=0は別に数える。件数だけで損失への寄与を決めず、二乗量と整合を併記する。後から外れを除去/補正量を縮小/良い店だけ選ばない。fallbackのc=0も全採点対象に含める。

## 時間による関係の違い

fitの保存yと8特徴について、各店のy平均・population std、および各feature-yのPearson相関を全8列で記述する。2015は保存inputのfeaturesがある窓だけの同じ記述を別欄に保存する。前者は各42、後者は各21窓の限定支持で、fallback45窓を主誤差から除いた評価に置き換えない。分散0の相関は理由付きnull。

全8列を事前固定し、都合の良い列や年度を選ばない。これらの残差や相関を予測入力に使わない。関係の変化を「ドリフトの原因確定」「shared係数が必ず誤り」「店別モデルなら改善」としない。時系列の重複・共通日・少数年があり、独立標本数/統計的有意性/信頼区間を補わない。

## 診断後の判断

前の8週候補の不採用・進捗未達は維持する。診断から係数grid、NN、店選択、2017追試へ進まない。次の仮説は、予測時点までの履歴から決められるものと、営業/供給/予定等の追加情報が必要なものを分けて設計する。関係が見えても新しい独立評価の代わりにはしない。

新script/設計/source/input pins/診断/原stdio・例外をfresh rootへ保存。旧root追記0。900秒2GiB/output1GiB/single32MiB/files32、通常24file768MiB/失敗8file256MiB、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16files維持。formal_permission=false/credit0/native reader禁止/登録holdout未読、追加agent0/CARE手動待ち・自動確認0/automation PAUSED。Gitは集約docsだけ、原quantity/ledger/係数/予測はlocalのみ。
