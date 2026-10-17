# S4-B2 保持consumerの専用workerと限定実機仕様

2026-09-14、基準840e351。[保持driver](anomaly-v03-held-driver-design.md)を専用workerと外側監視へ接続する。
新規held-launch-2026-09-14 batchだけ最大1回。成功・失敗・応答不明のいずれも枠を閉じ、旧case/旧source/既存枠を再利用しない。
追加はheld_launch.py、held_launch_probe.py、held_launch_supervisor.ps1、fake試験。既存driverはsnapshotへreaderの状態metadataを含める変更のみ。

## 起動前固定

実装を独立レビュー・保存後、別clean detached checkoutへ固定する。既存Python3.14.0 x64を-I/-Bで使用し、runtime/account/serviceを追加しない。
外部で生成するinput-pin.jsonはimplementation_revisionとsourcesだけを含み、その全体SHA256を起動引数へ固定する。
sourcesはgit ls-filesで列挙したsrc/banto_ai、tests/fixtures、tests/__init__.py配下の追跡py/ps1全件。raw bytesとGit blobの一致は生成側で確認する。
workerはclean HEAD、pin全体hash/schema、同じ全inventory、各sourceのbytes/hashを照合してからcontextを生成する。
最大512 source、pin256KiB、各source2MiB。これは選択コードの固定であり、完全runtime inventory、TOCTOU隔離、OS/VM digestや独立実行認証の代替ではない。

supervisorは永久に残すattempt-1.claimをCreateNewで作り、このbatchの監視枠を排他的に確保する。
既存stdout/stderr/監視記録があれば停止し、入力pin hashと空きRAM/disk各2GiBを確認する。衝突物を読み直したり消したりしない。
workerはattempt-1を排他mkdirしてから開始し、衝突時はdriverを実行しない。source/evidenceの既存bootstrap条件は前回仕様を継承する。

## workerと報告

native取得前にdriver/contextをmodule参照へ保存し、mainから戻った後も専用process終了まで保持する。
driverの終了コード80(resource)/81(保持して終了要求)/1(失敗)/0(局所完了)を報告障害で上書きしない。
resource以外はmetadata reportへsource revision、pin SHA、source count、attempt1を付け、320KiB以下のASCII JSONをstdoutへ1回だけ渡す。
resourceの場合は固定短文noticeを使い、通常reportを要求しない。reportのMemoryErrorなら出力前にnoticeへ切り替える。
stdoutの短いwrite/例外は失敗として記録し、2回目の出力・fallback・再試行をしない。後発MemoryErrorは80へ昇格し、一次例外と保持状態は維持する。
報告生成が通常例外で失敗した場合、既存81/1を維持してstdoutなしで終了する。出力失敗時のJSONが完全だったとは主張しない。
driver reportには実readerのcollection/files hash/close state等を含めるが、生payloadは返さない。
sourceの成功後/失敗後の列挙・再open・hash/copy/delete、marker rename、公開操作は行わない。

## 監視の限界と停止

worker内は既存40秒、private256MiB/working384MiB、空きRAM/disk各2GiB、最大1024資源点。
外側は起動した同じProcess objectだけを対象とし、500ms待機ごとに最大96点。45秒、同メモリ上限、空きdisk2GiB、stdout+stderr384KiBを監視する。
上限・監視例外ならそのworkerだけKillし、最大5秒で終了確認を求める。他project/processへ操作しない。
終了確認できなければ成功にせずworker_exit_not_confirmedを記録する。監視記録はCreateNewで一度保存する。
OS build/UBR・boot、前提空き量、観測列、worker PID/終了/終了code、stop reasonを保存し、process objectをDisposeする。
外側の空きRAMは事前確認、実行中はworker guardで確認する。同期APIの停止、500msの隙間、監視API自体の停止を完全に防ぐ保証ではない。
外側の最大working値は観測点の最大であり、OSの全期間peakや長期リーク不在を表さない。

## 実機判定と次の境界

新規facts.json/marker-pending.jsonの準備、prepare保存とwriter release、同handle consumer、収集証拠保存、全close、worker exit0と監視stopなしを局所完了条件にする。
native前後で固定code raw/Git blob/両checkoutを照合する。終了後は既知のstdout/stderr/監視記録だけを読む。
保存証拠のbytes/hashはworkerの報告値を記録し、今回sourceやprivate-evidenceを終了後に再openして検証したとは扱わない。
新規fixtureは残す。失敗や不明応答から同じ場所でやり直さず、次の試行には原因修正と別batch仕様が必要。
親/祖先/全inventoryの共通期間、bootstrap競合/内部割当の制約、独立process/tokenによるpeer・競合、marker write/renameと全publisher、正式OS/VM digest・B2/S4受入は未完了。
専用worker化は独立peer/tokenの干渉試験を意味しない。生bytes返却はisolation_unresolvedのまま。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completedを維持する。
