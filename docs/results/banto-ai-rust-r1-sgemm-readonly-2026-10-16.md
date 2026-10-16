# Rust R1 — SGEMMの6関数を監査、小行列経路の全bit再現（2026-10-16）

**実loadされたAccelerate/libBLASの6関数を上限内で読み、小行列T,N経路のFMA・lane合算・bias統合順を特定した。別に事前固定した保存値再現で、人工5caseのraw matmul3,840値とbias込み3,840値がPython参照と全bit一致した。train batchの実行経路は、未初期化設定からは確定できず保留した。** 新model候補・SGEMM/torch演算の呼出し・full forward・学習0。R1は安定版の累積1点未達、R2未開始。

## 読取り方法と来歴

[最初の固定条件](../../examples/configs/rust-r1-sgemm-readonly-20261016.json)に従った。libBLAS.dylibは通常fileとして存在しないため、別fileのbinaryと取り違えず、torch git08187d9e0fba026dc8217405802ab5381dc88d90のlibtorch_cpu handleからsgemm_を解決した。解決先のdyld header/slide、LC_UUID、__text、LC_FUNCTION_STARTSを確認した。

MacのUUIDは31104d4f4a7e3fa79e1855937b2011f2、OSは保存したplatform情報、libtorch_cpu SHAは既存ca979f3619acb92240c2ef46d7581b1a388761e0fccfa7dc491a7eaa153d584a。SDKのmach_vm.h/mach_init.h宣言を保存し、mach_task_selfだけにmach_vm_read_overwriteを使った。外部processへのattach/読取り、debugger、コード注入・実行・mapping変更はない。OSが成功と返し、要求sizeと返却sizeが一致した範囲だけを扱う。

header/load commandsは64KiB、function-starts dataは512KiB、関数数32,768、codeは1関数16KiB/合計6関数96KiBを上限とした。LC_FUNCTION_STARTSの次の境界で切り、各regionを読取り後に再照合した。実際は6関数/5,064bytes、全て非truncated、全phaseでUUIDと元source/参照/model/lock pinsを維持した。

読んだcodeをELFの.textへ格納した補助containerを作り、pinしたXcode llvm-objdumpで非実行のdisassembly入力とした。これは元のMach-Oファイルではなく、実code bytes/hash/virtual addressとcontainerを別に保存した。最初のentry listingには--disassemble-allによる.shstrtab表示もあるが、これは文字列dataであり命令証拠から除外した。以降は--section=.textを指定し、.shstrtabの見かけ上のFMA等を根拠にしていない。

## 対象選択と静的経路

各calleeを読む前に、先に閉鎖した呼出元bytesからB/BLをdecodeしてtargetを検証し、根拠とselectorをfresh declarationへ保存した。全callを探索せず、引数検査/error handler/他形状の枝は読まなかった。

| image virtual address | bytes | 選択根拠/役割 |
| --- | --- | --- |
| 0x18121adb4 | 296 | 解決されたFortran SGEMM entry |
| 0x18189b0c0 | 1,000 | entryの正常call、CBLAS形式の引数検査/転送 |
| 0x181899f74 | 852 | 正常call、GEMV/対称shortcutと一般経路の分岐 |
| 0x181392264 | 2,176 | 正常tail、shape/configによる行列積dispatch |
| 0x181210530 | 640 | 小形状T,Nの静的normal leaf |
| 0x18123cd78 | 100 | 一般dispatcherの設定query。読むだけで未実行 |

pin済みPyTorch LinearAlgebra.cppのrow-major出力処理と保存strideから、patchはcolumn-major SGEMM(T,N,m64,n96または12,k32,lda32,ldb32,ldc64,alpha1,beta1)に対応する。mm補助はbeta0。ABI変換後もalpha/betaのfloat registerと寸法は保持される。m/nが1のGEMV枝、beta1では成立しない対称shortcutを除いた。

coreはm/n>15、K幅、m*n*k、縦横比、初期化済み設定を使って分岐する。小形状m64/n12/k32では24,576演算、縦横比64/12>4、K32という条件から関連fast flagsが0となり、設定値によらずT,N leaf0x181210530へ到達する静的経路を特定した。m64/n96/k32は196,608演算、縦横比<4で別の幾何判定となり、同leafをtrainへ外挿できない。

## 未初期化設定を実行済み経路と誤認しない

[64byte設定読取り条件](../../examples/configs/rust-r1-sgemm-config-read-20261016.json)を別に事前固定し、同imageのreadable __DATA_DIRTY内0x1e63de950..990だけを二度読んだ。once token@988は0、参照する950/958/980の値も0で不変だった。fresh processで数値演算をしていないため、初期化済み設定ではない。initializerやSGEMMを呼んで埋めることはしなかった。

