# 実2013数量prefixのpin・完全性・compile-only/β0確認

2026-10-15 JST。人の今回の明示依頼により[metadata事前監査](demand-weighted-prefix-preflight-contract-2026-10-15.md)の次工程を実行する。**許可済み2013自Q primary210件の実input/保存encoded/実label/2013尺度だけ**数量decodeし、4primary+固定21削除=25個の数量prefixを新consumerで問題生成・β0再現する。学習/solve/非ゼロ係数学習・予測/2014性能採点/2015内容参照・再評価なし。immutable consumerの人工専用docstringは変更せず、本契約が今回の実2013 compile-only呼出を明示的に許可する。

## decode前の境界

旧metadata preflightの閉鎖projection・4primary/21削除planと、最新保護closure hashを信頼根とする。input-boundary-v2とordered-weight-input-auditの旧root closureを外部hashへ照合し、source file bytesをsingle bounded readして旧pinへ照合する。2014以前の470 metadataを再利用しても、**inputs.json/encoded-rows.json全decode→2014を捨てる方法は使わない**。

選択済み2013自Q210キーのinput/encoded raw spanを旧projectionから確定し、span境界・row pin・key/header/同Q/可用時点を確認してからそのrowだけstrict JSON decodeする。labels.jsonlは旧indexのoffset/lengthで同じ210 raw rowだけを切り出し、decode前に全file pin・raw row pinを一致させる。2014 input/encoded/label数量と2015はdecodeしない。全fileのbytes hashは許可する。transformは固定2013期間・2014開始の10店尺度だけ。

全210行のmetadataと全25planを数値decodeより先に検査する。入力とlabelのkey/store/origin/target14が一致し、target末日<2014Q cutoff、available=origin+14≤cutoff、past56の各日<origin・available翌日、尺度とmask usable_from=2014-01-01≤cutoff、固定FIT10/2013暦/発行Qを守る。元完全所属I/old_E/w-vの変更、行drop、r正だけの再正規化はしない。source/index/row/state pinや完全性が不一致ならその場で停止して失敗を保存する。

## 数量payloadの固定

raw labelはfinite非負int/float（bool不可）、Noneなし14日、observed全trueでrawと一致することを確認する。休業/営業とも欠測を0補完して学習へ入れない。raw0・休業raw正値を消さない。inputのpast0/None、観測flags、同休業mean28、保存history、旧x/reasons、固定encoder v2 τ1/20・p32nearest-evenのr/z/state pinを保存sourceと突合する。再構築は整合検査だけで数値仕様・係数・尺度を調整しない。

数量consumerには必要な自Q行だけのfresh strict JSON（input,label,weighted,transforms）を渡し、全source/buffers/path/reader/indexを含めない。全210 unique rowを一度だけmaterializeし、同じ凍結値から4primaryと21全店同日除外を構成する。削除版のw'=1/(10n'E),v'=1/(10n'I)は残存各店母数から再構築し、旧固定w幾何診断と区別する。

元E=旧x非NoneかつB>0、I=完全raw全行。r0適格は正w・目的定数に残り、None/B0はrisk分母へ残る。今回の旧選択で全店E/Iが揃わなければ救済せず停止。λ1・3係数・同休業mean28・under/over/非負制約は変更しない。

## 検証する到達点

immutable tools/demand_weighted_problem_consumer.pyのcompile_problemだけを呼び、solver/core importとfitを禁止する。compiler内で再構築した旧x/r/z/state pin、元E/I/w-vを保存値と照合する。25問題のG/rhs/C/h/e・非負normal/bound・元hinge/RHS/facet・全rowを保存し、固定β=[0,0,0]を代入してP=B、slack≥0、各row/季節平均paired under-over差0、J(0)=C/ridge0を確認する。β0は可行点であり最適解や学習済み係数ではない。

日次baselineはexact/displayともコピーし、canonical B=Fraction(math.fsum)と日次exact和の差を保持して比例補正しない。unit=14*Fraction(scale)を維持。raw completeの学習labelで観測のみと休業欠測0仮定が一致しても、後の2014評価modeは引き続き別に扱う。今回は新しい実性能scoreを作らず、四季条件を通過したとはしない。

人工canaryを先行し、row/file pin不一致、offset/index交換、全metadata前置、未来/別Q/2014要求、None/flags/負/bool/非有限/bit、旧x/r/z/state改変、r0削除・削除後分母誤り、I/O/solver到達、途中失敗・immutable closureを検証する。consumerへfull sourceが流れないAPI境界を確認するがOS全I/O隔離とはしない。

独立readerはadapter/consumer/encoder/旧feature/solverをimportせず、許可2013 selected raw rowを旧pinへ照合して独立decodeし、保存入力/label/stateとの一致、旧x/r/z、全25問題・目的・制約・β0・日次copyをchecked arithmeticで再構築する。保存問題の追認だけで終わらせない。全長/全case名/全subsetの欠落・重複も検査する。

## 資源・証跡・停止

各親900/子870秒、sampled Mac physical footprint/RSS各2GiB、整数・約分前積/和/比較8192bit。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持。大量の数量/問題stateはfresh bounded artifactへ保存し、stdioは進捗と要約のみ。全source/stdio/exit/selection・raw row decode ledger/payload pin/encoder・問題・β0 state/partial/failure/resource/closureを保存する。失敗/closed roots/source/旧変更を上書き削除しない。

調整2014以前、自Q共有λ1・元E/I、四季all/normal・元日両modeの平均under/overとMSE非増加・annualMSE厳密改善、同休業mean28、観測のみ/休業相当欠測だけ0仮定の分離を維持。新2014/2015採点なし。日次可用性は旧翌日/label+14仮定で実着荷timestamp/timezoneではない。保存選択履歴・既読2014適応性は解消しない。

compile-only完了でもfit_ready=false/can_launch_learning=false、heartbeat PAUSED、2015停止。solver・最適性・非ゼロ学習済み予測・実性能・PSI採用は認定しない。Windowsnative/OS依存包括suite/2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

Astra起動前確認による明記：immutable consumerの`consumer_artificial_ready_only=true`は旧sourceのreadiness fieldとして保持する。今回のdata scopeは外側に`authorized_real2013_compile_only`と記録し、人工実行や学習再開へ読み替えない。中断人工例はparent sealerを直接呼ぶ模擬検証で、実subprocessのTimeoutExpired経路を通した試験とは呼ばない。実運用の親はchild終了/timeout後に今回所有した未閉鎖rootだけをfailedでsealし、既closed rootを変更しない。
