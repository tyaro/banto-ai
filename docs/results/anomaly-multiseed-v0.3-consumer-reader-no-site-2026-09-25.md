# engineering readerのsite初期化を除外

2026-09-25。実装 `863af36c74aad1bc63ff42bd5b2b469c748882df`、基準 `6da417ce05d80d73c5f16ec8ee7e5ed14ff47be3`。OUT `artifacts/consumer-reader-no-site-2026-09-25`、最終文書revision・artifact pinは同directoryのsavepoint-evidence.json。[API](../anomaly-v03-consumer-reader.md)、[source/runtime計画](../anomaly-v03-consumer-source-runtime-plan.md)。

## 変更

別process readerのPython起動を`-I -B`から`-I -S -B`へ変更した。`-S`でsiteの自動初期化を止め、system site-packagesが起動時の検索pathに加わることを防ぐ。明示したcheckoutのsrc追加、入力anchor、30秒/512MiB/64KiBの監視、worker owner、公開結果のbytes照合と失敗記録のAPIは維持。

意図したsource差分はreaderとその試験の2file。前工程の47code pin・18data pinは変更前に全件一致を確認し、変更後はこの2fileだけを新pinとして記録した。古い保存点のpinは書き換えていない。generator.py/manifest.pyの既知CRLF/LF差も保全。

## 検証

通常権限の架空入力によるreader接続14試験を実行し、failure/error/skip0、3.963秒。追加1件＋既存13件で、算術suiteや720評価の再計算は行っていない。

追加試験は既存supervisorの起動optionをそのまま用い、子のbootstrap先頭だけに観測コードを追加する。実際の子processでno_site=1、isolated/ignore_environment/no_user_site/safe_path/dont_write_bytecode有効、site未import、startup hookなし、site-packages/dist-packages/PYTHONPATH指定先が検索pathに含まれないことを確認した。架空の環境package directoryだけを使い、Python本体やsystem siteを変更していない。この子が続けて保存済み架空レポートを確認し、別PID・終了確定・元公開物不変も確認した。

試験の感度を確認するため、別の新しい架空fixtureで起動optionから`-S`だけを除去した対照試験を1件実行した。`no_site=0`を検出して期待どおり失敗した（prior-startup-control.log）。本体sourceは変更せず、14試験の失敗数とは分けて記録している。

既存試験では起動観測を挿入しない通常bootstrapで読取成功を確認し、入力不一致・結果再封印・不完全結果・応答消失・timeout・終了未確認時のowner保持も確認した。実際に起動した7子processの監視記録をchild-processes.jsonへ保存。timeout/終了未確認は既存の模擬試験であり、実際のOS停止やハングを発生させていない。

## 資源と範囲

試験processの最大private 32.27MiB、監視した子の最大private 21.44MiB。試験前後の最小空きRAM 11.15GiB / commit余裕 19.45GiB、試験後C/D空き 124.34/365.97GiB。 OS Professional25H2/26200.9457、CPython3.14.0。監視側のruntime前後一致を確認。子の起動観測と監視側のruntime値は区別し、子の全DLL/stdlib/runtime受入とは扱わない。

旧保存点・closed・実計算checkout・本流・既存dirty文書の境界を保持、banto-24 PAUSED。登録データ読取・新評価・bootstrap・実freezeは0。formal/promotion/S6/trustはfalse、performance=not_evaluated、selected=null。

起動経路の改善は完了。source/runtimeの完全な証拠結合・正式consumer・最終audit・全体予算は残る。次は役割/source/process/起動条件の証拠validatorを具体化し、自己申告passや役割違いを拒否する小さなfixture試験から進める。正式gate/holdout、保留principal/UAC/ACL、上限変更、push/mergeは開始しない。
