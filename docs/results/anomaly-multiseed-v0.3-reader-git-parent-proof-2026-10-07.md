# v0.3 reader archive proofの親への受渡し（2026-10-07）

code `0f249f63be055f0937c67a7963f541daa9e6df83`、branch `codex/preformal-acceptance-scope`。先行child入口code `202b1c3` とterminal `e1b8924` を対象に、親の原raw verifierが必要とするmanifest受渡しを独立して保存した。

## 実装した範囲

- ReaderGitWorker.runからterminalへopt-in publisherを渡す。既定terminal publisherは従来のまま。
- terminalが原owner回収、exact lease、fresh archive readback、全call／最後failedの停止prefixを確認した後、固定 `channel/git-manifest.json` とproof envelopeを公開する。
- manifestを固定pendingへexclusive/fsync/readbackし、上書き禁止renameで完成名へ公開。proofはmanifestのpath/pinと既存Git proofを結ぶ。manifestとenvelopeは各32KiB以内。ackは両者の公開・checkpoint後のみ。
- IO／割込み時はactorへmanifest/proof raw・元例外を保持してlease errorをlatchする。partial manifest/proof/ackとarchiveを保持し、同actorの再公開を拒否する。
- ReaderGitArchiveVerifierは元ParentChannel、caller-held inventory bytes/pin、同じcheckpointを保持する。固定inventory file、proof-linked manifest pin、全archive原raw、receipt/policy/元creation/close、exact call coverageを再読取りして既存proofと照合し、最終manifest/inventory/archive readback後だけTrueを返す。
- verifier IO／改変失敗は元例外を保持し、追加読取りを反復しない。ParentChannelの元Popen保持／bind／fence契約を使う。

manifest pinは、このbound proofから親が捕捉するpinである。実行前に独立採択したmanifestではなく、native実行の認証にも読み替えない。

## 新しい焦点試験

新moduleのunique **12件、4.2033845秒、fail0/error0/skip0**。一回の最終source run。29選択source/science pinは前後不変、変更3fileの `scan_repository(paths=...)` はpass、clean code-saveで29 working/Git pinを照合した。

対象は原rawとmanifestを通る親fence、確認済みfailed prefixの原失敗raw保全、zero-job／成功prefix途中の拒否、manifest/proof/ackの部分IOと割込み、archive/manifest/inventory改変、外部manifest path拒否、元checkpoint例外latch。fake executor/Kernel/executable/creationを用いたprotocol試験である。1／2callのfixtureであり、30source・64Job実workerのnative／容量合格ではない。旧child12／terminal11／actor13／archive16／proof18の完成suiteは反復していない。

証跡root: `artifacts/preformal-reader-git-parent-proof-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 11375 | 3603e7eef6c8008c27d3525276462c21089a9bb7c652e4dbbe850b70c9d6d27a |
| focused.log | 2875 | e6978398a665e005b341b5d1ad5b5ee65690a624696ba6dff28b4e51f818206f |
| code-save-checkpoint.json | 443 | cc0e4d637efa9eae50823ad1e0aa4488c6ad1275d096c06d1f0129b73636a062 |

helper PID41952／creation134358449535211065／token93e73bfd259b55fe4f39382f7f0ddde9ef24a4ed15f9fd5590b8066baa22dfe5 はexit0、CIM残存なし。全helper終了、critical ownerなし、新native0、追加agent0。

## 次の独立単位

実親 `generate_and_read` のreader_started/on_startedとsuperviseへParent.create/bind/stop_fenceと本verifierを渡す。caller-held request/policy/inventory/source/profileと元Popen/creation、既存outer budget clockを結ぶ。現在、その実親接続は未実施。

新source/runtime profileとexclusive未使用rootの準備も未実施。旧14source／古いprofile pinは使わず、新選択30source・各phase32要求・予定64Jobを新revisionへ固定する。選択sourceは完全閉包ではない。producer pre26/post24と親111/111 actorの非対称境界は別単位。

root inventoryにはrequest/binding/stop/ack、caller inventory、manifest/proofと各pending、archive、inflight/失敗raw/partial archiveを明示して計上する。新manifest/pendingの追加も既存outer1MiB/32entry/depth2/reserve128KiB、archive512KiB、全体321MiB/672entry内に収める。上限緩和、旧raw/root整理、未測定rootへのreceipt移動、新native開始はしていない。

元owner未回収時は後続Git/workerを拒否し、元Job/process/thread/extra handleとPython ownerを保持する。marker不在・root exit・metadata flags、worker kill/waitを子Git回収へ読み替えない。

formal gate=`s4_acceptance_not_frozen`、formal_permission=false、credit0、登録holdout観測未読。実データ範囲は保存済み合成dev8/smoke2のengineering読取り・記述報告のみ。runner digest／候補採択、実ロード依存・異常時業務子孫、正式5残件・最終受入は未完了。
