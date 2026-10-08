# Publication準備CIの未保存証拠をcontinuationで照合

2026-10-08 JST、開始時2026-10-08T04:21:37Z。文書HEAD/origin b9948658b487ddcab98f96f8e03ca387afcd5c4c/clean、production aab97b86334baafa399067ba646ff8afd51850e9。元helper35864/47804は元creation/tokenに対応するprocess残存なし、repo helper/critical ownerなし。read-only rate_limit probeがexit0だったため、未保存分を新専用rootへ取得した。

今回production/test変更0、完成focus/旧suite/native/実worker/Job/pipe/exe/追加agent/runtime-profile再観測0。formal gate=s4_acceptance_not_frozen、permission=false、credit0、登録holdout観測未読。science2は既定pinへのhash metadata照合だけ。doc-only3文書を一回skip ciへ集約する。

## 原run rawを保持したまま不足分を取得

前回のpartial rootとAPI unexpected EOF、approval deadline、元failed helperは変更しない。新continuation rootは旧run rawのpath/pinを参照し、run APIを再実行せずrun rawのコピーも作らない。元run/rawと新attempt jobsで同じ外部実fullHEAD/attempt1/push/Phase 1 CI/.github/workflows/ci.yml/全3jobを固定した。

| run | 外部git実fullHEAD | 3.12/3.14/compare job | 結論 |
| --- | --- | --- | --- |
| 37721863325 | e0f8fc4b0121bde9b1755bd7858b7ced3c01b09a | 113131098507/113131098337/113139108805 | failure/failure/skipped |
| 37722343194 | b4366887f9b49509ae5722b41a3e683fd1586dbb | 113132652418/113132652615/113143096296 | success/success/success |

旧run rawは前者11719B/66500fa1e383e9703a52228365d0432e432f49a1e0b385cbb329a4bf9bfbadac、後者11707B/8aa825db6d629538501b76a6ec940116a601a4e856bff64672e14bdaef6b3ec5。旧partial rootは6file15590B/13file25626Bのまま、全pin/count/bytes不変。前回API失敗を今回の取得成功へ書き換えない。

## 先行failureの原因と原証拠

`artifacts/ci-diagnostic-37721863325-continuation-20261008/` へ未保存jobsと両failed-step logの新3rawを一度保存した。旧run raw参照と合わせた4raw pin。両logは3747tests/errors4/skip237。4件ともMock factoryに置換されたReaderGitWorkerをisinstanceの型として使い、TypeErrorが元例外を覆った。原failed-step logの小さい原因行で確認し、全logは展開しない。

これは先行37717924409と同じ4件の原型保持問題で、code b4366887f9b49509ae5722b41a3e683fd1586dbbへ既に修正済み。今回追加code修正・失敗ケース再実行・完成5焦点再実行0。先行runのfailure/比較skippedを後続runのsuccessへ読み替えない。failure runのjournal/local回帰/runner成功照合は追加0。

failure-summary.json 5701B/f7fe7fe9ba12416fe9bd0f67f35aa410c336d563188d6b6cd4a4d3ba986acc34。新failure continuation rootは最終8file1938888B、原run参照/元helper/返値記録を保全し、追加・同保存再実行なし。

## 型修正後successのCI照合

`artifacts/ci-diagnostic-37722343194-continuation-20261008/` へ未保存jobs/2journal/remote comparison-regression/3logの新8rawを一度保存した。read-only local regressionを新1rawとして追加し、旧run参照1＋新9＝10rawへ結んだ。

両minorは実journal3748tests/fail0/error0/skip237/source_unchanged=true/unittest_success=true/formal_permission=false。local-remote regression一致、comparison matched/共有29fixture、両minor必須28pass。workflow原Git object SHA256は1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8。完成済み別CIのverifier/downloadは反復しない。

runner v2はconsistent_candidate/full_journal_verification passed。3.12とcompareは20261004.327.1/prerelease=true、3.14は20260927.320.1/prerelease=false。保存された公式release/README metadata/blobと当該log/journalの外部pin一致だけを確認した。image digest未取得、候補未採択。CLI7は6raw一致、ci_windows_native_skip_ids.pyの既知CRLF6差1fileはworking/Git両pinを保持する。

