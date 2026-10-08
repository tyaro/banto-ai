# 新packet分割・全raw readbackの準備（2026-10-08 JST）

## 対象と保持順

開始2026-10-08T08:38:03Z/HEAD1a91b3b022ae4b8d627655f2425e5c7d95baa1bb-origin-clean。先行元8helper同creation-token不在/repo helper-critical ownerなし。対象sourceは既存worker_git_archiveの新PacketPartitionPreparationと新test。追加production module0/追加agent0/native0/runtime-profile再観測0、science2はhash metadataのみ/holdout未読。原rawは専用 `artifacts/preformal-packet-partition-preparation-20261008-prep/` へ保存する。

caller保持の原owner/checkpoint/context/packet/raw maximaをvalidation/clock/copy前から参照保持する。新format `anomaly-v03-worker-git-packet-partition-preparation-v1`、magic WGP2はmemory-only準備契約。caller宣言request/inventory pin・revision/root/root identity/leaseをcanonical context pinへ固定し、kind/event/全raw pinからpacket pinを作る。実channel request/未使用root/native ownerを発行または認証したものではない。

rawの各32768Bを新canonical chunk record→gzip→8B header付きframeへ変換し、原encoded/compressed/frame returnを判定・callback前に保持する。None receipt/partialとempty stdoutは別量。new archive growthはframe全幅の合計で、原partial raw inventory上限や既存rawをその予約として流用しない。

| 枠 | 上限 | 解釈 |
|---|---:|---|
| original raw chunk | 32768B | 最大値の割引やnative認証ではない |
| canonical decoded chunk | 65536B | 各recordの追加境界 |
| compressed frame payload | 131072B | 元128KiB上限を維持 |
| frame count | 64 | 1packet内のchunk数、64Git Job実行ではない |
| new archive growth | 524288B | frame headerを含む全合計 |
| manifest | 32768B | caller外部pin＋全frame/raw coverage |

全manifest raw/pin・frame順序/header/pin・chunk name/offset/total/byte数・全raw pinをreadbackへ結び、元packetとの一致を確認する。欠落・順序変更・payload改変・aggregate超過を拒否する。成功viewもnative_authorized/atomic_reservation/capacity_pass/lease_completed/parent_ack_authorized/execution_authenticated=false。executeは未準備native/archive IOを拒否し、実書込みやHANDLE close/rename/Job/worker/leaseを発行しない。

## 失敗保持と接続の限界

unknown圧縮returnや巨大returnは、原encoded/原returnを保持してframe生成前に拒否。clock/IO/KI・caller pin改変・公開pending/retained/incoming row消去・両snapshot改変は原第一例外をlatchし、error metadataを消してもreplayしない。原・拒否object/途中bufferはprivate original referencesにも保持する。cached prepare/viewはgzip/clock反復0。

旧v1 archive/read/append/manifestとrequest/entry/context/ack/proofへfield追加やpin解釈変更なし。変更source内の `_path`/`_inventory`/`_append_frame`/`SavedWorkerGitArchive`/`WorkerGitArchive` の5spanは原Git bytesと一致。ReaderGitParent.create_native拒否method437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7cも不変。前回の完成13AST監査や工程packet154696B圧縮拒否を再実行していない。

この新部品は実publication/reader/parent/native launcherへ未接続。caller object/値pinをraw Job/process/thread owner観測、Win ABI、原CloseHandle/child FileIO close/renameのtransport認証へ読み替えない。全planned-call累積archive、Python object/一時copy/RSS/他writer/native buffer/carrier/親将来failure・diagnostic/entry-context/partial/new growthのcoupled peak/global memory、全writer同request-root atomic予約は未測定・未完成。frame/manifest payload上限だけを容量合格にしない。

## 新しいriskケースだけの確認

実memory codecを用い、engineering stub event/独立宣言context/owner objectとtemp empty directoryで確認した。旧native/protocol fixture bodyを実行していない。new raw packetだけで分割全readback、Noneとempty、欠落・改変・順序、unknown/巨大圧縮返値、各frameが収まるaggregate超過、KI、cached view/native早期拒否、metadata消去・snapshot改変を確認した。temp directoryにarchive FileIOを書いていない。

