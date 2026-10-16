# 制約付き学習の数値実装契約：人工問題のみ

2026-10-15 JST。人の「進めてください」により、[第一設計](demand-constrained-training-design-2026-10-15.md)の次工程である数値backend・証明検証・人工fixtureを実装する。実データのfit/可行性solve/候補予測/2014再評価/2015内容decode・再評価は今回起動しない。2015停止とheartbeat PAUSEDを維持する。

## 固定する問題と数値表現

共通3係数・λ=1・全pastQのunder/over非増加・学習row非負、MSE目的、Q別MSE hard制約なし、後段alphaなしを維持。通常の目的J=Σw(r−xβ)^2+β²を、G=I+Σwxxᵀ、c=Σwxrとしてf=βᵀGβ/2−cᵀβへ定数/正の倍率だけ変えて解く。

backendは新規のstdlib `Fraction` 実装v1。依存追加・環境lock変更なし。人工入力は整数/有理数文字列、将来adapterが扱うbinary64はそのビット値の正確な有理数として符号化する。B/Yは既存math.fsumのbinary64総量を定数とし、unit=14u、r、h=unit*x、重み1/(40n)・1/(10n)以後は有理数で計算する。数学的重みは従来と同じで、旧floatの丸め誤差を再現する目的ではない。

βと双対証明は有理数文字列のまま保存・照合する。float丸め版を採用stateにしない。証明は符号化した問題に対するもので、元データ計測精度や予測性能の証明ではない。許容誤差や非劣性marginを設けず、厳密な符号/等式で判定する。

## 有限なsolver

3次元の非負制約線形QPから始める。全線形制約はaβ≤bで、β=0可行。primal active-setは0/空working setから始め、KKT方程式で方向pと乗数を解く。p=0で乗数が全非負なら最適、負の乗数があれば決定順で一つ除去。p≠0では最初のblockingまでstepし、その制約を加える。working setは独立なnormal最大3本。順序・tieは元制約index順、巡回はfailureとする。一般の有限収束を無条件には主張しない。

線形relaxationの解で各Qの元hinge和を厳密に再計算する。違反する側は、その解で正となるhingeの集合から有効なアフィンfacetを生成して加える。折点は寄与0として除外するが、全hingeの再計算では落とさない。各facetは全hinge和の下界で、元制約の必要条件。全元制約を満たすrelaxation最適解は元問題でも最適である。

固定上限：行512、cutting-plane 64round、追加cut512本、QP1回4096pivot・全体65536pivot、Fraction分子/分母bit長8192、certificate JSON 512KiB。各round/pivot/消去段でcheckpoint。親900秒/子870秒、Mac sampled footprintとpeak RSS各2GiB。cycle、特異KKT、上限、非有限入力、証明拒否はfailureで保存し、β0成功や解不存在へ読み替えない。実データでこの上限内に解けるかは今回未検証。

## 独立verifierとfixture

別moduleはsolverをimportせず、元rowsからG/c、全hinge、非負、証明に含まれるfacetの有効性を再構築する。元単位のrisk差≤0、dual≥0、Gβ−c+Aᵀdual=0、相補性を厳密に確認する。これは凸QPの十分条件で、primal/dual gap0を確認する。ゼロ返値だけの成功判定はない。独立実装も同じFraction演算基盤を使うため、数値ライブラリまで独立とは言わない。

人工fixtureは非ゼロ最適/ゼロ最適/非ゼロ可行でもゼロ最適、Q間衝突、hinge折点、非負境界、重複/従属normal、店等重みとfallback分母、未知入力floor/B0、未来/欠測/不正schema拒否を含める。小さい既知解と全facet・active subset列挙による別解も照合する。β/dual/cut/元rowの改ざん証明拒否、round/pivot/bit/cut/row/certificate上限とcycle検出のfailureも確認する。

全stdio/exit/source/fixture入力・結果/certificate/資源/旧state pin・closureをfresh EvidenceStoreへ保存。16MiB/512files/part256KiB/failure2MiB16filesを維持、新model artifactなし。旧変更・失敗・closed rootsは不変。Windows固有/native・OS依存包括suiteは行わず、Mac resource測定のみ。

この工程は人工問題での数値契約・実装・証明検証までで終了する。実データでの可解性/実行資源/性能は未検証。次に進む場合は実データ適用の別事前契約が必要で、人工結果から自動起動しない。2014以前の調整、同休業mean28、観測のみ/欠測0仮定分離、outer三条件と原予測保持、採用なしを継承する。
