# S4-B1 DETACHED指定での制限付きchild E2E確認

状態: **起動flags修正・全体pure/fake・独立レビュー完了 / 保存後preflight前 / 実機未実施 / no native acceptance**。

## 目的と修正

[限定return比較](anomaly-multiseed-v0.3-s4-b1-detached-return-result-2026-09-10.md)ではAL1/stage700を取得できた。
次はdebuggerを付けず、既存run_control_harness()の固定childを実際に復帰・実行させ、既存の全control確認まで進む。

coreの_startだけを、NO_WINDOWからDETACHEDへ変更する。要求flagsは0x08000404から0x40cへ。
SUSPENDED/UNICODE_ENVIRONMENT、制限token、handle非継承、標準handle未設定、desktop空文字、
固定Python/child、-B -I、限定environment/cwdを維持する。DEBUG系flagsやdebug register操作は含まない。
公開entrypointは引数なしのrun_control_harness()のまま。任意path/token/ACL/flagsを受け付けるAPIを追加しない。
この変更は隔離worktree内の候補だけで、本流へは未統合。

## 実行する範囲

新規system-temp UUID rootを1個だけ作り、既存fixture/protocol b1.2を使用する。
childのprocess identity、実primary tokenとduplicate token、source/runtimeを照合後にResumeする。
既存のcontrol/frozen両側でAccessCheckと実操作の期待値を検査する。
control側は書込み/追記/属性/EA/作成/削除/rename/replace等の固定操作、frozen側は期待したアクセス拒否を確認する。
操作対象は当該新規fixtureの固定ledgerだけ。既存の診断fixture・証跡や他projectには触れない。

childはprofile/source/操作・標準handle等を検査してreportを書き、parentは自然終了コード、report、6段階置換trace、
token drift、fixture、source/runtime driftを検査する。失敗をpass/skipへ読み替えない。
control検査を通った場合だけ既存のexact-ledger cleanupを実施し、各削除の確認と所有handle closeを記録する。
cleanup途中で失敗した場合は停止し、削除済みfileの復旧や残存treeのrepairをしない。
部分削除の前のprivate snapshotと進捗は、既存ControlOutcomeにin-memoryで保持する。

合格条件はstatus=native_control_pass、control_status=pass、cleanup_status=completed、teardown_status=pass、
success_residue_count=0、固定child reportの期待操作・isolated/no_bytecode/no_impersonation・非継承確認。
これはB1 engineeringの実行証拠であり、S4/native受入・formal run・publisher/B2・本流統合の許可ではない。
既存のnative_accepted/s4_accepted/formal_permission/execution_authenticatedはfalseを維持する。

## 資源と終了

実行前にread-only preflightとtemp volumeの空きdisk1 GiB以上を確認する。
child waitは既存30秒、親＋childのpeak private bytesは512 MiB未満で検査し、timeout/資源停止時は既存の所有childだけをterminate/waitする。
この30秒はchild待機のdeadlineであり、起動準備・source/runtime検査・cleanup全体の厳密なwall-clock上限ではない。
API/各reader等の既存上限を維持し、全体時間を短く見せるためにparentを強制終了してchildを残すことはしない。
debug-event256件やRPM/Get/Set上限はこの非debug実行には適用せず、いずれのdebug APIも使用しない。

実行用wrapperはignored artifacts/context-offline-2026-09-10/detached-control-once.pyに準備する。
harnessの呼出しは1か所/1回、追加起動・自動再試行なし。
公開要約fileを先に新規openし、harnessが戻ったら最終statusをstdoutへ先に出力/flushする。
資源停止後は追加のfile書込み/走査/hash生成をせず、既に所有している結果を保持したまま終了する。
非資源停止時に安全な公開resultと、private control/replace証跡の長さ・hashを要約へ保存する。
private rawは一般log/fileへexportしない。cleanup snapshotを含むprivate objectは既存仕様どおりcallerのmemory内だけにあり、
公開hashの保存をprivate全体の永続保存と呼ばない。失敗fixtureを追加走査・削除しない。

## 検証状況と判断対象

関係PureWindowsControls 61/61 pass（0.215秒）。追加caseで0x40c、固定child/environment/cwd、制限tokenの受渡し、
非継承・標準handle未設定・suspended状態の出力と、その段階でResume/Terminate/Closeを呼ばないことを確認した。
wrapperは構文とharness呼出し1か所を確認済みで、実機未実行。全体回帰・独立レビュー・保存後preflightは追記する。

準備完了後、**この新規fixtureでの通常control harnessを1回実行すること**を提示する。
前回のreturn比較1回の承認は消化済み。今回は固定child内の操作と成功時cleanupまで進むため、新しい判断対象として扱う。


## 全体検証と独立レビュー

debug/preflight/event＋PureWindowsControls全体234/234 pass（2.074秒）、repository safety/diff-check pass。
独立差分レビュー新規P0〜P3=0、指定PureWindowsControls61/61 pass（0.173秒）。
core起動引数・制限維持、wrapperの1回呼出し/先行report/資源停止後の追加保存抑制・private raw非公開を確認した。
比較観測とE2E成功を分け、新しい実行範囲にchild操作と成功時exact-ledger cleanupを含む説明も確認した。
完了通知のみを利用し、進捗ポーリングなし。担当のwrapper/native実行/private証跡参照/source変更なし。

実行wrapperは3526 bytes / SHA-256 cae6a4ee47236fbfd8a9d024204105e5b4484e91b3154033ce2af18821f04c48。これは準備済みfileの識別であり、実行済みの証拠ではない。
wrapperは既存resource reasons/MemoryError由来の状態に加え、報告されたWindows資源errorでも追加保存/hashを抑止する。
PC空きRAM7.81→8.32 GiB、C107.93→107.94 GiB、D75.36 GiB。単発値からリーク有無は未判定。
mainは基準889cfc3のままclean。通常control harnessの実機は未実施。
