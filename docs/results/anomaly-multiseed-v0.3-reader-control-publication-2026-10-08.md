# v0.3 child control公開と元keeper/terminal保持（2026-10-08）

## 保存範囲

code `6c9acf0fdb20f1d8971b24e0873fc5c7fbf09821` はoriginへpush済み。gate=`s4_acceptance_not_frozen`、formal_permission=false、正式credit0、登録holdout観測未読。新production module0、選択名30source/各phase32要求/予定64Git Jobを維持するが、完全runtime閉包ではない。

Actorはcaller-held append contextのrequest/inventory pin/root identity/14control maxima/同じcheckpointからControlPublicationAdmissionを発行し、元Python actorへIO前sidecar保持する。実readerの最終publisherは同じ原gateをmanifest/proof/ackへ渡す。旧形式/defaultの追加gateなし経路を維持し、新JSON fieldで旧pinを読み替えていない。

同じ原nativeへのactor参照をtransport/keeper IO前に保持。keeperは原actor/gateをledger IO前にcacheし、同じendpoint/owner sidecar/checkpoint/inventory pinを照合。control stream/error未解決時はcore close前・cached completionの両方を拒否する。原Job停止/empty/root終了/creationの観測はcacheを維持し、再reap/read/closeしない。gate.error/foreign linkはlatchし、後のmetadata消去で解除しない。

terminalは原gateと拒否gate/sidecar/原例外に付いたgateを診断前に保持。原body errorとack IO errorは別に保存し、swallowed IOでも通常報告・終了前に保持loopへ渡す。保持loopは新lease/Job/再publish/reclose/reapを作らず原Pythonを残す。既存native critical owner catchは同じ原keeperを維持する。

3公開名の最終照合は、原FileIO close return位置、closefd、rename return、元fd由来file identity、原canonical raw/published raw/current full raw/pinと同じ残余checkpointへ結ぶ。readback失敗は原成功rawと変更raw/例外を保持し公開再試行しない。FileIO.closeはPython fd所有streamの観測で、Win HANDLE CloseHandle returnではない。

## 新焦点のみ

初回11件は9pass/error2/fail0、5.0895249000168405秒。2errorはraw改変に対する親fenceの例外拒否と、fixtureで直接作ったkeeperのbackrefに関する試験側assertionだった。本体の拒否を両原logへ保全し、assertion訂正後の2件だけ0.802248599997256秒pass。先行pass9反復0。

source照合レビューでkeeper/terminalのclock/inventory/sidecar同一性を補強し、新1件だけ0.1574599000159651秒pass。拒否sidecar自体の元snapshot保持を補強し、新1件だけ0.09947560000000522秒pass。新13distinct/最終unique13、最終source単一13success runではない。各36source/science pin前後不変、変更test/keeper/terminal以外の33pinは全4component一致、先行control gateとの共通28pin不変。変更6production+新testの7file safety0。clean code-saveは36working/Git一致。

正常2callの原raw/archive/leaseとmanifest/proof/ack、semantic failed last prefixの原失敗raw保持、0-job拒否、manifest partial write、proof/ack unknown close、body error分離、swallowed IO、metadata消去、公開後raw改変、cached keeper完成拒否、core close前拒否、foreign gate/clock/sidecar保持を確認した。fixture構築/helpersだけを参照し、旧suiteをdiscoveryへ重複登録/実行していない。

fake Win API/Job/creation/private policyと小さい実FileIO/channel/archiveのprotocol gate。pipe executorは参照fixture receiptを渡すspy、retention loopは試験専用_pause escapeで観測する。実Win ABI/実pipe/exe/worker/全経路wall/容量/native認証の合格ではない。native0/profile再観測0/追加agent0。

## 原証拠

root `artifacts/preformal-reader-control-publication-20261008-prep/`。原helperは各live/executionへPID/creation/tokenを保存し、exit1/0/0/0、CIM残存なし。

| helper | creation_time_100ns | start_token |
| --- | --- | --- |
| 16228 | 134358852337683547 | 8c2e110203f725c7b920744382d391edc0678fd6021dcc126e9ea9984ac27971 |
| 49468 | 134358852716585502 | 39d4bb73dd80c3e36db0aae9a5749a0a1e3604c5ce893ca196f2da00ac2fcae8 |
| 32092 | 134358853289043072 | 63fe05eb797356aae22d167261da56293b74a40451fe51001ca39ba2083fcc96 |
| 43584 | 134358853751707074 | 044762363c55cd440c792aad91e2a7c949aca63a1cde3694ccecd198cde73180 |

| raw | bytes | SHA-256 |
| --- | --- | --- |
| focused.json | 11440 | 5b312cc2b86655421ac027e04a00e535ca50f6f0e7f27fee4f812e29fead74e7 |
| focused.log | 5173 | 6ec84e9fba8a6843de96f670a0d6d605b1e7c34be514205fadfb4eac19bc2044 |
| focused-v2.json | 11437 | b1b43b8fe8b36945571925791b50b3a61eb6070b978e3af4a561c0bea146e3b6 |
| focused-v2.log | 598 | db420c54a206ac66c5faf89f1db09d0d26753c2426418c315c5cd557a8b4999b |
| focused-v3.json | 11438 | 44e6a95343addf1072dd047969e71dcd44e8984336b93c2cbf78a7a9843ce2e9 |
| focused-v3.log | 360 | 25047b4dd6f0b4a441fb6611f4b0e645b928a776808963fd71191957d68f52b1 |
| focused-v4.json | 11439 | ab951e48739a11a28c219dfb0baa9b3cb46beee448591a014e078bc71de71846 |
| focused-v4.log | 334 | 87b3662eaf258a7b2888835467793175554f07191f5c2f73043828e65a1f7338 |
| focused-components-final.json | 2204 | cc3b3807f43fdfecea2a813485e3ab327ff97557f42528bebdd88dbe20e8dd8a |
| code-save-checkpoint.json | 7501 | fdaddc0fe538b46de5bbfb3a56a4ba224bd67fd3a9209add5e7a24126536e2ab |

## 次の保存単位と限界

Parent側inventory publisher、親binding/stop、初回request bootstrapへのgate発行は未接続。全publisher参加/親identity将来失敗raw/diagnostic/global/memory/atomic並行予約/coupled peakも未完了。child local gateの未解決IOを親が直接観測するprotocolは未実装で、ack公開と全writer同期の保証にはしない。

次はParent側inventory保存と同じrequest/inventory/control context/原ownerを結ぶ小さい境界。原partial rawと新archive frame growthを別量で計上し、新entry/context保存bytesも含める。snapshotをatomic予約に読み替えない。最新clean revisionのfresh source/runtime profile/private policy/request/unusedroot、原owner保持限定launcher/実control-packet-raw容量/exclusive準備が完了するまでReaderGitParent.create_nativeのroot/channel/clock/Job前拒否を維持。全7役whole.runを限定readerとして実起動しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/outputとcleanup30秒/poll0.25秒は維持。unknown Close/Delete/Unclosed/未回収/IO・割込みでは原Popen/Job/process/thread/extra handles/Python owner/raw/stream/pending/inflight/partial archiveを保全しblind retryなし。旧source/profile/モデル/pinや完成焦点/CI/native/使用済みrootを反復・流用しない。正式5残件/正式採択/最終受入は未完了。
