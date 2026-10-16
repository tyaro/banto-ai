# Rust SmallForecaster R0 — 学習・推論とbanto-industrial接続の契約

[現在の実装計画](banto-ai-rust-implementation-plan-2026-10-16.md)を工程順・成果物・終了条件の入口とする。本R0はモデル/数値/配置の契約として継承する。

状態: R1a/既存3テストpass。全55箇所×7caseの診断完了、局所超過0・上流累積1点未達でR1未合格。モデル変更/候補探索0、R2未着手。[全層診断結果](../results/banto-ai-rust-r1-all-layer-audit-2026-10-16.md)。2026-10-16 JST。
[上位計画](timesfm-inspired-practical-evaluation-plan-2026-10-16.md)に沿う。[機械設定r0.1](../../examples/configs/rust-small-forecaster-r0-20261016-r0.1.json)を次工程の入口とする。

## 実装の所属と依存方向 — 人の訂正（2026-10-16）

AI本体のRustクレートは tyaro/banto-ai 側に置き、tyaro/banto-industrial は利用・接続先とする。前回の「移植先」は接続先の意味であり、AI実装の配置先に読み替えない。

- **banto-ai**: 前処理、モデル、学習/loss/backward/AdamW、推論、モデル・optimizer checkpointと再開、共通Rust API/参照CLIを持つ。R1で作成するクレートの配置案はこのrepositoryの `crates/banto-ai`。当面一つのクレート内でmoduleを分け、必要が生じた段階で分割する。今回はクレート未作成。
- **banto-industrial**: タグ・履歴の取得と型変換、quality/time/unit policyの適用、学習jobのhost、UI、モデルの利用/切替を持つ。AI本体の実装をここへ移さない。
- **依存方向**: banto-industrial → banto-ai。利用時のversion/tag/commitを固定し、共通AI crateは製品DTO、banto-tagclient/tsquery、Tauri/PLC/Windows機能へ依存させない。実機固有の対応はadapterで処理する。

[現行機械設定r0.1](../../examples/configs/rust-small-forecaster-r0-20261016-r0.1.json)。旧r0 JSONと閉鎖artifactは不変の履歴として残す。数値・モデル・optimizer・参照pin・許容差・評価条件は変更しない。banto-industrial 1.98.1の確認は下流統合の条件であり、AIクレートを同repository内に置く理由ではない。

## 目的と今回の境界

TimesFM3を参考にした自作モデルの産業・需要での実用性を主目的とし、保全・点検支援を第一優先にする。Rustではforwardだけでなく学習/backward/optimizer/保存再開まで実装し、bantoから扱えるlibrary/CLIとjob・model管理へつなぐ。Python版は参照実装に残す。

