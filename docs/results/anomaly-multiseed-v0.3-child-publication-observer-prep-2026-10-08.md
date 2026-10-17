# v0.3 子publication observer接続準備（2026-10-08）

## 今回の保存範囲

Clean文書revision `081abc0503ee8a5dcfc75737e36d8ea62ae47f63` / production code `e3004745c83962b73ed21cf8415385a1328df4e4` の対象sourceだけを確認した。新production/test変更0、unittest/完成焦点/native/worker/Job/pipe/exe/追加agent/profile再観測0。44source/science working-Gitと先行44pinは不変。これは接続準備・source auditであり、実observer/carrier発行、native認証、wall/容量合格、positive ackの試験ではない。

## 原ownerが存在する位置と接続の欠落

1. `ControlPublicationAdmission.publish` は元pending/stream/fd/rawをIO前保持し、原FileIO close return、no-replace rename return、公開raw/file identityを元return位置へ結ぶ。FileIO.closeはPython owned fdの観測でWin HANDLE CloseHandle returnではない。
2. `publish_archive_ack` はmanifest→proof→ackを公開し、その後に3名の `verify_publications` を行う。したがって完成ackは最終検証より先に存在する。最後のverification/checkpoint/返却前のIO・割込みで失敗した場合も、子の元actor/gate/terminalは元raw/stream/errorを保持する必要がある。
3. `ActorTerminal.run_guarded` はack前後・通常返却前に同じ元gate/sidecarを確認し、pending/error中は原Python保持loopへ渡す。子のlocal保持objectを親が直接観測するcarrierは未接続。
4. 親 `ReaderGitParent.bind` は元PopenをIO前保持して元process HANDLEによるcreationへbindingを結ぶ。現在のfenceはack/proof/True verdict候補を保持しても子close/rename ownerがNoneのためFalse。cached拒否は再観測なし。
5. 実上位 `generate_and_read`→`supervisor.supervise` はstdin=DEVNULL、stdout/stderrをexclusive fileへ向ける。`READER_BOOTSTRAP` は `reader_worker_main(sys.argv[1:])` を呼び、pipe_ioを発行しない。既存child内Git CLI pipe transportをworker→parentのobserver carrierへ読み替えない。
6. supervisorはFalse/例外なら元UnreconciledWorker/Popen/handle/stop_fence/fence_errorを保持し、legacy kill/wait/Closeへ進まない。既存guarded retentionは同じ元fenceを呼ぶが、cached denialはIOを反復しない。worker exit0や完成rawを子local close成功へ読み替えない。

## 次の実装境界を固定

まず同じ元child gate/actor/verification/completed-original/stream/rawへ結ぶlocal保持objectを小さく準備する。capture入力と返った観測objectを検証/copy/clock/readback前に保持し、copy失敗やcallback改変でも先行objectと拒否objectを失わない。manifest/proof/ackの各原close-observed return、renameの元return位置、fd/path identity、元rawとpin、同じ元request/inventory/root/clock/revision/binding/worker identityを必要条件にする。未確認returnをclosed metadata、complete bytes、success flagsから生成しない。

Local保持objectはPython owner/streamを持つためJSON native資源へ入れない。将来のbounded canonical carrier envelopeは元local rawから導いたpin/contextを含めても、独立transportの代用ではない。3rawを無条件に一つの32KiB envelopeへ入れず、payload/encoded/frame/buffer/保持raw/partialの別量とhard boundを決める。今回の保存は将来carrier bytes/entries、並行予約、global/memory/coupled peakを未計測のまま許可しない。

次のlocal captureだけでは親のFalse拒否を解除しない。原launcherが作成したcarrier/kernel/HANDLEを同じ元Popen/creation/root/request/inventoryへ結び、元read/write/close返値とfull readbackを確認する境界は別単位。carrier自体の最後のclose/readbackが不明なら元ownerを保持して親拒否のままとする。新fileへのwitness保存や最後のmarkerを、当該witness publisher自身のclose成功証明にしない。

