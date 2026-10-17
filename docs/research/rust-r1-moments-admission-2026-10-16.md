現在の進捗（2026-10-16）: [FMA人工forward/局所一致は完了、全体候補は不採用](../results/banto-ai-rust-r1-fma-extension-2026-10-16.md)。modelは復元済み。is_require_gradは葉の勾配保持、graph参加はis_trackedで確認した。backward/学習は未実行。以下の当初条件と過去記録を保持する。

現在の進捗（2026-10-16）: 項目1の参照binary確認は[局所全bit再現](../results/banto-ai-rust-r1-binary-moments-2026-10-16.md)まで完了。項目2以降は[FMA実装条件](rust-fma-primitive-contract-2026-10-16.md)に沿って進める。以下の当初条件と旧負の結果は保持する。

# R1モーメント計算 — 次工程の受入条件（2026-10-16）

[照合結果](../results/banto-ai-rust-r1-moments-audit-2026-10-16.md)を受けた設計境界。R1の許容差・参照・元7ケースを変更しない。標準LayerNorm候補の再試行や、既知1点に合う算術探索はしない。現時点でmodelへ採用する追加方式は未選択。

1. **参照の計算順を確定する。** pinしたPyTorch wheel/build情報と実行コードから、4レーン更新後のscalar AddMomentsで積和縮約が行われるか等を確認する。ヘッダーの通常演算を一演算ごとにf32へ丸める解釈では、mean260/rstd21行が一致しなかった事実を維持する。FMAの有無を数値一致だけで選ばず、compiler/binaryから根拠が得られなければ未確定で止める。新たな数値比較を行う場合も、その根拠と有限回数を先に固定する。
2. **graphを保つ演算境界を選ぶ。** 推論だけのhostループやto_data/from_dataでdetachする方式はmodelへ接続しない。既存Burn pin/featureを保つtensor/backend拡張でf32 fused multiply-addを表現できるか調査する。公開APIに見つからなかったことから拡張不能とは断定しない。新依存・backend切替・グローバル変更を自動追加しない。
3. **FMAのforward契約を先に固定する。** 独立oracleはRust標準f32::mul_addとsystem fmafの相互照合を候補とする。人工の通常値、積の丸めが相殺される例、subnormal、signed zero、個別積がoverflowしても積和結果はfiniteの例を含め、入力・期待bits・有限範囲・非有限拒否の役割を事前保存する。f64経由だけで一般のcorrectly-rounded f32 FMAを保証しない。実装方式未決定なので、この文書はprimitive実行開始やAPI完成の宣言ではない。
4. **学習契約も残す。** 実数上の局所微分da=b・db=a・dc=1、broadcast軸のgradient合計、同一tensorを複数引数に使った際の加算を将来の独立確認対象とする。丸めたfloat関数の階段を微分する主張ではない。forwardが合ってもbackward成功とはしない。R2実行はR1全体通過後、既定の有限更新・再開fixtureに従う。
5. **model接続は一般方式で一度だけ。** 実装の根拠、全LayerNormへの一律適用、局所比較/全体比較の有限回数、採用/復元条件を数量計算前に別設定として固定する。元7ケースの全23anchorを通過して初めてR1を合格とする。失敗は保存し、許容差緩和・参照再生成・失敗点の例外処理をしない。

親900秒/子870秒、physical footprint・peak RSS各2GiB、build cache+target1.5GiB、旧artifact/EvidenceStore/stdio上限を維持。既存成果・失敗・closed rootsを保護する。保全・点検第一優先と学習を含むRust移植を維持し、CARE test/需要2015の再評価、下流repo変更、Windows native/OS依存検証は今回の範囲へ足さない。
