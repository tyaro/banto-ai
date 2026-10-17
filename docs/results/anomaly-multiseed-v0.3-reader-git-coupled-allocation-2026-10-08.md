# 現revisionのcontrol／raw／archive容量準備

2026-10-08 JST。準備HEAD `f566bc40f5d915dbfe7406ab3e4d74588d5f9c3d`、production code `26cf5cab7cdd1a5c2eb3d45757b5d20d8010e7a1`。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## 保存した小さい単位

専用 `artifacts/preformal-reader-git-coupled-allocation-20261008-prep/`。source/science41件のworking/Git blob一致と先行code-save pin不変を確認。選択30sourceはphase592899B、最大87676B、head/status＋30blobをpre/post各32要求、予定64call。runtime閉包や新profile観測は行っていない。

現sourceのclosed JSON構造でrequest/binding/stop/inventory/manifest/proof/ackのwidth候補を保存し、同じ候補request/inventory pinと64callへ結んだ。candidate名のfileは実channel名として公開していない。identity、clock数値、row offset/frame/evidence pinはwidth placeholderであり、request・receipt・proof・ackの発行、native creation/close/witnessの代用ではない。

callerが独立に明示するraw maximaはsource stdout128KiB/stderr16KiB/receipt16KiB/partial raw64KiB、計229376B。head stdout128B、status stdout64KiBも各callへ固定。正常source bytesから失敗capを作らず、既存Parentの必要条件だけでこの候補を照合した。

| width候補 | bytes |
| --- | ---: |
| request | 983 |
| binding | 331 |
| stop | 186 |
| caller inventory（64call） | 21757 |
| manifest（64rowの幅） | 15090 |
| linked proof | 9883 |
| ack | 704 |
| 完成名7候補の合計 | 48934 |
| 子publisher最大pending＋並行する親stop pending | 15276 |

順次manifest→proof→ack公開と親stopの並行を候補へ計上。request/inventory/binding準備前後、未知のrename/診断IO失敗、全entry保持順や並行atomic予約はまだ実証していない。7完成control＋最大2pendingに各既存32KiB capを使う粗いreader単独枠は、archive512KiB＋raw maxima＋reserve128KiB込み1179648Bでouter1MiBを超える。

候補widthに絞ったreader単独モデルは同じarchive/raw/reserve込み948946B、残余99630B。ただしこのwidthは実コード上の新hard boundではなく、親identityの任意失敗出力も含まない。entry peak・global/memory・全失敗raw・後続writerによる残余保持の保証やcapacity passにしない。旧786782B/31entryモデルを新revisionへ読み替えていない。

## encoderとpartialの別の保存量

原recoveryの `partial-archive.bin` はProofVerifierが読む原raw inventoryの一つで、actorのinflightから読まれた元失敗rawである。新WorkerGitArchiveの `worker-git.bin` 追加frameとは別の保存量。partial rawの64KiB capを、新archive追加frameの64KiB予約と読み替えない。WorkerGitArchiveは原packet保持→canonical JSON/base64→gzip→128KiB frame検査→512KiB total検査→appendの順。既存検査拒否ではpending packetと原rawを保持し、容量合格やlease/ackに進めない。

同じ候補inventory pinで現在のencoder形式へstdout131072B/stderr16384BのSHAKEによる任意bytesを投入した一回のprobeを保存。入力canonical JSON196906B、gzip152199B、frame header込み152207B。gzipは既存131072Bを21127B超える。

これはencoder容量の検討用bytesで、eventが空・receiptがNoneのため有効なreceipt/recovery packetではない。実native出力や実worker失敗を観測した証拠ではなく、通常sourceの圧縮を任意失敗rawへ流用できず、allocationだけではencoder適合を示せないという所見。実64packetのtotal、gzip/frameとreceipt/eventのcoupled peakは未完了。

| 原証拠 | bytes | SHA-256 |
| --- | ---: | --- |
| preparation-result.json | 13725 | aacf921328bbbd6a44de10b4897c53d36d5d1fbca78e79bf984a03d22d5809ea |
| unverified-encoder-probe.json | 196906 | 7d061d355542b33f68c3037431d1bcbd9b57b09cf07253f80b8104a5d154f9c5 |
| unverified-encoder-probe.gzip | 152199 | 44fe8982ae154a26cb340400ff3828173dec99c67a8d7513cfa259418fc8c3e9 |
| candidate-inventory.json | 21757 | 1e3e0ea733d3d9c86601950c8d81c6fde01204aa5179621d7c89789665723045 |

準備rootは実測13file/422682B、専用512KiB/16fileの準備枠内、一回完了。helper36804/creation134358789785960938/tokenc072231464578b09c9326c3cb5f4172f0c571cc205465ff492bd40a1855f5f1cはexit0/CIM残存なし。新production変更0・profile再観測0・完成焦点反復0・worker/Job/pipe/native起動0・追加agent0。実Win ABI/exe/worker/native認証/全経路容量合格ではない。

## 次の境界

原recovery rawと新archive growthの予約を区別し、親子control/pending・親identity失敗出力・診断と各writerの保持順を元shared outerへ結ぶ。原packetを検証・保持したままframe/totalを拒否できる範囲を、writer開始前の予約と照合する小さいcode単位にする。snapshotをatomic reservationやglobal/memoryの代用にしない。

ReaderGitParent.create_nativeはroot/channel/clock/Job前拒否を維持。latest clean revisionのfresh source/runtime/profile/private policy/request/unusedroot、元owner保持限定launcherとexclusive準備は未完成。全7役whole.runを限定readerとして起動しない。旧HEAD/profile/pin/14source、producer非対称pre26/post24、使用済み親archiveを流用しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和や未測定rootへのreceipt移動、旧raw整理は行わない。unknown Close/Delete/既存Unclosed/未回収/IO・割込みでは元owner/原handle/Python/stream/buffer/pending/inflight/partialを保持し、blind retry/後続Git-workerを拒否。metadata/root exit/EOF/worker kill-wait/途中capacity checkpointは回収True/lease/ackではない。

## 同時に保存した先行CI

CI37674558981は外部fullHEAD `f5ff80eb1345cacf108278514161cf957fb91238`/attempt1、各minor3522/fail0/error0/skip237/source不変・全3job success。専用rootへ10raw/14pin/local-remote一致/共有29fixture必須28/runner v2 consistent_candidate・保存後照合。index2783B/af49381d318858272a3bc0ec8d0b2decfd7724ddf61d1eed43809dc44fa352b9。3.12/compare新版prerelease=true、3.14旧版・公式release/README metadata/blob/log/journal外部pin一致のみ、digest未取得/候補未採択。CLI7 6raw一致/skip1file既知CRLF6差両pin。

download5392/creation134358786524413250/token343141d1be587b6b937375e18964f0b0f3d99fd648fcd9f01511e5f82644cb7b、verification26064/134358786942748597/token4b3429776edaabe51838df7956e6ee9321253c3e20a5541bcf44323f4909486cはexit0/CIM残存なし。先行reader entryのCIを後続allocation/forwarding/native/容量/正式受入へ読み替えない。未保存37677397653/full37b7feb/3529予定、37680026029/full26cf5cab/3536予定は開始時in_progress、終端を再照会していない。doc-only新CI追跡なし。正式5残件/正式採択/最終受入は未完了。
