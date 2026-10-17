# TimesFM3を参考にした自作モデルの実用性研究 — 目的と進め方の再整理

## 需要とPSIの既存実装を接続例に加える（2026-10-16）

[denroku-psi-demoの現状と引継ぎ](denroku-psi-ai-integration-2026-10-16.md)を確認した。現状はPython LightGBM学習→Rust推論/照合→静的JSON→画面/PSIで、Python不要の再学習は公式C APIを使う別の未実装計画がある。共通AIの配置はbanto-ai、利用側は産業のbanto-industrialと需要・PSIアプリ。各利用側→banto-aiの依存方向を守る。

R1/R2は自作SmallForecasterを先行する。既存LightGBMの特徴量・木推論・Python不要学習を同一engineへ押し込まず、共通化はmodel版/来歴/数量の意味/進捗・保存等の境界から行う。需要26週の出荷点予測と産業32stepの分位点を区別し、PSI/受注採用判断は利用側へ残す。R0.1の数値契約は不変。需要側のfixture利用・LightGBM移行・平均モデル比較は別工程で仕様と範囲を固定する。

## Rust実装の現在の計画（2026-10-16）

[AIクレート実装と製品利用の計画](banto-ai-rust-implementation-plan-2026-10-16.md)に従い、banto-ai内のR1a/R1bから学習・保存再開、有限CARE比較、banto-industrial接続へ段階的に進める。各段階の合格/停止条件と責務を固定した。今回実装/学習は開始せず、[R0.1数値契約](rust-small-forecaster-r0-2026-10-16.md)は不変。

## 配置方針の訂正 — AIクレートはbanto-ai（2026-10-16）

AI本体のRustクレートは tyaro/banto-ai 側に置き、tyaro/banto-industrial は利用・接続先とする。前回の「移植先」は接続先の意味であり、AI実装の配置先に読み替えない。 共通AI crateの配置案は `crates/banto-ai`、製品型/取得処理/jobのhost/UIはbanto-industrial側のadapterに置く。依存方向はbanto-industrial → banto-ai。学習・保存再開もAI側の範囲であり、推論だけに縮小しない。[現行R0契約](rust-small-forecaster-r0-2026-10-16.md)と[機械設定r0.1](../../examples/configs/rust-small-forecaster-r0-20261016-r0.1.json)へ反映。数値/評価条件は不変、Rust実装・buildはまだ開始していない。以下の移植先という旧表現は接続先を指す履歴として読む。

## Rust R0とCARE分析の現在状態（2026-10-16）

[保存予測分析/R0結果](../results/care-saved-diagnostics-rust-r0-2026-10-16.md)と[R0詳細契約](rust-small-forecaster-r0-2026-10-16.md)を保存。CARE検知3/12は固定し、未検知9件の機械的内訳と正常誤警報/可用性差を分析した。新しい学習/forward/閾値変更は0。

人の指定で移植先は**banto-industrial**（tyaro/banto-industrial）。main commit93d99efa…のsourceをpinして実型/外部名binding/raw履歴の不足情報を確認した。ScadaProjectは対象外。初回backend候補はBurn=0.22.0/Flex CPU+autodiff、数値許容差・AdamW・中立形式/再開を実装前に固定。**次はR1の孤立Rust crateでcompileと固定train参照のforward比較**。対象repoのRust pin1.98.1での統合、学習再開/全依存license/製品API受入は未確認。主目的/保全優先/学習含む移植を維持する。以下の過去時点の「未準備/未学習」は履歴であり、CAREの現在状態は完了・凍結である。

2026-10-16 JST。人の最新指示「元の目的に戻す」「需要予測・PSIのほかに元々の産業分野での利用も確認する」と、CARE ZIPのデスクトップ配置報告に基づく。Astraとの共同整理。今回の成果は文書・ソースの読取り監査とローカルアーカイブの受領metadataで、新しい学習・予測・採点ではない。

## 保全・点検のCARE契約を固定（2026-10-16追補）