Descriptorを拡張する際は新closed形式とfresh pinを用い、旧request/entry/context/ack/proofのpinへfieldを追加しない。14control全将来枠へ未登録carrierをこっそり追加しない。別read2をinherited最大3へ読み替えず、既存handle/stdin借用と元clock/上限/stopを保持する。

## 対象sourceを固定した位置

| 元境界 | source行 | 保存内容 |
|---|---:|---|
| [generate_and_read](../../src/banto_ai/anomaly_v03_preformal_owned_generated_attempt.py#L519) | 519–945 | 原source segment pinをboundary rawへ保存 |
| [reader_worker_main](../../src/banto_ai/anomaly_v03_preformal_owned_saved_attempt.py#L423) | 423–494 | 原source segment pinをboundary rawへ保存 |
| [ReaderGitParent._deny_child_publication](../../src/banto_ai/anomaly_v03_preformal_reader_git_worker.py#L412) | 412–434 | 原source segment pinをboundary rawへ保存 |
| [ReaderGitParent.bind](../../src/banto_ai/anomaly_v03_preformal_reader_git_worker.py#L382) | 382–393 | 原source segment pinをboundary rawへ保存 |
| [ReaderGitParent.create_native](../../src/banto_ai/anomaly_v03_preformal_reader_git_worker.py#L226) | 226–233 | 原source segment pinをboundary rawへ保存 |
| [ReaderGitParent.fence](../../src/banto_ai/anomaly_v03_preformal_reader_git_worker.py#L395) | 395–410 | 原source segment pinをboundary rawへ保存 |
| [publish_archive_ack](../../src/banto_ai/anomaly_v03_preformal_reader_git_worker.py#L27) | 27–66 | 原source segment pinをboundary rawへ保存 |
| [ControlPublicationAdmission.publish](../../src/banto_ai/anomaly_v03_preformal_worker_git_archive.py#L252) | 252–316 | 原source segment pinをboundary rawへ保存 |
| [ControlPublicationAdmission.verify_publications](../../src/banto_ai/anomaly_v03_preformal_worker_git_archive.py#L318) | 318–353 | 原source segment pinをboundary rawへ保存 |
| [ActorTerminal._control_pending](../../src/banto_ai/anomaly_v03_preformal_worker_git_terminal.py#L54) | 54–77 | 原source segment pinをboundary rawへ保存 |
| [ActorTerminal.retain_control](../../src/banto_ai/anomaly_v03_preformal_worker_git_terminal.py#L79) | 79–83 | 原source segment pinをboundary rawへ保存 |
| [run_guarded](../../src/banto_ai/anomaly_v03_preformal_worker_git_terminal.py#L153) | 153–182 | 原source segment pinをboundary rawへ保存 |
| [ChildChannel.acknowledge](../../src/banto_ai/anomaly_v03_preformal_worker_stop_channel.py#L404) | 404–416 | 原source segment pinをboundary rawへ保存 |
| [ParentChannel.fence](../../src/banto_ai/anomaly_v03_preformal_worker_stop_channel.py#L265) | 265–326 | 原source segment pinをboundary rawへ保存 |
| [_retain_guarded](../../src/banto_ai/anomaly_v03_process_supervisor.py#L36) | 36–54 | 原source segment pinをboundary rawへ保存 |
| [_stop_ack](../../src/banto_ai/anomaly_v03_process_supervisor.py#L30) | 30–33 | 原source segment pinをboundary rawへ保存 |
| [retain_until_exit](../../src/banto_ai/anomaly_v03_process_supervisor.py#L57) | 57–70 | 原source segment pinをboundary rawへ保存 |
| [supervise](../../src/banto_ai/anomaly_v03_process_supervisor.py#L97) | 97–276 | 原source segment pinをboundary rawへ保存 |

Source spanは当該revisionのASTから抽出した参照位置で、実行した試験数ではない。全file working/Git pinとsegment pinはrawへ保存し、巨大なsource/rawを展開しない。

## 証拠・元helper終了

専用 `artifacts/preformal-child-publication-observer-prep-20261008-prep/`、512KiB/32file/reserve128KiB/各保存raw32KiB以内。source-audit.json 19669B/b2778b674420ee62e62274c326f569d3c4f745cafdbc4ade3b99310e798fa534、observer-boundary.json 6681B/dfbacc5440913447a675b1690e9a630c6e2e7197954cb96b7742ecf8bf8ed71d。元source helper `49812/creation134358917243318555/token6dc692619dd2e969a4b0db685dba5b4e49692683fb61091b4e6c141ebf48c31b` はexit0/CIM残存なし。完成焦点/native/profileを反復していない。

CI37701667430（外部full4776152f7ace2ab0c8bbcd4d22175d096f9c2cdc/attempt1/push/両minor3618）は全3job success/fail0/error0/skip237/source不変。job3.12=113066311972、3.14=113066311745、compare=113079528290固定、新専用 `artifacts/ci-diagnostic-37701667430/`へ10raw14pin/local-remote一致/共有29必須28/runner v2 consistent_candidateを一度保存。summary2577B/f942b3d4050fe96cd5bda344e8a745eb05fdb1589a4201363e58c3b0373973b4、index2783B/aa0f5b330974056d83e3cd0a3cfa6282e04fb6e2680cbb2d5ac1eccdfb5aec9b、CLI sidecar2138B/2c1bd90d1123e437f64ef0a2c771787569503ecf0a55b39047b6b7ba74a2c004。全job20260927.320.1/prerelease=false、公式release/README metadata/blob/log/journal外部pin一致のみ、digest未取得/候補未採択。CLI7は6raw一致/skip1file既知CRLF6差両pinを保持。このCIはbootstrap revisionの観測で、新observer/native/容量/正式受入へ読み替えない。

元download `39252/creation134358915863384995/tokenf1ec9f3b83923798cee9dff23b05a4288bbe19b557ff4ed4544ea922bcef0bda`、verification `1448/creation134358916353643908/tokend9aa0effd124c18ad199e945347593963afba78199d1cd441bd6416998b9d446`、origin保存 `47220/creation134358916679904238/tokenc4cb2c885de43b0b066e44e74627aff846e7ae37cec2df96fb52a0c187034d89` はexit0/CIM残存なし。全helper終了/critical ownerなし。PID再利用は元creation/tokenで区別する。docpush後44working-Git/science/docs3/prep2raw/CI14pin/CLI両pin/HEAD=origin/clean/元4helper終了を専用post-saveへ照合する。

未保存CIは37703472925（full2e4eae8d37a4410948dc8e4cbb8a8a4387407e0b/3632予定）と37704906810（fulle3004745c83962b73ed21cf8415385a1328df4e4/3642予定）、開始時in_progress。完成CI/焦点は反復しない。doc-only新CI追跡なし。

## 維持する未完了項目

ReaderGitParent.create_nativeのroot/channel/clock/Job前拒否を維持。fresh latest clean source/runtime/profile/private policy/request/unusedroot/限定launcher/実control-packet-raw容量/exclusive未準備。新module0/名前30source/phase32要求/予定64Git Jobは未閉包。原partial rawと新archive frame growthは別量。全writer同request/root予約、親identity任意将来失敗raw/diagnostic、entry/context実保存bytes、atomic並行予約/global/memory/coupled peak、同期Peek/caller間wallと停止、loaded runtime/source/業務異常子孫は未実証または未完了。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry/depth2/reserve128KiB/global321MiB672entry、cleanup30秒/poll0.25秒を維持。古いsource/model/profile/pinを新cap/request/proofへ流用しない。旧raw-root整理/上限緩和/未測定rootへのreceipt移動/全7役whole.run限定実起動なし。

formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。正式5残件/正式採択/最終受入は未完了。
