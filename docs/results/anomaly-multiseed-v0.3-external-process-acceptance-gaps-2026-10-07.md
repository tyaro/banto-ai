# v0.3 外部program・異常時子孫回収の受入残件（2026-10-07）

最新CI修正: [spawn cleanup portable fixture](anomaly-multiseed-v0.3-spawn-cleanup-portable-ci-fix-2026-10-07.md)を9473523へ保存。CI f0b3d72はLinuxにctypes.get_last_errorがなく各minor fail1/error1、7rawを保全。testだけ1行stub、欠落状態で失敗2件のみpass・10pin/test safety/code-save照合、先行proof16pin不変。新native0・業務source変更0。専用worker archive/resolverは失敗修正を先に行ったため未実装、次段階の境界と上限は保持。以下は先行保存点の履歴。

最新CI追補: [子keeper8faa921のCI](anomaly-multiseed-v0.3-worker-stop-boundary-ci-save-2026-10-07.md)は両minor3220・10raw/14pin/local回帰/runner v2まで保存。新native0。実worker前の境界では旧parent archiveがverified source_blob専用でclose/identity/failed rawを扱わないことを選択source3/7da5aa9で確認。専用worker archive/resolver→0-job/部分ackと終端keeper→実entry/profile準備を小さい単位にする。旧archive/親nativeを流用せず、正式5残件と上限を保持。以下は先行保存点の履歴。

最新追補: [compact Git proof/verified lease部品](anomaly-multiseed-v0.3-worker-git-compact-proof-2026-10-07.md)をcode18324bf（新18焦点）とdiscovery修正7da5aa9（unique18/実試験再実行0）へ保存。正常/failed receipt、exact keeper recoveryと原raw/closeを区別してlease/parent fenceへ渡す。未解決cleanup/Unclosed/IO/改変は原owner/raw保全。初版CI実試験前RuntimeErrorを5rawで保全、修正後CIは別run。実worker/shared probe/archive reader/entryは未接続・新native0。次は実actorと原raw reader/終端keeperを入口へ結び、新inventory/root準備に進む。以下は先行保存点の履歴。

最新追補: [spawn attribute/stdio原owner保全](anomaly-multiseed-v0.3-spawn-cleanup-owner-2026-10-07.md)をcodef0b3d72へ保存。新9焦点/14 pin・変更3file safety・clean code-save pass。Delete/Close例外で元core/extra/buffer/両例外を保全し、keeperのnative root停止後も不明cleanupを再実行しない。protocol stub/native0、実entry/probe/compact proof/leaseは未接続。次はrequest/policy/root/call inventory＋raw pinのproofとlease/fence Trueを結び、unknown cleanupは保全に留める。CIe5ffは3191/全3job success・10raw/14pin・runner v2候補照合まで保存済み。以下は先行保存点の履歴。

最新追補: [子Git keeper/reap保全](anomaly-multiseed-v0.3-child-git-keeper-2026-10-07.md)をcode8faa921へ保存。新13焦点/14 pin・変更4file safety・clean code-save pass。元native ownerをreap/診断前に保持し、既存5秒cleanup/native creation/原named handle回収とledger/marker/sleep保全を接続。protocol stub/native0、実entry/probe/compact proof/failure raw/lease完了は未接続。次はspawn attribute/stdio cleanup例外の原owner保全、compact proof/lease、実entry/profile再準備の順。既存Unclosed/不明closeの未解決保全をackにしない。CIaacaは3178/全3job success・10raw/14pin・runner v2候補一致まで保存済み。以下は先行保存点の履歴。

最新追補: [receipt/post-close quiescence](anomaly-multiseed-v0.3-git-quiescence-post-close-2026-10-07.md)をcode3016448へ保存。新16焦点/13 pin・変更4file safety・clean code-save pass。原handleをclose/診断前に保持し、実post-close eventをreceipt/native creation/exit/accountingへ結ぶ。公開verifierは全retained raw/output/policy＋close witnessを照合。protocol stub/native0、channel compact proof・子keeper・worker actorは未接続。次はreap fallbackの元owner保持→child keeper→shared stop/lease/compact proofを先に結び、実invocation/新inventory/profile準備へ進む。以下は先行保存点の履歴。

最新追補: [channel v2部分公開/startup保全](anomaly-multiseed-v0.3-worker-stop-channel-publication-2026-10-07.md)をcodee5ff975へ保存。新13焦点/11 pin・変更2file safety・clean code-save pass、先行21/17反復0。pendingを同root内でraw照合→上書き禁止rename、bind前IO失敗でも元Popen保持、partial stop/startup割込みで無再arm。実worker/子keeper/実proof verifierは未接続・新native0。CIe4cb/01abは[10raw/14pin・runner v2照合](anomaly-multiseed-v0.3-worker-stop-boundary-ci-save-2026-10-07.md)まで完了。次は実Job receipt/close/失敗rawのproofと原owner keeperを先に結び、invocation接続後に新source/profile準備する。以下は先行各保存点の履歴。