人の指示で[CAREの版・利用条件・sensor/asset確認](../results/care-metadata-contract-2026-10-16.md)と[固定契約r1](care-a-maintenance-contract-2026-10-16.md)を保存。v6公式MD5一致/CC BY-SA 4.0、入力とlabelを別rootに分離、最初のFarm A/5asset/22file/3 Avg信号を留一5foldに固定した。推定異常区間内の検知とrecord可用性を評価し、M1の区間coverageを正常/異常truthにしない。現在は数値入力未準備・CARE未学習/未採点。次にquantity/maskと実境界を確認する。Rustへの最終移植は学習・optimizer/checkpoint再開・alarm state・banto APIまで維持。以下は過去の経過を含む。

## M1完了・次の用途契約（2026-10-16追補）

人の明示指示で[MetroPT M1実学習・評価](../results/metropt-macos-m1-2026-10-16.md)を完了。3seed×full/self各4096更新、全予測保存後の一括採点、独立数値照合まで実行した。fullの集約pinballはself-only比2.105%改善（2/3seed）、3targetのMAEはMA15を改善した。一方、1seedと圧力pinballの悪化・油温区間coverage不足を残す。予測の探索的利点であり、異常予兆の有効性へ広げない。

[CAREイベント評価設計](care-maintenance-evaluation-design-2026-10-16.md)を次の保全・点検契約の入口とする。metadata照合・asset分割・時点/label・正常profile・event/誤警報/先行時間の固定は未完、CARE学習はまだ始めない。Rust向けには全6選択stateのparameter/bufferとAdamW moment/step、schedule位置を中立形式で保存した。Rust学習・推論/banto接続の実装成立は別工程で確認する。既読MetroPT testへの延長/校正を自動追加せず、需要/2015/正式holdout/OS境界を維持する。以下は過去の経過を含む。

## 現在の進捗と用途の優先（2026-10-16追補）

人の回答により産業側の第一優先は**保全・点検支援（異常の予兆）**。MetroPTの予測実験はその基礎確認で、予兆の有効性はCAREのevent評価で別に確認する。次の用途契約はCAREを優先し、油圧/XJTU全実験を待たない。必要な点検の先行時間や誤警報の許容値はまだ未設定であり、数値を捏造しない。

計画に沿って[MetroPT Mac M0](../results/metropt-macos-m0-2026-10-16.md)を完了。固定13日/3targetの厳格変換、8,967/123/123窓、Macの未学習forward2回、境界10項目/新guard6件、独立読戻し、Rust向けneutral初期stateを保存した。実学習/性能採点/2015再評価は0。以下の本文は初期整理時点の経過を含む。M1実学習は再開待ち、Rust学習/banto統合は最終目的として維持する。

## 主目的と前回解釈の訂正

**TimesFM3の公開構造を参考に、独立初期化・独自学習する自作モデルが、産業設備と需要予測の用途で必要な価値を、単純な基準に対してどこまで実現できるかを検証する。**

