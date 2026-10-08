# Publication carrier経路をまとめた試行（2026-10-08 JST）

## 範囲と保存

人の停止後、一回だけ少し大きい単位を試す指示で実施。開始時は2026-10-08 00:45:21 UTC、HEAD/origin `706de3e0f8e631b93f58d33a18ffd9ea64848ba9`、clean、元helper/worker/critical ownerなし。heartbeat `banto-10` はPAUSEDのまま。

子local capture → bounded送信 → 親受信/creation/context/full raw照合 → fence拒否 → 子terminal/cached keeperと上位callerの原owner保持を一つのcode保存へまとめた。code `112f3cd0cf2973213ca70b1d5337e8c423468246`、3production＋新testの4file、一回commit/push済み。途中のレビュー・fixture訂正はローカル保存だけで、途中code push/CIは発行しなかった。文書追補はskip ci。

これはfake Win APIと実小FileIOを使うprotocol経路。実worker→parent carrier、実限定launcher、実Win ABI/pipe/exe/native認証、全経路wall・容量合格ではない。親ack/auth/atomicはfalse、native入口拒否を維持する。

## 接続した経路

- 既存archiveへ明示opt-in `PublicationCarrier`。原creator/kernel/native/read/writer HANDLE/API/checkpoint/owner/入力tupleを検証・IO前保持。Job用stdout readerへ転用せず、未spawnの専用原creatorに限定。同方向再bindは原・拒否双方を保持してlatch。
- CP gateの`arm_publication_carrier`から、3公開名の原close/rename return/full rawを保持した既存local captureを送る。PCR1＋length＋SHA256の40B headerをpayloadと別量でcaller frame capに計上、frame全体は最大32KiB。4096B以内のWriteFileで原buffer/count/returnを保持、short/False/unknown/KIは再送しない。
- 親は同じ原creator/read HANDLEを保持し、原Popen/HANDLE creation returnとbinding、request/inventory pin、root identity/clock/revision/worker identityを固定して受信する。Peek/ReadFileは最大4096B、保持read attemptは128まで。既読prefixのコピー履歴を積み重ねず、上限到達時は原buffer/count/partial frameを保持して拒否。
- 完成frameのcanonical closed payload/digestを照合し、3公開名の全raw pin/fd-path identity/countを再読取り。元shared checkpoint後にも全rawを再読取りして原rawと変化rawを保持する。返った観測objectはvalidation前に保持。cached経路は元frame/payload/pin/ownerをメモリ照合し、native/file/creation IOを反復しない。
- 子publisherのsend返値/unknown pendingは同じgateからactor/terminal/cached原keeperへ見える。上位`retain_parent_publications`も原・sidecar carrier/例外/stream/buffer/rawを保持し、metadata消去で原IOを解除しない。元native keeperを再生成しない。
- 親candidateは完成bytes/full rawの整合性だけ。原child-local close/rename ownerの実transport認証は未接続なので、fenceはcandidateを保持してFalse。HANDLE close、io release、lease/ack/native回収を発行しない。sender/receiver双方の原creatorと未close handlesは保持する。

新disk publisher/file/entry JSON field追加0。既存request/entry/context/ack/proof pinの読み替えなし。借用stdio/inherited最大3を増やす実launcherは発行していない。default local publisherはcarrierなし、既存file-directed経路を維持する。

## 新試験と保全

| ローカルrun | 結果 | 秒 |
|---|---|---:|
| 初回新16 | 15pass/fixture fail1/error0 | 9.2008107 |
| fixture訂正の失敗1だけ | pass | 0.5559897 |
| 原例外固定/再実行拒否/親checkpoint改変の新3だけ | pass | 1.7513945 |
| 保持read attempt上限の新1だけ | pass | 0.5519058 |
| 上位caller原carrier保持の新1だけ | pass | 0.0857702 |

初回のfake Peekはavailableを32768に丸めていたため「超過を初回read前に拒否」の試験期待と不一致。そのfixtureだけall availableを返すよう訂正。原log/失敗rawは保全。pass済み15/先行完成焦点/旧suite/native反復0。

新21distinct/最終AST unique21、body呼出し22、合計試験12.1458709秒。最終source単一21success runではない。各48source/science pin前後不変、他45は全5component一致、先行共通44pin不変。変更4file safety0。clean code-saveは48working/Git/最終component一致、HEAD=origin。新production module0、名前30source/各phase32要求/予定64Git Jobは完全runtime閉包ではない。

fake API/Job/creation/private policy/Popen/queue＋実小FileIO/fsync/channel/archiveのgate。pipe executor/親独立inventory checkpointの一部は明示fixture、retentionの停止は試験専用_pause escape。実Win ABI/実process/worker起動0。追加agent0、runtime/profile再観測0。

rawは専用 `artifacts/preformal-publication-carrier-path-20261008-prep/`。旧rootへ追加せず、専用512KiB/32entry・reserve128KiB内で保存。原focus/helpers/componentsを残す。

- 初回focused15030B/`5902ba4590450e8a29874f447c5e6a5f6929b1deb5a47caaf89a93a4aaff8c59`、原log4784B/`8e88883f6bb47ee1591455f6e5b2a958705b4d1757c14ab92e454dff65f8a2cb`。
- components-final-v2 3845B/`2511b9055b3012071749c2dda6788c64c9a7280f2af105ee1762d44326ad5ded`。
- code-save14335B/`de8fc9e187cc51cb3baa947a54c17667ef674844b8de08fb155aeaf9311f8581`。

元helper5件は各live/executionに同じPID/creation/tokenを保存。初回13932/134358949947762340/`0b628950422c9b57f30b3dd57001967e60523ae3184e3a0b083294a9ebc958fa`はfailed/exit1、以後16644/134358950470985999、47888/134358951587823777、26000/134358952297421312、30172/134358953268496965はpassed/exit0。各元tokenを保持し、PID単独で再利用processと同一扱いしない。保存後CIM/head/origin/docs/raw/source照合はpost-save.jsonへ保存する。

## 限界と次の単位

frame cap/128 read attemptは保持量の拒否境界。同期Peek/WriteFile/ReadFileのblocking・caller step間wall/stop保証、実kernel buffer boundではない。actual carrier raw/encoded/buffer/pending保持をcoupled容量へ計上し、同じ原launcher/Popen HANDLE creationとcross-process原child ownerの認証を別単位で準備する。native入口はその前に開かない。

全writer同request/rootのatomic並行予約、親identity任意将来失敗raw/diagnostic、原partial rawとnew archive frame growthの別予約、entry/context実bytes、global/memory/coupled peak、fresh latest-clean source/runtime/profile/private policy/request/unusedroot/exclusive限定launcherは未完成。snapshot/cached raw/sidecar/候補frameをcapacity pass/native許可にしない。上限緩和/旧raw-root整理/未測定rootへのreceipt移動なし。

CI37704906810/full e300474/3642予定、37708333072/full9a83455/3658予定は今回再照会・再保存0。新code full112f3cdのCI終端は未照会。旧CI/失敗rawを新codeの受入へ読み替えない。正式gate `s4_acceptance_not_frozen`/permission=false/credit0、登録holdout観測未読、正式5残件/最終受入は未完了。

今回、公開をcode一回＋doc-only一回に集約できた。ローカルの小さい保全と失敗ケース限定確認は維持した。総作業時間の短縮率は比較測定していない。heartbeatはPAUSEDを維持し、人の次の指示を待つ。
