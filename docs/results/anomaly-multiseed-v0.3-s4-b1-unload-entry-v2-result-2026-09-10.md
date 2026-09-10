# S4-B1 管理情報観測v2の実機結果

状態: **承認済み1回終了 / KernelBase.dllの初期化失敗bitを確認 / 自然終了0xC0000142 / 原因APIは未確定 / no native acceptance**。

ユーザーの「続けてください」を、修正版の限定診断1回への了承として実行した。
cleanな隔離worktreeのHEAD b0a81ee（v2実装3699d2e）で、新規専用fixtureを使い
DebugDriver(unload_entry=True).runを1回だけ呼んだ。今回の1回は消化済みで、追加起動は行っていない。
[v1結果](anomaly-multiseed-v0.3-s4-b1-unload-entry-result-2026-09-10.md)の未保存値を、今回の値で埋めない。

## 1. 観測と終了・保存

初期reportまで2.365秒。driver/observerはobserved、primary/secondary reasonなし、resource_stop=false。
これは診断が観測を完了したという結果であり、restricted childの起動成功ではない。

| 観測対象 | v2の結果 |
| --- | --- |
| ntdllの固定code3窓 | 全947 bytesのSHA一致 |
| 管理情報 | RBX先112 bytesの完全read、rawをprivate保存 |
| 対象 | 有効なLOAD slot3のKernelBase.dll。entry内baseとUNLOAD baseが一致 |
| image size（entry+0x40） | **0**。v2で許容する範囲内 |
| flags（entry+0x68） | **0x38a28e** |
| 初期化失敗bit | **0x100000が設定済み** |
| callback（entry+0x38） | 対象baseからのRVA **0x5060** |
| 子processの自然終了値 | **0xC0000142** |

bitの意味は参照ntdllのInitializeNode失敗処理での設定命令に基づく。
KernelBase.dllの管理情報に初期化失敗の印があったことは確認できたが、callbackの過去の戻り値や最初の失敗APIは未観測。
code3窓の一致を、KernelBase.dllを含むloaded image全体の一致へ拡張しない。

通常eventはCREATE python、LOAD ntdll、LOAD kernel32、LOAD KernelBase、UNLOAD KernelBase、
UNLOAD kernel32、EXITの7件。最初のUNLOADで採取し、7件すべてのContinueを確認した。
drainは0件、TerminateProcessはnot_started。stopのexit_continued=falseは通常observerがEXITを処理したためで、
終了通知を未処理にした結果ではない。process signal、debug ownership解消、所有process/thread handle close、
teardown=pass、failure_count=0を確認した。

追加memory読取りは最大どおり4回/1059 bytes。従来のstack2048 bytesは別枠で、context/stackの繰返し取得なし。
終了後は最終summaryを先に出力/flushし、private証跡115051 bytesをwrite/flush/closeした。
bufferと保存fileの有界readbackのSHA-256は一致した。

`155215a8f0b1cb4d6dd69f29b3c2c401c3f0b741b5672b890acc69f71c23c325`

normal7/drain0、wait/continue inflight=false、未確認領域はzero。
metadataのdriver状態は証跡保存前のscopeで、最終write/flush/closeは先行reportを根拠とする。
fixture_retention=unverified、native_accepted/formal_permission=falseを維持する。

## 2. 現在のKernelBase.dllと公開PDBの照合

保存image行の名前・volume/file IDと現在のSystem32 KernelBase.dllをheld handleで照合した。
fileは4212112 bytes、PE SizeOfImageは4202496 bytes、SHA-256は次のとおり。

`becad014fb8efa8cb5e314931cca92778ad42c649b12a6909632cacd68af4f40`

現在fileのPE AddressOfEntryPoint=0x5060は、今回保存したcallback RVAと一致する。
これは現在fileの参照情報との対応であり、実行時KernelBaseの全bytesの一致は未証明。

