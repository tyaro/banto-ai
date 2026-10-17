# v0.3 Git exclusive sink／outer leaf admission（2026-10-08）

code `8eba6cfa9dd3fcf633e314908327f7449fe8a9d0`。clean文書HEAD `72f106d9b81e67be597d9c8195169b9a053adb10` からの小さいopt-in単位。

## 保存した境界

- `GitSinkAdmission` は元root/root identity/revision/call/checkpointを保持し、検証前にbootstrap UnreapedJobへ結ぶ。call/root identityはcopyしてcallerの後変更に追随しない。phase/lease/operation/source/expected pin/raw inventoryをclosed fieldで確認する。
- 元shared checkpointを呼び、既存`_directory_snapshot(root,32,2,identity)`で実在庫を同期計測する。現在bytesに未保存rawの全最大値と128KiB reserveを足し1MiB以内、現在entriesに将来raw files/未作成inflight directoryと診断2entryを足し32以内の場合だけ作成へ進む。receipt/partial archiveも保守的に予約し、stdoutの失敗保存capを正常source pinのbytesから推定しない。partial archiveが既存archiveと同じ内容でもこの部品はdedupや予約消費の扱いをしない。
- 固定`worker-git-inflight`をexclusiveで作り、stdout.bin/stderr.binを元FileIOでexclusive空fileとして作る。返った原streamをfstat/checkpointより前に保持し、file identity/size/closefd=trueを確認する。FileIOのx modeは既存fileを拒否し、pathから開く場合はclosefd=trueで所有する。[Python FileIO仕様](https://docs.python.org/3/library/io.html#io.FileIO)
- 元streamを既存BoundedGitSpoolへ渡し、保存枠内の最後の検知byte／最大4096B／exact write/flush/fsync／元checkpointを維持する。各checkpointで元fdとpathのidentity/count、残余予約を確認する。後からrootが増えて枠外になればwrite前に拒否する。
- invalid cap/root/call、第二sink作成失敗、IO/割込み、root/file差替え・枠外では元stream／partial raw／pending／元errorをbootstrap ownerへ保持し、同じ原例外を再送出する。後続create/再openを拒否し、blind close／旧raw整理をしない。

これは実小FileIO/fsync/root計測とstub shared clock/checkpointによる部品gate。Job/pipe/process起動0。元native Jobへのsink owner受渡し、実executor、出力limitで元Job停止、receipt/post-close witness publisher、worker呼出しは未接続で、`ReaderGitParent.create_native`のroot/channel/Job前拒否を維持する。bootstrap／EOF／閉じたstreamをlease/ackにしない。閉じたstreamのcheckpointは未確認として拒否し、実close後のadmission再照合には元named close/raw witnessとの接続が必要。

同期計測と保守的予約の部品であり、並行parent/child書込みのatomic予約やcoupled peakを保証しない。FileIO/pipeの全経路wall、実Win ABI、exe/worker、native認証、全4root/global/memory/容量合格ではない。親の既存clock/sampler/global budgetの代用にしない。

## 焦点と保存

新12件を一回の最終source run、0.0762106秒、fail0/error0/skip0。exclusive空FileIO/call cap/copy、generic失敗stdout1MiB要求の作成前拒否、実既存bytes/reserve/entries/future raw計上、旧inflight不変、第二file失敗と再試行拒否、post-open割込みの元stream保持、枠内最後byte、後続root増加でwrite前拒否、実root差替え、bool cap拒否を確認した。

33 source/science pin前後不変、先行pipe作成gateの共通32pinのうち変更owned_git_job以外31pin不変。変更2file target safety／最終unique12／clean code-save33working-Git一致。旧suite/native/profile再観測反復0、追加agent0、全helper終了／critical ownerなし。新production module0／名前30source／各phase32要求／予定64Jobを維持するが完全runtime閉包ではなく、fresh source/profile/policy/request/unusedroot未準備。

raw: `artifacts/preformal-git-sink-admission-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 10438 | `1b0f12cf9f0a2422f852c1bc3325f8a2a9bacba007fca5a90bd9f5be1b04e779` |
| focused.log | 2357 | `be105094b3fba03a841ba4fbc2d5699ab9e176a4932fc18b6a9e93becffa1ef7` |
| code-save-checkpoint.json | 374 | `12112767db0ff7bdc302ee7138be8fcea8dd922c9af78995afdb1b47cb966daf` |

helper25272/creation134358650299164087/tokenbbf79194c88ee6898d64b4f08dd3f261c783f4fdc664fbe7365c1199586932f0 はexit0/CIM残存なし。元identity/tokenはlive/executionへ保存、PID単独で過去processと同一扱いしない。

## 次の単位

元pipe creator／SpawnIOOwnerと本admissionの元stream・spool・bootstrapを同じoriginal nativeへ結び、実transportのstop/reapを保持する小さい単位を進める。close後は原named close/raw witnessへ結んで再照合し、metadataだけで閉じたfdを解決済み扱いしない。output_limit時は元Job停止へ渡し、未回収・unknown Close/Delete・既存Unclosed・IO/割込みで原Popen/Job/process/thread/extra handle/Python owner/stream/pending/inflight/partial archiveを保持して後続Git/workerを拒否する。同期Peekのwall/停止、parent/child予約と実packet/rawのcoupled容量、限定caller／元owner保持launcherは未実証のまま。

最新clean HEADのfresh source/runtime/profile/policy/request/unusedrootとexclusive準備が完成するまでnative入口を開かず、全7役whole.runを限定readerとして起動しない。旧14source/profile/pin、producer pre26/post24を親111/111へ流用しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理なし。正常readback済み新inflight固定3fileと新directoryだけ整理可能。旧正常モデル786782B/31entryを新request/codecapへ読み替えず、generic失敗1MiBの旧reader1704030B>reserve後917504Bも保全する。

formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。先行全repository safety30秒timeoutは未確認保全・再試行なし。実ロード依存／業務異常子孫／正式5残件／正式採択／最終受入は未完了。
