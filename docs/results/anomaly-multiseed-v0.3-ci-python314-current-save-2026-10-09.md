# Python 3.14単一CIの原証拠保存

## 今回の範囲

2026-10-09開始10:39:32Z、HEAD c25813db605cbafc31a0ef98b4eba79e726c7216/origin/upstream一致・clean。先行元8helperのfull creation-start_token/live-executionとCIM同original不在/repo helper-critical ownerなしを確認。production/test/body0、新worker/native/完成focus/基本probe/追加agent/profile再観測0。

CI37913386221/git実full b4a0401680b0d938598c71ff890948f208eee2b5/attempt1/push/Phase 1 CI/.github/workflows/ci.yml/workflow349172377をcompact一回でcompleted-successへ固定。外部原run11699B/5526a9653cdbd3eb9516ea91b1a59c7f810ee280430e527b25d5e1a8e913d503、jobs113763626515 test(3.14)/113772270721 verify-python314-journalの双方completed-success。新code4f20c013a64dfc86b01d70e86f08f626a99c60c1のrun選択一回で37918180709/push/Phase 1 CI/in_progressを特定、attempt/jobs/終端未固定。原list164B/aa76abdfc110257aa688e51385ebf0f8eaae2a47c2c8be0f365bc5f41dd580a8。新CI待機/再照会/download/local verifier0、doc-only CIを追跡しない。

## 原rawと独立検証

固定attemptのjobs/artifacts/2job logs/2zipを各一回取得し、単一member名・展開上限8MiB・外部run/fullHEAD・artifact digestを照合。journalとremote検証JSONを各一回展開保存。二つのartifact digestはzip rawのSHA256に一致し、runner image digestではない。

- journal4082414B/e612acc2758ed8654cfcf15167bb2a488cf9b46628e56ee10477243aa04f9422。
- remote regression37192B/7f78471bd9098c5fa1a84ddd01cd4bd4170bee2fabe78724804d6a789c4ae3a4。
- unittest artifact11609663143/zip347901B/7cb363e966d56ca7ceb8f0d062421ed6085693ebe2792f5726abe90e04b00d2f。
- verification artifact11609928000/zip7997B/90fdafdac44a9bd7ded0dd9b0f86761649e59e89c3bfd06912ca71887d9ba01b。

現ci_verify_python314_journalを原external fullHEAD/workflow SHA256 71f0e56eb9b0bb11a6e181e860a64ba45a6a4004cde7d4a5bf35d2b42cbf65a7/run37913386221/attempt1で一回実行。local verifierはexit0/verification_status=passedを出力。実run_finished/discovered/tests_run3930、failure0/error0/skip237（Windows native213＋non-S4 optional24）、source_unchanged=true/shared inventory29 complete/必須28passedを確認。cross_python_comparison_performed=false。3.12実行や版間比較の結果へしない。

## 原metadata失敗と追補

原verify helperはlocal rawとremote rawの完全一致assertでexit1。local37193Bは末尾CRLF、remote37192BはLFで差1byte、保存済みJSONは全field一致。原script/live/execution failed/failure/tool traceback/local raw-stderrを保全し、原helper/ローカルverifier/全suite/旧focusを再実行しない。別metadata continuationは保存済み2rawのstrict JSON/CRLF-only/外部source pin/実summaryを読み取り照合しただけ。raw_equal=false/json_equal=true/CRLF-only=trueを別々に保存、原failedをpassedへ書換えない。

local verifier実行前の7CLI working-Git pinは原helper内で観測したがmetadata失敗前に個別保存されていない。追補は現7CLI working前後-Git原b4a0401を照合し、6exact/ci_windows_native_skip_ids.pyだけ既知CRLF差を両pin保持。現在の照合を実loaded runtime closure/原native認証へ補わない。元helper process全stdout-stderrは未保存、selected verifier/gh CLI bytesとtool excerptを保存。scripts inventoryのpath missもmetadata tool excerptで、production/CI/native/Sol容量失敗ではない。

- local-verification.json: 37193B/b885b8c8ceebac26fd70abf412125e38a3d4b9c2a00763cec7a2715de13e7c1e。
- local-verification.stderr.bin: 0B/e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855。

metadata continuation4683B/23112aeb5e7c40f257650828f3efde00016c570e6a72b4da264ee6111d043b15。原2job logsは原run/jobs IDへ固定し、全raw pinは専用rootで保持。

## runtimeと未完了範囲

原journal runtimeはUbuntu24.04/x86_64/GCC13.3.0/kernel6.17.0-1022-azure/CPython3.14.8/SOABI cpython-314-x86_64-linux-gnu/runner image20261004.327.1。image digest未取得・候補未採択、Linux3.14互換性の保存でWindows正式CPython3.14.0/実Win ABI/native Job/ACL/stdio/child transport/容量/正式S4ではない。最新writer準備code4f20c01の成功証拠へ読み替えない。旧failure379079/3930 failure1/verify skipped、先行ローカル複数source-run、旧CI/閉鎖rootは原記録を保持・追加なし。

原CI artifacts/ci-diagnostic-37913386221/は16MiB256entry/single8MiB内、metadata artifacts/preformal-ci-python314-current-save-20261009-prep/は512KiB32entry/reserve128KiB/single128KiB内。元全helper終了とGit保存後、両rootを最終manifestで閉鎖し追加/同保存/完成CI再実行を禁止する。今回code/test変更0、3文書をdoc-only一回skip ciへ集約。

次はCI37918180709のcompact一回・終端なら未保存rawを新rootへ一回保存。それから実IO writer同request-root参加/原owner排他/all-writer atomic/fresh loaded runtime source closure-profile-private policy-request-unusedroot、全planned32entry/原partial-new growth-codec-native buffer-object overhead/global coupled peak/実callsite-HANDLE-stdio-child close-rename transport認証の未完成経路へ進む。基本runtime probe/宣言roster/cached completionをnative許可へしない。

自走ACTIVE、追加agent禁止、状態不変の通知/再照会なし。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout観測未読/正式5残件・最終受入未完了、create_native早期拒否/全7役whole.run限定reader実起動禁止/元caps・unknown原owner-stopを保持。停止割込み/Sol容量エラーでは保全後PAUSED。
