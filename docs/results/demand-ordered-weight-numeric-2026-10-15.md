# 順序付き重みの数値仕様固定・人工統合確認

2026-10-15 JST。2015の参照・再評価を停止したまま、[事前数値契約](../research/demand-ordered-weight-numeric-contract-2026-10-15.md)と[Astra確認](../research/demand-ordered-weight-numeric-astra-review-2026-10-15.md)に基づき、共通重みの定数・演算順・保存形式を固定した。実データのr、係数、予測、新2014評価は計算していない。

τ=1/20（0.05）、z/rの絶対格子2^-32・最近接偶数丸めを全店・全季節共通に固定した。τは発行前56日の営業相当観測平均μを単位とする変化尺度で、前block比5%成長/閾値/最適値/確率ではない。店13・特定日・実r分布への合わせ込みや定数grid探索は行わない。

```text
a=d3, b=(d1+d2)/2
r_raw = s * 2max(a*b,0)/(a²+b²+V+1/400)
r_stored = nearest_even_grid(r_raw, 2^-32)
new_x = exact_fraction(old_x)*r_stored  # 切片を含む
```

実装は[encoder v2](../../tools/demand_ordered_weight_v2.py)。旧初版も保存した。μ/曜日平均はexact Fraction、各zで一度丸め、L/d/a/b/V/r_rawはchecked exact Fraction、最後rで一度丸める。特徴積は丸めずexact分数文字列で保存する。8192bit超過は停止しr0に救済しない。最大finite/subnormal混在も人工確認し、成功caseの最大整数は2136bitだった。

raw域のzとa/bの上界からrの最後の丸め後も0≤r≤s≤1と示し、実装でも検査する。z誤差≤2^-33とr_rawから保存rへの誤差≤2^-33は別。生rawの無丸め式と保存rの差全体を2^-33と主張しない。raw encoder全体の連続性、将来方向、予測性能を証明したものでもない。

## 人工確認の結果

人工37packet、107assert、期待どおりの拒否30件を通過した。別readerは新encoder/数値core/solverをimportせず、Fractionと独自丸めで入力pin・主要数値state・fallback・特徴積・ラベル損失等5159比較が一致した。J=1..14、正負tie、横ばい/持続/反転/単発、曜日のみ、true0/null、μ0/J空、weekday平均0、-0/subnormal/maxfinite、入力妥当性と途中bit上限、時点違反を含む。

origin前56日だけをstrict入口へ渡し、日付gridとnext-day availabilityを検査する。2015originは値/iteratorに触る前に拒否し、raw未来混入・未可用はエラー。wide adapterはdate metadataで選択してから必要3字段だけをコピーし、未来value/余計labelのフィールド参照をcanaryで検出した。2015日付のcanaryは人工metadataで、実2015ファイルの内容ではない。関数入口の確認でありOS sandboxや実prefix統合の検証ではない。

01-01/12-25休業相当、営業予定unknownを維持。営業相当の実測0は平均/Jに含め、欠測は特徴用に0補完しない。休業相当日のraw0/正値/Noneは別に記録して特徴から外し、他の祝日を一律休業にしない。

既存project_input/project_label/label_scenariosとbounded atomsへ、日付/固定mask/過去56日一定10の人工4例を渡した。旧曜日mean28=10と休業予測0をvalidate_inputで確認し、観測のみはrawのまま、欠測0仮定は**休業相当日のNoneだけ**0補完・営業相当Noneは保持する。closure正値も消さず、quantityは休業相当日を除外し、complete14日総量は全日可用の場合だけ採点する。各modeの損失と母数を分けて保存・独立照合した。実データ評価の代替ではない。

人工4行を実encode_featuresに通し、元E3行/I4行と各1/3・1/4を維持した。r0の適格2行はzero vectorでEに残る。旧不支持行は履歴r>0でもfeatures=None・E外/I内で、全raw非ゼロr2行と旧適格非ゼロr1行を区別した。この小adapter試験は本物の学習prefixやQPまで統合した証拠ではない。

