# TimesFM3参考の自作モデル — 実用性検証の具体計画

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

2026-10-16 JST。人の「計画を立てましょう」に対応。[上位目的の再整理](timesfm-inspired-dual-domain-plan-2026-10-16.md)と[産業3データのMac取得結果](../results/industrial-data-macos-intake-2026-10-16.md)を出発点とする。Astraのread-only批評を反映した**計画**であり、新実験の開始記録ではない。

## CAREの現在状態（5fold実学習と評価完了、2026-10-16）

[CARE5fold実学習・イベント評価を完了](../results/care-macos-learning-evaluation-2026-10-16.md)。固定r1の各4,096更新/4val選択、既存train profile/scheduleを維持し全5fold freeze後に採点。共通支持で事前4条件を通過（macro検知20%対baseline6.67%、false0.84656対1.07104/1000記録h、警報割合/earlinessも改善）。ただしpooled3/12、9未検知、3asset検知0、nativeだけがevent22を検知した可用性差を保持する。全5unitと独立保存値検算pass、model/AdamW/RNG/sampler位置のneutral参照も保存。r1は完了・固定しtest再調整を追加しない。次は保存値での未検知/asset/可用性の仮説整理とRust R0契約/backend・配布条件の整理。保全・点検第一優先、産業/需要の自作モデル実用性、学習を含むRust移植とbanto統合を維持し、製品採用や未知holdout成功とはしない。需要2015停止、既存調整/評価分離、OS境界、heartbeat PAUSEDを維持。

## M1の現在状態（人の明示再開後、2026-10-16）

[3seed実学習・評価を完了](../results/metropt-macos-m1-2026-10-16.md)。固定13日/3target、3seed×full/self-only各4096更新・4val時点、全予測freeze後の一括採点を変更せず実行した。fullの集約pinballはself-only比2.105%改善・2/3seed一致、点MAEは全3targetでvalidation固定MA15比改善・各3/3seed一致。1seedと圧力pinballの悪化、油温coverage80の約69.4%を保存し、予兆・正常envelope・製品採用を認定しない。

M1の有限実行はここで終了し、既読testへの追加seed/延長/校正を自動追加しない。CAREの実学習・評価も上節のとおり完了した。全6選択modelとAdamW学習状態を中立形式に保存し、Rustの学習・推論とbanto統合の最終目的を維持する。Windows native/OS依存suiteと需要2015は未実行/停止、heartbeat PAUSED。以下のM0/再開待ちの記載は当時の経過を含み、現在状態は本節と結果報告を優先する。固定JSON/manifest/recipeのbytesは不変。

## 計画の遵守・現行revision（2026-10-16追補）

**今後の作業はこの計画と工程別の詳細仕様に沿って行う。主目的や評価条件を、実装の都合・結果の良し悪しで黙って変更しない。** 人の最新指示を優先し、各工程の開始時にPlan ID/revision・問い・固定入力・成果物・中止点を保存する。目的/期間/対象/特徴量/候補/指標/seed/予算を変更するときは、理由・影響・既読情報・旧新差分を実行前に記録し、旧証拠を保持する。test結果を見た後の変更は新候補であり、同じ未知評価のやり直しにはしない。固定契約内の通常実装では反復確認を求めず進めるが、停止中の実学習・2015再評価を計画の存在だけで解除しない。

現在のM0/M1契約は **MPT-MAC-20261016-r2**：[MetroPT詳細仕様](metropt-macos-multiday-protocol-2026-10-16.md)、[設定JSON](../../examples/configs/metropt-macos-multiday-20261016.json)、[日時候補窓manifest](../../artifacts/metropt-complete-days-timestamp-20261016/calendar-windows.jsonl)。数量を見ない日時監査で元の連続43日案が不成立だったため、日時上の完全日を時系列順で13日選ぶ独立segment案に改訂した。旧監査・[改訂前全文snapshot](../../artifacts/metropt-plan-detail-20261016-records/before-index.json)を保存済み。下記も現行案へ更新した。

