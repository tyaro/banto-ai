# initial-readerの保持順と容量残件（2026-10-07）

clean HEAD `463f3331ae3709058a6625707b7acc9c36eb8267` / code a12c3e9の選択9sourceをworking/Git rawへ照合。保存済み30source pinも不変。専用rawは `artifacts/preformal-reader-git-peak-plan-20261007-01/`、`coupled-peak-plan.json` は12328B / `615c691e0e88b0b9e5a2d6dce3ffd67e859e273e556b6338245a42ec602ef831`。

これはsourceに沿ったファイル保持順とJSONサイズモデルである。process起動、既存試験、profile再観測、native実行は行っていない。placeholderのrequest/identity/proof/ackを実証拠として公開していない。

## pendingとinflightの共存

channelは同一slotのpendingをexclusive保存・readback後、上書き禁止renameで完成名へ移す。子はmanifest→proof→ackの順に公開し、親のstopは並行して公開できる。未確認IO時はpendingを保持して再公開を拒否する。全6frameの完成名と全pendingが同時に存在するという前回の単純加算を、通常の公開順のピークとして扱わない。

正常callは元receipt/stdout/stderr、archive readback、exact leaseを確認後、その新inflight3fileとdirectoryを削除する。failed prefixは元3fileを保持したままproof/ackへ進み得る。resolverは追加partial-archive rawも扱えるが、選択した実actor/native executorはその別名fileを作らない。append失敗のpartial archive本体は `worker-git.bin` として同じ512KiB枠に数える。

## サイズモデル

64callの固定schema、64rowのmanifest/proof、指定root/path、pinのSHA-256長、native identityのABI整数を置いたモデルでは以下のJSONサイズとなる。モデル中の数値placeholderをnative観測や実コードによる新上限に読み替えない。

| frame | モデルbytes |
|---|---:|
| request | 1019 |
| binding | 335 |
| stop | 190 |
| caller inventory | 21990 |
| manifest | 15082 |
| proof envelope | 9906 |
| ack | 724 |

archiveは既存512KiB上限を使用。正常source（最大48839B）とclean statusを扱うモデルのinflight stdoutは64KiB、receipt16KiB/stderr64KiBを計上。親identity4callはverified receipt各16KiB/head各128B/clean status0B/stderr0Bとして計上した。親blob archiveは本モデルの対象外。

| 保持場面 | reader bytes | 親4identityを含むbytes | 親16entry＋診断reserve2を含むentries |
|---|---:|---:|---:|
| bodyのreadback／停止raw保持 | 695278 | 761070 | 28 |
| 正常manifest pending | 562904 | 628696 | 25 |
| 正常proof pending | 572810 | 638602 | 26 |
| 正常ack pending | 573534 | 639326 | 27 |
| 最後failed prefixのack／終端 | 720990 | 786782 | 31 |
| 失敗stdoutを既存1MiBまで保持 | 1704030 | 1769822 | 31 |

正常schemaモデルはreserve後917504Bと32entryに収まる。しかし実圧縮archive容量、任意失敗raw、controlの実サイズ、停止時write overshootは未測定・未強制である。capacity合格・native許可とはしない。診断2fileは既存128KiB/2entry reserveへ計上し、未測定rootへの移動は行わない。

## 次の実装境界

実owned Git executorはsource_blob stdoutの既存上限1MiBを使い、25ms周期でサイズを観測する。正常pinのsourceサイズを失敗出力の上限に読み替えない。最後のfailure raw保持だけでreader rootが1704030Bになるモデルが残る。

限定launcherのnative前検証で、この未解決範囲を拒否する。各exact callを元shared rootの残余bytes/entriesへ結び、原Job/process/thread/extra handleを保持したまま失敗出力も枠内で保存できる実出力経路と停止・IO失敗の小さい焦点確認を先に固定する。poll後の超過だけをhard boundと宣言しない。0-jobや途中成功prefixをackへ読み替えず、未回収時は後続Git/workerを拒否する。

その後に限定reader caller／launcher、最終clean HEADのfresh profile/policy/request/rootをexclusive準備する。全7役や旧rootを反復せず、上限緩和・raw削除・未測定rootへの移動は行わない。

helper47832/creation134358505036030703/token02f02efbedb73cec4be3e557e591221ab968d708400b8b6f35649c9e72a5bab5はexit0/CIM残存なし。critical ownerなし・native0・追加agent0。正式gate `s4_acceptance_not_frozen`、formal_permission=false、正式credit0、登録holdout観測未読、正式5残件を維持。
