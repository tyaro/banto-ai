# Rust R1 — バイナリの丸め順を確定、局所出力を全ビット再現（2026-10-16）

計画に沿って、**前回残った平均260行・逆標準偏差21行の差を、レーン統合時の二つの積和縮約で説明できた**。実バイナリから決めた一つの計算順で、全49入力/1,953行のmean/rstdと全124,992出力がビット一致した。モデル本体は変更していないため、元のR1累積1点未達・R2停止は維持する。

## ソースから実行コードへの結び付け

[読取り条件](../../examples/configs/rust-r1-binary-audit-20261016-r2.json)を実行前に保存した。インストール済みPyTorch2.14.0の `libtorch_cpu.dylib` をSHA-256/サイズ/UUIDでpinし、dyldが読み込む実pathとの一致を確認。pinは調査後も不変。Mach-Oのsymbol tableとfunction startsを解析し、Xcodeのllvm-objdumpでfloat LayerNorm呼出元、幅64で使う `RowwiseMomentsImpl<float,4>`、OMP呼出元の3関数を取得した。各範囲は16KiB以内、切り詰め0、命令列bytesとhash・tool/version/command/stdio/exitを保存した。

Binary SHA-256: `ca979f3619acb92240c2ef46d7581b1a388761e0fccfa7dc491a7eaa153d584a`。このMac wheelの証拠であり、別のPyTorch buildやWindowsへ同じ計算順を一般化しない。

最初のselectorは別depth版とcold関数を含む12関数が見つかり、6範囲の上限で停止した。逆アセンブルや数値kernelは未実行で、そのfailed root/source/stdio/exit/closureを保持。先にsymbol inventoryを保存したうえで、幅64・4レーンではchunk数1/depth<=4となるソース分岐から対象を絞った。上限の引上げや数値に合わせた関数選択ではない。

## 確定した丸め位置

以下のアドレスはslide前のMach-O仮想アドレス。前後のregister/dataflowと4レーン展開を確認し、FMA命令の存在だけではなく、どの式に対応するかを結び付けた。

| 範囲 | 命令 | 対応 |
| --- | --- | --- |
| 0x1f82028 / 0x1f82030 | fmla.4s | レーン内の平均/m2更新 |
| 0x1f822e4–0x1f822f8 | fsub, fmul, fmul, fmadd, fadd | lane0の分散補正項と既存m2の加算 |
| 0x1f82300 | fmadd s2, s4, s7, s2 | lane0の平均更新 |
| 0x1f82314 / 0x1f82320 | fmadd / fmadd | lane1のm2補正/平均更新 |
| 0x1f82334 / 0x1f8233c | fmadd / fmadd | lane2のm2補正/平均更新 |
| 0x1f82348 / 0x1f82358 | fmadd / fmadd | lane3の平均更新/m2補正 |

`delta=round32(lane_mean−mean)`、`c=round32(16/(n+16))` とすると、平均は `fmaf(c,delta,mean)`。m2の補正項は `cross=round32(round32(delta×delta)×c)`、`m2=round32(m2+fmaf(cross,float32(n),lane_m2))`。最後の既存m2との加算は分離される。前回はこの平均更新と補正項の積和を分離演算へ丸めていた。

affineの両weight/biasが存在する分岐では、中心化→rstd乗算→gamma乗算→beta加算という命令順を確認した。ヘッダーだけでscalarの積和縮約有無を決めてはいけないことも保存する。

## 保存値での一度だけの確認

[命令対応と再現条件](../../examples/configs/rust-r1-binary-moments-20261016.json)を数量計算前に固定した。前回の4レーン更新と初期stack統合はそのままに、上記のscalar統合だけを実命令のFMAへそろえた。system fmafを診断oracleに使い、保存済みPython入力・native moments・PP出力だけを読み、Torch kernelやmodel forwardは起動していない。相違時の丸め順探索・retryは0とした。

| 項目 | 結果 |
| --- | --- |
| 入力 / 行 / 出力要素 | 49 / 1,953 / 124,992 |
| 平均のビット不一致 | 0 |
| 逆標準偏差のビット不一致 | 0 |
| 正規化・affine出力のビット不一致 | 0 |
| 元の局所許容差の超過 | 0 |
| 新Torch kernel / model full forward / 学習 | 0 / 0 / 0 |

これは保存済みの有限7ケース/全7LayerNormでの局所再現。入力全般の誤差保証やRust全体のR1合格、需要/保全の性能改善ではない。元のR1 full forwardを修正して再評価した結果ではないことを区別する。

## 実装へ進む境界

[FMAの実装・人工検証条件](../research/rust-fma-primitive-contract-2026-10-16.md)を保存。次はgraphを保つ最小のFMA表現を選び、人工forwardで独立oracleと確認する工程。今回のhost scalar診断をmodelへ貼り付けず、private bridgeのunsafe変換や未証明のf64積和代用も使わない。forward契約の後、全LayerNormへ一律に適用する有限比較を別に事前固定する。Rust学習/backwardはR1全体通過後のR2の条件を維持する。

元の許容差・参照・weights・Cargo.lock・model core・旧成果/失敗/closed rootsを保持。保全・点検支援第一優先、産業/需要の自作モデル実用性と学習を含むRust移植目的も維持。CARE test/需要2015再評価・新データ/依存取得・下流repo変更・Git push・本番採用は0。需要2014以前調整、同休業mean28、四季両側非増加、観測のみ/欠測0評価分離は不変。

## 資源と記録

| 単位 | 秒 | 監視込みfootprint / RSS |
| --- | --- | --- |
| rust-r1-binary-declaration-20261016-records | 1.978 | 37,405,704 / 61,964,288 B |
| rust-r1-binary-audit-20261016-records | 1.993 | 44,778,528 / 107,855,872 B |
| rust-r1-binary-symbols-20261016-records | 1.845 | 33,539,080 / 118,194,176 B |
| rust-r1-binary-declaration2-20261016-records | 1.427 | 37,192,712 / 61,767,680 B |
| rust-r1-binary-audit2-20261016-records | 6.800 | 181,175,592 / 232,521,728 B |
| rust-r1-binary-moments-declaration-20261016-records | 1.708 | 37,012,488 / 61,718,528 B |
| rust-r1-binary-moments-20261016-records | 1.763 | 47,350,792 / 72,089,600 B |

selectorの初回失敗のみexit1、他はexit0。親900/子870秒、physical footprint/peak RSS各2GiB、build cache+target1.5GiB（最終967,097,375B）、旧artifact/EvidenceStore/stdio上限を維持。Mac process groupのsample観測でありhard OS capではない。Windows native/OS依存suite未実行、heartbeat PAUSEDを維持。既存NumPy未導入警告はstderrに保持。

主要rootは `artifacts/rust-r1-binary-audit2-20261016` と `rust-r1-binary-moments-20261016`、各宣言とrecords。失敗rootも保持し、全source/stdio/exit/state/closure・命令対応/集計/文書前後は `artifacts/rust-r1-binary-results-20261016-evidence` に保存。大型dylib本体は重複保存せず、全体hashと選択範囲bytesを保存した。