r2詳細化後の人の「計画に沿って進める」により、[M0の実装・数量品質・最小接続](../results/metropt-macos-m0-2026-10-16.md)を完了した。13日/3target、共通窓8,967/123/123を維持、未学習forwardはfull/self各1回だけ。実学習・validation/test予測・性能採点・2015再評価は0で、M1は再開待ち。Rust向けのneutral初期stateを保存し、実学習停止/heartbeat PAUSEDを維持する。新しい具体的理由なしにM0や同種監査を反復しない。固定JSONのstatus/authorizationは凍結時点の記録であり、最新の実装状態とM0許可範囲は結果・phase記録を参照する。

## 1. 目的と成果の区別

**TimesFM3の公開構造を参考にした自作モデルが、産業設備と需要予測で、単純な基準以上の価値を持つかを検証する。** 比較対象のmean28やQP自体を改善することへ主目的を置き換えない。

**最終到達点に、学習・推論の両方をRustへ移植し、banto側から使いやすく組み込める形にすることを加える。** 2026-10-16の人の明示指示による目的の追加である。Python版は実験と数値比較の参照実装として活用し、最終のRust学習・推論経路ではPython interpreterやPython subprocessを必須にしない。予測の実用性、Rustへの数値移植の成立、banto統合の使いやすさを別々に判定する。Rust化そのものを予測改善や製品採用の証拠にはしない。

| 到達点 | 答えること | 現在 |
| --- | --- | --- |
| 実装成立 | 独立初期化の自作モデルを動かし、情報境界・資源・保存を守れるか | Windowsの産業pilot、Mac需要モデルの実績に加え、Mac産業モデルの未学習forward接続を確認。Mac産業M1の3seed paired実学習・評価も完了 |
| 予測上の追加価値 | 単純予測を上回るか、系列間経路が何を加えるか | 単日・既読期間の限定結果。新しい複数日/設備への一般性は未確認 |
| 用途上の価値 | 点検、運転判断、生産/在庫判断に役立つか | 必要な先読み時間・損失・判断条件を具体化して別評価する |
| Rustでの学習・推論とbanto統合 | Pythonを必須にせず学習、再学習、再開、推論、モデル管理をbantoから扱えるか | 最終目的へ追加。API/モデル形式/数値比較/配布条件の設計から進める。Rust実装・統合受入は未着手 |
| 公式と同等 | 公式TimesFM3の学習・汎用性・性能を再現したか | 未達。今回の小型独自学習とは別の主張 |

人の回答により産業用途の第一優先は**保全・点検支援（異常の予兆）**。MetroPT予測は基礎確認とし、異常予兆の価値はCAREのevent評価へ進めて別に判断する。次の用途契約はCAREを優先し、油圧/XJTUの全実験終了を待たない。必要な保全先行時間、許容誤警報、業務損失は未設定。以下の予測時間幅は探索設定で、現場要件を確定したものではない。

## 2. 二領域の順序

需要予測と産業予測を両方の本線に残す。同時に多数の学習を始めず、最初の実行対象をMetroPTの一件へ絞る。

| 工程 | 問いと成果物 | 次へ進む判断 |
| --- | --- | --- |
| M0 完了 | MetroPT複数日比較の実行前パッケージ。Mac移植差分・時刻と既読履歴・固定窓/期間・一対の学習条件・集計/終了条件を一つにする | 未決を解消し、実学習を再開する明示指示後にM1へ。監査の反復はしない |
| M1 完了・産業の最初の評価 | MetroPTで自作full/self-onlyとlast-value/MA15の複数日比較 | 工程成立、機構の価値、モデルの価値を別判定。未達でもその一巡で終了 |
| D1 需要の本線 | 既存10店の平均数量を改善するモデル一候補の設計。旧NNと休業/欠測・支持の不一致を解消し、同条件mean28と比較する契約 | 今回は設計まで。新学習・実2014採点・2015再評価へ自動接続しない |
| I2 油圧 | 制御された60秒cycle内の短期予測で、多信号経路の価値が残るか | 状態診断と分離した一候補の有限比較。M1を見た無制限の調整はしない |
| I3 XJTU | 2軸RMSの短期推移を、未学習の軸受で予測できるか | 短寿命軸受を落とさない固定小型構成。RULや故障検知の合格へ転用しない |
| I4 CARE | 運転状態を考慮した予測残差が、単純検知より故障予兆に役立つか | asset分離・label独立と単純検知との比較。予測誤差ではなくevent単位で判定 |
| R Rust化・banto統合 | 学習・推論のRust実装、version付きモデルと学習checkpoint、banto用API/実行管理 | 下記R0〜R4で段階確認。数値同等性と業務価値を分け、推論だけで移植完了としない |
| A 応用 | commissioning、drift/profile、read-only Hub、PSI意思決定 | 対応する業務条件と評価データがある場合だけ別工程として具体化 |

