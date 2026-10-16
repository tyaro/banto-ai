# 固定重みの発行前入力接続・集中とrankの監査

2026-10-15 JST。[事前契約](../research/demand-ordered-weight-input-audit-contract-2026-10-15.md)、[人工補強](../research/demand-ordered-weight-input-audit-preparation-amendment-2026-10-15.md)、[算術・失敗保存補強](../research/demand-ordered-weight-input-audit-runtime-amendment-2026-10-15.md)を先に保存し、Astraと設計/実装/結果を確認した。

**固定τ=1/20・絶対p32最近接偶数丸めを、許可10店の2013–2014発行前入力470行へ接続した。各季節の候補学習入力はrank3を保つ一方、少数店舗・発行日への集中が残る。学習、係数推定、候補予測、ラベル数量の新decode、性能採点、2015参照・再評価は行っていない。fit_ready=false。**

## 入力境界と母数

研究データとして意味decodeした既存ファイルはinput-boundary v2のinputs.json、transforms.json、cutoff-availability.jsonのみ。labels.jsonl/全履歴CSV/混合packet/旧state・予測の数量をdecodeせず、歴史的な完全I membershipは検証済みaccepted_keys台帳から引き継いだ。保護対象の整合性確認はbytes hash/closureだけで行った。

重み関数へ渡すfresh packetは各origin前56日のdate/available_at/valueだけ。store/key/baseline/scale/target/label/path/readerを渡さず、別の旧xへ保存rをexactに掛ける。真open0は保持し、特徴用欠測0補完なし、01-01/12-25休業相当とunknownを維持。旧同mask mean28/scale/理由を保存・照合した。

旧2013尺度は2014cutoffでの遡及学習用前処理であり、2013当時のprospective前処理とは呼ばない。新r用μ/曜日平均/Vは常に当該origin前56日だけ。next-calendar-dayは可用性の仮定で、実着荷時刻の証明ではない。

候補学習用は各cutoff以前完結・availableな自Qだけ、全て2013のI/E=30/60/70/50、発行日3/6/7/5。各店の元w=1/(10nE)、v=1/(10nI)とr0行を保持した。2014issueのIはラベル未参照でunknown、旧入力適格Eだけの記述用店等重みを用いた。両者の重みを学習・採点結果として混同しない。

## 自Qの候補学習入力（学習は未実施）

| Q | 元I/E | 保存r>0行 | r>0店舗 / 発行日 | old→new rank | 新energy最大の発行日 / share | 発行日質量相当数 old→new |
|---|---:|---:|---|---|---|---|
| Q1 | 30 / 30 | 10 | 8 / 3 | 3→3 | 2013-03-26 / 41.58% | 2.99993→2.89531 |
| Q2 | 60 / 60 | 24 | 10 / 6 | 3→3 | 2013-06-04 / 35.98% | 5.9988→3.84387 |
| Q3 | 70 / 70 | 30 | 10 / 7 | 3→3 | 2013-07-30 / 55.65% | 6.99863→2.61872 |
| Q4 | 50 / 50 | 19 | 9 / 5 | 3→3 | 2013-10-08 / 70.71% | 4.99963→1.83562 |

energyは元Eのw*r²*||x||²（切片を含む固定3座標）。shareはこの二乗量の構成比で、ラベル誤差、予測寄与、leverageではない。質量相当数は1/HHIという集中の記述で、独立発行日数/有効標本数/標準誤差に読み替えない。異なるQや年度も独立検証ではない。

Q3は2013-07-30が55.65%、Q4は2013-10-08が70.71%を占める。Q4の上位3発行日は96.20%。rank3でも5発行日の大部分の二乗量が1日に寄る状況は解消されていない。最大日を除外したり定数を変えたりせず、この診断を保存した。

