# S4-B2 公開前後の保持とconsumer観測期間

2026-09-14、基準86efa66。実装savepoint **1c03cfece1464f8231b7d223c7f91828a639bd97**。
[保持期間model仕様](../anomaly-v03-retention-window-design.md)を実装・検証し、初回独立P2 1件を修正、再レビューP0〜P3残件0。
**子handleのclose/reopenの間隙と、全fileを同時に保護できるconsumer期間を区別した。**
新規23＋既存283＝306件pass/0.219秒。今回はpure modelとfake backendの契約確認だけで、新規実機試行は0回。
全isolation/protected commit/future immutability/formal permission/execution authenticated flagsはfalse、B2/S4受入は未完了。

## 得られた条件

既存SealedFilesはcontinuation内で元rootと全子を保持し、callbackから戻る前に子をcloseする。
その後の再openまでの間隙を、前回の「保持中ならDELETE共有拒否が効いた」という実機結果で埋めることはできない。
前回4ケースの結果や最大1回枠は変更・再利用していない。

| 経路 | 今回のmodel結果 |
| --- | --- |
| 同IDの新guard取得を確認してから旧payload guardをclose | 共有条件の保持が重なり、consumer期間の欠落なし |
| open intentだけ記録し、確認前に旧guardをclose | 期間の欠落。後から同ID/同bytesでも履歴を修復しない |
| 読み終えたfileを閉じてから残りを読む | 全fileの共通期間なし。全照合一致だけでは結果を返せない |
| 公開中に欠落し、その後すべて再取得してconsumerを開始 | 新consumer期間と古い公開期間は別。前者のmodel一致で後者を修復しない |
| share3で保持 | DELETE拒否の条件はあるがdata WRITEを共有する |
| share5で保持 | data WRITE拒否の条件はあるがDELETEを共有する |
| 全file照合一致・共有条件の共通期間あり、他境界は既定未解決 | observations_match_only。bytes返却不可 |
| 上記に他境界の明示的test仮定を追加 | common_interval_model_only。照合した同じimmutable bytesだけを返せる |

既存payload sealerは0x160081、marker sealerはDELETE付き0x170081、いずれもshare READ=1。
新readerをshare1で重ねると、payloadの共有条件は両立するが、markerでは既存DELETEと新readerの共有条件が衝突する。
marker readerをshare5にすると共有条件は両立するが、旧guardを閉じた後はDELETE共有拒否を維持できない。
これは[CreateFileWの双方向共有条件](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)と既存accessからの予測であり、追加の実機検証結果ではない。
ACL/namespace/取得成功の保証ではなく、WRITE_DACとdata WRITEも区別した。

## 実装と故障確認

初期pinはmarkerを含む2〜8 file、最大24世代slot/128イベント。file64KiB、descriptor8KiB、marker16KiBの上限。
ID/accessの合成確認後だけheldとし、close intent以降はguardとして数えない。同じslotは再利用しない。
公開開始から観測完了までと、consumer開始から完了までの欠落を別々に保存する。
後から再取得しても欠落は消さず、観測完了後のcloseは過去の区間を変えずに現在のguard不足を表示する。
data READ/WRITE/DELETEの共有条件だけを扱い、一般の権限評価・実OS操作の証跡としない。

初回304件はpassだったが、独立レビューでP2を検出した。
余分なslotのopen/close応答が未確定でも、既存guardから全読取ができればcommon_interval_model_onlyとbytes返却が可能だった。
全slotの未確定状態を観測完了前とbytes返却前に拒否するよう修正し、2試験メソッドを追加。
完了後に新たな操作を始めた場合も返却前に判定する。元の観測履歴は保つが、失敗を無視して返却へ戻らない。

最終306件では失敗/error/skip/expected failure/unexpected successが全て0。
重複slot/read/close、pin/実権限/bytes/SD不一致、未完了読取、共有衝突、不明応答、保持欠落、外部変更、元失敗と後発resource stop、上限、snapshotの独立性を確認した。
既存fake SealedFilesのcallback中に全子が生存し、戻る前にすべてcloseすることも照合した。
既存PublicationOrderのisolation_unresolved gateとproducer unknownをconsumerの一致で変更できないことを確認した。
独立レビューはread-only、進捗ポーリングなし。修正後の再レビュー以降にコードを変更していない。repository safety/diff検査pass。

## 保存と資源

54 sourceのraw bytes/Git blob/候補checkout一致を確認した。前回delete-matrixの49 sourceと14 artifactsは全て不変。
corrected-checks.jsonl224673 bytes/hash9c614996c3ab2715be80c817f5165e4af4e54b0902760e8641e5c2a133d08b81。
savepoint-evidence.json12370 bytes/hash8c43033877fd80b3fac04c6155e5c11e7bfb915c64959b052078db5879eb0ee7。
ignored artifacts/retention-window-2026-09-14/へ8 artifacts/論理574370 bytes（manifest自身を除く）。初回/修正後の両テスト記録を保持。

UTC13:26:58の空きRAM14.73GiB/C117.51GiB/D53.16GiB、13:29:45はRAM14.32GiB/C117.51GiB/D52.96GiB。
PC全体の変動原因は未特定。今回の記録量とは分け、長期リーク不在・全期間最大の証明にしない。他processへの操作はない。
開始時の軽量観測UTC13:18:41はRAM15.37GiB/C117.51GiB/D53.16GiB（ツール応答のみ、manifestの開始点とは別）。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和を維持し、正式pinは変更しない。
既存Python3.14.0を使用。新規worker/監視/checkout/常駐process/実機fixtureは追加していない。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変。旧batch/旧source、S3/D2/production、push/merge/CI、新runtime/account/serviceへ操作なし。

## 次に具体化する部品

元rootと全sealed fileのborrow中に有界consumer読取を終え、照合したbytesを返す部品を優先する。
markerの別openによる保護移管を前提にせず、既存の所有範囲内で読み終える候補である。現時点でnative publisherへの接続や方式採用は行わない。
親/祖先namespace・全inventory・descriptor・既存保持者の権限行使/移管までの共通期間は子の共有条件から証明できず、modelでは明示的test仮定に隔離した。
marker write/rename、独立process/token・競合、全publisher、正式OS/VM digest、B2/S4受入は未完了。
別account/サービスや受入契約の変更が必要になれば、具体的な実装と運用負担を判断材料にする。
