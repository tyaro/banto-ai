# S4-B1 最初のunload時の管理情報観測

状態: **実装・fake試験・独立レビュー完了 / read-only preflight待ち / 新規実機診断は未承認・未実行 / no native acceptance**。

## 目的と得られる判断

[静的status解析](anomaly-multiseed-v0.3-s4-b1-startup-symbol-analysis-2026-09-10.md#5-statusの静的な生成伝播候補2026-09-10追記)では、
初期化失敗のstatusが生成・伝播される複数の経路を確認したが、実行された経路と失敗DLLを特定できなかった。
今回は最初のnormal UNLOADに限り、解放対象moduleの管理情報に0x100000の印が残っているかを調べる。
現在imageのInitializeNodeは失敗処理0xe86eで[module+0x68]にこのbitをORする。
bitの有無は観測値として残し、初期化callbackの戻り値そのものや最初の失敗APIとは扱わない。

- bitあり: そのunload対象の管理情報に、参照imageで初期化失敗時に設定するbitが観測されたという証拠。
- bitなし: そのmoduleの当該bitが保存時点でclearだったという証拠。起動成功や別moduleの失敗不存在の証明にはならない。
- 条件不一致/取得失敗: その状態を残して停止し、別register/address/後続UNLOADで再試行しない。

LOAD_DLLのhandle由来の名前・identity行とunload baseを結び、対象の名前を判断する。新しい名前pointerの読取りはしない。
対象名が判明しても、そのDLLを修正・置換すべきだとは判断しない。

## 保存証跡での実現可能性

4回目の証跡（hash c98e30a618e2933d5c206ec292e8dc4d3c5756f751c6cb541b0ea255ef0fb4fe）を再照合した。
現在ntdll（hash a74f7482085eab125ccc09152ab7e0b5994bcb13e1a7b29880bdbb24179ecb8b）の
LdrpUnmapModuleは引数をRBXに保持し、[RBX+0x30]をRDXに渡してNtUnmapViewOfSectionをCALLする。
管理情報のbaseを0にする命令0xa7956と、呼出し元での管理情報解放はこのCALLの後にある。

保存RIPはntdll+0x161304、stack先頭の戻り先はntdll+0xa7956。
保存RDXは当該UNLOADのbaseと一致、RBXは検証済みDereferenceModule frameの復元RBXとも一致した。
RBXは8-byte alignedのuser address範囲内だが、その先160 bytesは保存2048-byte stackの外にある。
したがって候補pointerまでは既存証跡で確認でき、管理情報の内容は新しい観測が必要。
この照合は現在fileと過去のloaded bytesが完全に一致した証明ではない。

unload経路ではnode状態を-2に書き換える命令0x867bbもある。
後からnode状態だけを読んでも初期化時の状態が残るとは限らないため、今回node pointerの追跡は採用しない。

## 追加取得と照合の順序

既存のcontext/stack collectorに `DebugDriver(unload_entry=True)` で明示的に接続する。既定はfalse。
collectorと845-byte scratchはchild作成前に確保する。最初のnormal UNLOAD、初期thread、同じpending eventだけを選ぶ。
借用process/thread handleとPID/TID、停止・inflight・所有状態、時間/資源予算の既存検査を使う。
従来どおりGetThreadContext 1232 bytesとstack 2048 bytesを各1回取得した後、次を実施する。

1. 既存image行と過去のLOAD/UNLOADから、ntdllと解放対象が有効なloadに対応することを確認する。
2. RIP=ntdll+0x161304、stack先頭=ntdll+0xa7956、RDX=UNLOAD base、RBXの8-byte alignment/user範囲を要求する。
3. 下表のcode windowsを所有childから各1回読んでSHA-256を比較する。全3件が一致するまでRBX先を読まない。
4. RBXから**112 bytesを1回**読む。baseフィールドがUNLOAD baseと一致し、image sizeが(0,128 MiB]かつuser範囲内であることを要求する。
5. 0x68のDWORDとbit比較結果、112 bytes、対応するLOAD slotをprivate証跡へ保存する。

| RVA範囲 | bytes | 必須SHA-256 |
| --- | --- | --- |
| 0xa7914..0xa7962 | 78 | e0a563e3a45030256777f689a5762c637e3f286542eab1a002adb9a55fd6593b |
| 0x1612f0..0x161308 | 24 | 14116fd0c31066a6d45243a44f006cc6725bb451c1e7fed5a57e074e5f3ad058 |
| 0xe5d0..0xe91d | 845 | f86272015b824466fa57a03405df5fd1728e1bed86ffe3aab15b61faf419789c |

codeは計947 bytes、管理情報と合わせた**追加ReadProcessMemoryは最大4回/1059 bytes**。
従来stack読取りを含めると最大5回/3107 bytes。短いread・失敗・中断・hash不一致を成功に補完しない。
codeのdiskコピーは作らず、一致件数と固定recipe識別子を記録する。recipe名は参照したbuildであり、実行OSを認定する値ではない。
OS buildは従来のUBR緩和済みruntime検査で別途実測記録する。新しいsymbol検索・DL・適合する別recipeへの自動切替なし。

参照PEのbase relocation表1712 bytes/814個のDIR64 relocationを検査し、3 code windowsとの重なりはなかった。
これは通常のbase relocationで比較対象が変化しないことの確認であり、実際のloaded bytes一致は実機で別途判定する。
3 windowsの一致からimage全体の認証や、そのcodeが過去に実行されたことまでは主張しない。

## 停止・保存・資源条件

各追加readの前後で同じpending/所有handle/stop/resource/時間予算を再確認する。
read不確定・長さ不一致・code不一致・entry不一致で既存owned stopへ進み、後続eventやdrainで追加取得しない。
GetThreadContextやReadProcessMemory以外の新規native APIは使わない。
全breakpoint拒否、権限・token・code・registry・PEBを書き換えない条件を維持する。

既存の30秒/256 events/親＋child512 MiB未満の予算検査、停止drain最大32回/5秒、driverのdisk余裕検査を維持する。
この時間は同期native呼出しを強制中断できるhard timeoutの保証ではない。API前後で判定する。
追加rowはcontextの8 KiB枠内に含め、全体metadata64 KiBを増やさない。途中scratchはprivate ownerに保持し公開しない。
source pinにcollector1件を加え、19 sourcesをindexと照合する。raw fieldは既存B1DBG001 private証跡に含める。
resource stop時は既存の証跡disk書込み抑止に従う。通常終了時はpost-run summaryのwrite/flush/closeを任意解析より先に完了する。
過去の診断fixture/証跡は保持し、新しい診断を行う場合は新規専用fixture1個を使う。
他project、system-wide監視、常駐helperは操作・追加しない。

## 実機判断の前に完了する項目

fake試験で、callsite/image/寿命不一致、全code windowの不一致、false/short/oversize read、各read中の中断/stop/resource、
private内容の保持、field不一致、driverの停止/drainと証跡への接続、context8 KiB/全体64 KiB、既定offを確認する。
独立レビューは変更差分とこの計画に限定し、実childやprivate証跡の再取得を委譲しない。進捗ポーリングなし。
source保存と実read-only preflightを終え、追加1059 bytesを含む限定実機診断1回の範囲を提示する。
ここまでの実装準備は、追加実機診断の実施を意味しない。

## 実装とfake検証の完了

DebugUnloadEntryを追加し、DebugDriverの明示的なunload_entry=Trueだけで接続した。既定はfalseを維持する。
3 code windowsと上記の参照要約のRVA/サイズ/hashが一致することも機械的に照合した。
contextのRIP/RSP/TID/slotを最大幅にした成功例のJSONは7389 bytesで、8192-byte枠内。
既存driverの予約容量試験は19 source行と各collectorの全予約枠を含めても64 KiB未満を確認した。

変更に関係するfake34/34 pass（0.491秒）、debug関連全体130/130 pass（1.120秒）。
独立差分レビュー新規P0〜P3=0、指定fake34/34 pass（0.540秒）。repository safety/diff-check pass。
独立担当は完了通知のみを利用し、進捗ポーリングなし。実child・native preflight・private証跡への操作は委譲していない。
今回の実装準備で実ReadProcessMemory/GetThreadContext、対象memoryの書換え、追加child起動は行っていない。
