# 実用性検証とRust学習へ戻る計画改訂結果

2026-10-16 JST。[改訂2](../research/banto-ai-practical-training-return-plan-2026-10-16.md)を保存し、人の指示どおりpointer追跡を停止した。既存成果から実用性とRust学習の未確認部分を整理した。新しいモデル実行・学習・評価は行っていない。

## 判断と次工程

原R1は389,214要素中1点未達、最終正規化/元単位分位点は各6,048値pass。同一入力385局所比較の超過0を保存集計と照合。残差index3450の超過は1.74191474915e-07、限界比6.784155%。小ささだけで無視せず、学習gradient/更新への影響は未確認とした。context候補index183とは分離した。

正式R1を合格にするには元の全条件が必要。bit一致やOS内部の完全解明は追加要件にしない。追加修正は数学/公開Rust演算に根拠のある一般方式を最大1つ、局所一巡と通過後の固定7case全体一回まで。現在新候補なし、根拠がなければ実験0で未達保留とする。

R1未達でも人工データだけの学習部品と保存再開を独立したR2Pとして準備できるよう、作業順を改訂した。人工R2Pは元のloss/gradient/parameter/moment許容差と同backend再開bytes一致を使い、正式R1/R2合格とは数えない。実データの正式R2は原R1通過後という条件を維持。次の具体的な工程は現source/manifest/lock/feature/学習graphの不足整理と人工fixtureの仕様固定。

保全ではCARE検知3/12・未検知9・正常false3、native支持差を保持。MetroPT M1の探索的改善と一部悪化、区間coverage不足も[既存結果](metropt-macos-m1-2026-10-16.md)へ帰属した。既読testの追加評価や校正は行わない。業務上の先行時間・誤警報の必要条件と、移植/学習の正しさを別判定する。

## 保護と確認

R0.1 JSON SHA bd5c962c711decbad2e590af71ed9474d1f6256351571d3b16a8e3ada047c57a は不変。model/manifest/lockを含む29 protected filesと、元13 artifact rootsのclosureを保存し、文書更新後に同じhashを確認した。関連する旧pointer条件JSONやfailed rootsを上書き/削除していない。前後の計画・引継ぎ・READMEはfresh artifact/EvidenceStoreへ保存した。

今回の範囲は既存summary/比較集計の照合と文書改訂だけ。新forward/backward/optimizer更新/score/SDK-memory read/build/テスト/新データ/外部送信/Git push/製品変更0。既存test成功を現manifestで再検証したとはしない。現manifestの研究feature不整合は次の棚卸し事項とし、今回変更しなかった。

親900/子870秒、physical footprint/peakRSS各2GiB、cache+target1.5GiBと元artifact/EvidenceStore/stdio枠を維持。Macの文書/保存集計確認と、Windows native/OS固有機能の未実施を分ける。CARE test/需要2015停止、2014以前調整/同休業mean28/四季過小量・過大量非増加/観測と欠測0分離、heartbeat PAUSEDを維持。

集約はartifacts/rust-practical-training-replan-20261016、文書前後・source・根拠の集計・closure pinsは同-evidence、publication自身のstdio/exit/stateは同-records。今回のplan artifactがcompleteであることは、R1や学習が合格した意味ではない。
