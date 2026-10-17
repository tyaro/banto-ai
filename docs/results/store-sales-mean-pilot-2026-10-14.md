# 独立mean出力の実装・一回評価（2026-10-14）

## 判断

平均用の出力と損失を固定設計に従って実装した。日次mean・14日総量mean・総量quantileを区別する経路は成立したが、今回の候補は単純基準への追加価値を確認できなかった。研究基準mean28総量＋限定暦配分を維持し、採択しない。

モデルを延長・別seedで再試行する根拠は得ていない。次は追加学習より先に、既存公開データの**過去の販促実施列が入力として利用でき、基準の残差に追加情報を持つか**をtrain期間だけで調べる。将来実施値を既知予定へ読み替えない。

## 新実装と4確認

`demand_model_mean.py` / `demand_train_mean.py` / `check_demand_mean.py`を新namespaceに追加。旧code/weights/完成評価は変更・反復していない。C56/P7/H14/V3/D64/L2、暦12/統計2、120805parameters。

独立mean head64→1を追加し、daily_mean=total_mean×配分。総量Q10/Q50/Q90は別head。decision_quantityはnull。meanをQ50や上下区間に強制しない。meanの目的は `.5*日次固定尺度MSE+.5*総量固定尺度MSE`、学習lossはこれに `.25*固定尺度総量pinball` を加えたもの。

新4確認は一回all passed（2.351秒）：meanとquantileの出力分離・日次合計整合、meanの大小をquantileへ拘束しないこと、非対称な少数例でのmean用目的とgradient、ゼロcontextでの有限な新head gradient。完全ゼロの予測を有限parameterで表せない正配分/floorの制約は残し、休業を学習済みにしていない。

## 一回学習

同snapshot、元train尺度・支持ledger、保存256×8 batch列、991/25/16origin、CPUfloat32/2threads/interop1/deterministic。独立init seed20261014、AdamWの予算不変。旧学習を反復せず、新候補256stepだけを実行した。

| step | validation Lmean |
| --- | ---: |
| 64（選択） | 0.0151407862 |
| 128 | 0.0156849833 |
| 192 | 0.0159009032 |
| 256 | 0.0154100118 |

選択後2017固定16originを一度forward。旧候補のMAE/pinballを主にしたvalidation lossとは目的が異なり、値を直接比較して改善とは言わない。2017は既知の回顧期間で、未見一般性能・メーカー精度を示さない。

## 平均用指標での比較

旧入力候補の総量Q50と整合日次配分、mean28、限定暦配分は保存予測を再利用し、RMSEを新しく集計した。旧modelのforward/fitは0。店舗・日付・実績の一致を確認し、集計は原保存数量の精度で行った。

| 方式 | 日次RMSE | 14日総量RMSE | 総量Bias % | 日次WAPE % |
| --- | ---: | ---: | ---: | ---: |
| mean28 | 100.650968 | 575.452895 | −0.839908 | 14.770136 |
| mean28総量＋暦配分 | 94.532393 | 575.452895 | −0.839908 | 14.424314 |
| 前候補Q50・配分 | 100.143014 | 588.212232 | −3.028263 | 14.614032 |
| 新mean head | 100.673815 | 583.664729 | −1.833382 | 14.732380 |

新meanは旧Q50より過小Biasが小さく、総量RMSEも少し小さいが、単純基準より総量RMSE/Biasとも悪い。日次RMSEは暦配分より約6.5%大きい。Q50とmeanは統計対象が異なる比較であり、meanという名前だけで期待数量が正しく推定できたとはしない。

| 店舗 | 総量RMSE mean / 基準 | 日次RMSE mean / 暦配分 |
| --- | ---: | ---: |
| 5 | 309.253544 / 308.314061 | 59.165579 / 54.557611 |
| 11 | 851.269365 / 836.529442 | 136.321424 / 125.056996 |
| 12 | 449.106071 / 445.644516 | 91.222556 / 90.517040 |

