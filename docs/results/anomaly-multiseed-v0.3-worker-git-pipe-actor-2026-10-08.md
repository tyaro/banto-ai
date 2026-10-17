# Worker Git actor の opt-in pipe invocation

2026-10-08 JST。code `2213c0910390129158a0bd433bff94a786df8204`、branch `codex/preformal-acceptance-scope`。gate `s4_acceptance_not_frozen`、formal_permission=false、正式credit0、登録holdout観測未読。

## 接続した範囲

`WorkerGitActor(pipe_io=...)` は元kernel/stdin/shared clock/root identityを検証前に保持し、descriptorのdict/root identityをcopy固定する。defaultは既存file-directed `run_owned` のまま。caller-held request/policy/inventoryのexact次callから、同じcheckpointを持つ `GitSinkAdmission`、normal completionの `GitPipeTransport` へ渡す。

元clockでcall開始を保持し、exclusive sink→pipe/spawn→parent writer close→bounded step→Job open中のreceipt inputs→named IO/core close→receipt publisherの順で呼ぶ。pending step間は25ms sleep、IO/割込みは元transportのabortへ渡し、元Job/追加IO/stream/pending bufferを保持する。同期Peekとcaller step間のwall/停止保証は実証していない。

元returnを保持し、receipt/stdout/stderr/close witnessの原raw、専用archive保存readback、exact lease照合の後だけfinishする。正常receiptは後続callへ進め、正常readback済みの新inflight固定3fileとそのdirectoryだけ整理する。semantic failed receiptはfailed prefix/rawを保持して後続Git拒否。bootstrap/read/unknown close/publisher IO failureをreceipt成功へ読み替えない。

critical catchは元ChildGitKeeperを先に保持してoriginal/child/leaseを照合し、既存normal keeperのpromote latchへ渡す。新keeperでcached Job/creation/core close/pending publisher IOを置き換えない。keeperがない旧境界だけ既存constructorへ渡す。keep_ownerもsame original/child/lease必須。元pending receipt ownerがあるcached completionはlease/ackへ渡さない。既存terminal guardが同じcritical/keeperを報告や通常終了より先に保持する呼出し順を確認した。

## 新焦点と失敗の保全

raw: `artifacts/preformal-worker-git-pipe-actor-20261008-prep/`。

- 初回10件: 1pass/4fail/5error、1.0583848秒。参照fixtureのos置換にfstat/fsyncがなく、9件がsink作成途中で停止。全原logを保全。
- fixtureだけに実fstat/fsyncを渡して、失敗9件だけ再確認: 9pass/fail0/error0/skip0、3.6480686秒。初回passのroot identity拒否1件、旧suiteは反復0。
- distinct新10/最終unique10。最終source単一10success runではない。各39 source/science pin前後不変、test以外38pin両component一致、先行publisher共通35pin不変。変更2file safety findings0、clean code-save39working/Git一致。
- 正常archive/lease/cleanup、異なる元creationで2call継続、semantic failed prefix、unknown publisher closeとcached keeper/pending owner、read/sleep割込み、partial archive、Job前root拒否、descriptor copy、terminal保持の入口順を確認。

| 原証拠 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 12131 | e45f833b3a99139ee5ad88fda4e1a5288625008c9dd2278794128852d243d024 |
| focused.log | 19057 | 14e2a6f7a37975d293c8fe5c5bde41821dd71c021d0fbc8e58cd979dec189826 |
| focused-v2.json | 12128 | c2a9be380a68c0d1aeb04a6711739b508d2cda1426887d9f579b11d233a91ef5 |
| focused-v2.log | 2166 | fc525d9d21a4cdaefe9fd5d90a399161b42c7f6f4cc6d7ffce5897dcb2304543 |
| focused-components-final.json | 1069 | 3b7893191eb8934f6b17e0818dea3ee76d0599817cee562842bf097bc23610af |
| code-save-checkpoint.json | 6902 | bbb61c80cd685182c0cf13928a59e35a97e0907747395b45f5675055c864d5a3 |

focus43184/creation134358736442870686/tokend7bb48d3fc54bbba595039ac9a5ff78db38a216250e5af101c00a87d528e17dc、訂正46312/creation134358736909183019/tokenfae720d108ec8e94095d63767dd615bef129ae661072f18b7788c4b866711b31はexit1/0・CIM残存なし。PIDのみで同一process扱いしない。

## 限界と次の単位

fake Win API/Job/process/creation/policy/memory/executable＋実小FileIO/fsync/channel/archiveのprotocol gate。実Win ABI/exe/pipe/worker/native認証/容量合格ではない。元Python保持loopの永続性や実worker終了も実nativeで確認していない。新native0・追加agent0・全helper終了・critical ownerなし。新production module0、名前30source/各phase32要求/予定64Job維持だが完全runtime閉包ではない。

実reader entryからpipe_ioを発行・forwardする経路と、shared clock/root admissionを限定caller/元owner保持launcherへ結ぶ準備は未完了。ReaderGitParent.create_nativeのroot/channel/Job前拒否を維持する。次はその小さい受渡し境界と並行予約/coupled容量を確認し、最終clean HEADのfresh source/runtime/profile/policy/request/unusedrootをexclusive準備する。全7役whole.runを限定readerとして起動しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和/未測定rootへのreceipt移動/旧raw-root整理なし。0-job/途中成功prefix/未登録owner/未回収/poison archiveはack拒否。unknown Close/Delete/既存Unclosedは元owner/raw保全、blind retryなし。

## 同時に保存した先行CI

CI37666095841は外部fullHEAD `690af4900da6fc198ca7f389db2a61fe1374f602`/attempt1、3job success、各minor3481/fail0/error0/skip237/source不変。専用 `artifacts/ci-diagnostic-37666095841/` へ10raw/14pin/local-remote一致/共有29必須28/runner v2 consistent_candidateを保存。index2783B/73b589911219e3812abce12d8aa653be13e77140bf73b92b35f123b373c30fb9。全job20260927.320.1/公式外部pin一致、digest未取得/候補未採択。CLI7は6raw一致/skip1file既知CRLF6差を両pin保存。今回actor code/native/容量/正式受入の証拠に読み替えない。