人が**利用・接続先として banto-industrial** を指定した。AI本体はbanto-ai側のRustクレートとする（下記訂正を優先）。確認した実体は[tyaro/banto-industrial](https://github.com/tyaro/banto-industrial)、main commit `93d99efa06e8eda8c623567c5d117409fb2a3c8b`。ソース23ファイルを読取り、tree内Git blob SHAと照合した。Mac内の既存checkoutは見つかっていない。clone/外部repo編集/pushは行っていない。先行auditの未確認候補ScadaProjectは人の回答で**接続先から除外**し、その型や品質方針を本契約に流用しない。旧audit自体は履歴として保つ。

今回は既存CARE予測の事後分析、公式backend仕様・対象repositoryの読取りと契約固定まで。モデル実行・学習・依存導入・Cargo buildは0。既読CARE testの再調整は行わない。

## Backendと配布の有限選定

最初のR1候補を **Burn =0.22.0 / Flex CPU / first-order autodiff** に固定する。候補を増やしてbackend選定だけを繰り返さない。

| 候補 | 公式資料で確認した性質 | 初回の判断 |
| --- | --- | --- |
| Burn 0.22.0 | FlexはRust CPU backend、reverse-mode autodiff、optimizer record保存/読込。MSRV1.95、MIT OR Apache-2.0 | 最初の実装候補 |
| Candle 0.11 | Rust CPUと学習経路、任意のMKL/Accelerate | 有限比較の代替候補。学習非対応とはしない |
| tch 0.26 | Rust wrapper、README指定LibTorch2.13.0、native C++依存 | 今回のPython Torch2.14.0との互換は仮定しない。初回候補にはしない |

[Burn現行ドキュメント](https://burn.dev/docs/burn/)、[v0.22.0 crate仕様/MSRV](https://github.com/tracel-ai/burn/blob/v0.22.0/crates/burn/Cargo.toml)、[Flex仕様](https://github.com/tracel-ai/burn/blob/v0.22.0/crates/burn-flex/Cargo.toml)、[Autodiff](https://burn.dev/docs/burn/backend/autodiff/index.html)、[optimizer保存](https://burn.dev/docs/burn/optim/struct.ModuleOptimizer.html)、[Candle公式](https://github.com/huggingface/candle)、[tch公式](https://github.com/LaurentMazare/tch-rs)。取得本文/URL/exit/内容SHAを `artifacts/rust-r0-source-audit-20261016` に保存した。古いNdArray tutorialを現在の推奨経路として採用しない。

予定依存は `burn = { version = "=0.22.0", default-features = false, features = ["std", "optim", "flex"] }`。CPUを明示し、初回比較はworker thread1。外側のdefault-features=falseだけで、transitiveなSIMD/rayon等も無効と断定しない。R1冒頭で実際のfeature graph、CPU kernel、Cargo.lock、全依存license/配布条件を保存する。未compileなので利用可能性/速度/配布成功は未認定。

Macの標準rustup shimはIntelバイナリで起動できない。既存のnative `~/.rustup/toolchains/stable-aarch64-apple-darwin/bin/{cargo,rustc}` は1.95.0として直接起動できる。グローバルPATH/rustupは変更していない。研究用孤立crateの初回確認はこのnative toolchainを候補とする。一方、**banto-industrialの現行pinは1.98.1**。統合時に1.95へ下げず、R4では対象pin上で別にcompile/検証する。Macに1.98.1を導入済みとはしない。

## Python参照とデータ契約

最初のモデルはSmallForecaster full、109,024 parameter、V3/C128/H32/P32/D64/L2、4head、FF128、dropout0、q=[0.1,0.5,0.9]。source SHAと参照ファイルのbytes/SHAは機械設定に固定済み。

入力はCPU float32有限 `[B,3,128]`、B=1..8。学習target `[B,3,32]` は別引数で、推論要求に未来値/イベントlabelを入れない。時刻・signal順・単位・availability・qualityを前処理契約として保存する。0は有効な数量、missing/nonfiniteは0へ置換しない。CAREの10分規則やstatusのroleは元のr1に従い、実運用の周期へ無条件に流用しない。

context内だけのmeanとpopulation std（correction=0）、trainで固定したcontext floorを使う。LayerNorm eps1e-5、GELUはerf版、Softplus beta1/threshold20、temporal causal maskの除外logitは負の無限大。p50±Softplusから順序付きquantileを作り元単位へ戻す。[公式Tensor演算](https://burn.dev/docs/burn/tensor/struct.Tensor.html)の存在確認だけでは数値一致とせず、R1で中間値を比較する。

Pythonの `Forecast.mean` はcontext中心値であり、将来需要の期待値ではない。共通出力では `context_center` と明示する。現在のq50を需要数量の平均予測と呼ばず、需要/PSIのmean headや14日総量は別契約に保つ。

最初の参照は性能を見て選ばず**番号最小のfold0**。保存済み選択step4096のneutral model/layout、trainの先頭・末尾2batch（計30,720B）、fold0のprofile/scheduleを使用する。初回R1はこのtrain入力と人工入力の数値移植確認に限定する。CARE testのforward/採点は追加しない。

## Tensor・モデルと学習checkpoint

中立package v1はUTF-8 JSON manifestとlittle-endian row-major tensor binary、SHA256 closure。manifestの必須項目は機械設定に列挙する。dtype/shape/name/offset/length/payload hashを持ち、checked arithmeticで範囲・重複・overlap・未掲載tensorを拒否する。読込の失敗で部分modelを活性化しない。

Linearの共通配置はPyTorchの `[out,in]`。backendが `[in,out]` ならweightだけでなく対応gradient/AdamW momentsも同じ規則で転置する。全named parameterと永続buffer `scale_floor/position/time_mask` を保存し、非永続series_maskはfull/self-onlyの明示構造から復元する。名前や登録順を推測してoptimizer stateを対応させない。

推論packageには構造・head・信号順・単位/校正・前処理/profile・clock/quality policy・recipe/学習範囲・source・license/provenanceを含める。再開checkpointにはさらにnamed AdamW moments/整数step、実sampler scheduleと次位置、RNG方式/version/state、選択履歴・best stateを含める。既存neutral内float32のstepは有限の整数であることを検査して整数へ移す。Python pickleやBurn内部recordだけを唯一の共通形式にしない。

Python RNG bytesをRustで同seed再現できるとはしない。dropout0の初回は保存済み実scheduleを再生し、更新中の追加乱数drawはしない。将来stochastic演算を加えるときはRust側RNG契約も必要。CARE参照packageはreference_onlyで、匿名sensorの校正・単位を実機へ対応済みとしない。Burnとbantoのコードlicense、CARE CC BY-SAのデータ来歴、学習modelの配布条件を一律に認定しない。

## 学習・数値比較の受入条件

AdamWはlr3e-4、β=(0.9,0.999)、eps1e-8、decay0.01、AMSGrad/cautious decay=false。bias/LayerNormも含む全parameterへ同じdecay。gradientは全parameterのglobal L2でclip1、係数min(1,1/(norm+1e-6))。元Torchはforeach/fused=false。bias correction、decoupled decay、epsilonの位置まで照合する。Burnの[AdamW既定値](https://burn.dev/docs/burn/optim/struct.AdamWConfig.html)は参照と異なるため、既定任せにせず明示指定し、不一致なら同じtensor/autodiff上の互換optimizerを実装する。

実装結果を見る前に次の許容差を固定する。通常は各要素 `abs(Rust-ref) <= atol+rtol*abs(ref)`。

| 比較対象 | atol / rtol等 |
| --- | --- |
| 正規化入力・中間activation | 2e-6 / 2e-5 |
| 元単位quantile | 1e-4×train T32 + 2e-5×abs(ref_q-context_center) |
| normalized loss | 1e-6 / 2e-5 |
| gradient | 2e-5 / 2e-4、かつglobal相対L2<=2e-4（参照norm0ならcandidate norm<=2e-5） |
| 1更新parameter | 1e-6 / 1e-5 |
| 第1/第2moment | 1e-7 / 2e-4、1e-10 / 3e-4 |
| 8更新parameter / loss | 3e-6 / 3e-4、1e-5 / 5e-4 |
| 同一Rust backendの連続8更新と4+復元+4 | parameter/moments/counter/outputのbytes一致 |

shape/mask/時点/支持/ID/順序/保存roundtripは厳密一致。maximum/floor/pinballのtieでのsubgradientもR2の人工fixtureで比較する。差が出たときは原因を記録して停止し、test結果を根拠に許容差を緩めない。同一保存score列に対する3連続/解除/gap/file resetのalarm stateは厳密一致。数値差が閾値をまたいだら判定差を報告し、epsilon追加で隠さない。

R2の短い8更新は移植fixtureとして先に入力/初期state/stepを固定する。初回は保存weight＋fresh optimizer step0、同じ先頭8 train batchで連続8対4+4を比較する。別の1更新fixtureで保存step4096/momentsのimportを確認する。これを元CARE実験の継続学習や再評価と呼ばず、validation/選択/校正/testを追加しない。

## banto-industrialへの接続案

確認した[実型types.rs](https://github.com/tyaro/banto-industrial/blob/93d99efa06e8eda8c623567c5d117409fb2a3c8b/crates/banto-tagclient/src/types.rs)・[binding.rs](https://github.com/tyaro/banto-industrial/blob/93d99efa06e8eda8c623567c5d117409fb2a3c8b/crates/banto-tagclient/src/binding.rs)を正とする。設計文書の概念TagValueSnapshotを実装済みDTOと取り違えない。

| 境界 | 現行契約と接続条件 |
| --- | --- |
| identity | BindingRequest(binding_key,external_name) → catalog外部名。StableTagIdは監査情報でありbinding keyではない。renameはunresolved。同名再作成も単位/校正/文脈を再検査 |
| live値 | ValueEntry(tag,v:Option<f64>,q,t,value_source)とValuesSnapshot(revision,t,run_id,collection_mode,values)。Goodで有限Some(v)を必要条件にし、Bad/Stale/Unknown/null/未解決をmissingとして保持 |
| source | 初期の実運用adapterはConfigured/Realに限定する案。computed/db/internal/simulation/derived_simulationは明示された別のmodel/data policyを要する。live実装はまだない |
| 時点 | 各値のsource tとadapterが観測するavailable_atを分け、発行前に利用可能な値だけ使う。snapshot全体のtを全tagのsource tへコピーしない |
| watch | 最新状態を同周期にpollしても新しい観測にはならない。on-changeの無通信を欠測/据置へ自動変換せず、周期・freshness・集約契約を別途固定 |
| 再接続/変更 | run_id、名前、unit/scaling/config変更で系列境界を分け、contextをreset。過去/新世代を無断連結しない |
| raw履歴 | TsQuery::read_rangeのRawRow(ptime_ms,Vec<Option<f64>>)を数量取得候補にする。NULL/設定不在を0にせず、metadataをfileごとに保持 |
| 画面用履歴 | CollectHistory/DecimatedRangeはmin/max envelope。中点や平均を作って学習数量へ流用しない |
| 履歴の不足情報 | rawのptime/valueだけではsource t、受信availability、per-value品質・値源を復元できない。既存rawを正常品質と偽装せず、別の明示入力契約かquality/availability sidecarが整うまで実学習への採用を止める |

[RawRange型](https://github.com/tyaro/banto-industrial/blob/93d99efa06e8eda8c623567c5d117409fb2a3c8b/crates/banto-tsquery/src/types.rs)、[画面履歴](https://github.com/tyaro/banto-industrial/blob/93d99efa06e8eda8c623567c5d117409fb2a3c8b/apps/chronogazer/core/src/collect/history.rs)、[tstore schema](https://github.com/tyaro/banto-industrial/blob/93d99efa06e8eda8c623567c5d117409fb2a3c8b/crates/banto-tstore/src/schema.rs)を保存。CAREの匿名file-local clockと製品UTC epoch-msも明示的に区別する。tstore clockにWindows用途のOS固有処理があり、Mac共通coreの成立を製品Windows機能の受入へ広げない。

共通APIはpackage検査/読込/予測、train job開始/進捗/取消/再開、checkpoint保存/読込、model一覧/登録/明示activation/rollback。型/API名は提案であり、既存REST routeやworkspace crateを追加済みとはしない。長時間学習はbounded worker/sidecarで収集・監視/PLC周期やUI threadから独立させる。出力は点検の判断材料とし、PLCへの制御書込には接続しない。

## 次の順序と停止条件

1. **R1**: banto-ai内の `crates/banto-ai` を最初は単独buildし、exact dependencyをlock、license/feature/CPU/toolchainを確認しcompile。固定fold0 weightと2 train batch、人工constant/zero/floor/nonfinite/mask/quantile入力でforwardと中間値を照合。
2. **R2**: 別の実行前fixture契約を保存してloss/gradient/clip/AdamW・8更新/保存再開と成熟moment importを確認。
3. **R3**: R1/R2通過後に別の有限実データ移植比較を固定。元の科学条件を保ち、既読testであることを明記。
4. **R4**: banto-industrialのpin1.98.1でadapter/CLI/job/model管理を接続し、取消/原子的checkpoint/品質・時刻・単位変更を確認。Windows native/OS固有試験を分ける。

R1以降の実行前に親900秒/子870秒、physical footprint/peak RSS各2GiB、既存artifact/EvidenceStore/stdio上限を維持する。Cargoはjobs1とし、**compiler/linker等の子孫プロセスも計測**する。現在のPython用main PID観測だけをCargo全体の2GiB保証にしない。超過・compile/link失敗・数値不一致は保存して停止。OSライセンスの同意やグローバルtoolchain変更を自動実施しない。R3/R4の本実行は本契約の存在だけでは開始しない。

現在の次工程はR1の実装と有限数値確認。今回で移植成功/学習再開/banto統合/保全業務合格は認定しない。需要2015再評価停止、2014以前調整・同休業mean28・四季平均の過小/過大非増加・観測のみ/欠測0分離、heartbeat PAUSEDを維持する。
