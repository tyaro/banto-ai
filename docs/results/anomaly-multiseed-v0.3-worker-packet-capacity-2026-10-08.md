# 現source・工程合成失敗packetのarchive上限拒否（2026-10-08 JST）

## 確認した範囲

開始2026-10-08T07:48:35Z/HEAD2edd91bb8a0f63d76c66575fdf95d5a2bcde78ba-origin-clean。先行元8helperの同creation-token process不在/repo helper-critical ownerなし。production code d4e5f2ec90a9c17be90af4eadebadb4b769a409b不変。production/test変更0、旧suite/完成焦点/13AST監査/native/追加agent/runtime-profile再観測0。science2はhash metadataのみ、登録holdout観測未読。

今回のunitは現60source-science working-Git pinと名前30source/予定64callを固定し、新しい工程合成失敗receipt/eventを現在のProofVerifier→WorkerGitArchive.appendの実encoder→compressed上限拒否まで接続した。実native worker/Job/pipe/exe・Win ABI・child IO owner認証を実行した結果ではない。

名前30sourceは合計820544B、最大job_tree_owner120035B/cc126fca55a0cfe128f90215283669b45f8589bbaca8103fb7233694dbddd5a5。generatedは60準備pin内・名前30外。予定pre/post各32＝64callはmetadata inventoryで、実行していない。原fixture inventoryは1callだけであり、予定64Job/完全runtime閉包へ読み替えない。実runtime profile/private policy/native request/exclusive launcherはNoneのまま。旧f566bc40のsource幅・無効encoder probe・旧profileは流用していない。

## 新packetの拒否

新専用原root `artifacts/preformal-worker-packet-capacity-20261008-prep/` の原FileIOへ、source_blobの失敗stdout131072B/stderr16384Bを直接書いた。expected source pinは現最大sourceの実pin。Kernel/Job/process creation・executable observation・exit17・closeは明示fake。原receipt2544Bと元return後のpost-close eventを保存bytesとしてProofVerifierへ渡し、失敗receiptのprotocol consistencyを確認した。旧probeのevent空/receipt Noneではない。native_start_identity_authenticated等の原fixture fieldは合成値として保全し、実native認証へしない。

原raw inventoryはstdout131072/stderr16384/receipt16384/partial-archive65536の独立caller maxima内。今回partial-archiveはNone、actual rawは150000B。WorkerGitArchive.appendは原packetをcopyし、snapshot verifierとの一致を確認して、実raw_b64 record/JSON/gzipを作った。compressed154696Bが原MAX_RECORD131072Bを23624B超過し、`worker archive compressed record byte bound` で拒否した。

append試行は1回。new frame/candidateは生成前、_append_frame呼出し0、原worker-git.binは0Bのまま、writerはpoisoned/pending packet・encoded・compressed保持。receipt/outputを別rootへ移動していない。codecの上限を上げず、lease/ack/native recoveryを発行しない。この例は現在のprotocol checksを通る工程合成失敗入力でも、raw最大値だけではcompressed最大値を保証できないことを示す。

| 別量 | bytes | 扱い |
|---|---:|---|
| 原receipt/stdout/stderr | 150000 | 原3fileを保持 |
| encoded canonical record | 200873 | 保存gzipのbounded readbackで原bytes/pinを照合 |
| compressed | 154696 | 原rootの131072B＋23624Bの2partでlossless保持 |
| 原compressed上限 | 131072 | 緩和しない |
| 仮の8B header込み必要幅 | 154704 | 実frameではない |
| 原archive | 0 | append前拒否 |
| 原partial archive | 0 | 今回None、将来failure最大値の削減根拠ではない |

raw_b64 ASCII payloadは200004B。保存bytesと現append sourceから、gzip return位置で原packet raw150000＋record raw_b64 payload200004＋encoded200873＋compressed154696を同時保持するpayload下限705573Bを算出した。Python object/一時copy/JSON string/caller保持の追加bytes/RSS、他writer/native buffer/carrier/entry-context/親failure/partial/new archive growthを含むcoupled peak/global memoryは未測定。payload下限をmemory容量合格にしない。

