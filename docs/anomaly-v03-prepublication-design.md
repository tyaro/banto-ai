# S4-B2 公開前の証跡保存と選択ハンドル解放

日付2026-09-14。基準5c76c58。注入backendを使うtests/fixturesの接続部品。
[終端owner設計](anomaly-v03-handle-lifecycle-design.md)を拡張する。
実native取得・writer・DACL・flush・publication entrypointは追加しない。

## 同期借用と事前解放

HandleOwner.borrowed(indices, operation)は所有中のpinだけを同期callbackへ渡す。
callback中のfinish、release、別borrowは拒否し、握り潰されてもownerを停止させる。
borrowは通常値を返し、callback例外を同一の例外として伝播する。取得pinの外部持出しを防ぐsandboxではない。

release_before_publish(step, indices)はprepare/seal_payload/verify_finalのpending中にそれぞれ1回のみ。
rename_payload/commit_markerなどでは許可しない。解放対象は重複なしの非empty tupleで、子から親の逆順。
親だけを閉じて所有中やunknownの子を残す選択を事前に拒否する。
途中closeが失敗した場合、選択済みの残りhandleのcloseは試すが、公開処理は停止する。

closed/unknownのslotは借用も再解放も拒否する。終端finishはまだownedのslotだけを閉じる。
未知closeを再試行することで、再利用された番号の別handleへ触れる経路を設けない。
事前解放成功ではjournalの工程をsucceedにせず、teardownも完了させない。
呼出側が工程の残る確認を終えてからsucceedし、最後に終端finishを行う。

事前解放エラー後でも呼出側が明示primaryをfinishへ渡した場合はその例外を優先し、
既に検出したresource stopは保持する。明示primaryがなければ最初の内部エラーを再送出する。
単一threadのtrusted内部契約。借用排他はこのowner APIを通る同期呼出に限り、
直接保持pinを使う外部操作や他thread/native process全体を同期するものではない。

## 解放前の証跡barrier

anomaly_v03_prepublication.build_evidenceは、工程名、科学source revision、marker bytes、
全toy payload bytes/hash、全owner slotのvolume/file ID/種別/content hashとraw descriptorを固定する。
物理path・handle番号・例外本文は含めない。payloadの相対名は既存modelの検証を通す。

- payloadは既存modelの最大8 files/各64KiB/合計256KiB、marker16KiB。
- descriptorは各slot最大2048 bytes、slot最大32。raw descriptorの意味やDACLをこの部品で検証しない。
- base64を含めcanonical JSONの各記録は最大512KiB。上限を超えたら保存前に拒否する。
- prepare/seal_payload/verify_finalの3記録でattemptの保存要求は最大1.5MiB。
- Python process全体のピークメモリ上限ではない。構築・再構成・sink用の複数bufferを持ちうる。

EvidenceBarrierはmarkerをjournalの独立した期待hashに照合し、観測pinはowner全slotへ照合する。
全記録を再構成してraw bytesをexact比較するため、再hashしたflag改変・余分なfield・source/marker差替え、
fileの重複・byte変更・owner pin差替え・欠落を拒否する。
descriptorの自己申告を認証せず、native_observations_authenticated=falseを維持する。

保持するroot/stage/marker等のindexをprotectedとして指定し、対象に含む解放を拒否する。
どのindexが実際のrename handleかを型から推測しない。呼出側が検証済みの役割を指定する契約。
barrierは必要なpinを同期borrowしたままpersist_evidence(step, raw, sha256)を呼び、
Noneによる保存成功応答を得てからrelease_before_publishへ進む。
この成功応答自体は実保存・flush・private DACL・独立読戻しを証明しない。

保存前にphaseとbyte予算を予約する。保存例外・不正応答・応答喪失はunknownで停止し、再保存しない。
保存確認後にcloseが失敗した場合はsavedを残し、既存証跡を削除・置換せず全体を停止する。
snapshotのreleasedは保存応答と選択close群の成功を表し、公開成功・終端teardown完了ではない。
retry/cleanup/formal_permission/execution_authenticatedはfalse、acceptance_statusはnot_completed。

## 保存backendの範囲

試験のsinkはメモリ内のexclusive名前表を使う。別の1試験だけは通常temp領域の小さなfileをxbで作成し、
raw SHA-256の読戻しと既存file拒否、handle解放後もbytesが残ることを確認する。
これは通常のローカル保存の部品試験で、Windows private DACL/flush/電源断耐久性を示さない。
試験用tempfileは正常終了時に清掃する。実失敗fixtureの自動清掃を導入したものではない。

本番用sinkには、新規private evidence rootの所有、exclusive名前/handle取得、途中write・flush・close・
読戻し失敗の追跡、総予算と独立した実保存の確認が必要。今回の部品はそれらを実装しない。
marker名が消える前にraw bytesと観測情報を保存する順序を固定したが、
実native観測の新鮮さ、descriptorと各fileの対応・意味は実backendの責務として残る。

## 接続範囲と実機への残件

既存6工程journalを増やさず、各工程内の事前解放と証跡保存を接続した。
ownerの固定slot集合は構築時の全取得を前提とし、writer解放後に別権限で開く途中取得・所有移管は未実装。
新旧handleが同じ物を重複所有する案にはしない。取得順/再取得時のidentityとbyte照合をnative側で設計する。
事前解放APIを直接呼ぶtrusted callerに保存barrierを強制する仕組みではない。
production入口を作る際はbarrier経由へ閉じ、試験用APIを正式受入の証明としない。

別projectの連続稼働試験はユーザーから終了通知を受領した。
同時負荷を避けるための追加抑制は解除し、通常の空きRAM/disk確認・工程別保存を継続する。
既存B1の終了済み試行枠や正式受入条件は、この通知によって更新・再開しない。
後続の[取得追跡・private sink](anomaly-v03-private-sink-design.md)で新規root/fileの取得・保存部品を追加し、
[限定実機保存](results/anomaly-multiseed-v0.3-s4-b2-private-sink-2026-09-14.md)は3個478 bytesで成功した。
続く[実観測証跡](anomaly-v03-observed-evidence-design.md)で取得済み3 slotsの一括管理移管と
native pin/descriptor/bytes→本barrier→private sinkのprepare保存・選択解放を限定実機で確認した。
writer解放後の権限を変えた再取得、動的slot追加、後続phaseの実観測・renameは残る。
