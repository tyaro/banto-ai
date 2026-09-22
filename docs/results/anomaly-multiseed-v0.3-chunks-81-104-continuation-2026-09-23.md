# v0.3 完了済み81区間からの24区間継続

2026-09-23 JST。**現在は実行中であり、新規144評価の成功は未確定。** ユーザーの「進めて下さい」に基づき、保存点855e359136d568ddf5b29bef84a7d69e82e9e009と最新closedを照合して、`continue --max-chunks 24`を起動した。対象はchunk81〜104の24区間だけ。成功時は累計105区間/630評価、next105、残り15区間/90評価となる。実装変更なし。

## 開始確認と外部pin

実計算source/consumer/controllerはclean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`。同じ`artifacts/v03-runs/r1`を閉鎖記録から継続する。今回のcontrolは000006。prepared raw SHA-256 **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。

開始closedは **`run/control/000005/closed.json`** / raw SHA-256 **a6b8fd6160b496d9a7dea83cef3ec22814c8b12676df273eb591fb5368384758**。journal243/next81/yielded、累積活動86406.475041秒から継続する。実行中にこの開始pinを使って重複起動しない。前回controller PID39544/collectorは終了済みで再実行しない。

前回manifestは候補`artifacts/chunks-57-80-continuation-2026-09-22/savepoint-evidence.json`、10443 bytes/SHA-256 **c4017dacb4a80da2a27fe90c57f53c0fab95991ce44bb8a91b969909c891f0ca**。記載49ファイルとmanifestの計50件を照合し、前回runの5221 files/10761163678 logical bytesはhash・一覧とも完全一致。追加invocationファイルと関連計算processが起動前にないことも確認した。

preflight UTC2026-09-22T23:49:02.714929+00:00、空きRAM11698061312/C160047202304/D119168217088 bytes。Windows11 Pro25H2/AMD64/26200.9457/local NTFS、CPython3.14.0/MSC1944/source v3.14.0:ebf955dとexe/DLL hashは前回と一致。Windows Updateはengineering実値記録で許容し、旧正式pinは不変。本流D:/develop/banto-aiは889cfc3/clean、実計算sourceはc01d1c9/clean。既存dirty親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。

## 起動・監視・途中保存

候補`artifacts/chunks-81-104-continuation-2026-09-23`に起動記録と外部証拠を保存する。controller PID **29852** / 開始UTC **2026-09-22T23:50:51.3450097Z**（JST2026-09-23 08:50）。非表示background processで起動し、PID・開始日時・wrapperコマンドを照合した。実argv/runtimeはrequest.jsonへ保持する。前回wrapperのcontrol番号・開始pin・区間範囲だけを更新した。

wrapperは60秒ごとにcontroller private/peak、空きRAM/C/D、journal段階を記録し、区間ごとのverified receipt（sequence246〜315）を外部保持する。中間receiptはclosedの代用にしない。既存heartbeat **banto-24** を今回のFOLLOWUP.mdへ更新・再開した。30分ごとに1回だけ確認し、新規6/12/18区間の節目でこの結果文書とcurrent-handoffを中間保存する。追加agent、短い間隔の進捗poll、過去成果物の繰返し数値再計算は行わない。

## 予算と完了条件

前回実測では既存57区間の確認を含む最初の新規区間の開始が8928.3〜8988.3秒、fresh inspection63.336秒。単純換算は既存1区間155.5〜156.6秒、新規1区間884.0〜886.5秒。今回は既存81区間の照合に約3.5時間、新規24区間を含め33878〜34023秒（約9.4〜9.5時間）、追加保存約3GiBを見込む。

48時間候補予算の残り活動時間86393.524959秒（約24.00時間）。仮に残り39区間を24/15に分ける線形試算は累積約41.65〜41.74時間だが、固定費、layout/seed差、inventory増加、再試行・遅延を分離しておらず保証ではない。**今回の上限は24区間のみ**。32GiB候補出力上限、空きRAM4GiB/disk20GiBの開始条件、controller private2GiBの境界検査、producer/auditの既存所有process上限を維持する。全体上限は協調的な境界検査で、process treeの強制上限ではない。

終了後はexit0/yielded/新規24/next105を確認し、collect.pyのIO/hash照合を1回実行する。全所有process終了、各監査、前回5221ファイル不変を確認し、5文書の最終保存（長い引継書§141）とfinalize_evidence.pyを完了してheartbeatを停止する。異常終了でも記録を保全し、成功専用collectorや未閉鎖invocationを再使用せず判断点を報告して停止する。追加invocationは自動起動しない。

campaign加算0/正式許可false、独立監査は保存score以降のみ。完全runtime inventory/独立S6、全120区間/holdout/性能評価、Phase 2/3全体の完了は追加しない。保護ProgramData roots/principal/SAM参照、UAC/ACL/service/task/VM変更、push/merge/CIなし。
