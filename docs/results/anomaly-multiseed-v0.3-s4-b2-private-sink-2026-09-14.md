# S4-B2 取得追跡・Windows private証跡保存の検証結果

日付2026-09-14。基準af973237a12223f20a8cd4fe76986354634c7100。
実装・native実行savepoint **847de63d63e3ec0cdc9b2063401c19be63533241**。

**新規18＋既存72＝90 testsがpassし、新規private領域への3ファイル保存をWindows実機で確認した。**
独立レビューのP2計5件を是正し、最終再確認の新規P0〜P3は0。
[設計と試行範囲](../anomaly-v03-private-sink-design.md)を参照。
tests/fixturesのengineering部品であり、native publisherやS4受入の完了ではない。

## 実装と検証

TrackedOpenはOSから取得したraw handleを観測・後続割当てより先に記録する。
取得後の失敗では一度だけcloseし、応答喪失時の再closeや、不明な値の推測をしない。
取得前・raw記録前の異常で所有を把握できない場合はunavailableとしてworker終了を必要とする。
既存HandleOwnerへの動的移管や、無制限OOM下での漏れなしを保証する機構ではない。

WindowsPrivateSinkは新規root/fileへprivate protected DACLを付け、既存祖先を保持する。
新規fileの排他的作成、identity/SD検証、全量write、FlushFileBuffers、同handle読戻し、
SD再検証、closeまでの各段階を追跡する。既存file/rootを上書きせず、成功・失敗物を自動削除しない。
各記録512KiB・3記録合計1.5MiB。今回の実機試行は合成JSON3個・合計16KiB以下にさらに限定した。
低水準B1部品を利用するが、B1ハーネス・token生成/変更・独立token controlsは実行しない。

初回86件pass、3件の回帰追加後89件pass、資源停止の回帰追加後は最終90件pass。
全回failure/error/skip/expected failure/unexpected successは0。
最終の正本はcorrected-checks.jsonl。final-checks.jsonlという既存名は89件時点の中間記録として保持する。
取得直後・観測・write/flush/readback/close失敗、短いwrite、改変readback、二重操作、
停止拒否の握り潰し、元例外と後発資源停止、失敗したtoken取得の出力値を含む。
新規18件は模擬・故障注入であり、native故障試行の件数ではない。

独立レビューで以下を是正した。担当はread-onlyで、試験/native/編集なし、進捗ポーリングなし。

- 低水準_Failure.errorの資源WinError分類漏れ。
- OpenProcessToken失敗時の非ゼロ出力を所有済みと扱う経路。
- close内の再入停止を握り潰すと保存成功を返せる経路。
- 資源停止後に通常snapshot/JSON報告を保存する経路。固定最小通知とexit80へ限定した。
- 外側監視のworker起動後、try/finallyに入る前の割当て失敗でworkerが残る経路。

最後の監視修正は起動前の状態確保、try内での起動・Process保持、finallyでの終了確認とした。
停止は保持ProcessへのKill。Start-Process内部の起動後返却喪失までの保証はない。
監視PowerShellの構文確認、repository safety、staged diff-checkはpass。
最終pure検証の11 sourcesとprobe・tests初期化・低水準coreを含む14 filesを確定Git blobとraw bytes照合した。

## 実機で確認した範囲

cleanな実装HEADと監視scriptのSHA-256をlaunch-plan.jsonへ固定してから実行した。
2026-09-14 UTC07:37:55、このPCのCPython3.14.0 MSCv1944 Win64、Windows26200.9445。
新規artifacts/private-sink-2026-09-14/attempt-1/private-evidenceだけに保存した。

| 確認項目 | 結果 |
| --- | --- |
| 保存物 | prepare.json 156 bytes、seal_payload.json 161 bytes、verify_final.json 161 bytes、計478 bytes |
| 保存順序 | private SD検証→全量write→flush→同handle読戻し→SD再検証→closeを3回完了 |
| 終了後 | exact 3-file inventoryとraw bytes/hash一致を確認し、3 filesを保持 |
| 所有終了 | 祖先/root/fileの追跡14 handlesと照会用tokenのclose確認、worker exit0 |
| 時間 | 外側0.400秒、workerの最終資源観測0.040秒 |
| 資源観測 | private最大17.84MiB、観測時点のOS peak working25.64MiB / peak commit17.98MiB。資源停止なし |