最新channel契約: [共有clock/stop/ack metadata](anomaly-multiseed-v0.3-worker-stop-channel-2026-10-07.md)をcodeaaca57cへ保存。21焦点/9 pin・変更2file safety pass。caller pin・root/creation identity・deadline・no-new-work・必須quiescence verifierを固定し、marker不在/単なるroot exitをTrueにしない。実worker invocation/Job probe/子keeper/native証拠verifierは未接続、新native0。

最新owner境界: [親supervisor stop fence](anomaly-multiseed-v0.3-worker-stop-fence-2026-10-07.md)をcode01ab74fへ保存。17焦点/9 pin・変更2file safety pass。未確認時は元worker/Popen/handleとfenceを保持し、kill/wait/close/final contextに進まない。True後のwait未確認・close失敗もguarded ownerとして保持する。共有stop/ack・worker invocation・子Job keeper/actorは未接続、新native0。

最新callback境界: [producer/initial-reader](anomaly-multiseed-v0.3-worker-source-callback-boundary-2026-10-07.md)をcode e4cb23aへ保存。24 distinct実試験・7 pin・変更3file safety pass、全repository safetyは30秒timeoutで未確認。workerへのpolicy/共有stop/keeper/actorは未接続、新native0。producer pre26/post24とinitial-reader14/14の在庫を固定し、次はinitial-reader小actorのowner終端・共有stop接続。

最新native: [親blob/identity共通予算](anomaly-multiseed-v0.3-parent-git-blob-budget-native-2026-10-07.md)をclean d57326e（code9c49c4a）で一回実測。67 source・134 blob＋4 identity Jobはexit0/active0、pre/post pin一致、30.874/90秒、保存checker v2 pass、sampler/helper終了。archive520,852 Bで512 KiB残余3,436 B。CI9af/1159も保存照合済み、CI9cは未完了。worker内Git・実ロード依存・業務異常子孫・正式5残件は継続。以下の未開始表記は先行source/部品unit時点の保存履歴。

最新: [親blob actor接続](anomaly-multiseed-v0.3-parent-git-blob-actor-2026-10-07.md)をcode9c49c4aに保存。45焦点/11 pin/safety pass、元Job/shared stop/phase cache/失敗raw保全と実callerpre/post gate、compact64 KiB indexを接続。正常時の新inflight3fileだけの整理を確認。67 source/134 blob＋4 identityの限定nativeは未開始、critical keeper付きlauncherが次の単位。

最新追補: [bounded archive部品](anomaly-multiseed-v0.3-git-receipt-archive-component-2026-10-07.md)をcode1159b9aへ保存。54焦点・10 pin・safety pass、synthetic130 receipt/88 cache hit/65 stdoutの保存protocol fixtureは472,003 B。production Job/shared budget/元handle接続は次の単位、限定native未実施。srcに加えて現在実callerの5toolだけを明示許可する。正式5残件は維持。

次の追補: [親blob読取り境界](anomaly-multiseed-v0.3-parent-source-blob-callback-boundary-2026-10-07.md)をcode9af4a96に追加し、47焦点/9 pin/safety・65 selected保存source照合がpass。production Job/compact receiptは未接続。静的在庫は218 blob call、従来receipt890 entry、unique source1,109,815 Bでouter32 entry/1 MiBを超える。上限を保持した集約保存が次の単位。CI37568898031は進行中、新native0。

再開後の追補: [親HEAD/cleanの4 Git Job](anomaly-multiseed-v0.3-parent-git-identity-budget-native-2026-10-07.md)をcode9ddaed7で共通予算へ接続し、74焦点試験・clean限定native・別保存checkerがpass。親blob/worker内Git・実ロード依存・業務異常子孫は残る。以下は先行source監査時点の保存記録。

## 保存範囲

clean `6f1270f05614e7127ecdd876da77dcc1805c1858` とnative code `343c8639b0acfb2be535c02b5aaf4288b8f3d43e` の選択15 sourceについて、working rawと両Git blobが一致することを確認した。保存した[静的source監査](../../artifacts/preformal-external-process-gap-audit-20261007/source-gap-audit.json)は5,938 B / SHA-256 `1624adfb0966372c1e9441d79ab1a625e5990f0cfbdb621f1a4cfcd2049aa3cf`。ASTで位置を記録した裸のGit呼出し構文は16箇所で、実行回数や全source閉包の数ではない。

