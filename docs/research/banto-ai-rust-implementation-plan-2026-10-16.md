# banto AIのRustクレート実装と製品利用の計画

状態: 2026-10-17の整理でmainのWindows修正を取り込み、検証済みlock最小案を適用。人工Python参照は保存済み、Rust人工学習/保存再開は未実装。停止済み拡張と単発調査は履歴へ退避。[整理結果](../results/research-consolidation-2026-10-17.md)。R1は1点未達/正式R2停止、許容差不変。
計画ID: BANTO-AI-RUST-PLAN-20261016-v2。旧v1全文は今回の文書前後証跡へ保存。

**今後の作業はこの計画と[R0の数値契約](rust-small-forecaster-r0-2026-10-16.md)に沿って進める。** 各工程の開始前に対象・固定入力・成果物・合格条件・資源上限を保存し、変更理由を記録する。主目的はTimesFM3を参考にした自作モデルの産業・需要での実用性検証であり、保全・点検支援を第一優先にする。Rustで学習から推論まで動かし、bantoから利用できる状態を目指す。

## 改訂2の優先事項

[実用性とRust学習へ戻る計画](banto-ai-practical-training-return-plan-2026-10-16.md)を現在の作業順として優先する。OSの初期化・転送stub・pointer追跡は停止し、保存済み8byte slot条件は実行しない。原R0.1の許容差・正式R1条件は変えない。

R1未達の間は、人工入力/label/parameterだけのloss・gradient・clip・AdamW・保存再開を独立したR2Pとして準備できる。正式R2や実データ学習への移行とは区別する。棚卸しと人工fixture仕様固定は完了し、隔離lock最小案とPython人工参照の生成も完了した。次は固定小型Rust学習部品の実装。R1の追加候補は一般的根拠がある場合だけ最大1方式、局所一巡/通過後の全7case一回に限る。根拠がなければ実験0で未達保留とする。

## 配置と責務

AI本体の実装は **tyaro/banto-ai** に置く。産業側は **tyaro/banto-industrial**、需要・PSI側は既存の **denroku-psi-demo** を接続例とする。各利用側がbanto-aiへ依存し、共通AI側はアプリへ逆依存しない。現時点で両アプリから共通crateを利用済みという意味ではない。

| 配置 | 担当 |
| --- | --- |
| banto-aiのRustクレート | 入力検査・前処理、モデル、推論、loss/backward、AdamW、学習進捗・取消チェック、モデルとoptimizerの保存・再開 |
| banto-aiの参照CLIと検証用コード | 共通APIの実行例、Python参照との比較、固定データでの評価。研究データはクレートへ同梱しない |
| banto-industrialのadapter | タグ・raw履歴の取得、製品型から共通入力への変換、品質・単位・時点の対応 |
| banto-industrialのアプリ | 学習jobの起動・監視・取消、UI、モデルの選択・切替・rollback、点検担当への結果提示 |

共通AIクレートは製品DTO、banto-tagclient/tsquery、Tauri、PLC・Windowsサービスへ依存させない。ジョブを別プロセスで動かすか専用workerにするかは、製品接続時に収集周期・応答性を測定して決める。どちらでも学習本体は同じAIクレートを呼ぶ。

最初は1クレートで開始する。推論用と学習用の別クレートへの分割は、実際に依存量や配布サイズが問題になってから判断する。

~~~text
banto-ai/
  Cargo.toml
  Cargo.lock
  crates/banto-ai/
    Cargo.toml
    src/
      lib.rs
      input.rs
      preprocess.rs
      model/
      train/
      checkpoint/
      error.rs
    examples/
      predict.rs
      train.rs
    tests/
  models/mini-transformer/       Python参照を維持
  tools/                        参照出力生成と独立比較
  docs/research/                契約と計画
  docs/results/                 実行結果
~~~

crates/banto-aiの推論/loader/CLIは実装され、過去のCPU build結果を保存済み。train moduleや完全な学習checkpointは未実装。現manifestとの整合は隔離lock案で確認済みだが元lockへ2026-10-17に適用済みで、CLIの外部公開や追加crate、ネットワークAPIは含めない。

## 需要とPSIの既存実装を接続例に加える（2026-10-16）

[denroku-psi-demoの現状と引継ぎ](denroku-psi-ai-integration-2026-10-16.md)を確認した。現状はPython LightGBM学習→Rust推論/照合→静的JSON→画面/PSIで、Python不要の再学習は公式C APIを使う別の未実装計画がある。共通AIの配置はbanto-ai、利用側は産業のbanto-industrialと需要・PSIアプリ。各利用側→banto-aiの依存方向を守る。

