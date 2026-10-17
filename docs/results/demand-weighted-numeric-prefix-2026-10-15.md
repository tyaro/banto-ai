# 実2013数量prefixのpin・完全性・問題生成とβ0確認

2026-10-15 JST。[事前契約](../research/demand-weighted-numeric-prefix-contract-2026-10-15.md)・[Astra確認](../research/demand-weighted-numeric-prefix-astra-review-2026-10-15.md)・[決定表](../research/demand-weighted-numeric-prefix-decisions-2026-10-15.json)。

**許可済み2013年の210件・2,940日分の実ラベルがpin照合と完全性検査を通過し、数量入りprefixによる25問題すべてでβ0のbaseline再現と可行性を確認した。独立54,191比較が一致した。学習・solve・2014採点・2015再評価は実行していない。**

quantity_payload_materialized=true / real2013_compile_verified=true。fit_ready=false / can_launch_learning=falseを維持する。固定β0は可行点の確認であり、学習済み係数・最適解・改善を意味しない。

## pin・完全性・時点境界

前回の[metadata監査](demand-weighted-prefix-preflight-2026-10-15.md)の閉鎖projectionと4primary・全21削除計画を継承した。境界sourceと保存encodedの旧closureを外部hashへ照合し、inputs/encoded/labels/transformsの4ファイルをbounded single-readしてfile pinを照合した。2014行も含むファイルのbytes hashは行ったが、全JSONをdecodeしてから2014数量を捨てる処理は行っていない。

全210行のmetadata・25計画、続いて全630 raw row span pin（input/encoded/label各210）を数量decode前に検査した。切り出すrowは2013年の固定21発行日×既存10店（6,7,10,13,15,17,19,23,26,27）だけ。実行側も独立側も、同じ許可済み210 uniqueラベルを各一巡decodeした。各工程のsource row JSON decodeは630回とtransform1回である。

key/store/origin/target14、identity SHA、発行Q/cutoff、past56の日付・翌日可用性、target末日<cutoff、label可用日=origin+14≤cutoff、変換の2013期間と2014開始を確認した。targetが次Qへ跨いでも発行Qを用いる。独立readerはstrict field set・配列長・bool型・weekday support≥3・全25計画の完全集合も照合した。

210 raw labelはすべて14日がfinite非負int/floatかつobserved=true、Noneなし。今回の選択内ではraw0も0件だった。欠けた行を落とす・ラベルを0補完する・休業maskでraw正値を消す処理はない。したがってこのprefix内では観測のみと休業相当欠測0仮定は一致するが、0/欠測の実データ挙動をこのprefixで検証したとはしない。人工例で別途検証し、将来の2014評価modeは分離したままとする。

日次可用性は旧「past翌日/label+14」の仮定であり、実際の到着timestamp/timezoneの検証ではない。尺度は2014cutoffで使う2013通年変換で、2013発行時のオンライン可用性を主張しない。旧保存資料の選択履歴や既読2014の適応性も解消していない。

## 数量入りconsumerと元分母

新[adapter](../../tools/demand_numeric_prefix_adapter.py)がinput・label・保存weighted・固定transformsのみのfresh strict JSONを作った。full source・buffers・path・index・readerはconsumerへ渡さない。旧input/past0/None・観測flags・同休業mean28・history・旧x/reasons、固定τ=1/20・p32nearest-evenのr/z/state pinを照合した。encoder全stateを独立再構築し、記録されたmax_bits値そのものを除く数値stateも一致した（max_bits≤8192は別検査）。仕様・尺度・係数の調整はない。

| 発行Q | 元I | 元E | r>0 | r=0 |
|---|---:|---:|---:|---:|
| Q1 | 30 | 30 | 10 | 20 |
| Q2 | 60 | 60 | 24 | 36 |
| Q3 | 70 | 70 | 30 | 40 |
| Q4 | 50 | 50 | 19 | 31 |

primaryは各店E/I=3/6/7/5、w=1/(10nE)・v=1/(10nI)、各和1を保持した。r0の127行を落とさず正wと目的定数に残した。None/B0を含む元risk所属の扱いも変更しない。全店の同じ発行日を除く21版は、残存n'E/n'Iに再重みする既定計画どおりで、旧固定wの幾何診断と異なる。4primary+21削除=25 compileであり、25 solveではない。

