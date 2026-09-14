# S4-B2 実観測からprepare証跡への接続結果

2026-09-14、基準19e474b17409f3051ab2944f5f22829530824a95。
実装・実行savepoint **9172afb13d1d2b2afc9034c6d352639d47d7c3ec**。

**新規18＋既存90＝108 testsがpass。実Windows上の識別情報・private権限情報・実bytesから
prepare証跡を保存し、その後にsource fileを選択解放する接続が成功した。**
[設計・限定試行仕様](../anomaly-v03-observed-evidence-design.md)を参照。
native publisher、権限移行、S4受入は未完了のまま。

## 実装と検証

callerが先に保持するAcquiredOwnerへ取得済み3 slotsを一括移管する。
全領域確保・graph照合・cell関連付けの後、単一active切替で管理を移す。
その前の失敗はcaller所有、切替後の応答喪失でもreceiverを保持して終了できる。
raw close主体は元のTrackedOpenで統一し、移管元のclose/acquireや二度目adoptを拒否・停止する。
これは固定batchの管理移管であり、途中のslot追加やwriter権限を変えた再取得ではない。

各観測の前後でlease/owner/journalを確認し、実bytes、volume/file ID、private SDと取得時pinを照合する。
全file slotとpayload名/markerのexact対応を要求し、build_evidence→EvidenceBarrier→WindowsPrivateSinkへ接続した。
祖先は元callerが保持し、移管した新規root/2 filesの後に解放する。既存祖先のDACLは変更しない。
SD記録は既存Win.securityの正規化JSON。一般継承DACLの収集や独立token実効権限の認証は行わない。

新規14件の部品確認後、独立レビューP2（停止を検知した後もsecurity/check/後続slotのIOが走る経路）を是正。
各観測境界とownerだけの資源停止を確認し、停止後IOがないことを回帰検証した。
再adopt拒否を握り潰した場合の停止も補強した。
記録済み選抜は初回107件pass/0.102秒、最終108件pass/0.084秒。両回failure/error/skip0。
テスト整備中の配置ミスによるNameError1件は、この記録済み選抜より前に是正した。

最終独立再確認は新規P0〜P3=0。probe/監視/仕様も読み取り確認し、担当の試験/native/編集なし。
進捗ポーリングなし。repository safety・staged diff-check・監視PowerShell構文確認はpass。
最終実行時の15 sourcesにtests初期化/coreを加えた17 filesを、確定Git blobとraw bytes照合した。
旧private sink probeのfinally内returnを外へ移してSyntaxWarningを解消し、両probeの警告なしcompileも確認した。
旧成功試行の原記録と実行済み監視scriptは変更せず、前回manifest内の全artifact hashを再照合した。

## 限定実機結果

cleanな実装HEADと監視script hashをlaunch-plan.jsonに固定した。
新規artifacts/observed-evidence-2026-09-14/attempt-1だけを使用した。

| 確認 | 実結果 |
| --- | --- |
| source | private source-fixtureにfacts.json 45 bytes＋marker-pending.json 415 bytes、計460 bytes |
| 観測・保存 | source root/file3 slotsの実識別・private SD・bytesを含むprepare.json 2880 bytes |
| 保存と解放 | barrierのreleasedをassertし、source filesは保存後に解放。終端で残るroot/祖先/sinkを解放 |
| 終了 | source13＋sink12＝25 tracked handles、照会token2個のclose確認、worker exit0 |
| 終了後検査 | source exact2 filesと証跡exact1 fileを照合、全raw bytesとhashが一致 |
| 実行 | Windows26200.9445 / CPython3.14.0 MSCv1944 Win64、外側0.355秒 |
| 資源 | worker内4境界、最終0.039秒、観測private最大18.43MiB/peak working26.26MiB、資源停止なし |
| 記録品質 | stderr0 bytes、監視console要約に実値が出力された |

journalはprepare pendingから終端で意図的に停止し、prepare=unknown/model_status=stopped/
failure_reason=operation_error、teardown=succeeded、commit_observation=not_startedとなる。
これは公開手順全体の成功報告ではない。実行していない後続5工程をsucceededにしない。
保存/選択解放の局所条件はprobeのassertを通過している。

今回の別枠は最大2回中1回目成功で終了し、未使用枠の繰越なし。前回private保存枠とB1終了枠を再開しない。
DACL seal、writer再取得、relative rename/.complete、独立token controls、既存publisherは実行していない。
実故障・競合のnative受入は残る。今回の失敗経路は模擬・故障注入による検証である。
1秒未満のため外側1秒監視samplesは0。観測後の記録生成を含む全期間の最大メモリや長期リーク不在は主張しない。
Start-Process内部の起動後返却喪失やhard時間上限は保証しない。

## 記録・資源と次の境界

新規ignored root artifacts/observed-evidence-2026-09-14/に記録した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| final-checks.jsonl | 78019 | 4befd0bdc4898dafd641896805db9c45a4e969abcd83f03802096a4999306c02 |
| attempt-1/probe-result.json | 12093 | d79e395361bab9ceb12c140374a1ed6c6ac2f43875d5f7aa5bac8c3f0c42ceb6 |
| attempt-1/private-evidence/prepare.json | 2880 | dff3fe3bdaaaa2b6d8dbd62f4d22b560d17d8d1ffbd97a957a303ba1ada5da36 |
| attempt-1.supervision.json | 520 | 3bd0ae623ade6c40cd54664449e0821cc0e425ab492cb65f28461dd37ab7adcc |
| resources-final.json | 395 | 214659ed9ba17bc3a5396f7c26f9d43c3b3169de21c00878399f9566e8d397b2 |
| savepoint-evidence.json | 7495 | 2b86f64832772d21e6640ec1dd0c4cd97c6c1cbb13fc46d5a7aacf4515e67e95 |

manifest自身を除く16記録は計205392 bytes。記録用scriptも含む論理bytesでありdisk占有量ではない。
source/実行HEAD/監視script/各bytesをmanifestで結び付け、前回原記録の不変も確認した。

開始UTC07:55:38 RAM8.42GiB/C107.75GiB/D87.12GiBは当時の取得結果から転記。
実機前保存08:07:10 RAM8.66GiB/C107.75GiB/D87.12GiB、
最終保存08:09:16 RAM7.86GiB/C108.28GiB/D87.12GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。
点観測の増減を本作業やリークに帰属させない。worker・検証processは終了し常駐処理なし。
別projectの連続稼働終了による追加負荷制約の解除と、通常の資源確認を継続した。

次はwriter解放後に権限を変えた再取得、取得済みidentity/bytesとの対応、slotの寿命設計を進める。
その後にDACL seal・保持親への相対rename・競合/非上書き/失敗証跡をnativeで確認する必要がある。
formal_permission=false、execution_authenticated=false、acceptance_status=not_completedは維持。
正式OS整合、VM digest、runtime closure/consumer凍結、native全受入、S4受入は未完了。
src/科学config/schema/registry/正式OS pin、本流889cfc3は変更なし。旧Linux CIへ件数加算なし。
push/merge/CI起動、新runtime導入、共有環境/別project/旧failure rootsへの操作なし。
