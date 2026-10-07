# bounded Git出力保存部品と限定native入口（2026-10-07）

code `3ee5dc2b1f3d35cb9bfc6d1cfccec94035f9a0a4` はpush済み。変更はowned_git_job、reader_git_worker、新testの3file。source module追加0でreader対象の名前は30source／予定64Jobのまま。新しいraw pin/profileは未準備で、古いpinを新codeへ読み替えない。

## 保存部品

`BoundedGitSpool` はcallerの元streamを検証前に保持し、原shared checkpointとsync callbackを使うbyte sink。`next_read_size()` は最大4096Bか保存枠の残余までを返す。保存枠の最後の1byteを検知用sentinelに使い、そこまで保存するとoutput_limitを返し後続readを拒否する。原read blockはwrite/flush/sync/checkpointより前に保持する。

partial/不明write、flush/sync/共有stopのIO・割込みでは `BoundedSpoolFailure` に元sink/stream/原例外/pending rawを残し、後続writeを拒否する。EOF処理はflush/sync、元stream close、closed=Trueの確認を行い、不明close時は元streamを保持してblind retryをしない。EOFやstream closeをJob回収・lease・ackの証明にはしない。

これは投入bytesを制限する部品である。実callerは新exclusive・空の保存fileと原native ownerへ接続する必要があり、既存fileの総容量やnative pipeの出力を本部品だけで保証しない。callerが指定する保存枠は既存operation/stdout/stderr上限以下、検知1byteもその枠内に含む。新clock、別rootへの保存、元rawの削除は行わない。

`ReaderGitParent.create_native` は実pipe/owner/capacity接続が未完成のため、root/channel/worker作成前にResourceStopで拒否する。capture_boundedやproof metadataだけでは通さない。現在のcreate/default callerとfile-directed executorは従来の動作を保持する。

## 焦点と保存照合

最終sourceの新12焦点を一回、0.0090987秒で実行。fail0/error0/skip0。実小fileのwrite/fsync/EOF、検知byte停止、read残余4096B、過大block、partial write、write割込み、flush/sync/clock例外、不明close、invalid cap、native入口のroot/Job作成前拒否を確認した。実pipe/Job/Win ABI/native認証の試験ではない。

33source/science pinは前後不変。変更3fileのscan_repository(paths=...)はpass、code-saveでHEAD=origin/clean・33working/Git pin・module unique12 discoveryを照合。実試験の再実行0、旧suite/native反復0、追加agent0。全repository safetyの先行30秒timeoutは未確認として維持。

rawは `artifacts/preformal-bounded-git-spool-20261007-prep/`。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| focused.json | 10224 | `0a5aeea86e9fa2d2fbcd3ef15793a2a9b4933674591e07bf85f730dea8324356` |
| focused.log | 2155 | `64a9c61cbac4c4849e4e98c58c0c5bda1d4afbdc529c5d138bc7cfd25e7f3344` |
| code-save-checkpoint.json | 397 | `900ebf97d51e74dabeae58bc4dfd7eda236df51f7de52038db526d19b5340b79` |

helper48456/creation134358515016584692/token245683362c71c150cff2e5fab9ffb38c85659e526ac1e0e2bb738f2856f0fbc5はexit0/CIM残存なし。critical ownerなし・native0。

## 次の接続

元private Jobのspawn/stdio cleanupと原pipe read handles、sink stream/pending blockをIO前に同じownerへ保持する。既存keeperのinherited最大3の範囲へ別read handleを無理に読み替えず、追加ownerの停止/EOF/close不明とPython終端を先に扱う。

exact callの元root残余bytes/entries、保存枠と検知byteを実read/write経路へ渡し、output_limitで元Jobを停止する。停止・read/close/診断失敗でもownerを捨てず、原raw/receipt/post-close witnessを照合後だけarchive/lease/proofへ進む。単なるpoll後超過をhard boundにせず、未接続のcreate_nativeは拒否を維持する。

この接続の焦点確認後に限定reader caller/launcher、最終clean HEADのfresh inventory/profile/policy/requestと専用未使用rootを準備する。archive512KiB、outer1MiB/32entry/depth2/reserve128KiB、全体321MiB/672entry、元wall/memory/output、cleanup30秒/poll0.25秒を維持する。正式gate s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読、正式5残件は保持。
