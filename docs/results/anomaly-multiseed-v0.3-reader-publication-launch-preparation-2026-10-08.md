# Reader publication launcher資源の保持・入口接続準備

2026-10-08 JST。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。実データは保存済み合成dev8/smoke2のengineering読取り・記述報告だけ。追加agent0、新production module0、実worker/Job/pipe/exe起動0、runtime/profile再観測0。

## まとめて接続した経路

code e0f8fc4b0121bde9b1755bd7858b7ced3c01b09a。3production＋新testの4fileを一つのunitでcommit/pushした。

- ReaderPublicationLaunchPreparationはcaller-held kernel/stdin/既に返った原専用NativeGitPipes/controller/entry/context/storage/checkpointをcopy・検証・clock/root IO前保持する。原Popenをgetter/creation/binding IO前から保持し、原bind return、同HANDLE、原carrier bind returnを保持して、実request/inventory/root identity/clock/revision/binding pin/worker identity/entry pinへ閉じた32KiB以下の新memory contextを結ぶ。再bind・第二準備・sidecar消去・context改変は原と拒否資源を両方保持し、最初の例外へlatchする。
- 発行optionは非JSONのPython resourceとcontext value/pin。reader_worker_mainはparse/import/診断前に元argv/kernel/stdin/creatorを保持し、ReaderGitWorker→原Actor/control/storage→原senderをarchive FileIO前にarmする。closed未検証input objectの受渡し、foreign kernel/request/root/clock/binding/worker/entry pinを入口で拒否する。Actor constructorの原tupleとprobeへ同じinputsを結び、error metadata復元でも再armしない。
- 原FileIO unknown close、creation/import/copy/clock IO、割込みは同じ原Popen/creator/native/stream/raw/pending/error/Python ownerへ結ぶ。cached optionsはcreation/read/open/write/close/rename/nativeを反復しない。stdinは借用しcloseしない。
- operationが返っても専用creatorの原HANDLE close経路は未接続なので、返値を原return位置で保持しreader_publication_launcher_owner_not_reconciledで通常print/return前の原Python保持loopへ渡す。FileIO.closed、disk一致、sender deliveryを原native close/recovery/lease/ackへ読み替えない。

元NativeGitPipesはstdout/stderrの各read/writeを保持する。今回のCreatePipeは全てfake APIで、kernel発行・実限定launcher・cross-process HANDLE複製/明示inheritance・実child IO owner認証は未接続。Python resource objectを実Popen子へ渡したとはしない。専用carrierの別HANDLE群をstdio inherited最大3へ読み替えない。旧external v1/v2/v3/v4、request/entry/ack/proofへfield追加なし、新disk carrier file0。既存READER_BOOTSTRAPはreader_worker_main(sys.argv[1:])のまま発行しない。ReaderGitParent.create_nativeはroot/channel/clock/Job前拒否を維持する。

native_launch_authorized/capacity_pass/atomic_reservation/parent_ack_authorized/execution_authenticatedはfalse。正常composing snapshotは明示stub、Popen/creation/kernelはfake、main operationはspy。実小FileIO/fsync/channel/archiveのprotocol gateであり、実ABI/worker/pipe/native認証/全経路wall/容量合格ではない。

## 確認と初回timeout

新22distinct/最終AST unique22、取得できたbody23（pass22/error1）。初回helperのbody数と各verdictは未取得。最終source単一22success runではない。

| component | body | pass | error | 秒 |
| --- | ---: | ---: | ---: | ---: |
| 初回helper | 未取得 | 未取得 | 未取得 | timeout保全 |
| main原因1件 | 1 | 0 | 1 | 2.2376528999884613 |
| 未確定16件 | 16 | 16 | 0 | 30.894595100020524 |
| 新risk4件のみ | 4 | 4 | 0 | 9.525248199992348 |
| 新risk2件のみ | 2 | 2 | 0 | 3.383438099990599 |

初回main fixtureがio.json_bytesをreader invocationのcanonical JSONとして使い、末尾形式不一致で原保持loopへ入った。逐次log/試験専用Escapeがなく結果が取得できなかった。元PID47372/creation134359022572275102/token7d64dceca781d938e6b46b84dcc969db5d6848b6ff53a6ff2d587da8f80d13e4・専用script一致/critical_owner=false/実native資源0を照合し、helper-timeout.jsonを保存して元試験helperだけを停止した。これを通常終端・原native/unknown FileIO回収成功へ読み替えない。

1件の原因logを取得してcanonical fixtureとEscapeを訂正した。初回に実行された未確定prefixへ再入した可能性があり、反復0とはしない。先行完成focus/旧suiteの反復はしない。16pass確定後は新4＋新2だけ確認した。新riskは未検証入力object/sidecar復元/import失敗/正常返値後の原creator保持、親・子error metadata消去後の再arm拒否。最後の16内main試験期待を原owner保持へ更新し、完成16は再実行しない。新正常返値保持caseでその具体的残リスクを確認した。

