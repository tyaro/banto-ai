# Publication launcher準備CIの終端観測と部分保存

2026-10-08 JST。開始時2026-10-08T04:06:30Z、文書HEAD/origin `641d130712222839d05689706faf619030bb0d1f`、clean。元helper49692/43992/49872は各元creation/tokenに対応するprocess残存なし。sandbox内CIM読取りのAccess denied後、許可済みread-only照合でrepo helper/critical owner残存なしを確認した。

今回production/test変更0、完成focus/旧suite/native/実worker/Job/pipe/exe/追加agent/profile再観測0。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。science2はhash metadata照合だけ。doc-only追補を一回skip ciへ集約する。

## 終端を観測した2件

| run | 外部git実fullHEAD | attempt/event/workflow | 原run rawの結論 |
| --- | --- | --- | --- |
| 37721863325 | e0f8fc4b0121bde9b1755bd7858b7ced3c01b09a | 1/push/Phase 1 CI/.github/workflows/ci.yml | completed/failure |
| 37722343194 | b4366887f9b49509ae5722b41a3e683fd1586dbb | 1/push/Phase 1 CI/.github/workflows/ci.yml | completed/success |

開始時read-only状態照会では、前者3.12job113131098507/3.14job113131098337 failure、compare113139108805 skipped、後者3.12job113132652418/3.14job113132652615/compare113143096296 successを観測した。これらのattempt jobs原rawは後述の接続断により保存できていない。状態照会の表示をjobs pin固定やCI証拠完成へ読み替えない。

git rev-parseが返した実fullSHAと外部run原rawのhead_sha/id/run_attempt/name/path/event/status/conclusionを照合した。先行launcher準備runのfailureを後続型保持修正runのsuccessへ書き換えない。各minor3747/3748は予定算術のままで、journal実数・source不変・fail/error/skip数は今回未確認。failure原因は原failed-step log未取得のため未特定で、先行4件TypeErrorと同じ原因だとは推定しない。

## 原rawを一度保存した位置と停止境界

2件を独立した新専用rootへ一度保存しようとした。両方ともrun raw取得後、`/attempts/1/jobs?per_page=100` のreadが `unexpected EOF` / exit1で失敗した。

- `artifacts/ci-diagnostic-37721863325/`：run.json、jobs.json.stderr、failure-save-error.json、元live/execution、保存scriptの6file/15590B。AssertionError `('jobs.json', 1)` を原例外の記述として保持した。jobs/failed-step logs/failure-summaryは未取得。
- `artifacts/ci-diagnostic-37722343194/`：complete/run.json、download-error-0.log、download-failure.json、元live/execution、未実行verification/origin用scriptなど13file/25626B。RuntimeError `gh read failed:1` を保持した。jobs/journal/comparison/regression/3log/complete-summary/indexは未取得。scriptを置いたことをverification/origin実行へ読み替えない。

failure側の初回起動はautomatic permission approval reviewがdeadline内に完了せず、process作成前に拒否された。toolが許した一回だけ同じ起動を再試行し、その元helperが上記read failureを保存した。review timeoutの記録はbatchのapproval-first-timeout.jsonへ別保存。安全性の否定、native owner回収失敗、Sol容量エラーへ読み替えない。

元helperは各fallible保存前にPID/creation/tokenをliveへ保存、finallyで同identityのfailed executionを保存した。保存後Get-Process creationとCIMで同じ原identity残存なしを確認した。

- failure save：35864/creation134359062042342629/token13c17abc2d2ab9ac9efd70dd228f0aae89b5378337d90ee473c32ff326bc43bb、failed/元process残存なし。
- success download：47804/creation134359061023655906/tokenf3c5d484b4cc4bc59d7078e6f30371b6d29653b58ed6f4960d5c0753fda70b23、failed/元process残存なし。

PIDだけで過去processと同一扱いしない。両保存処理は再実行せず、取得済みrun raw・stderr・失敗・元helper identityを保全する。この2rootへ追加しない。正常CI証拠完成/local回帰/runner v2照合/候補採択にはしない。

batch `artifacts/preformal-ci-terminal-partial-save-20261008-prep/` のsave-checkpoint.json 5219B/sha256 d5745d767cb5b3d5e23ca7a960ea2c446f44fd3741e3c4db7d8000302d35cb36は全partial pin/元helper2件/選択source3＋science2（union5）working-Git/HEAD-origin-cleanを照合した。approval-first-timeout.json 241B/686b898ce195e625c5a311dcdff6247185a7fc43a642da3ad06a72fcdd647074。docpush後はこのbatchへ保存後照合を一度保存する。

## 次の保存と機能準備

新CI37724967759/full aab97b86334baafa399067ba646ff8afd51850e9は開始時in_progress、3.12job113140946456/3.14job113140946251。予定各minor3769、journal未確認。doc-only新CI追跡なし。

次のCI保存では接続状態を確認し、旧partial rootの原run raw/pinを参照しながら、未保存のattempt jobsとfailed-step logs、またはsuccessのjournal/comparison/regression/3logだけを新専用continuation rootへ取得する。旧保存script・保存済みrawを反復せず、原failureを成功へ書き換えない。success時だけ当該fullHEADのlocal regression/runner v2を一度確認し、完成CIを再実行しない。今回のAPI read failureと前回session6296のunexpected EOFは別の原失敗として保全する。

共有HANDLEのduplicate/inheritance、元限定launcher owner→同Popen HANDLE creation→child-local close/rename/raw witnessのtransport認証準備は次の機能unitへ引き継ぐ。共有後の原HANDLEを未共有abort-closeへ読み替えない。原API/返値/Popen/ownerをIO前保持し、unknown IOでは同じ元owner/raw/pending/errorを保持して後続拒否する。

fresh最終clean source/runtime/profile/private policy/request/unusedroot、全writer同request/root atomic予約、親identity任意failure raw/diagnostic、原partialとnew archive growth別予約、entry/context実bytes、packet/gzip/frame/receipt/partial coupled peak/global/memory/exclusive限定launcherは未完成。ReaderGitParent.create_nativeのroot/channel/clock/Job前拒否を維持し、native入口を開かず全7役whole.runを限定readerとして起動しない。名前30source/phase32要求/予定64Git Jobは完全runtime閉包ではない。snapshot/cached raw/sidecar/context pinをatomic/native許可にしない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB、global321MiB672entry、元wall/memory/output/cleanup30秒/poll0.25秒を維持。旧raw/pin/失敗/使用済みrootを整理・上書きしない。FileIO.close、closed/released、worker exit、EOF、marker不在、kill-wait、完成ack/proof rawを原native回収/全writer同期/lease/ack認証へ読み替えない。正式5残件/正式採択/最終受入は未完了。Sol容量エラー未確認、ACTIVE維持。
