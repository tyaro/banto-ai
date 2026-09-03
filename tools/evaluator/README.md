# Evaluation tools

chronological split、point／interval metric、residual anomaly metric、calibration check、report generation の共通 utility 用です。

単一の aggregate score が運用上の失敗を隠さないよう、metric は signal、horizon、operating mode、event type 別の slice を保持します。
