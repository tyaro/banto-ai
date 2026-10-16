# Rustの現実装棚卸しと人工学習の検証条件

2026-10-16 JST。[復帰計画](banto-ai-practical-training-return-plan-2026-10-16.md)の工程0/1として、現実装の不足と、人工データだけの学習部品・保存再開を検証する条件を固定する。[機械契約](../../examples/configs/rust-r2p-synthetic-protocol-20261016.json)と[全人工fixture](../../examples/configs/rust-r2p-synthetic-fixtures-20261016.json)を正とする。入力・数式・解析的期待値は固定したが、数値参照bytes生成、Rustの学習実装・実行はまだ行っていない。

ポインタ追跡は停止のまま。R0.1の許容差とR1の残1点未達を保持する。本工程は独立した小型学習エンジンR2Pの準備であり、正式R2実データ学習や全SmallForecasterの学習成立を認定しない。

## 現実装の棚卸し

| 対象 | 現在あるもの | 学習へ進むために必要なもの |
| --- | --- | --- |
| Cargo/backend | Burn0.22.0/Flex/std/optim。installed manifestではoptimがautodiffを有効にする | 実効feature graphとlockの整合確認。autodiffを使うためだけの新依存は不要と静的には読めるが、実効graphは未確認 |
| parameter | BTreeMapの名前付きTensor。source由来のschemaは62tensor、学習対象59/109,024値、buffer3/348値 | 学習leafを明示的にautodiff/require_gradへし、名前・shape・順序を固定。parameter_count()の定数を実列挙の代用にしない |
| forward | 正規化・patch・attention・headと最終host Vec出力 | lossに渡すnormalized tensor/center/scaleをhostへ戻さず返す境界。現在のpredict()のVec出力を学習graphへ戻さない |
| loss/gradient | crate内の学習loss、全parameter勾配管理は未実装 | normalized pinball、tie、全件mean、名前付きgradientの完全性、buffers非学習、更新ごとのgraph切離し |
| optimizer | Burnのoptimizer sourceは利用可能だが、互換更新器は未実装 | 固定Torch sourceの意味に従う一つのnamed AdamW。global clip、全parameter decay、整数step、momentsの保存 |
| checkpoint | neutral readerはmodelと任意AdamW項目を検査するが、返すのはmodelだけ | moments/step/scheduleの保持と完全性、writer、commit、復元、取消、不完全保存拒否。現在のreaderを再開対応済みと呼ばない |
| 研究用module | FMA/context/fused-linear sourceと過去の局所検証がある | 現manifestに対応feature定義がない。自動復活・採用はせず、R2Pは標準tensor演算から始める |
| 公開入口 | 推論inputは未来targetを含まず、0は有効値、非finiteを拒否 | 学習targetは別引数。人工欠測の0埋めや評価labelの流入を追加しない |

現modelは初期化時のTensorを学習leafにしておらず、backward APIも持たない。Burn0.22のinstalled sourceにはTensor.autodiff().require_grad()、backward()、grad_remove()がある。古いBurnのgeneric backend型を前提に新APIを設計しない。学習leafの値とoptimizer状態を名前で対応させ、graph内部IDを永続identityに使わない。

neutral readerはmodel::項目の完全性を検査しても、再開に必要な全AdamW項目の完全性は検査・返却しない。float32のstepを検査する旧readerを新しい整数checkpointの代わりにしない。新しいwriter/readerは小型人工state用の別schemaから実装する。

## 依存設定の停止条件

readonlyのcargo tree --locked --offlineはexit101で、lock更新が必要と報告した。現manifestの直接依存はburn/serde/serde_json/sha2、lockのroot項目には追加でgemmが残る。現sourceのlib.rsが条件付きで参照するreference-normalization/fma-extension/fused-linear-extensionの3featureはmanifestにない。Cargo/lockは変更せず、実行準備は未完了として記録した。

