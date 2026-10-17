# Rust R1 — patch出力一致、once条件未達で経路確定を停止（2026-10-16）

**保存済みtrain-first patchの一度のLinear実行は元の6,144値と全bit一致した。設定88bytesも実行後二度で一致したが、事前条件のonce値-1は得られず、52638546だった。warm-bindingは失敗として閉鎖し、query結果とtrain実行経路は未確定のまま保持した。** 再実行、追加の実行命令読取り、model全体比較、Rust候補、学習は行っていない。R1は安定版累積1点未達、R2停止。

## 固定条件と一度の実行

[事前条件](../../examples/configs/rust-r1-sgemm-warm-binding-admission-20261016.json)は変更しなかった。fresh declarationで保存入力・参照出力・元六関数roots・source/SDK・model/lockのhashを固定した。入力は閉鎖済みartifacts/rust-r1-linear-python-20261016のtrain-first/input、patch.weight、patch.biasだけ。比較参照は同rootのtrain-first/python/fusedであり、再生成していない。保存payload全体のhashを照合したが、数値として展開したのはこの4entryだけ。ラベルや元データセットは開いていない。

torch2.14.0/git08187d9e0fba026dc8217405802ab5381dc88d90、libtorch_cpu SHA ca979f3619acb92240c2ef46d7581b1a388761e0fccfa7dc491a7eaa153d584a、実load済みlibBLAS UUID31104d4f4a7e3fa79e1855937b2011f2を検証。VECLIB_MAXIMUM_THREADS=1をtorch import前に設定、torch/interopも1。Linearはmeta deviceで作りCPUランダム初期化を避け、保存値をCPU Parameterへ設定した。contiguous input[8,3,4,32]、weight[64,32]、bias[64]とstrideを記録し、eval/no_gradのforwardを一度だけ呼んだ。

出力[8,3,4,64]の6,144値はbit不一致0、bytes SHAは元参照と共に948d88ef836769bd380160afaba08ad73b81f9712c44bd9fda94ee9b29b7d8e2。これは元の補助patch演算との同一性確認であり、Rust modelの改善や元R1全体合格を意味しない。

## 観測と停止理由

同imageのreadable/non-executable __DATA_DIRTY内[0x1e63de938,0x1e63de990)だけをown-task mach_vm_read_overwriteで実行前一度、後二度読んだ。各88bytes、返却size/OS成功/boundsを検証。Mach-O header/load commands/function-starts metadataの読取り以外に実行codeの新規読取りはない。旧六関数scopeは再開していない。

| virtual address / type | 実行前 | 実行後（二度同一） |
| --- | ---: | ---: |
| 0x1e63de940 / int32 | 0 | 1 |
| 0x1e63de950 / int32 | 0 | 2 |
| 0x1e63de958 / int32 | 0 | 1 |
| 0x1e63de960 / int32 | 0 | 1 |
| 0x1e63de968 / uint64 | 0 | 12582912 |
| 0x1e63de980 / int32 | 0 | 0 |
| 0x1e63de988 / int64 (once predicate) | 0 | 52638546 |

raw bytesとfieldsは保持した。global@940=1だけでquery=1とは認定しない。事前条件はonce@988==-1を前提としており、保存query/coreの命令にはその値以外でonce helperへ進む枝がある。そのhelperの意味を未確認のまま、安定した非ゼロ値を「初期化完了」や「初期化失敗」と断定しない。stateのonce_initialized=falseは**この固定-1判定の結果**であり、実際の初期化が未完了と証明したものではない。

数値比較と設定保存の後、固定gateでAssertionError/exit1となった。artifacts/rust-r1-sgemm-warm-binding-20261016と同-recordsはfailedのまま保存し、成功rootへ書き換えていない。再試行・待機後の追加読取り・thread条件変更・TLS query直接呼出しは0。torchのNumPy未導入warningもstderrへ保存した。list/f32 packingで出力を比較し、このwarningはbit比較の失敗原因ではない。

## 次工程と解釈上の限界

[次のsource/design条件](../../examples/configs/rust-r1-sgemm-once-semantics-admission-20261016.json)を保存した。まずinstalled SDKのdispatch_once公開宣言・inline実装と版/hashを確認し、once predicateの表現と完了保証を区別する。実OS/runtimeへ対応する根拠が得られなければ不足として残す。別版sourceや今回の出力一致に合わせて-1条件を後付けで緩めない。

このsource工程に新たな数値演算、live memory読取り、選択leaf監査は含めない。保存事実だけで次の判断ができるかを先に整理し、必要な場合だけ有限の独立観測条件を別に事前固定する。今回はこのsource工程をまだ実行していない。query/dispatch経路を推定した次leafアドレスは固定していない。

## 状態・資源・OS分離

model.rs SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80、Cargo/lock/default/許容差/元参照は不変。新Rustテストはdiagnostic-only変更のため追加実行していない。R1累積1点未達/R2停止、保全・点検支援第一、自作モデルの産業・需要での実用性、学習とoptimizer再開を含むRust移植の目的を維持。需要2015/CARE test再評価・学習・下流編集・Git push・製品採用0。需要2014以前調整、同休業mean28、四季両側非増加、観測のみ/欠測0分離、heartbeat PAUSEDを維持。

本観測はMacの実load済みAccelerateとown-process memoryに限る。Windows固有機能・OS依存suiteは未実行で、共通Rust coreの成立やWindowsでの結果とは分ける。

親900/子870秒、physical footprint/peakRSS各2GiB、build cache+target1.5GiBと既存artifact/EvidenceStore/stdio枠を維持。宣言/一度の実行の最大監視込みfootprint 181,044,496B、RSS系 239,878,144B、cache+target 1,037,488,009B。監視はsample方式でhard OS capではない。全source/stdio/exit/state/closure、失敗、入力pins、前後raw設定、出力、文書前後を保存した。集約はartifacts/rust-r1-sgemm-warm-results-20261016と同-evidence、publication自体のstdio/exit/stateは同-records。