R1/R2は自作SmallForecasterを先行する。既存LightGBMの特徴量・木推論・Python不要学習を同一engineへ押し込まず、共通化はmodel版/来歴/数量の意味/進捗・保存等の境界から行う。需要26週の出荷点予測と産業32stepの分位点を区別し、PSI/受注採用判断は利用側へ残す。R0.1の数値契約は不変。需要側のfixture利用・LightGBM移行・平均モデル比較は別工程で仕様と範囲を固定する。

## 現在ある成果を使う

| 保存済み成果 | 次工程での用途 |
| --- | --- |
| SmallForecasterとPython学習コード | 演算・loss・optimizerの参照。産業q50を需要平均と読み替えない |
| CAREのneutral model・named tensor配置・AdamW状態 | Rustの読込、weight/gradient/moment配置と成熟optimizer状態の比較 |
| CARE fold0の先頭・末尾train batchとprofile | 最初のforward比較。番号最小foldを採用し成績で選び直さない |
| CAREの全初期state・sampler schedule・選択checkpoint | 後の有限学習比較で同じ初期値と入力列を使う |
| 全5foldの固定予測・閾値・警報・評価 | Rust化による数値・可用性・判定差を検出する参照 |
| MetroPT M1の3seed full/selfとbaseline比較 | 産業予測の既存結果を維持。初回Rust成立のために全実験を再実行しない |
| banto-industrialのsource監査 | 外部名binding、品質、時刻、raw履歴と画面履歴の違いをadapter設計に反映 |

CAREは検知3/12、未検知9件、正常false3という限界も固定する。移植の成功と保全性能の十分さは別に判定する。既読testに合わせた閾値・連続回数・信号・学習量の再調整は行わない。

## 工程と完了条件

| 順序 | 工程 | 主な成果物 | 完了条件 |
| --- | --- | --- | --- |
| 1 | R1a クレートとCPU build | Cargo構成、lock、feature/依存license一覧、子孫を含む資源記録 | banto-ai内で単独buildでき、製品repoへの逆依存がない |
| 2 | R1b 前処理と推論 | model実装、neutral loader、予測API、Python比較結果 | 固定2batchと必要な人工ケースがR0許容差内、時点・shape・mask・信号順が一致 |
| 3a | R2P 人工学習基盤の独立準備 | 人工fixture、loss/gradient/clip/AdamW、8対4+復元+4 | 元の数値条件で部品/再開を検証。R1合格や実データ学習とは数えない |
| 3b | R2 学習と保存再開 | loss/gradient/clip/AdamW、checkpoint、短いtrain例 | 1更新と8更新が数値条件内、連続8対4+復元+4が同一Rust環境でbytes一致 |
| 4 | R3 CAREの有限移植比較 | 保存モデル推論比較、全5fold有限学習の結果 | 固定条件・全予測freeze後採点を守り、精度・警報・支持・資源の差と失敗を説明できる |
| 5 | R4a 産業/需要の製品adapter | 共通型との変換、学習job管理、モデル利用例 | banto-industrialからAIクレートを呼び、品質/時刻/取消/切替の契約を満たす |
| 6 | R4b 対象OSと配布 | toolchain別検証、license/配布物、運用手順 | 共通coreとWindows固有機能を別に検証し、Pythonなしで学習・再開・推論できる |
| 7 | 業務利用の判断 | 用途別の受入条件、評価報告、採否 | 点検の先行時間・誤警報の許容値と対象設備に照らし、実用性を判定する |

次の着手はR2Pの現状整理と人工fixture仕様固定。正式R2は原R1とR2Pの完了後に限る。R3/R4は入口条件と実行仕様を整えてから進め、計画の保存だけを実データ再学習や製品変更の開始記録にしない。

### R1aで実行環境を確立する

既存のnative Rust1.95.0を初回候補に、Burn =0.22.0 / Flex CPU / autodiffを試す。[R0設定r0.1](../../examples/configs/rust-small-forecaster-r0-20261016-r0.1.json)の数値仕様を継承する。backend選定をやり直す工程にはしない。

最初にcompiler/linkerの子孫を含む監視を用意し、jobs1で依存解決・buildを有限単位で実行する。Cargo.lock、実際のfeature graph、toolchain、依存licenseを保存する。MacのIntel rustup shimは使用せず、グローバル設定やOSライセンス同意を自動変更しない。製品側のpin1.98.1との互換はR4で確認し、AIクレートの配置やtoolchainを製品repoと混同しない。

