# 自Qの重み付き制約solver：人工検証完了

2026-10-16 JST。[起動前契約](../research/demand-weighted-solver-artificial-contract-2026-10-15.md)・[Astra確認](../research/demand-weighted-solver-artificial-astra-review-2026-10-16.md)・[決定表](../research/demand-weighted-solver-artificial-decisions-2026-10-16.json)。

**人工41保存ケースを解き、全件で元の過小量・過大量制約/非負条件とJ尺度のKKT・primal/dual gap=0を独立確認した。うち25件は新consumerの人工10店prefixから生成した1,190問題行である。実データの学習、実problemの内容decode、2014採点、2015参照・再評価は実行していない。**

solver_artificial_ready=trueだけを更新する。fit_ready=false/can_launch_learning=false、heartbeat PAUSEDを維持する。人工最適性の証明から需要予測の改善・実データでの可解性・頑健性・PSI採用を認定しない。

## solverの設計

新[tools/demand_weighted_solver.py](../../tools/demand_weighted_solver.py)は具体的なproblem.rowsだけを受けるpure stdlib Fraction solver。旧consumer/encoder/solverを変更せず、新sourceとして保存した。入力のxは既にz=r×旧特徴量であり、solverでrを再乗算しない。自Q単独の3係数、λ=1、元E/Iとw/vを維持する。r0でも旧Eならfit weight>0、None/B0はfit0、riskは元の完全所属を残す。和1だけでなく、r0のweightを他行へ移す改変も拒否する。

G=I+Σwzzᵀ、q=Σwz(Y−B)/unit、C=Σw((Y−B)/unit)²からJ=βᵀGβ−2qᵀβ+Cを再構築する。全P=B+unit*zβ≥0と、自Qの平均under/overが同じbaselineを超えない制約を解く。総量を固定しない。λ=1とw≥0によりGは正定値なので、rank不足や全r0でも数学上の一意最適解を持つ。ただし有限実装が任意の入力で上限内にその解を返す保証はしない。

active-setはβ0から開始し、独立normal最大3本、KKT方向とdual、blocking stepを用いる。tie/負dual除去は元constraint index順。線形QPの解で元の全hingeを再計算し、違反側の正hinge集合からvalid separating facetを追加する。折点はsubsetに入れず、元hinge計算では残す。β0の2 supporting facetだけで完全制約と扱わない。

certificateは元problemのpin、β、有効cut集合、active descriptor/dual、round/pivot、J、上限を保存する。内部QPはJ/2を使うが、出力dualは2倍して**2Gβ−2q+Aᵀdual=0**へ統一する。独立verifierはsolverをimportせず、全元rowsからG/q/C、全nonnegative/両hinge、全cutの正当性・登録/重複、dual>0、相補性、stationarity、dual boundを再構築する。valid cut上の厳密KKTと元制約への可行性、gap0により、その人工の符号化問題の一意最適点を確認した。

## 人工問題・独立照合

保存41caseは14micro+25consumer+逆順2。追加のdeterministic replayとI/O canaryが2呼出あるため、成功solver API呼出は43回。直接linear kernel5件は別である。期待拒否35件も成功件数に含めない（solver API拒否31・内部helper直接拒否4）。新solverの実データ呼出は0。

人工consumer25件は固定2013暦の4primary+全21発行日削除で、保存した実2013問題を流用していない。独立readerはcase名と(Q,除外日)、全10店の固定暦・行数・key、B/Y/unit/x、元nE/nI・w/v、G/q/Cを人工batchから照合した。全case名・tiny5/kernel5/mode10の完全な集合も固定一致させ、zipによる行省略を防いだ。

**consumer25件はすべてβ0が最適だった。非ゼロ最適解は別のmicro/逆順13件で確認した。** consumerから非ゼロ解、さらに日次bridgeまで一貫検証済みとはしない。今回の固定人工41caseは最大round3・total pivots8・cuts3で終わったが、一般的な退化問題や実problemの成功保証ではない。

| 人工case | β（exact） | J |
|---|---|---:|
| interior_nonzero | 1, 0, 0 | 2 |
| total_changes | 1/2, -3/2, 0 | 5 |
| zero_optimum_nonzero_feasible | 0, 0, 0 | 5/2 |
| hinge_kink | 0, 0, 0 | 2 |
| three_dimensions | 1, 1, 1 | 12 |
| all_r0_positive_constant | 0, 0, 0 | 4 |
| r0_retained | 2/3, 0, 0 | 28/3 |
| nonnegative_boundary | -1/100, 0, 0 | 3920599/1000000 |

total_changesの最適点はbaseline合計20から21へ総量を変更する。ゼロ最適の例でもβ=(0,−1/4,0)が元両hinge/非負を満たし、J=87/32はβ0より劣ることを確認した。ゼロ返値を「非ゼロ可行点なし」と解釈しない。全r0でも目的定数を残した。