immutable [consumer](../../tools/demand_weighted_problem_consumer.py)から全25問題・計1,190行のG/rhs/C/h/e、非負normal/bound、元hinge・β0 supporting facets、日次copy・可行点証跡を保存した。λ=1・3係数・同休業mean28・四季平均のunder/over非増加条件は不変。β0代入でP=B、全row・各Q平均のpaired under/over差=0、slack≥0、J(0)=C・ridge=0を確認した。β0における2 supporting facetがhinge制約の完全表現だとは扱わない。

日次baselineはexact/displayともコピーした。canonical B=Fraction(math.fsum)と日次exact和に差があるprimary87行は、その残差を保持し、再配分や丸め直しをしていない。誤差をごまかすための総量再固定・係数変更ではない。

consumer内のsolver import・file IO・旧LabelReader到達は各0。指定関数のcanaryであり、OS全体のI/O隔離の証明ではない。旧consumerのconsumer_artificial_ready_only=trueは凍結source由来のlegacy readiness fieldとして保持し、外側のscope=authorized_real2013_compile_onlyで実行範囲を明記した。人工データとして数えたり、学習の許可へ読み替えたりしない。

## 検証・証跡・資源

人工41check・期待拒否26件を先に通した。全metadata/全file/全row pinの前置、未選択2014数量sentinelをdecodeしないこと、未来/別Q/2014要求・offset/index・ラベルNone/flags/負/bool/非有限/bit・旧x/r/z/state改変・r0削除・削除後誤分母・I/O/solver到達を確認した。完全性の不正例は人工decoder注入によるsemantic検査であり、raw bytesのpin一致を省略する実データ経路ではない。

独立readerはadapter/consumer/encoder/旧特徴量/solverをimportせず、元sourceの許可2013行をpin照合して読み直し、全25case・subset・目的・制約・重み・β0・日次baselineを再計算した。Astraのstrict型・配列・header・identity・support・計画の指摘をfresh v2へ反映し、旧reader sourceを保持した。独立比較54,191件、compiler/独立とも最大933bit（約分前の積/和/比較8192bit以内）。原版readerは未実行、v2を一巡実行した。

| Mac実行 | 秒 | sampled physical footprint | peak RSS |
|---|---:|---:|---:|
| 実prefix/25 compile | 10.369998 | 84,017,728B | 93,847,552B |
| 独立照合 | 1.732823 | 79,790,728B | 91,979,776B |

親900/子870秒・各メモリ2GiBの既定内。測定はsampled checkpointでOS hard capではない。model artifactは11file/9,781,493B、最大file2,789,425B。normal24file768MiB・total32file1GiB・single32MiB・failure8file256MiB、EvidenceStore16MiB/512file・part256KiB・failure2MiB/16file、stdout1MiB/stderr128KiBの上限を拡張していない。

全source・stdio/exit・selection/binding・decode前pin ledger・完了raw/state journal・数量payload・全問題/β0・partial/failure/resource/closureを保存した。人工の意図的失敗と模擬中断の2 failed rootsも保護した。模擬中断は親sealerを直接呼んだ試験で、実subprocess TimeoutExpired経路の試験ではない。実行・独立の予期しない失敗はなく、旧変更・失敗・closed roots・旧handoff/index全文を保持した。

Mac Python3.14.8の共通人工・実prefix・独立照合pass、Mac資源観測pass。Windows固有/nativeおよびOS依存包括test suiteは未実行として分ける。

## 停止条件と次の境界

今回完了は実2013数量prefixの接続と問題生成・β0検証まで。学習/solve、非ゼロ係数・新予測、2014数量decode/新採点、2015内容参照/再評価は0。四季all/normal・元日前後の平均under/overおよび総量MSE非増加・annual MSE厳密改善という実性能ゲートは、今回新たに評価していない。

調整2014年以前、同休業仮定のmean28、観測のみ/休業相当の欠測だけ0仮定の評価分離を維持。現在の完了から自動的に学習へ進まず、人の明示的再開と既存AND開始条件の確認が必要。実学習済みβの接続、全25solve、2014の性能ゲート・頑健性判定は残る工程である。

heartbeat PAUSED、fit_ready=false/can_launch_learning=false、PSI採用なし。2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

証跡：[準備](../../artifacts/macos-demand-numeric-prefix-20261015-preparation-records/root-closed.json)、[実行](../../artifacts/macos-demand-numeric-prefix-20261015-execution-records/root-closed.json)、[model](../../artifacts/macos-demand-numeric-prefix-20261015/root-closed.json)、[独立](../../artifacts/macos-demand-numeric-prefix-20261015-readback-v2-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-numeric-prefix-20261015-doc-records/root-closed.json)。
