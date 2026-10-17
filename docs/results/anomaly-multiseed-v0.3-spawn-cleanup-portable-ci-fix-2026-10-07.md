# v0.3 spawn cleanup fixtureのLinux CI修正（2026-10-07）

保存code `9473523f3d2dd04259b6b8492ea3b9a237600e69`。gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。変更はtest fixtureの1行。

## 失敗原証拠と修正

CI37590543104 / 外部HEAD `f0b3d72deea42ab984ad70a20a20cd7dcace7225` / attempt1は両minor3229件、各fail1/error1/skip237/source不変、全run failure。3.12 job112690704814、3.14 job112690705168、compare112707082230はskipped。run/jobs/failed-step log/2full job log/2journalの7rawを `artifacts/ci-diagnostic-37590543104/` に保全した。compare logとcomparison/regressionは実行されておらず、成功CI保存やrunner候補照合へ読み替えない。journal imageは3.12=20260927.320.1、3.14=20261004.327.1、digest未取得/候補未採択を維持。

失敗はSpawnCleanupOwnerTestsのtest_body_and_delete_interruptions_keep_both_errors_and_unassigned_root（failure/AssertionError）とtest_original_body_failure_with_successful_cleanup_reaps_and_keeps_default_error（error/AttributeError）。Linuxにctypes.get_last_errorがなく、fake AssignProcessToJobObject=False時のowner._needが想定OSErrorを作れなかった。test setUpへpatch.object(ctypes,'get_last_error',return_value=5,create=True)を追加し、既存fake Win APIとともにそのAPIを明示する。本番owner/keeperや受付flag・停止/原handleの保全は変更しない。

## 焦点と保存

CIで失敗した2件だけを再実行。Windows上でもctypes.get_last_error属性を除去してLinux相当の欠落を再現し、fixtureがstubを追加できることと、終了後の元global ctypes属性復元を確認。2件 / 0.004320秒、fail0/error0/skip0。全module discoveryは従来9件のままで、9件全runや先行proof18/keeper13等の反復はしない。これはfake API試験で、実Linux/実Win ABI/native/実exe/容量の合格ではない。

選択10 source/test/science pin前後不変、変更test safety pass。code-saveはHEAD=origin/clean、10 working/Git pin一致、先行proofの選択16 pin不変を照合。全repository safetyは先行e4cb30秒timeoutの未確認を保持、再試行しない。全helper終了・critical ownerなし・追加agent0・新native0。

raw: `artifacts/preformal-spawn-cleanup-portable-fixture-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 3676 | `0f1500be4dcaca0048924c49ee9a17b7dc336c2b18973ea4cdb12da6d31a9839` |
| focused.log | 554 | `205b1ab3016b56ce86286d42894d54e79bc8d1cf71eb78ce91f9eccf2d894cef` |
| code-save-checkpoint.json | 694 | `96bfdde7766c572da48c9962472679fc266117b07223e4e7fe5a57376534db78` |
| CI37590543104/failure-complete-index.json | 2863 | `1d5a879c0cf8c98048f819cc7d8f143722bb8f066059389b210977c1baac2021` |

修正後CI37596406096（HEAD9473523、各minor3247予定）は進行中。先行proof CI37592838738（HEAD7da5aa9、3247予定）も終端未確認で、今回のfixture修正を含まない。各外部HEADの完了/失敗を個別保存する。旧失敗rawと初版discovery失敗CI37592461789も保全する。

## 次の小さい単位

予定していたworker archive/resolverは、この具体的なCI失敗を先に直したため未実装。次は旧parent archiveを流用せず、成功/failed receiptの原close event、identity call、確認できたrecovery eventとexact raw inventoryを専用opt-in archive/resolverへ結ぶ。実actor/shared stop probe/原keeperのPython終端保全、0-job/部分ackを実entryの前に固定し、新source/runtime inventoryと未使用rootを準備する。新nativeはその後の別exclusive準備で扱う。既存outer1MiB/32entry/depth2/reserve128KiB・全体321MiB/672entryを保持し、旧使用済みrootへ追加/再起動しない。正式5残件と実データengineering読取り範囲は変わらない。
