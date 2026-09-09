# S4-B1 管理情報観測v1の実機結果

状態: **承認済み1回終了 / code3窓一致 / 観測側のサイズ前提で停止 / flags未保存・未確定 / no native acceptance**。

ユーザーは追加1059 bytesを含む限定実機診断1回の問いに「続けてください」と回答した。
HEAD fb08c34（実装316abf5）のcleanな隔離worktreeで、DebugDriver(unload_entry=True).runを1回だけ実行した。
新規専用fixtureを使用し、診断の再試行・既存fixtureの再利用/削除/修復はしていない。

## 実行結果と保存

初期reportまで2.214秒。driver/observer status=failed、primary_reason=entry_image_size、secondaryなし。
context/2048-byte stackを各1回取得し、code947 bytesとentry112 bytesを含む追加1059 bytesも要求長どおり読めた。
ntdll code3窓のSHAはすべて一致し、対応LOAD slot3のKernelBase.dllとentry内baseの一致検査までは通過した。
その後のDWORD[entry+0x40]に対する **0 < size <= 128 MiB** 検査で停止した。

v1はこの検査の後でしかentry raw/size/flagsを証跡へ載せない実装だった。
今回entry status=entry_uncertain、code_windows_confirmed=3、confirmed_bytes=1059、last_read_bytes=112は保存されたが、
読んだサイズの値・112 bytesのraw・初期化失敗bitの実値は保存されていない。0だったのか上限超過だったのかを断定しない。
実行process終了後のscratchを読み直したり、今回の未保存値を後続の結果で埋めたりはしない。

| 領域/slot | event | 内容 |
| --- | --- | --- |
| normal 0 | CREATE_PROCESS | python.exe |
| normal 1 | LOAD_DLL | ntdll.dll |
| normal 2 | LOAD_DLL | kernel32.dll |
| normal 3 | LOAD_DLL | KernelBase.dll |
| normal 4 | UNLOAD_DLL | module3。ここで取得し、サイズ検査で停止 |
| drain 0 | EXIT_PROCESS | code=1。停止処理後の終了通知 |

normal受信5件、observerのContinue確認4件。通常経路のEXIT_PROCESSは未観測。
owned stopはTerminateProcessを要求し、pending UNLOADを解放、drain1回でEXITのContinueとprocess signalを確認した。
したがってcode1を元の起動障害の自然終了値とは扱わない。
stop/driver teardown=pass、failure_count=0、debug_ownership_resolved=true、所有process/thread handleは双方close済み。

driver.run直後にwrite_summaryの最終行を先に出力/flushし、続いて既存bufferだけから詳細を保存した。
WriteFile/FlushFileBuffers=confirmed、evidence_file_closed=true、private証跡114763 bytes。
実行時buffer SHA-256は **36dcd18871234b76b5db32b7a258b7bf157a61f8ad3763cfbf4a9cff3a6b1a87**。
既存の有界held-handle読取りで保存fileのhash一致とB1DBG001形式を照合した。
normal5/drain1、wait/continue inflight=false、未確認領域bytesはzero。
metadata中のdriver結果は証跡write/flush/close前のscopeで、最終保存状態は先行reportで確認する。
fixture_retention=unverified、native_accepted/formal_permission=falseを維持する。

## 保存stackで追加確認できた範囲

現在ntdllのidentity/name/hashと保存image rowを照合し、同じ保存2048 bytesから10段のunwind/CALLを確認した。
停止点はsaved_stack_exhausted。LoadDllInternal frame0x1ff1bの復元RBXは保存stack offset584を指し、
そのDWORDは今回も0xC0000142だった。生のregister/絶対addressは公開要約へ出していない。
これは解放中の内部statusの観測であり、今回の自然終了コードや最初の失敗DLLを確定するものではない。
3窓以外の実行時loaded bytesの完全一致未証明というunwindの制約も維持する。

## 観測側で見落としていた条件と修正方針

現在imageのLdrpUnloadNodeには、0x865caのXOR R15D,R15Dと、0x86815のMOV DWORD [RDI+0x40],R15Dがある。
後者は0x867e9で[entry+0x68]のbit0x80を検査する経路上にあり、その後0x86839でDereferenceModuleを呼ぶ。
すなわち解放前にサイズを0にする経路があり、「unload時でも必ず正のサイズ」という観測側の前提は成立しない。
この静的経路の存在だけで、今回の未保存サイズが実際に0だったとは証明しない。
隣接する次の関数0x86880より前の6 fragments/164命令も確認し、R15の書込みはprologのXORとepilogのPOPだけだった。

修正候補v2では0も許容し、上限とuser範囲を維持する。サイズは読取り長や次のpointer追跡には使わない。
追加取得の対象・回数・1059-byte上限・code照合・base一致を維持する。
また、完全readと直後の予算検査を通った112 bytes/sizeをprivate証跡に先に保存し、解釈失敗と取得失敗を区別する。
base/sizeの検証に失敗すればentry_uncertainのまま停止し、flags/bitを確定値として出さない。
short/false/中断readを完全なrawへ補完することはしない。
この修正を実機で試す場合は、準備・試験・レビュー後に別の1回として判断を求める。今回の承認を再利用しない。

## 実測環境と負荷

同runのpreflightは19 sources/215813 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存exe/python314.dll hash一致。UBR緩和と実測記録を維持する。
memory sampler64回、親＋childの記録上peak commit23793664 bytes（約22.69 MiB）、peak working34648064 bytes（約33.04 MiB）。
これは短い診断中のsample値であり、継続的なリーク試験ではない。
実行前PC空きRAM8.68 GiB、C102.31 GiB、D75.36 GiB。
追加権限/ACL変更、code/registry/PEB変更、breakpoint追加、常駐helper、他project操作は行っていない。

## v2修正の検証

サイズ0の成功、base/上限不一致でも完全readのrawを保存してflagsを未確定にする経路を追加確認した。
driver接続試験でも、サイズ0の正常観測と、上限不一致後のowned stop/private証跡保存を検証した。
関係fake32/32 pass（0.499秒）、debug全体131/131 pass（1.078秒）。独立レビュー新規P0〜P3=0、指定32/32 pass（0.478秒）。
context成功例の最大幅JSONは7418 bytesで8 KiB枠内。全体64 KiB容量試験もpass。repository safety/diff-check pass。
担当の完了通知を利用し、進捗ポーリングなし。v2で追加の実child・実RPMは行っていない。

修正保存3699d2e後のread-only preflightは19 sources/216179 bytes、2.256秒、verified、同じruntime/hash、resource_stop=false。
今回の公開要約6件はignored artifacts/context-offline-2026-09-10に保持し、計51469 bytes。
native-summary.jsonl、native-readback.json、rejected-size-static.json、stop-and-internal-status.json、v2-preflight.json
（これら5件はunload-entry-接頭辞）とunload-size-zero-path.json。新規private証跡は別に114763 bytes。
実行後の参照ntdll有界readは4回、今回証跡の有界readは2回で、hash一致・reader closeを確認した。
参照read回数には、静的解析でfragment終端を短く仮定して停止した1回と、次の関数境界を使って修正した読取りを含む。
診断childを追加起動したものではない。PDBは既存cacheを1回再使用し、追加download/raw imageコピーなし。
確認後PC空きRAM8.38 GiB、C102.34 GiB、D75.36 GiB。主作業以外の変動も含むためリーク有無は未判定。
mainは基準commitのままclean。v2の実機実行は別の1回として判断待ち。
