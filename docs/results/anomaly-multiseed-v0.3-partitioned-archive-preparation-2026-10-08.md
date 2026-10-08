# 全planned-callの新partition archive準備（2026-10-08 JST）

## code保存とmetadata continuation

code c5bffdb1e23d1563020d7fc2345fb1bfc1bad5c3をunit一回commit/push、origin一致・cleanで保存した。原code-save helper11428/creation134359253656061229/token802b4ba1a377bad4508e5ac982a0be83c1060d34beb4e890d9242a60f654eaccは2文書working CRLFとGit LFのraw equality AssertionError/exit1でfailedを保持。原script5786B/65437e82d31280bcbb2fa27447934468c8bf0457ff85b64efb0855d3d621489d、failure37B/ad6267c5a8f4f2ceb833b7bba226b0393e7bd53e86056197da8228c82aa88bdb、診断両pinを保存した。handoff649CRLF/report50CRLFだけの差でsource/codec/CI/native回収/Sol容量失敗ではない。tool traceを原process stdout-stderr全byte fileへしない。

別code-save-continuation.pyの47552/creation134359254702227521/token5c38bcd203027282f692c2b60a08c4b2ad10f4d5d02b6bb32900888a55300ae8が同30秒・Git batch各512KiB16entry/output1MiBで未保存metadataを完了。code-save-continuation21392B/b2e178ad840b9b3aee2e8d25dbc0cd9d5aec162e631ce276fd4929d0cbc767faは62source working-Git exact/science hash metadata/code docs2 working-Git両pinとCRLF限定差/原focus4raw-components/元helper/旧3root不変を照合。原failed helper書換え/原同script/試験/codec再実行0。今後文書を明示LFで書き、既知差がある原code docsの両pinはそのまま保持する。

未保存CIは先行37752779492/git実full21b4b4fadc1bc856b286324907b5ac5a9ea42010（開始時attempt1/push/Phase1CI/in_progress、3864算術予定/journal未確認）と新37756831995/git実fullc5bffdb1e23d1563020d7fc2345fb1bfc1bad5c3（新push後workflowName原値Phase 1 CI/push/in_progress、attempt/jobs/終端未固定、3885=3864＋新21算術予定/journal未確認）。新gh stdout164B/6e71021275732d7901088501171613e60b28266549c1d1ce99cb8b6a4009a79dをci-state.json内に保存。先行compactはtool trace f1a824の観測metadataで元CLI bytes未保存、原raw全部へしない。先行状態再照会/全終端download/local回帰/runner0/doc-only新CI追跡なし。

今回doc-only3文書を一回skip ciへ集約し、postはmetadataだけ62working-Git/science/最新docs3/当該code docs2両pin/全raw/元helper exact identity/CIM同original不在/HEAD-origin-lsremote-clean/旧3root不変を一度照合する。production/test追加0/完成焦点反復0、専用512KiB32entry/reserve128KiB rootを閉じる。原failedをpassedへ書換えない。

## Scopeと原owner

開始2026-10-08T09:07:42Z、HEAD/origin c986ddb22cc9c01267e8c02b2c734b7e6b494af1一致・clean、先行元8helper同creation-token不在/repo helper-critical ownerなし。既存worker_git_archiveの新PartitionedArchivePreparationと新testを同目的unitへまとめた。追加agent/runtime-profile再観測/旧suite/完成focus/13AST監査/native実行0。

原caller owner/checkpoint/allocationをvalidation-copy-clock前保持し、新closed anomaly-v03-partitioned-archive-preparation-v1を照合する。fieldsはformat/context/call_growth_maxima/archive_max_bytes/formal_permissionだけ。caller contextはrequest_pin/inventory_pin/revision/root/root_identity、callごとのleaseは登録順0から固定する。1..64個の独立growth最大値を全て最初に合計し、512KiB以内のcaller archive最大値へ照合する。完了枠の割引なし。これはメモリ上の算術契約で、OS/all-writer atomic予約ではない。

同原owner object/clock object/context・正しい次leaseの原PacketPartitionPreparationだけを受け、全frame/manifest/full raw readback後にcallのgrowth/offset/packet manifest pinを登録する。original returned view/packetとimmutable pin bytesを判定・次callback前に保持する。各call独立最大値と全体最大値を照合し、recovery prefix後は次callを拒否する。全planned-call非空coverageだけをbundleへ結び、全raw/外部manifest pin・順序offset・packet幅・trailing bytesなしを確認する。原partial-archive.bin raw slotをnew archive growthの余裕へ流用しない。64は予定call数上限であり64Git Jobを実行した結果ではない。

original allocation/returned packet/row/incoming marker消去・callback KI・reentrant register・ledgerと表示rowの同時置換・cached bundle差替えは原第一例外/原owner/packet/途中view-readback/bundle/拒否incomingを保持する。metadata復元で解除せず、再codec/再registration/relaunch/reap/recloseへ落とさない。cached prepare/plan/bundleはclock/codec反復0、executeはnative/publication未準備でAPI/IO/clock前に拒否する。

旧v1 packet/request/entry/context/ack/proof/pin解釈は変更しない。旧_path/_inventory/_append_frame/SavedWorkerGitArchive/WorkerGitArchiveと先行PacketPartitionPreparationの6AST spanをGit bytesへmetadata照合して不変確認した。完成旧焦点を実行した結果ではない。create_nativeのroot-channel-clock-Job前拒否437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7c不変。actual generate/reader/legacy archive IO/原native owner-Popen bridge/child transportへの接続なし、borrowed stdin close0。

## 新ケース

