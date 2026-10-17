# banto AIの実用性検証とRust学習へ戻る計画

2026-10-16 JST。人の「ポインタ追跡は止めて、これまでの成果を整理し、実用性検証とRustでの学習に戻る計画を見直す」という指示を反映する。[実装計画](banto-ai-rust-implementation-plan-2026-10-16.md)の改訂2として、次工程の順序と調査範囲は本書を優先する。[R0.1](../../examples/configs/rust-small-forecaster-r0-20261016-r0.1.json)の数値許容差・正式な合格条件は維持する。

**OS内部のポインタ・転送先追跡を停止する。R1の残る1点は未達として保存し、追加修正を有限に制限する。並行して、実データを使わないRust学習部品の検証を独立工程に分け、保全・点検支援の実用性へ戻る。** この改訂は計画と保存済み成果の整理であり、学習・推論・再評価を実行した記録ではない。

工程0/1の追補: [固定条件](rust-r2p-synthetic-training-contract-2026-10-16.md)と[lock最小案/Python参照](../results/rust-r2p-lock-and-python-reference-2026-10-16.md)を保存済み。隔離案はpackage/feature不変で通過、107独立照合pass。元lockへ未適用。次は案の適用と固定小型Rust部品実装、Rust学習/保存再開は未実行。

2026-10-17追補2: 人の承認で[R0.2](rust-r0.2-comparison-amendment-2026-10-17.md)を定めた。正式R2の更新比較は|勾配|≥10·epsの要素で判定し、正式R2の入口はR1の最終出力と同一入力局所比較385件とする（中間値は診断として記録）。R1の合格条件と本計画の許容差は変えない。

2026-10-17追補: [整理結果](../results/research-consolidation-2026-10-17.md)。検証済みlock最小案を適用し、停止済みの実装/調査を履歴へ退避した。工程0/1の凍結仕様とPython参照は保持。次は工程2/3の小型Rust実装であり、以前の未適用表記は当時の状態。

## 主目的と継続する境界

主目的はTimesFM3を参考にした自作モデルが、産業設備の保全・点検支援と需要予測・PSIに価値を加えるかの検証である。第一優先は保全・点検支援。AI本体はbanto-aiに置き、Rustで推論だけでなくloss・backward・optimizer・保存再開まで扱う。banto-industrialとdenroku-psi-demoは利用側で、今回編集しない。

実装の数値互換、学習の正しさ、予測性能、保全判断の有用性を別に判定する。移植が成功しても検知性能の十分さは別であり、最終予測が数値条件内でも中間値の未達を消さない。q50やcontext_centerを需要の平均販売数量へ読み替えない。

## 保存済み成果と活用先

| 成果 | 分かったこと | 次に活かす方法 |
| --- | --- | --- |
| [MetroPT M1](../results/metropt-macos-m1-2026-10-16.md) | 3seedのfull/self学習を完了。集約pinballは平均2.105%改善、2/3seed一致。点MAEは3targetとも固定MA15より改善。一部seed・圧力pinball悪化と区間coverage不足も保存 | 自作多信号モデルの探索的価値とRust用state/scheduleを再利用。既読testでseed追加・学習延長・再校正をしない |
| [CARE 5fold](../results/care-macos-learning-evaluation-2026-10-16.md) | 共通支持の事前4条件を通過したが、検知3/12、未検知9、正常誤警報3。native baselineだけが検知したeventもある | 保全の実用性課題を検知・誤警報・先行時間・可用性・asset差で整理。予測誤差の改善だけで採用しない |
| [CARE保存分析](../results/care-saved-diagnostics-rust-r0-2026-10-16.md) | 未検知8件は超過が3連続に届かず、1件は共通支持で超過しない。運用上の原因や故障原因を証明したわけではない | 新しい評価設計の仮説に残す。既読testの閾値・連続回数を合わせ直す材料にしない |
| [Rust推論・全層診断](../results/banto-ai-rust-r1-all-layer-audit-2026-10-16.md) | 固定7caseの最終出力は条件内。同一入力385比較の局所超過0、累積中間値は1点未達 | 元参照・保存入力・中間値・loader・比較器を再利用。全層再生を反復しない |
| context/LN・FMA | 局所bit一致とgraph参加は確認したが全体候補は不採用。backwardは未検証 | 演算の意味と独立部品の参考。現行モデルへの再接続や学習利用を自動採用しない |
| fused linear | 人工検証は通過したが154組が現行とbytes同一で改善0 | 同じ候補を再試行しない。API名やbias初期化だけでは演算順が変わらないという負の結果を保持 |
| SGEMM/転送stub | 小形状の命令再現と64byte stubまで確認。train kernelとprivate once値は未確定 | 補助資料として凍結。解明を実用性・Rust学習の前提にしない |

