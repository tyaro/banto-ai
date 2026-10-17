# worker archive追加frameと保持control枠の照合

2026-10-08 JST。最終code `f54cfa991ada7dde9be8b4cd9d67594e3740f280`、初版 `bff9d30fa21ff05fb94d7cf5fe734dd044810739`。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## 保存したcode単位

既存worker_git_archive moduleへopt-in `ArchiveAppendAdmission` を追加。新production module0、選択30source/各phase32要求・予定64Jobを維持するが、source/runtime閉包の証明ではない。

callerのroot/identity/revision/inventory pin/control limits/shared checkpointを保持・copyし、同じ元writer/verifier/endpoint/rootへIO前bind。完成・pendingのrequest/binding/stop/worker-inventory/git-manifest/git-proof/ack、計14名のpositive maxima（bool拒否、各既存32KiB以内）を必須にする。foreign inventory、再bindや異なるshared checkpointは拒否して元writerを保持する。callback後にも保持planのcanonical bytesとoriginal binding/原archive bytes/順序を照合し、減らされたcontrol表や別root/clockへ追随しない。

Writerは元packetを検証・保持し、encoded/compressed/frame/candidate/manifestをIO前保持する。既存decoded1536KiB/frame128KiB/archive512KiBを維持。append前に元root identityで実snapshot（32entry/depth2）、現在の全保存bytes/entries、全14control maxima（既存controlも保守的に再計上）、実frame追加bytes、reserve128KiB/診断2entryを同期確認。原recovery `partial-archive.bin` のcapを新frameの予約に読み替えない。原partial/receipt/stdout/stderr等がrootに保存されていればsnapshotで別量として計上する。

元archive bytesを再読取りしてからappend。従来のarchive/resolver・原raw readback後、同じ元frame/before bytes/full disk readbackとroot/将来control枠を再照合して初めてstorage完成を記録する。write後に別writerの保存量が増えた場合もarchive/raw/pendingを保持・poisonし、後続appendや再書込みを拒否する。clock/IO・割込みは元例外/frame/packetをlatchする。

root snapshotと後続control statはatomicではないため、観測済みcontrolのbytes/entryを差し引かず全14枠を保守的に加算する。既存分の二重計上による拒否も保持し、native容量合格のためにこの枠を緩めない。

本gateは同期snapshotによる拒否と保存後照合であり、全writerを参加させたatomic reservationではない。完成記録のatomic_reservation/lease_completed/parent_ack_authorized/execution_authenticatedはfalse。control publisher自体の上限強制、親identity任意失敗出力の将来枠、global/memory/並行peakは未接続。既存actor/entryはこの新opt-inをまだ発行・forwardしていない。default追加gateなしのarchive経路は従来の検査/形式を維持。ReaderGitParent.create_nativeはroot/channel/clock/Job前拒否のまま。

## 新焦点と保存pin

専用 `artifacts/preformal-worker-git-append-admission-20261008-prep/`。fake Win API/creation/receipt fixture＋小さい実archive/rootのprotocol gateで、実Win ABI/pipe/exe/worker/native認証/全経路容量合格ではない。

- 初版新7件一回0.6983723秒、fail0/error0/skip0。
- callback後の保持control表の改変拒否を追加し、新1件だけ0.1048704秒pass。さらにroot snapshot後のcontrol公開で差引き枠が減るraceを補強し、新1件だけ0.1439509秒pass。先行8/旧suite反復0、新9distinct/最終unique9。最終source単一9success runには読み替えない。
- 各35source/science pin前後不変。他33pin全3run一致、先行容量準備の共通33pin不変。変更2file safety findings0、初版clean code-save35working/Git一致。補強code-save-v2はuntracked doc draft1件のみdirtyを明記し35working/Git一致。
- 原partial raw cap1Bから独立したframe追加とcaller input copy、保持失敗rawのbytes計上、将来pending/診断entry計上、clock割込みの原frame/例外保全、write後の並行保存増加でpoison/no replay、foreign inventoryの空archive前拒否、closed control maxima/bool拒否、callbackによる枠削減拒否、root scan後control公開がbytes/entry枠を解除しないことを確認。
- 新worker/Job/pipe/native起動0、profile再観測0、追加agent0、登録holdout観測読取り0。

| 原証拠 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 10789 | fdf4718d10984430a472800c7ed002ff73c47f0deebb4e29ae761028df3a6ade |
| focused.log | 1598 | 5c719b0597f41fa1e488a62591250288cbdd2b6ea82aeeb20e066709e6f00211 |
| focused-v2.json | 10789 | f4b03c81c69ca9230a9fb634ef7f5fd2056141f9081db8b09343bdbb96383336 |
| focused-v2.log | 287 | feb6c54083773e1f68a3627e19fbfba4349aeb6d32314dc9005a49e1383bf37a |
| focused-components-final.json | 1046 | 56428e1ef836e3b449a2a5cea4304775e4bace17c0a1557c9ba4fb738d613995 |
| code-save-checkpoint.json | 6206 | 8b7506a2b15f2c07c72659950eff2b67977ad970d958b2d7805168603b0a4bb8 |
| focused-v3.json | 10787 | 697d06c18269c669d0d505ebaaf0a5f12a8af6c692a25df1ff750f128f921939 |
| focused-v3.log | 327 | 845c50c459d5daaed5d7309443a111a96ea3299f571188cd7eb01dc3ccbc00ee |
| focused-components-v2-final.json | 1402 | d04c77c1b9985770a7e55b049e8abc230802904fc32950b5b3b9f14f6c74eab1 |
| code-save-v2-checkpoint.json | 6673 | 5db6aff685cda14d5a754f371f3f79ca2b2ce6448420166b1b395c71bc6bbf13 |

