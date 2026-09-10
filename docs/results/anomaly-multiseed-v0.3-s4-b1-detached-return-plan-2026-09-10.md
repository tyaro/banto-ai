# S4-B1 コンソールに接続しない起動条件でのreturn比較

状態: **修正保存・全体fake・独立レビュー/preflight完了 / 限定1回の返答待ち・実機未実施 / no native acceptance**。

## 目的と変える条件

[console失敗候補の実測](anomaly-multiseed-v0.3-s4-b1-console-failure-result-2026-09-10.md)でallocation候補にC0000022が返った。
次は同じ制限tokenと固定childで、起動時のコンソール指定だけを変え、既存return観測のAL/stageを比較する。

DebugDriver(init_return=True, detached_console=True)のみで明示的に選ぶ。
detached_consoleはboolだけを受け付け、init_return以外のmodeとの併用は拒否する。既定はfalse。
診断launchのNO_WINDOW 0x08000000をDETACHED_PROCESS 0x8へ置換し、実際の要求flagsは0x0000040eにする。
従来の0x08000406から、UNICODE_ENVIRONMENT/SUSPENDED/DEBUG_ONLY_THIS_PROCESSを保持する。
NEW_CONSOLEやNO_WINDOWとの併記、handle継承、token/ACL/desktop/environment変更、通常core child launchの変更は行わない。

[Microsoft flags説明](https://learn.microsoft.com/en-us/windows/win32/procthread/process-creation-flags)と
[コンソール生成説明](https://learn.microsoft.com/en-us/windows/console/creation-of-a-console)を根拠にした比較である。
DETACHEDで生成されたconsole processはコンソールに接続していないとされるが、
今回のアクセス拒否回避やPython本体の起動成功は未検証。これをsecurity boundaryやconsole作成の禁止機構とも扱わない。
起動要求flagsをLaunchResultとprivate証跡のlaunch.requested_creation_flagsへ保存する。
APIに渡すargumentsの値とcreation_stateを記録し、過去の証跡を補完しない。

## 観測と終了

使用するcollectorは検証済みkernelbase-26200.9445-return-v3のまま。
[return観測計画](anomaly-multiseed-v0.3-s4-b1-init-return-plan-2026-09-10.md)のLOAD時code2窓2195 bytes照合、
初期threadのRVA0x50baに対するdebug register設定1回、最初の一致例外でのreason1/RIP/DR/TF検査を維持する。
Get最大3回/Set最大1回/RPM最大3回2197 bytes。console_failureの4地点・caller slotは併用しない。
RVA0x3aeea0のWORDとALをprivate保存し、ALやstageの未知値も保持する。

AL=1/stage=700が得られれば、従来AL=0/stage=600との対照として解釈する。
AL=0または別stage/未取得なら、その事実を残して終了する。成功値を必須にして失敗値を捨てない。
観測は実RET前であり、成功側の値が得られてもchild E2E・自然終了・native受入とは別に扱う。

どの値でもinit_return_observed_stopから既存owned stopへ進み、通常Continue/handled化をしない。
Terminate確認後だけpendingを解放し、失敗時は所有未解消を保持する。DR復元・再設定・追加起動・自動再試行なし。
最終reportを先に出力/flushし、証跡保存・終了と有界readbackを確認する。

## 上限・検証

既存30秒/256 events/親＋child512 MiB未満/空きdisk1 GiB、context8 KiB/metadata64 KiB、owned drain32/5秒を維持する。
設定API回数は1、取得量は2197 bytesへ戻る。nativeのhelper常駐、他project操作なし。
同期API前後の期限確認であり、途中の強制中断保証ではない。

関係fake46/46 pass（0.874秒）。新旧launch flagsの正確な受渡し・非継承・所有、非bool拒否、
外側driverでdetached指定とAL1/stage700の取得・意図的終了・private証跡へのflags保存を確認した。
資源停止/設定中断/失敗時の既存挙動も維持する。全体回帰・独立レビュー・保存後preflightは追記する。
比較の実child/実SetThreadContextはまだ実施していない。

## 次の実機判断対象

console_failure v1の限定1回承認は消化済み。今回の比較は新たな起動設定を含む。
準備完了後、**DETACHED指定で新規fixtureを1回だけ起動し、既存return観測を実施すること**を提示する。
過去の上限小幅拡大の意向を、起動条件を変えた追加実行への無制限な承認とは扱わない。


## 全体検証と独立レビュー

debug＋preflight/event全体173/173 pass（1.762秒）、全metadata予約枠の容量確認もpass。
独立差分レビュー新規P0〜P3=0、指定fake46/46 pass（0.824秒）。
既定flags維持・明示mode制約・要求flagsの保存・観測後の意図的終了を確認した。
allocation候補と拒否された内部API/object/ACLの確定、単発比較とchild E2E成功を区別する留保も確認した。
担当の完了通知のみを利用し、進捗ポーリングなし。担当のnative実行/private証跡参照/source変更なし。

repository safety/diff-check pass、mainは基準889cfc3のままclean。
PC空きRAM9.23→8.88 GiB、C108.21 GiB、D75.36 GiB。単発値からリーク有無は未判定。
比較用の実child/実SetThreadContextは未実施。


## 保存後の事前確認と再開条件

実装・試験・結果・計画をeaacd30に保存。read-only preflightは1.943秒、21 sources/239171 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存exe/python314.dll hash一致。detached-return-preflight.jsonへ保存した。
execution_authenticated/launch_authorized/native_accepted/formal_permissionはfalse。この確認でchild起動・SetThreadContextは行っていない。
repository safety/diff-check pass、mainは基準889cfc3のままclean。

準備は完了。DETACHED指定で新規fixture1回、既存return観測Get3/Set1/RPM3回2197 bytesの実施について返答を待つ。
この問いへの「続けてください」は当該比較の1回への了承として扱い、再確認せず実行する。
観測・不一致・失敗のいずれでも自動再試行しない。最終report・終了・証跡保存の確認を先に行う。