## 検証不足と失敗の保存

初版rootは23packet/3130比較でcompleteだが、手計算ラベルが既存規則を試験していなかったため、統合確認完了とは扱わない。[補強契約](../research/demand-ordered-weight-numeric-test-amendment-2026-10-15.md)を保存してv2へ進めた。

v2は全r正と旧適格r正を混同したchecker期待値でexit1、v3は人工exact欄の10.0文字列でexit1。それぞれ[期待値の訂正](../research/demand-ordered-weight-numeric-v2-failure-2026-10-15.md)、[fixtureの訂正](../research/demand-ordered-weight-numeric-v3-failure-2026-10-15.md)とsource/stdio/exit/resources/failed closureを保存した。v4はこの2点だけを直して完了した。式・τ・丸め・実装v2は変えず、失敗source/rootの上書き/削除はない。文書保存script初版も非ASCII bytes literalの構文で実行前に停止したためsource/exit1/failed closureを保存し、文書script v2でencodeへ訂正した。

## 維持する評価条件と次工程

weight_encoder_artificial_ready=true、**fit_ready=false**。実データでの改善は未検証で、旧Q1条件不適格の判断も変更しない。調整2014以前、自Q10店共有係数/λ1、元E/I分母、学習平均under/over≤同休業mean28、外側の四季all/normal平均under/over非増加とMSE条件、元日/年末、観測のみ/休業欠測0仮定分離を維持する。固定分類/店番号/特定日ルールや事後差替えを加えない。

次は別契約で、新past56 payloadの実prefix接続と時点canary、非ゼロrの店/発行日数・feature energy集中・rank・fallback理由の支持監査を行う工程。今回はそこへ自動接続しない。薄い支持からτ/λ/閾値を再探索しない。以後のfit/2014評価も別の有限起動契約と全予測先保存が必要。2015再評価・正式holdout・PSI採用は認定/再開しない。

## 共通MacとOS別結果・資源

共通処理の人工確認はMac/Python3.14.8でpass。Windows固有/nativeとOS依存包括suiteは未実行。Mac libproc footprint/RSSの測定だけを別に実施した。Windowsと同等の資源制限試験とは扱わない。

人工child 0.124333秒、sampled footprint 17,662,456B、peak RSS 29,802,496B。reader 0.022157秒、14,172,664B/26,247,168B。親900秒/子870秒・各2GiB内、sampled checkpointでありOS hard capではない。既存artifact/EvidenceStore上限を拡張せず、モデルartifact生成0。全stdio/exit/source/固定契約/人工input/state/result/resource/closureを保存した。

既存source/state/260予測/失敗/closed rootsをhashとclosureで保護した。2015の旧artifactを含む保護対象はbytes整合性だけで、値のdecode/fit/predict/scoreなし。heartbeat PAUSED、未commit/push/新取得/依存lock/Xcode変更/外部研究データ送信、2016–17/予約31–54/販促/Windowsnative/CARE/課金API/本番採用なし。

証跡：[事前固定](../../artifacts/macos-demand-ordered-weight-numeric-20261015-preparation-records/root-closed.json)、[初版](../../artifacts/macos-demand-ordered-weight-numeric-20261015-records/root-closed.json)、[v2失敗](../../artifacts/macos-demand-ordered-weight-numeric-20261015-v2-records/root-closed.json)、[v3失敗](../../artifacts/macos-demand-ordered-weight-numeric-20261015-v3-records/root-closed.json)、[v4人工と独立reader](../../artifacts/macos-demand-ordered-weight-numeric-20261015-v4-records/root-closed.json)、[文書構文失敗](../../artifacts/macos-demand-ordered-weight-numeric-20261015-doc-syntax-failure-records/root-closed.json)、[文書閉鎖](../../artifacts/macos-demand-ordered-weight-numeric-20261015-doc-records/root-closed.json)。
