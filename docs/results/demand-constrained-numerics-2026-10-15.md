# 制約付き学習の数値実装：人工21fixtureと最適性証明を確認

2026-10-15 JST。人の「進めてください」により、[数値契約](../research/demand-constrained-numerics-contract-2026-10-15.md)を先に保存し、人工問題だけで実装と証明を確認した。14本体＋2縮退＋5集計修正の21fixtureがpass。7人工問題と人工40店Qcell prefixの計8certificateを、別プロセスでsolver未importの独立verifierへ読み戻した。実データのfit/可行性solve/候補予測/2014再評価/2015内容参照・再評価はない。

Astraの静的レビューで予測helperと学習の総量集計の不一致が見つかった。旧コード・complete証拠を保持し、[v2補記](../research/demand-constrained-numerics-v2-amendment-2026-10-15.md)に従い[新入口](../../tools/demand_constrained_qp_v2.py)で統一した。[Astra双方のレビュー](../research/demand-constrained-numerics-astra-review-2026-10-15.md)も保存。QPの数学的なcoreと独立verifierは変更していない。

## 実装と証明の対象

stdlib Fractionによる3変数ridge QPで、目的は既存の正規化MSE＋λ1。全pastQのunder/over非増加と学習row非負を直接制約する。Q別MSE hard制約、後段alpha、総量固定、特徴/λ探索は加えない。未来入力へのfloorとB比例配分の設計は維持するが、今回の実装確認は総量helperまでで、実運用forecast pipelineの準備完了とはしない。

primal active-setで線形QPを解き、元hinge違反時は有効facetを加える。元の全hingeと非負、全保存cutを別moduleが再構築し、dual≥0、stationarity、相補性、primal-dual gap0を厳密に照合する。正定値ridgeに対してこの証明は最適性を支える。根拠は著者公開の[Convex Optimization・KKT十分条件](https://www.seas.ucla.edu/~vandenbe/cvxbook/bv_cvxbook.pdf)。独立verifierはsolverをimportせず、Fraction演算基盤は共通である。

| 人工問題 | 最適beta | cutting-plane round | 確認内容 |
|---|---|---:|---|
| intercept | 1, 0, 0 | 1 | 切片もλ1で罰する既知解 |
| changes_aggregate_total | 1/2, -3/2, 0 | 1 | 総量B=20から21への変更を許す |
| quarter_conflict | 0, 0, 0 | 2 | Q間衝突でゼロ最適を証明 |
| zero_optimum_nonzero_feasible | 0, 0, 0 | 1 | ゼロ最適でも別の非ゼロ可行点がある |
| exact_hinge | 0, 0, 0 | 2 | 誤差0の折点を保持 |
| two_cuts | 1, 0, 0 | 2 | 複数Qのcutを同時追加 |
| three_dimensional | 1/4, 5/6, 1/2 | 1 | 3特徴の非ゼロ解 |

5小問題は全hinge facet・active subsetを列挙し、別のCramer法でも同じbetaを得た。追加2fixtureは負λでのworking normal除去、zero normal・zero-step・同率3blockerを確認した。人工prefixは40店Qcellの重み、fallbackも含むrisk分母、入力を変更しない受渡し、future/部分label/偽造特徴の拒否を確認した。実際の店舗ラベルは読まず、旧fixtureの人工生成値だけを用いた。

## 集計の不一致と修正

v1の学習側はmath.fsumしたbinary64総量をFraction化したが、予測helperは各日を先にFraction化して足していた。これは端数を含むと異なる。v1の最適性証明は学習問題に対して有効で、予測側の集計一致まで保証していなかった。失敗を隠さず両rootを保持した。

| 人工日次baseline 0.1, 0.2, 0×12 | 厳密な有理数 |
|---|---|
| 旧helper | 10808639105689191/36028797018963968 |
| 学習側の規定総量 | 1351079888211149/4503599627370496 |
| v2 helper | 1351079888211149/4503599627370496 |

v2のquantity_totalをfrom_prefixのB/Yと予測helperのBで共有し、整数ケース、端数、一致、入力不変、不正数量/unit/補正経路の次元拒否を追加確認した。B0/x=Noneの早期fallbackは次元検査前であり、モデル状態の検証をhelperだけで代用しない。v2人工prefixのbeta=(1/10,0,0)も保存し、別プロセスでgap0を照合した。旧14+2は修正後に無目的に再実行せず、新しい5fixtureだけを実行した。

## 有限停止と限界

行512、64round、追加cut512、QP4096pivot/全65536pivot、bit長8192、certificate512KiBを固定した。人工probeでround/pivot/総pivot/bit/cut/行/certificate上限とcycleをfailureにし、最適β0や不可行へ置換しないことを確認。改ざんbeta/dual/cut/元問題/目的の証明拒否もpass。expected failuresは理由を保存しており、未解決の実データrun失敗ではない。

bit検査は一部累積演算後であり、任意入力の途中資源膨張をハードOS制限で防ぐものではない。KKT証明は最適性の証拠であり反復履歴や資源履歴の全正しさの証明ではない。verifierはround内訳とtotal_pivotsの全整合を検証しない。上限・cycle・特異系は数値手続きfailureで、原問題不可行性ではない。

人工fixtureでのpassは、実データで非ゼロ解が得られること、上限内で完走すること、予測が改善することを保証しない。旧2014既読の独立性は回復せず、実データfit-ready/PSI採用とは認定しない。Q別MSEは学習保証せず、将来のouterは三条件を全Q/両labelで報告し悪化の原予測を保持する。

## 資源とOS別結果

| 工程 | child秒 | sampled footprint bytes | peak RSS bytes |
|---|---:|---:|---:|
| 本体14fixture | 0.810003 | 18,743,752 | 37,011,456 |
| 独立7証明+縮退2fixture | 0.053090 | 15,712,712 | 32,833,536 |
| v2追加5fixture | 0.201837 | 17,744,328 | 36,110,336 |
| v2独立証明 | 0.013495 | 11,354,568 | 27,541,504 |

共通Mac/Python3.14.8で人工数値工程はpass。Windows固有/nativeおよびOS依存包括suiteは未実行、Mac resource計測のみ。追加の数値ライブラリ/solverを導入せず、既存環境lockは変更しない。

親900/子870秒・physical footprint/peak RSS各2GiB・従来EvidenceStore上限を維持し、全stdio/exit/source/fixture/certificate/資源/旧state pin/closureを保存。新しい実店舗モデルstate/artifactはなし。旧変更・失敗・closed rootsのhash/closure不変、同梱Git diff検査、Xcode設定/ライセンス変更なし。

調整対象2014以前、同休業仮定mean28、raw0/null/unknown、観測のみと休業相当の欠測0仮定の分離を維持。実データ欠測0学習0、2015新内容/再評価0。2016/17・予約31–54・販促・正式holdout・CARE・課金API・新データ・研究データ外部送信・commit/push・削除・本番採用なし。heartbeat PAUSED。

**本数値工程は完了。次は実データ適用の別事前契約でcutoff受渡し・数値証明・資源上限・終了条件を固定する工程。今回の人工結果から実データsolveや2014再評価へ自動接続しない。2015再評価停止を継続する。**

証拠：[本体](../../artifacts/macos-demand-constrained-numerics-20261015-records/root-closed.json)、[独立readback](../../artifacts/macos-demand-constrained-numerics-20261015-records-readback/root-closed.json)、[v2](../../artifacts/macos-demand-constrained-numerics-20261015-v2-records/root-closed.json)、[文書とv2独立readback](../../artifacts/macos-demand-constrained-numerics-20261015-doc-records/root-closed.json)。
