# v0.3 Git close原証拠／sink admission再照合（2026-10-08）

code `30d38f4485040d649fcdc7c052c06f3fa6ea642b`。clean文書HEAD `6412654be770954fac084c99fb2c80b757984bb9` からの小さいopt-in単位。

## 保存した境界

- `GitSinkAdmission`はexclusive FileIOの元fdをfstat前に保持する。`bind_io_close`は元adapterを検証／checkpoint前に保持し、同じGitPipeClose/output/native/streams/keeperを確認して元keeperへ明示bindする。再bindでは元adapterと拒否adapterを保持する。
- closed sinkのcheckpointはmetadataだけで許可せず、原adapter/keeperのcached Job・kernel、原native/output、元named read close、実FileIO.close eventのapi/fd/return/file identity/raw pin、元spoolのclose/pending/errorを確認する。元pathのregular identity/countと全raw再読取り/hashを原readerの観測へ結び、保存枠の未保存残余を再照合する。
- 原stream/eventを読取りより前にclose_pendingへ保持し、成功済みrawもclosed_observationsへ保持する。同じサイズのraw改変で原成功rawと今回の変更rawを両方保持する。unknown Close/Delete／IO/clock割込み／元close/reader error／pending rawでは同じ原nativeへerrorをlatchし、後続admissionを拒否する。原closeやreap/readを反復しない。
- sink1本のclose直後も元eventが保存済みなら容量checkpointを通せるが、この途中checkpointは全Job/core/quiescence/lease/ackの完了ではない。cached closeも全raw再照合する。admission自体が新しいCloseHandle/FileIO.closeを実行することはない。

これはfake Win API／CreatePipe／spawn／Job/process/creationと実FileIO/fsync／3B非空stdout／空stderr/root計測のprotocol gate。実Win ABI/exe/worker/native認証／全経路wall・容量合格ではない。原close結果のio_released／parent_ack_authorizedはfalse、keeper completionは未完了のまま。実worker入口への新sink/close保持、実transport/stop-reap/output_limit時元Job停止、pipe receipt publisher、並行atomic予約/coupled容量は未接続で、ReaderGitParent.create_nativeのroot/channel/Job前拒否を維持する。

## 焦点と原失敗の保存

初回13 unittest呼出しはfixtureがPeekNamedPipe/ReadFileをreader構築後に設定したため全13件setUp error、本体到達0。原rawを保全してfixture順序を訂正した。次の13本体は12pass/1fail/error0、1.1875522秒。残る1件はfixtureの例外注入がread handle74ではなく旧stdio62だけだったため、注入先を訂正してその1件のみ0.0643626秒でpass。pass済み12件と旧suiteは反復0。

新13 distinct本体／最終unique13で、最終source単一13success runへ読み替えない。正常close/cache/非空raw・途中sink checkpoint/core未完了、metadata/declared adapter拒否、欠落event/foreign fd/file identity、同サイズraw改変、clock/partial close割込み、再bind、unknown read closeの後続拒否、late pending rawを確認した。参照fixtureはmoduleとsetupのみ、旧TestCaseを重複discoveryしない。

各36 source/science pin前後不変、変更test以外35pinは全3component一致、先行handoffの変更production以外共通34pin不変。変更2file target safety／最終unique13／clean code-save36working-Git一致。新production module0／名前30source／各phase32要求／予定64Jobを維持するが完全runtime閉包ではなくfresh profile/policy/request/unusedroot未準備。旧HEAD/profile/pinを流用しない。全helper終了／critical ownerなし／実native0／追加agent0。