build不能・上限超過・必須演算不足なら、その理由と保存物を報告して工程を止める。原因が分からないままbackendを追加したり、予算を拡大したりしない。

### R1bで前処理と推論を移す

入力を有限float32 [B,3,128]、出力を元単位の順序付き分位点 [B,3,32,3] とする。profile・信号順・時刻・利用可能時刻を明示し、学習target [B,3,32] は別に渡す。製品のタグ型をmodel APIに持ち込まない。

neutral tensorを検査して読み込み、context正規化、patch、attention、LayerNorm、GELU、headの順に比較する。まず保存済みfold0 modelと先頭・末尾train batchを使い、差が出た最初の演算を特定する。中間値の記録はこの診断に必要な範囲に限る。

人工ケースは、定数系列・観測0・scale floorの下/境界/上・非有限/shape不正・mask・分位点順序を対象とする。時間と欠測の境界はRustへ移す部分を確認し、既存Python側の試験群を無目的に再実行しない。欠測の0埋めやCARE statusの入力利用は追加しない。

R0で固定した全条件に達した場合だけR1を合格とする。追加修正は改訂2の最大1方式/一巡条件を守り、根拠がなければ未達保留。OS内部追跡や点ごとの調整はしない。高速化・GPU・量子化・モデル拡張は後回しにする。

### R2で学習と再開を移す

下記は正式R2の条件であり、原R1通過前の実データ学習は停止したまま。先行するR2Pは人工state/label/scheduleだけで同じ学習部品と再開を検証し、実行前に別fixtureを固定する。R2Pの実行も今回の計画改訂では開始していない。

context-normalized pinball loss、backward、全parameterのglobal norm clip、互換AdamWを実装する。weightと同じ規則でgradient/momentsを配置し、bias/LayerNormを含む更新対象をPythonに合わせる。

学習前に次の有限fixtureを保存する。

1. 保存weightからfresh optimizerを作り、同一の最初のtrain batchで1更新を比較する。
2. 同じ初期weight・fresh optimizer・固定8 train batchで8更新を比較する。
3. 同一Rust backendで連続8更新と4更新後に保存・別プロセス復元・残4更新を比較する。
4. 保存step4096/momentsを使った別の1更新で、成熟optimizer状態のimportを比較する。
5. gradient clip、decay、pinball/floorのtie、破損・不完全checkpointの拒否を人工ケースで確認する。

checkpointは一時出力から検証後に確定し、不完全な保存物で既存の有効モデルを置き換えない。取消は更新境界で受け付け、最後に完了したstep/schedule位置・checkpoint・取消理由を保存する。実際に保存処理が影響するケースで故障注入を行い、単なるsave/load成功だけで再開を認定しない。

ここではvalidation選択・校正・CARE test予測を追加しない。8更新の一致と保存再開が通ればR2を終了する。需要の人工rawP境界系列を再開する工程にはしない。

### R3でCAREの移植差を確認する

入口はR1/R2完了と、別の有限実行仕様の保存である。最初に保存済み5fold modelから元の固定入力へ推論し、予測・支持・警報の再現を確認する。その後、固定初期weightと実sampler列を使い、元と同じ5fold/各4096更新/4選択点の学習比較を行う。初期値は保存初期stateを中立形式へ変換して使い、異言語で同seedを指定するだけにしない。

各foldのstate/選択/閾値/予測/警報を保存し、全foldを閉じてからevaluatorへtruthを渡す。学習・選択・校正へevent truthを入れない。baselineは同じ固定profile・支持で比較し、native支持も別に報告する。

保存モデル推論の許容差はR0を継承する。4096更新後の累積差は8更新用の許容差を自動流用せず、長期比較の数値条件を実行前に別途固定する。RustとPythonの差が出ても、閾値・選択点・学習量で成績を合わせ直さない。検知率・正常誤警報/警報時間・先行時間proxy・asset別・可用性・資源を報告する。

これは既読CAREの移植確認であり未知評価には戻さない。全5foldを完了したら比較を閉じ、追加seed/延長/候補探索を自動的に足さない。MetroPT・油圧・XJTUの全再実験をRust利用の前提にしない。

### R4で利用側と接続する

利用側はversion/tag/commitを固定してbanto-ai crateを利用する。産業側はbanto-industrial、需要・PSI側はdenroku-psi-demoの既存Python学習/Rust推論経路を接続例とする。需要側では現行予測JSONとの互換を先に固定し、LightGBMから自作モデルへの置換やPython不要学習は別の有限工程として扱う。外部名をアプリのbinding_keyへ対応させ、値・quality・source時刻・観測したavailability・unit/校正・run/catalog世代を共通入力へ変換する。