- complete-summary.json 3313B/d5fd3b8b7edf7a8cf16b08c46158b80a54c719eff2d76ad46bc80ec1c8040526。
- ci-complete-index.json 3433B/57019b5479e824fa54b6affca54564108a6acda6b242c99f76870f81f06a9e43、14pin。保存pathはartifacts相対で旧run参照と新raw/metadataを区別した。
- 3.12 journal3932309B/8421d956b1456a539ecafbdc8ef6202231c6f92d468d03f41361305928df31b1、3.14 journal3931664B/a7814292f36e26e4838864c2b848be8d4eb66c6001fbd25e749a3861258131e4。
- runner input3594B/954293ad92b5046a4ad978b61b5f357e0ca7a65af63e846dae11188cc5d72cb7、result4091B/7f5df7814b6531383a81d73aec04e8339c0e2feccd1aa35b14f05f31a34ed95f。

success continuation rootは最終33file10032474B。14CI pin/CLI両pin/全root pinを保存後照合へ結び、旧rootへ移動・追加しない。Ubuntu CIの当該fullHEAD結果であり、最新aab97b8のCI/native/全経路wall/容量合格/正式受入へ読み替えない。

## 元helperと保存後照合

各helperはIO前に元PID/creation/tokenをliveへ、finallyに同identityをexecutionへ保存した。Get-Process creation/CIMで同じ原identity残存なしを照合し、PID単独で同一扱いしない。

- failure download：41224/134359070202595175/token45884b167185be94cdc36b1140d02ee523eaa07a639787342688c29de355b087、saved_failure。
- success download：39560/134359070228317956/token7c87118c6e9500fcd533f976786a59e643e5b6c78e192e6a707c2d64d1616192、passed。
- local verification：47192/134359071128071488/tokene3ebf7a81938968ef3a0a8e13252fb92bc87732cd9326eac1dc52b9d1842af72、passed。
- runner/index/CLI：22788/134359071567431487/token26708b90fbdcf93c47124b73e96a73a0bc10d770410eb8953c7e742e82bd99f1、passed。

batch `artifacts/preformal-ci-terminal-continuation-save-20261008-prep/` の初回metadata確認はPowerShell PSObject.Properties.Countが各propertyのcount配列を返すためsuccess_index_bindingで停止した。実indexは14pinであり、原失敗358B/3a60df80ff978ebed3d2df15a57bd62de40cfe6ee99a6b84358dd0a7b0670e18を別保存し、件数取得だけ@(...).Countへ訂正した。CI numerical verifier/download/runnerの再実行0。

save-checkpoint.json 14089B/d6ee35ceffc442c593dff83ff25680a3cf2710cfc309b32e2d1da08e4cf24f6bは旧partial2root不変/新success14pin/failure4raw/CLI両pin/全root pin/元4helper/選択source3＋science2union5 working-Git/HEAD-origin-cleanを照合した。API probe観測184B/0f4192ff96b2461fa327fa755006c68d7cef621363ccee2a0828f339db879693はtool-owned session38873 exit0、creation未取得でnative回収にはしない。docpush後はbatchへpost-saveを一度保存する。

## 残るCIと次の機能unit

未保存CIは37724967759/git実fullaab97b86334baafa399067ba646ff8afd51850e9だけ。今回compact readは3.12job113140946456/3.14job113140946251両in_progress、compare未発行、run未終端。各minor3769は予定でjournal未確認。doc-only新CI追跡なし。終端時だけ外部fullHEAD/workflow/run/attempt/jobsに固定し、新専用rootへ原raw一度保存する。今回完成success37722343194/failure37721863325や全先行完成CI/focusは反復しない。

次は共有HANDLEのduplicate/inheritance、元限定launcher owner→同Popen HANDLE creation→原child-local close/rename/raw witness transport認証の機能準備unit。fresh最新clean source/runtime/profile/private policy/request/unusedroot、全writer同request/root atomic予約、親identity任意将来failure raw/diagnostic、原partialとnew archive growth独立予約、entry/context実bytes、packet/gzip/frame/receipt/partial coupled peak/global/memory/exclusive準備は未完成。ReaderGitParent.create_nativeはroot/channel/clock/Job前拒否を維持し、nativeを開かず全7役whole.runを限定readerとして起動しない。

元wall/memory/output/cleanup30秒/poll0.25秒、archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entryを維持。snapshot/cached raw/sidecar/context pin、FileIO.closed/close、完成ack/proof、worker exit/EOF/marker不在/kill-waitを原native回収/atomic/lease/ack認証へ読み替えない。旧raw/pin/失敗/使用済みrootを保持。正式5残件/正式採択/最終受入は未完了。全helper終了/critical ownerなし/Sol容量エラー未確認、ACTIVE維持。
