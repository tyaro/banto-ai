# 非ゼロ人工pipeline：独立readerのケース名解析補記

2026-10-16 JST。実行rootはcompleteで8非ゼロ解/240予測/228scenarioを保存した。初版独立readerは8stateと初期23予測まで検査後、`open_zero`を含むnameを無制限splitして5部分となり、4変数へ展開できずValueError exit1。failed EvidenceStore・全stdio/exit/source/progress/closureを保持した。

fresh reader v2はnameを最初の3つのunderscoreだけで分割し、残りをvariant全体として扱う1箇所の修正。旧sourceは変更しない。問題・solver・β・予測・人工label・数値仕様・上限・集合・成功条件は変更せず、保存済み同rootだけを独立照合する。追加compile/solve/予測/label生成はしない。

新readback-v2 rootへsource/binding/stdioexit/独立結果/resource/closureを保存し、旧failed rootも保護hashへ加える。学習/2015停止、その他事前契約の限定を維持する。
