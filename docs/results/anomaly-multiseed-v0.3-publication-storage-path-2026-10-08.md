# Publication storage経路のまとまった保存（2026-10-08 JST）

## 保存点

人の「進めて下さい」で継続。開始01:17:17 UTC、HEAD/origin `617d6c5abf31930e0992e726f5eea9324f17f551`、clean、元helper5件はcreation/token照合で残存なし、repository worker/critical ownerなし。新code `0b80bf7d21f42e22a358e895ca160f1142fc6f81` は4production＋新testの5fileを一回commit/push済み。途中保存はローカルだけ、文書追補はskip ci。

既存carrier/control/archive/sinkと親・子の原ownerへ同じstorage gateを明示opt-inで接続。新production module0、新disk publisher0、旧request/entry/context/ack/proof JSONへfield追加0。旧pinを新形式へ読み替えない。

## 実装した境界

- `PublicationStorageAdmission`は原endpoint/request/clock、caller inventory raw/pin、root identity、allocation、checkpoint、Python ownerを検証・copy・IO前保持。独立したclosed allocation `anomaly-v03-publication-storage-allocation-v1`を32KiB以内のlinked plan/pinへ結ぶ。caller copyは元callbackによる変更へ追随しない。
- frame40B込み最大32KiB、archiveは既存512KiB以下のcaller上限、carrier failure rawはframe2本分以上/64KiB以下、親failure rawは閉じたstdout/stderr/receipt/任意partial maxima。caller inventory各callの失敗raw最大値を別に保持し、正常source bytesからfailure capを生成しない。原partial-archive.bin capを新archive growthへ読み替えない。
- 保持byte bufferの必要枠は128×4096B＋20×32KiB＋8×frame cap、caller枠は2MiB以下。これはPython object/decoded構造/stdlib/runtime/RSSの測定やmemory合格ではない。
- 元shared checkpoint/実root snapshot32entry/depth2の現在量へ、全14将来control枠、全call最大rawとinflight directory、独立archive最大追加枠、carrier失敗raw/2entry、親future raw、reserve128KiB/診断2entryを加える。観測済みcontrolやarchiveの量を後のstatで割り引かない。保守的二重計上による拒否を維持する。
- Actor/Parentのarmから原CP gate、原writer/append admission、原sink/bootstrap、原carrierへ渡す。control公開、archive追加前後、sink作成前後、carrier IOの同じroot/clockで再照合。archive実bytes/追加分もcaller cap内でなければ拒否。post-spawn時は同じ元nativeへstorage ownerをIO前に保持する。
- original/sidecar参照の消去、plan/clock/owner変更、IO・unknown close/KIでは元stream/fd/raw/buffer/pending/例外を保持してlatch。controlの原unknown close例外もstorageへ即時保持し、別例外へ置換しない。既存cached ChildGitKeeper/terminal/上位ParentPublicationRetentionから原storageを隠せず、reopen/reclose/read/reap/append replayなし。
- `native_launch_preview`は同じ原plan/owner/返ったroot観測を保持するだけ。atomic予約、fresh runtime閉包、原child IO owner transport認証、native許可はFalse。ReaderGitParent.create_nativeのroot/channel/clock/Job前拒否を維持する。

snapshotは全writerのatomic並行予約/global/memory代用ではない。actual all-publisher登録、初回request bootstrap前の上位発行/forward、限定launcher、実carrier、原child owner認証は未完成。legacy/default経路はstorageなし・追加keywordなし。

## 新試験と失敗保全

| component | 結果 | 秒 |
|---|---|---:|
| 新20初回 | 17pass/1fail/2error | 4.4580753 |
| 失敗3の期待訂正＋新4だけ | 6pass/1fail/error0 | 4.6019034 |
| control原unknown close伝播の未成功1だけ | pass | 0.4659339 |

初回3件は先行channelを保持したfixture rootの残余不適合と、拒否がarchive前に起きることへの期待違い。実root拒否は維持し、正常接続を確認する3経路のsnapshotは明示stubとした。実先行channelを残したままcreator発行前に拒否する新ケースを別に保存。旧rootを整理してpassへ変えない。

新unknown FileIO closeケースでstorage原例外への即時伝播不足を検出。terminalはstreamを保持していたが、storage側も同じ元KIで停止するよう修正し、その未成功1件だけpass。FileIO.closed metadataは原close return観測の代用にしない。FileIO.closeはWin HANDLE CloseHandle returnではない。

