# Astra：実2013数量prefix・完全性・問題生成/β0確認

2026-10-15 JST。ユーザー指定の既存gpt-6-astra担当を再利用して、設計・source・保存結果をread-onlyで確認した。追加agentなし。2014数量・採点・2015・学習は対象外。

全210 metadata/25計画→全4file pin→全630 raw span pinを数量decodeより先に検査すること、2013選択行だけのfresh JSON、完全raw14日、元E/I/w-v、旧x/r/z/state pinを維持することを確認した。

中断人工試験はsealer直接呼出の模擬試験と明記し、実TimeoutExpired経路の試験と呼ばないこと、immutable consumerのlegacy人工readiness fieldを残して外側に実2013 compile-only scopeを付すことを指摘した。契約と実装へ反映した。

独立readerの数式再構築には整合としたが、strict field set/bool/配列長・metadata header・identity SHA・weekday support・全25計画のQ/cutoff/exclude検査を補強するよう指摘した。source凍結済み原版を保持してfresh v2に反映し、独立の数量read前に再確認した。

## 保存結果の最終確認

新たな blocking 点はありません。準備・実行・独立readback・モデルartifactはいずれも `complete`、integrity passedを確認しました。実行前後のモデルclosureも一致し、保護source・closureのhashも保持されています。

確認された到達点は、**許可済み2013の210件・2940観測を使った25問題の生成と、β0 baseline再現の独立照合完了**です。54,191比較、最大933bit、1190問題行で一致しています。

r0行は元分母に残っています。primary87行のcanonical総量と日次exact和の差も、日次コピーと残差保持という固定仕様に一致します。

報告では、encoderの記録済み`max_bits`値そのものは再現対象外である点と、中断閉鎖テストは模擬である点を維持してください。これは学習・最適性・実性能・採用の確認ではありません。`fit_ready=false`、`can_launch_learning=false`、2014採点・2015停止は妥当です。