| Q | 新energy最大店舗 / share | 上位3店舗 / share | 新Gram trace | 正規化Gram determinant |
|---|---|---|---:|---:|
| Q1 | 26 / 33.39% | 26, 10, 7 / 84.57% | 0.0033966 | 0.0782252 |
| Q2 | 27 / 31.28% | 27, 19, 17 / 71.98% | 0.00593666 | 0.0811914 |
| Q3 | 7 / 35.26% | 7, 15, 6 / 60.85% | 0.0124384 | 0.248046 |
| Q4 | 10 / 26.96% | 10, 7, 17 / 68.23% | 0.0237712 | 0.0520562 |

旧Gram traceは各Qで約1.02、重み後は上表の値まで小さくなる。λ1を維持しても正則化との相対関係は変わる。係数の大きさや予測幅がどうなるかは学習しておらず未検証である。正規化detはdet(G)/積diag、cos²は非中心化列間の値。condition number/Pearson相関/effective-rank閾値としては使わない。

## 店舗別：非ゼロ行数と罰則なしrank

各セルは「保存r>0行 / 元E行（new rank）」で、raw rと保存rの相違も機械可読表で別に保持する。

| 店 | Q1 | Q2 | Q3 | Q4 |
|---:|---|---|---|---|
| 6 | 1 / 3（1） | 2 / 6（2） | 2 / 7（2） | 1 / 5（1） |
| 7 | 1 / 3（1） | 3 / 6（3） | 4 / 7（3） | 2 / 5（2） |
| 10 | 1 / 3（1） | 1 / 6（1） | 2 / 7（2） | 2 / 5（2） |
| 13 | 1 / 3（1） | 4 / 6（3） | 4 / 7（3） | 3 / 5（3） |
| 15 | 0 / 3（0） | 1 / 6（1） | 3 / 7（3） | 1 / 5（1） |
| 17 | 0 / 3（0） | 1 / 6（1） | 4 / 7（3） | 2 / 5（2） |
| 19 | 2 / 3（2） | 4 / 6（3） | 3 / 7（3） | 0 / 5（0） |
| 23 | 1 / 3（1） | 1 / 6（1） | 2 / 7（2） | 4 / 5（3） |
| 26 | 2 / 3（2） | 4 / 6（3） | 4 / 7（3） | 2 / 5（2） |
| 27 | 1 / 3（1） | 3 / 6（3） | 2 / 7（2） | 2 / 5（2） |

Q1の店15/17、Q4の店19は全旧適格行のr0で、変換後の行はzero vectorになる。行はE/Iと分母に残る。10店共有のpool全体はrank3だが、各店が3方向を支えるという意味ではない。店番号/季節型の固定分類や除外ルールへ変換していない。

exact rankは罰則を足す前の旧/新3列で計算し、new rank=旧xをr>0行に限定したrankを全群で照合した。店別/発行日別rank、最大3pivot/witness、basis包含、direction2列rank、Gram/energy一致も保存した。ridgeで可逆になることを情報の十分性とは扱わない。

## 2014発行側：入力だけの分布

| Q | 全入力 / 旧E | 全行r>0 / 旧E内r>0 | 非ゼロ店 / 発行日 | old→new rank | 新energy最大日 / share | 新energy最大店 / share |
|---|---:|---:|---|---|---|---|
| Q1 | 70 / 50 | 23 / 14 | 6 / 5 | 3→3 | 2014-02-12 / 50.41% | 10 / 40.80% |
| Q2 | 60 / 60 | 23 / 23 | 10 / 6 | 3→3 | 2014-06-04 / 42.74% | 27 / 55.75% |
| Q3 | 70 / 70 | 33 / 33 | 10 / 7 | 3→3 | 2014-09-24 / 73.12% | 15 / 23.31% |
| Q4 | 60 / 60 | 22 / 22 | 9 / 6 | 3→3 | 2014-11-05 / 68.61% | 19 / 22.22% |

全260入力では旧E240、全行r>0が101、旧Eかつr>0が92（全10店・24発行日）。通常250では全行r>0が93、旧Eかつr>0は同じ92。元日10入力のうち履歴r>0は8だが旧E0で、全てfeatures=Noneを維持しrank0・feature energy0。zero-totalのshare/HHI/質量相当数はnull。rを0へ書換えて旧不支持と混同していない。