engineering stub event/caller宣言context/owner object/empty temp directoryと実memory codecだけ。初回は全call coverage、全将来最大値拒否、closed fields、bool幅拒否、完了後最大値変更、foreign owner/clock/inventory、重複lease、call独立超過、recovery prefix、partial coverage、返値改変/参照消去/reentry/KI、row/bundle改変、external repin、cached/native早期拒否を確認した。zero/partial名のcaseはpartial prefixを観測したもので、zero-bodyを別観測へ加算しない。reviewは元ledgerと表示rowの同時置換の新1だけ。

| component | 新body | 結果 | 秒 |
|---|---:|---|---:|
| 初回 | 20 | pass/fail0/error0/skip0 | 0.2728249999927357 |
| review ledger/display同時置換 | 1 | pass/fail0/error0/skip0 | 0.016096600040327758 |

新21distinct/body21/最終unique21、pass済み20/旧suite/完成focus/native反復0。別source/runであり最終source単一21success runではない。各62source-science pin前後不変、他60全component/先行60共通pin不変、変更2file safety0/new production module0。名前30合計849510B、最大worker_git_archive123874B/a9b770f61632ad88c9cc0eac12fb324e6b4d274768e34637ff513636b64e9a0c。generatedは62準備pin内/名前30外、名前30/予定phase32ずつ64Git Jobはruntime未閉包。旧幅/profile/cap/pinを新HEADへ流用しない。

| raw | bytes | SHA-256 |
|---|---:|---|
| focused.json | 24886 | 50d724cadcea41fb322dee087b3b3a17b331384ee9f3c75064b0f094e23034d3 |
| focused.log | 4614 | c0832243ac1eea7d931b2fc5fa879f75b412c52e93b4a54da89a7beeb20b1436 |
| focused-v2.json | 23665 | 75ec732fab7d975edced5ebf0ed8db0a67e758925a22d65bc68e6d4f1da4b7e3 |
| focused-v2.log | 346 | a0f09c0b102099aa8f2bb8d48b4aea4323c667101df9f2e1f5a39e7f64a6f40f |
| components.json | 18280 | 12af2e49dec3b3c07dd94a571f7209c6e65da054345f9329b715b9daeb9c8abe |

元23680/creation134359248975149120/token76c3e8777b5c7d3c4a62ba65bd808697a44b61fc7f28f8e4e78655240bfe780cはlive/execution passed・full identity一致・CIM同original不在。

元40568/creation134359249748082840/token2d5531068af32976501dd17345927237b08bc7ef004d496b8a0b4f758d2be824はlive/execution passed・full identity一致・CIM同original不在。

元13128/creation134359250324475801/token0fc64c250759e075a94a660714df8b47fee470a13424ea471708d6c3c4a88115はlive/execution passed・full identity一致・CIM同original不在。

初回CIM保存のPowerShell token_sha256属性参照は実start_tokenではなくnull比較だった。原helpers-before-git.jsonを保持し、helper-token-confirmation.json1152B/d913029b81e42fb90ab3ebd15ff2b07c7b2c77e34b800dfab2f4876ad4f82576で欠けたstart_token全object比較だけ完了した。CIM再実行0/PID単独判定なし、原process stdout-stderr全byte fileの捕捉ではない。

## 保存と残リスク

unit確認後code commit/push一回、doc-only追補をskip ciへ集約。専用root artifacts/preformal-partitioned-archive-preparation-20261008-prep/へ原rawをexclusive保存し、30秒累積metadata上限/Git batch各512KiB16entry/output1MiB/512KiB32entry/reserve128KiB/single128KiBを維持する。旧packet分割28file147369B/continuation8file61328B/CI3844root38file10282900Bへ追加しない。原post timeout/原packet154696B圧縮拒否/旧failed helpersをsuccessへ書換えない。

先行CI37752779492/full21b4b4fadc1bc856b286324907b5ac5a9ea42010は開始時compact一度attempt1/push/Phase1CI/in_progress、終端未固定。3864算術予定/journal未確認、状態不変の再照会/終端download/local回帰/runner0。新code push後のCIはGitが返す実fullSHAだけを一度選択し、doc-only新CI追跡なし。実journal count/実summary取得前に期待数/pinを発行しない。

native/atomic/capacity/lease/ack/authは全てfalse。このunitは原child/native owner/request/rootの実認証、原API/Job/process/threadの回収、Win ABI、実archive FileIO/cross-process実publicationを発行した部品ではない。buffer/object/dict/tuple/一時JSON/コピー/decoded raw追加保持/RSS/他writer/global coupled peakは未測定。allocation/view/manifest/payload幅をnative許可や容量合格にしない。

次は同request/rootへ親identity任意将来failure raw/diagnosticとentry-context実bytes、原partial・new archive growth・保持codec/native buffer/object overheadを独立量で計上し、全writer atomic予約/exclusiveと原owner保持へ結ぶ準備。fresh latest-clean runtime/profile/private policy/native request/unusedroot、実callsite Create/Assign/member return-HANDLE owner-attribute lifetime/stdio実owner継承/cross-process/child endpoint-close-rename raw transport認証は未準備。全経路wall-stop/実loaded runtime-source/業務異常子孫/正式5残件・正式採択・最終受入は未完了。formal gate=s4_acceptance_not_frozen/permission=false/credit0/holdout未読。元archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64/outer1MiB32entry depth2 reserve128KiB/global321MiB672entry/cleanup30秒poll0.25秒/stop保持/native入口早期拒否/全7役whole.run限定reader実起動禁止を維持。
