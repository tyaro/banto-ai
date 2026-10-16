# v3人工fixtureのexact文字列エラーを保持

2026-10-15 JST。v3はE/Iと非ゼロrの二計数を通過したが、追加した人工ラベル試験のcandidate_daily_exactへstr(float)の10.0等を渡して停止した。既存bounded arithmeticは整数/分数文字列を要求するためであり、許容型を広げない。v3 source/stdio/exit1/resources/failed closureを保持する。

v4ではこの人工fixtureのcandidate_daily_exact/candidate_totalだけをstr(Fraction(value))へ直す。実装v2、τ/丸め/式/入力契約/テスト条件は変えない。実データや2015を参照しない。初版・v2・v3の閉鎖状態と全sourceを保持して、同じ有限集合を完了する。
