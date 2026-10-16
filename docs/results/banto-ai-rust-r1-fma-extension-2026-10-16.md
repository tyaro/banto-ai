# Rust R1 — FMA拡張forward成功、モデル接続候補は不採用（2026-10-16）

**公開APIによるFMA拡張の人工forwardと局所LayerNormの全bit一致は通過した。一方、モデル全体では中間値3点が元の許容差を超えたため、接続候補は不採用としてmodel.rsを元bytesへ戻した。現在の安定版は従来の1点未達のまま**。許容差・参照・weightsを変更せず、R1は未合格・R2学習は未開始。

## 公開拡張APIと人工forward

[FMAの事前条件](../../examples/configs/rust-r1-fma-extension-20261016.json)を保存後に実装した。Burn0.22.0の `extension` featureに公開のbackend_extension、into_dispatch/from_dispatch、具体backend primitiveの安全な変換口があることを確認した。private bridgeやunsafe表現変換は不要だった。

`crates/banto-ai/src/fma.rs` はFlex CPUのprimitive storage上でRust標準f32::mul_addを使う。Autodiff<Flex>には三親のNodeGuardを保ってchildを登録し、既存tensor APIのexpandでbroadcastを表現する。高水準to_data/from_dataの読戻し・値の再注入はしない。backwardの実装コードはcompileしたが、逆伝播は実行も認定もしていない。

専用の非default feature `fma-extension` からburn/extensionとburn/autodiffを有効にする。Burn=0.22.0、Cargo.lock、既存defaultは維持。offline/lockedで実行し、Cargo treeのpackage集合は前後とも154で同一、FlexのSIMD/rayonは有効化していない。新package/versionの追加・download・registry編集・backend変更は0。

| 人工確認 | 結果 |
| --- | --- |
| 独立system fmafとRust scalar oracle | 固定20値のbits一致 |
| 通常Flex / Autodiff FlexのFMA | 各20値のbits一致 |
| broadcast / 転置viewとalias / offset view | 6 / 6 / 4値一致 |
| 入力不変・中間graph参加 | 確認 |
| shape/dtype/空shape/自動微分context・非有限境界 | 7拒否条件を確認 |
| 既存Rustの入力/causal/neutral整合テスト | 3件pass（接続前と候補接続後） |
| backward / optimizer / 学習 | 0、正しさ未確認 |

相殺、subnormal、signed zero、積単独はoverflowしても積和はfiniteの例を含めた。f64のmul+addをf32へcastすると0x3fc00002になるが、正しいFMAは0x3fc00001となる固定反例も確認し、その代用方式は使わなかった。

三つの技術的失敗を保存した。初回はprivate into_contiguousの呼出しでcompile失敗し、公開to_contiguousへ修正。次はテストがis_require_gradをgraph参加と誤解していたため、pinしたAPIの意味に従いis_trackedへ修正した（勾配を保持する葉と中間ノードの区別）。三回目はDeviceの等値比較がautodiff設定を区別しないことを境界試験で検出し、autodiff/checkpoint設定を明示比較した。演算式・期待bits・入力は変更しておらず、成功判定はfresh probe4のみ。非有限拒否でcatchした3件のpanicは意図した境界試験で、最終exit0と区別してstderrへ保持した。

## 一般的なモデル接続候補の有限比較

[接続前の固定条件](../../examples/configs/rust-r1-fma-model-20261016.json)に従った。binaryで確定した4lane/幅64のWelfordとscalar FMA統合を、host診断ループではなくtensor slice・普通のf32演算・公開FMAノードで表現した。全7ケース/全7LayerNormの同一Python経路入力で候補49組の124,992出力がPPとbits一致し、旧balanced式49組も保存RPとbytes一致した。

局所gate通過後に、一度だけ全LayerNormへ一律のcfg hookを置き、既存3テストと固定7ケースのfull forwardを実行。入力、context正規化、attention、linear/GELU、weightsなどは不変。元の23anchor/389,214要素に元R0.1許容差を適用した結果は以下。

| ケース | 元R1中間値の超過 |
| --- | --- |
| train-first | 1 |
| train-last | 2 |
| zero / constant / floor-below / equal / above | 各0 |
| 合計 | 3 / 389,214 |

- train-first / blocks.1: 1要素、最大許容差比1.003292136。
- train-last / blocks.1: 2要素、最大許容差比1.486830216。

正規化後/元単位の最終分位点は、それぞれ全7ケース/6,048要素が元許容差内で、非有限・順序違反はない。しかし全体の中間値gateは不通過であり、最終出力の通過や局所の完全一致だけで合格へ変更しない。

保存tracesで、最初のLayerNormより前のcontext_center/context_scale/normalized_context/patch/tokensは、候補と安定版が全35箇所でbytes一致した。参照Pythonとの差はそのまま残っており、同一Python入力での局所一致と、自経路の入力差を含むモデル全体の一致が別であることを確認した。3点を特定の一演算だけへ因果帰属せず、誤差伝播を別に検討する。

## 採否と現在の状態

事前の復元条件に従い、hookだけを戻しmodel.rsの元SHA `acefec42e7506d807f7deae22269f30f9bf409a8c8cf9d1ddb59c2ef6af7fa80` とbytes一致を確認した。候補source・全予測・局所/全体比較・失敗recordsは保持し、default featureは変えていない。FMAとreference_layer_normはopt-inの研究APIとして残るがSmallForecasterからは呼ばれない。現在の安定版の累積1点未達は不変で、今回の候補3点と混同しない。

同じ候補のretry、3点向け例外、許容差緩和、参照再生成を行わない。次は保存済みの初期context平均/尺度の差をソースと演算順から整理し、一般方式の根拠があるかを判断する。LayerNorm単体一致を再検証する必要はない。新候補/有限比較/採否を事前に固定できるまで新model forwardは起動しない。

保全・点検支援第一優先、産業/需要の自作モデル実用性、学習を含むRust移植の目的を維持。CARE test/需要2015再評価・実学習・下流repo編集・Git push・製品採用0。需要調整2014以前、同休業mean28、四季過小/過大非増加、観測のみ/欠測0評価分離、heartbeat PAUSEDを維持。Windows native/OS依存suiteは未実行。

## 資源と保存

全単位が親900/子870秒、physical footprint/peak RSS各2GiB以内。監視込み最大footprint 302,124,104B、最大RSS系指標 424,394,752B、cache+target最終 994,629,553Bで1.5GiB以内。process group sampleの捕捉限界がありhard OS capではない。旧artifact/EvidenceStore/stdio枠を維持した。

主要rootはartifacts/rust-r1-fma-fixture-20261016、rust-r1-fma-probe4-20261016、rust-r1-fma-local-kernel-20261016、rust-r1-fma-full-comparison-20261016、rust-r1-fma-model-restore-20261016および各records。全source/stdio/exit/state/closure、package/feature確認、集計/文書前後はartifacts/rust-r1-fma-results-20261016-evidenceへ保存。全体比較は結果rootがcompleteでもparity=falseによりcommand exit1であり、技術的失敗のexit101と区別した。
