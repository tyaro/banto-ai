# Astra：rank3・週変化係数非ゼロの人工接続

2026-10-16 JST。ユーザー指定の既存gpt-6-astra担当を再利用しread-onlyで設計/source/保存結果を確認。追加agentなし、実データ内容は閲覧しない。

A/B/Cと一定targetによりrank3と全β成分非ゼロを事前保証できることを確認。SVDに頼らず正規方程式のnorm恒等式を有理数だけで検査する案を提案した。binary64旧xとexact target、Q1休業除外差、罰則なしGram/minorを維持した。週項はfloor前の3成分代数分解から日次まで確認し、係数差替え予測は行わない方針とした。

起動前に、独立再構築state.r_storedとweighted r・z/problem・全ledgerの明示接続を補強する指摘があり、source凍結前に反映した。

## 保存結果の最終確認

新しい blocking はありません。execution/readback と model closure は complete・整合、保護対象185 closure／293 source、今回の source pins、全 phase freeze の一致を確認しました。

8問題すべて非罰則 rank3・週係数非ゼロ・KKT gap0。640予測、週寄与168件、独立照合の結果も報告と一致します。

結論には次の限定を残してください。

- floor は未到達。`B≠E` の10件は全て baseline copy で、比例配分488件は全て `B=E`。
- 全8解は非制約 ridge 解が既に可行で、証明書の active 一覧は空。制約によって最適解が変わる接続経路は今回の対象外です。
- 週寄与168件は persistent 160件＋open_zero 8件。weekday C は80件です。
- 人工 baseline 真値で悪化する112セルを保持しており、未来の非悪化や実性能の保証にはなりません。

「rank3・週係数非ゼロの人工接続を検証済み」までが妥当です。実学習・2015停止、`fit_ready/can_launch_learning=false` を維持してください。
