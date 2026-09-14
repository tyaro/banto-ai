# S4-B2 保持consumerの専用worker・限定実機結果

2026-09-14、基準840e351。実装savepoint **9cc926f3c2c6cadff10c041ec0d0521c32016d3e**。
[専用worker仕様](../anomaly-v03-held-launch-design.md)を実装し、独立P0〜P3所見0件、377件pass/0.508秒を確認後、新規max1の限定実機試験を行った。
**新規2fileの準備・同handle読取・照合・証拠保存・全closeが完了し、worker exit0/終了確認、外側監視stopなし。**
実機は0.860秒、UTC14:43:21.2087356〜14:43:22.0892657。最大1回枠は閉鎖し、fixtureを保存して残す。
外部consumer bytes返却はisolation_unresolvedのまま。隔離・将来不変性・B2/S4全受入の完了ではない。

## 専用起動と監視

input-pin.json全体SHA、clean HEAD、追跡src/banto_ai/fixtures等の全py/ps1 inventoryとbytes/hashを照合してからnative取得する。
supervisorのCreateNew claimとworkerの排他attempt mkdirにより同じ枠を再使用しない。
取得前にdriver/contextをmodule参照へ固定し、resource/不明closeでも専用process終了まで保持する。
stdoutは通常reportまたは固定resource noticeを1回だけ書く。report/短いwrite/例外で80/81を1へ下げず、後発MemoryErrorは80へ昇格する。
出力失敗後の2回目のnoticeや再試行はない。通常reportへreaderのcollection/files hash/close metadataを含める変更だけを既存driverへ追加した。

外側監視は起動した同じProcess objectだけを対象とし、500ms/最大96点、45秒、private256MiB/working384MiB、空きdisk2GiB、stdout+stderr384KiB。
worker内は40秒、同メモリ上限、空きRAM/disk各2GiB、1024点。監視例外や超過では当該workerだけを終了し、5秒以内の終了確認を要求する。
時間的な隙間や監視API自体の停止を排除する保証ではない。外側の空きRAMは事前、実行中はworker guardで検査する。

## 実機で確認した内容

別clean detached checkoutはC:\Users\TKent\.codex\worktrees\held-launch-20260914\banto-ai、HEAD9cc926f。
新規attempt-1だけを使用した。source rootは既存WindowsPrivateSinkのCreateDirectoryW/再open方式であり、単一呼出しdirectory取得の保証を組み合わせたものではない。

| 記録 | 結果 |
| --- | --- |
| facts.json | 42 bytes、同handle取得hash be793aa97ba27ec1a79877d13399612d07a66fcd6d45848664964a193591e09b |
| marker-pending.json | 415 bytes、同handle取得hash c67f80da25b921237b5603d6cb330fd741597383fbbf5dcbecf4cddf5aff0c71 |
| consumer | complete、61 guards、全file close確認、consumer内のpath再open/新handle取得なし |
| 元source/sink | 各13 lease closed、query token各1 closed。sealed reader2本もclosedで計28 handle＋2 token |
| prepare保存の報告値 | 2876 bytes/hash3a6eefc745936247fd9e174ceb19b759f8de3d13e7aa2d519f186f10e5cd2778 |
| 収集証拠保存の報告値 | 1063 bytes/hash84983d51e4314e6dd7a4f734cdd440881242e113d1c68ccdbab962d514a59181 |
| worker | PID43324、exit0、終了確認、retained=false、監視stopなし |
| 出力 | stdout27846 bytes、stderr0。正常JSONとsource revision/pin SHAを照合 |

prepare/収集証拠のhashはworkerの保存・読戻し完了報告から取得した。終了後にprivate-evidenceやsourceを再openして独立に照合した値ではない。
準備/path確認、sealerの再open、evidenceのreadbackは周囲の既存部品の動作であり、consumer内の再openなしと区別する。
marker-pending.jsonを読めたことを、完了印の公開・rename・protected commit成功とは扱わない。

内部資源100点、最後0.266秒。private最大21245952/working29495296、報告されたOS working peak36118528 bytes。
外側は1点、0.599秒時点でprivate28524544/working35942400 bytes。内部/外側の時点と観測範囲は異なり、どちらも長期リーク不在の証明ではない。
全記録は今回の資源上限内。worker/監視終了、常駐なし、他project/processへ操作なし。

## 固定・回帰・保存

新規17＋既存360＝377件pass、failure/error/skip/expected failure/unexpected successは全て0。
pin/HEAD/inventory/サイズ/改変、排他attempt、報告故障、stdout異常、一次例外と二次resource、終了までのcontext保持をfakeで確認した。
独立レビューはread-only、進捗ポーリングなし、レビュー後code変更なし。PowerShell構文/repository safety/diff検査pass。
initial-checks.jsonl273518 bytes/hashf12b722db71d77b58a6da440bcde5766adf7ab58b0cefe4329acd7d36c903c68が回帰根拠。

選抜65 sourceはraw/Git blob/候補・native両checkoutを前後照合。入力pin対象106 sourceを含むunion134 sourceはnative raw/Git blob一致を前後確認。
入力pin17176 bytes/hash0aaa69ce665e9af43f2ee6d29808453081fe4e009af7325c00e4a4450f7f8026。
候補側の追加runtime source22件は既存CRLF、Git/native側はLFだった。最初の準備照合で検出し、改行正規化だけで一致することを記録した。これらの候補fileは変更せず、nativeの実bytesを入力pinへ固定した。
この差分を検出した時点でattempt/fixtureは未作成。native試行の追加や再試行ではない。完全runtime inventory/実行認証/TOCTOU隔離を認定するものではない。
前回held-driverの60 source中59は不変。変更1件はdriver snapshotへのreader metadata追加。前回manifest/8 artifactsは全て不変。

ignored artifacts/held-launch-2026-09-14/へ13 artifacts/論理440266 bytes（manifest自身、別checkout複製・実fixtureを除く）。
savepoint-evidence.json40219 bytes/hash1eaba249cdbd404120bb8671f8112876e6f26cd0fddc71bee399016266cd667d。
UTC14:41:05 RAM13.94GiB/C117.29GiB/D51.39GiB、14:45:23 RAM14.03GiB/C117.29GiB/D51.39GiB。
開始時軽量観測UTC14:34:03はRAM13.68GiB/C117.30GiB/D51.39GiB（ツール応答のみ）。PC全体変動の原因は未特定、今回の論理記録量と分ける。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和を維持し、正式pinは変更しない。既存Python3.14.0を使用。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変。旧case/旧source、S3/D2/production、push/merge/CI、新runtime/account/serviceへ操作なし。

## 次に確認する条件

元handleでの局所読取が通ったので、次は親フォルダーの保持中に名前一覧への追加を防げる条件を具体化する。
新規fixtureで親のshare条件とpath指定の新規file作成を分ける。ADD_FILE用handle取得の拒否だけで、pathによる追加操作も拒否されると推定しない。
今回のsource/成功枠は再利用せず、別の有界仕様・fake故障確認・レビューを先に行う。
親/祖先/全inventoryの共通期間、bootstrap競合/内部割当、独立process/tokenのpeer・競合、marker write/renameと全publisher、正式OS/VM digest・B2/S4受入は未完了。
別principal等の運用変更が必要なら、その差分と負担を具体化して判断材料にする。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。