次の実装前には、元snapshotを保護した隔離copyでoffline lock同期案を作り、package/version集合を変えず必要なroot edgeだけを直せるか確認する。依存version更新や旧研究feature復活を一緒に行わない。差分がこの範囲を超えたら適用せず停止する。

人工harnessはtraining-tests=[]と明示test target r2p_syntheticで隔離する案を固定する。受入commandはcargo test --locked --offline -p banto-ai --features training-tests --test r2p_synthetic。これらのfeature/targetは今回追加しておらず、まだ実行可能なcommandではない。古い診断exampleの自動列挙を含む--all-targetsを本検証に使わない。

## 人工データと期待値

全入力はJSONから一度だけCPU float32へ変換する。乱数・実データ・CAREのweight/label・既読testは使わない。PyTorch参照もCPU、thread/interop1、foreach/fused=falseで固定し、installed source/gitとrecipeを保存する。

### lossと勾配

lossはr=(actual-center)/scale-predictionに対するmax(τr,(τ−1)r)の全B×C×H×3平均、τ=[0.1,0.5,0.9]。入力contextを使うfull modelではなく、predictionを独立leafとする部品検証。center/scale/labelは定数で、学習しない。

| case | 主な境界 | 手計算によるloss |
| --- | --- | --- |
| L0 | prediction[-1,0,1]、actual0 | 1/15 |
| L1 | prediction/actualが全0、全分位点でtie | 0 |
| L2 | actual2、全残差が正 | 11/15 |
| L3 | actual−2、全残差が負 | 11/15 |
| L4 | center10/scale2/actual12、label正規化と端のtie | 7/30 |
| L5 | B2/H2で全件平均の分母を確認 | 2/5 |
| L6 | B2/C2で異なるcenter/scaleのbroadcast | 19/60 |

解析的gradientはr>0なら−τ/N、r<0なら(1−τ)/N、exact tieなら(0.5−τ)/N。L1はloss0でもgradientが全0にはならない。L0〜L4のgradientを有理数で保存し、L5/L6も同じ式で独立検算する。installed Torchがこの期待値に元許容差内で一致することを参照生成のgateにし、違えばRustを走らせず停止する。

### global clipとAdamW

clipは全named gradientのL2 normを合わせ、一つの係数min(1,1/(norm+1e-6))を掛ける。zero/below1/exact1/cross-parameter norm5の4case。normがちょうど1でも分母の1e-6により係数は1未満となる。parameterごとのclipへ置換しない。

AdamWはlr3e-4、β=(0.9,0.999)、eps1e-8、decay0.01、全parameterへdecay。fresh zero-gradient、符号混在、epsに敏感な微小gradient、global clip、人工step4096のmomentsあり、momentsありzero-gradientの6caseを各1更新だけ比較する。None gradientを0と同一視せず、名前欠落は更新前に拒否する。zero-gradientでも既存momentは消去せず、stepとdecayを扱う。

数学的な独立oracleはm/vの更新、bias correction、decoupled decay、sqrt後のepsという固定式。実際のfloat32の比較参照はinstalled Torchの単一tensor処理であり、f64数式の値だけに置き換えない。Burn既定optimizerと複数候補を比較して結果に合う方式を選ばず、Torch互換のnamed更新器一方式を実装する。

### 小型学習問題と保存再開

人工affineモデルのweight[3,2]・bias[3]の計9値だけを学習する。q=x@weight.T+biasをpinballへ渡す。これは学習経路と配置を確認するtoyで、順序付き分位点を返す製品APIやSmallForecasterの代わりではない。

初期値・4種類のbatch・8回の順序[A,B,C,D,A,C,B,D]を全JSONで固定した。Pythonは連続8更新を一度だけ行い、各stepのloss/gradient/clip/parameter/m/v/counterとstep0..8のprobeを保存する。Rustは次の3processだけを使う。

1. Aで連続8更新。
2. Bで同じ初期stateから4更新しstep4を確定保存、step5の前に取消を受けて終了。
3. Cを新processで起動しBのcheckpointを復元。step4/probeを照合してから残4更新。

