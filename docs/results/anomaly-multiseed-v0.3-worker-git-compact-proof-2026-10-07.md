# v0.3 worker Git compact proof／verified lease部品（2026-10-07）

部品code `18324bf9e4b9f183e2b2b8d42d7c3bfdbe3f1145`、test fixtureのmodule参照修正code `7da5aa92b007965b3a51fd94afb73d6add67d3c3`。gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## この単位

ProofVerifierはcallerが別に保持したcanonical inventory raw/pin（32 KiB以下・64 call以下）をchannel request/policy pin・revision・root identity・repository・phase・正確なoperation/source/output pinと固定raw inventoryへ結ぶ。compact proofにはlease/kind/evidence pinを保存し、原raw readerでreceipt/stdout/stderr・post-close witnessまたはrecovery observation・partial archiveを再読取りして照合する。完成全call、または最後がfailedの停止prefixだけを認め、count・元creation identity重複・raw差替え・外部policy差を拒否する。proof自体は32 KiB以下。raw上限は既存receipt16 KiB/stderr64 KiB/operation stdout上限とpartial archive512 KiB以下から選択し、caller inventoryで狭める。正式容量の上限や合格は変更しない。

VerifiedLeasesは元keeperをraw読取り前に保持し、正常/failed receiptには全raw＋実executorのpost-close link、recoveryには同じChildGitKeeper/original/lease・全原handle close・empty/creation・cached completionと失敗raw全pinの一致を必須にする。rawを再照合した後だけfinish_jobへ渡す。failed receipt/recoveryは新Jobを止め、failedのまま親fence用proofへ結ぶ。keeperの元observationのlease/raw/ack flagsはfalseのまま保全する。unknown attribute/close・既存Unclosed・未回収ownerはrelease/ackしない。診断/readback/ledger/保存割込みはadapter・元keeper・rawを保持して新Jobを拒否する。原rawの削除やreceipt移動、native API再実行はない。

ChildChannel.finish_jobの既定metadata APIは互換のまま、このadapterはopt-in部品。実worker/actor/archive reader/共通Job probe/実entryへのParent.bind/fenceとChild wait/keeperは未接続。evidence readerは原保存bytesを解決する契約で、今回fake Kernel/executable/creationとfixture rawにより検証した。raw/close宣言の整合性は実worker・実exe・実Win ABI・native認証・容量合格を証明しない。元ownerを持つPythonの終了保全を実entryまで通す作業は残る。

## 焦点とdiscovery修正

部品18324bfで新18試験 / 8.703312秒、fail0/error0/skip0。正常/failed receipt→lease→ack→実ParentChannel.fenceのcode経路、exact keeper回収とpartial raw保全、未知cleanup/Unclosed/偽recovery拒否、raw欠落/改変/上限/二度目読取り差、IO/割込み、ack保存失敗、failed prefix、全planned call必須、元identity重複拒否を確認した。64 distinct saved callのcompact proofは32 KiB内で、当該fixtureのfake executorは1回のみ。新native0、旧keeper13/post-close16/channel21/fence17/publication13/spawn9の試験反復0。

選択16 source/test/science pin前後不変、変更2file safety pass、code-save HEAD=origin/clean・16 working/Git一致。code保存後、test moduleにimportした旧TestCaseがdiscoveryに含まれ34件になる問題を検出。7da5aa9でfixtureをmodule参照へ修正し、unique新18件だけをdiscoverすること、他15 pin不変・変更test safety・16 working/Git pinを確認した。修正後は試験実行0、初回18件を最終source同一の新18件runへ読み替えない。

初版CI37592461789（HEAD18324bf）は両minorが実試験開始前RuntimeError、compare skipped。run/jobs/failed log/2journalを `artifacts/ci-diagnostic-37592461789/` に保全、各journalのtest_started=0。local duplicate discoveryの34→18修正を別に記録し、旧CIをsuccessにしない。修正後CI37592838738（HEAD7da5aa9、各minor3247予定）は進行中。

raw: `artifacts/preformal-worker-git-proof-20261007-prep/`。焦点helper PID38812、creation134358343886102391/token57add0378993f73d0ff704b9dfefd5fb94f7734c2c2a7ae24d52a3ccc233efdeはexit0・終了確認済み。追加agent0・critical ownerなし。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 5397 | `0fb5bbc29339a2549326c97463eddc806bc15ddff5b3828019b8b3b2080f2b24` |
| focused.log | 3799 | `975daba6c20395521a835fae39c1f4853146ff14cd0675e2ca49b572c2dd2524` |
| code-save-checkpoint.json | 596 | `91f358d7719ca505cc65ca76863dca8c5298589b5c229c92333195ed3dfdd4f5` |
| module-discovery-final.json | 5172 | `61ebd6651552ead0d5a2f05a9057cd1dc22b884b69bf932b36f913e5a68aafa1` |
| discovery-code-save-checkpoint.json | 501 | `723893d481d3beb3a89e8dcf7c4ce4cc02c803e0860c5dcfd314b3a5b9f1e41b` |

## 次の小さい単位

保存済み正常receipt/recovery eventを原raw readerで解決する実actor/archive境界、stop probeとlease開始、例外時keeperのPython終端保全を実invocationへ結ぶ。Parent.create/on_started bind/fence、Child wait/probe/keeper/proofを入口へ渡し、実importを含めsource/runtime profileを新revisionで準備する。旧14/14やproducer pre26/post24を読み替えず、親111/111へ流用しない。起動前失敗の0-job proofや部分ackの再照合はこの部品では許可せず保全に留め、入口接続時に範囲を固定する。

control完成4＋pending4、git-proof.jsonとそのpending、caller-held inventory、inflight/失敗raw/partial archiveを測定rootへ計上する。現outer1 MiB/32 entry/depth2/reserve128 KiB・全体321 MiB/672 entryを保持し、接続/拒否/停止保全と新exclusive準備が完成するまで新nativeは開始しない。旧親archive残余3436 Bの使用済みrootへ追加/再起動しない。全repository safetyは先行e4cb30秒timeoutの未確認を保持し再試行しない。実ロード依存・業務異常子孫と正式5残件は別単位。
