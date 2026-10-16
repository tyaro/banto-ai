# 全alphaゼロの原因分析と制約付き学習の検討範囲

2026-10-15 JST。今回の人の依頼は2015停止のまま、Astraと原因を分析し、過小量・過大量の非増加を学習へ組み込む方法を検討すること。

今回の計算は保存済み共通残差モデル4state、そのcutoff以前の2013–2014 prefix、旧独立readbackからの記述監査だけとする。旧beta・alpha・Dは固定し、同Qの初期under/over微分、誤差と補正の符号、floor作用の有無を照合する。最適化・可行方向探索・新beta・新予測・候補成績・2014再評価・2015内容読出しと再評価は実行しない。人工2行の方向例は実データの改善証拠ではない。

仮説は「MSEだけで先に方向を決め、後段で幅だけを制限すると、両側条件を満たす別方向を探せない」。保存Dの失敗から、全係数空間での不可能性や別方式の改善を推定しない。原因診断後もλ・期間・特徴・許容差を探索しない。

第一設計案は既存3係数・λ=1・尺度・重み・入力支持を維持し、全pastQの両側非増加と学習row非負を係数最適化に直接課す。Q別MSEは今回学習hard制約に追加せず、既存正規化MSEを目的とし、将来のouter診断では従来のMSE含む三条件を分離報告する。currentQ限定・soft penalty・Q別MSE追加は今回の比較候補にしない。solver・数値証明契約は未固定なので、この文書はfit起動契約ではない。

同休業仮定mean28、raw0/null、unknown営業状態、01-01/12-25休業相当は維持する。学習は観測完全ラベルのみ、欠測0仮定は別評価に留める。2014以前のcutoff可用性とinput/label受渡境界を維持する。

記述監査は親900秒・子870秒、Mac sampled physical footprintとpeak RSS各2GiB、従来EvidenceStore 16MiB/512files/part256KiB・failure reserve2MiB/16files内。新モデルartifactは作らない。全stdio/exit/source/旧state pin/closure/負結果をfresh rootへ保存し、旧変更・失敗・closed rootsを保持。2015はimmutability hashだけで内容をdecodeしない。heartbeat PAUSED、push・採用・外部研究データ送信なし。Windows native/OS依存包括suiteは対象外。