raw: `artifacts/preformal-git-sink-close-link-20261008-prep/`

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 11272 | `2293c49ddc6844e703aa310b50e2858e098ea38c6f9d101f5201b67ef62629f2` |
| focused.log | 31659 | `0045c36a767b32bd78345b359c279a959b627b8d868e29f2118c28c3efc538b0` |
| focused-v2.json | 11270 | `ec26d4d8a355263f8b006889a9db0070d518c5b1d1e287ffdf363e30e6a6fd4c` |
| focused-v2.log | 3306 | `ae601325bb7c18acd3667475b7c86ec55d199f780a56e49194acae06fcfde1ae` |
| supplement.json | 11270 | `ddc108597d7e4bac4146d7df72b55c74b9486697202258098900fbe6de0faf01` |
| supplement.log | 303 | `f9338e427d8b037566a8c0261e771907dca7f4abe290f1deca664b00bd072508` |
| focused-components-final.json | 1245 | `f3f01ede952e98933f4f8bf107e81e126b3e0c1b37eef3f1d4f3d99e258bc497` |
| code-save-checkpoint.json | 470 | `f58838c9ccfa95433313523f21f3ab83cdcc6847da959d69e275f6c9f6f07012` |
| initial-failure-analysis.json | 271 | `2410d2cc72c61afc5126d5de63867b05b2cd3b906febe967cfa2c0e9d6f05465` |
| ci-first-empty-query.json | 254 | `2fd974fcc8a80c3b960c8315244e3b1a58e8d72cd750a881f798cba8b707ceba` |

helper43312/creation134358680131483725/tokencd87f6e03f383c48cd7827c1640c35954328819ed94ee61b53ffddea37a120ef はstatus=failed／CIM残存なし。
helper10276/creation134358681133377657/token23b05dda73536e9819f377b5a3f7913ebf1493e8c170002c24526ad318a71b19 はstatus=failed／CIM残存なし。
helper35624/creation134358682163237507/tokenda8fc225cb2f006b19d51b7aadf568855fa0ec32d35835d7385a3c91d0b92ee2 はstatus=passed／CIM残存なし。

元identity/tokenをlive/executionへ保存し、PID単独で過去processと同一扱いしない。最初のCI --commit照会は実HEADと異なるSHA入力で空選択、原記録を保全し実fullHEADで新CI37660790390（full30d38f4485040d649fcdc7c052c06f3fa6ea642b/各minor3468予定・進行中）を確認した。空選択をCI実行／終端へ読み替えない。

## 次の単位

原pipe/sink/spawn/output/reader/close/keeperを使う実transport executorを小さく接続する。原returnと全raw/witnessからpipe receipt publisherへ渡し、exact call/元shared rootの保存枠とstop probe/output_limit→元Job停止を結ぶ。原Python ownerをterminal catch/keeperへ渡して終了で失わない。未回収・unknown close/Delete・既存Unclosed・IO/割込みで原Popen/Job/process/thread/extra handle/stream/buffer/pending/inflight/partial archiveを保持し後続Git/worker拒否、blind retryなし。

同期Peekのwall/停止と並行parent/child予約/coupled容量は未実証。最新clean HEADのfresh source/runtime/profile/policy/request/unusedroot、原control/packet/rawの容量と元owner保持の限定caller/launcher／exclusive準備が完成するまでnative入口を開かず、全7役whole.runを限定readerとして起動しない。旧14source/pin、producer pre26/post24を親111/111へ流用しない。

未保存CI37654425831（full8eba6cfa9dd3fcf633e314908327f7449fe8a9d0/3444予定、直近3.12success・3.14進行中）、37655643970（full27be314059e8f092b994258ada176dab3c17c717/3455予定・進行中）、37660790390は各終端時の原run/attempt/jobs/fullHEAD/workflowを固定して新専用rootへ一度保存。成功時だけlocal/runner v2、失敗は小さい原因確認と保全。doc-only新CI追跡なし、完成CIは反復しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。上限緩和／未測定rootへのreceipt移動／旧raw-root整理なし。正常readback済み新inflight固定3fileと新directoryだけ整理可能。旧正常モデル786782B/31entry／generic失敗1MiBのreader1704030B>reserve後917504Bを新cap/requestへ読み替えない。

formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。先行全repository safety30秒timeoutは未確認保全・再試行なし。実ロード依存／業務異常子孫／正式5残件／正式採択／最終受入は未完了。
