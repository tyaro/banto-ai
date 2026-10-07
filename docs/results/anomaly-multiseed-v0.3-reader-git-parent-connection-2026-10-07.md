# v0.3 initial-readerの実親caller接続（2026-10-07）

code `217f0ea66470d24bd9ecd3043a5ec428557b6fc3`、branch `codex/preformal-acceptance-scope`。先行 [archive proof受渡し](anomaly-multiseed-v0.3-reader-git-parent-proof-2026-10-07.md) を実 `generate_and_read` のopt-in reader経路へ接続した。

## 保存した接続

- `reader_git_plan` はchannel_root／外部policy／source_pinsのexact fields。既存linked budgetとfresh producer／initial-reader profileが必須。通常reader／producer経路は既定のまま。
- caller-held source pinsは新30 selected sourceとexact一致し、working rawを再読取りする。親のこの処理はGitを起動しない。子のidentity/blob callbackが、その後Git rawとの一致を確認する。producerの既存Git経路はこの単位の変更対象ではない。
- profileチェックはreader追加16sourceも含む30sourceを必須とし、旧14source profileの流用を拒否する。
- ReaderGitParent.createが元linked producer budgetのouterを保持する。固定4root inventory／producer stage／outer leaf直下channel、同じstarted_at/wall、samplerを使いParentChannel.create→exact inventory→原raw verifier→entryを結ぶ。
- inventoryは各phase head/status＋30blob、各32要求・予定64Job。request/policy/revision/root identityと各source/raw boundを固定、64Job/32KiB以内。新module追加なし。
- 親checkpointは元EnvelopeBudgetのproducer stageを再照合する。innerのbounded phase logを追加／resetせず、新clock/samplerを作らない。元linked probeとouter root identityも確認し、stop／clock/root異常をlatchする。
- 実reader invocationへheld entryとprofile pinを渡す。reader_boundaryは元producer境界／outputs/profileを保持し、readerの30source working pinを再読取りする。
- on_startedはReaderGitParentへ元Popenを保持し、Parent.bindを元native creation観測／binding保存より前へ渡す。stop_fenceはreaderだけに渡す。未確認時は既存UnreconciledWorker／原keeper経路に残す。

source pins、creation、sampler、native ackの試験値はfake fixtureである。working pin照合を実行前Git証明、metadata／root exit／worker kill/waitを子Job回収に読み替えない。元owner／原raw／partial archiveの保全とblind close/Delete拒否は継続する。

## 焦点試験と失敗保全

新moduleのunique10件。初回 **10件、8pass/2fail/error0/skip0、2.3975808秒**。2件はfake supervisorのreplyにruntime_observationフィールドがなくreader到達前に停止した。fixtureだけを訂正し、その **2件だけ0.7613278秒でpass**。他8件・旧完成suiteは反復していない。初回を最終sourceの単一10success runには読み替えない。

対象は30source/64call、元outer clock/sampler、unlinked/wrong leaf・source pin欠落/改変・clock reset拒否、partial bind IOと元Popen保全、linked stop、実generate_and_readのinvocation/bind/fence受渡し、profile不足/追加source欠落の起動前拒否、bind失敗時の元UnreconciledWorker/keeperへの受渡し。

37 source/science pinは各run前後不変、変更test以外36pinは両run一致。変更3file safety、最終unique10 discovery、clean code-save37 working/Git pin照合がpass。fake supervisor/Kernel/executable/creation/clockによるprotocol gateで、実exe/Win ABI/native認証・容量合格ではない。

証跡root: `artifacts/preformal-reader-git-parent-connection-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 13672 | 93b0fe7f2e261b0ea0a6f6afe643001e07f5efbedf901c492d4eef127ffeec9e |
| focused.log | 4243 | 3a791012f558281fee6311e5d69f07fa54b26a9fabbfa4d8aad9acc39f11d549 |
| corrected-two.json | 12395 | 1e896f3990b8daacd0a62cf9171f11021560d9c9452a4791fe93e388f9cbd659 |
| corrected-two.log | 602 | 2a28e49546b3b7a7d82ab19bb7d0ebbf111e2955a98ad9d09a699b74bccc211b |
| focused-components-final.json | 6405 | a262577ebad9698926fbc032d17001d1ab0465ebb218ee0dd6a3eec043cf1682 |
| code-save-checkpoint.json | 495 | 8cad9a0ac48d0daf0ac923cc43a5510f135b6fc0f70225546a4cdc7d84df7b3e |

helper42096/creation134358460555898896/token89ff55f9a2c727d31123a845150ba9519b170e27b339d0d5070b1f79c4b80114 はexit1、訂正42328/134358460955460099/token5629e8d21f3130b2b574274b6cb9fd7b6f0ad16dfb9bfe394094f9de3d160bb7 はexit0。CIM残存なし、全helper終了・critical ownerなし、新native0・追加agent0。

## 次の小さい単位

上位のgeneration_publication_budget.run／実trial callerでは、このplanのforwardingをまだ接続していない。次にその受渡しとexclusive plan準備を固定する。新revisionのsource/runtime inventory/profile、外部policy/request pin、channel/inventory/manifest/proof各pendingとinflight/失敗raw/partial archiveを含む正確なroot inventory・容量見積りを先に保存する。新profile／専用native requestは未準備。

30 selected sourceは完全なsource/runtime閉包ではない。旧14source／古いpinを使わず、producer非対称pre26/post24を親111/111へ渡さない。全7役／旧親native／完成した焦点試験は反復しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB/32entry/depth2/reserve128KiB・全体321MiB/672entry・cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理なし。実上位callerと拒否/停止保全、fresh profile/exclusive準備が完了するまで新nativeを開始しない。

formal gate=`s4_acceptance_not_frozen`、formal_permission=false、credit0、登録holdout観測未読。実データ範囲は保存済み合成dev8/smoke2のengineering読取り・記述報告のみ。runner digest/候補採択・実ロード依存/業務異常子孫・正式5残件/最終受入は未完了。