I2/I3/I4をM1開始の条件にしない。保全・点検が最優先ならM1後にI4のデータ契約を優先し、油圧/XJTUの全実験完了を待たない。需要D1の設計もM1の勝敗に従属させない。これらの工程を一括自動実行する許可ではない。

## 3. M0 — 実行前パッケージ（今回完了）

新しい原データの取得や、同種の人工境界試験は不要。以下を一度まとめて閉じる。

1. **Mac移植差分**：既存 `small_model.py` の構造を維持し、Windowsメモリhelperへ依存する `train.py/check_model.py` をそのまま起動しない。新しいMac用trainer/launcherで入力adapter・CPU実行・時間/メモリ・保存を接続する設計。旧source・Windows失敗・closed rootsは保持する。
2. **時刻と既読履歴の監査**：取得済みMetro原本のtimestamp列と既存の読取り記録だけで、下記期間の可用性・cadence・欠損/重複/順序を確認する。数量・誤差の良さで日付を選ばない。既読単日は新しい未知評価と呼ばない。新しい期間も利用履歴を確認するまでは「未使用」と断定しない。
3. **一つの候補窓manifest**：train/validation/testのorigin・context/label境界と除外規則を固定。timestampだけで分かるのは暦上の候補窓であり、数量のfinite性等を含む実際の共通支持は、後の許可された読取り時にこの固定規則を適用して確定する。各日を独立segmentとし、context/labelとも日・splitを跨がない。未来共変量・故障報告は入力にしない。数量変換や実forwardを含む次工程の範囲は別に明示する。
4. **条件と終了点の固定**：seed・更新数・選択時点・全予測先保存・集計式・不足時の停止を保存。時間/品質による不成立は、別日への自動移動で救済しない。支持の最低条件は、この時刻監査後・数量/成績の読取り前に一度決める。

M0の出口は、実行できる一件の契約と、残る未決点の一覧。具体的な不足がなければ準備も終了する。Mac固有の新しい接続を実行する場合は一回の小さいtensor接続に限定し、完成済み10構造確認や全CIを反復しない。**初版は走査0、r2で日時監査を実施。その後のM0実行で新converter/adapter、paired trainer/slot/scorer、数量品質と未学習接続を実装・確認した。学習経路自体のbackward/optimizer/再開は未実行で、M0接続と学習成功を区別する。**

M0の納品物は、Mac用実行部分のsource/差分仕様、固定した設定JSON、候補窓manifest、必要なMac接続の記録を一組とする。実学習を自動起動する入口は作らない。実装と接続まで進める指示があればその範囲を実施し、さらに別の計画書を作るだけで終わらせない。

## 4. M1 — MetroPTの有限比較案

以下はr2で固定した有限比較契約。M0で数量品質とMacの未学習接続は成立したが、実学習の勾配/optimizer/所要時間は未確認。学習再開を許可するものではない。詳細条件は仕様とJSON、実装結果はM0報告を参照する。

