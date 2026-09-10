# S4-B1 DETACHED条件での最初のDLL UNLOAD観測

状態: **候補修正・全体回帰・独立レビュー・保存後preflight完了 / 実機未実施**。

## 目的と最小変更

[通常childの結果](anomaly-multiseed-v0.3-s4-b1-detached-control-result-2026-09-10.md)は0xC0000142で、失敗DLLは未特定。
次はDebugDriver(unload_entry=True, detached_console=True)を使い、
同じDETACHED指定のdebug launch0x40eで、最初の通常UNLOADイベントのDLL・loader entry・終了経過を取得する。
診断modeの変更は、DebugDriverの既存detached_console optionを、init_returnに加えてunload_entryでも使用可能にすること。
既定false、bool必須、collectorの相互排他、plain/console_failureとの併用拒否を維持する。
core通常launch0x40c、制限token/ACL、非継承、固定Python/child/-B -I/environment/cwdは変更しない。

既存DebugContext + DebugUnloadEntry v2を再利用する。code/RVA/hash/取得サイズや解釈条件の変更なし。
対象は最初の通常UNLOADだけで、別DLLへの選び直し・後続eventでの再取得・drain時の取得なし。
初期threadでなければnot_initial_thread、UNLOAD自体が来なければnot_observedを記録する。
callsite等が違えば既存の検査で停止し、未確認値を補完しない。

## 読取り・継続・停止の範囲

GetThreadContext最大1回（既存1232-byte AMD64 CONTEXT）、stack ReadProcessMemory最大1回2048 bytes。
既存ntdll code3窓947 bytesのhash一致後、loader entry112 bytesを最大1回読む。
合計RPM最大5回3107 bytes、Get最大1回。SetThreadContext、software/hardware停止点設定、
target memory/code/token/ACL/PEB/registry書換え、symbol lookup・pointer walk・追加handle openは行わない。
既存のevent image情報とtoken/security確認、初回Resumeと通常debug-event Continueは使用する。

loader entryのflags/init_failure_bit、image_size、module_load_slot、初期thread/callsite一致を記録する。
UNLOADは正常な解放でも生じ得る。flagsや対象DLLを見ずに失敗箇所と断定しない。
この診断もdebugger有りの別runなので、非debug実行の因果関係を直接証明しない。
正常eventは既存方針でContinueし自然EXITを記録する。未検証breakpointは従来どおり拒否してowned stop。
bootstrap breakpointを通過させたり、診断結果をchild E2E成功に読み替えたりしない。

新規専用system-temp fixture1個。診断fixtureは成功/失敗とも保持し、cleanup/repairしない。
時間30秒/256 events/親＋child512 MiB未満/temp volume空き1 GiB以上を維持する。
owned stopは既存のterminate/pending解放/drain最大32回・5秒、signal/ownership/closeの確認を行う。
同期APIを厳密なwall-clockで強制中断できる保証ではなく、各呼出し前後で予算を検査する。
metadata64 KiB/context8 KiBと既存private証跡上限を維持する。資源停止後の新規読取り・追加hash/保存は抑止する。

## 実行と記録

ignored artifacts/context-offline-2026-09-10/detached-unload-once.pyを準備した。
2427 bytes / SHA-256 b8ce387f512c150804a6e4de9b6c596f2f5bc063eee7f3e004d4f83a0c8112a7。
構文とrun呼出し1か所を確認済み、未実行。wrapperは事前に新規公開要約fileを開き、
driver.run()を1回だけ呼び、最終reportをstdoutへ先行出力/flushし、非資源停止時だけ公開要約を保存する。
private rawは既存の起動前取得済みevidence handleへdriverが保存し、write/flush/close結果を確認する。
必要な照合は終了結果を確保してから既存の有界readerで1回行い、他fixtureを走査しない。
全acceptance gateはno。本流統合・formal/B2/publisherは実行対象外。

## 検証と判断対象

関係fake44/44 pass（1.136秒）。既存fault matrixをNO_WINDOW/DETACHEDの両方で実行し、
code不一致・資源停止・entry検証失敗時の停止/証跡/handle close、Get1/RPM最大5、
Setなし・cleanupなし、起動要求flagsと証跡metadataへの保存を確認した。
全体回帰、独立差分レビュー、source保存後read-only preflightの結果を追記する。

準備後、新規fixtureの限定観測1回を判断対象として提示する。
引継書§6の「追加probeは承認なしに繰り返さない」に従い、通常controlの1回とは区別する。
この具体的な問いへの「続けてください」は本診断1回への了承として扱う。失敗しても自動再試行なし。


## 独立レビューで見つかった出力中の資源停止を修正

初回レビューでP2が1件あった。既存write_summaryが詳細構築中のMemoryErrorを通常のdetails.failedとして捕捉し、
wrapperが次のhash生成・file保存へ進める問題である。今回の通常control結果に資源停止はなく、再実行はしていない。
write_summaryはMemoryErrorをownerへlatchして同じ例外を再送出するよう修正した。
最終driver状態は詳細構築前にflush済みで、以降のreport/file保存へ処理を進めない。wrapperのwithは既存fileをcloseする。
最終行またはstream出力自体のMemoryError等も従来どおり伝播して、その呼出し以降を実行しない。
runの結果と、その後のreportで発生した障害は時点を分け、既に出たdriver結果を後から書き換えない。

images・hash・JSON構築中のOOMを注入し、最終1行の保持、同じ例外の伝播、資源latch、次のreport/hashなしを回帰確認した。
関係fakeはreportを含め49/49 pass（0.929秒）。report sourceもpreflight固定対象に追加し、保存後は22 sourcesを照合する。
全体回帰とレビュー是正確認の結果は以下に追記する。


## 全体回帰とレビュー是正確認

最終pure/fake全体235/235 pass（2.719秒）、repository safety/diff-check pass。
初回レビューの指定fake44/44（0.964秒）pass、P2=1を上記修正で解消。
是正確認の追加差分は新規P0〜P3=0、report fake5/5（0.001秒）pass。
担当は実機・wrapper実行・private証跡参照・source変更をせず、完了通知だけを利用した。進捗ポーリングなし。
修正後の空きRAM7.74 GiB、C107.92/D75.36 GiB。mainは889cfc3でclean、追加実機は未実施。


## 保存後preflightと次の1回

実装・試験・通常control結果・次の計画を021956cへ保存した。
保存後read-only preflightは2.028秒、22 sources/242703 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。detached-unload-preflight.jsonへ保存した。
child起動・SetThreadContextなし、全acceptance gate no。限定診断の準備は完了。

次の判断対象は、新規fixture1個でDETACHED指定の最初の通常UNLOADを1回だけ観測すること。
Get最大1回、RPM最大5回3107 bytes、Setなし、既存30秒/256 events/親＋child512 MiB予算とowned stopを維持する。
この問いへの「続けてください」は当該1回への了承として扱い、clean状態/wrapper hashを確認後、同じ了承を再確認せず実行する。
条件不一致・失敗時の自動再試行なし。自然EXITと強制停止、未観測と検査失敗、証跡保存結果を分けて記録する。
