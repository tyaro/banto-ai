進捗（2026-10-16）: [人工forward/graphはpass、全154局所はbaseline bytes同一で改善なし・不採用](../results/banto-ai-rust-r1-fused-linear-2026-10-16.md)。primitiveは非default、model接続/全体forward/学習0。以下の安全性条件を保持する。

# Fused linear — 実装前後の安全性条件（2026-10-16）

[固定受入条件](../../examples/configs/rust-r1-fused-linear-admission-20261016.json)に従うpure-Rust候補。数値結果から方式を変えない。非default featureで公開Burn extensionを使い、同じgemm0.19.0を直接参照する。

`finite_fused_linear` はx[...,k]、weight[k,n]、bias[n]を検査し、shape/dtype/device/autodiff/checkpointの不一致を拒否する。m=1..120、k/n=1..128だけを扱う。高水準処理はreshapeと公開dispatch変換だけ。weightのstrideは維持し、to_contiguousによる別候補を混ぜない。

Flex primitiveは型・rank・shapeを再検査する。公開layout/storageから各axisの非負stride、start_offsetを取得し、`start + Σ((dim−1)×stride)` と最終byte境界をchecked arithmeticで算出する。最大indexがtyped storage未満、byte範囲がisize以内と確認後に、全論理入力/weight/biasの有限性を検査する。負stride/範囲外/overflowはGEMM前にpanicする。public primitiveの不正metadataを信頼してpointerを作らない。

出力は別の新規Flex allocation[m,n]であり、m×n個全てをbiasで初期化する。入力storageは共有しても読み出しだけ、出力には他の参照がない。連続出力のrow stride=n/column stride=1は各出力へ一意に書く。全allocationへの借用は同期GEMM完了まで生きる。

unsafeはこの証明の後のgemm公開pointer呼出し一箇所に隔離する。渡すshape/stridesは検査済みであり、各入力の全アクセスと出力全writeがallocation内にある。read_dst=trueに対し全出力初期化済み、destination/product係数は各1、共役なし、Parallelism::None。private bridge、unsafe型変換、vendor FFI、packingやkernel選択の変更はしない。返値が非有限なら採用せずpanicする。

Autodiffの三parent guardはchild登録まで保持し、x/weightをbackward stateに残す。dx=dY@W.T、dW=x.T@dY、db=sum_rows(dY)を既存backend opsでcompileする。reshapeのgraphも保つ。graph参加とbackwardの数値的正しさは別で、今回backwardは起動しない。学習/optimizer/再開はR2の別gate。

独立Fraction算術による8人工caseの期待bitsは実装と依存変更前の `artifacts/rust-r1-fused-linear-declaration-20261016/fixture.json` に閉鎖保存済み。両経路、全parentのgraph参加、入力不変、transpose/offset view、拒否条件を確認してから154局所へ進む。model/defaultの変更は局所採用条件を満たすまで行わない。