6番目のquery命令は、thread-local flagが非ゼロなら1、そうでなければ初期化後のglobal int32@0x1e63de940を返す。未初期化ならonce helperを通る。このquery自体も実行せず、TLS callbackやinitializerの先へ読取りを広げていない。したがって今回のcoldゼロやVECLIB_MAXIMUM_THREADS=1という環境変数だけで、前のtrain演算のkernelを認定しない。

## 小行列の命令順と別の有限再現

leaf0x181210530では、Kの4要素ずつをFMAで4laneへゼロから累積し、faddp二段で(lane0+lane1)+(lane2+lane3)へ合算する。K32、m64は4の倍数、n12は偶数なので、今回の小形状はKやm/nのscalar/GEMV尾部を使わない。biasは積累積の初期値ではなく、合算とalpha乗算の後にCをloadし、beta*CをFMAで加える。

根拠は0x181210574（accumulator zero）、5bc/5fc（vector FMA）、61c/660（pair合算）、698（alpha乗算）、690/6a0（C loadとbeta FMA）。biasをKループへ先入れする普遍的な修正を、この小行列の証拠から提案しない。

読取り監査とは別に[一度の保存値再現条件](../../examples/configs/rust-r1-sgemm-small-replay-20261016.json)を閉鎖保存した。新しいnative参照を生成せず、既存linear-boundaryのzero/constant/floor-below/equal/aboveの5caseだけを用い、system fmafとf32丸めで命令どおりに再現した。

| 比較 | 結果 |
| --- | --- |
| raw product vs 保存Python mm | 3,840値、bit不一致0 |
| bias統合後 vs 保存Python fused patch | 3,840値、bit不一致0 |
| 同じ参照に対する保存Rust baseline patch | 1,572値でbit差（既存の局所許容差は通過済み） |
| 新SGEMM / torch operator / Rust candidate / full model / 学習 | 全て0 |

これはbinary解釈を確認する1回の診断再現であり、trainの演算順やRust modelの合格を意味しない。別のFMA順・精度・算術候補を試さず、元の参照・許容差・weights・closed rootsは変更していない。

## 次工程を固定

6関数の読取りscopeは完了し、残るtrain経路を推測して7関数目を追加しない。[初期化後bindingの次工程条件](../../examples/configs/rust-r1-sgemm-warm-binding-admission-20261016.json)を保存した。これはまだ未実行。

次の独立unitは、元train-firstのpatch input/weight/biasだけでnn.Linearを一度実行し、元6,144出力のbytes一致を要求する。その前後に同imageの__DATA_DIRTY88bytesを範囲検査付きで保存し、once完了と設定の不変性を確認する。global@940が1ならqueryはTLSの両枝とも1と確定でき、追加query呼出しが不要になる。そうならなければ不明として止め、実行回数やthread設定を変えない。

目的は初期化済み設定と既存命令からtrain dispatchをbindすることであり、元のfull model/R1や既存7caseを再評価する工程ではない。追加の実行code読取りもこのunitには入れず、実pathが確定した場合だけ次のexact-address/単一region監査を別条件として固定する。元の六関数scopeを無目的にリセットしない。bias-first候補やvendor FFI採用へ直行しない。

## 状態・資源・OS分離

model.rsは元SHA acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80、Cargo/lock/defaultも今回不変。R1は安定版累積1点未達、R2停止。許容差変更・CARE test/需要2015再評価・実学習・下流編集・Git push・製品採用0。保全・点検支援第一、自作モデルの産業/需要での実用性と、学習/optimizer再開を含むRust移植目的を維持。需要2014以前調整、同休業mean28、四季過小/過大非増加、観測のみ/欠測0分離、heartbeat PAUSEDを維持した。

実行code/SDK/own-process memoryの証拠はMac固有であり、共通Rust coreへOS依存を追加していない。Windows native/OS依存suiteは未実行。Macのlibrary監査とWindows成立を分けて報告する。

全32roots/各実行は親900/子870秒、physical footprint・peak RSS各2GiB、build cache+target1.5GiBと旧artifact/EvidenceStore/stdio枠を維持。最大監視込みfootprint 182,536,016B、最大RSS系 244,957,184B、最終cache+target 1,037,488,009B。process group sampleの捕捉限界がありhard OS capではない。全source/stdio/exit/state/closure、image UUID/regions/raw bytes/補助ELF/commands、設定読取りと再現、文書前後はartifacts/rust-r1-sgemm-results-20261016-evidenceへ保存した。