各4保存componentの54source/science前後不変、他50は全component一致、先行forwarding共通50pin不変。変更4file safety0。science2は既定pinへのhash読取りだけ。code-save時54source/science working-Git/HEAD=origin/cleanを確認した。

原focus helpers: 47372は上述timeout停止・自身finally記録なし。42976/134359024519869766/tokenac95f41bfcb4774712b5cd184d491a3e9ad887d7aabe66a67586e0c3739e0c15はfailed、13376/134359025009839917/token6ebbbddf0b1a2dcab88d6d23a67234dc9f2fe271270a9cdec9cb62f49bc6e969、43244/134359027059485794/token262439f3b9aca92aa43c5b3a134dd60755c26be46f2db229fac9bf0adab1b043、47624/134359028244354563/tokenc4a9398c5f635edfb4c75212267db134798b838c61532a6f66d4bced5133c4d4はpassed。code-save46732/134359030399873010/token0f435161cf9d5dc3677581f1dc1e277454041484ecc6ffbaabfa2b773c6f57beはpassed。元live/executionのexact identity/tokenで区別する。

raw artifacts/preformal-reader-publication-launch-preparation-20261008-prep/。

- components.json 2041B/66f67211d5e873664cb1defd04658018023e937225d2b6d40e1a9c7e94693c07
- code-save.json 12775B/70b8e0dd8b780402c11605edba79b685700140012af2d32a6525245949182635
- focused-v3.json 17063B/55e8b8b1e3ca78300f0a5d891ceb5db7ea466cde5ab454cc21b82870f18da141
- focused-v4.json 17061B/68f904698574db4909015de36ef9c99960be63e4effe157aa7c444af686bde79
- focused-v5.json 17060B/36bc33a1ea14a20c3642b27018c08fedf474cc240fd89f6fab58b3549c078d32

初回code-save stdinのsrc import経路欠落（body/identity観測前）と、git由来でない不一致fullSHAによるCI空選択も別rawとして保持した。空選択をrun実行・終端へしない。以後はgitが返した実fullSHAだけを使用した。

## 同時に見つかった先行CI失敗の別unit

CI37717924409/fullfa82cf720df6a428ad0c4b344b0fe100e0bd05a0/attempt1/push/Phase 1 CIは両minor failure/compare skipped。元run.json/jobs.json/両failed-step logの4rawを専用artifacts/ci-diagnostic-37717924409/へ一度保存。各logは3725tests/errors4/skipped237。journal数値・source不変・local regression・runner候補の成功照合は追加しない。

4errorの原因は保持判定のisinstance(worker,ReaderGitWorker)がMock factoryでTypeErrorを出して元例外を覆ったこと。code b4366887f9b49509ae5722b41a3e683fd1586dbbは原classをimport時の固定referenceへ結び、未知factoryを回収ownerとして採用しない。1production＋新testの独立unitとして一回commit/push。外部failure4件だけと、factory置換後も原worker/actor/例外を保持する新1件が一回1.3084639000007883秒pass。全suite/完成22focus反復なし。初回補助scriptのprior filename置換ミスはFileNotFoundError/body0で別raw保存し、成功runにしない。

- CI failure-summary.json 4184B/ffe55f52a42611b6139a66894257abcfe54c8b058e64bf944c9c456b4b642497
- 型保持 focused-v2.json 17264B/fc77073777b2f9baa2e9fcda29cd12f497975eae2f77148ed2517065c3f4d501、log 1251B/d89c04ce8ef0f8fd43edcc38cee6a750164d4a51ebcf91e2eb8d800bb72560e1
- 型保持 code-save.json 8485B/8984202ca93dca9d53b9a72723a9b8810a08b487e251ccf7e5e5790b21570a21

修正後55source/science working-Git/origin/clean、名前30source/各phase32要求/予定64Job、phase747843B/最大archive94523B。これは完全runtime閉包ではない。先行22の最終sourceにCI修正を追加したものとして保存し、22をこのsourceの単一runへ読み替えない。

新CI37721863325/fulle0f8fc4b0121bde9b1755bd7858b7ced3c01b09aと37722343194/fullb4366887f9b49509ae5722b41a3e683fd1586dbbはin_progress観測。doc-only追加CIを追わない。

## 次の境界

実限定launcherのkernel/専用creator/child-local HANDLE受渡し、元Popen HANDLE creation、原owner close returnとchild-local publication IOのtransport認証は未接続。fresh最終clean source/runtime/profile/private policy/request/unusedroot、全writer同request/root atomic予約、親将来failure raw/diagnostic、partial rawとarchive growthの独立予約、entry/context実bytes、packet/gzip/frame/receipt/partial coupled peak/global/memory/exclusive準備を維持して次unitを確認する。同期Peek/Read/Write/caller間wall・停止は未実証。準備完成前にnative入口を開かず、全7役whole.runを限定readerとして起動しない。旧HEAD/profile/pin/14source、producer pre26/post24、旧容量model/候補widthを流用しない。
