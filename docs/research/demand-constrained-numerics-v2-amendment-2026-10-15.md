# 数値契約v2補記：総量の集計を統一

2026-10-15 JST。v1人工14fixture＋追加縮退2fixtureと7certificate readbackはpassしたが、Astraの静的レビューで予測helperが`ΣFraction(日次B)`、学習が`Fraction(math.fsum(日次B))`になっている不一致が見つかった。整数中心の旧fixtureでは検出できなかったため、v1の全コード・complete記録・証明を保持し、推奨入口を新規`demand_constrained_qp_v2.py`へ変更する。実データ適用はない。

新入口のquantity_totalは14日有限非負binary64/intをmath.fsumで一度総量化し、その保存binary64値をFractionへ変換する。from_prefixのB/Yと予測helperのBに同じ関数を使う。unit=14u以後のexact算術、QP core、独立verifier、λ/特徴/重み/制約/上限は変更しない。非正unit、不正な日次数量/次元を拒否する。旧moduleのpredict_totalは履歴として保持し、新入口からは利用しない。

修正確認は人工の端数[0.1,0.2,0×12]、入力/予測の一致、既知整数結果、負値/非有限/bool/長さ/unit/次元拒否、人工prefixの既知解とcertificate照合で行う。数値規則はfixture結果を見る前に本補記で固定する。実データfit/予測/2014評価/2015内容参照・再評価は0。

v1の最適性証明はその符号化された学習問題に対して有効で、予測helperの集計一致まで証明したものではなかった。KKT証明は反復ログ・時間/メモリの正しさの証明でもない。bit長検査は一部累積演算後で、実データ完走の保証はない。v2追加fixtureだけを実行し、変更のない旧14＋追加2fixtureを無目的に反復しない。終了は今回も人工数値工程までで、実データには別事前契約を要する。
