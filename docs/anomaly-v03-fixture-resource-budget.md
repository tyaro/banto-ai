# 限定fixture工程の資源停止条件

`_anomaly_v03_fixture_budget.FixtureBudget` は、新しいfixture保存先を対象に、容量・system commit余裕・RAM・ディスク空き・親process private・経過時間を監視する。[実装](../src/banto_ai/_anomaly_v03_fixture_budget.py)、[試験](../tests/test_anomaly_v03_fixture_budget.py)、[保存結果](results/anomaly-multiseed-v0.3-fixture-resource-budget-2026-10-01.md)。

[数値worker](anomaly-v03-fixture-worker.md)と[主集計audit](anomaly-v03-fixture-numerical-audit.md)の入口へ接続した。既存supervisorには任意の `resource_probe` を追加し、停止理由が返れば所有する子だけを停止・終了確認する。既存利用者が指定しなければ従来動作を維持する。

## 既定の小さい予算

| 項目 | 制限 |
| --- | --- |
| 呼出し/共有工程の経過時間 | 120秒 |
| 親process peak private | 512MiB |
| 新規保存先の通常ファイルbytes合計 | 32MiB |
| directory entry数 / 深さ | 256 / 8 |
| system commit余裕 | 2GiB以上 |
| 空き物理RAM | 2GiB以上 |
| 出力先volumeの空き容量 | 5GiB以上 |
| 観測間隔 | 0.25秒＋観測処理時間 |
| 停止後の最終診断用予約 | budget/resultの2ファイルで最大64KiB |

従来の子上限60秒/private256MiB/stdout+stderr合計1MiBも併用する。親と子のprivate上限は別々で、合計512MiBの制限ではない。親のpeakはOSが保持するprocess開始以来の値を使う。子の起動前には従来の空きRAM4GiB・disk20GiB条件も残る。

`budget_limits=None` なら上記既定値を用いる。指定する場合は全項目を持つMappingとし、上限を下げるか最低余裕を上げる変更だけを受け付ける。失敗後の自動上限拡大・再試行・成果物削除は行わない。

## 工程ごとと共有工程の使い方

`calculate_with_evidence(..., budget_limits=None, resource_budget=None)` と `audit_with_evidence(..., budget_limits=None, resource_budget=None)` は、それぞれ自分の新規receipt directoryの監視を必ず開始する。親のsource/入力検査から、子の計算・終了後照合・保存までを対象とし、最後にresource-budget.jsonを残す。

analysisとauditをまとめて制限するときは、新規の共通rootに `FixtureBudget(root)` を作り、`start()` 後、両呼出しへ同じ `resource_budget` を渡す。各receiptは共通rootの子directoryでなければならない。共通monitorは全役割の終了まで開いておき、途中の入力準備・工程間でも `checkpoint()` を呼ぶ。これにより次工程で時間・総容量をリセットしない。入力もこのrootに保存すれば合算される。

呼出し側はfinallyで `finish(budget, root, result, owner_error=sys.exception())` を実行し、最後に `save_result(root, result)` を行う。個別呼出しがverifiedでも、共有budgetが失敗した全体結果を成功として扱わない。個別receiptは当時の観測として保全する。これは制御用の資源記録であり、科学payloadや公開wrapperの追加ではない。

共有monitorを指定しない別々の呼出しは、それぞれの予算である。既存campaign全体や任意の保存先を自動的に監視するものではない。

## 観測と停止

Windowsの `GetPerformanceInfo` からsystem commit総量・limitを読み、差をcommit余裕とする。情報欠落を0扱いせず、観測失敗で停止する。原因を当該processのリークと断定する処理ではない。

保存先のメタデータだけを上限付きで列挙し、通常ファイルの長さを足す。リンク/reparse pointを辿らず、hardlinkや未知の種類、過大なentry数/深さは拒否する。Windowsの列挙キャッシュはリンク数を0として返す場合があるため、各pathのlstatで実際のリンク数を確認する。元評価directoryや保護rootを走査しない。

別threadが観測し、最初の停止理由を保持する。free値が回復しても自動再開しない。初回・親の各段階の境界・終了時にも確認する。監視thread自体の異常終了も失敗となる。記録はsample件数・first/last・最小/最大値・最初の理由だけで、毎回のログを無制限に蓄積しない。

子の実行中は既存supervisorが停止理由を読み、元Popenのprocessだけをkill/waitする。終了確認できない場合は元ownerを保持する例外を返し、診断保存やmonitor終了の失敗でもownerを失わない。監視threadの終了を確認できない場合も、成功とせず `UnclosedMonitor` とmonitor参照を保持する。

親の照合・mapping・保存は協調的停止で、段階の境界で中止する。実行中の1回の関数やnative callを強制的に中断する仕組みではない。停止後は書けたpayload/logを残し、検査済みと未確認の部分を混同しない。

## 上限の意味と記録

これは観測値に基づく停止条件で、OSのhard quotaではない。観測間隔・停止/終了確認時間・進行中の限定writeによる超過分は発生しうる。最終budget/result各32KiB以内は診断予約として別に許容する。残容量不足などで診断自体を保存できなければ成功を返さない。

容量は指定root内の通常ファイルの見かけのbytesであり、alternate streams、物理割当量、別directoryの総容量を保証しない。出力先volumeの空き容量は別に監視する。敵対的な同時書換え、他processの停止、子孫探索・Job Objectによる任意tree終了は対象外。

成功した呼出しは `resource_budget_passed=true` を追加する。resource-budget.jsonにはlimits、shared_root、samples、first/last、extrema、stop_reason、monitor_exit_confirmed、passedを保存する。正式許可・S6・full closureは引き続きfalse。小さいfixtureで停止条件が動いたことを、正式2,880評価/50,000反復の登録予算や実行許可へ変換しない。
