# S4-B2 親保護と完了印の順序案（未採用）

2026-09-14。親privateでは保持親NT renameが成功し、親frozenでは保持親/同一親内の両形式が5で拒否された。
API形式を替えるだけの追加試行は行わず、次の試験fixture設計を検討する。
既存6工程model、S3 hardlink marker、D2、production入口、科学仕様、正式pinの変更決定ではない。

## 推奨する次の設計作業

独立レビューで、親private中に別actorが取得した追加/DELETE_CHILD等の権限が固定後も残り得る点を指摘された。
そのactorを脅威範囲から除外しない。本案は残存権限を隔離できる条件が未充足で、順序変更だけの実装へ進める状態ではない。

payloadの名前変更を親private中に済ませ、その後の親固定・最終検査が完了するまで、consumerが有効な完了印を読めない案をpure modelで検証する。
完了印を最後にrenameする現行案は親の新規書込み許可を必要とする可能性が残るため、単にroot固定を遅らせるだけでは足りない。
次の候補は、専用fixture内の.completeをCREATE_NEW/共有なしで空のまま予約し、保持したwriterで最後に内容を書いてflush/closeする方式。
この完了印方式は未実装・未採用であり、既存marker契約とは区別した候補である。

| 順序 | 候補の動作 | consumerへ公開できない条件 |
| --- | --- | --- |
| 1 準備 | 親private、stage/file作成。空.completeをCREATE_NEW/共有なしで取得 | 完了印の存在だけで成功としない。予約handle保持中は通常read open不可 |
| 2 子固定 | payload writerのwrite/flush/close、子file/stageのfrozen DACLと原bytes/ID読戻し | 完了印は空のまま。子内容・権限を検査できない場合は停止 |
| 3 名前変更 | 全stage子handleを閉じ、stageを保持したままpayloadへrename。rootはprivate | 完了印は空のまま。rename応答不明は後続の内容書込み禁止 |
| 4 親固定 | rootと予約markerを同一handleでfrozenにし読戻す。自分のmarker writerは先に取得した書込み権限を保持 | このDACL変更だけでは、別actorの既取得権限を取り消せない。自分のmarker以外が変更不能とは主張しない |
| 5 最終検査 | 固定後にexact inventory/元payload ID・bytes・SDを検査し、証跡を保存 | 親private中の追加・入替え・削除があれば失敗。有効markerはまだ書かない |
| 6 完了印 | 予約済みmarkerへ固定bytesをwrite、exact byte count、flush、close確認 | 有効bytes書込み開始後の応答喪失・flush/close失敗は公開状態unknown。再試行・削除・rollbackなし |

root/stage/祖先の保持とDELETE共有なしを維持し、名前変更後に旧stage pathを使って観測しない仕組みが必要。
既存の「元writerを全て閉じてから固定」から、marker writerだけを例外として保持する変更がある。
consumerは存在だけでなく、完了印のexact bytes/長さ/hash、root/payload固定状態と固定inventoryを検証する必要がある。
これも読取り時点の一致確認であり、将来の不変性を証明しない。別actorが固定前から親の追加/DELETE_CHILD等のhandleを
保持している可能性を残したままでは、最終検査後やmarker公開後の名前集合の変更を排除できない。
共有違反・空/部分markerを「準備中または無効」と扱う新しいconsumer契約が必要になる可能性がある。
共有なしは単一プロセスの生存を保証しない。crashでhandleが閉じた場合も、空/不完全な完了印は受入不能でなければならない。
完全なmarker bytesが書かれた後のcrash/失敗では外部から読める可能性があり、失敗したから未公開とは扱わない。
closeは電源断耐久性の証明ではない。新方式でrenameの原子的な名前出現を保証したと主張しない。

## 実装前に潰す論点

- final pathで作ったmarkerの原bytes/size/SD確認とwrite/flushのための取得権限、共有mode、例外的writer寿命を固定する。
- root固定前に別actorが加えた余分な子、名前の差替え、削除が固定後検査で拒否され、markerへ進めないことを確認する。
- 別actorの既取得parent handleと権限を明示的なmodel状態に含め、sealでその状態を消去しない。
  最終検査後・公開後の追加/削除を遷移として試験し、残存権限を排除・隔離する根拠がない限り保護済みcommitを認めない。
  根拠不明も排除済みとして扱わない。実OSでどの操作が保持権限を使えるかを確認する前に、不可能とは仮定しない。
- write前・部分write・全write後・flush・closeそれぞれの故障とcrashに、unknown/未公開を正しく割り当てる。
- consumerのsharing violation/空marker/部分marker/有効markerの分類と、有界な観測方法を定義する。存在チェックだけのconsumerへ適用しない。
- 既存6工程の成功を借用せず、この順序を表す別の小modelでsingle-use/再入/元例外/資源停止を試験する。
- 仕様・独立レビュー・source固定がそろうまで新しいnative枠を開始しない。

別案としてpublisher専用のprincipal/tokenを使い、親の書込み許可をconsumerから区別する方法もある。
現在のEveryone denyにはpublisherも含まれるため、単にallow ACEを足す案ではない。別の権限設計・運用条件が必要になる。
このPCに新しいサービス・account・runtimeを追加する案は、具体化・必要性の判断前には実行しない。

まず残存権限があれば受入を拒否するpure modelとconsumer条件を具体化し、隔離が必要な点と既存の受入契約に触れる点を判断可能な形にする。
別actorの事前取得を防ぐ生成/隔離手順、または権限の残存下でも守れる別方式が固まるまでは、候補のnative実装へ進まない。
現時点ではS4の全保護・marker commit・正式受入は未完了であり、どちらの案も正式契約へ採用していない。

## 2026-09-14 pure modelでの具体化

[残存権限と完了印のmodel](anomaly-v03-publication-order-model-design.md)を39cac0dで実装した。
[202件pass・独立指摘0](results/anomaly-multiseed-v0.3-s4-b2-publication-order-model-2026-09-14.md)、実機試行の追加なし。
隔離unresolvedでは既知peerが0・全照合一致でもwriteを拒否する。後段故障用の隔離仮定は実OSの根拠にならない。
既取得権限を親固定で消さず、最終確認後/公開後の外部変更、部分write・応答喪失、consumerの単発分類を扱った。
全照合一致もsnapshot_matchesに限り、方式採用・保護済みcommit・将来不変性を認めない。
次は実際の生成/隔離条件と一貫したconsumer観測、例外的marker writerの権限/寿命を具体化する。上記native開始条件は維持する。

生成/隔離の次段は[隔離条件と単一呼出し取得候補](anomaly-v03-isolation-basis-design.md)で具体化した。
CreateDirectory2WのSDK宣言/exportは確認済みだが、API本体は未実行。取得間隙の縮小とnamespace隔離を区別し、
既取得parent権限・peerの取得/使用・writer移管・consumer一貫性の未解決条件を維持する。
[設計レビュー指摘0・保存結果](results/anomaly-multiseed-v0.3-s4-b2-isolation-basis-2026-09-14.md)を参照。
