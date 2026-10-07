# v0.3 worker stop channelの部分公開・startup保全（2026-10-07）

code保存点 `e5ff97567a62764048576ce10606ce72bb6ab684`。先行channel `aaca57c`／stop fence `01ab74f`の小さい追補。正式gateは `s4_acceptance_not_frozen`、`formal_permission=false`、正式credit0、登録holdout観測未読。

## 変更と停止保全

- 新requestはchannel v2。frameを同じ測定rootの固定 `*.json.pending` へexclusive保存し、fsync・raw pin/canonical readback後、既存 `_rename_no_replace` で完成名へ公開する。完成名だけをbinding/ackとして読む。上書き禁止とframe32 KiBを維持する。
- 失敗したpending、完成したが公開/最終readbackに失敗したframeを保全する。再write・旧root整理・上限緩和は行わない。実接続のroot inventoryには最大4 pending＋4完成frameとcompact proofを含め、既存outer/root reserve内で再準備する。これは容量の実測合格ではない。
- Parent.bindは最初のlive/creation/IO照合より前に元Popenを保持し、expected binding pinをwrite前に保持する。BaseExceptionを元binding_errorへ保持し、再bindを拒否する。
- Parent.fenceは未公開bindingでもstopを先に発行し、binding不在/expected pin未取得でFalseを返す。stopのpartial staging失敗でも原Popenとguarded fenceを保持し、kill/wait/closeへ進まない。
- Childはpartial bindingをpendingとして扱う。partial stopは新Job禁止のヒントとして永久latchするが、ack=Trueの根拠にはしない。ackのpartial write/readback/rename失敗後も無再arm。
- Child.wait_for_bindingはcallerの既存started_at/wall内で最大poll0.25秒、残余が短いときはその残余だけ待つ。deadline/読取り/sleep割込みで停止し、元例外を保持する。

## 焦点試験と保存照合

新しいpublication/startup classだけ13件、2.500131秒、fail0/error0/skip0。partial binding中の並行probe、supervise＋on_started bind＋stop_fenceの実関数を使ったfake Popen保全、stage/final readback失敗、request読取り割込み、partial stop/ack、上書き禁止rename、公開中断、共通deadline、startup割込みを確認。先行channel21件とstop fence17件は反復していない。

source/test/scienceの選択11 pinは前後不変、変更2file `scan_repository(paths=...)` pass。全repository safetyは先行e4cbの30秒TimeoutExpiredで未確認のまま、再試行/上限変更なし。初回helperはregistryの保存先指定ミスで試験開始前に停止（実試験0）し、helperと失敗を保全、v2で正しい既存registry metadata pinを用いた。登録holdoutの観測は読んでいない。

raw root: `artifacts/preformal-worker-stop-channel-publication-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 3849 | `2c5c01179f2218846ce5800cf6d20eac86afe99c98693fa0be0fefeda42c8f05` |
| focused.log | 3053 | `b491db6d5b6542aab8f44f6b22f69a94e218e7f078cbe3726a340b988d749dfa` |
| code-save-checkpoint.json | 440 | `c2317bd2f994b3076fa6967a29586123e29a7339d87eaa68cb8dd7cc0eb21663` |
| preparation-failure.json | 255 | `8c298035f6c6d91385c63da381c20cdb43e3427e5b951466fc9891108424106a` |

code-saveはHEAD=origin/clean・11 working/Git pinを照合。全helper終了、critical ownerなし、新native0・追加agent0。新CI37583002436（HEADe5ff975、各minor3191件予定）は進行中。

## 次の小さい接続

clock/creation/Job close flags/quiescence verifier/Popenはprotocol stub。実worker invocation、実Git Job probe/子keeper、実proof verifier、initial-reader actorは未接続で、通常worker経路は従来のまま。この13件を実Job回収・実exe・全runtime閉包・容量合格へ読み替えない。

次はcompact quiescent proofの実receipt/close/失敗raw照合と、元Job/process/thread/extra handleを保持する子keeperを固定する。診断・marker保存・割込みの失敗でもPython終了で元ownerを失わない経路を先に結ぶ。実Parent.create/on_started bind/stop_fenceとChild wait/probe/Job leaseのinvocation接続を小さく進める。実import後にsource inventory/profileを新revisionで再準備し旧14/14を読み替えない。新nativeは接続/拒否/停止保全ができた後の別exclusive準備とし、現段階では開始しない。
