# v0.3 Git pipe read／原disk readback接続（2026-10-07）

code `43da351954ccc80af5ddc2d91b53027b80786bc3`、先行clean文書HEAD `140ad946aa3c98e09dbb70581a1f6ca60e085b82` からの小さいopt-in部品。通常file-directed executorは変更せず、`ReaderGitParent.create_native` のroot/channel/Job前拒否を維持。実pipe作成・spawn・追加IO close/release・receipt/witness・元root残余admissionは未接続で、新nativeは0。

## 接続した処理

- `GitPipeReader` を既存owned_git_job moduleへ追加、新production moduleは0。元GitOutputOwnerへreaderを検証/IOより前に保持し、kernel、原readback mapping/copy、元sink streams、先行readerを保持。元shared checkpointを使用する。
- 各readは元handle/最大4096B/保存残余のpendingを先に固定する。元diskを既存投入blockの全digest/countへ照合し、既存・改変sinkをpipe IO前に拒否。readbackの元returnも検証前にpendingへ保持する。
- `PeekNamedPipe` のavailable以下で `ReadFile` の要求量を固定。available/counter/buffer/API結果を原pendingへ保持し、原blockはspool IO前に保持する。API失敗・割込み・不明countでも原buffer/counter/native例外を捨てない。
- 元blockのexact write/flush/fsync後、disk全体のcount/digestと原checkpointを確認した後だけpendingを進める。partial write/readback不一致・IO/割込みは元owner/spool/error/rawをlatchし、native read・spool writeを再実行しない。
- 空availableと0バイト成功はpending。観測したbroken pipeだけをEOF記録にするが、sink/read handleは保持し、Job回収/lease/ack/追加IO解除を許可しない。上限内最後の検知byteまで保存したoutput_limitは以後両pipeのreadを拒否し、元Job停止は実callerへの次接続として残す。

0バイト成功がEOFを意味しないこととanonymous pipeのbroken pipe条件は [Microsoft ReadFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile) で確認した。[PeekNamedPipe](https://learn.microsoft.com/en-us/windows/win32/api/namedpipeapi/nf-namedpipeapi-peeknamedpipe) の同期handleは複数threadでblockする可能性がある。serial呼出adapterをworker全経路のnonblocking/wall保証へ読み替えず、実transport/停止接続と限定nativeで扱う。

## 焦点と保存

新13件を一回の最終source run、0.1539225秒、fail0/error0/skip0。exact available/4096、disk readback/prefix改変、空available/0バイト/broken pipe、Peek失敗、Read割込み/partial raw、partial sink write、検知byte、readback割込み、既存sinkの入口拒否を確認。kernel/native ownerはstub、sinkは小さい実file/fsync。実Win ABI/実pipe/Job/native認証/容量合格ではない。

33 source/science pinが試験前後不変、変更3fileのtarget safety pass、module unique13 discovery、clean code-save33 working/Git blob一致。先行IO owner12/spool12/旧suite/nativeは反復0、先行33pin中変更production2file以外の31pinも不変。名前30 source/各phase32要求/予定64Jobは維持するが、完全runtime閉包ではなくfresh profile/policy/request/unusedrootは未準備。旧HEAD/profile/pinを読み替えない。

raw: `artifacts/preformal-git-pipe-reader-20261007-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 10343 | `e04d6e19d86713f6f2a73922d54d58e68b322c450db798db28df89147ea925bc` |
| focused.log | 2636 | `dd8acf905ff7abd8548d6e3a19fb9c99d4e1a5cb96925f62ab891e2f250b8e93` |
| code-save-checkpoint.json | 576 | `8b03a43a90b27cb9fb68f58397581bf9ffb88c0a66216dae0d0b13054d799eb5` |

helper31484/creation134358555884446190/token0b497027b4f42efc099c4071e51434e76886534bddee77d01eca7d0d05a66ff9はexit0/CIM残存なし。全helper終了・critical ownerなし・追加agent0。

## 次の単位

原spawn/stdio cleanupへpipe/read handles/sink/write側streamの元owner保持を渡し、実transportをexclusive空sinkとexact callの元root残余bytes/entriesへ接続する。read結果の失敗rawも既存枠内に保持し、output_limitで元Jobを停止。元ChildGitKeeper.cached native終了/creation、元read handle EOF/close、sink/raw witnessを追加IO解除とreceipt/post-close verifierへ結ぶ。unknown Close/Delete/既存Unclosed/未回収では原Python owner/handle/stream/pending/inflight/partial archiveを保持、後続Git/workerを拒否する。

接続・拒否/停止保全とfresh exclusive準備が完成するまでnativeを開始しない。archive512KiB/outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和・未測定rootへのreceipt移動・旧raw/root整理はしない。先行全repository safety30秒timeoutは未確認として保全する。正式gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読、正式5残件/採択/最終受入は未完了。
