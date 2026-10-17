# 支持監査：人工fixtureと表記の補強

2026-10-15 JST。実データのr計算前。初版準備は人工Gram fixtureの期待値で失敗した。第三列だけ小さい行列は列正規化後のvolumeが小さくなるとは限らず、normalized determinant<2^-100という期待が誤りだった。元source/stdio/exit1/failed rootを保持し、v2の人工行列を実際にほぼ従属な列（x3=x2+微小差）へ訂正する。Gram式を試験通過のため変更しない。

Astraの事前コード確認を反映し、stored-positiveの軸countはall_stored_positive_count、stored weight合計はall_stored_r_sumと表記する。raw r正/保存r正/旧Eかつ正/方向あり/支持不成立等の行・店・発行日集合をcategory_supportへ追加する。cos²/正規化detの[0,1]範囲とrank3↔positive Gram detをexact検査する。これらは表記/監査の補強で、τ/丸め/encoder/期間/特徴/目的/risk母数を変更しない。

正規化Gram volumeと非中心化cos²を共線性の記述と呼び、condition number/effective rank/独立標本数とは呼ばない。実r未計算の状態でこの補強を固定し、人工試験を通してから一巡する。2015停止・fit_ready=false・新学習/予測/採点なしを維持する。
