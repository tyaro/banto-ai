# v0.3 完了済み3区間からの6区間継続

2026-09-21 JST開始。対象はclean `C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、実装 **c01d1c978f78bab51391392d56cdcb7aab5afaab**、出力`artifacts/v03-runs/r1`。

**2026-09-22 JST終了: 新規6区間・36評価すべて成功、累計9区間・54評価。** 約90分42秒で正常閉鎖し、次の未完了区間は9。以下の開始・中間保存点は実行中に保存した履歴である。

## 開始保存点

ユーザーの「進めていきましょう」に基づき、最新closedから **`continue --max-chunks 6`** を開始した。既存chunk0〜2/18評価を保持し、chunk3〜8の最大36評価を順次追加する。目安は前回実測から約90分/追加約0.8GiBで、再開時の既存証拠再照合やseed/layout差の時間は変動する。成功時の次区間は9/累計54評価となるが、この保存点では未完了。

starting closedは`run/control/000001/closed.json` / raw SHA-256 **bfa729b447de0ce57d32439acb65ce025e718e82e7c40ebd55dda5d316d9c2da**。prepared hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。新しいinvocationは000002。実行中は同じrunを再起動せず、途中receiptをclosed pinとして使わない。

候補worktreeの`artifacts/six-chunk-continuation-2026-09-21/preflight.json`に開始前照合を記録した。前回manifest（4953 bytes/SHA-256 **adf08b7f2f32907c45c94bf8e9656a91292137efe02f83a00f6cb0d68ff1d5aa**）と記載11ファイル、既存run205ファイルを照合して不変。実sourceはc01d1c9/clean、本流889cfc3/clean、候補6557188と既存dirty8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全した。

開始前UTC2026-09-21T14:24:18.428702+00:00、空きRAM13286776832/C173749780480/D119512629248 bytes。Windows11 Pro25H2/AMD64/26200.9457/local NTFS、CPython3.14.0/MSC1944/source v3.14.0:ebf955dとexe/DLL hashは前回一致。Windows Updateはengineeringで実値記録する方針を維持する。

同folderの`run.py`は前回wrapperから明示区間数・外部closed pinだけを更新し、`request.json`に実argv/runtimeを保存する。60秒間隔でcontroller private/空きRAM/disk/journal状態を記録し、所有producer/auditの既存時間・メモリ上限も維持する。診断表示だけで成功判定せず、終了後のclosed記録と成果物を照合する。全体48時間/32GiBは境界での協調停止による候補予算である。

実装変更・追加agent・広い回帰試験の再実行なし。単一writerを維持し、保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIは行わない。全120区間の自動起動や正式gate変更、Phase 2/3完了へ読み替えない。

## 前半の中間保存点（2026-09-22 JST）

開始保存点1873c37の後、約10分の既存3区間の再開照合を経て新規計算へ進んだ。経過約51分でchunk3/4/5がverified_completeとなり、今回18評価追加・累計6区間/36評価の記録が揃った。chunk6はrunning、同じinvocation000002を継続中である。

verified sequence12/15/18のreceiptを外部`verified-receipt-000012.json` / `verified-receipt-000015.json` / `verified-receipt-000018.json`へ保持した。これは中間確定記録で、再開用closed pinではない。管理処理の最大privateは225722368 bytes（約215.3MiB）、chunk6開始後の標本は105472000 bytes（約100.6MiB）、空きRAM13051863040/C173314277376/D119512604672 bytes。後半3区間の成功や最終closedはまだ確定していない。

## 最終結果

中間保存点は**ed28579**。その後chunk6〜8も完走し、実CLIはexit0/`yielded`/`stop_reason=null`、`chunks_verified_in_invocation=6`、`next_unverified_chunk=9`となった。各区間6 success、failed/inconclusive/not_started各0。登録dev seed2486912926863618161のlayout3〜8についてcore/quality-stress×C0/C1/C2を生成した。journalは既存9記録に18記録を追記して計27。全所有producer/audit/inspection processは正常終了確認済み、停止理由・観測エラーなし。

| chunk / layout | producer秒 | producer peak private bytes | audit秒 | audit peak private bytes | payload bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3 / 3 | 564.035 | 347295744 | 86.417 | 192446464 | 132557761 |
| 4 / 4 | 560.398 | 346537984 | 90.335 | 191356928 | 132580562 |
| 5 / 5 | 545.863 | 345866240 | 88.784 | 190623744 | 132588984 |
| 6 / 6 | 539.601 | 349519872 | 89.349 | 194879488 | 132523889 |
| 7 / 7 | 550.892 | 348921856 | 89.818 | 194240512 | 132568248 |
| 8 / 8 | 546.310 | 346492928 | 92.085 | 191983616 | 132587721 |

各payloadは41 files、auditは6区間すべて`ledger_checks_passed`。独立監査範囲は保存score以降のledgerで、profile/score導出・bootstrapの独立検算ではない。各descriptor hashは外部`evidence.json`と最新closed内のdescriptor mapに保持する。sequence21/24の中間receiptも外部保持した。

最新外部closed pinは **`C:/Users/TKent/.codex/worktrees/v03p/banto-ai/artifacts/v03-runs/r1/run/control/000002/closed.json`** / raw SHA-256 **`37b94e035b4468b18ff6381e0a17ed7ca6aaedb99cccb14cfaebcb10d8597501`**。prepared pinは不変。次回は同じclean c01d1c9とこの最新pinでcontinueする。初期closed、000001、途中receiptは再開に使わない。

## 最終照合と資源

今回の実時間5442.063274秒（90分42秒）、runの累積活動時間8005.085221秒（約2時間13分25秒）。再開時のfresh inspectionは55.240秒/peak39096320 bytes。60秒診断では既存3区間の再開照合を含む起動段階が542.4〜602.4秒の間に終了した。これは標本間の範囲であり、厳密な工程別時刻ではない。

run全体は **595 files/1196786729 logical bytes（約1.115GiB）**、今回の追加390 files/797161044 bytes（約760.2MiB）。hardlinkの別名もそれぞれ数える。CLIの`output_bytes_before_closed_state=1196309451`は予算対象のrun subrootの集計で、全root集計とは範囲が異なる。終了後のcollectorで新規6区間のclosed/request/inspection、journal/descriptor、audit、marker/payload inventoryを照合し、全595ファイルをpinした。既存205ファイルは完全一致。collectorは128.340秒/peak187580416 bytes、数値計算の再実行なし。

producer最大349519872 bytes（333.3MiB）、audit最大194879488 bytes（185.9MiB）、controller peak227127296 bytes（216.6MiB）/終了時81104896 bytes（77.3MiB）。60秒間隔90標本の空きRAM最小12757803008 bytes（約11.88GiB）。区間処理中のcontroller privateは増減し、終了時には低下した。観測中の資源不足や診断エラーはなく、診断threadも終了済み。長期リーク不在を証明するものではなく、private値は直接所有するprocessの値である。

終了UTC2026-09-21T15:55:10.529690+00:00（JST2026-09-22 00:55）、空きRAM13211693056/C173294256128/D119512580096 bytes（C約161.4GiB/D約111.3GiB）。Windows26200.9457/CPython3.14.0/exe・DLL hashは開始・終了・各workerで一致。Windows Updateのengineering実値記録を維持し、旧正式pinは不変。

証拠は候補`artifacts/six-chunk-continuation-2026-09-21`、最終commitと保全記録は`savepoint-evidence.json`。前回three-chunk-runのmanifestと記載11ファイル（計12）、既存dirty8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621、本流889cfc3/cleanを保全する。実装変更・追加agent・広い回帰試験なし、repository safety/diff-check pass。

## 次回の実行単位と残件

残りは **111区間/666評価**。再開するたびに既存verified区間を再照合するため、短い呼出しを繰り返すほど所要時間が増える。今回の1回の再開実測から、inspectionを除く起動時間を既存3区間に配分し、新規区間時間を約807〜817秒とする単純試算を`continuation-estimate.json`に保存した。

| 次回以降の区間上限 | 残りの呼出し回数 | 再照合される既存区間の延べ数 | run開始からの累積活動時間の概算 |
| --- | ---: | ---: | ---: |
| 6 | 19 | 1197 | 約81〜88時間 |
| 12 | 10 | 630 | 約56〜59時間 |
| 24 | 5 | 285 | 約40〜42時間 |

**次の候補は24区間/144評価**（同じ単純試算で次回約6時間/追加約3GiB）。実行を終了させずに途中のreceiptと文書を保存する方式を続け、再開確認の繰返しを減らす。今回の記録では次の実行は起動していない。全残区間の自動起動や予算の正式freezeではない。

この試算は起動時の他の固定費を分離しておらず、seed/layout差、inventory増加、再試行、runtime変化・資源競合を含まない。48時間/32GiBの候補予算に必ず収まる保証はなく、次の実測で見直す。全体上限は境界での協調停止である。

campaign加算0/正式許可false、完全runtime inventory/独立S6は未完了。全dev/smoke/holdout、性能評価、Phase 2/3全体の完了は追加しない。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。