CodeViewのGUIDは72cce506-944d-e026-7c17-2ad64287f9bd、image age1。
[Microsoft公開symbol serverの該当PDB](https://msdl.microsoft.com/download/symbols/kernelbase.pdb/72CCE506944DE0267C172AD64287F9BD1/kernelbase.pdb)
を非圧縮16 MiB上限で1件取得した。HEADはmsdlの302と転送先の200、body GETは1回。
12521472 bytes、12.986秒、SHA-256は次のとおり。

`163b1364515ec25a34d0be3eb91cb988dd74b84f115e82968fe98040b556dca1`

64 KiB分割read、Content-Encoding/length/ETag、socket5秒と処理間の30秒期限検査を使用した。
これはAPIを途中で強制中断する保証ではない。圧縮fallback・追加install・cache全体の操作なし。
既存byte-only matcherでGUID一致、DBI age1/AMD64、PE section headers全一致、OMAPなしを確認した。
Info age2はimage age1以上で、[前回確認したMicrosoftのPDB検証規則](anomaly-multiseed-v0.3-s4-b1-startup-symbol-analysis-2026-09-10.md)
に適合する。100068 records/44946 public functionsを走査し、関数名はentry RVAのexact一致だけを採用した。
download要約のinternal_guid_age_verified=falseは取得時点の記録で、後続の照合結果は別要約に保持する。

| entry RVA | exact一致した公開symbol名 |
| --- | --- |
| 0x5060 | KernelBaseDllInitialize |
| 0x51d0 | KernelBaseBaseDllInitialize |
| 0x4e6c0 | _KernelBaseBaseDllInitialize |
| 0x5ff0 | ?Initialize@Globals@ARI@@SAJXZ（以下、ARI::Globals::Initialize） |

## 3. 次の観測で区別したい経路

現在fileのentryを通常のreason=1で静的に辿ると、戻り値を分ける箇所は次の2系統になる。
今回の実行履歴を復元した表ではなく、例外・異常制御移動を含めた原因の網羅的な除外でもない。

| 系統 | 現在fileの命令と意味 |
| --- | --- |
| A: 基本初期化の戻り値 | 0x5068で0x51d0をCALLし、そこから0x5214で0x4e6c0へtail JMPする。entry側0x5103がALと1を比較し、AL≠1なら0x50baでその値を返す。**AL≠1をすべてfalseと同義に扱わず、0を返す場合が通常のfalse候補** |
| B: ARI初期化の戻り値 | AのAL=1の経路で、0x5133が0x5ff0をCALLする。0x5138のTEST EAXと0x513aのJSで負statusなら0x51c0へ進み、AL=0を返す |

_KernelBaseBaseDllInitializeには、WORD RVA0x3aeea0へ100/200/400/500/600/700を書き込む経路がある。
値とその後の通常失敗分岐を対応させると、次の観測候補になる。

| 書込み位置・値 | 近傍の失敗候補／静的に言える範囲 |
| --- | --- |
| 100の書込み前 | 0x4e8faのNtQuerySystemInformation後、負statusで0x4ec6bへ進む経路 |
| 0x4e94b: 100 | 0x4e992のCsrClientConnectToServer、または0x4ed52のCsrpLocalSetupForSecureProcess後、負statusで同じfalse出口へ進む経路 |
| 0x4e9ab: 200 | その後の共有情報調整などを通る途中段階。値だけから失敗APIは割り当てない |
| 0x4eb9a: 400 | 0x4eba1のBaseNlsDllInitialize後、AL=0でfalse出口へ進む経路 |
| 0x4ebba: 500 | 0x4ebc1のRtlInitializeCriticalSection後、負statusでfalse出口へ進む経路 |
| 0x4ebda: 600 | 0x4ebe1のConsoleInitialize後、AL=0でfalseを返す経路 |
| 0x4e82a: 700 | 基本初期化の成功側での書込み。これだけでentry全体やARI初期化の成功は示さない |

これらは到達段階の候補であり、値と失敗APIは一対一ではない。0x4ea02のWORD書込みは別RVA0x3aedc0で、同じ値に数えない。
detach側の本体とfragment[0x19f476,0x19f4c6)も当該WORDを読んでcleanupを分岐する。
確認した範囲に直接のゼロ化はないが、呼出し先等を含む全書込み不存在や、UNLOAD時点での値の保持は証明していない。
**今回、このWORDは取得していない**。moduleがunmapされる観測位置で、そのmemoryを安全に読めるかも未検証。

次工程は、現在の全breakpoint拒否・対象memory書換えなしの条件で、失敗後にも意味が残る値を取得できるかを評価すること。
このWORDの読取りだけを追加すれば必ず原因が判明するとして実機へ進めない。
有用な観測位置・上限・不一致時の停止を具体化し、必要な実装・試験・レビュー後に新しい実機範囲を提示する。
DLL名が絞れたことを、DLLの破損や置換・設定権限緩和の根拠にはしない。

## 4. 資源・検証・保存物

同runのpreflightは19 sources/216179 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存exe/python314.dll hash一致。Windows Updateに伴うUBR緩和と実測記録を維持した。
memory sample74回、親＋childの記録上peak commit23801856 bytes（約22.70 MiB）、peak working34435072 bytes（約32.84 MiB）。
PC空きは実行前RAM7.99 GiB/C102.09 GiB/D75.36 GiB、解析後RAM8.62 GiB/C101.93 GiB/D75.36 GiB。
他projectを含むPC全体の変動なので、差分全量を今回の処理に帰属させず、単発値からリーク有無も判定しない。

今回source/testの変更なし。既に通過済みのv2 fake/debug試験を繰返し実行していない。
公開要約の値・段階値6件の書込み先・文書リンクを照合し、repository safety/diff-checkはpass。
公開JSON5件を用いた独立レビューは新規P0〜P3=0。AL≠1の扱い、stageとAPIの非一意性、実行履歴未証明の留保を反映した。
担当は実child・private証跡読取り・試験を実施していない。完了通知を利用し、進捗ポーリングなし。

ignored artifacts/context-offline-2026-09-10へ次を保存した。既存証跡・fixtureも保持する。

- unload-entry-v2-native-summary.jsonl / unload-entry-v2-native-readback.json
- kernelbase-reference-entry.json / kernelbase-symbol-download.json
- kernelbase-initialization-static.json / kernelbase-base-initialization-static.json
- kernelbase-detach-fragment-static.json
- kernelbase-72CCE506944DE0267C172AD64287F9BD1.pdb（再取得不要）

公開要約7件は計104477 bytes、PDBは別に12521472 bytes。mainは基準889cfc3のままclean。

実行後の今回private証跡有界readは2回、現在KernelBase.dll有界readは4回で、各readerはcloseした。
PDBは保存済みcopyを再使用した。生register/絶対address、image rawコピーは公開要約に含めない。
追加起動、追加権限/設定変更、breakpoint追加、常駐helper、他project操作なし。
本流統合、child E2E成功、native受入、formal permissionは未達のまま。
