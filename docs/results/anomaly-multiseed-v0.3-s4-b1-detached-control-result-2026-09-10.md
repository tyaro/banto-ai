# S4-B1 DETACHED通常child検証結果

状態: **通常control失敗 / child_exit=0xC0000142 / teardown pass / no native acceptance**。

## 実行と確認結果

ユーザーの「お願いします」を[通常検証計画](anomaly-multiseed-v0.3-s4-b1-detached-control-plan-2026-09-10.md)の1回への了承として、
cleanな6d1466a（core修正ab147d5）で準備済みwrapperを1回実行した。追加起動・再試行なし。
wrapperは3526 bytes / SHA-256 cae6a4ee47236fbfd8a9d024204105e5b4484e91b3154033ce2af18821f04c48で照合。
run_control_harness()を直接1回呼んだもので、NativeWindowsControlsというtest classを実行した結果ではない。

status=failed、reason=child_failed、winerror=0、child_exit_code=3221225794（0xC0000142）。
control_status=failed、cleanup_status=not_started、teardown_status=pass、resource_stop=false。
core記録elapsed_seconds=0.3133907、wrapper全体2.407秒（直前preflight等を含む）。
通常launchは保存済みsourceの要求flags0x40c。要求値の照合でありOS内部状態の独立計測ではない。

置換traceはincomplete、confirmed_records=0、last_stage=null、source/original_destination_state=not_observed。
complete_prefix/unconfirmed_tailは0 bytes、private_replaceは空bytes、private_controlはnull。
child reportの合格確認には到達していない。traceが空であることを任意の起動処理が未実行だった証明には使わない。
success cleanupは開始しなかった。失敗fixtureは自動削除・repairせず、retained_existence=unverified、known_bytes=5912。
保存後にfixtureを再open・走査して存在を確認したものではない。所有handleの終了処理はcoreのteardown passを記録した。

## 前回との差と解釈

[前回のreturn比較](anomaly-multiseed-v0.3-s4-b1-detached-return-result-2026-09-10.md)はdebug launch0x40eで、
KernelBaseのRET直前AL1/stage700を観測し、そこで意図的にterminateしていた。
今回の非debug通常launch0x40cでは自然終了コード0xC0000142となり、E2E成功は得られなかった。
前回の値はその停止点の成功側の観測として有効だが、実RET/Python起動・全DLL初期化成功へ拡張しない。

debug flag・停止点観測の有無・独立runという差がある。今回どのDLL/内部APIが失敗したかは未特定。
同じKernelBaseが後続で失敗した、別DLLへ進んだ、debuggerの有無が原因、のいずれも現時点では確定できない。
coreのDETACHED変更は隔離候補として保持し、修正完了や本流統合可能とは扱わない。

## 証跡・環境・資源

公開要約detached-control-native-summary.jsonlは2016 bytes、
SHA-256 b41de63f393c01b02d4f492cb46d7bea2957cb8319147b663f43c80d7d4a40c4。
その2行を1回の有界readで照合し、detached-control-result-check.jsonに記録した。
private rawの一般file exportなし。private_controlが無いため、完全なcontrol証拠を保存したとは扱わない。
空private_replaceのSHA-256はe3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855。

同run preflight verified、21 sources/239293 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
Windows Update後のUBR緩和は維持し、実測buildを記録。last bootは2026-09-09T10:43:08.5000000+09:00。
core記録の親＋child peak private23097344 bytes（22.03 MiB）、peak working32804864 bytes（31.29 MiB）。
system commit34474733568/limit70493097984 bytes。
空きRAM7.66→7.80 GiB、C107.93 GiB、D75.36 GiB。単発の前後値からリーク有無は判定しない。
他project操作・既存fixture削除・追加DLL/PDB読取り/downloadなし。

native_accepted/s4_accepted/formal_permission/execution_authenticatedはfalse。本流889cfc3はcleanのまま。
次は[DETACHEDでの最初のUNLOAD観測](anomaly-multiseed-v0.3-s4-b1-detached-unload-plan-2026-09-10.md)を準備する。
今回了承された通常control1回は消化済み。