新しいnative・業務worker・追加agentは0。登録holdout観測未読、正式credit0、`s4_acceptance_not_frozen`、`formal_permission=false`。全7役r7の成功終了・14phaseと独立保存checkerは保全し、今回はsourceの残件のみ整理した。

## 実経路と残件

| 境界 | 保存sourceで確認した事実 | 残る受入証拠 |
| --- | --- | --- |
| producer / initial-reader / saved-reader / writer / fresh reader | [直接supervisor](../../src/banto_ai/anomaly_v03_process_supervisor.py)のPopen・元handle、stop時kill、wait、未回収時の所有権保全。生成と公開の実入口から使用する。 | private Job等により、異常時の業務子孫を停止し、root exitと対象tree終了を確認する実経路の証拠。直接worker終了だけで子孫終了を判定しない。 |
| analysis / audit | [実draw bridge](../../src/banto_ai/anomaly_v03_preformal_bound_draw_bridge.py)の `_supervise` が直接Popen、元handle在庫、kill/wait、未回収時に `UnreapedMeasurement` を保持。 | 2役と各外部helperの異常終了・time/memory/output停止を、同じouter budgetとtree回収へ結ぶ。 |
| source境界のGit | [generator](../../src/banto_ai/anomaly_v03_preformal_owned_generated_attempt.py)、[initial-reader](../../src/banto_ai/anomaly_v03_preformal_owned_saved_attempt.py)、[saved-reader](../../src/banto_ai/anomaly_v03_preformal_saved_row_reread.py)、common/document/draw側の選択source比較に `check_output(['git', ...], timeout=10)` が残る。 | caller保持の絶対exe path・raw pin・環境・元handle・入力出力・終了を、実際に使う各境界へ結ぶ。外部program/helperの実ロード依存も別途照合する。 |
| 7役runtime在庫 | [runtime observer](../../src/banto_ai/anomaly_v03_role_runtime_observation.py)の前後stdlib・import/native/cache在庫。親post-exitはcaller source manifestを使用し、fresh Gitを起動しない。 | 外部programのロード、途中だけの依存と異常子孫は、この候補の認証範囲外。境界在庫の成功を全runtime閉包へ読み替えない。 |
| 既存Git Job prototype | [owned Git](../../src/banto_ai/anomaly_v03_preformal_owned_git.py)にexe/PATH・links・環境の外部pin、[Git Job](../../src/banto_ai/anomaly_v03_preformal_owned_git_job.py)にsuspended起動/assign/resume、TerminateJobObject・active_processes=0・root exit・未確認handle保全がある。 | [five-role parent-owned v7](../../src/banto_ai/anomaly_v03_preformal_five_role_parent_owned_git.py)はcandidate profileを拒否し、今回の全7役callerと接続されていない。Gitの実ロードcode・全外部helper閉包も未認証。 |

prototypeの全統合を追加必須にしない。再利用する機構は最終経路の必要な境界を選び、既存限界と外部pinを保持して採択前の限定試験へ結ぶ。

## 次の小さい実装単位

1. 実callerとworkerのGit使用境界を外部program policyへ結ぶ。絶対exe/raw pin、許可argv・環境、source full revisionと要求出力pin、元process handle、exclusive stdout/stderr/receiptを入力として固定する。各10秒の既存上限と共通時計・資源・log上限を維持する。
2. 起動前にprivate Jobへ所有させ、rootと対象業務子孫のexit/reap・accounting終了を確認する停止経路を、7役の実入口へ結ぶ。未確認時は元Job/process/thread handleとrawを保持し、成功扱い・次worker開始を拒否する。
3. 実際に使うGit・helper・DLL/CRTを外部期待pinへ照合する。在庫の採取箇所と、親確認・子実行・終了後確認の担当を版付き契約へ固定する。exe本体のpinだけでロード依存を認証済みにしない。
4. 新しい限定試験はpin/role/root/identityの差替え、起動・accounting観測失敗、root先行終了、子孫残存、time/memory/output停止、未回収handle保持、停止後のworker起動拒否を対象にする。今回この異常fixtureは実行していない。既存の全工程nativeは反復しない。

保証A/B・26H2・runner同定の改訂採択、正式登録入力consumer、最終同revisionのLinux/Windows・dev8/smoke2・独立受入、正式共通予算と容量2倍は、[証拠索引の5残件](anomaly-multiseed-v0.3-preformal-evidence-index-2026-10-07.md)に残る。

CI37547050883（HEAD21d3866）とCI37548282365（HEAD6f1270f）は監査開始時進行中。完成したrawを各HEADへ固定して保存・runner v2照合する。文書だけの保存は新しいCIを起動せず、この2件の追跡を継続する。
