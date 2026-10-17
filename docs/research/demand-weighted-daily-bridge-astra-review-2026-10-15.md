# Astra：非ゼロ係数の日次bridge人工確認

2026-10-15 JST。ユーザー指定の既存gpt-6-astra担当を再利用しread-only確認。追加agent・実データ/実ラベル/fit/2015なし。

既存配分のB=F(fsum),E=sumF,unit14F(u)、copy/floor/比例P/Eの区別、issue Qで14日全体へ適用、fallback前のβ/時点検査を支持した。非ゼロβでもdot0はcopy、copyのB−E差と微小非ゼロdeltaでの枝切替・再配分を隠さないよう指摘した。

初期fixtureの14日block内一定では週特徴が0になり、week-onlyと相殺が十分な識別例にならないこと、均一baselineでは誤った均等配分も通ることを指摘した。実行前に固定最終7日+1/曜日加算を導入し、週列非ゼロ、2つ以上の非ゼロ積の相殺、非均一shapeの正負配分と独立cross-productを追加した。日次表示有限だがfsumだけoverflowする拒否も追加した。

独立readerの39case名/全scenario集合/全配列/r-z/branch/丸め差/shape/相殺の確認にblocking指摘なし。float fixture v2修正はB!=Eを作るためでcore・条件緩和ではないと確認し、初回failed保持を求めた。反例は各caseの反例であり全10店四季ゲートではないという限定も支持した。

## 保存結果の最終確認

Astraが初版failed、v2 execution/readback両closure complete・integrity passedを確認した。39case/82replay/189check/期待拒否30、stdout819047B、独立4553比較、分岐29/8/2、forecast222bit/独立333bit・資源上限内を確認した。float_copy/tiny/changed、非ゼロ2積相殺、丁度/負floor、表示値と表示fsumの別overflow拒否を保存結果から確認し、blockingなし。

微小補正例ではB−E=1/2^54を保持し、exact比例日次和=PだがdisplayのfsumはBに留まり、表示差は−deltaになる。小さな総量補正から同じ小ささの日次変化や表示変化は保証できない。この限定を明記する。

16反例は人工case別・mode別で、全40店Qセルや四季性能ゲートの評価ではない。daily_bridge_artificial_ready=trueだけを支持し、実prefix/solve/最適性/性能改善は未検証、fit_ready=false/can_launch_learning=false・学習/2015停止維持を確認した。初回失敗とfixture修正の履歴を保持し、人工完了から実データ接続へ進めない。
