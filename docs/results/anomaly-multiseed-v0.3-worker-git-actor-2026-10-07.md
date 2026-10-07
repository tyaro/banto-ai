# v0.3 worker Git actor境界の保存（2026-10-07）

code `f0ecd8942432811120a2c82145cecf89822650ff`。正式gate `s4_acceptance_not_frozen`、formal_permission=false、正式credit0、登録holdout観測未読。実データ範囲は保存済み合成dev8/smoke2のengineering読取り・記述報告のみ。

## 接続した境界

- opt-in `WorkerGitActor.call` はcaller-held request/policy/revision/root/inventoryを再照合し、exact phase/operation/source/output pin、次lease、専用未使用inflight rootを固定。原 `run_owned` にprivate Job policy、capture_quiescence=True、共有stop probe、元10秒を渡す。
- 原returnを診断前に保持し、原receipt/stdout/stderrとpost-close witnessを再読取り。専用worker archive/resolverの保存readback後だけexact leaseを完了する。成功後は新inflightの固定3fileを個別整理し、既存raw/rootを整理しない。失敗receiptは原rawを残し新Gitを拒否する。
- UnreapedJob/UnclosedHandlesはchild ledger IOより前に元ownerをactorへ保持し、元例外をそのまま再送出。`keep_owner` は同じChildGitKeeperへPython保持を委ね、回収済みoriginal eventと原失敗rawを保存・再読取り後だけleaseを完了する。archive/ledger失敗をlatchし、後続callbackはappend/native closeを反復しない。unknown close/Delete/既存Unclosedは保全のまま。
- storage、close、creation、実executor factsはfake APIのprotocol試験。実worker入口はまだこのactorを呼ばず、Parent create/bind/fence、Child binding wait、終端catchからkeep_ownerへ入る経路、0-job/部分ackは未接続。新native0・追加agent0・全helper終了・critical ownerなし。実exe/Win ABI/runtime閉包/容量合格を示さない。

## 焦点試験と失敗の保全

初回helperはcreation_observationのimport先、次のhelperはdiscovery期待数14（実際13）で試験開始前に停止。各tests_started=0の失敗を別保存した。実13件gateは12 pass・1 error/2.257016秒。2call fixtureが最初のreturn identityを共有更新したため、actorが原raw不一致を拒否した。test helperのreturnをdeep copyへ訂正し、その1件だけ0.519830秒でpass。distinct新13件、他12件反復0、初回13件を最終sourceの単一13件success runへ読み替えない。

初回と訂正1件の各20 source/science pinは実行前後不変。変更test以外の選択19 pinは両runで一致。変更2file safety、最終unique13 discovery、clean code-save20 working/Git pin一致を確認。先行archive16/proof18等は反復0。先行全repository safety30秒timeoutは未確認のまま、再試行しない。

raw: `artifacts/preformal-worker-git-actor-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json（初回12 pass/1 error） | 8338 | `ca70a0dc6499d3dad2f4e22c48f6c2b2368c8a489cdf6138b55dd1d6c187eeae` |
| focused-corrected-one.json | 6763 | `5014dcb16b4d3dfd112c9a3b940f665d4358c89ff4c1cea298fd8bbb559f58ee` |
| focused-components-final.json | 5397 | `279a0170e2d3496686813c361ca21b4222446f09c0082624f1270bdbaaaf564f` |
| code-save-checkpoint.json | 584 | `f092ce9298e72d24b89c2ec0827096cf6d1e58dad2b992f16160eefa6767086f` |

helperはdiscovery失敗PID44296/creation134358395420321977、実13件PID10052/creation134358395730034610、訂正1件PID35320/creation134358396028699301。各元tokenはlive-helper各rawへ保存、tool exit1/1/0とCIM残存なしを照合。PIDだけで同一process扱いしない。

## 次の保存単位

入口接続前に0-job/部分ackの未完了範囲と、元Popen/子Job keeperをPython終端で失わない実catch経路を固定する。その後Parent.create/on_started bind/fence、Child wait/actor/probe/keeperを実invocationへ渡す。実importを含むsource/runtime inventoryを新revisionで準備し、旧14/14や古いpinを流用しない。producer pre26/post24を親111/111へ渡さない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB/32entry/depth2/reserve128KiB、全体321MiB/672entry、cleanup30秒/poll0.25秒を保持。control完成4+pending4、proof/pending、caller inventory/manifest、archive、inflight/失敗raw/partial archiveを測定rootへ計上する。共通予算は現在caller supplied checkpointで、専用exclusive準備/拒否/停止保全と実入口が完成するまでnativeを開始しない。上限緩和・未測定rootへの移動・旧使用済み親rootへの追加なし。

先行fixture修正CI37596406096は外部HEAD9473523に限定して両minor3247/fail0/error0/skip237/source不変・全3job success、10raw/14pin・local/remote回帰一致・共有29/必須28・runner v2 consistent_candidateを保存した。詳細は[CI保存](anomaly-multiseed-v0.3-worker-stop-boundary-ci-save-2026-10-07.md)。未保存CIは37598762191（HEADba6f82e/3263予定）と新37602415125（HEADf0ecd89/3276予定）。runner digest未取得・候補未採択、正式採択・最終受入・正式5残件は未完了。