| component | 新body | 結果 | 秒 |
|---|---:|---|---:|
| 初回 | 15 | pass/fail0/error0 | 0.09793280001031235 |
| 保持row/incoming owner/packet消去 | 3 | pass/fail0/error0 | 0.012656799983233213 |
| incoming field/record値改変 | 2 | pass/fail0/error0 | 0.016516100033186376 |

新20distinct/body20/最終unique20。pass済み15/3/旧suite/完成focusの反復0。3source/runの結果であり、最終source単一20success runではない。各61source-science pin前後不変、他59全component不変、先行59共通pin不変、変更2file safety0。source inventoryを61へ再固定し、名前30合計836299B/最大job_tree_owner120035B/cc126fca55a0cfe128f90215283669b45f8589bbaca8103fb7233694dbddd5a5を確認した。名前30/予定32phaseずつ64Git Jobは完全runtime閉包ではなく、旧source cap/profileを新HEADへ流用しない。

| raw | bytes | SHA-256 |
|---|---:|---|
| focused.json | 24336 | b79c0ce5c2b3c6f4fee5efd4f2d00bc91943af916e3b32f0175ed20bcc5fc3e8 |
| focused.log | 3566 | e37b50ba090006323b68c528b9eab93e6808907c3c19bc6bd7e7d8832b4efb4c |
| focused-v2.json | 23493 | e25c915d0ce04e561e273714e92de36aad396c26461e63e22a254f84965c052e |
| focused-v2.log | 799 | 062df4654ba1ea96a835b660eb596fe1bae8a0b84da6a6d4886d3be7c917965b |
| focused-v3.json | 23425 | ec78512c507e90a94c1eb3864e3ca8fc21884702fb162f75f14e8442169272ec |
| focused-v3.log | 573 | d02aceba760241317201df2fbc93ac6e9683fdea372c17ebab6221111b1d7de1 |
| components.json | 18598 | 38334cf84a0b21b4cd2a25b70f4550da41c5bdbab0eabdd85e6187bc9aafcdac |

元focus32828/creation134359227184446107/token868a67175fa1c8db76ae2e7d51d8964d5657c1f2e28a7fbfffa82d3239c41b66、v2の34064/134359228267373916/token16f7102bbd7f8e7ba95e57f294f04ed2ef20689e1cee994b39ef0c4a1cea1335、v3の50168/134359229020522266/token001f0da87db2e0218f23d4bcfaec38436cda74bf4b092b15ff831477d8bde1a6、components42916/134359229912844203/tokenaaac844a07a9027fd2ab73a6f732450817cec8c4e04e09ee527d95f65842851fはlive/execution passed/critical_owner=false。Git前に元creation-token不在を確認し、保存後も原helperへ固定して照合する。PID単独判定なし。

## 保存と次の境界

確認済みunitをcode commit/push一回で保存し、doc-only追補をskip ciへ集約。61working-Git/science hash metadata/原focus6raw・components・元helper・旧root不変/HEAD-origin-cleanを照合して専用rootを閉じる。512KiB32entry/reserve128KiB、元wall/time/output/stop保持を維持し、旧CI3844 root38file10282900B/batch20file57142B/原packet14file319974Bへ追加・反復しない。

次は同request/rootへ全planned-call archive累積・親identity将来failure/diagnostic・原partialとnew growth別予約・entry-context実bytes・buffer/object coupled peak/global memory/all-writer atomic予約/exclusiveを結ぶ準備。fresh latest-clean runtime/profile/private policy/native request/unusedrootと、原Create/Assign/member実return/HANDLE owner/attribute lifetime/stdio継承/child owner transport認証は未準備。native入口/create_native早期拒否/全7役whole.run限定reader実起動禁止を維持。formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/holdout未読、正式5残件/正式採択/最終受入は未完了。
