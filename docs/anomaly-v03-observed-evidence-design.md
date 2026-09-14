# S4-B2 取得済みハンドルの管理移管と実観測証跡

基準19e474b、2026-09-14。tests/fixturesのengineering部品。
前回のprivate保存枠とは別に、prepareの実観測→保存→選択解放だけを接続する。

## 所有と観測

AcquiredOwnerはcallerが先に保持するreceiverである。全TrackedOpenのready/error/handle、
親子graph/重複/最大32 slotsを検査し、既存HandleOwnerの全追跡領域を構築してから
各cellを関連付け、単一のactive切替で管理を移す。それ以前の割当て・関連付け失敗では
source cellはcaller-ownedのまま。返却が失われても保持receiverのactiveで終了責務を判断できる。
同期trusted codeで、Python内部の無制限OOMや非同期thread/悪意あるprivate-field改変の保証ではない。

raw CloseHandleを呼ぶ主体は各TrackedOpenのまま、既存HandleOwnerのbackendがそのcellを通る。
移管元の公開close/acquire再呼出し、receiverの再adoptは停止を記録し、握り潰しても継続できない。
close不明の数字を再利用しても二度目のraw closeをしない。
finishは既存ownerの選択解放状態を利用して子から親を閉じ、残る外側ancestorはcallerが最後に解放する。
動的なslot追加、writerを閉じて異なる権限で再取得する機構ではない。

inspect_nativeは取得済み_Boundのidentity、exact file bytes/hash、SD観測を読み、
前後のidentityと各操作前後のlease/owner/journal停止状態を検査する。
権限記録はWin.securityの正規化JSONであり、生の自己相対SDや独立token実効権限の認証ではない。
再利用するWin.securityはprotected/private用途であり、一般祖先の継承DACL収集器ではない。
native root/fileのSDは現在user/SYSTEM/Administratorsのprivate policyと照合する。
writer取得済み権限の取消し、hostile same-user、owner/adminのDACL変更への防御は扱わない。

capture_recordは全live owner slotsを借用し、全file slotとpayload各名/marker1個のexact対応を要求する。
native bytesとmarkerの独立hashを照合し、観測pinを採用時pinに照合してbuild_evidenceへ渡す。
EvidenceBarrierがその記録を保存してから選択fileを閉じる。1 fileでも不明/失敗なら記録返却を止める。
本接続は全slotsがまだownedのprepare向け。解放後の再観測・権限移行・rename後の名前照合は残る。
全出力not_completed/formal_permission=false/execution_authenticated=falseを維持する。

## 新規の限定native試行仕様

| 項目 | 今回の固定範囲 |
| --- | --- |
| 実行前 | pure/fault検証・独立レビュー・clean exact HEAD、監視script hashを保存 |
| runtime | 既存Windows CPython3.14.0 Win64。新規導入なし。実OS build/bootは記録 |
| root | candidate artifacts/observed-evidence-2026-09-14/attempt-1またはattempt-2のみ |
| source | 新規private source-fixtureにfacts.jsonとmarker-pending.json、各4096 bytes以下 |
| 証跡 | 別新規private-evidenceへprepare.json1個、64KiB以下、probe結果128KiB以下 |
| native操作 | 新規root/file作成、private SD照合、source write/flush/readback、3 slots管理移管、実観測/証跡保存、選択解放、終端解放、終了後bytes照合 |
| source所有 | source root＋2 filesの3 slotsを移管。既存祖先はsource callerが保持し最後に解放。証跡sinkは別所有 |
| 対象外 | DACL seal、writer再取得、rename/.complete、B1 controls、token変更、旧root/他project操作、正式publisher |
| 予算 | worker private256MiB/working384MiB、空きRAM/drive各2GiB以上、境界40秒/外側45秒、約1秒process監視 |
| 回数 | 最大2。原因特定と修正レビュー後だけ別rootで2回目を許す。成功で終了し、未使用枠は繰り越さない |
| 異常時 | 以降は所有解放のみ。資源停止は固定通知/exit80で通常JSON保存を抑止。不明handle再close/自動清掃なし |

新規workerはhidden起動、保持Processだけを監視・停止・終了確認する。
前回監視scriptの起動前確保/try内起動/finally終了確認を引き継ぎ、console要約のnull表示を修正する。
Start-Process内部の起動後返却喪失、hardリアルタイム上限、電源断耐久性は保証しない。
旧private sink probeの資源通知をfinallyの外へ移し、Python3.14構文警告を解消する。
旧成功試行の原記録・実行済みscriptは変更せず、表示確認のために再実行しない。

成功条件はprepare保存/選択解放、source/証跡のexact inventory/raw一致、全追跡close、
両照会token close、worker exit0。journalは公開前で意図的に停止しteardown成功、
commit_observation=not_startedを確認する。モデル6工程を架空に成功させない。
全native受入、正式OS整合、VM digest、runtime closure/consumer凍結、S4受入は別の残件。

## 実行結果

9172afbのclean HEADで1回目が成功。source2 files/460 bytesから実観測を含むprepare証跡2880 bytesを保存し、
選択解放・追跡25 handles/token2個のclose・worker exit0を確認した。外側0.355秒、stderr0 bytes。
今回枠は成功で終了し、2回目を繰り越さない。[結果・保存記録](results/anomaly-multiseed-v0.3-s4-b2-observed-evidence-2026-09-14.md)を参照。

後続の[reader再取得](anomaly-v03-reader-reacquisition-design.md)で、writer解放後の新読取り世代を追加した。
親borrow内で元ID/bytes/SD・実GrantedAccessを確認してreaderを閉じる。動的slot追加やseal/renameへのlive移管は残る。

続く[file権限固定](anomaly-v03-file-sealing-design.md)でinspect_nativeのfrozen SD検証を追加し、
2 filesの固定後観測を別世代へ接続した。後続phaseの証跡barrier更新・directory/root seal・renameは残る。