初版2484/creation134358798991684775/token44c70a0d0184fbd916832160e5d09ce6306221fbe33cde70b3fab3197fa73249、追加46780/134358800085457600/token276dbd102a04a1f7e41eae5d588a1dc582fdb1c03098f15639580ccd748e2e02、race37100/134358805776994390/token978778c7368a66a53edea21b0b1b97341c3c6e68cf7cf352daabe77bd512dcc7はexit0/CIM残存なし。PID単独で同一process扱いしない。全helper終了/critical ownerなし。

## 次の境界

caller-held control limitsとこのappend gateをActor/Reader entry/Parent/external planの同じinventory pinへ渡す小さいunitが必要。新fieldや新inventory形式を旧pinに付け足さず、元IO ownerを保持して拒否する。全control publisher/親identity将来失敗rawの枠を同じrequest/rootへ結ぶ実並行予約と、実packetのframe/total容量確認は後続単位。正常pin bytesや旧widthモデル948946B/残余99630B、未検証gzip152199Bのprobeを新cap/request/proof/容量合格にしない。

fresh latest clean revisionのsource/runtime/profile/private policy/request/unusedrootと元owner保持限定launcherのexclusive準備は未完成。全7役whole.runを限定readerとして起動しない。旧14source/profile/pin/producer pre26/post24や使用済み親archiveを流用しない。unknown Close/Delete/既存Unclosed/未回収/IO・割込みでは原Popen/Job/process/thread/extra handle/Python owner/stream/buffer/pending/inflight/partial archiveを保持し、blind retry/後続Git-worker拒否。metadata/EOF/root exit/worker kill-wait/途中snapshotは回収True/lease/ackではない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output/cleanup30秒/poll0.25秒を維持。上限緩和/未測定rootへのreceipt移動/旧raw-root整理は行わない。完成焦点/旧native/使用済み容量準備rootの反復・追加保存なし。正式5残件/正式採択/最終受入は未完了。

## 同時に保存した先行CI

CI37677397653は外部fullHEAD `37b7feb400c754c5030b3164f020390cf36572d7`/attempt1/各minor3529、全3job success/fail0/error0/skip237/source不変。専用rootへ10raw14pin/local-remote一致/共有29fixture必須28/runner v2 consistent_candidate・保存後照合。index2783B/d6c1b7cad72a43e2ff23cb4e3a0ca9db81e65416def31d0bfe6edaea6c119158。3.12/compare旧版、3.14新版prerelease=true、公式release/README metadata/blob/log/journal外部pin一致のみ、digest未取得/候補未採択。CLI7 6raw一致/skip1file CRLF6差両pin。

download10912/creation134358795938417469/token9c1f7aa07f0d3369981864ac19bb72aad6c3998c55f841779907922a6071d798、verification20756/134358797330419477/token8cee7bfe37fbf047a090a4b659dc4c1aaecca224c80ef1c4f96e8baa31b7bf8bはexit0/CIM残存なし。このCIを新append gateのnative/容量/正式受入へ読み替えず反復しない。doc-only追補はskip ci。

CI37680026029（外部fullHEAD `26cf5cab7cdd1a5c2eb3d45757b5d20d8010e7a1`/attempt1/各minor3536）も全3job success/fail0/error0/skip237/source不変。専用rootへ10raw14pin/local-remote一致/共有29必須28/runner v2候補一致・保存後照合。index2783B/09fc65245c357ed5d56b16ff92861c9cc0c8e27a5c580a7390779f8b164d6f44。3.12/compare新版true、3.14旧版・公式外部pin一致のみ。原download25200/creation134358802619569049/tokenb162adf947c4242d58c7607ce71fc6f26bf9b0355789f453a42782c0289c83c4、verification9928/134358803301251796/token5f44e2d0821e6e2b6f531b73548982600b6b840ed2c6f93d441fe5f4ffa39dbfはexit0/CIM残存なし。全7helper終了、critical ownerなし。このCIを新append gate/native/容量/正式受入へ読み替えない。

未保存CIは初版37685672435（実fullbff9d30fa21ff05fb94d7cf5fe734dd044810739/各minor3544予定）と補強37686697633（実fullf54cfa991ada7dde9be8b4cd9d67594e3740f280/3545予定）、push後in_progress。実fullSHA/workflow/run/attempt/jobs固定で終端原rawを新専用rootへ一度保存する。doc-only新CI追跡は増やさない。
