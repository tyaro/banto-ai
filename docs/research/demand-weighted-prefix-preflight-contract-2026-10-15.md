# 実学習prefix→新consumer：metadata事前監査と将来の接続条件

2026-10-15 JST。人の「学習/2015再評価停止のまま接続条件固定・時点来歴チェック」に対応する。今回の実行範囲は**metadata事前監査だけ**。新実ラベル数量decode/新実r・旧x・z計算/数量payload生成/compile_problem/fit/solve/候補予測/性能採点/2015内容参照・再評価を行わない。[人工consumer](demand-weighted-consumer-artificial-contract-2026-10-15.md)と[人工日次bridge](demand-weighted-daily-bridge-contract-2026-10-15.md)の完了を実接続や学習許可へ拡張しない。

## 信頼根と数量をdecodeしない抽出

旧complete input-boundary-v2とordered-weight-input-auditのroot closureを、最新保護記録が保持するclosure hashへ結び付けて検証する。rootに書かれた現在値だけを信頼根にしない。各fileは旧closure記載のbytes/hashを、bounded single-read bytesに対して照合してから抽出する。

数量なしのbinding/cutoff-availability/label-index/audit-groups/freeze/input-pins/membership-metadataだけは通常のstrict JSONで読む。inputs.json/encoded-rows.json/transforms.jsonの全JSON decode後に数量を捨てる方法は使わない。ASCII JSONのpath指定lexerで、past_values/past_observed/baseline/scales値/旧x/r/z/encoderの数量subtreeを意味decode・数値変換せず読み飛ばす。許可するのはschema/key/store/date/available/mask/unknown/policy/old eligibility・reasons/transform期間・usable_from/encoder入力pin・固定規約だけ。数量skip subtreeのsyntaxは検査し、raw bytesのhash/span pinは保存してよい。8MiB/file・depth64・token1,000,000・scalar string32KiB・数字token2468字で停止する。新取得やCSV/旧fit/予測へ接続しない。

## 現在のmetadata接続

全470件のinput/index/保存encodedのkey集合・identity・1:1対応、past56暦と翌日available、固定target14/mask/unknown、2013変換期間・2014開始を照合する。保存historyのdate/availableとinputを照合し、旧encoder input pin/stateの来歴を保持する。r/z値の再計算や数量整合を確認したとはしない。

完全rawラベル所属Iはpinned cutoff-availabilityのaccepted keysからだけ継承する。decodedキーとacceptedキーの旧metadata一致、cutoff、全470件のaccepted/excluded分割、sourceの旧独立検証へのchainを確認する。indexの可用日・欠測の推定でIを作り直さない。

各2014Q開始cutoffについて、元accepted集合から**発行日Qが同Qの2013行**だけを選ぶ。2013-02-26から14日間隔の21日×FIT10=(6,7,10,13,15,17,19,23,26,27)、Q別30/60/70/50行・3/6/7/5日を完全一致させる。target末日<cutoff、label.available_at=origin+14≤cutoffを確認。2014 accepted行や他Qは渡さず、targetが次Qに入っても発行Qで選ぶ。

旧audit train membershipのkey/store/origin/old_E、E/I、各店w=1/(10nE)/v=1/(10nI)を一致させる。元Eは保存旧入力適格性の来歴から継承し、r>0だけに絞らない。r0店/窓の削除・再正規化や元日/店舗例外なし。全Q元E/Iが保持されないなら停止する。全21発行日削除版も固定列挙し、残存各店E/Iで再重みするmetadata計画だけを作る。旧固定w幾何診断と区別し、再fitしない。

新consumerへ渡すのはstrict full-schemaを保った**metadata検査専用payload**。数量/observed/feature/r/z/scaleにはアクセス時に失敗するopaque placeholderを入れ、ラベルはindex由来のheaderだけを渡す。batch_metaだけを実行し、compile_problem/row_numbers/encoder/fixed_features/Arithmetic.value/LabelReader._decode/外部I/O到達をcanaryで禁止する。これは実行可能な学習prefixではなく、quantity_payload_materialized=false、consumer_compile_executed=false。実際のsubsetは全4primary+21削除の25 metadata payload、元4primary計210行を重複なく確認する。

## 将来、数量を持つprefixを渡す場合のAND条件（今回は未実行）

1. 旧closure/file/row/index bytes pin、keyと各時点・同Q固定calendarが一致し、単一readしたraw labelがdecode前にrow pinへ一致する。
2. 保存Iの各raw labelがfinite非負・完全観測14日であり、observedとraw Noneが一致する。欠測は休業/営業とも学習に0補完しない。不一致ならdropせず停止する。
3. past56のraw0/None、元binary64 mean28、旧x/reasons、固定encoder v2のr/z/state pin、2013尺度、元E/Iと重みを新consumerの数量段階で一致確認する。新rやscaleをラベルで調整しない。
4. numeric payloadは必要な2013自Q行だけのfresh JSON。全入力・label reader/index/pathへの参照を渡さず、外部I/Oなしのconsumerへコピーする。段階間のsource/state pin・canonical payload pin・行ごとのbindingを保存する。旧stateと新問題行の一致/β0再現も確認する。
5. compileの可行性確認とsolverの起動を分ける。数量整合/実compileは別の依頼範囲、fit/solveは人の明示的な学習再開指示まで起動しない。4primary+21削除=最大25solveの将来枠を増やさない。2015再評価許可は別。

## 検証と保持

metadata parser/preflightに人工canary（quantity sentinel、許可外/未来/別Q/metadata改ざん/欠けた台帳/店舗欠け/重複/重み改変/抽出制限・syntax）を先に実行する。独立readerは新extractor/preflight/consumer/encoder/solverをimportせず、別lexerで元source bytesから許可metadataを抽出し、全選択と25 payload/元E-I/重み/来歴対応を照合する。保存projectionを追認するだけで終わらせない。metadataだけのpin一致は内容の真実性/署名認証/actual arrival/数量完全性を新たに証明しない。日次可用性は旧『翌日・label origin+14』仮定で、実timestamp/timezoneは未検証。2013尺度は2014cutoffでの遡及前処理で2013当時のprospective変換ではない。保存学習資料の選択履歴と既読2014の適応性は解消しない。

各準備/実metadata監査/独立/文書の親900/子870秒、Mac sampled footprint/peakRSS各2GiB、計算整数・約分前積/和/比較8192bit。artifact normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、EvidenceStore16MiB512files/part256KiB/failure2MiB16files、stdout1MiB/stderr128KiBを維持。全stdio/exit/source/metadata projection・binding/state/partial/failure/resource/closureをfresh rootへ保存する。失敗/closed roots/source/旧変更は上書き削除せず、handoff/index旧全文を保持する。

調整2014以前、同休業mean28、四季平均under/over非増加と既存MSE条件、観測のみ/休業相当欠測だけ0仮定の評価分離、raw0/None/unknown、固定01-01/12-25仮定を維持する。実性能ゲートは未評価。preflight完了でもfit_ready=false/can_launch_learning=false、heartbeat PAUSED、2015停止、PSI採用なし。Windowsnative/OS依存包括suite/2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更なし。

Astraの起動前指摘を受け、2014発行260件も固定26日×FIT10と完全一致させ、全12 issue groupのmembership・保存old_E/重み・I unknownを検査する。一貫して2014日付だけを変更した人工projectionも拒否する。raw state span pinは旧sort_keys/compact ASCII serializationのbytes来歴で、新r/z/数量整合の再実証とは呼ばない。独立抽出は別regex tokenizerを用い、人工quantity bombでも両lexerが数量scalarをjson.loadsへ渡さないことを確認する。