記載は実行時の保存sourceに対する結果である。現checkoutのmanifestには他作業由来の変更があるため、過去のbuild成功を現在の全feature構成へ広げない。研究用moduleが存在することと、現在のCargo featureから利用可能であることも区別する。

## 残る1点にどこまで対応するか

対象は安定版train-last / blocks.1 / index3450、座標[3,1,3,58]。Python値0.0283811092376709、Rust値0.028383851051330566、絶対差2.7418136596679688e-6、固定限界2.567622184753418e-6。超過分は約1.742e-7で限界比約6.784%。これは限界に対する比率であり、最終予測が6.8%悪いという意味ではない。

全体389,214要素中1点が未達。最終正規化分位点・元単位分位点は各6,048値が条件内。保存した全層分解では当該残差加算の同一入力差は0で、差は上流から伝わっている。この1点への分岐や残差加算だけの補正を正当化しない。context+LN候補で未達だったindex183は別候補の結果であり、現行の3450と混ぜない。

| 判断したいこと | 必要な対応 |
| --- | --- |
| 正式なR1数値互換合格 | 元の全中間値・最終出力条件をすべて満たす。1点の除外、許容差拡大、参照再生成、最終値だけへの条件変更はしない。全bit一致までは要求しない |
| Rust学習部品の正しさ | 人工入力でloss/gradient/clip/AdamW/保存再開を独立検証できる。R1合格とは数えない |
| 全モデルの学習影響 | 現時点では未確認。最終予測passや局所差passだけでgradient・更新・再開の正しさを断定しない |
| 保全・PSIでの有用性 | 業務指標と情報境界で判定する。残1点の解消だけでは業務合格にならない |

追加のR1対応は次の上限にする。まず保存済み証拠を一度整理し、公開Rust演算・数学的仕様から全caseに一律適用できる一般修正の根拠があるか判断する。**現在、新しい採用候補はない。根拠がなければ新実験0でR1を未達保留とする。** OS/vendor内部の追跡を再開しない。

根拠が得られた場合も候補は最大1方式。方式・適用範囲・必要な局所比較・採否条件・保存先を実装前に固定する。既存の同一入力結果を再利用し、新候補の局所確認は一巡、条件通過後の固定7case全体確認は一回だけ。全体未達なら元modelへ復元して終了する。1点だけを直して別の点を発見する反復、型/演算順の組合せ探索、既に不採用の候補の再試行はしない。各unitは既存時間・資源上限内とする。

この上限でR1が解決しなければ、正式R2/R3/製品同等性の認定は保留する。R1の受入境界を変更する必要が生じても、本改訂で暗黙に条件を外さず、数値契約の変更案として別に扱う。

## Rust学習へ戻る実行順

R1未達の間も、人工データだけの学習基盤を独立したR2Pとして準備できるよう順序を改める。これは旧R1→正式R2の合格順を維持した上での準備工程の追加である。**R2Pの通過をR1や正式R2の通過へ読み替えず、実データの学習停止も解除しない。**

| 順序 | 工程 | 入力と成果物 | 完了・停止条件 |
| --- | --- | --- | --- |
| 0 | 現在の実装と契約の整合確認 | model/manifest/lock/source/featureのsnapshot。学習用のparameter登録、host読戻し境界、neutral配置の不足一覧 | 現checkoutを過去の候補sourceと混ぜない。既存変更は保護し、必要な依存/lock修正は別の具体的変更として記録。R1再生はしない |
| 1 | R2P人工fixtureの固定 | 明示した小さな人工parameter・予測・label・尺度・schedule。Python参照と独立した手計算可能ケース、tie/clip/decay/zero-gradient | 実行前に期待値・既存許容差・名前/配置/更新対象・有限回数を固定。実データ、CARE weights/labels、test truthを使わない |
| 2 | R2P学習部品 | normalized pinball loss、autodiff、named gradient、global norm clip、互換AdamW | loss/gradient/1更新parameter/第1第2momentをR0.1の各許容差で検証。非finite・欠落/重複parameter・不正shapeを拒否。失敗は保存して止める |
| 3 | R2P保存再開 | 同じ人工state/scheduleの8更新と、4更新→別process復元→4更新。取消/破損/不完全保存も確認 | 同じRust backendのparameter/moments/counter/output bytes一致。更新位置とscheduleを復元し、旧checkpointを壊さない |
| 4 | R2P全モデルの人工接続 | 固定した人工state/context/labelで学習可能なtensor graphへ接続。推論と学習で演算・配置を共用 | 新しい固定fixtureのloss/全parameter gradientを原許容差で確認。独立の接続確認であり、元R1の未達は残る。hostで計算した参照値をgraphへ注入しない |
| 5 | 正式R2 | R1全条件とR2Pが通った後、固定CARE fold0 train-prefixの1更新・8更新・成熟step4096 import | 実行前fixtureを別途保存し、R0.1の既存条件を適用。validation/校正/test/選択を追加しない。入口未達なら実行しない |
| 6 | R3とbanto接続 | R1/R2完了後の有限移植比較、製品adapter・job・保存/切替 | 元の科学条件と別の実行仕様を固定。共通coreとWindows固有試験を分離し、製品採用は別判定 |

