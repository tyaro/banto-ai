# native buffer準備revisionのCI終端保存（2026-10-08 JST）

## 対象と開始状態

開始2026-10-08T08:22:39Z/HEAD732fee4201f1ca09b3fd6b7f53134d4e2731466a-origin-clean。先行元4helperのcreation-token対応process不在/repo helper-critical ownerなし。production code d4e5f2ec90a9c17be90af4eadebadb4b769a409bは不変、production/test変更0、完成focus/旧suite/13AST監査/native/追加agent/runtime-profile再観測0。science2はhash metadataのみ、登録holdout観測未読。

gitが返した実fullSHAへ限定して未保存CI37743146137を一度compact照会し、completed/successを確認した。新専用root `artifacts/ci-diagnostic-37743146137/` へ未保存原rawを一度保存し、batch `artifacts/preformal-ci-native-buffer-save-20261008-prep/` へ準備・件数/summary発行・checkpointを保存した。旧完成CI/packet/metadata continuation rootへ追加・再実行していない。

## 外部実行と保存結果

原run/jobs rawはfullHEAD d4e5f2ec90a9c17be90af4eadebadb4b769a409b/attempt1/push/Phase 1 CI/workflow `.github/workflows/ci.yml` に固定。workflow SHA-256は1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8で当該Git bytesと一致。

| job | ID | 実結果 |
|---|---:|---|
| test (3.12) | 113198312223 | completed/success |
| test (3.14) | 113198312515 | completed/success |
| compare-shared-fixtures | 113210284774 | completed/success |

原9raw（run/jobs・journal2・comparison/regression・log3）にlocal回帰1を加え10raw14pinまで保存した。両journalの実run_finished/discoveredは3844、fail0/error0/skip237、source不変/unittest_success=true。算術予定を実数へ読み替えず、原journalの最終行取得後にsave-completeへ期待3844を発行し、pre-journal scriptも保全した。

local regressionとCI regressionは一致、comparisonはmatched/共有29fixture、必須28各minorを確認。runner origin candidate v2はconsistent_candidate、full journal verificationはpassed。実summary取得後、runner/index双方へ同じ2584B/98810507…の実raw pinを発行し、先行旧summary-pin metadata失敗を反復していない。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| 3.12 journal | 4011960 | 4ed3d48b8c85ddf713da276e366d86eb8d5d60a98e62b0ba1701c9b8697bd9a1 |
| 3.14 journal | 4012558 | e6078a95f294423d9ce4d675ea8468ccd4fa15d8c2133612265f5d9f2518d486 |
| complete-summary.json | 2584 | 9881050794a2b1059147c868389f84a35316bc9329510d8352c8a4ac12a98047 |
| ci-complete-index.json | 2784 | b62bd9ff02c942df4ca86e73958d37dd79ec26fae2f5f906cdb0dea93c45e1a9 |
| local-cli-source-pins.json | 2138 | 6edc096c572795a9dcf16e654287c1bc1e3f706f5e5c01437088d2b09c81b18b |
| journal-count-binding.json | 1474 | 3e3def1e2f6577395e5991923d61f387132bdfdbe8f855ea46b3a46b804fd089 |
| summary-script-binding.json | 971 | 1673b18a8e6e1243191e36b7a2803ae13a49bcacaa46b8dfad1d09c7a9c1b119 |
| save-checkpoint.json | 12638 | 0b0f5b8481c0c633a5f1f63c0d2e0effef15bc8cdb4e83d3cc7230821caeef68 |

## runner・CLI・owner identity

3.12 imageは20261004.327.1/prerelease=true、3.14・compareは20260927.320.1/false。保存公式release/README metadata/blobと原log/journalの外部pin一致だけを確認し、image digestは未取得、候補は未採択。既存公式保存rawを新rootへcopy/再取得していない。

CLI7の6fileはworking-Git raw一致、残り `tools/ci_windows_native_skip_ids.py` は既知CRLF6byte差のみ。working pinと当該fullHEAD Git pinの両方をsidecarへ保全した。

| helper | 元PID | creation_time_100ns | start_token |
|---|---:|---:|---|
| prepare | 48032 | 134359215288138041 | d30d187b9e898836f80feaac991b45268ace3b3e6257668c4e148e7d762b3efa |
| download | 21736 | 134359215421862939 | d5c31ab8909c0142145a30701cce07aaa24113441c1cbc2fc2d68d2c7511ebe5 |
| count binding | 25164 | 134359216129993209 | 7f1c822f861b84957c247e8ebf4cd6beb0d51d30fa0f52cd6b8d2c39583e7e82 |
| verification | 35848 | 134359216135382040 | 7c1ac5e19b7d3b7c5f00bd4d2bbeaec012f4f5fe003a6d3a6f4c46a6f006eb5f |
| summary binding | 26020 | 134359216544365907 | b643240d6b289330cab9b3bd7c9f414053fea38868167c4aebfd6a6602e1eafa |
| origin | 28360 | 134359216547391335 | 0edb6220dbdd967d0f53b6d34dd03887ce13a0894c0763259548ec2efa284e62 |
| checkpoint | 25436 | 134359217034286019 | 2cc2a75cecd3b7168e9c9db48ab9cbe0a711119072bab4fed8e8ecaeae8cf03e |

各live/executionは同creation-token/passed/critical_owner=false。checkpointで元6helperの現在CIM creationとの比較により同original不在を確認した。PIDだけの再利用判定をしていない。原native Job/process/thread HANDLEの回収を観測したhelperではない。

## 保存単位と残件

checkpointは全37CI原file/14pin/CLI両pin/選択source3＋science2 union5 working-Git/元6identity/HEAD-origin-cleanをmetadataだけ照合した。閉じた旧native-buffer24file127365B、原packet14file319974B、packet continuation14file94207Bのcount/bytes不変も確認した。doc-only3文書を一回skip ci commit/push後、metadataだけpost照合しCI/batchへ同raw exclusive保存して閉じる。完成download/numerical/local regression/runner/旧focusの反復なし。

CI root上限16MiB256entry/single8MiB、batch512KiB32entry/reserve128KiB、元wall/time/output/stop保全を維持する。現production revisionの未保存CIなし、doc-only新CI追跡なし。先行packet原metadata失敗とcompressed154696B>131072Bの拒否は別に保持し、このsuccess CIで書き換えない。

CI3844は未発行native buffer admission準備revisionの外部工程確認。実Win ABI/限定launcher/専用HANDLE継承/child close-rename IO owner認証/packet容量/正式受入を確認した結果ではない。次は128KiB frame/512KiB archive上限を保つ新closed packet分割/別raw参照とsame lease/request/root/inventory/原owner/full raw readback/manifest pinの契約を準備する。旧format/pinの解釈変更や上限緩和をせず、原partialとnew archive growthは別量として保持する。

fresh source-runtime-profile-private policy-request-unusedroot/exclusive、all-writer同request-root atomic予約/親将来failure診断/entry-context実bytes/packet-raw-buffer-object coupled peak/global memory、原Create/Assign/member実return・原HANDLE owner/attribute lifetime・child transport認証は未完成。create_native root-channel-clock-Job前拒否/native入口/全7役whole.run限定reader実起動禁止を維持。formal gate=s4_acceptance_not_frozen、formal_permission=false、credit0、holdout未読、正式5残件/正式採択/最終受入は未完了。
