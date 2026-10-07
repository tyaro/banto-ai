# v0.3 Git pipe作成／元spawn ownerへの受渡し（2026-10-08）

code `6a77b8ef764ff97a4ed929ed2616b2ef6bca8c4a`。clean文書HEAD `1df3f4c585c5a1e561f5f31a7883cea4ee3c952e` からの小さいopt-in単位。

## 保存した境界

- `NativeGitPipes` は元kernel/checkpoint、bootstrapの元UnreapedJob、CreatePipeのread/write出力bufferを最初のIOより前に保持する。stdout/stderrを順に作り、native returnと原出力値を検証・post checkpointより前に保持する。成功した4handleの正値・相互aliasを確認し、write側をfdへ変換せず元NativePipeWriterへ固定する。
- APIがFalseまたは例外・割込みの場合は元error／output buffer／先行成功pairを保持して元ownerを再送出する。失敗したCreatePipeの出力はindeterminateのまま保持し、値が正でもCloseHandle対象へ読み替えない。再create／blind closeをしない。[Microsoft CreatePipe契約](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createpipe) を確認した。
- NULL security attributesによる非継承pipeを元SpawnIOOwnerの明示DuplicateHandleへ渡す。4096Bのbuffer hintはkernel bufferのhard boundではない。[同APIの説明](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-createpipe) に従う。
- `bind_spawn` は原sink mappingをcopy/検証より前に保持し、同じ原creator／kernel／read handles／write objectsを元SpawnIOOwner/nativeへ結ぶ。再bind・foreign kernelをJob/process IOより前に拒否し、先行descriptorと拒否した資源も保持する。bind後の失敗は同じ原spawn nativeへ保持し、bootstrapからsuccessorへの参照も残す。
- `_kernel` へCreatePipeの型を追加した。通常の追加IOなしspawn／file-directed executorは既定経路を維持する。

本単位はfake Win API／Job／processによるprotocol gate。実CreatePipe、Win ABI、pipe、実exe、worker、全経路wall・容量合格、native認証は未確認。exclusive空FileIO sink／exact callの元shared root残余bytes・entries／失敗raw保存枠／実executor／pipe receipt publisherは未接続。`ReaderGitParent.create_native` はroot/channel/Job作成前の拒否を維持する。bootstrap ownerやEOFを0-job proof／回収済みackへ読み替えない。

## 焦点と保存

新12件を一回の最終source run、0.0101876秒、fail0/error0/skip0。原API出力/cache、非継承とbuffer hint、1番目/2番目Falseとindeterminate出力保全、API割込み／pre-post clock失敗、handle alias、原writer Duplicate、foreign kernelのJob前拒否、再bindの資源保持、invalid checkpointを確認した。参照fixtureはmodule参照とfake setupのみで、旧suiteを実行・重複discoveryしない。

35 source/science pin前後不変、先行close linkの共通34pinのうち変更tree owner以外33pin不変、変更2file target safety／unique12／clean code-save35working-Git一致。新production module0、選択30source／各phase32要求／予定64Jobの名前は維持。選択在庫は完全runtime閉包ではなく、最大source53955Bもcapではない。fresh source/runtime/profile/policy/request/unusedrootは未準備で、旧revision／profile／pinを流用しない。

raw: `artifacts/preformal-native-git-pipes-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 10990 | `66ba497de7ce94fbd0353edf9472db34b6174562a449aa01445e2c41e8539691` |
| focused.log | 2655 | `50084baf84a69cb6a3e03edc1637d3596aa0aab12de6b7eb849040b17737647b` |
| code-save-checkpoint.json | 374 | `21435510634616866793f271f2cdb857d0881bef820750de97bc9dab46f1b467` |

helper19340/creation134358634208959515/tokenbd68a9aff14a6f8afc097264b34f392c44c3240a64b3f938c0d34b67f044832e はexit0/CIM残存なし。元identity/tokenをlive/executionへ保存。全helper終了／critical ownerなし／native0／追加agent0、完成焦点・native・profile再観測の反復0。

## 次の単位と受入状態

exclusive空FileIO sinkをIO前保持し、exact callと元shared root identity／残余bytes・entries／reserveへ保存枠・最後の検知byteを結ぶ小さいadmissionを固定する。原spawn/output/reader/close/keeperへの実transport、output_limit時の元Job停止、原returnからのpipe receipt witness publisherはその後に接続する。未回収・unknown Close/Delete・既存Unclosed・診断/IO/割込みでは原Popen/Job/process/thread/extra handle/Python owner/stream/buffer/pending/inflight/partial archiveを保持して後続Git/workerを拒否し、blind retryやPython終了へ落とさない。

同期Peekのwall／停止保証、実control/packet/rawのcoupled容量、限定reader caller／元owner保持launcherと最新clean HEADのexclusive準備が完成するまでnative入口を開かない。全7役whole.runを限定readerとして起動しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理なし。正常readback済み新inflight固定3fileと新directoryだけ整理可能。旧正常容量モデル786782B/31entry、generic失敗stdout1MiBのreader1704030B>reserve後917504Bを新cap/requestへ読み替えない。

formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。実ロード依存／業務異常子孫／正式5残件／正式採択／最終受入は未完了。先行全repository safety30秒timeoutは未確認保全・再試行なし。
