# v0.3 完了済み33区間からの24区間継続

2026-09-22 JST。**現在は実行中であり、追加144評価の成功は未確定。** ユーザーの次工程への指示を受け、保存点28100c4と最新closedを照合し、`continue --max-chunks 24`を起動した。対象はchunk33〜56の24区間だけ。成功時は累計57区間/342評価、次chunk57、残り63区間/378評価になる。実装変更なし。

## 開始確認と外部pin

実計算source/consumer/controllerはclean **c01d1c978f78bab51391392d56cdcb7aab5afaab**、`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`。同じ`artifacts/v03-runs/r1`を閉鎖記録から継続する。今回のcontrolは000004。

prepared raw SHA-256 **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。開始closedは **`run/control/000003/closed.json`** / raw SHA-256 **af04684d25c99f69e64a2ac5aacffd92be930d6325ceddd5d9a0ee254f5fa7a0**。journal99/next33/yielded、累積活動28855.997764秒から継続する。実行中の再起動や追加invocationは行わない。

前回manifestは候補`artifacts/twenty-four-chunk-continuation-2026-09-22/savepoint-evidence.json`、10289 bytes/SHA-256 **ddbb32983dadb84fbdca50d990f346c02cdaa5bedc8949d016504562e6d48ec8**。記載48ファイルとmanifestの計49件を照合し、前回runの2137ファイル/4384532669 logical bytesはhash・一覧とも完全一致。新しいinvocationの追加ファイルがないこと、起動前に関連計算processがないことも確認した。

preflight UTC2026-09-22T01:22:52.725775+00:00。空きRAM13703512064/C167815163904/D119512027136 bytes。Windows11 Pro25H2/AMD64/26200.9457/local NTFS、CPython3.14.0/MSC1944/source v3.14.0:ebf955dとexe/DLL hashは前回と一致。Windows Updateはengineeringの実値記録で許容し、旧正式pinは不変。

本流D:/develop/banto-aiは889cfc3/clean、実計算sourceはc01d1c9/clean。既存dirty親policy文書8461 bytes/SHA-256 443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。保護ProgramData roots/principal/SAM参照、UAC/ACL/service/task/VM変更、push/merge/CIなし。

## 起動・監視・途中保存

候補`artifacts/chunks-33-56-continuation-2026-09-22`に起動記録と外部証拠を保存する。controller PID **6872** / 開始UTC **2026-09-22T01:24:22.5430796Z**（JST10:24）。Windowsの非表示background processとして起動し、実argv/runtimeは`request.json`に保持する。PIDだけで判断せず、開始日時とwrapperコマンドも照合する。

前回のwrapperからcontrol番号・開始closed・対象区間だけを適合させ、60秒診断とverified receipt保持を引き継ぐ。新規verifiedのsequence102〜171を区間ごとに外部保存する。controller private、空きRAM/C/D、journal段階を`progress.jsonl`と`latest.json`へ記録する。中間receiptはclosedの代用にしない。

既存heartbeat **banto-24** を今回のFOLLOWUP.mdへ更新して再開した。30分ごとに状態と資源を1回確認し、新規6/12/18区間の節目でこの文書とcurrent-handoffだけを保存する。追加agent、短い間隔の進捗poll、過去成果物の繰返しhash/数値再計算は行わない。PCとアプリを稼働させたまま継続する。

## 予算の判断と完了条件

前回24区間の診断ログでは、既存9区間の確認を含む最初の新規区間の開始が1810.4〜1870.4秒の間だった。fresh inspection60.285秒を差し引いた単純換算は既存1区間194.5〜201.1秒、新規1区間790.9〜793.4秒。今回の既存33区間を含む見積りは25458〜25738秒（約7.1時間）、追加保存約3GiBとなる。最初の約1.8時間は既存区間の再照合が中心になる。

48時間候補の残り活動時間143944.002236秒（約39.98時間）。残り87区間を仮に24/24/24/15で区切る線形試算は全累積42.1〜42.7時間だが、固定起動費、seed/layout差、inventory増加、再試行・遅延は分離しておらず保証ではない。今回許可された実行範囲は区間33〜56のみ。32GiB候補出力上限、空きRAM4GiB/disk20GiBの開始条件と所有producer/audit上限を維持する。全体上限は協調的な区間境界検査で、process treeへの強制上限ではない。

終了後はexit0/yielded/新規24/next57を確認し、準備済み`collect.py`によるIO/hash照合を1回実行する。全所有process終了、各監査、前回2137ファイル不変を確認し、5文書の最終保存と`finalize_evidence.py`を完了してheartbeatを停止する。異常終了でも記録を保全し、成功専用collectorや未閉鎖invocationを再使用せず判断点を報告して停止する。campaign加算0/正式許可false、独立監査は保存score以降のみ。完全runtime inventory/独立S6、全120区間/holdout/性能評価、Phase 2/3全体の完了は追加しない。
