# v0.3 Python3.14単一CI3972の原証拠保存（2026-10-09）

## 対象と範囲

開始2026-10-09T11:42:48Z/HEAD fe8635f0b3861fefbf33ec6e9a6a85b4d8974ba5/origin/upstream-clean。先行元6helperの保存full creation-start_token/live-executionをread-only CIMへ照合し、同original不在・repository helper/critical ownerなしを確認した。

今回production/test/body0、旧focus/旧suite/基本runtime probe/native/追加agent/profile再観測0。未保存CI37923042206をcompact一度でcompleted-successへ固定した。新run選択・待機・反復照会・doc-only新CI追跡0。旧closed raw-rootへ追加していない。

## 原run/jobs/artifacts/raw

CI37923042206/gitfull e541e27b874a3c177336bbef527f613ab4c14447/attempt1/push/Phase 1 CI/.github/workflows/ci.yml/workflow349172377。原run11699B/e663790356c3bd5e49f1d0d5e8f3ba31ca65cff88e09b372975b9d00f400c28e、2job113795323234 test(3.14)/113803493060 verify-python314-journal全success。各jobs/artifacts/2logs/2ZIPを一回取得し、原CLI stdout/stderr bytesを保存した。

unittest artifact11613492662/ZIP350510B/b1385b37333cbba307853351dc86029fa0c461627ae094bea898e3ead3bc1561、verification artifact11613279721/ZIP7997B/24e38e744484af917e852e7d118724a615c50af60cee9bac08b213d84765adcf。両artifact digest一致、各1member・decoded上限8MiBを照合。ZIP digestはrunner image digestではない。

journal4116331B/227237b0543d9da47842588a72010811ed71caeb53bfa8aa30a0dfc6d3fac889、remote regression37192B/e0e17ed19a4da1ca5626af6633e87c61931c0340b087abe5619b8d6502a338d6。新raw root artifacts/ci-diagnostic-37923042206/、新metadata artifacts/preformal-request-remaining-writers-20261009-prep/。metadata root名は次工程の準備名だが、今回bodyはCI保存だけでparent_failure/diagnostic IOの新接続は実施していない。raw16MiB256entry/single8MiB、metadata512KiB32entry/reserve128KiB/single128KiBを維持し、最終manifestで閉鎖する。

## 独立検証一回

現tools/ci_verify_python314_journal.pyをexternal Git fullHEAD/workflow SHA25671f0e56eb9b0bb11a6e181e860a64ba45a6a4004cde7d4a5bf35d2b42cbf65a7/run37923042206/attempt1へ結び一回実行。exit0/verification_status=passed。原run_finished/discovered/tests_run3972/failure0/error0/skip237（Windows native213/non-S4 optional24）/source_unchanged=true/shared29 complete/必須28passed/cross_python_comparison_performed=false。3972は実journalと独立verifierのsummary取得後に記録し、算術予定を実件数へしない。

CLI7実行前working/Git pin・原Git batch stdout/stderrを個別保存した。6exact、tools/ci_windows_native_skip_ids.pyだけ既知CRLF差の両pin/rawを保持。working前後不変だが、full loaded runtime閉包・native認証ではない。

local verification37193B/f5decddb34baa6158994a5631ecab04ec63183be02ff27c671b773f08b638945、remote37192Bの末尾CRLF/LF差1byte。JSON全field一致/raw_equal=false/json_equal=true/CRLF-only=trueを両原rawで保存。verification-save4054B/dd94cb5f6ee09f24ab586ffa07d515d558134338b3c98569b76ddbd9ab979c72。旧CI3930のraw-equality failed helperは保全し、原helper/verifierを再実行していない。

原runtimeはUbuntu24.04/x86_64/GCC13.3.0/kernel6.17.0-1022-azure/CPython3.14.8/SOABI cpython-314-x86_64-linux-gnu/runner20261004.327.1。image digestはnot_collected・候補未採択。Windows正式CPython3.14.0/実Win ABI/Job/ACL/stdio/child owner/OS排他/容量/正式S4の合格ではない。

## Sourceと未完成の境界

3972件はe541 writer-storage接続準備source/runの単一CI保存である。同revisionのローカルfocus原失敗・複数source/runを最終source単一18successへ書換えない。旧3954/3930、旧failure379079/verification skipped、旧2minor比較をこの3972successへ読み替えない。

現working67source/scienceの元pin・検証済みdoc-only親tree非交差をmetadataだけ確認する。科学hash metadataのみ、登録holdout観測は未読。現在code e541の未保存CIは今回保存でなくなり、doc-only新CIは追跡しない。

次は未接続parent_failure/diagnostic/child bootstrap実IO、同原owner OS排他・all-writer atomic、fresh latest-clean loaded runtime-source closure-profile-private policy-request-unusedrootへの機能接続準備。全planned32entry/原partial-new growth-codec/native buffer-object overhead/global coupled peak/実native return-HANDLE-stdio-child endpoint-close-rename原transport認証は未完了。最新archive130691B/source cap131072Bとの差381Bを容量保証へせず、将来source増分はfresh inventoryへ固定する。

create_native早期拒否/全7役whole.run限定reader実起動禁止/formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了/元caps・unknown原owner-stop/追加agent禁止を維持。人の明示再開によりACTIVEで継続する。Sol容量エラー/人の停止割込みでは保全後PAUSED・重複再試行なし。

今回の開始source selector path missとrg .agents missはselected tool excerptだけstartup metadataへ保存し、helper process全byte log/CI-production-native-Sol失敗へしない。全CLI bytes/pins/selected tool traceはhelper process全stdout-stderr捕捉を意味しない。
