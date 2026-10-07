# Reader入口への借用pipe IO受渡し

2026-10-08 JST。code `f5ff80eb1345cacf108278514161cf957fb91238`、branch `codex/preformal-acceptance-scope`。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## 保存した接続

`reader_worker_main(argv, pipe_io=...)` はcallerの元kernel/stdinをparse/診断より先に保持しdictをcopyする。JSONへnative objectを入れず、exact worker Git entryとfresh runtime profileがある場合だけReaderGitWorkerへopt-in keywordを渡す。defaultでは新keywordを渡さず、通常callback-free経路を維持する。

ReaderGitWorkerも借用資源を検証前に保持/copyし、descriptorはkernel/stdinだけを許可する。clock/rootをcaller dictで差し替えない。元monotonic関数を一度保持し、checkpointとactorのcall windowへ同じ関数を渡す。root identityは既存の外部entry/listからtupleへ結ぶ。元request/policy/inventory/phase/binding/root reserve確認後にpipe actorへ渡し、actorは同じ元Job/keeper/receipt/raw/archive/exact leaseへ進む。stdinは借用資源として保持し本境界ではcloseしない。

実限定launcherのkernel/stdin発行、parent-child並行予約、coupled容量、fresh runtime/profile/policy/request/unusedrootは未準備。ReaderGitParent.create_nativeはroot/channel/Job前拒否のまま。全7役whole.runを限定readerとして起動しない。

## 新焦点

raw `artifacts/preformal-reader-git-pipe-entry-20261008-prep/`。新8件を一回の最終source run、2.8249811秒・fail0/error0/skip0。元IOの保持/copy、checkpointと同じclock/外部root identity、caller変更後の資源保持、foreign clock/root dict拒否、JSON注入拒否、CLI→guard/profile/callbackへの順、entry/profile必須、native親入口前拒否を確認。

36 source/science pin前後不変、先行actor共通32pin不変、変更3file safety findings0、module unique8/clean code-save36 working-Git一致。先行actor10distinct/reader旧12/その他完成suite反復0。fake profile/channel/process identity/actor spy＋実小channel/archive fileのprotocol gate、実Win ABI/exe/pipe/worker/native認証/容量合格ではない。process/pipe起動0・追加agent0・全helper終了・critical ownerなし。名前30source/phase32要求/予定64Jobは維持するが完全runtime閉包ではない。

| 原証拠 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 11323 | 0f56fa2970e517e1f6918d398692eff7ee342a365e3d935b8e56af23ee80d51a |
| focused.log | 1904 | 5f1399656bc072aa65bc280f7e76ebf5f5a18d3835a1d337866a5395a3df151f |
| code-save-checkpoint.json | 5878 | 1929729a1927e250f262a408b37a9eacce9b9f560d5796730320524b032189d8 |
| next-capacity-boundary.json | 5284 | 7a6e78e74df0bcc4976ba966873afd8acd6c843bbed1352fb0d52d7bc93d1174 |

focus46604/creation134358746765026177/token117305b17ccaff1bd9c215223f39498be834e69236d62f97f2e8ec0ffcbb0749はexit0・CIM残存なし。初回code push直後のCI空選択を原記録へ保存し、後の実fullSHA選択で37674558981/in_progressを確認。空選択を終端へ読み替えない。

## 次の容量境界

現revisionの選択30sourceはphase合計590655B、最大owned_git_job.py 87676B。旧source bytesを流用していない。現Parent.createのgeneric source raw inventoryはstdout1MiB/stderr64KiB/receipt16KiB/partial-archive512KiB、raw maxima合計1654784Bで、空outerでもreserve後917504Bへ収まらない。source正常pin bytesを失敗stdout capに読み替えない。

次はexplicit失敗出力の保存枠、partial archiveとparent/child control公開の保持順/予約を正確なcall inventoryへ結び、実control/packet/rawのcoupled peakを既存上限内で固定する。最終clean HEADのfresh source/runtime/profile/policy/request/unusedrootと元owner保持限定launcherのexclusive準備後にだけnative入口を検討する。古いモデル786782B/31entryは新容量合格ではない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。unknown Close/Delete/既存Unclosed/未回収は元Popen/Job/process/thread/extra handles/Python owner/stream/buffer/pending/inflight/partial archiveを保持し、blind retry/後続Git-worker/元Python終了へ落とさない。0-job/途中成功prefix/未登録owner/poison archiveはack拒否、metadata/root exit/EOF/worker kill-waitを回収Trueにしない。

## 同時に保存した先行CI

CI37667626735は外部fullHEAD `289cbbcb18fd4919db4f697c1a93cfc55f8e4c89`/attempt1、両minor3491/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37667626735/` へ10raw/14pin/local-remote一致/共有29必須28/runner v2 consistent_candidateを保存。index2783B/7c9e7063418cf40f4fa0c4055d08cb01fc6bf00f6ae06c54804628df44cde15e。3.12/3.14新版20261004.327.1/prerelease=true、compare旧20260927.320.1、公式release/README metadata/blob/log/journal外部pin一致のみ。digest未取得/候補未採択。CLI7の6raw一致/skip1file既知CRLF6差は両pin保持。本codeの実native/容量/正式受入へ読み替えない。