画面用min/max履歴は学習値に使わない。raw履歴に残っていない品質・source時点・availabilityは「正常」と補わず、明示された履歴入力契約かsidecarが整うまで実学習に採用しない。on-change snapshotを周期pollして同じ値を新観測にすることも避ける。これらの未決点はcoreのR1/R2を止めず、製品の実入力接続を止める条件とする。

専用worker/sidecarから学習進捗を取得し、取消・再開・失敗をUIへ返す。推論packageと再開checkpointを区別し、モデルの検証・明示切替・rollbackを確認する。学習負荷が収集周期やUI応答へ及ぼす影響も測定する。保全出力は点検支援として提示し、PLC制御書込へ接続しない。

Mac共通coreの検証と、Windowsサービス・DPAPI/keyring・昇格・製品時刻処理などのOS依存検証は結果を分ける。Macでの成立だけでWindows製品利用を認定しない。配布時はコード・依存・CAREデータ/modelの来歴と利用条件を別々に確認する。

## 実用性の評価を並行して維持する

保全・点検の第一候補はCAREである。現在の未検知9件やasset差を今後の設計仮説として残すが、既読testで調整しない。次の新モデル候補を試す場合は、開発/選択と最終確認の分離、必要先行時間、許容誤警報回数、対象設備の支持条件を先に決める。業務値が未定でも共通coreの移植は進められるが、業務合格は保留する。

MetroPTは圧力・温度・電流の予測という既存の基礎結果を維持する。油圧とXJTUは、保全判断の問いと評価単位を先に定め、予測誤差の小ささを故障予兆の有効性へ読み替えない。新データ取得や未使用期間の開封は本計画の実行に含めない。

需要/PSIも上位目的に残す。産業の分位点出力と将来販売数量の平均を別のhead・用途契約として扱う。需要2015再評価は停止、調整は2014以前だけ、同じ休業仮定のmean28比較、四季平均の過小量/過大量非増加、観測のみと欠測0仮定の評価分離を維持する。PSIの判断は在庫・入荷・lead time・費用条件をそろえた別評価とする。

## 将来の古典ML比較候補

[linfaとsmartcoreの候補メモとAstraレビュー](rust-classical-ml-linfa-smartcore-note-2026-10-16.md)を後日の研究候補として残す。共通する回帰を一種類だけ比較し、保全用の正常状態モデルを優先する。Rustでの学習・前処理込み保存・別プロセス推論と資源を確認し、用途別候補も絞る。現在のR1/R2の工程順・数値条件は維持し、依存追加や古典ML実験は別の有限仕様を固定してから行う。

## 資源と保存

各実行単位は親900秒/子870秒、Mac physical footprintとpeak RSS各2GiB。Cargoはjobs1とし、compiler/linker等の子孫も追跡する。測定方法・sampling間隔・短命processの捕捉限界を保存し、main PIDだけでプロセス群全体の上限を満たすと断定しない。

normal artifactは24file/768MiB、単一32MiB、失敗込み32file/1GiB。EvidenceStoreは16MiB/512file/part256KiB、失敗reserve2MiB/16file、stdout1MiB/stderr128KiBを維持する。全command/source/stdio/exit/state/資源/closureを保存し、旧変更・失敗・closed rootを上書き/削除しない。必要なcheckpoint分割は内容・再結合検証を契約化し、保存枠を超えるために既存成果を消さない。

上限超過、入力/来歴不一致、時点漏洩、数値不一致、保存不完全は失敗として残す。原因を直せる場合は変更点を明示したfresh rootだけで再開する。同じ条件の再試行を繰り返さない。新しい目的や修正理由がなければ、その工程を終了または停止する。

## 次に着手する内容

[固定R2P条件](rust-r2p-synthetic-training-contract-2026-10-16.md)に沿い、[隔離lock案と人工Python参照](../results/rust-r2p-lock-and-python-reference-2026-10-16.md)を保存済み。元lockのgemm直接edge1行削除は適用済み。次に、feature-gated小型loss/gradient/clip/互換AdamW/checkpointを実装する。固定fixtureから開始し、閉鎖済みPython参照を再生成しない。

その後の有限Rust受入は連続8対4+復元4、人工AdamW6、拒否6/8、writer途中停止3。元R0.1の許容差を守り、不一致を保存して依存工程を止める。今回Rust実装・build・test・保存再開は未実行。原R1未達/正式R2実データ停止、ポインタ追跡停止、CARE/需要の停止、各資源枠とheartbeat PAUSEDを維持する。
