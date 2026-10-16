# 元日の観測ゼロを含む2015追加評価（実行前固定）

2026-10-15 JST、人の「元日の販売ゼロも含めた2015評価」「営業不明ゼロを休業と決めつけず旧250窓と別報告」に従う。仮説は、固定主方式が過去の選択窓に入らなかった元日の観測ゼロでどれだけ過大予測するか、営業状態unknownを保持したまま確認すること。改善するための後付け学習や休日の強制0はしない。

## 別の評価窓

許可済み10店6/7/10/13/15/17/19/23/26/27、origin2015-01-01、target2015-01-01〜01-14の10窓だけを追加評価する。原250窓/3490日/240完全総量/1.811781%改善の閉鎖結果は保持し、再計算・差替え・合算しない。新評価は元日を含む追加14日評価であり、年間評価を新たに260窓へ置換したものではない。原250窓とJan13–14×10=20店日が重なるので単純合算をしない。新10窓の総量は完全14日labelの場合だけ採点。

元日時点で入力可能な履歴は原selected-internal.csvの10店/2014以前のみ。入力はorigin−56..origin−1=2014-11-06〜12-31、欠測Christmasを観測0にしない。原u/暦42支持/72列/lambda0.01/365日poolを固定。origin−365<=packet originかつ全14label末日<originをmetadataで選択してからprofile/quantityを組み立てる。210窓・各店21窓、最古2014-02-25/最新2014-12-02/最大label2014-12-15、全店均等支持/最低140の規則を保持。元日発行用の共有ridgeを一回fitし、state/標準化/全pool keysを保存。旧Jan13又は2015で更新されたstateは使わない。

主は前の2014inner/outerで固定したrolling_calibrated、alpha0.2063357718495031を保持。新NN学習/forward/checkpoint/alpha/λ/方式選択なし。新occurrence fitなし、前unitのfit300に基づくunsupported occurrence-stateを再利用（mixed正値420/0ゼロ/open支持0、p=null）。raw rollingは診断副比較として先に固定し、結果で主へ昇格しない。

## 営業状態・label・指標

実在as-of営業予定はないので全140予測日unknown。祝日や実0からclosed/openを認定しない。元日の観測0はunknown_zero、正値unknown_positive、欠測missing。元日に0だから予測にも0を与えるoracleを作らない。新合成器はunsupported確率なら固定主数量予測を保持。p=1を推定済みと表示しない。確定休業の実測精度を主張しない。

2015 snapshotは10予測をlabelなし保存した後にだけ数値を解釈する。既存閉鎖snapshotからFIT/target日metadataを選んでからsalesを読取り、完全calendar/mask/有限非負値/duplicateを検査。今回のtarget外の2015値は数値化しない。JSONやhashの照合はquantityを使う学習ではない。

mean28を主対照、新合成器付き固定主・raw rollingを列挙。日次MSE/u²、完全14日総量MSE/(14u)²と半々jointを10店等重み、MAE/WAPE/bias、店舗別を報告する。zeroとpositiveの各日を別に日次scaled MSE/MAE/bias/平均予測/過大予測日数で診断し、ゼロだけのWAPEは分母0でnullとする。ゼロsubsetを部分総量として採点しない。旧250窓の参考表は既存summaryから引用のみで、支持の違うjoint値を直接の改善と呼ばない。

新fixtureはJan1時点に終了したpacket選択/未来・現在label poison/365境界/当日入力拒否/target日のmetadata先行と0・null区別/10窓grid/zero-only WAPE null/旧窓との20店日重複を検査。旧新合成器の10fixtureは直近passを再利用し無目的に反復しない。

fresh macos-demand-newyear-2015-20261015及びexecution/readback/doc-records。契約/source/config/固定selectionとoccurrence-state/210pool metadataとstate/profile/10label前後予測/140営業・確率・label分類/summary/全stdio/exit/失敗prefix/closure、原source/root前後不変を保存。親900/子870秒、Mac sampled footprint/peakRSS各2GiB、通常artifact24files768MiB/全32files1GiB/single32MiB/失敗8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16files。既存変更/失敗/closed rootsを保持。

2016–17/予約31–54/販促数量/正式holdout/Windows native/CARE/課金API/新取得/外部送信/Git push/削除/追加agentなし。共通CPU/Mac機構の結果とWindows固有/OS依存包括test未実行を分離。既読探索的評価/未知性能claim0/formal_permission=false/本番採用0。heartbeat PAUSEDを保持し、今回の直接委任を評価・照合・文書保存まで完了する。

事前fixtureで欠測総量時のNone比較エラーを検出し、元execution-records failedを保持。実データ評価/元日fit開始0。欠測総量のjoint/改善店舗数/改善率をnullとする集計修正を行い、同8fixtureをfresh macos-demand-newyear-2015-20261015-v2へ保存して進める。支持不足店舗を除いてaggregateを作らず、科学条件/窓/α/λは変更しない。