| 項目 | 設計案 |
| --- | --- |
| 対象 | tp3/bar、oil_temperature/ºC、motor_current/A。結果を見て圧力だけへ対象を絞らない |
| 期間 | timestamp完全日から既読02-21を除く最初13日。train 02-03/04/15/16/18/22/25、val 03-08/18/22、test 03-23/25/26（全2020年）。日内独立窓。source-naiveを研究上UTC解釈。確定後に数量不良でも差し替えない |
| 入出力 | 既存C128/H32/P32、3系列、1分間隔。過去128分→次32分、3分位点。14信号全部や未来負荷を自動追加しない |
| 主候補/機構対照 | 既存109,024 parameterのfull/self-only一対。時間・系列attention等の構造は維持し、系列maskだけを変える |
| 単純基準 | 同じ情報・originのlast-valueとMA15を両方報告。対象ごとの主baselineはvalidation MAEでこの2方式から一度選び、testでは選び直さない |
| 学習 | 独立初期化、CPU float32、batch8、AdamW lr3e-4/wd.01等を詳細仕様へ固定。train-only尺度とcontext-only正規化。日等確率の置換抽出、各seed内で初期stateとbatch列を両構成に共通化 |
| 有限予算 | 固定seed 20261016/20261017/20261018、3seed×2構成。各構成共通4,096更新上限。別seed・幅・LR・期間gridは0 |
| 選択 | 512/1024/2048/4096更新の4時点だけをvalidation固定尺度pinballで比較し、同値は早い時点。両構成を同じ共通更新数まで完了し、選択checkpointを個別保存 |
| testの隔離 | 全3seedの選択stateを確定し、全test予測を保存してから一括採点。後続seedへ先行test成績を返さず、best seedを選ばない |
| 窓 | train 8,967、val/test各123の日時候補を固定、日・split跨ぎなし。日ごと最低train1,153/1,281、eval37/41で分母固定。raw数量不良は変換全体失敗、変換済quality窓guardとは区別。補間なし |
| 集計 | seed別・日別・target別・lead別、全支持/除外。異なる原単位のMAEを平均しない。集約は固定train尺度で無次元化し、日とtargetを等重み |
| 保存 | 各seedを独立したfresh実行rootとする。全seed完成前に「良いseedだけ」のtest採点へ切替えない。未完ならcampaign incomplete |

4,096更新はこの有限候補の学習予算であり、収束やモデル能力の上限を保証しない。3seedは**学習乱数への感度**であって、3独立設備・3独立検証ではない。同じ1設備・指定各3日のvalidation/testの範囲でしか結論しない。取得可用性で選ぶ回顧的標本で、欠測のある連続運用を代表しない。

### 分けて判定する三つの問い

- **系列間経路の追加価値**：full対self-onlyの固定train尺度pinball/WISを主に比較する。seed平均と各seedの方向、target別の利点/悪化を併記。平均が小さく、3seed中少なくとも2つが同方向の場合のみ「この条件で機構上の利点が見られた」と記述する。効果量を必ず出し、これだけで実用性を合格にしない。
- **自作モデルの予測価値**：各targetのp50 MAEを、validationで固定した単純baselineと比較する。seed平均の改善と少なくとも2seedの方向一致があるtargetを、事前の3target全表の中で示す。全target/全seedの悪化も残す。一部の改善をモデル全体の優位としない。単純baselineに分位点を用意していないため、そのMAEとモデルWISを数値の大小で比較しない。
- **用途への適合**：遅延・メモリ・予測範囲の幅/coverage・外れ方向・実際の判断に必要な誤差を確認する。研究上の微差や名目coverageだけで点検支援・正常envelope・運転合格を認めない。最小実用差や業務損失の閾値は、用途が決まるまで未設定であることを開示する。

同じ日・lead・targetの大量の点を独立な標本数へ数えない。3seedの一致を統計的有意性としない。旧公式TimesFMのC120/H15/11過去共変量という異条件の報告は参考欄だけに置く。旧process peak約2.77GiBの実行や新しい公式重み取得を、今回の2GiB内計画へ追加しない。

### 終了条件

- 情報境界違反、nonfinite、共通更新未完、支持不足、900/870秒・2GiB・保存上限超過：工程未成立。残りのseedや同じ評価への救済探索は止める。
- 完走して単純基準に差がない/悪化：この条件で追加価値未確認。学習延長やtestに合わせた修正を自動追加しない。
- 条件付きで改善：同設備・指定複数日の探索的利点まで。別運転/設備での確認は別の次工程にする。
- 用途を満たすか判断できない：業務適合は未判定。監査・人工件数を増やして代替しない。

## 5. 他データで確認する役割

### 油圧：cycle内予測と状態診断を分ける

準備済みPS1/PS2/EPS1、10Hz、C128/H32なら過去12.8秒→次3.2秒。最初はこのcycle内予測で、full/self-only一対とlast-value/MA15を比較する。実行予算やseed数はM1の運用結果を使い**性能結果を見ず**次契約で一度固定する。cycleを跨ぐ窓は作らず、cycle単位の分割・集計・train-only正規化を維持する。

