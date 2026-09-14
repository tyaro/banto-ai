# S4-B2 ファイル保持とconsumerの共通観測期間

2026-09-14、基準86efa66。[削除条件の実機結果](results/anomaly-multiseed-v0.3-s4-b2-delete-matrix-2026-09-14.md)を、
公開前後の寿命条件へ接続するpure model。実行可能なnative publisherや隔離認証ではない。
tests/fixtures/anomaly_v03_retention_window.pyとその試験を追加し、既存native入口・所有処理・公開gateは変更しない。
新規実機枠、fixture生成、account/service/runtime追加、旧caseへの操作はない。

## 既存実装との接点

SealedFiles.seal_and_useは、元rootのborrow中だけ子handleを保持してcontinuationを呼び、戻る前にすべての子をcloseする。
payloadはaccess0x160081、marker-pendingは0x170081で、ともにshare READ=1。markerだけがDELETEを保持する。
これは権限固定後にも消えない。今回のmodelはこの実装の定数を参照し、既存fake backendでもcallback中/終了後の生存範囲を確認する。

CreateFileの共有判定は、新規accessと既存shareだけでなく、新規shareと既存accessも整合する必要がある。
共有設定はhandleが閉じるまで有効である。[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)。
以下はこの仕様と既存accessからの予測で、追加の実機結果ではない。

| 引継ぎ案 | 共有条件だけを見た予測 | 寿命上の帰結 |
| --- | --- | --- |
| payload sealerにreader/share1を重ねる | 対象のread/write/delete条件は両立 | 新readerの取得確認後に旧handleをcloseすれば、その条件の保持を重ねられる |
| DELETEを持つmarker sealerにreader/share1を重ねる | 新readerが既存DELETE accessを共有せず衝突 | 同じ手順をmarkerへ一般化できない |
| marker readerをshare5にする | 既存DELETE accessと両立 | 旧guardのclose後、新reader単独ではDELETEを拒否しない |
| 既存marker handleをcontinuation内で借りて読み終える | 別openを必要としないmodel経路 | callbackの外へlive handleを持ち出さず、照合済みbytesの返却を検討できる |

共有条件の両立はACL、path/ID、親、mapping、取得成功の保証ではない。WRITE_DACをdata WRITEと同一視しない。
明示的移管・DuplicateHandle・権限縮小のadapterは作らない。単に複製を呼べば現行の所有/受入条件が閉じるとは判断しない。

## 有界の記録契約

初期pinはmarkerを含む2〜8 file、名前とvolume/file IDは一意。file bytes最大64KiB、descriptor最大8KiB、marker最大16KiB。
markerの文法解釈はせず、事前に固定したtoy bytesとのexact比較に限定する。最大24世代slot・128イベントで、履歴を無制限に積まない。
既存file roleのaccessだけを扱い、一般のWindows ACL evaluatorではない。各openの共有maskは0〜7。

open intent→ID/実権限と両方向共有条件の合成確認→held、close intent→closedを記録する。
元slotは再利用不可。intentや不明応答を新しいguardと数えず、close intent以降は保護に依存しない。
余分なslotも含め、未確認open/closeが1件でも残れば観測完了もbytes返却も拒否する。観測完了後に新たな操作を始めた場合も返却前に再確認する。
状態queryやIO callbackはない。各イベント自体はtrusted synthetic inputであり、OS応答や資源解放を認証しない。

各fileのDELETE共有拒否とdata WRITE共有拒否を別々に追跡する。share3は削除を拒否してもdata WRITEを共有し、share5はその逆である。
一方が欠けても「両方を保護」とは扱わない。複数heldのうち最後のguardを失ったときに欠落を記録する。
公開区間は明示startから観測完了まで、consumer区間はbegin_observationから完了まで。途中の欠落はstickyで、同ID/同bytesの再取得で消さない。
古い公開区間の欠落があっても、後から新しい共通観測期間を作ること自体は区別する。その成功で公開区間の履歴は修復しない。

全fileの元held slotから、それぞれのpinのID/bytes/descriptorを1回ずつ照合する。読み終えたfileも観測完了までguardが必要。
途中でclose/reopenした後に全て一致しても共通期間の証明にはしない。明示的な外部変更は停止後/完了後にも記録し、再認定やABA resetを行わない。
最初の失敗は保持し、後発resource stopを昇格する。停止後も既知heldのclose記録は可能だが、open/read/再開は不可。
イベント枠枯渇はresource stopで、その後の台帳拡張も拒否する。これはnative cleanupを省略する実装ではなくpure traceの上限である。

## 観測結果と未解決条件

| 状態 | 出力 |
| --- | --- |
| 読取不足・pin不一致・不明操作・停止 | 完了不可、元失敗/未解消状態を保持 |
| 全照合一致だが共有条件の共通期間に欠落 | observations_match_only |
| 全照合一致・共有条件の共通期間あり、他境界は既定unresolved | observations_match_only |
| 全照合一致・共有条件の共通期間あり、他境界に明示的test仮定あり | common_interval_model_only |

assume_other_boundaries_stable_for_testは作成時だけの反実仮想。親/祖先のnamespace、inventory、descriptor変更、
保持者の権限行使、handle流出・移管、非目標のprivileged writer等が期間中の一貫性を壊さないと仮定する。
子の共有条件からこれらを導かず、既知peer0や全pin一致を代わりの証拠にしない。
共通期間があるmodel結果だけがchecked_payloadを返せる。返すのは照合時に保存した同じimmutable bytesで、完了後のpath再読取はない。
区間終了後のcloseは過去の観測履歴を消さず、現在のguard不足は別表示する。外部変更を新たに観測した場合は返却を止める。

[既存公開順序model](anomaly-v03-publication-order-model-design.md)のisolation_unresolved gateは維持する。
consumerのmodel一致でproducerのunknownを解消したり、marker書込み・protected commitを許可したりしない。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 次の実装判断

優先して具体化する候補は、元rootと全sealed fileのborrow中に有界consumer読取を完了し、確認したbytesだけを返す経路。
これは同process内の観測部品の候補で、全publisher完成や外部consumerへの運用方式採用ではない。
marker書込みとrename、親/祖先/全inventoryの共通観測期間、失敗後の所有終了、正式pin/独立process/token・競合の要件は引き続き未解決。
別account/サービスや既存契約の変更が必要になる場合は、実装差分と運用負担を具体化して判断材料にする。
