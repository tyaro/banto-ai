# banto AI Rust R1の実装と再開条件

状態: R1a/R1b着手。ソース実装・依存解決・Python参照準備まで完了、Rust build/型検査/テスト/推論比較は未完。2026-10-16 JST。
[実装計画](../research/banto-ai-rust-implementation-plan-2026-10-16.md)と[R0.1](../research/rust-small-forecaster-r0-2026-10-16.md)に沿う。

## 実装した範囲

AI本体をbanto-ai側の [crates/banto-ai](../../crates/banto-ai/Cargo.toml) に作成した。root Cargo workspace、単独のlibrary、比較用predict example、入力/neutral model検査とcausal maskの試験を追加した。banto-industrial/denroku-psi-demoへの変更・依存はない。

| module | 実装内容 |
| --- | --- |
| input | 過去の有限float32 [B,3,128]、B=1..8を検査。観測0を保持し、非有限・shape不正を拒否 |
| checkpoint | trusted manifestのSHA、schema、named tensor/dtype/shape、overflow、offset/overlap/padding、finite値・scale floor・causal maskを検査 |
| model | 明示Flex CPU、context正規化、full variate/causal temporal attention、LayerNorm/GELU、順序付きquantile |
| predict example | 固定fixtureを読み、中間値を新規rootへ出力。失敗もclosureへ保存 |
| tests | ゼロ/欠測/shape、neutral破損、未来queryが過去出力へ影響しないことを検査するコード |

現在は推論ソースの段階であり、テストの成功を示すものではない。学習/backward/AdamW/再開はR2の予定。loaderは既存CARE neutral参照用で、製品用のmodel package仕様をすべて実装済みとはしない。q50やcontext_centerを需要の期待値に読み替えない。

## 依存解決

初回の新規lock生成はexit101。Burn0.22の無効な任意LibTorch依存が要求するzip0.6系が全yankedのため、CPU featureだけでも解決できなかった。