profileの状態labelを入力へ入れない。完成60秒cycleから状態を推定する問題と、cycle途中から未来を予測する問題は異なる。状態診断へ進む場合は、支援する部品/判断、利用できる時点、単純なセンサー統計による対照、class支持と誤判定を先に決める。既存cycleブロックは同一試験装置であり、自然劣化・RUL・独立設備の証拠ではない。class不足を評価後のcycle入替えで救済しない。

### XJTU：短い寿命も保持したRMS予測

既存C128/H32では、例えば42/52/114点の軸受が評価できず、train側の123点軸受も落ちる。長い軸受だけへ絞らない。

- 次候補は両軸RMSだけのV2/C16/H4/P4、幅64/2blockという一つの小型構成。16分の過去要約から次4分のRMSを予測する探索設定で、RULの出力ではない。
- 8特徴量のどれがtestで良いかを探さず、先に両軸RMSを選ぶ。残る特徴量は記述資料として保持する。
- 各条件でordinal1–3がtrain、4がvalidation、5がtestという準備済みの軸受単位案を使う。全15軸受を保持し、同一軸受の窓をrandomに別splitへ混ぜない。
- 新しい変換rootで全軸受の必要特徴量を用意する。既存の3軸受pilot rootを書き換えない。波形間を連続25.6kHzデータへ結合しない。
- trainは軸受を等確率で選んでから窓を選ぶ。評価も軸受等重み・条件別とし、長寿命軸受が窓数で支配しない。
- 入力には発行前RMSだけを渡す。全寿命の平均/標準偏差、残寿命比、最終file数を正規化や特徴へ使わない。baselineはlast-valueとMA5を固定候補とし、性能を見る前に選択方法を確定する。
- V/H/Pを変えるため旧V3モデルの接続成功は流用しない。必要なshape/mask/headの差分だけ確認し、汎用可変長ライブラリへ拡張しない。

RMS推移の予測に成功しても、故障時刻、保全先行時間、RULの正しさは別問題。これらは別のlabel契約と判断が整ってから検証する。

### CARE：実際の異常予兆の候補

原本は受領済みだが、版・利用条件・センサー説明・asset同一性・重複履歴をまだ照合していない。まずmetadataで対象と分割を固定し、その後に限定した観測prefixと評価labelを分離する。同一風車の複数eventや重複履歴がtrain/testを漏れないようにする。

未来status・event_label・event_start/endを入力にせず、正常運転statusを無故障の保証としない。運転状態別の単純検知と、自作モデル残差による一候補を比較する。閾値・持続条件はtrain/validationだけで固定し、event単位の検知率・誤警報・先行時間・正常期間の警報を報告する。単なる予測MAEやRMS改善を故障検知成功へ読み替えない。全20GB展開・全変数探索を最初の一件にしない。

## 6. 需要予測・PSIの本線

既存の平均数量モデル、過去統計・暦・mask、ゼロ/欠測分離、baselineと保存評価を再利用する。産業用Q50や `Forecast.mean`（context正規化平均）を期待販売数量へ流用しない。

D1は「発行時点で利用可能な入力と同じ休業仮定を持つ平均数量モデル一候補が、mean28より日次/14日総量に価値を加えるか」の設計に限定。旧NNの小幅MSE改善/MAE悪化、fit時の元日支持、後続の休業相当処理、入力分布の不一致を整理し、2014以前の調整範囲だけで答えられる問いを一つ選ぶ。過去に失敗した店舗・発行日専用の補正を加えない。

四季平均の過小量・過大量非増加と既存MSE条件、同休業mean28、観測のみ／休業相当欠測だけ0仮定の分離を維持する。営業日の欠測は0にしない。QPは別の統計比較候補・評価部品として保管し、ニューラル実用性研究の前提条件へ戻さない。

2014は既読の開発期間、2015は再評価停止。既読の結果を未知検証へ戻さない。産業側の再開指示を需要の実学習・2015再評価へ拡張しない。PSIは在庫、入荷、生産/調達lead time、ロット/賞味期限、過不足費用等を共通条件にしてから別に検証し、予測の微差をPSI採用にしない。

## 7. 最終実装 — 学習も含めたRust移植とbanto統合

### 移植の対象と使い方

