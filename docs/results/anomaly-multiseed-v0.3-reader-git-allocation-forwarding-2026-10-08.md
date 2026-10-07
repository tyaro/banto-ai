# 外部plan pinからParentへのraw allocation forwarding

2026-10-08 JST。code `26cf5cab7cdd1a5c2eb3d45757b5d20d8010e7a1`。formal gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。

## 保存した境界

allocation付きexternal planは `anomaly-v03-preformal-initial-reader-git-pipe-plan-v2`、pipe_raw_limits必須のclosed canonical JSON。既存v1のfields/形式は維持し、v1に追加fieldを付けたりv2からallocationを省略したりして旧pinを読み替えない。

上位generation_publication_budgetの既存32KiB caller descriptor/pin readerが、revision/outer/channel/private policy/fresh profile/source pinsとallocationを照合してresolved planへcopyする。既存shared clock/linked budget開始後も元descriptor pinから再読取りし、同じresolved planだけをgenerate_and_readへ渡す。新sampler/clock/phase resetなし。

実generate_and_readはplanをroot/profile/runtime IOより先に保持/copy。source namesに対するallocationをproducer/reader supervisor開始前に検証し、Parent.createへ同じpipe_raw_limitsをopt-in keywordで渡す。allocationなしでは新keywordを渡さずdefaultを維持する。Parentから先は既存exact64call inventory/raw pin/admission/actorへ結ぶ。forwarded flagをnative/lease/ack/採択に読み替えない。

## 新焦点と原失敗

raw `artifacts/preformal-reader-git-allocation-forwarding-20261008-prep/`。

- 初回7件5pass/error2/fail0、0.5178363秒。参照fixtureのROOT置換を保持したまま実caller fixtureを作り、registry読取り前に停止。原log保持。
- fixture ROOTの復元順だけ訂正、error2件だけ0.6522768秒pass/fail0/error0/skip0。pass5/旧suite反復0。新7distinct/最終unique7、最終source単一7success runではない。
- 各41 source/science pin前後不変、test以外40pin両component一致、先行allocation共通35pin不変。変更3file safety findings0、clean code-save41working/Git一致。
- 新形式/external pin/allocation copy、v1/v2 field不一致拒否、cap raw改変拒否、shared clock内pin再読取り/linked budget forwarding、開始後改変でstage前拒否、実callerのprofile IO前copyとParent keyword、bad capで両supervisor前拒否を確認。
- composing runのstageとsupervisorはfakeで、実producer/reader/全7役/nativeを起動していない。実saved synthetic dev8/smoke2や登録holdout観測も本unitでは読取り0。

| 原証拠 | bytes | SHA-256 |
| --- | ---: | --- |
| focused.json | 12958 | 40c2817fcc90f4bad4a96aee6bcd6cf9b18de6ab073483c91cbaab1b09a407ec |
| focused.log | 5475 | 5bc301f0725bd1c4262d1542f16db62e80dffb255bd87c5b1f4c8bf25a990731 |
| focused-v2.json | 12956 | 1cebf1358c4d7ed15ca878d0c26b330e70bf7fad1992321c9a5dd2eb27122d2c |
| focused-v2.log | 618 | 3ba9eaf2039fef989c903538f90bbf4354920b4ecc5205833318fab0a16ccab3 |
| focused-components-final.json | 1089 | 16e58e2ebc9c298e71ce31acd77bd514a3d1cba3b0531d067bdf621a97bbd1bb |
| code-save-checkpoint.json | 7287 | 7e8ede2fec25b45d8e36360aa5a8546e14008eed7b2cd3ab8ae12ad0f3f2db3e |

focus10720/creation134358772698525411/token0f37d6aa5ab685590321576bcd518e899043f9343758313d88102cc7b0631470、訂正31804/134358773475776992/tokenfc2f5d718e6e5da9ea1e69a34979cc1e8cad0da142c884142462fda344bde2ebはexit1/0・CIM残存なし。全helper終了/critical ownerなし/native0/追加agent0。fake profile/shared budget/stage/supervisor＋小さい原canonical fileのprotocol gate、実Win ABI/exe/pipe/worker/native認証/全経路容量合格ではない。

## 残る容量・停止境界

上位からallocationは届くが、parent-child request/binding/stop/manifest/proof/ackとpending、archive/raw/gzip/frame/receipt/partialのcoupled peak・並行予約・最大残余は未固定。次はこの保持順/最大値を同じrequest/root/callに結び、native前の容量拒否と原owner保全を固定する小さいunit。snapshotをatomic reservation/global/memoryの代用にしない。

latest clean revisionのfresh source/runtime/profile/private policy/request/unusedrootと元owner保持限定launcherは未準備。create_nativeのroot/channel/Job前拒否を維持し、準備完成までnative入口を開かない。新production module0/名前30source/phase32要求/予定64Jobは未閉包。旧14source/profile/pin、producer pre26/post24、旧容量placeholderを再利用しない。全7役whole.runを限定readerとして実起動しない。

archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持。unknown Close/Delete/既存Unclosed/未回収/IO・割込みでは元owner/Popen/Job/process/thread/extra handles/Python/streams/buffers/pending/inflight/partial archiveを保持、blind retry/後続Git-worker拒否。metadata/root exit/EOF/worker kill-wait/途中checkpointは回収True/lease/ackの代用ではない。

## 同時に保存した先行CI

CI37672383958は外部fullHEAD `2213c0910390129158a0bd433bff94a786df8204`/attempt1、両minor3514/fail0/error0/skip237/source不変・全3job success。専用 `artifacts/ci-diagnostic-37672383958/` に10raw/14pin/local-remote一致/共有29必須28/runner v2 consistent_candidateを保存。index2783B/6f68f8f23d7ae4d83d7c220a3ae1a602c99c748a633edaa3edf7779d170ab102。全job20261004.327.1/prerelease=true/公式外部pin一致のみ、digest未取得/候補未採択。CLI7は6raw一致/skip1file既知CRLF6差を両pin保持。本forwarding codeの実native/容量/正式受入へ読み替えない。
