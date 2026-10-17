# 制約付き共通残差：既読2014への単一適用契約

2026-10-15 JST。人の明示依頼「2015再評価停止のまま、実データ適用条件固定→2014検証、Astra確認」に基づく。本契約が以前の人工限定工程に代わり、下記一巡だけを許可する。旧coreの人工限定docstringは当時の履歴であり、今回は旧ソースを変更せず本契約で範囲を明示する。2015停止とheartbeat PAUSEDは継続する。

## 仮説と一仕様

MSEだけで補正方向を決めた後のalpha縮小ではなく、全pastQの両側非増加を係数推定へ直接入れることで、固定3特徴に有効な別方向があるかを調べる。改善・非ゼロ可行解の存在は前提としない。

既存3係数/λ=1/全係数罰則、正規化MSE目的、全pastQのunder/over非増加と学習row非負、40店Qcell支持、入力支持/尺度/重みを維持する。Q別MSE hard制約、後段alpha、店季節別係数、currentQ限定、soft penalty、特徴/λ/期間/許容差探索はない。旧exact core、v2入口、独立verifierを変更しない。

学習は許可10店(6,7,10,13,15,17,19,23,26,27)の2013–2014だけ。保存済み検証済みprefixをfresh JSON copyし、2014-01-01/04-01/07-01/10-01の順に4回fitする。観測完全prefix210/270/330/400、特徴適格210/250/310/380を固定照合する。学習関数には全input/label reader/index/sourcepathを渡さない。過去Qは年をまとめた発行Q別。目的の適格行重みと制約の全観測完全行・店等重みを混同しない。特徴不支持行もrisk分母に残す。欠測0仮定で学習しない。

## 数値・予測の固定

stdlib Fraction active-set/cutting-planeと既存exact verifierを用いる。B/YはF(math.fsum(日次))、unit=14F(u)、xは保存binary64のexact Fraction。重みはexactな1/(40n)・1/(10n)。4stateのβは有理数文字列、float表示を採用状態にしない。各fitは独立verifierの元hinge/非負/全cut/KKT/gap0確認が済むまで未確定。ゼロ最適・非ゼロ不可行・数値失敗を分ける。

予測は各発行日のQ開始stateだけを用い、後のstateを遡及適用しない。P=max(B+unit*xβ,0)。入力不支持/B0はP=B。日次配分は次に固定する。

- Δ=P−B=0、入力不支持、B=0は旧baseline日次値をそのままコピー。この場合、ΣFraction(B_d)とcanonical Bの端数差は明示的な例外として許す。
- P=0<Bは全日0。
- その他のΔ≠0はFraction(B_d)*P/ΣFraction(B_d)で配分し、exact日次和=Pとする。

全日次が必ずcanonical Pへ一致するとは主張しない。表示floatは補助で、主総量採点はcanonical B/Y/Pを使用し表示日次から再集計しない。配分分母・copy例外・exact日次和・表示roundoffは予測台帳へ保存する。canonical Bと日次和の差を改善として数えない。maskの0と非負を維持。B0/xNoneは早期fallbackで、係数状態の検証はcertificate確認で別に済ませる。

## 凍結・採点・採否

全4stateと全260発行予測を採点前に保存し、それらのpinをfreeze markerへ保存してから、2014ラベルだけを別経路でread_available(asof=2014-12-31)し採点する。後cutoffで既に確定した過去ラベルを使うことと、outer成績を見て再調整することは区別する。同origin未来targetの先読みはない。

observedはraw nullを欠測のまま、assumed_missing_zeroは従来どおり休業相当mask位置だけnull→0の仮定として別採点。真0/null/営業unknown/01-01・12-25休業相当を維持する。全260、通常250、元日10、Q別all/normal、年末を別群で示す。2014の通常250は旧2015の250と別。支持は観測3630日/250総量、仮定3640日/260総量、元日真0全10店を照合する。

主総量MSEは店別平均((P−Y)/(14u))²の店等平均、under/overは店別平均max(±(P−Y),0)の店等平均。各modeの観測完全総量集合は候補/Bで同じ。営業相当日の数量MSE（非休業mask・観測値のみ）、全観測日次MSEもexact日次から補助報告する。

今回はpaired差をexactに求め、僅かでも正なら違反とする。旧floatのMSEtol1e-12/数量tol1e-8での判定から厳密符号へ変えることを成績前に固定する。表示丸めで違反を消さない。候補と対照とも同じcanonical総量・尺度・窓・店重みを使い、旧報告値から差分を作らない。

必須条件はQ1–Q4のallとnormal、および元日10について、両modeそれぞれ総量MSE/under/overがB以下。全260・通常250・年末は集約/記述報告。全必須条件通過と同値を分け、「本一巡で総量改善」は必須条件全passかつ全260の両mode総量MSEが厳密減少した場合だけとする。いずれも既読2014内の結果で、製品採用/独立性能/未知保証ではない。outer違反QをBへ事後差替えせず原予測と違反を残す。

## 上限・failure・終了

旧上限（512row/64round/512cuts/4096pivot・全65536/bit8192/cert512KiB）を維持する。scoreの有理数中間/結果にもbit8192を確認し、上限で失敗なら未完了として残す。新モデルartifactは通常24files/768MiB、総32files/1GiB、単一32MiB、failure予約8files/256MiB。EvidenceStoreは16MiB/512files/part256KiB/failure2MiB16files。

準備fixture・一巡・独立readback・文書閉鎖の各工程で親900秒/子870秒、Mac sampled physical footprintとpeak RSS各2GiBを別々に適用。工程全体が合計900秒以内という意味ではない。OS hard capではなく一部bit検査は累積演算後。全stdio/exit/source/旧state pin/途中state・予測/失敗/closureを保存する。

数値failure・上限・cycle・証明拒否なら後Qと採点へ進まず終了し、B代替・上限緩和・救済再fitを行わない。独立readback不一致なら成功認定を止め、failureとして閉鎖して報告する。既存変更/失敗/closed rootsは上書き削除しない。結果が改善/悪化/全B/failureのいずれでも一巡で終了し、新候補や2015確認へ接続しない。

新取得/2016–17/予約31–54/販促/正式holdout/Windowsnative/CARE/課金API/研究データ外部送信/Git push/本番採用は対象外。Mac共通処理とWindows固有/OS依存包括suiteの結果は分ける。Astra方法・進め方監査はread-onlyで確認し、実装後・結果も確認する。

## 起動前v2補強

Astraの実装レビューにより、予期しないモデル全体の40店Qcell支持不足は即例外停止とし、行単位のfeature不支持B固定と区別する。failure予約枠へ完成済みの部分予測そのものも保存する。新入口はtools/demand_constrained_2014_v2.py、旧v1と人工6fixtureのcomplete準備記録は保持する。係数/目的/制約/数値上限/採点規則は変更しない。追加の停止・保存fixtureと旧統合6fixtureを新入口に対して確認してから一度だけ実データ適用する。
