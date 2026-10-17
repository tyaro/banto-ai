# v0.3 子Git原owner keeper・reap保全（2026-10-07）

code保存点 `8faa921fc5c9e33ebe1a84799b3747c22326f28c`。formal_permission=false、正式credit0、登録holdout観測未読、gate=s4_acceptance_not_frozen。

## 実装境界

Git `_execute` のreap fallbackは、追加Terminate/診断より前に元UnreapedJobを保持し、original_error/stop_errorをそのownerへ付ける。元例外へのgit_stop_error属性付与を止め、属性拒否・cleanup停止割込みでも元Job/process/threadを捨てない。

新 `ChildGitKeeper` はcaller childの停止latchとactive leaseのowner ledgerに元exceptionを保持する。ledger IO失敗も通常IO例外へ変換せず、元ownerへkeeperを付けて元exceptionを再送出する。元native handleだけにTerminateJobObject、未割当suspended rootにはTerminateProcess、既存5秒cleanup内のJob accounting/root exit、元process handleからPID/creation照合を行い、empty確認後に元3 handle＋最大3 inherited handleをcloseする。後続Git/workerや新Jobは開始しない。

named closerはCloseHandle/診断前に全原handleを保持する。Falseと確認できた未close handleは、そのhandleだけを再closeし既に閉じたものを再処理しない。例外でclose成否不明なら未attempt分とsecondary UnclosedHandlesを保全して自動再closeを拒否する。既存UnclosedHandlesだけではJob handleが既に閉じているか判断できないため、report flagによる自動回収を行わない。

close成功後の記録失敗にも再close禁止を先にlatchする。recovery observationをcacheし、marker IO/sleep割込み後はnative終了/closeを再実行せず同じ観測を保持する。callbackにはcopyを渡す。原owner、secondary owner、原raw/inflight/partial archiveを削除せず、callback成功だけでlease完了/parent ackを許可しない。

## 13焦点・保存

新13件 / 0.019733秒、fail0/error0/skip0。fake Kernel/creationとchild ledger stubで、元handle＋extra回収、live/missing exit拒否、unassigned root停止、停止/creation例外、既知Falseだけのclose retry、不明close保全、既存Unclosedの保全、marker/sleep失敗の無native反復、post-close記録失敗、extraによるcore override拒否、ledger IO時の元owner再送出、hostile原例外＋reap/cleanup割込みを確認。先行post-close16/channel21/stop fence17/publication13を反復していない。新native0、実exe/容量合格の証明ではない。

選択14 source/test/science pin前後不変、変更4file safety pass。code-saveはHEAD=origin/cleanと14 working/Git pin一致、全helper終了・critical ownerなし・追加agent0。全repository safetyは先行e4cb30秒timeout未確認のまま、再試行/上限緩和なし。

raw: `artifacts/preformal-child-git-keeper-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 4812 | `0e4ec777e8824113bbb74c70ac60b37dec0cad283af7148c169d7f25aa259130` |
| focused.log | 2830 | `1d2ba6e580d711d46bace53742a55d058557bc654691f371d296b1d95617df01` |
| code-save-checkpoint.json | 571 | `86ada80dfc36e858eec83cf539d79c6c5a956659d57c06808944d6dcffbd685c` |

## 次の接続と保留

keeperのnative API経路を実装したが実worker invocationでは未使用。shared Job probe、lease完了、failure raw照合、compact32 KiB proof、親外部pin verifierへは未接続。recovery observationのlease_completed/failure_raw_verified/parent_ack_authorizedはFalseのままで、metadataや単なるroot exitをformal/native回収完了へ読み替えない。

次は `_spawn_cli` のattribute-list/stdio cleanup例外でも元Job/process/thread/extra handleを失わない下位境界を固定する。この現経路はDeleteProcThreadAttributeListとstdio CloseHandleの例外を持つため、実entry/native前に保全する。既存Unclosed/不明closeの継続保全は未解決状態として区別し、blind再closeをしない。次にfailed/raw observationをrequest/policy/root/native call inventoryへ結ぶcompact proof・lease完了を接続し、Parent bind/fenceとChild wait/probe/keeperを実invocationへ渡す。実import/source/profileを新revisionで再準備し旧14/14・旧native/rootを読み替えない。既存outer/root/reserve内の準備・拒否/停止保全が完了するまで新nativeを開始しない。

新CI37587463962（HEAD8faa921、各minor3220件予定）進行中。37581339092（HEADaaca57c/3178）は保存済み。未保存は37583002436（HEADe5ff975/3191）、37585092575（HEAD3016448/3207）、37587463962の3件。正式5残件は変更しない。
