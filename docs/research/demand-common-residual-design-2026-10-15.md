# 共通3係数残差モデル：2014だけの一巡時系列診断契約

2026-10-15 JST。人の「続けてください」に基づく次工程。[prefix事前契約](demand-prefix-adapter-design-2026-10-15.md)の10fixture/独立readback complete後、Astra方法・評価監査担当（既存gpt-6-astra2名read-only）に最終仕様を提示し、両者が明確な矛盾なし、別契約凍結後に2014-only一巡可能と確認した。新性能計算前に本契約を保存する。両担当は新計算/編集/2015参照なし。

## 固定入力・対象・推定

FIT10既読2013/14だけ。前年特徴/成功gate/店・季節偏差/分類器なし。14真観測かつ過去14日全て休業相当01-01/12-25以外、B総量>0のときだけfeature適格。真0有効。将来label欠測で予測適格性を変えない。x=(1,(T7−B)/(14u),2*(latest7合計−previous7合計)/(14u))。T7は直前7日の曜日値を未来14日のopen仮定maskへ反復した合計。第2量は過去週差の14日相当で未来mask期待値ではない。uはfull2013観測平均（真0含む/欠測除外）、cutoff2014以後の変換。標準化/特徴選択追加なし。

各Q開始01-01/04-01/07-01/10-01のmaterialized prefixだけをfit関数へ渡す。全470入力/label reader/index/sourcepathをfit関数へ渡さない。prefixにはcutoff前に完結・仮定利用可能になった観測完全targetだけを含む。API上のデータ分離でありPython sandboxではない。過去確定した先行outerQのlabelを次cutoffの固定規則で学習に使うことは許可。同一originの予測保存前にそのtargetを使わない。

feature適格学習行のn_qsをQ×storeで数え、全4Q×10店が各1以上を必要とする。構造的支持不足なら全係数ベクトルβ=0/B、件数理由保存し再配分して救済しない。w_i=1/(4*10*n_qs)、総和1。r=(Y14−B)/(14u)、最小化は sum w_i(r_i−x_iβ)^2 + 1*(β0²+β1²+β2²)。λ=1は恣意性のある固定一仕様で最適値とは言わず、切片も罰則。3×3正規方程式をCholeskyで解く。非有限/解失敗はfailureとして保存し停止、Bで隠さない。

## 出力と過去同季節の内部制約

先にR=max(B+14u*xβ,0)を作りD=R−B、最後にP=B+alpha_q D。日次p_j=b_j*(P/B)、閉日0、B=0/feature未支持はB固定。各日の平均を別々に推定したとは言わない。β目的はfloor前の線形残差MSE、alpha制約はfloor後の固定Dに対する数量risk。floor順序を変えない。

各cutoffの過去同Qの全観測完全prefix（feature未支持はD=0）をalpha用集合とする。beta適格集合とは別で、w=1/(10*n_s)により店等重み/店内窓等重み。全10店の完全label支持が無ければそのQ alpha0。e=B−Y、A=sum w*(D/(14u))²、C=sum −w*e*D/(14u)²。同じ集合/重み/Dからunder/over凸適格上限とMSE上限max(0,2C/A)を求め、alpha=clip(C/A,0,min(1,Uunder,Uover,UMSE))。A<=1e-24ならalpha0。全Q共通最小上限なし。厳密有理数piecewise side_boundを既存immutable実装から使用。

betaと同じfit labelでalphaを決める内部最適化で、独立校正/検証ではない。当該outerQは対応alphaをQ中固定、後のlabelで救済更新なし。各cutoffの全Qalpha/全sampleを保存するが新候補gridではない。

## 一巡の比較・停止

候補はこの一方式＋同休業mean28のみ。全4cutoffモデルと全260予測を採点前に保存。学習に使う過去label利用と、同originの未到来target利用を混同しない。観測only/休業相当だけ欠測0仮定を別採点、rawnull/真0/unknown/休業仮定維持。2014全260、通常250、元日10を分け、Q別通常は元日を除いて別表示、Q別全窓も保存。重複合算なし。不支持20窓もBとして全分母に残す。

発行日の四季それぞれについて同一窓/同一label支持/10店macroで総量MSE、平均under、平均overの候補−B差を両label別に保存。MSEtol1e-12/数量tol1e-8。通常Qと元日別及びQ全窓の違反を隠さない。outer結果を見てQ予測をBへ差替えず、不適格のまま原予測/違反を保存。全年平均で相殺しない。Bの運用安全性も本診断では認定しない。

全B/支持不足/三条件違反/改善いずれでも一巡で終了。λ/特徴/期間/分割/cap/候補の追加なし、2015内容参照/予測/再評価へ接続せず、採用/置換なし。2014既読で独立性回復なし。先行支持監査の210/250/310/380や2014適格240は独立Nではない。

## 検証と保存

fixtureで正規方程式、和1重み、切片罰則、支持不足、floor前後、alpha適格区間、B比例/0、未来行拒否を検査。独立readerは別の線形解法/有理数二分探索risk境界、全prefix時点、全予測/両label scalar/paired判定/全source-state-roots失敗不変を照合する。保存後は仕様変更して同outerへ戻らない。

親900/子870秒、Mac sampled physical footprintとpeakRSS各2GiB、既存Files24通常files768MiB/単32MiB/全32files1GiB/失敗reserve8files256MiB、EvidenceStore16MiB512files/part256KiB/失敗2MiB16filesを保持。全stdio/exit/source/旧state/各新state/closure、負結果を新rootへ保存。2016/17・予約31–54・販促・正式holdout・Windowsnative・CARE・課金API・新取得・外部送信・push・採用なし。heartbeat PAUSED維持。
