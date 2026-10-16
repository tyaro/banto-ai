# 実学習prefixの接続条件固定・時点来歴metadata監査

2026-10-15 JST。[事前契約と将来の接続AND条件](../research/demand-weighted-prefix-preflight-contract-2026-10-15.md)、[Astra確認](../research/demand-weighted-prefix-preflight-astra-review-2026-10-15.md)。

**470件のmetadataと旧保存所属を照合し、2013自Qの4primary計210行と全21削除版の25metadata payloadが新consumerのbatch_metaを通った。独立15,698比較が一致した。完了したのは時点・来歴のmetadata事前監査で、数量を持つ実学習prefixの接続ではない。**

quantity_payload_materialized=false、consumer_compile_executed=false、fit_ready=false / can_launch_learning=false。学習・2015参照/再評価は停止したまま。

## 固定した接続条件と今回の範囲

将来の数量payload接続は、旧closure・file・row・index pin、同Qの固定暦、入力/labelの可用性、完全raw14日、元mean28/旧x/r/z/state pin、元E/I・重みをANDで確認してから、必要な2013自Q行だけのfresh JSONを渡す。休業/営業とも欠測を学習へ0補完しない。数量の問題生成とfit/solveの起動を分け、人の明示的学習再開指示なしにsolverを起動しない。将来最大4primary+21削除=25solveの枠も維持する。

今回実行したのはその前段で、input-boundary v2とordered-weight-input-auditの既存sourceを、外部に保存された旧closure hashへ結び付け、single-readしたbytesを旧file pinに照合してからmetadataだけを抽出した。新取得・元CSV・旧fit/予測に接続していない。

数量入りinputs/encoded-rows/transformsは全JSON decodeしてから数量を捨てず、新[ASCII path lexer](../../tools/demand_prefix_metadata_json.py)で数量subtreeを意味decode/数値変換せず読み飛ばした。past値・観測flags・mean28値・scale値・旧x/r/z・encoderの数量字段はmetadata内でNoneに置換した。raw bytesのhash/spanは来歴として保存したが、数量整合を新たに確認したとはしない。

新[metadata preflight](../../tools/demand_weighted_prefix_preflight.py)からconsumerへ渡す数値部分は、アクセス時に失敗するopaque placeholder。ラベルはindexのkey/store/origin/target/available headerだけを渡し、batch_metaのみ呼んだ。これは実行可能な学習prefixではない。

## 暦・可用性・所属

全470件でinput/index/保存encodedのkey集合・identityと1:1対応、past56日付と翌日available、target14、01-01/12-25休業相当mask・unknown、変換2013期間と2014開始、保存history/encoderの時点metadataを照合した。2013は21発行日×10店の210件、2014も独立した固定26発行日×10店の260件に完全一致した。保存全16group（4train＋12issue）のmembership・保存old_E/重みも一致し、発行対象をlabelの有無や完全性から作り直していない。

完全ラベル所属Iは旧cutoff-availabilityのaccepted keysから継承した。旧accepted/decoded metadataと全470のaccepted/excluded分割、weighted auditの元input pins/同membership/freeze pinsを突合した。indexが利用可能な日付を持つことだけからcompleteと推定していない。**raw label完全性を今回読み直した証明ではない。**

| 発行Q | 2013自Qの元I/E行 | 発行日数 | 各店nE / nI | 利用cutoff |
|---|---:|---:|---:|---|
| Q1 | 30 | 3 | 3 / 3 | 2014-01-01 |
| Q2 | 60 | 6 | 6 / 6 | 2014-04-01 |
| Q3 | 70 | 7 | 7 / 7 | 2014-07-01 |
| Q4 | 50 | 5 | 5 / 5 | 2014-10-01 |

各primaryの10店は同じnE/nIを持つ。w=1/(10nE)、v=1/(10nI)、和各1を保持し、保存旧Eをr>0で絞らなかった。r0をdrop・再正規化しない。targetが次Qをまたいでも発行Qで選び、target末日<cutoff・label可用日=origin+14≤cutoffを確認した。2014のaccepted行や他Qは新consumerへ渡していない。

全21発行日削除版は、その日の10店を同時に外し、残存E/Iへ再重みするmetadata計画だけを作った。これは旧元w固定の幾何診断とも、削除再fitとも区別する。全25payloadに数量は含まず、25solveを実行したという意味ではない。