## metadata失敗の保全とcontinuation

原helperはprotocol確認・上限拒否・圧縮2partの正常write/readback後、packet-refusal.json保存前のcanonical JSONでtupleのfake close-return ledgerを拒否され、V03ValidationError/not a JSON value/exit1になった。metadata失敗をproduction/CI/native回収失敗へ読み替えない。原helper49300/creation134359199561702246/token6fbec55b2c513c0457ddce1d8df47e6215335094a019b540338892958b1e3088はlive/execution failed、同original不在。実native0/critical_owner=false、metadata JSON生成前失敗で未解決native/stream IOのkeeperはない。

原root14file319974Bを閉じて変更・再実行せず、`artifacts/preformal-worker-packet-capacity-continuation-20261008-prep/` へ未保存metadataだけを保存した。原gzip2partのbounded single-member decodeから、原encoded/event/receipt/outputをreadbackし、原FileIO3raw・inventory/request pin・原0B archiveに照合した。eventをclosed/disk一致から生成していない。原fake CloseHandleのreturn listは個別raw保存前に失われたため、補っていない。tool trace/exception.jsonは原process stdout/stderr byte file全体の捕捉ではない。

continuation47100/creation134359202381141235/token4bc43d03b55afd2c95756140fdb6137b6b6b9efd8fcd72c0b50ebfb1d2616072はpassed。原protocol/encoder/helperの反復0、原failed helperをpassedへ書換え0。checkpointは原14file/60working-Git/science/metadata/元failed・passed両identity-token/CIM同original不在/旧3root不変をmetadataだけ照合した。PID単独判定なし。

| metadata | bytes | SHA-256 |
|---|---:|---|
| source-packet-preparation.json | 37338 | 54a9c9c929b674cb8a373bbb389c1ce8fd7112c88e71465edadfe26987494c25 |
| packet-readback.json | 2885 | 98aeac6858714e9af70e9c6509535a7ed623aab6f27895f9d45c9af4e3127433 |
| payload-accounting.json | 909 | c5a45d9ad9ad8c1dcf163c245d8ef783b627f0c4dcc26703b70d2b5f10379642 |
| save-checkpoint.json | 13141 | 3376e13195ba49cf430047edc477531962e4e4fd0022b06ced4bd4a34fa2e8ce |

doc-only3文書を一回skip ciで保存後、60working-Git/science/docs3/原14pin/continuation原raw/元3helper/HEAD-origin-lsremote-clean/旧3root不変をmetadataだけ一度post照合し、continuation rootも閉じる。各新root512KiB32entry/reserve128KiB、原rootdepth2/single128KiB、元wall/time/output/stop保全を維持する。原compressedを2part保持したことを128KiB frame合格へしない。旧raw/失敗/rootへ追加・整理なし。

## 次のunit

未保存CI37743146137/full d4e5f2ec90a9c17be90af4eadebadb4b769a409bは今回3.12job113198312223in_progress/3.14job113198312515success、compare未発行/run未終端。3844は予定/journal未確認、終端download/local回帰/runner追加0。完成CI3829/3812/旧CIの反復なし、doc-only新CI追跡なし。

次は上限を保った新closed形式のpacket分割/別raw参照の契約を検討し、同lease/request/root/inventory/原owner・full raw readback・manifest pinへ結ぶ準備をまとめる。旧v1 packet/request/entry/ack/proofや旧pinの解釈を変えない。原partial rawとnew frame growthを別量として数え、entry/context実bytes・親将来failure・同writer/native/carrierのcoupled peak/global memory/all-writer予約を閉じる必要がある。現caller capsのままnative入口を開かない。

fresh runtime/profile/private policy/native request/unusedroot/exclusive、原Create/Assign/member return/Job-process-thread owner/attribute lifetime・stdio継承/child close-rename-raw transport認証は未完成。create_native root-channel-clock-Job前拒否/全7役whole.run限定reader実起動禁止を維持。formal gate=s4_acceptance_not_frozen、formal_permission=false、credit0、holdout未読、正式5残件/正式採択/最終受入未完了。
