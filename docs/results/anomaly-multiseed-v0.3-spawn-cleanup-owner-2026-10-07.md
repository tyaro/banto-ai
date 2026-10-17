# v0.3 spawn attribute／stdio cleanupの原owner保全（2026-10-07）

code保存点 `f0b3d72deea42ab984ad70a20a20cd7dcace7225`。gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## この単位

_spawn_cliはDeleteProcThreadAttributeList/stdio CloseHandleより前に、元Job/process/thread、全parent inherited handle、元spawn例外とattribute Python bufferをUnreapedJobへ保持する。DeleteのIO/割込みは元ownerにcleanup_errorを保持して送出し、attribute_list_cleanup_pendingを残す。stdioのclose例外は成功済みduplicateを除き、失敗/未attempt duplicateと元core handleを保持、unknown_close_handlesを明示する。plain IO/割込みで原ownerを捨てず、後続診断や通常terminalへ進まない。

通常成功のtupleとstdio cleanup、既知False時の従来reap＋UnclosedHandles、元body失敗時のreap＋元例外を維持する。keeperはpending attribute/unknown stdioでも元root/Jobを停止・empty/原creationまで再照合できるが、不明Delete/Closeを反復せず全原handleとbufferを保全する。lease/ackを完成扱いにしない。これは未解決cleanup状態の保全であり、自動回収済み証明ではない。

## 焦点と保存

新9件 / 0.011122秒、fail0/error0/skip0。fake Win API/msvcrt/creationで、正常tuple、Delete IO・割込み、body＋Delete両例外、未知stdio close、既知False従来reap、failed reap時core＋extra保全、keeperのroot停止とDelete/Close無反復、元body例外互換を確認。先行keeper13/post-close16/channel21/stop fence17/publication13は反復0。新native0、実exe/実Win ABI/容量合格の証明ではない。

選択14 source/test/science pin前後不変、変更3file safety pass、code-saveはHEAD=origin/clean・14 working/Git一致。全helper終了・critical ownerなし・追加agent0。全repository safetyは先行e4cb30秒timeout未確認を維持、再試行/上限緩和なし。

raw: `artifacts/preformal-spawn-cleanup-owner-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 4807 | `229a1b62c57a358d5ff5a9dfdce665bf17444fdcd1fb31a3e73632aa1c0eab86` |
| focused.log | 2161 | `edcab593d69b98e1fed061e350bc8360e7ce687834416d5df10888c3f1792b64` |
| code-save-checkpoint.json | 530 | `f313a24e18f7236cc121d040fad682219140031d191ad7bc88e8e247bc07330e` |

## 次の小さいproof単位

実worker invocation/shared Job probe/compact proof/failure raw検証/lease完了は未接続、通常worker経路は従来のまま。次は正常receipt＋post-close witness、回収確認できたfailed/recovery observation、未解決ownerを区別するcompact32 KiB proofをrequest/policy/root/phase/native call inventoryへ結ぶ。元inflight/partial archiveとraw pinを保持し、実receipt/output/policy/close/失敗raw照合後だけlease完了と親fence Trueへ接続する。unknown attribute/close/既存Unclosedは保全のみでTrueにしない。marker不在/root exit/flagsだけでは許可しない。

その後Parent.create/on_started bind/stop_fenceとChild wait/probe/keeperを実invocationへ結び、実importを含むsource/runtime profileと専用未使用rootを新revisionで準備する。旧14/14やnative保存点/使用済み親rootを読み替えない。pending4＋完成frame4＋proof/inflight失敗rawを既存outer/root/reserveへ計上し、接続/拒否/停止保全前には新nativeを開始しない。

新CI37590543104（HEADf0b3d72、各minor3229件予定）は進行中。37583002436（HEADe5ff975/3191）は保存済み。未保存は37585092575（HEAD3016448/3207）、37587463962（HEAD8faa921/3220）、37590543104の3件。正式5残件は変更しない。