3店舗とも総量RMSEで基準に届かない。新mean/baseline総量倍率は0.984203–0.993778、平均0.989921。自分のQ50よりmeanが低い窓は42/48で、大小を強制しない設計通り。どちらも正しい条件付き分布の推定になったという証拠ではない。

保存出力の元日3窓の日次RMSEはmean186.760861 / 暦130.198637、残り45窓でも92.117263 / 91.662529。元日だけを除けば十分優れるという結果にもなっていない。

## validationの単純基準を事後記述

新選択値に対し、同じ2016年25起点×3店舗のmean28予測・実績を既存校正ledgerから再利用し、同じuと式でvalidation Lmeanを記述した。新forecast/fit/選択や基準の再計算は0。

基準Lmean=0.0150464114、新選択Lmean=0.0151407862。基準が約0.62%小さい。前者は保存値のPython float64算術、後者は原Torch float32の集計で、bitwise比較とはしない。差は丸めより十分大きいが、小標本の優位性検定ではない。

この比較は候補評価後に固定した事後診断。checkpoint64の元選択を遡及変更していない。今後は、ニューラルcheckpoint間の最小値だけでなく、同じvalidation目的の単純基準を出力前に比較対象へ含める方針とする。今回の未採択判断はtestを使った新係数の作成ではない。

## quantileは別欄

新candidateのQ10/Q90は41/48 covered（85.42%）、下限未満2/上限超過5、平均幅1715.318611、interval score2216.030535。基準の固定/直近score2092.694240/2080.379115より大きい。校正保証・安全在庫採択0。mean用の評価をquantileのcoverageで補わない。

## 次の研究unit

既存データのonpromotionは予定版ではなく実施側の列。**origin前の値だけ**を使う過去説明系列としての可能性を先に確認する。公開データにあるから将来既知とはしない。

次の順序は、列の意味・記録支持・日付/as-of仮定を固定→2013–15の小さい対象snapshotだけ保存→過去状態と基準残差の記述を確認。情報がなければ新モデルを増やさない。関係が見えても販促の因果効果とはしない。新学習は追加情報の根拠と別の出力前設計が成立してから行う。

## 保存・資源

新学習15.279266秒、OS peak private/pagefile1,032,085,504B。実CPython3.14.0/Torch2.14.0+cpu/Windows。閉鎖model18files/3,339,898B、日次合計と総量meanの最大float32差0.0009765625。

計算はHEAD8036659505eee6f6b7df22a1ec64588167798c78＋未commitの新source。clean commit計算ではない。source全文/SHA/設計/input/固定support/日付列/initial/4checkpoint/prefix/選択/meanとquantileの原予測・対応・journalを保存した。

- `artifacts/representative-store-sales-mean-checks-20261014-records`：4新確認/全stdio/exit0。
- `artifacts/representative-store-sales-mean-pilot-20261014` と同名 `...-records`：原model outputと全stdio/exit0。summary candidate-complete、closure complete。
- `artifacts/representative-store-sales-mean-analysis-20261014-records` と対応launch：保存出力と75validation基準行の新記述、forward0。
- 文書 `...-mean-doc-20261014-records`、Git後 `...-mean-git-20261014-records` post-saveを優先。

全新root/各prepは閉鎖し追記/再実行禁止。既存の失敗ラベル/encodingエラー・閉鎖rootは不変。今回新4確認・一候補、旧確認/評価/CI/native反復0。原データ/生予測/fit/重みはlocalのみ。

900秒2GiB/output1GiB/single32MiB/files32、記録16MiB512files/256KiBparts/reserve2MiB16files、prep128KiB16filesを維持。正式gate不変/formal_permission=false/credit0/登録holdout未読/native reader禁止。直接研究ACTIVE/automation PAUSED、追加agent0/CARE手動報告待ち。同GitHubへの独自codeと集約文書の継続承認を保持。
