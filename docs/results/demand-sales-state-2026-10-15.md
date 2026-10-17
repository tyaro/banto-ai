# 休業ゼロ・営業中の販売ゼロ・欠測の分離と固定2015評価

2026-10-15 JST。人の直接委任を[実行前契約](../research/demand-sales-state-design-2026-10-15.md)から実装・確認・既存10店2015評価まで完了した。新しい合成器は確定休業の販売0を通常のblend後に適用し、営業中の販売ゼロ、営業状態不明の販売ゼロ、欠測を別状態にする。営業予定が不明な日を祝日だけで0にしない。

固定250窓では営業予定がなく、観測販売ゼロもないため、新設計の追加性能改善は0。原主予測を維持してmean28比1.811781%改善/10of10、暫定2%未達・PSI採用false。実在の休業0・営業中の販売0の精度を確認済みとは呼ばない。

## 実装した分離

[demand_sales_states.py](../../tools/demand_sales_states.py)は営業予定のknown_at<=issue時点・同ID最新版・store scope・取消・競合を既存as-of入力で検査する。出典と公表時刻の真正性をこの処理単独では認定しない。未来版/時刻不明版のpayloadを使わず、最新unknownは旧closed/openを置き換える。

量の観測と営業状態は別fieldとして保持する。

| 営業状態 | 観測値 | 記録する状態 |
|---|---|---|
| closed | 0 | closed_zero |
| open | 0 | open_zero |
| unknown | 0 | unknown_zero |
| open | 正値 | open_positive |
| unknown | 正値 | unknown_positive |
| いずれも | 未観測/null | missing |
| closed | 正値 | 対象販売チャネルとの矛盾として拒否 |

予測は、発行時に確定closedかつ販売チャネルの休業時販売0契約ありなら、通常の数量getterや確率getterを使わず0を合成する。従来の正の基準約79.4%下限を休業日に残さない。契約がない場合は予測null、1日でも予測nullなら期間総量もnullとし、部分和を完全総量と呼ばない。原観測値や欠測labelは変更しない。

openの販売発生確率は営業確認済み観測だけ、unknownの確率は休業確認のないmixed観測から推定する。unknown_zeroをopen_zero又はclosed_zeroと認定しない。mixedの確率を営業日だけの確率や営業確率と呼ばない。missing/closedは確率分母から除き、14以上かつ正値・0の両classがある時のみp=positive/nを返す。支持のあるpと適合する正の条件付き数量平均を掛ける。片class等の支持不足ならp=null/理由を保存して、元の観測販売平均をfallbackとして保持する。p=1を学習済み確率と表示しない。

## 実データの支持と限界

評価用の営業予定は空入力。これは全店営業を意味せず、許可済みsnapshotに店舗別の発行時点の営業予定がないことを意味する。旧固定8月日±3日暦は数量モデルの説明変数のままで、営業判定には使わない。新評価は原主模型のrolling_calibrated/inner alpha0.2063357718495031を固定し、新NN/ridge学習・state forward・alpha選択を行わない。

| 支持 | 正値 | 観測0 | 欠測 | 営業状態 |
|---|---:|---:|---:|---|
| 原fit300の14日target | 4200 | 0 | 0 | 全unknown |
| 既存2014time120のtarget（事前調査） | 1680 | 0 | 0 | 営業予定なし |
| 固定2015評価の14日target | 3490 | 0 | 10 | 全unknown |

各店mixed occurrence学習支持420正値/0ゼロ、推定p=null/reason=no_observed_zero。open支持0/reason=insufficient_observations。3500予測日すべて営業unknown・確率未推定reference fallback、確定休業0日/確定営業0日/祝日による強制0日0。数量モデルの原学習targetは正値だけだが、営業ラベルと確率negative classがないため、実在の二部モデルを十分学習できたとは認定しない。

選択済みsnapshotには2013/2014年の各元日で10店それぞれの観測0、2015元日でも10店の観測0がある（事前調査）。その原因は営業予定なしでは休業と同定できない。今回の原fit窓/評価開始2015-01-13には入らない。ゼロの効果を見せるために発行日やfit窓を後付けで増やさない。Christmasは欠測なので0にしない。将来、元日を含む別固定評価を組む場合も、今回の250窓の結果と分け、営業予定なしで休業0の精度と呼ばない。

