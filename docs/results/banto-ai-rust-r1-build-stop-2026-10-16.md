# Rust R1 — Xcode確認通過、ビルド容量上限による停止（2026-10-16）

計画ID BANTO-AI-RUST-PLAN-20261016-v1のR1a/R1bに沿って再開した。人がXcode利用規約の確認・同意完了を連絡し、fresh clang起動確認はexit0。続くCPUビルドは**依存キャッシュとtargetの合計768MiB上限で停止**した。R1未完、Rustのテスト実行・推論の数値一致は未確認。

## 実行結果

| 項目 | 結果 |
| --- | --- |
| clang --version | exit0、artifacts/rust-r1-compiler-ready-20261016 |
| cargo test --locked --offline --all-targets --features reference-tests | process groupをSIGTERM、returncode -15、テスト実行前 |
| 経過 | 274.302秒、子870秒以内 |
| 停止時の監視disk値 | 805,979,625B、上限805,306,368B |
| 停止後のregular file合計 | 805,979,625B（内訳はdisk-inventory.json） |
| 監視込みphysical footprint最大 | 922,044,888B、2GiB以内 |
| 監視込み同時RSS最大 | 690,470,912B、2GiB以内 |
| waitで得た子peak RSS | 683,343,872B、2GiB以内 |
| 監視 | 12,018 sample、最大間隔0.095377秒、同時最大5process |

最終stderrはBurn関連ライブラリのコンパイル中。banto-aiの型検査・テスト成功を示す出力はない。資源監視はsamplingでありhard OS capではなく、短命processの捕捉限界はexit.jsonのまま。停止理由はXcode規約やメモリではなくdisk予算である。OSの空き容量不足という診断でもない。

コマンド、全上限内stdio、source snapshot、source pins、exit/resource/state/failure/closureはartifacts/rust-r1-tests-20261016へ保存した。開始前と停止後のsource/lockは同じ。失敗rootはfailedのまま保持。既存キャッシュ・target・closed rootsの削除/移動、上限の拡大、backend変更は実施していない。

## 残る工程と再開条件

ビルド用cache/targetの容量条件を具体的に見直してから再開する。通常artifact24file/768MiB・単一32MiB、EvidenceStore16MiB等の保存上限とビルドキャッシュ枠は別に扱い、変更が必要なら理由と新上限を先に記録する。現時点では上限引上げは未承認・未実施。現在のcache/targetは停止後も残るため、同じ条件の再試行はしない。完了に必要な最終容量は未確定で、今回の超過値だけを完成容量と見積もらない。

次はfresh rootでcargo test→固定predict example→独立比較器の順。[準備報告](banto-ai-rust-r1-preparation-2026-10-16.md)の7ケースと[R0許容差](../research/rust-small-forecaster-r0-2026-10-16.md)を維持する。Python参照は再生成しない。R2学習/保存再開はR1通過後に別fixtureを固定して進める。

Mac共通経路はcompiler起動のみpass、Rust coreは未検証。Windows native・OS依存包括suiteは未実行。CARE test/需要2015再評価、学習、下流repo編集、push、本番採用は0。AI実装はbanto-ai、banto-industrialとdenroku-psi-demoは利用側。保全・点検を第一優先とし、学習を含むRust移植の目的を維持する。需要2014以前調整/同休業mean28/四季両側非増加/観測のみと欠測0分離、heartbeat PAUSEDも維持。

文書変更前後・固定設定・全実行記録・容量内訳の保存先はartifacts/rust-r1-build-stop-20261016-evidence。過去の準備報告のXcode待ち記述は履歴とし、本報告を現状とする。失敗を成功へ変更していない。
