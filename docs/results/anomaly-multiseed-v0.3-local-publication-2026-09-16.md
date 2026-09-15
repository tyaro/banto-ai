# 通常権限・単一writerの保存API

2026-09-16 JST、ユーザーの「次に進めてください」により、引継書§116の方針で再開。
実装savepoint **75a245ac190b944426371118ebda3fe820391f5c**。
[保存APIの使い方と範囲](../anomaly-v03-local-publication.md)を追加した。

## 実装したこと

既存の排他的作成・非上書きrename・完了印・内容の再読取りを共用し、`LocalPublication` / `publish_local_result` / `verify_local_publication` を追加。
呼出し側が既存の親フォルダーと新しい実行名を指定し、通常権限で計算済みの小さな結果を保存できる。
同じ出力先は1処理だけが使う運用を前提とし、新marker `anomaly-v03-local-complete` でtemp fixtureの形式と区別する。

既存実装で、writeがファイル作成前に失敗した場合やclose後でも同じオブジェクトを再使用できた穴を修正。read/write/verify/publishの失敗後は停止し、close後も再使用できない。
完了印作成の試行前に `commit_attempted` を記録し、応答喪失後に失敗記録を追記して有効な完了構成を壊さないようにした。
独立レビューで、2回目のcallbackが内部read失敗を捕捉すると外側publishが成功へ進むP2を指摘され、commit前の停止状態再確認と回帰を追加。最終P0〜P3所見0件、進捗poll0。
通常保存処理の保証であり、意図的な別process改ざん、専用account分離、全ディレクトリ構成の停電耐久性を認定しない。

## 確認した結果

最終sourceで **27 tests / 全pass / failure・error・skip 0 / 3.715秒**。
選抜は `tests.test_anomaly_v03_local_publication` 12件と、既存 `tests.test_anomaly_v03_publication.PublicationTests` 15件。
排他・非上書き、partial write/fsync失敗、内容検査/rename/marker失敗、停止・close後の拒否、callbackの捕捉、commit応答喪失を確認した。
通常Python子processを保存途中で `os._exit(23)` により終了させる試験では、保存済みの途中ファイルを保持し、完了印なし・consumer拒否・同じ保存先の再使用拒否を確認。
repository safety / diff-check pass。正式native試験、アカウント/ACL試験は追加していない。

修正途中で広く選んだ4 module回帰は、重い評価データ生成を含んだため、対象PID23824の実command/start時刻を照合してUTC16:34:06に停止。**このrunは中断でありpassには数えない。** CPU320.8125秒、停止時private104050688/working115589120 bytes。他processは停止していない。
中断時のTemporaryDirectory cleanup完了は未確認。一時出力の場所を個別記録していなかったため、古いfixtureと混同する削除や探索は行わなかった。今後も全module回帰を機械的に再実行せず、変更に必要な試験を選ぶ。

## 通常権限での保存実演

公開成果物は `artifacts/local-publication-2026-09-16/results/demo-01`。
新規2ファイル `result.json` / `summary.md`、合計28 bytesの手書き内容を保存した。実データ評価や計算性能の結果ではない。
writer PID6436、UTC16:35:46.462368〜16:35:46.597217、exit0。保存直後の新規readbackは `local_verified=true / payloads=2`。
同じ `demo-01` への2回目の保存はFileExistsErrorで拒否し、元の結果を再検査して不変を確認。
writer終了後、別の通常Python process PID18180がUTC16:37:05にreceiptを使って再読取りし、同じ2 payloadを検証してexit0。P-U権限分離試験ではなく、writer→readerを順番に実行した結果である。

marker SHA256 **64e214f17417960928cd9d517d66414c97a22e8413162074ae2ef7d29b154df1**。
実演記録943 bytes/hash **d4690ba3b30dd30a370abc01c6346bfe94485376f4636bab80a35616b3479178**。
別process reader記録274 bytes/hash **0ccc5803ca842153412fe474f00a640a20a7434b02b8a6b0998061686588d3cf**。

## 保存・資源・再開点

input24101 bytes/hash **a6f0cf63d0cf944097747b20bad74516b980aa9516207cda7ef774debeaceeb4**。
前回選抜113 source不変＋今回選抜4 paths（既存ファイル改修2、新規ファイル2）、計117のworkspace/git blob一致。前回公開artifact16件不変。
最終manifest27900 bytes/hash **7504a0c6d241e22b35a0891acfcfd0e6dae3715acc8d84d822955deb3b512d81**。自身を除く8 artifacts/論理26958 bytes。これは当該公開directoryの量で、中断テストの一時出力を含まない。
終了後UTC16:37:06、空きRAM6307483648/C149470707712/D198224175104 bytes（D約184.6GiB）。PC全体の変動原因や長期リーク不在は未確認。
OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。本流889cfc3/clean。
専用principal/rootへアクセスせず、reset/enable/logon、追加特権、UAC、ACL変更、service/task/VM/profile追加、push/merge/CIなし。旧9 root閉鎖とj/診断の消費済みguardを維持。

**通常保存APIは利用可能。次は、結果を作る側からこのAPIへ接続する小さな開発用経路を進める。** 同じ保存先の並列更新は避け、既存API/テストを再利用し、専用principalや厳密な分離試験を自動再開しない。
今回formal campaign entry、科学的評価条件、受入gateは未変更。正式契約への接続は、通常開発の保存成功と区別して扱う。
local_publication_performed=true。他のnative_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。