**最終到達点には、学習・推論の両方をRustへ移植し、bantoから使いやすく組み込める形にすることも含める。** 人の2026-10-16の追加指示による。Rustで前処理、forward、loss/backward、optimizer、保存/学習再開、推論を扱い、最終経路でPython interpreter/subprocessを必須としない。Python版は研究と数値比較の参照として使う。banto向けlibrary API/CLI、version付きモデル・再開checkpoint、学習jobの進捗/取消/再開を成果物とする。[具体計画のRust工程R0〜R4](timesfm-inspired-practical-evaluation-plan-2026-10-16.md#7-最終実装--学習も含めたrust移植とbanto統合)に従い、予測の価値・数値移植・統合の使いやすさを別判定する。推論だけの書出しで学習移植完了とはしない。Rust backendとbanto接続先の現行APIは今後確認して固定する。

需要予測・PSIは実用性を調べる対象の一つであり、産業用途や自作モデル研究を取り下げる指示ではなかった。mean28や統計補正を改善すること自体を主目的に置き換えた解釈を訂正する。[10月13日の主問](timesfm3-utility-and-reproduction-2026-10-13.md:5)、[当初の産業用途](../research-implementation-plan.md:13)を、人の最新指示に沿って再び上位に置く。

[直前のAstra目的監査](demand-purpose-alignment-astra-review-2026-10-16.md)の「TimesFMを本筋へ戻す根拠はない」という判断は、人の用途選択を目的の廃止と読んだ前提に基づくもので、現在の方針として採用しない。一方、人工境界試験の反復を区切ること、数値最適性と実予測性能を分ける指摘は維持する。旧文書は履歴・原証拠として書き換えない。

構造の参考実装、独自データ学習、公式学習の再現、公式同等性能、業務への有用性はそれぞれ別の到達点とする。自作することだけ、統計モデルに微差で勝つことだけ、人工試験が通ることだけを成功条件にしない。

## 既存成果をどう活かすか

| 成果・根拠 | 確認できている範囲 | 今後の使い方・限界 |
| --- | --- | --- |
| [産業用SmallForecaster](timesfm3-small-model-design-2026-10-13.md)、[独自学習pilot](timesfm3-small-model-pilot-2026-10-14.md) | 109,024 parameter、3系列、C128/H32、時間・系列attention、分位点。独立初期化から学習・選択・予測を完走 | 産業側の自作モデルの出発点。full対self-onlyの比較を再利用。単日・1設備・1seedの探索結果 |
| 同pilotの精度 | fullはself-only比で集約pinball約2.55%低い。圧力・電流のMAEは両単純基準より小さいが、油温は移動平均15に届かず、区間も未校正 | 系列間情報が役立つ条件・役立たない条件の仮説。油温失敗を消さず、別期間・設備への一般性は未確認 |
| [公式TimesFM3の旧MetroPT評価](../results/timesfm3-metropt3-evaluation-2026-09-04.md) | C120/H15、past共変量11、同条件の統計基準との限定比較で有望だった報告 | 参考水準。自作C128/H32/V3とは条件が違い、直接の勝敗・同等性能の証拠にはしない。旧process peak約2.77GiBは現在2GiB上限を超えるので同じ実行を提案しない |
| [需要用Block再利用モデル](../results/store-sales-small-model-2026-10-14.md)、[mean head](../results/store-sales-mean-pilot-2026-10-14.md) | 過去・未来暦、欠測mask、日次配分と総量の分離。単純基準への追加価値は未確認 | 入力契約と失敗原因の教材。既存2016/2017を読み直さず、同じtestへ調整しない |
| [需要StatisticalFeatureMean](../../models/mini-transformer/demand_statistical_feature_model.py)、[Mac新規生成](../results/demand-macos-rebuild-2026-10-15.md) | 自己系列TransformerEncoder＋過去統計8入力の平均補正。30,369 parameter、Macでstate/profileを生成済み | 需要側の保存モデル候補。産業SmallForecasterとは別の構造で、同じ多変量モデル・同じ重み・汎用化済みとは呼ばない |
| [既存10店2015の旧NN評価](../results/demand-existing-stores-2015-2026-10-15.md) | 元の250窓ではjoint MSEがmean28比0.758848%改善、MAE/WAPEは悪化、暫定2%目安未達 | 小幅差と指標の衝突を示す既読の開発記録。この値を後続の休業相当仮定・元日入り評価の成績へ付け替えない。2015再評価は停止 |
| [営業・ゼロ・欠測の分離](../results/demand-sales-state-2026-10-15.md)、後続の休業相当仮定 | 発行時点の入力、raw観測と仮定、観測のみ／休業相当欠測0仮定の分離、総量支持の扱いを実装 | 需要モデル共通の入力・評価資産。未知を祝日だけで確定しない。営業日の欠測は0補完しない。仮定は物理的な休業の真値証明ではない |
| [重み付きconsumer](../results/demand-weighted-numeric-prefix-2026-10-15.md)、[QP solver](../results/demand-weighted-solver-artificial-2026-10-16.md)、[最新境界](../results/demand-rank3-zero-boundary-artificial-2026-10-16.md) | 元母数・重み、β0再現、独立最適性証明、制約付き非ゼロ解→日次、丸め・floor・厳密0を確認 | 別の統計補正候補と評価の参考部品として保管。Transformerの学習・性能・TimesFM再現成果へ算入しない。直ちにQP実fitへ進まない |
| 時点分離・source pin・予測先保存・全stdio/exit・closure・Mac資源計測 | 来歴と評価の再現基盤がある | 二領域で再利用する。既存試験や証拠保存の件数を増やすこと自体を研究課題にしない |
| [CAREローカル受領metadata](care-local-archive-metadata-2026-10-16.json) | ZIPとREADMEの確認まで | 産業の異常予兆検証に使う新しい候補。未取込・未評価で、旧「手動download待ち」は現在状態ではない |

### モデルの系譜と出力を混同しない

- 産業SmallForecasterは時間causal attention＋同位置の系列attentionを持つ。需要の初期多系列モデルはBlockを再利用した別の入出力・headであり、最新StatisticalFeatureMeanは自己系列encoderによる別系統の候補。
- [SmallForecasterのForecast.mean](../../models/mini-transformer/small_model.py:64)はcontext正規化の平均であり、将来の期待値headではない。p50も平均販売数量へ読み替えない。需要mean用の出力と評価を別に使う。
- 共通構造や部品の価値を検証することと、一つの重みで両領域をzero-shot予測できることは異なる。後者は今回成立しておらず、初期の成功条件にも追加しない。
- 公式重み・教師出力を用いる経路は独立学習と分ける。現在の設計を公式の完全再現・公式同等性能と表示しない。外部仕様・利用条件を新たに採用する時は、その時点の一次資料と版を確認する。

## 二つの領域で答える問い

| 領域・順序 | 自作モデルで答える問い | 比較と判断 | 未確認の業務価値 |
| --- | --- | --- | --- |
| 産業① 設備tagの予測 | 過去の圧力・温度・電流の相互関係が、単系列と単純基準に比べて、将来の信号と予測範囲を有用にするか | 当面は既存MetroPT pilotのC128/H32を構造比較の参照とし、運用時間幅と混同しない。候補full、自作self-only対照、last-value/MA15を核に、target別MAE/RMSE・pinball/WIS・coverage/幅・欠測時の可用性・遅延/メモリを別報告。期間や用途を増やす前に条件を固定 | 何分先の予測で、誰が何を判断するか。圧力低下・温度上昇の確認を助ける候補として扱い、許容誤差や実アラーム閾値を作らない |
| 産業② 異常の早期検知 | 自作モデルの予測残差・範囲が、運転状態を考慮した単純検知より、誤警報と検知遅れの面で役立つか | CAREを候補とし、先にデータ契約を固定。単純な運転状態別統計検知を基準にし、必要な場合だけモデル残差を一候補追加。イベント単位の検知率・誤警報・先行時間・正常期間への影響を主に扱う。forecast MAE改善だけで検知成功としない | 保全担当者の点検判断。実際の停止回避・費用低減は別の検証 |
| 需要予測・PSI① 数量予測 | 暦・過去水準・変化・欠測を扱う自作モデルが、同じ情報と休業仮定のmean28より、日次数量と14日総量を改善するか | 既存10店・調整2014以前を維持。四季平均の過小量/過大量非増加と既存MSE条件、観測のみ／休業相当欠測0仮定の分離、全店・季節・通常/元日の報告を維持。NNと統計補正の結果は別欄 | 数量誤差の小幅改善を生産/補充判断の価値へ直結させない |
| 需要予測・PSI② 意思決定 | 予測の違いが、共通の在庫・納期・費用条件で欠品/過剰/廃棄を減らすか | 現在は未評価。条件を後から都合よく設定しない。平均・中央値・意思決定量を分ける | 在庫、リードタイム、ロット、賞味期限、費用、service level等が必要 |

産業①と需要①は両方を研究の本線に残す。実行をすべて同時に始めるという意味ではない。CAREは産業②の独立した応用評価であり、MetroPTの予測研究を廃止する代替ではない。

元々の[commissioning、drift、rollback可能なprofile、read-only Hub連携](../research-implementation-plan.md:15)も応用先として保持する。ただし、通常予測の区間がそのまま正常envelopeとは限らない。運転mode・正常の根拠、汚染防止、held-outの検知・profile比較、rollback確認を別に要する。現在の需要補正やCARE受領だけでこれらを完了・採用としない。既存C0/C1/C2の合成評価を自作Transformerの性能件数へ加算しない。

## CAREの現在状態と取込前の設計

親agentが人の指定した `/Users/tyaromax/Desktop/Care_to_compare.zip` を確認した。5,503,439,673 B、ZIP中央directoryは110 entry、宣言展開総量19,987,485,991 B。streamによる原本SHA-256は `ca61379e98956d891041ad45c885109bd8a14199fde0688d0184a11c2d4194f1`。このhashはローカル原本識別で、公式digestとの一致や配布版を認証したものではない。

README記載では3風力発電所・36風車・95dataset、10分間隔のSCADA、発電所ごとに86/257/957特徴量。各CSVにtrain_test・asset_id・status_type等、別のevent_infoに正常/異常labelとイベント期間がある。これはREADMEの説明で、実CSVとの整合は未確認。README以外のmember payloadはまだ読んでいない。feature_descriptionとevent_infoの内容、実観測、イベント一覧・発生時刻は未読。

今後の入口は次の順序とする。今回これらの本体処理は行っていない。

1. [従来の取得案内](pc-handoff-2026-10-14.md:69)の配布元と、原本の版・利用条件・公式digestの有無を照合する。ZIP名だけでZenodo v6と認定しない。
2. READMEとセンサーの説明を基に、対象の物理量、単位、状態、時刻・集計区間、予測可能な情報を固定する。957列を小型V3モデルへそのまま入れず、イベント結果を見てセンサーを選ばない。
3. 観測学習prefixと評価labelを分離する設計を先に書く。同一風車の複数event・重複履歴を学習と評価へ無造作に跨がせず、発行前実績だけで前処理/閾値を作る。未来のstatus、train_test区分、event_label、event_start/endを予測入力へ混ぜない。statusは既知時点を満たす運転条件としてだけ検討する。READMEの「正常運転」statusから無故障を保証しない。
4. 原本はその場で保持し全展開・全量複製をしない。将来の取込も、固定した少数対象をstreamで読み、出力上限内の限定sliceを新rootへ保存する計画を先に作る。ZIP全体のtestzipやCSV一括decodeも今回行わない。

旧Store Salesの2016/2017・予約店舗31–54の禁止は需要側の境界であり、CAREの匿名化した年・event IDへ機械的に転用しない。一方、CAREを受領したことは旧正式holdoutや未知評価labelの読取り、実学習・採点の再開を許可するものではない。

## Macで現在使えるものと不足

文書・sourceの存在と、データ・学習済みstateの受領を分けて記録する。

- 産業SmallForecaster、data.py、train.pyのsourceはMacにある。原Windowsの `artifacts/representative-small-model-training-20261014` と `artifacts/benchmark/benchmark-metropt3-timesfm3` は今回確認した同相対pathには存在しない。`artifacts/public-datasets` も存在しない。Mac全体や元PCにないと証明したものではない。
- 需要の `artifacts/macos-demand-rebuild-20261015` は存在し、Mac3.14.8の新規学習・評価は既存報告に保存済み。今回stateをloadし直したりforwardしたりしていない。
- CAREはローカル原本候補を受領したが、データ変換・学習・検知評価用のdatasetはまだない。
- 旧Windows産業結果は報告の根拠として使えるが、Macで再現・資源適合したとは表示しない。原閉鎖rootを受領する場合は別pathでpin照合し、同名rootへmergeしない。必要な資産は原本manifest・split・尺度・選択state・保存予測・source/closure・失敗記録とし、artifacts全体のコピーは必須にしない。

## 次の工程と終了判断

**直ちに進める順序は、共通資産の対応整理 → 産業側のデータ契約とMac接続条件 → 二領域それぞれの有限評価計画。新しい人工境界ケースやQP実fitを次工程にしない。**

| 工程 | 作るもの | 終了点 |
| --- | --- | --- |
| 0 今回 | 本計画、Astra確認、CARE原本metadata、目的を修正したhandoff/roadmap入口 | 目的・資産・未回答・停止を一度整理して終了。完了 |
| 1 次の準備候補 | CAREの配布版/利用条件・センサー説明の照合、MetroPT旧資産の受領必要一覧、Mac対応に必要なsource差分の読取り | 観測・イベントlabelを新たに採点せず、対象/時点/split/入力量/保存上限の案を固定。具体的不足があればそれを列挙して終了 |
| 2 有限評価計画 | 産業予測と需要数量の問いを一件ずつ固定し、必要な場合にCARE検知を後続の一件へ分離 | 使用情報・候補/対照・fit/選択/評価分離・主副指標・資源・失敗停止を出力前固定。既存stateの確認で答えられる問いには新学習を追加しない |
| 3 再開指示後の実験候補 | 必要な一候補と一つの機構対照を、固定範囲で一巡する保存済み証拠 | 工程不成立／追加価値なし／条件付きの探索的利点を区別。悪化・全baseline・未判定でも終了。seed/幅/日付選別や同じtestへの救済をしない |
| 4 応用の判断 | 異なる運転/設備への確認、保全・PSIの共通判断条件 | 用途・データ・条件が揃う場合だけ別工程へ。予測だけで異常検知・試運転・PSI採用を認定しない |

需要2014・2015と産業MetroPTの既読単日は、整理し直しても未使用holdoutにならない。独立検証が必要な段階では、学習/調整へ使っていない設備・期間を事前に確保する。現在の制約内で確保できなければ「一般性未確認」で止め、既読期間の反復で埋めない。新しい対象で運用上の合格値を設定する際は、人の必要誤差・先読み時間と計算予算に結び付ける。目的復帰を理由に需要側の既存非悪化条件を緩めない。

## Astraの最終確認と採用判断

既存Astra agent `astra_weight_support_audit` が、元の研究資料・モデルsourceを独立読取りし、さらに本統合案をread-onlyで確認した。目的整理の範囲で大きな矛盾・blockingなしという回答を得た。これは実行許可や性能の合格を意味しない。

採用した指摘は以下。

- 前回の「TimesFMへ戻す根拠なし」を撤回し、需要という用途の選択と上位目的の廃止を区別する。
- 三モデルの系譜、公式との異条件、context正規化平均と将来期待値、QPとTransformerの成果を分ける。
- 産業予測と需要数量を本線に置き、CAREは原本hash保存・未取込として異常予兆の別評価へ位置付ける。AstraはCARE本体を開かず、親agentの受領metadataとREADME観測に基づく設計を批評した。
- 資産・データ契約・有限評価計画を次工程とし、人工境界の反復やQP実fitへ自動接続しない。
- 「Mac平均模型はmean28を上回らず」と一括せず、開発別店舗の未達と、既存10店の小幅MSE改善/MAE悪化を分ける。Astraも以前の総括の対象群限定が不足していたと訂正した。

主agentはこれらを採用し、今回は目的・計画の整理までで終了する。新しい学習・評価の開始判断はしていない。

## 今回の実行範囲と維持する境界

実データ学習と2015再評価の停止、heartbeat PAUSEDを維持。現在の人の指示は目的整理とCAREの配置報告であり、学習再開指示ではない。CAREは「手動取得待ち」から「ローカル候補あり・原本hash保存・未取込」へ更新した範囲だけが変わる。

2016/2017の再読・予約31–54・販促数量・正式holdout・Windows native・CAREの観測/イベントlabel decode・課金API・新規download・外部研究データ送信・Git push・本番採用は今回行っていない。Astraは既存agentを再利用し、追加agentは作成していない。

将来実験の親900秒/子870秒、Mac physical footprintとpeak RSS各2GiB、既存artifact/EvidenceStoreの個数・単体・総量・失敗予備上限を維持する。大きいCARE原本の外部入力と、新しく出力するartifactの容量は区別する。source・state・全stdio/exit・失敗・closureを残し、旧変更・失敗・closed rootsを上書き/削除しない。Windowsのprivate bytesとMacのfootprint/RSSは同じ指標ではない。

今回の実行は文書・source読取りとZIPのstream hash/中央directory/README読取りのみ。モデルimport・学習・solver・新予測・再採点・OS依存suiteは未実施。旧Windows報告、既存Mac共通経路の結果、今回の文書整理を別々に扱う。