write失敗・flush失敗・close応答喪失は今回模擬で検証した範囲で、実機では正常保存だけを試した。
同じuser/SYSTEM/Administratorsのprivate policy照合であり、別token実効権限やowner/adminの意図的変更への防御ではない。
rename、.complete生成、既存publisher、campaignは実行していない。
最大2回の今回枠は1回目成功で終了。未使用枠の繰越なし。終了済みB1枠も再開しない。

1秒未満で終了したため外側1秒監視のsamplesは0。worker内の5境界とOS high-water値を保存した。
最終観測以後の報告生成を含むprocess全期間の最大値や、長期メモリリーク不在を証明するものではない。
stderrにはPython3.14のfinally内returnに対するSyntaxWarningが2件あり、原文を保持した。
監視consoleのSelect-Object要約はnull値になったが、保存したsupervision JSONには実値があり、
exit0/worker_exited/source一致をそのJSONから別途assertした。console表示を成功根拠にしていない。
この2点を記録し、表示確認のために成功済みnative試行を繰り返していない。

## 保存記録と資源

新規ignored root artifacts/private-sink-2026-09-14/に原記録を保存した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| corrected-checks.jsonl | 64466 | e2b4457c040ab38acdbd2314e977071880a395dfe5a80860631b6825f15bdd93 |
| attempt-1/probe-result.json | 7230 | e31c5a3994c9c2f464413c4df0782180fae31d625f82f103b48cdbca6c7dfb20 |
| attempt-1.supervision.json | 517 | d041690ec1d8aaec6ff20895db1671d72245da9a76340d4993972393af6c367b |
| resources-final.json | 395 | 069f1f80d4abcda70eb667f2cc5342c5a57e3c33133e23f319feef0f37b452d7 |
| savepoint-evidence.json | 7624 | f5b19ea0da77f228472fccaf7ac98fb0b8d9f9c9639ddbaaefb6cd59d01e5acf |

savepoint-evidence.jsonは14 source照合、3回のpure検証の区別、レビュー是正、native記録、
監視script、launch plan、各private fileのhash、ユーザーの同時負荷制約解除を結び付ける。
manifest自身を除く16記録は合計210654 bytes。記録用scriptも含む論理bytesでありdisk占有量ではない。

作業開始UTC07:13:01 RAM5.37GiB/C106.74GiB/D71.08GiBは当時の取得結果を転記。
実機前保存07:34:32 RAM9.13GiB/C108.01GiB/D87.12GiB、
最終保存07:38:45 RAM8.15GiB/C107.45GiB/D87.12GiB。
boot2026-09-09T10:43:08.5000000+09:00、build26200.9445を記録。
資源は点観測であり、この作業やリークへの増減の帰属はしない。
workerと短い検証・記録processは終了。常駐処理なし。別project/旧failure roots/共有環境への操作なし。

## 残る接続

次はTrackedOpenの取得済みpinを既存ownerへ移し、実nativeのpin/descriptor観測から
EvidenceBarrierの記録を構築してこのsinkへ接続する。writer解放後の権限を変えた再取得も未実装。
保持親への相対rename、marker/payload保護、競合・失敗証跡を含むnative全受入は残る。
syntax警告と監視console要約は次にprobeを変更する際の整備対象として記録した。

formal_permission=false、execution_authenticated=false、acceptance_status=not_completedを維持する。
正式OS pin26200.9168、VM image digest、runtime closure/consumer凍結、S4受入は未完了。
src/科学config/schema/registry/正式pinは変更なし。旧Linux CIへ件数を足さない。
本流889cfc3はcleanのまま。push/merge/CI起動、新runtime導入なし。