自作モデルの前処理、時点・ゼロ/欠測/qualityの扱い、train-only尺度、forward、loss、backward、自動微分、optimizer、checkpoint選択、学習再開、推論、評価を対象とする。産業の分位点モデルと需要の平均数量モデルは意味と仕様を分け、一つのheadや同じ重みへ無理に統合しない。baselineと時点分離・共通支持・保存契約も引き継ぐ。

banto向けには、(1)Rust library API、(2)同じ処理を呼ぶ小さいCLI、(3)version付きモデルpackage/学習checkpoint仕様を成果物にする。APIは概念上、入力検査・学習job開始/進捗/取消/再開・モデル読込・予測・評価を扱う。実際のmodule名やbanto側型との接続は、接続先repositoryの現行契約を確認してから固定する。接続先をまだ確認していない段階で既存banto APIへ適合済みとしない。

呼出側はPython実験scriptや内部tensor配置を知る必要がない形を目指す。tag/店舗ID、時刻、単位、shape、quality、予測の種類（平均/p50/分位点）、モデルversionと来歴を明示し、入力不正・非対応version・資源上限・中断を型付き結果で受け取れる設計にする。学習は長いjobとして推論/アプリの応答経路から分離し、取消後も保存済みcheckpointと失敗理由を残す。新モデルは明示的な切替えで利用し、旧版へ戻せるようにする。

推論packageには構造version、parameter、前処理/尺度、対象・単位・head、学習範囲/recipe/source pinを含める。再開用checkpointにはoptimizer state、更新位置、sampler schedule/位置、乱数state、選択履歴も含める。推論packageと再開checkpointを混同せず、Python固有のpickleだけを唯一の受渡し形式にしない。最終形式はR0で決める。

### 段階と完了基準

| 工程 | 実施内容 | 完了の判断 |
| --- | --- | --- |
| R0 契約 | banto接続先、Rust計算backend、依存/利用条件/配布、API、tensor/parameter配置、モデル/再開形式を一度選定 | CPUの学習と推論をRustから完結できる見通し、用途別の入出力、比較条件と許容差を実装前に保存。native依存があれば配布要件を明示 |
| R1 推論・前処理 | 既存構造の前処理/normalization/mask/head/forwardを移植し、固定入力と共通重みでPython参照と比較 | shape・単位・mask・欠測・時点境界の一致と、事前固定した数値許容差内の予測一致。ここでは学習移植完了としない |
| R2 学習経路 | loss、gradient、clip、AdamW、parameter更新、保存/再開を移植 | 同じ初期parameter・batch列の1step/短い複数stepで中間値・loss・gradient・更新を照合。連続学習と中断再開を比較し、Pythonを起動せずRustで学習が進む |
| R3 有限の実データ比較 | 対象を固定してRustで学習から選択/推論/評価まで実行し、Python参照と比較 | 元の分割・品質・baseline・選択条件を守り、精度差・時間・メモリ・失敗を報告。既読testを未知検証へ戻さず、移植差を精度調整で隠さない |
| R4 banto接続 | library/CLIからjobとモデルのライフサイクルを扱い、配布/読戻し/取消/再開/旧版への切替えを確認 | bantoの小さい利用例で学習と推論を呼べ、必要な依存と操作を説明できる。対応OSごとの動作・資源を実測し、製品採用は用途条件で別判断 |

Rust backendはこの目的追加では決定しない。R0時に公式の現行仕様で必要演算・自動微分・optimizer・CPU対応・保存/再開・利用条件・配布を確認し、有限の選定とする。ONNX等への書出しやPython学習の呼出しだけを、Rust学習の達成には数えない。Python不要とnative依存なしは同じ条件ではないため、採用依存を明示する。

異言語でseedを同じにしただけでは同じ初期値・batch列とは扱わない。比較用parameterとscheduleを共通の値で渡す。GELU、LayerNorm/標準偏差、softplus、mask、lossのreduction、gradient clip、AdamWのbias correction/eps/weight decay、float精度/配置を記録する。離散的な時点・支持・欠測の判定は一致を要求し、浮動小数の絶対/相対許容差は演算・fixtureの尺度に基づき結果を見る前に固定する。長い学習のbit一致は前提にせず、ずれが選択や評価へ与える影響も示す。

### 現在の研究との順序

