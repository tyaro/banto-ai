# 旧source-object CI attempt 1のfailure原保存 — 2026-10-11 JST

人の明示再開に従いACTIVEを維持。開始2026-10-11T10:48:19Z/clean HEAD c25cc5356587033b43f556240e5881186017a8f5、production/test code 0919168683de1bdeafaea73bd5e2b44da77f7459 は不変。元17helper full creation-start_token/live-execution一致/CIM同original不在、原2failed・過去failedを保持、repository helper-critical ownerなし。

## 限定endpointと原failure

未実行 actions/runs/37963486811/attempts/1 を別unitへ明示して一回取得。37963486811/full2d66f40e0fbf0ec1e0ec251996399c59bbd2c314/attempt1/push/Phase 1 CI/.github/workflows/ci.yml/workflow349172377 は実completed-failure。原run11727B/963f0f9977da433ec2372b68fd3e5b8f86e4cf941d8fbe3e8ab1e6f650bb381f/stderr0/exit0を保存した。

前回run API unexpected EOF/stdout0/stderr91B/a6bbe26d78db48a2e48dde50a0b9546d9f001c1ad8013a29ba9945275c959427/原Python helper exit1・failed/原gh exit別保存Noneは元閉鎖rootへそのまま保持。同failed run API/原helperの無条件再試行ではない。別endpointの原returnを過去の未保存返値へ補わない。

2job113931906023 test(3.14) failure・113949032012 verify-python314-journal skippedを実jobs/fullHEAD-run-attemptへ固定。未保存jobs/artifacts/失敗job log/ZIP/journalを各一度取得、原gh stdout-stderr pinとexit0を保存。skipped job log0、verification artifact0、full journal success verifier0。

## 原journalと小cause

test log952113B/6a881173726570680939c59de3f77257e5e3fcbd4f5e81d7e930fa4491e7de31、journal4205837B/7c624cb455cc7a35fbf95f6fe210dc2b9621752b9929228b128b57be61845549。artifact11634278396/ZIP359271B/5c34fcccc2d41508c3d64b134e24b212260a3479833ebc17a8bbbe882fa8c4fb/単一unittest.jsonl member/decoded8MiB/artifact digest一致。ZIPdigestはrunner image digestではない。

原run_startedのexternal fullHEAD/workflow SHA25671f0e56eb9b0bb11a6e181e860a64ba45a6a4004cde7d4a5bf35d2b42cbf65a7/run37963486811/attempt1一致。実run_finished/discovered/tests_run4081/failure0/error1/skip237/source_unchanged=true/shared29complete/unittest_success=false。4081は実summary取得後に固定した。必須28passed判定やfull journal success検証を実施していない。

唯一のerrorは tests.test_anomaly_v03_preformal_git_receipt_archive.GitReceiptArchiveTests.test_phase_cached_parent_inventory_fits_as_synthetic_receipt_fixture、原exception class V03ValidationError、原logのblob archive file byte limit。全source二phase fixtureが常時512KiBへfitする旧test期待による既知のerrorで、productionの容量guard拒否を成功へしない。

当該期待は既にf9で全source/二phase planと容量上限を保持したfits-or-preserves-byte-bound-refusalへ訂正済み。今回固定済み1case/全suite/旧focusを再実行せず、code変更0。原2d66/4081failure、別f9/4081success、最新091916/4097successを別source/runとして保持する。今回CIのtemp archive原prefixはartifactに含まれず未保存。旧localの523790B prefixやsynthetic receiptをこのCIの原raw/native証拠へ補わない。

failure-analysis19163B/4eeaa29e5de213ef159c160c52bde8a5d6e938e7579939e77529715e5c3f28d7。run/summary/errorと原logの小excerptをmetadataとして保持。実Ubuntu24.04/x86_64/GCC13.3.0/kernel6.17.0-1022-azure/CPython3.14.8/SOABIcpython-314-x86_64-linux-gnu/runner20261004.327.1、image digest未取得・候補未採択。Windows正式3.14.0/実Win ABI/Job/ACL/stdio/child owner/容量/正式S4の証明ではない。

## 保存と次unit

113source-science working pin不変、verified091916/prior37 Gitとdoc-only親tree非交差を継承。create_native437B/旧SourceBatch14301B/元caps/schema不変。旧CI4097/main/post3root count-bytes-manifest pin不変、旧root追加・整理・collector/basic probe/native image/profile/37Git再実行なし。科学hash metadataだけ、holdout観測未読/credit0。

原raw artifacts/ci-diagnostic-37963486811-attempt1/ は16MiB256entry/single8MiB。metadata artifacts/preformal-ci-source-object-attempt-terminal-20261011-prep/ と artifacts/preformal-ci-source-object-attempt-post-20261011-prep/ は各512KiB32entry/reserve128KiB/single128KiB、最終manifestで閉鎖。追加/同保存/完成download/元helper/固定1case反復禁止。selected CLI/log/pinsはhelper全process stdout-stderr捕捉ではなく、foreground closure identity/full logsはNone。

今回production/test/body0、引継ぎと本保存記録2pathだけ一回[skip ci] commit/push。現在追跡していた未保存CI終端はなくなった。完成CI4097/4081failure以下/旧failure/旧2minorの再照会-download-verifier、doc-only新CI追跡を開始しない。

次は未接続source-object captureと実supervisorの元stdout/stderr・絶対期限・原owner保持のcallsite境界へ進む。実起動/native認証/全future32entry-global peak容量は未証明。fresh runtime完全閉包-profile-policy-native request-unused exclusive root、OS排他-allwriter atomic、診断専用公開/parent_failure実raw/child bootstrap/child close-rename原transport、正式5残件と最終受入も未完了。

formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/登録holdout観測未読。create_native早期拒否・全7役whole.run限定reader起動禁止・元caps/unknown原owner-stop・追加agent禁止を維持し、ACTIVEで継続する。