## 2015の結果

許可済み10店6/7/10/13/15/17/19/23/26/27、2015-01-13+14*k(k=0..24)、250要求を保持。予測はlabelなし保存後に原actualを付与し、各店349日/24完全総量、全3490日/240完全総量を維持した。10日の欠測labelはnullのまま、13日総量は作らない。

| 方式 | 日次scaled MSE | 総量scaled MSE | joint |
|---|---:|---:|---:|
| mean28 | 0.134053954571 | 0.020878675703 | 0.077466315137 |
| 新合成器＋固定主rolling | 0.132506798845 | 0.019618791454 | 0.076062795150 |
| 旧NN3328（比較） | 0.133491411548 | 0.020265515764 | 0.076878463656 |

新主のmean28比1.8117810108507548%改善/10of10、日次/総量MSE非悪化・支持不変=true、development_progress=false/minimum2%/business_adoption=false。前回主rollingからのjoint差0.0、250予測値すべて完全一致。暦やゼロ処理による新しい性能改善を主張しない。

| 副指標（10店等重みmacro） | mean28 | 新主 |
|---|---:|---:|
| 日次MAE | 48.845588649 | 48.428857454 |
| 総量MAE | 328.732636813 | 314.545816713 |
| 日次WAPE% | 17.067803322 | 16.960160066 |
| 総量WAPE% | 7.852857053 | 7.564897374 |
| 日次bias | 1.179059349 | -0.102876029 |
| 総量bias | 3.764422340 | -14.990657501 |

biasはprediction−actual。店舗・四半期・支持の全結果はsummaryに保存し、前unitと完全一致。全店joint改善は全副指標改善を意味しない（店舗13の日次MAEは小幅悪化）。既読開発の探索的評価で未知性能・有意性・潜在需要・PSI発注損失を主張しない。

## 確認と保存

新架空境界10testがpass。休業0/営業0/unknown0/欠測、closed正値矛盾、missing/closed除外の確率分母、両class不足p=null、fitのscope/date metadata先行、確定休業でgetter不要・blend下限回避、祝日unknown非ゼロ、future営業版payload未読、最新unknown、予測nullで全総量null/競合拒否を確認した。架空の正値とゼロは機構確認だけで、実在学習には使っていない。既存営業日処理の6testもpass。共通CPU機構16件をMacで確認し、Windows固有機能・OS依存包括suiteは新実行0/未検証として分離する。

artifacts/macos-demand-sales-state-20261015は12files/3,197,373B/complete。契約/source/config/fit4200label/occurrence-state/frozen合成/3500日営業・確率ledger/250label前後予測/3500label状態ledger/summary/closureを保存した。同execution-recordsに全child stdout/stderr/exit0、元5rootの前後照合。readback-recordsで4200学習支持・null確率・原選択・250予測完全一致・全3500分類・3490/240・scalar日次/総量MSE・source/原closure不変を独立照合、complete。

child1.577773秒/親2.183206秒、Mac sampled peak physical footprint151,520,000B/peakRSS219,889,664B。親900/子870秒・各2GiB・保存上限内、OSのhard capやWindows private bytesとの同等性は主張しない。NumPy未導入のTorch警告はstderrに保存、Torchは既存Files writerのimportだけで新模型計算なし。doc-recordsで文章値・links・全closure・PAUSED設定・Git差分空白を照合した。

既存変更・原失敗・closed rootsを保持、Mac未commit。2016–17/予約31–54/販促数量/正式holdout/Windows native/CARE/課金API/新取得/外部送信/push/削除/追加agentなし。formal_permission=false/本番採用0。

今回の直接委任は完了、heartbeat PAUSEDを保持。実在のゼロ対応を検証する次の必要情報は、店舗/対象販売チャネル/日付/open・closed・unknown/発行前に分かった時刻・出典・改訂を伴う営業予定と、営業確認済みの観測ゼロ・正値・欠測を含む過去実績。または元日を含む別評価を前もって設計する必要がある。いずれも既存の未知を休日から埋めず、今回の閉鎖成果を上書きしない。
