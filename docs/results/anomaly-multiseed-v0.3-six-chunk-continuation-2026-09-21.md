# v0.3 完了済み3区間からの6区間継続

2026-09-21 JST開始。対象はclean `C:/Users/TKent/.codex/worktrees/v03p/banto-ai`、実装 **c01d1c978f78bab51391392d56cdcb7aab5afaab**、出力`artifacts/v03-runs/r1`。

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
