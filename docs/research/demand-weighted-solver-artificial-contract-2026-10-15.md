# 重み付き自Q問題solver：人工専用の設計・検証契約

2026-10-15 JST。人の依頼はsolver設計・人工検証であり、実データ学習と2015再評価の再開ではない。[数量prefix/β0検証](../results/demand-weighted-numeric-prefix-2026-10-15.md)の実problem・materialized・raw sourceは内容decodeせず、閉鎖hashの保護だけを行う。新規人工問題と人工consumer出力だけをsolveする。

## 数式・境界

固定3係数・自Q共有λ=1。新consumerと同じproblem.rowsのkey/quarter/B/Y/unit/x/fit_weight/risk_weightを受け、xは既に固定重みrを掛けた特徴量で再度rを掛けない。単一Q、元fit重み和1・risk重み和1、None/B0はfit0、r0適格行は正fit重みと目的定数を維持する。solverはstore/index/label reader/pathに接続せず、具体的な有理数行だけを受ける。人工と名付けたAPIは呼出範囲の約束で、データの人工性を数学的に証明する機構ではない。

G=I+Σwxxᵀ、c=Σwx(Y−B)/unit、C=Σw((Y−B)/unit)²、J=βᵀGβ−2cᵀβ+Cを再構築する。制約は各P=B+unit*xβ≥0、同じ自QのΣv max(−(P−Y),0)≤baseline under、Σv max(P−Y,0)≤baseline over。総量を固定せず、後段alpha・tolerance・救済fit・係数探索なし。四季の実評価ゲートはsolverの人工検査と分け、調整2014年以前、同休業mean28、観測のみ/休業相当欠測だけ0仮定の分離を維持する。

有限active-setで0可行点から線形QPを解き、全元hingeを再計算して違反側の正hinge集合からseparating facetを加える。β0の2 facetだけでは完全な制約集合と扱わない。G正定値はridgeと非負wから得る。KKT方向・dual・step・blocker・working setを保存し、tieは元constraint index、負dual除去もindex順。追加normalの独立性を検査し最大3本。cycle/特異KKT/従属/資源/数値限界はfailure、β0成功・解不存在へ読み替えない。一般問題での有限収束は無条件に主張しない。

## 数値と証明

新stdlib Fraction版を別ファイルに保存し旧solver/consumer/encoderを変更しない。入力はbounded canonical有理数文字列。全実装の加減乗除・比較・消去・objective/hinge/gapをchecked arithmeticで行う。GCDにより積を作る前に相殺可能な因子は除けるが、形成する整数積・和と比較cross-productはFractionの約分前に8192bitを検査する。bool/float/非有限/非canonical文字列/過大tokenを拒否する。binary64由来は人工consumerが保存した正確な有理数を使う。

固定上限はrows512、round64、cuts512、per-QP pivots4096・total65536、bits8192、certificate512KiB。上限は下げる試験だけ許可。全pivot/消去/roundでcheckpoint。各親900/子870秒、sampled Mac physical footprint・peak RSS各2GiB。既定artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを拡張しない。

独立verifierはsolverをimportせず、別checked算術で全rowsからobjective、元全hinge/非負、全cutの正当性、dual非負、相補性、2Gβ−2c+Aᵀdual=0、primal/dual gap=0を再構築する。内部active-setはJ/2の勾配を使うが、証明書では乗数を2倍しJの尺度へ統一する。G≽Iにより符号化した問題の一意な最適点の証明とする。数学的最適性は人工の符号化問題だけに限り、需要予測の改善・頑健性・実データ可解性・PSI採用を証明しない。全cutは有効下界で、実行時のsubset列挙はしない。

## 先に固定する人工fixture

既知の非ゼロridge解、総量変化、ゼロ最適でも非ゼロ可行、hinge折点/複数cut、3次元、非負境界、重複・反対・従属/zero normal・同時blocker・負dual除去、r0/None/B0/元分母を含む行。tiny問題は別の全facet/active subset列挙（Cramer）でも照合する。Q1–Q4の別問題、行順変化とdeterministic replay、binary64の有理数保持を確認する。

新consumerへ人工10店の固定2013暦4primary+21削除を渡し、25人工問題をsolve/独立検証する。旧実2013保存問題は再利用しない。日次接続は人工の既存bridge/consumer β0 replayを利用し、閉鎖mask・営業0・None/observed・元日/年末と評価2modeの違いを保持する。実2014/2015の性能を採点しない。

改ざんβ/dual/cut/subset/J/problem pin、混合Q・重複key・不正符号/重み/長さ/型、round/pivot/total/bit/cut/row/certificate limit、消去特異/巡回の拒否を記録する。失敗注入の一部は内部helperを直接呼ぶことを明記し、実timeout経路の試験と混同しない。

全source・入力pin・人工入力・結果certificate・全pivot/round state・stdio/exit・partial/failure/resource/closureをfresh rootへ保存。Astraに設計と保存結果をread-only確認してもらう。旧変更/failed/closed roots/handoff-index全文を保ち、heartbeat PAUSED、fit_ready=false/can_launch_learning=falseを維持する。

実ラベル/実problem内容decode・実学習solve・新実予測/2014採点/2015再評価・新データ取得・外部研究データ送信・push・依存lock変更・Windowsnative/OS依存包括suite・採用なし。この工程の完了から自動で実データsolveへ進まない。

Astraの実行前指摘を反映：B>0かつx非Noneの旧Eはr0を含めfit_weight>0を必須にし、総和1を保つr0質量移動も拒否する。独立verifierは宣言limits.bitsも演算へ適用する。ただし証明書のmax_bits値そのものはsolver実行経路の診断であり、別演算順序の独立readerで同値再現する主張はしない。独立reader自身のmax_bitsを別に記録する。J尺度の数学的KKT証明とruntime診断を区別する。
