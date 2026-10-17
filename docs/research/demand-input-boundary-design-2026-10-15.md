# 入力・ラベル分離と時点整合の事前実装契約

2026-10-15 JST。人の依頼と前計画、[Astra実装前確認](demand-input-boundary-astra-review-2026-10-15.md)に基づく。今回は分離schema・可用性台帳・契約fixture・独立readbackのみ。新fit/候補予測/score/2015内容参照・再評価を起動しない。

## 固定するデータ境界

許可FIT10=(6,7,10,13,15,17,19,23,26,27)。混在sourceの2013/14 packet470を一回migrationで投影。2013の210は選別履歴を持つhistorical資料、2014の260はJan1+14*k/k0..25×FIT10の独立定義カレンダーと一致を必須とする。将来の発行対象をlabel存在・行数・完全性から作らない。

inputs.jsonは厳格allowlistでraw past56・観測mask・連続過去日付/仮定available_at・target14日付・既存同休業mean28・assumed_open_mask・unknown営業状態・固定policy参照・store/origin/schema/identityだけ。actual/raw_prediction/profile/encoded/complete/scale値等を入れない。inputcanonicalhashにlabel由来hashや混在source pinを含めない。入力loaderは混在source/labelパスを受け取らない。

transforms.jsonへfull2013尺度と尺度根拠期間/usable_from、2013だけを根拠とした休業仮定01-01/12-25と根拠期間/usable_fromを分離する。2013行の履歴特徴は当該origin以前、変換は2014cutoff学習として初めて使える。2013当時の擬似予測用途は拒否。原0/null/観測mask・営業unknownを維持する。

labels.jsonlはraw actual/observedとkey/store/origin/target/version/available_atだけ。label-index.jsonへbyte offset/length/rowpinと日付metadataを置く。fit readerはinputとindexのmetadataでcutoff可用性を判定してから、許可された過去rowのbyte区間だけをdecodeする。全payload hash照合は可能だが未来label数量をdecodeしない。manifestはinput/transform/label/indexの別pinsを結合し一対一keyを検査する。label改ざん/欠落/余分/範囲相違を拒否し、input経路はlabelファイル欠落・変更・並替えでも独立して読める。

## 日付と利用可能性の仮定

source日付の暦日単位。実配信時刻/timezoneは不明でありTokyo時刻へ変換したとは扱わない。past56はorigin−56..origin−1、target14はorigin..origin+13。日次観測は対象日翌日、14日label全体はorigin+14日の開始までに利用可能という即時日次確定の仮定（遅延・改訂は未検証）。full2013尺度/休業仮定は2014-01-01から利用可能と仮定。asof比較は日付境界inclusiveでavailable_at==cutoffを許可、target末日==cutoffは拒否。

input contract readinessとfit label completenessを別APIにする。予測時のreadinessはinputとtransformだけを使う。fitはQ開始2014-01-01/04-01/07-01/10-01以前に変換が利用可能で、target末日<cutoff、available_at<=cutoffのrowだけlabel decodeし、完全な観測labelを選ぶ。Q中係数固定は方策metadataを保存するだけで、新state/モデルは生成しない。

同mask Bは旧値copy一致に加え、原past最後28日の観測（真0含む）weekday平均>=3から作った既定B×maskと照合する。これは入力整合チェックで、新候補予測や成績比較ではない。scaleは原2013観測平均、maskは2013根拠pinと照合する。由来期間endとusable_fromを両方検査。

## 検証・維持する評価契約

JSONオブジェクト重複key、レコード重複、余剰/不足field、入れ子、NaN/Infinity/bool数量、日付・長さ・mask・identity・label対応・pin・範囲・未来/遅延availabilityを拒否。可用性index改ざんはmetadata同一性とpinned bindingで拒否。未来labelをdecodeしないspy fixture、ラベル値/欠測/順序/存在カナリアでinputs/hash/groups/readiness不変を確認。入力不適格理由はlabel情報を持たない。

独立readerでraw2013/14 snapshotからpast56/target14/2013尺度/休業仮定とコピーを照合し、Qcutoff選択210/270/330/400、2013擬似予測拒否と2014歴史学習許可、観測/欠測0シナリオ分離を確認。2014全260をinputgroupで固定し、原nullを仮定0へ昇格しない。

四季平均under/over非増加と総量MSE非悪化、同休業mean28、観測only/欠測0評価分離はpolicyとして維持。今回それらの成績は計算せず、達成を認定しない。outer違反を事後Bへ差替え禁止、2014既読なので独立性は回復しない。特徴/量変換/λ/校正方策未固定でモデルfit準備完了とも言わない。

fresh rootとexecution/readback/doc-recordsへ全stdio/exit/source/旧state/closure、失敗も保存。親900/子870秒・Mac sampled footprint/peakRSS各2GiB、通常Files24files768MiB/単32MiB/全32files1GiB/失敗reserve8files256MiB、EvidenceStore16MiB512files/part256KiB/reserve2MiB16filesを維持。旧変更/失敗/closed roots上書き削除なし。2015新内容参照・評価0、2016/17/予約31–54/販促/正式holdout/Windowsnative/CARE/課金API/新取得/外部送信/push/採用なし。heartbeat PAUSEDのまま本有限工程を閉じる。
