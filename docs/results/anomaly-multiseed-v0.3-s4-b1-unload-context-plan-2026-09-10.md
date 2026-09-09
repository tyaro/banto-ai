# S4-B1 最初のDLL unload通知での実行状態観測案（2026-09-10）

状態: **独立設計レビュー完了 / collector未実装 / 追加実機診断未承認・未実行**。

目的は、既に観測された最初のUNLOAD_DLL通知の時点で、初期threadがどこを実行しているかを保存すること。
現在の全breakpoint拒否、既存所有processだけの停止、30秒/256 events/親＋child512 MiB未満を維持する。
Procmon、loader snaps、code/PEB/registry変更、SetThreadContext、新規breakpointを必要とする案にはしない。

## 既存証跡と公式仕様から分かったこと

3回の診断は例外/breakpoint/debug string/RIP eventなし、通常7 eventsで0xC0000142へ終了した。
最後の保存証跡のslot4/5はKernelBase.dll、kernel32.dllに対応するUNLOAD_DLL通知である。
保存した生DEBUG_EVENTにはCONTEXTやstack内容はないため、過去のcall stackは復元できない。

[Debugging Events](https://learn.microsoft.com/en-us/windows/win32/debug/debugging-events)によると、
通知時は対象processの全threadが停止し、ContinueDebugEventまで再開しない。
また、process終了時の自動DLL unloadはUNLOAD_DLL通知を発生させないと記載されている。
このため観測したunload通知を、単にOSの終了処理で必ず出る通知として片付けない。
ただし特定のFreeLibrary callerや失敗元、loader rollbackをその事実だけで断定しない。

[GetThreadContext](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getthreadcontext)は
停止中threadの実行状態を取得し、THREAD_GET_CONTEXTを要する。CONTEXTはarchitecture固有の構造・alignmentを持つ。
通知で停止中の区間を使い、追加SuspendThread/ResumeThreadは行わない。
[ReadProcessMemory](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-readprocessmemory)は
PROCESS_VM_READを要し、要求全範囲が読めない場合は失敗する。部分取得を完全なstackとして扱わない。

## 観測範囲の具体案

| 項目 | 上限・扱い |
| --- | --- |
| 対象event | normal channelで最初に受けたUNLOAD_DLLのみ、1回 |
| thread | 起動時に所有した初期threadのみ。event TIDと一致しない場合は対象外として記録して終了 |
| 取得API | GetThreadContext 1回、成功時のみReadProcessMemory 1回 |
| CONTEXT | x64 CONTROL/INTEGERのみ要求。構造全体の固定領域と16-byte alignmentを事前確保・検査 |
| stack | 取得RSPから最大2048 bytes。固定長1回、範囲の縮小再試行・別領域探索なし |
| 保存枠 | context/stack/状態を含む追加private JSONを16 KiB以下に設計し、全体64 KiB上限も再検証 |
| 実行時の解析 | 命令実行・stack unwind・symbol download・pointer追跡なし。owned local bytesへの保存のみ |

取得位置はevent decode/identity確認後、通常Continue前。初期thread handleとprocess handleは
起動ownerから借用し、GetThreadId/GetProcessIdOfThread/GetProcessId等で既存PID/TIDとの一致を確認する。
OS管理のevent handleを新規所有へ変換せず、collectorはhandleを開閉しない。
normal observerへの1か所だけの接続とし、stop/drain/EXIT後/資源停止後には取得しない。

最初のunloadが別threadの場合はそのTIDを理由付きで記録し、新しいthreadをopenせず、次のunloadへ対象をずらさない。
最初のunloadが来なかった場合もnot_observedとし、追加再実行しない。
この1回は新規の子メモリ読取りを含むため、従来のACL/image取得だけの実行承認を拡張して使わない。

## 境界・所有・失敗処理

固定CONTEXT/stack/output length/状態rowはchild作成前に確保する。初期化済みのCONTEXT flagsを要求し、
必要なCONTROL/INTEGER flagsが返ったこと、RIP/RSPの整数範囲、RSP+2048のoverflowを確認する。
取得先bufferのaddressを16-byte alignedにし、bufferの寿命をcollectorに保持する。
CPU ABI/offset/sizeの根拠は[公式x64 CONTEXT](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-context)とSDK定義で確認する。

RSPの値は対象addressとしてReadProcessMemoryへ渡すだけで、親process内pointerとしてdereferenceしない。
bytes-readは0〜2048に限定し、成功時も要求長一致を確認する。FALSE・短い取得・不正値・OOM・時間/資源上限では
最初の失敗理由を保持し、追加native取得を行わず既存owned stopへ進む。
失敗したreadのbufferは確定stackにしない。資源停止時は従来どおり証跡の新規serialize/writeを抑止する。
結果未確定のAPIは再試行せず、pending eventは既存停止ownerへ引き渡す。

## 得られる情報と限界

RIPは通知時の実行位置であり、例外addressや失敗APIのaddressと同一ではない。
stack bytesにはreturn address以外の値も含まれる。単にmodule addressらしい整数を並べてcall stackと表示しない。
正確なunwindには対象image範囲・対応するunwind情報等の検証が必要であり、今回は実行中に追加収集しない。
既存のload baseだけでmoduleの終端を推測し、RIP/stack値の所属を断定しない。
最初のunload時点では既に元の失敗情報が失われている可能性もある。
raw stack/registersは非公開証跡に限定し、表示は状態/byte数のみ。別projectへの送信や全文公開はしない。

## 実装へ進む前の点検

独立担当へ設計の範囲・停止との接続・pointer/ABI・資源・解釈上の問題を確認依頼する。
実装後はfakeでalignment、対象外TID、1回制限、API失敗/短い取得、OOM、保存容量、breakpoint拒否維持を試験する。
preflight source範囲とprivate evidence全体容量を更新・検証してから、追加実機診断1回の具体的条件を提示する。
この設計文書の保存やレビューだけで実行承認済み・起動成功・native受入とは扱わない。

## 独立設計レビューとローカルSDK照合

既存の独立担当へこの設計と必要な既存adapterだけをread-onlyで依頼し、新規P0〜P3=0。
完了通知を利用し、進捗ポーリング・追加担当の起動は行っていない。
実装レビューでは、各native取得前後の予算検査、pending/inflight条件、中断直後の再取得抑止、
全体64 KiBの最悪時容量を確認する。設計レビュー通過は実装やABIの検証済みを意味しない。

このPCのWindows SDK 10.0.26100.0のum/winnt.hにあるAMD64定義をread-onlyで照合した。
CONTEXT_AMD64=0x00100000、CONTROL=同値|1、INTEGER=同値|2、要求合成は0x00100003。
構造にはDECLSPEC_ALIGN(16)が付き、P1Home〜P6Home、ContextFlags/MxCsr、segment/EFlags、
debug registers、integer registers、Rip、512-byte floating-point領域、vector/special領域が続く。
この定義に基づく実装候補値はContextFlags offset48、Rsp offset152、Rip offset248、全体1232 bytes。
これらは今回ヘッダから導出した値で、C compilerや実GetThreadContextによるABI試験は未実施。
特にctypesの構造サイズだけで16-byte allocation alignmentを保証したとは扱わない。

実装の最初の段階では、aligned owner bufferとoffset検査、fake APIへの引数・返却範囲検査を作る。
固定stack領域と部分結果を保持し、remote pointerを親側で参照しない構造を先に確認する。
通常channelのpendingが確定し、wait/continueがinflightではなく、stop未開始の条件をnative呼出し前後で守る。
例外・breakpoint・EXIT・drainではこのcollectorを呼ばない。所有handleが不明な時点で補完openしない。

今回code変更・実child・GetThreadContext/ReadProcessMemory実呼出しはない。
開始時空きRAM8.77 GiB/C102.24 GiB/D75.36 GiB。次工程はこの範囲の実装とfake試験であり、実機実行ではない。