公式Burn v0.22.0の既存Cargo.lockをseedとして保存し、Cargoが許す既存locked packageの保持でローカル解決を通した。registry/yank flag変更、架空stub、別backendへの切替は行っていない。根拠は[公式lock](https://github.com/tracel-ai/burn/blob/v0.22.0/Cargo.lock)と[Cargoのyank仕様](https://doc.rust-lang.org/cargo/reference/publishing.html#cargo-yank)。

Cargo treeのnormal/buildとeffective featuresでは154packageが有効。実行backendはFlex CPU、Flex featureはstdのみ、rayon/SIMD/LibTorch/CubeCL/remote/ndarrayは無効。実有効依存のlicense宣言と同梱license本文を保存した。Cargo metadataの全resolve graphには無効な任意枝も現れるため、active集合の正本はCargo treeにした。metadata全graphを実際のbuild集合と取り違えない。

lock内には無効なzip0.6.6/tch/torch-sys/burn-tchが残る。**lockfileなしで新たな利用側が解決できることは未確認**で、配布/下流統合までの課題として残す。ローカルのlockによる解決を、そのまま製品配布の成立としない。

## 参照入力と数値比較の準備

`artifacts/rust-r1-python-reference-20261016` に、pinned fold0 modelと既存trainの先頭/末尾batch、人工zero/constant/floor-below/equal/aboveの7forwardを保存した。実データはtrain入力2batchだけで、同梱targetはskipして数量decodeしない。test/validation/calibration/truthへのopenはaudit hookで拒否した。Pythonは3.14.8/Torch2.14.0、1thread、学習/backward/optimizer0。

floor-equalのpopulation stdは全3系列で保存floor32と厳密一致。belowはfloorを使い、aboveはfloorを上回った。全出力finite/quantile順序を確認。中間値を含む参照は約1.5MiB、入力約32KiB。これはRustとの一致を確認した結果ではない。

[Rust比較器](../../tools/public-data/rust_r1_compare.py)を用意した。全case・named tensor・shapeを対応させ、R0の中間値/元単位quantile許容差と厳密な分位点順序を使う。数値不一致時は全件の差と先頭例を保存し、許容差を変更せず原因を調べる。現時点でRust出力はなく比較器未実行。

## 現在止まっている理由

Macの `/usr/bin/clang --version` はexit69で、次を返す。

> You have not agreed to the Xcode license agreements.

診断全文・command/exit/資源は `artifacts/rust-r1-compiler-preflight-20261016` に保存した。Xcode/Apple SDKの利用規約確認・同意は人が行う前提とし、自動同意や別経路による回避はしていない。非同期に人へ `sudo xcodebuild -license` またはXcode初回起動での確認を依頼している。

native Rust1.95.0とcargo/rustfmtは直接起動できる。workspace内に1.95.0のtoolchain pinを保存した。Cargo fmtはexit0で全Rustソースをparse/整形したが、**型検査やlinkの成功ではない**。compilerが使えることを確認してから、下記の有限実行へ進む。

## 再開手順

すべてrepository rootで実行する。監視wrapperはlocal Cargo home/target、native toolchain、jobs1、RAYON_NUM_THREADS=1を設定する。各記録先/outputは未使用名を使い、失敗したものも再利用しない。

1. Xcodeの利用規約確認後、compiler preflightをfresh rootで一度行う。
2. pinned入力/破損/maskの試験とexampleのbuildを行う。

~~~sh
environments/demand-macos/.venv/bin/python -B tools/public-data/macos_rust_run.py \
  --records artifacts/rust-r1-tests-20261016 -- \
  /usr/bin/env BANTO_R1_REPO="$PWD" \
  /Users/tyaromax/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo \
  test -p banto-ai --locked --offline --all-targets --features reference-tests -- --test-threads=1
~~~

3. 保存fixtureだけでRustを実行する。

~~~sh
environments/demand-macos/.venv/bin/python -B tools/public-data/macos_rust_run.py \
  --records artifacts/rust-r1-predict-20261016-records -- \
  /Users/tyaromax/.rustup/toolchains/stable-aarch64-apple-darwin/bin/cargo \
  run --locked --offline -p banto-ai --example predict -- \
  artifacts/care-learning-fold-0-20261016/selected-neutral-layout.json \
  artifacts/care-learning-fold-0-20261016/selected-neutral.bin \
  artifacts/rust-r1-python-reference-20261016/fixtures.json \
  artifacts/rust-r1-python-reference-20261016/inputs.bin \
  artifacts/rust-r1-burn-predictions-20261016
~~~

4. Rust出力rootがcompleteになった後に比較する。

~~~sh
environments/demand-macos/.venv/bin/python -B tools/public-data/macos_industrial_run_v2.py \
  --records artifacts/rust-r1-compare-20261016-records -- \
  environments/demand-macos/.venv/bin/python -B tools/public-data/rust_r1_compare.py \
  --reference artifacts/rust-r1-python-reference-20261016 \
  --rust artifacts/rust-r1-burn-predictions-20261016 \
  --output artifacts/rust-r1-compare-20261016
~~~

R1が通るまでR2学習、CARE test予測/再評価、製品コード変更へ進まない。R1の合格後は既定のR2有限fixtureを別に宣言する。

## 資源と保存

Rust用wrapperを追加し、commandと同process groupのcompiler/linker等の子孫をlibprocで追跡する。要求sampling20ms、親900秒/子870秒、supervisorを含むlive physical footprint/aggregate RSS各2GiB、Cargo jobs1、cache+target768MiB、従来stdio/成果上限を適用する。子孫の短命process/別groupの完全捕捉やOS hard capは保証しない。disk走査等を含む実sampling最大間隔も記録し、要求20msを常に満たしたとはしない。

依存tree解決の44.258秒が現時点の最長Rust準備unit。監視込みfootprint peak293,799,280B、aggregate RSS peak260,096,000B。依存cacheは観測約480MB。Python参照unitの資源は同名records/summaryに保存。いずれも学習/製品性能のbenchmarkではない。

失敗は、最初の宣言snapshotの相対path、初回lock解決、license archiveの古いtimestamp、metadata全resolveをactive graphと誤解した検査、compiler preflightを保管した。license archiveは原文bytesのwritestrで保存し、active graphは既存の成功metadataとCargo treeを使って訂正した。依存queryやmodel forwardを同一条件で無目的に反復していない。保存済みroots・失敗・科学条件は保持する。

主なrootsは `rust-r1-declaration2-20261016`、`rust-r1-lock-seed-20261016`、`rust-r1-tree-20261016`、`rust-r1-effective-features-20261016`、`rust-r1-metadata3-20261016`、`rust-r1-format-20261016`、`rust-r1-python-reference-20261016` と同名records。今回の最終source/文書前後/状態は `artifacts/rust-r1-prepared-20261016-evidence` に保存した。

Mac共通のsource・入力準備まで、Windows native/OS依存suiteは未実行。需要2015停止、2014以前調整・同休業mean28・四季の過小/過大非増加・観測/欠測0評価分離、heartbeat PAUSEDを維持する。外部アプリ変更/新データ取得/研究data送信/Git push/本番採用は0。


監視のdisk走査は別threadへ移してmemory samplingを妨げにくくし、人工の親子process2件でsmokeを実施した。exit0、92sample、実最大間隔23.55ms、監視込みfootprint27,903,224B/RSS50,446,336B。旧監視の最大間隔1.418秒の記録は保持した。研究参照modelを要するintegration testはreference-tests featureのopt-inで、通常のunit testは保存modelを要しない。どちらもRustテスト実行はSDK設定後である。