tiny5件は全hinge facet・active subsetを別のCramer列挙で解いてβ/Jを照合した。kernel5件は1/2/3面、zero/比例/反対normal・同時blocker、負dual除去を既知解および独立J-gapで照合した。全pivot journalに零長stepとactive除去が記録された。比例normalに対する別dualも同じstationarityを満たし、解βの一意性と乗数の非一意性を区別した。

入力/上限の期待拒否35件は、不正型・符号・重み・schema・混合Q・key重複・r0質量移動、各row/round/cut/pivot/total/bit/certificate上限、singular/cycle/比較・加算中間bitを含む。内部helper直接4件は、実solver経路でそのfailureが生じた試験とは区別する。独立側はβ・dual・subset・side・J・bound/normal字段・pin・尺度・active/cut欠落・round/total・宣言bit上限など16改ざんを拒否した。

元日/年末の10人工scenarioで、観測のみと休業相当欠測だけ0仮定のactual・support数を独立確認した。営業日のNoneはNone、営業0は観測、休業相当日の正値はそのまま、0補完は休業相当かつNoneだけ。ラベルを学習へ0補完していない。これはβ0 replayの評価mode検査で、solverで得た係数の日次bridge統合や実四季ゲートの検証ではない。

## 数値・失敗・資源と保存

全加減乗除・比較cross-product・KKT消去・rank・目的/hingeはchecked arithmetic。GCDで相殺した後に形成する整数積・和もFraction約分前に検査する。入力はcanonical有理数文字列とし、float/bool/NaN/非canonicalを拒否する。人工binary64由来の値は正確な有理数のまま扱った。solver最大939bit、独立計算最大320bitで8192以内。独立側にはcertificateの宣言bitsも適用した。ただしsolver実行経路の報告max_bits値そのものは独立同値再現の対象ではなく、数学的最適性証明とは別のruntime診断である。

固定上限：rows512、round64、cuts512、per-QP pivots4096/total65536、certificate512KiB。上限を緩めず、試験時は下げるだけ。cycle/特異KKT/従属blocker/反復・桁数・保存・資源上限はfailure/未判定であり、β0成功・近似成功・解不存在へ読み替えない。一般的なcycling回避や実問題での収束は未保証。

| Mac実行 | 秒 | sampled physical footprint | peak RSS |
|---|---:|---:|---:|
| 人工solver/consumer/test | 6.002784 | 38,355,496B | 50,364,416B |
| 独立証明/列挙 | 0.990496 | 91,570,752B | 103,792,640B |

各親900/子870秒・各2GiB内、sampled checkpointでOS hard capではない。artifact 15files/13,000,546B、最大6,390,283B。normal24file768MiB/total32file1GiB/single32MiB/failure8file256MiB、EvidenceStore16MiB/512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持した。

全source/人工inputとpin・compiled/solver result/certificate・全pivot/round journal・stdio/exit・partial/failure/resource/closureを保存した。期待拒否は同じcomplete artifactへinput/type/reason付きで保存、今回予期しないfailed rootはない。既存の実quantity/model/rootは内容decodeせずhashだけで不変を確認した。旧変更・失敗・closed roots/source・handoff/index全文を保持した。I/O canaryは1人工solveのbuiltins.open/Path.open到達0で、OS全sandboxの証明ではない。実timeout経路の新試験も行っていない。

Mac Python3.14.8の共通solver人工/consumer接続/独立証明pass、Mac資源観測pass。Windows固有/nativeとOS依存包括test suiteは未実行として分離する。

## 実データへ進む条件

調整2014年以前、自Q共有λ1、同休業mean28、四季all/normal・元日両modeの平均過小量/過大量・総量MSE非増加、annual MSE厳密改善の既存ゲートを維持する。観測のみ/休業相当欠測だけ0仮定の評価も分離する。今回この実性能ゲートは未評価。

実solver適用前の問題/consumer pin接続、実係数の予測bridge・結果凍結・証明失敗時の停止などを既存AND条件に沿って確認する必要がある。実学習は人が新たに明示再開するまで起動しない。実2013 problem decode/solve、2014実数量/新採点、2015内容参照・再評価はいずれも0。fit_ready=false/can_launch_learning=false、heartbeat PAUSED、PSI採用なし。

2016–17/予約31–54/販促/正式holdout/CARE/課金API/新データ取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

証跡：[人工実行](../../artifacts/macos-demand-weighted-solver-artificial-20261016-execution-records/root-closed.json)、[全state/model](../../artifacts/macos-demand-weighted-solver-artificial-20261016/root-closed.json)、[独立検証](../../artifacts/macos-demand-weighted-solver-artificial-20261016-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-weighted-solver-artificial-20261016-doc-records/root-closed.json)。