新24distinct/最終AST unique24、body28呼出し、最終source単一24success runではない。pass済み17/以後成功6/旧完成焦点・旧suite反復0。各49source/science pin前後不変、他46全3component一致/先行共通44pin不変、変更5file safety0。clean code-save49working-Git/最終component/HEAD=origin一致。新module0/名前30source/各phase32要求/予定64Git Jobは完全runtime閉包ではない。

fake Win API/Job/creation/private policy/Popen/queue＋実小FileIO/fsync/channel/archive/rootのprotocol gate。composing正常経路は明示stub snapshot、pipe executorはfixture receipt spy、retention停止は試験専用_pause escape。test cleanupはそのfixtureのPython filesだけ。実worker/Job/pipe/exe起動0、実Win ABI/native認証/全経路wall・capacity合格ではない。

## 原rawとhelper

専用 `artifacts/preformal-publication-storage-path-20261008-prep/`。旧rootへ追加/再実行せず、専用512KiB/32entry・reserve128KiB内で保存。

- 初回focused15417B/`ed5454cac90f4431fdce402cb27e01775b5653e38cd2dc28a5c2a79b07642374`、原log12964B/`b87d2d71e9f0b0f9eb466a43183fdf9f41d805210c3169a900d8e9e2b237dff6`。
- 第二focused15414B/`36e2f2bcf0018c783c47baf66fe01601b31ed12d21138e1978819ee2c8fcb908`、原log2745B/`99146de3cab32c42d8de460220310aaec7fb38e6950e91598fc20f2c01a8c0b1`。
- 最後focused15415B/`44d26b5d97d8a5f39717434bb3046479920d964c4bcc07c191e797b585a7a474`、log364B/`9596542381d74b73563df8d272f33507fa7c9f61d047a4dc5b8368abbcc0aa87`。
- components3424B/`dc05fed4f06d6f57a71497873e02bf461dc292304de1e73a2667c7ee39e96ee0`、code-save14725B/`ed63e99719a5e30d4446cc28d2497f00a8ce1a0566414805dd6977813c54dd8a`。

元helper3件は同じlive/execution identity/tokenを保持。28084/creation134358968580554824/token`c2f40360aa9cc07f534612e019bcb57f3d17c59649ffffa2f3794f5aacc5164a`はfailed/exit1、28156/134358971626707583/`302db62c10015e9f10d9249028d728282be89e9767b6d621176de85b6487c968`はfailed/exit1、36104/134358972303268447/`7a191a2a2236e270d36f84c749541c231a4f020428739910c6cd697f3d5250d2`はpassed/exit0。CIM残存なし、PID単独で再利用processと同一扱いしない。保存後49source/science/docs2/raw/HEAD-origin-clean/元3helperの照合をpost-save.jsonへ保存する。

## 次のまとまった単位と制約

fresh closed external descriptorから、このallocationをParent/bootstrap IO前、entry/Reader/Actorへ同じcaller pinで発行・forwardする。旧v1/v2/v3へ新fieldを足さず、inventory発行順とroot identity取得前後の原ownerを固定する。今回のarmは既存ownerへの明示opt-inで、上位実caller発行は未接続。

その後も全writer同request/root atomic予約、親identity任意将来失敗raw/diagnostic、原partialとnew frame growthの別予約、entry/context実bytes、coupled peak/global/memory、fresh latest-clean source/runtime/profile/private policy/request/unusedroot/exclusive限定launcherと原child owner transport認証を確認する。同期Peek/Read/Write/caller間wall・停止は未実証。cap緩和/未測定rootへのreceipt移動/旧raw-root整理はしない。全7役whole.runを限定readerとして起動しない。

今回はCI終端読取り/download/local回帰/runner候補照合の追加0。既存37704906810/full e300474・37708333072/full9a83455、新先行full112f3cd、新full0b80bf7の終端未照会。実fullSHA以外や空選択をrun実行/終端へ読み替えず、後続で専用rootに一度保存する。完成CIと旧failure rawは反復/新code受入へ読み替えない。

formal gate `s4_acceptance_not_frozen`、permission=false/credit0、登録holdout観測未読、正式5残件/最終受入は未完了。人の進行指示に従い、保存後heartbeatをまとまった機能経路単位でACTIVEへ戻す。重複実行を避け、human stop/Sol容量エラーは原owner/証拠保全後PAUSEDを維持する。
