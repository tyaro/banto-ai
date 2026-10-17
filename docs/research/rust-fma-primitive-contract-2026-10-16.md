現在の進捗（2026-10-16）: [FMA人工forward/局所一致は完了、全体候補は不採用](../results/banto-ai-rust-r1-fma-extension-2026-10-16.md)。modelは復元済み。is_require_gradは葉の勾配保持、graph参加はis_trackedで確認した。backward/学習は未実行。以下の当初条件と過去記録を保持する。

# f32 FMA — Rust実装と人工forwardの受入条件（2026-10-16）

[バイナリ照合結果](../results/banto-ai-rust-r1-binary-moments-2026-10-16.md)で参照の丸め順は局所再現できた。次はmodelへ接続できる演算境界の実装設計。現時点で実装方式・primitive APIの完成、Rust全体のR1成功は認定しない。

- 意味はround-to-nearest/ties-to-evenのf32 fused multiply-add。乗算の中間値をf32へ丸めず、積和を一度丸める。呼出側の普通のmul/addまで無差別にFMAへ変えない。今回確定したWelford/レーン統合の指定箇所へ共通に適用する。
- AI本体はbanto-ai内に置く。Burn0.22.0/Flex CPUのpinを維持して、公開拡張点またはtensor演算でgraphを保持できる最小方式を調べる。公開API調査では直接のFMAは見つからず、bridgeの中身はprivateである。unsafeな内部表現の読替え、registry編集、backendの自動切替、依存追加はしない。既存APIだけで実装できない場合は必要な変更範囲を設計として明示する。
- hostのto_data/from_dataで値を再注入する診断コードを学習modelへ転用しない。f64のmul+addをf32へcastするだけの方式は、二重丸めを排除できず一般のIEEE FMA代用とはしない。形式的根拠なしにその方式を採用しない。
- 人工forward fixtureを実行前に一つ固定する。通常値、相殺（(1+2^-23)×(1−2^-23)−1）、subnormal、signed zero、積単独はoverflowしても積和はfiniteとなる例、broadcast、shape拒否を含める。入力bits、期待bits、有限/非有限の責務を保存。独立なRust f32::mul_addとsystem fmafを相互照合する。実装候補は一方式とし、科学的な不一致後の候補探索をしない。
- 勾配契約は実数の局所微分da=b、db=a、dc=1とbroadcast軸の合計、引数alias時の加算。float丸め関数そのものの数学的微分を主張しない。forwardで一致してもbackward成功とはしない。backward/更新/optimizer再開の実行は元R1全体通過後のR2で行う。
- model接続の前に、全7ケース・全7LayerNormへの一律適用、局所比較とfull forwardの有限回数、元23anchorの許容差、採用/復元条件を別の機械設定で固定する。通過前に学習へ進まず、許容差変更・参照再生成・既知1点だけの例外処理はしない。

親900秒/子870秒、physical footprintとpeak RSS各2GiB、build cache+target1.5GiB、旧artifact/EvidenceStore/stdio枠、既存変更/成果/失敗/closed rootsの保護を維持。保全・点検第一優先、産業/需要の自作モデル実用性、学習を含むRust移植目的は不変。CARE test/需要2015再評価、下流編集、Windows native/OS依存検証をこの人工forwardへ混ぜない。