M0から前処理、構造、recipe、sampling、stateを明示的に分け、後のRust参照比較へ使える形で保存する。Rust化を意識するために現在のMPT-MAC-20261016-r2の期間・モデル・loss・評価を変更しない。まずPython参照で現在の有限候補の性質を確認し、R0の契約整理を並行できるようにする。油圧・XJTU・CARE・需要の全実験終了を、R0や最初の固定モデルの移植開始条件にはしない。

初回の移植候補は仕様が固定された産業SmallForecasterを起点とし、需要平均モデルの契約は別に保持する。最初の一候補のRust化だけで全用途対応とはしない。現在の実学習停止・2015再評価停止、各900/870秒・2GiBと保存上限は維持し、将来のR2/R3も実行前契約に従う。移植目的の追加を、直ちに実データ学習を開始する指示へ拡張しない。

## 8. 実行・保存・OSの境界

- 実行候補はMacのPython3.14.8/既存Torch、CPUを基本とし、依存lockやWindows nativeを研究の都合で変えない。
- 各seed等の実行unitは親900秒/子870秒、Mac physical footprintとpeak RSS各2GiB。M1は最大3unit（計最大2700秒の親予算）。第3slotは一括採点まで同じ子870秒枠内で行い、第4親unitを追加しない。途中に追加seed/候補を挿入しない。全unitを一つの900秒実行と誤記しない。
- 各artifactのnormal24file/768MiB、total32file/1GiB、single32MiB、failure8file/256MiB。EvidenceStore16MiB/512file、part256KiB、failure2MiB/16file、stdout1MiB/stderr128KiBを維持。原本cacheと新生成物を分ける。
- source/input/state pin、sampling/選択、label前の予測、全stdio/exit、partial/failure/closureを保存し、旧変更・失敗・closed rootsを上書き/削除しない。Macの測定値はWindows private bytesやOS hard capと同一視しない。
- Mac共通経路の研究評価と、Windows固有/native/OS依存の受入は別に報告する。旧クラウドfile一覧やnative gateの全面完成を、小型予測研究の前提へ戻さない。
- 正式holdout、需要2016/2017・予約31–54・販促数量、新モデル取得、課金API、外部研究データ送信、Git push、本番採用は今回の計画に含めない。

**初版/日時r2の後、今回M0では固定対象の数量変換と未学習forward2回を実施。実学習/solver/validation-testモデル予測/性能採点/2015再評価は0。実学習・2015停止、heartbeat PAUSEDを維持する。** 再開の指示は、最初のM0準備だけか、M1の産業実学習までかを分けて扱い、需要やCAREへ自動拡張しない。

## 9. Astraの確認

既存Astra agent `astra_weight_support_audit` が、新取得報告・handoff・既存実装のread-only読取りに基づき批評した。追加agentや実験はない。

採用した指摘は、MetroPTの一件を最初にすること、機構対照と単純baselineへの価値を別判定にすること、3seedの意味と全seed予測の先保存、数量結果を見る前の日付/支持固定、短寿命軸受を落とさないXJTU設計、CAREのlabel独立、需要の停止と条件維持である。Astraは3seed×4,096更新・4選択時点を有限案として許容したが、実行許可や業務適合を認定したものではない。

M0の後、人の明示指示により**M1の有限学習・評価も完了**。次の用途契約は保全・点検のCAREを優先し、R0の契約整理も独立に進められる。新しい欠落なしにM0、同種の人工確認やmetadata監査を反復しない。

本書を保存した後の最終read-only確認でも、Astraは目的整理・有限計画の範囲で重大な矛盾なしと回答した。timestampによる候補窓と、後の数量読取りで確定する共通支持を区別する指摘を採用した。実行許可・性能認定ではない。

今回r2の詳細化でも既存Astraがread-only確認し、13日案の新しいblockingなしと回答。raw変換/窓guard分離、固定分母、日等重み、数量不良後の日付差替え禁止、回顧的な完全日標本の限界、尺度生成後のfinite/正検査を反映し、レビューを終了した。

その後の人の指示で、上位目的にRust学習・推論とbanto統合を追加した。これは目的・工程の追補であり、MPT-MAC-20261016-r2の科学的比較条件/JSON/日時manifestは変更していない。直前までのAstra確認を、このRust追補への独立確認済みとは扱わない。