## 人工・独立照合

人工14check・期待拒否37件を先に通した。数量bombを含む人工sourceは両lexerで数量scalarをjson.loadsへ渡さず、許可metadataとspan pinが一致した。metadata不正、未来/別Q/欠け・重複、I台帳、旧E/重み、元pins、syntax/depth/byte/string/number token上限を拒否した。2014日付を全source/index/group/bindingで一貫変更する人工例も、固定発行暦と異なるため拒否した。

実metadata子プロセスはconsumer内のcompile_problem/row_numbers/encode_features/fixed_features、Arithmetic.value、LabelReader._decode、Path.open、builtins.openをcanaryで禁止し、各到達0、batch_meta呼出25回を記録した。ラベルquantityのdecode、r/旧x/z再計算、問題生成、fit/solve、候補予測・採点は0。I/O canaryは指定された経路の検査で、OS全体を隔離した証拠ではない。

別readerは新extractor/preflight/consumer/encoder/solverをimportせず、**元source bytesから別regex lexerで再抽出**して保存projectionと比較した。閉鎖pin→file bytes→metadata、全470対応/16group、4primary/21削除計画、元E/I・重み、全停止flagの15,698比較が一致した。保存projectionだけを追認したものではない。state raw span pinは旧sort_keys/compact ASCII serializationのbytes来歴で、r/z値の再検証やencoder全stateの数量再構築ではない。

## 限定と残る工程

日次可用性は旧『pastの翌日・labelのorigin+14』という明示仮定であり、実際の到着timestamp/timezoneは未検証。2013尺度は2014cutoffでの遡及前処理で、2013発行時に使えた変換とはしない。旧保存学習資料の選択履歴や既読2014の適応性も解消していない。

実raw labelのrow-pin照合とdecode、完全raw14日の再検証、数量を持つfresh prefix、実数値consumerの問題生成・β0再現は未実施。これらの実施には別の明示依頼範囲が必要で、今回の完了から自動的に接続しない。fit/solve・実学習済み係数の予測・2014性能検証、2015再評価も未実施・未解禁。

調整2014以前、自Q共有λ1、元E/I、同休業mean28、四季all/normal・元日両modeの平均under/over・総量MSE非増加とannualMSE厳密改善という既存条件を維持。観測のみ/休業相当欠測だけ0仮定の評価分離、raw0/None/unknownの区別も維持する。実性能ゲートは今回未評価で、metadata整合から性能・独立性・PSI採用を認定しない。

## 資源・保存・OS区分

実metadata child 0.231185秒、sampled footprint 55,689,744B / peak RSS 68,075,520B。独立reader 1.291022秒、179,389,040B / 204,701,696B。各親900/子870秒・各2GiB内。独立metadata重み算術の最大8bit（8192内）。productionの重みは10店/470以下のcountsだけを使う小整数計算で、需要数量計算ではない。lexerは8MiB/file・depth64・token1,000,000・string32KiB・数字token2468字を維持した。

stdout460,069Bは1MiB内。既存artifact/EvidenceStoreの上限を拡張せず、全stdio/exit/source/metadata projection/binding/plan/state/partial/failure/resource/closureを保存した。今回の準備/metadata/独立は各1巡でcomplete、新規failed rootなし。過去の失敗/source/closed roots/変更はそのまま保持し、handoff/index旧全文を保持した。

Mac Python3.14.8の共通metadata処理・人工・独立照合pass、Mac固有footprint/RSS観測pass。Windows固有/native・OS依存包括suiteは未実行。資源はsampled checkpointで、OS hard capではない。

heartbeat PAUSED。2015内容参照・再評価、新実数量decode、新r/学習/問題生成/予測/scoreなし。2016–17/予約31–54/販促/正式holdout/CARE/課金API/新取得/外部研究データ送信/commit-push/依存lock/Xcode変更/本番採用なし。

証跡：[準備・source抽出](../../artifacts/macos-demand-weighted-prefix-preflight-20261015-preparation-records/root-closed.json)、[metadata事前監査](../../artifacts/macos-demand-weighted-prefix-preflight-20261015-execution-records/root-closed.json)、[独立元bytes照合](../../artifacts/macos-demand-weighted-prefix-preflight-20261015-readback-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-weighted-prefix-preflight-20261015-doc-records/root-closed.json)。
