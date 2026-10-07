# v0.3 上位callerの未解決publication保持（2026-10-08）

## 原ownerを終了前に保持する境界

Code `2e4eae8d37a4410948dc8e4cbb8a8a4387407e0b`。既存reader moduleのParentPublicationRetentionとretain_parent_publicationsを、実generate_and_readのOSError/ResourceStop/KeyboardInterrupt等のcatchから通常診断・結果公開・返却より前に接続した。元request bootstrap/inventory gate/current sidecar/rejected sidecar/caller plan/原入力tuple/stream/pending/raw/error/Python ownerを保持する。元pending観測も一つずつ保持してから次のfallible属性を読み、secondary diagnostic割込みで先行資源を失わない。

未解決IO時は元保持objectへ0.25秒pauseを繰り返し、open/write/close/rename/source/fence/read/reapを反復しない。pause割込みは最初の原例外だけ保持する。metadata/pending/error消去やsidecar復元で元保持を解除せず、foreign保持object/第二worker例外も原と拒否資源を両方保持する。未知closeをFileIO.closed/disk一致/keeper returnで解除しない。healthyな観測済みpublisherと追加gateのないdefault file-directed経路は新保持を発行しない。

既存UnreapedWorker/UnreconciledWorkerがある場合は元process/handle/stop_fence/fence_errorと同じ例外を保持objectへ結び、元supervisor keeperへ診断IO前に渡す。新native keeperへ置き換えない。原callable/例外をkeeper IO前に保持し、返値とreturn_observedを元return位置から保存する。返却/割込み後もPython publication IOは保持し、二度目のkeeper entryは拒否する。このreturn記録はnative回収・lease/ack/auth認証ではない。

初回bootstrap失敗はPopenがなく、kill/wait/native closeの対象を生成しない。retention中は通常のresult.json/supervision.json公開へ落とさず、新worker/後続Gitを開始しない。元worker keeperの既定30秒cleanup/poll0.25秒、既存shared clock/各root/memory/output上限は変更しない。

## 新焦点の原runと訂正

初回新13件は11pass/2fail/error0/skip0、4.192301400005817秒。2failは、先に完了したproducerのsupervision.jsonを不存在と期待した試験側の誤り。本体はretentionへ到達しており原log/rawを保存した。完了producerの証拠を保全し、active readerの未公開supervisionへ期待を訂正、失敗2件だけ1.1659645999898203秒pass。keeper再入拒否・元callable/return保持補強の新1件だけ0.3495334000326693秒pass。pass済み11/先行13/旧suite反復0。

新14distinct/最終unique14、最終source単一14success runではない。各43source/science pin前後不変、fixture訂正の他42pin不変、reentry補強の他40pin不変、先行bootstrap共通40pin不変、変更3file safety0、clean code-save43working/Git一致。上位generated moduleはreader選択30source外なので準備pinへ別に加えた。名前30source/各phase32要求/予定64Jobを実ロード閉包へ読み替えない。新production module0。

上位generate catch自体を実行し、native/runtime/creation/profile/Popen/supervisorはfake/spy、実小FileIO/channelと保持pendingを使用。retention loopは試験専用_pause escapeで解除し、cleanupは試験所有Python fileのみ。実worker/Job/pipe/exe起動0、native0/profile再観測0/追加agent0。実Win ABI/native認証/全経路wall/容量合格ではない。

## 原rawとhelper

専用 `artifacts/preformal-parent-publication-retention-20261008-prep/` は512KiB/32file/reserve128KiBを維持。

| component | focused bytes/SHA-256 | log bytes/SHA-256 |
| --- | --- | --- |
| 初回13・fail2保全 | 13403 / 6a8f690046c649137bc594fd83e192dc792d60e0bd2a4822b8696bd81b7079a4 | 5472 / 06241aaa717f9a3c45625d79884280360a8fc99b2c14d99c7f2e7a25921927c7 |
| fixture訂正2だけ | 13402 / 0d7a4213c7dccd0200e035c2380588ad3781463d61dbf3db2a8346601d39e1cb | 646 / 2ed6165a3f8ce5dea7bb89279f8a72f5315cbabf3499240d1735c5d37a9beb67 |
| 再入補強1だけ | 13402 / 1391e41ebf161985971bbb19fe9da0cd768daa87f9a8c80d34520fd0e477f123 | 372 / 724e58bd64095a77672b45e98132f9b7cfe91d95948fe629965c540a4e928aa6 |

components2121B/0cc2639582ed963b13c2840b51b6a6ef4a58639d2de16c93b895324c0b6223fa、code-save8465B/2f4ca0e824068ce5dae3555b22036718a824248ef6081065e0c99f28637e9197。

元helper `17608/creation134358896838046948/token769f9dc36d4ecf96add067ede2205f5291bb86e6c78fb99e911cce4bcec93a58 (failed)`、`33212/creation134358897224878554/tokend60743a8489e54c3b561ea5741c2c5b508b98aa10c9a82a16c896eef77dd8837 (passed)`、`39672/creation134358898546305742/tokend2f34531e7d2a20358f06b777533ee66ed389f12c5712b838c26806bd54ae6de (passed)` はlive/executionのcreation/tokenを保持し、exit1/0/0・CIM残存なし。全helper終了/critical ownerなし。PID再利用を元processと同一扱いしない。docpush後の43working-Git/science/docs3/焦点6raw/既存CI28pinのhash照合のみ/CLI両pin/元7helper終了は新専用post-save-checkpoint.jsonへ保存する。

## 次の境界と未完了

child localのunknown publication IOを親が直接観測するprotocolは未実装。既存ack/proofの完成rawやworker exit、metadata/marker不在/root exit/EOF/kill-waitだけで全writer同期・native回収/lease/ackを許可しない。次は子local ownerの原close/rename/raw witnessと親fenceのexact request/root/inventory/worker identityを結ぶ拒否境界を対象sourceだけ確認する。

全writer同request/root予約、親identity任意将来失敗raw/diagnostic、原partial rawと新archive frame growthの別計上、entry/context実保存bytes、atomic並行予約/global/memory/coupled容量は未完成。snapshot/sidecar/context/cached rawをatomic予約/native許可へ読み替えない。fresh latest clean source/runtime/profile/private policy/request/unusedroot、元owner保持限定launcher/実容量/exclusive準備は未完成。ReaderGitParent.create_nativeのroot/channel/clock/Job前拒否を維持しnative入口は開かない。全7役whole.runを限定readerとして起動しない。

formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。実ロード依存/業務異常子孫・正式5残件/正式採択/最終受入は未完了。旧raw/pin/失敗/使用済みroot/上限/stop保全を維持。
