# 産業用公開データのMac新規取得契約（2026-10-16）

人の「WindowsからコピーせずMetroPT-3、油圧、XJTU-SYを公式配布元から取得して準備」による新規取得。既存の新取得禁止はこの3件に限って更新される。学習・モデル推論・性能採点・2015再評価・正式holdoutの停止は解除しない。

公式入口はUCI791、UCI447、WangBiaoXJTU/xjtu-sy-bearing-datasetsのREADMEで案内されたGoogle Drive。UCIはCC BY 4.0を公式ページで確認。XJTUは公開者の予後アルゴリズム検証向け利用・論文引用案内に基づく研究取得とし、CC BYや商用/再配布許可を推定しない。配布metadataと原本hashを保存する。

原本はrepository外の同workspace outputs/industrial-source-cache-20261016へ取得する。UCI2ZIP約295MB、XJTUは6分割RAR約4.4GBの全体が対象。これらは原本入力cacheで、生成実験artifactの単体32MiB/総量1GiBと区別。空き約111GiB確認済み。各HTTP取得はfresh root、HTTPS/TLS検証維持・curl retry0/子870秒・親900秒、1file最大800MiB、Mac physical footprint/RSS各2GiB。全stdout/stderr/exit/header/source・成功/失敗closureを各記録rootへ保存する。失敗partialを保全し、既存rootに再試行しない。

MetroPTと油圧は既存の原本size/hashとの一致と全ZIP member CRC/hashを検査。XJTUはGoogle公式配布案内の6partsを揃え、RAR全体の整合とファイル構成を検証する。公式期待hashが不明な場合、ローカルhashを公式署名と呼ばない。

準備する入力は、MetroPTの既読探索日2020-02-21の既存60秒/mean-last・14信号変換、油圧のcycle境界/センサーrate/別profileラベル、XJTUのbearingごとの時間順と2振動軸。モデル実行はしない。油圧cycleを連続寿命にせず、XJTUのfile間を連続25.6kHz波形にしない。故障報告・profile・最終寿命/未来状態を入力へ混ぜない。変換出力と独立したラベル・分割契約を保存し、既読と未採点を分ける。

新しい生成artifactは既存normal24files768MiB/total32files1GiB/single32MiB/failure8files256MiB、Evidence記録16MiB512files/part256KiB/failure2MiB16files/stdio1MiB128KiBを維持。Windows native、正式holdout、需要側禁止年度・店舗は対象外。旧変更/失敗/closed rootsを上書き/削除しない。heartbeatはPAUSEDのまま、追加agent/外部研究データ送信/Git push/製品採用なし。