R2Pは数学・学習エンジンの成立を確かめる工程で、成績改善や実データの反復学習を目的にしない。最初の次工程は0と1の仕様固定であり、いきなり8更新や全モデル実装へ飛ばない。学習可能な型・parameter登録・optimizer対応が現推論APIにない場合は最小の分離設計を先に示す。現在のSmallForecasterを学習済み機能として扱わない。

## 許容差と保存再開契約

数値条件はR0.1を参照し変更しない。normalized activationはatol2e-6/rtol2e-5、normalized lossは1e-6/2e-5、gradientは2e-5/2e-4にglobal相対L2条件も併用する。1更新parameterは1e-6/1e-5、momentsは第1が1e-7/2e-4、第2が1e-10/3e-4。8更新parameter/loss、元単位quantile、zero-reference normの特則、厳密なmask/ID/時点/順序・同backend再開のbytes一致も元契約を継承する。

AdamWのlr/β/eps/decay、全parameterへの適用、clip norm1と分母の1e-6、foreach/fused条件、weight/gradient/momentの配置を固定する。PythonとRustの同seedだけを状態一致の根拠にせず、実scheduleと初期stateを保存する。丸めの差が警報閾値をまたいだ場合もepsilonを足して隠さない。

## 実用性検証で次に答える問い

保全では「予定した点検に役立つ先行時間を確保しながら、誤警報と発行不可期間をどこまで減らせるか」を主な問いに戻す。既存CAREの3/12とnative可用性差を基準資料として残す。業務上の必要先行時間・許容誤警報・対象設備の要件は、次の実用性契約で具体化する。未定のまま製品合格にはしないが、Rust部品の実装準備を止める条件にはしない。

新候補を評価する前に、既読CARE/MetroPTを開発資料として扱うこと、開発・選択・最終確認の時点/asset境界、quality/availability、支持不足時の扱い、比較baseline、event集計と正常時の警報指標を固定する。今あるtestを再び未知holdoutと呼ばず、新データ取得や未使用期間の開封はこの改訂に含めない。

油圧は制御cycle内予測と状態診断、XJTUはRMS短期予測とRULを分ける既存計画を維持し、全データでの再実験をRust学習の前提にしない。需要は平均数量headと同休業仮定mean28の比較を維持。調整2014年以前、四季平均の過小量/過大量非増加と既存MSE条件、観測のみ/欠測0仮定の分離、2015再評価停止を維持する。PSIは在庫・入荷・lead time・費用条件を固定した別の業務評価とする。

## 停止する調査と保護

SGEMM/once/TLS/PAC/転送stub/pointer slotの追跡、vendor関数の直接呼出し、追加のlive code/data読取りを今後の既定工程から外す。保存した8byte slot条件は実行しない。関連する旧JSON・source・raw bytes・failed rootsは履歴として保持し、statusを書き換えない。再開にはこの停止を明示的に見直す人の指示が必要で、通常の「進めて」で復活させない。

親900秒/子870秒、physical footprint・peak RSS各2GiB、cache+target1.5GiB/jobs1、元artifact24files/768MiB/単一32MiB、失敗32files/1GiB、EvidenceStore16MiB/512files/part256KiBと失敗reserve、stdout1MiB/stderr128KiBを維持する。旧変更・失敗・closed rootsを上書き/削除せず、新規rootと文書前後の保存を使う。共通Mac coreとWindows native/OS固有機能は分ける。heartbeat PAUSED、Git push・下流編集・製品採用は行わない。