Rustのtoy更新は計16、独立AdamW6case込みで計22。Bを取消ケースに兼用し、取消検証のため別の学習軌道を増やさない。共通stepでのparameter/m/v/counter/schedule_next/probeは同一Rust backend間でbytes一致を要求する。Python参照値をRustの復元stateへ注入しない。

## 数値とcheckpointの合格条件

[R0.1](../../examples/configs/rust-small-forecaster-r0-20261016-r0.1.json)をSHAで参照し、数値条件を再定義しない。

| 比較対象 | 継承する条件 |
| --- | --- |
| normalized loss | atol1e-6 / rtol2e-5 |
| clip前後の全gradient | atol2e-5 / rtol2e-4とglobal相対L2<=2e-4。参照norm0の特則も継承 |
| 1更新parameter | atol1e-6 / rtol1e-5 |
| 第1/第2moment | 1e-7/2e-4、1e-10/3e-4 |
| 8更新parameter / loss | 3e-6/3e-4、1e-5/5e-4 |
| 同じRustの連続対復元 | parameter/moments/counter/schedule/probeのbytes一致 |

toyの各更新を保存し、step1のparameter/lossは原one-update/normalized-loss条件、step2..8のparameter/lossは原eight-step条件を使う。momentsとgradientsは各stepで元条件を使う。この人工問題でのprefix判定への割当ては実行前の本契約に固定し、元R1や正式R2の判定を変更しない。新しい限界や平均での超過相殺は導入しない。norm/coefficient等の補助値は原因説明用に保存し、既存数値gateの置換に使わない。

checkpointはbanto.synthetic-training-checkpoint.v1。名前・shape・dtype・ordered parameter一覧・m/v・整数step・recipe/fixture/schedule hash・次位置・buffer・backend/thread identity・RNGなしを保存する。payloadとmanifestのfsync/検証後、exclusive commit markerを最後に書く。新規rootだけを作り、旧checkpointやactive modelを置き換えない。

復元はmarker/schema/hash/完全な名前集合/bounds/finite値/v非負/整数counter/schedule一致を全て確認してから新しいautodiff leafを作る。graph IDやhost pointerは保存しない。step4からnext_position4を再開し、gradientやmomentsをゼロ初期化し直さない。揮発的PID/時刻や保存先pathを論理stateのbytes比較へ混ぜない。

不正component6case、checkpoint不正8case、writer途中停止3地点を固定した。全変異の内容はfixture JSONへ列挙。破損・負v・欠落moment等はfresh copyを閉鎖する前に作り、閉鎖済みrootを改変しない。途中失敗でも既存の有効checkpoint hashが不変で、復元consumerが不完全stateを拒否することを確認する。これらのための追加optimizer更新はしない。

## 実行順と完了の意味

次はmanifest/lockの最小整合案を保存し、固定人工データのPyTorch参照と独立期待値を生成・閉鎖する。その後にRust consumer/更新器/checkpointを実装し、固定caseを一巡する。参照不一致・数値超過・復元差・上限超過は保存して従属工程を停止し、fixtureや許容差を結果に合わせて変えない。

全SmallForecasterの人工学習接続はこのv1の外で、部品通過後に別fixtureを固定する。正式R2のCARE prefixや成熟state importは原R1完了後。現時点のR1残1点をこの小型問題で合格扱いにしない。保全・点検支援の目的、CARE/MetroPT test凍結、需要2015停止/2014以前調整/同休業mean28/四季両側非増加/観測欠測0分離を維持する。

親900/子870秒、physical footprint/peakRSS各2GiB、cache+target1.5GiB/jobs1、artifact/EvidenceStore/stdioの旧上限をそのまま継承。compiler/linker子孫も監視する。Mac共通CPUとWindows native/OS固有試験を分け、今回Windowsは未実行。ポインタ追跡・新データ取得・下流編集・Git push・製品採用は行わず、heartbeatはPAUSEDを維持する。