2014Q3は09-24が73.12%、Q4は11-05が68.61%の新energyを占め、Q2は店27が55.75%。これらは発行前の特徴分布で、当日の正誤・需要実績・予測改善を示さない。店13や特定日だけへの調整はしていない。

観測のみ/休業欠測0仮定の性能評価は両方とも未実行。今回のinput特徴は同じ1組で、ラベルmodeをrへ混ぜない。今後の評価でも観測rawは維持し、休業相当欠測だけ0仮定、営業相当欠測は保持する。元日/年末/四季all-normalを分ける既存条件を変えない。

## 確認・失敗・資源

実行前人工36checkと独立算術/比較/失敗閉鎖144checkをpass。実入力470行/16群、別readerは新encoder/audit/数値core/旧feature関数/solverをimportせず81,665比較・652 rank証跡を再構築して一致した。保存packetと元input、全r/特徴積/旧x/B/mask、accepted membership/各1n、全集中量/Gram/rank・basisを照合した。

最大整数はencoder 109bit、監査 454bit、独立reader 453bitで8192以内。実行child 6.734790秒、sampled footprint 51,773,944B、peak RSS 59,424,768B。reader 4.412287秒、58,655,272B/71,254,016B。各親900/子870秒・各2GiB、Mac sampled観測でOS hard capではない。

初版の近共線fixture期待値は、列が小さいだけで正規化volumeが小さくなると誤解して失敗した。fixtureだけをほぼ従属な列へ訂正した。runtime初版は一時pathの/var symlinkをresolveせず既存整合性readerに拒否された。両failed root/source/stdio/exit1を保持し、成功扱いへ変更しない。実データの接続/監査/readbackは一巡でcompleteだった。

Astraの起動前確認で、独立算術の比較を含むbit検査、質量sortのchecked比較、resource/timeout時のfailed閉鎖、prelaunch新root確認を補強した。完了行/群をappend-only journalへfsyncし、強制停止時もそのbytesを修復せず保持する仕組みと人工閉鎖fixtureを保存した。

旧source/state/260予測/失敗/closed roots/既存変更を保護し、artifact通常24files768MiB/全32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16filesを拡張していない。全stdio/exit/source/input-pin/state/partial/failure/resource/closureをfresh rootへ保存。

共通Mac/Python3.14.8で接続・人工・独立照合pass。Windows固有/nativeとOS依存包括suiteは未実行。Mac資源API測定だけを別確認し、Windowsと同等の検証とは扱わない。

## 結論と維持条件

**input_integration_audited=true、fit_ready=false。** 数値的な接続とrankの成立は確認できたが、少数日・店舗への集中は残る。rank3だけで十分な情報量・頑健性・将来改善・四季平均under/over非増加を認定しない。重みを見た後の閾値/τ/λ/期間/店舗除外/固定分類や救済fitはしない。

学習はまだ行わない。この監査で終了し、次に進むなら集中と薄い単一年支持を明記した別の学習/有限終了契約が必要。調整2014以前、自Q10店共有λ1、元E/I分母、同休業mean28、四季all-normal平均under/over非増加・MSE条件、観測のみ/休業欠測0仮定分離を維持する。旧Q1条件不適格判定は変えず、2015参照・再評価は停止、heartbeat PAUSED、PSI採用なし。

未commit/push/削除/新取得/外部研究データ送信/依存lock/Xcode変更。2016–17/予約31–54/販促/正式holdout/Windowsnative/CARE/課金API/本番採用を起動していない。

証跡：[入力接続・全state/監査](../../artifacts/macos-demand-ordered-weight-input-audit-20261015/root-closed.json)、[実行stdio/exit](../../artifacts/macos-demand-ordered-weight-input-audit-20261015-execution-records/root-closed.json)、[独立readback](../../artifacts/macos-demand-ordered-weight-input-audit-20261015-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-ordered-weight-input-audit-20261015-doc-records/root-closed.json)。[Astra確認](../research/demand-ordered-weight-input-audit-astra-review-2026-10-15.md)。
