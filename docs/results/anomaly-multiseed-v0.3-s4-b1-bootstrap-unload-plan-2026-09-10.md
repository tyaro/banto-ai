# S4-B1 初期停止点の限定照合とUNLOAD観測の継続

状態: **了承済み1回実施 / bootstrap継続confirmed / 自然EXIT C0000142 / UNLOADなし**。

## 目的と許可する条件

[DETACHED診断](anomaly-multiseed-v0.3-s4-b1-detached-unload-result-2026-09-10.md)は最初のbreakpointで既定停止した。
次はDebugDriver(unload_entry=True, detached_console=True, bootstrap=True)だけで、
固定起動の初期thread・最初の例外・確認済みntdllの寿命・固定code・通常caller frameとの整合を検査する。
全条件が一致したpendingに限り、DBG_CONTINUEを1回呼んで以後の既存UNLOAD観測へ進む。
既定はoff。bootstrapはbool必須かつDETACHED+unload専用、init_return/console_failure/plainとの併用不可。

Microsoftの[ContinueDebugEvent仕様](https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-continuedebugevent)では、
例外にDBG_CONTINUEを使うとhandled扱いになる。この変更はその限定1回を許すもので、
単に最初のbreakpointを無条件に通すものではない。一般的なbootstrap認証や全初期化履歴を証明しない。

初回例外の受領時点で選択を消費し、検証失敗後に別の例外を選び直さない。
PID/初期TID、CREATEとの対応、先行例外なし、first_chance1、code80000003、flags0、
chained record null、parameters1かつparameter[0]=0、固定ntdll RVA122239を要求する。
parameter[0]=0は保存済み今回証跡で確認した値。未使用parameterの意味は推測せず、
Continue直前の再検査では176-byte event全体の変化も拒否する。
確認済みntdll LOADは単一かつ生存中、base範囲/整列、借用process/thread handleと実PID/TIDを照合する。

## 追加の有界読取り

recipeはntdll-26200.9445-bootstrap-v1。
追加RPM1回目でntdll RVA122204の62 bytesを読み、固定hash
cc1cef07481f3ac8e2dc416ffe823e0fd00b0c493355ade7e14aa31067bfa009と照合する。
GetThreadContext最大1回（AMD64 CONTROL/INTEGER、1232 bytes）でRIP=base+12223a、
TF=0、RSPのuser範囲と16-byte整列を要求する。
このRIPは候補条件であり、今回の実機ではCONTEXTを取得していないため未測定。
一致しなければRIPを書き換えたり他値を許容したりせず、その値を保持して停止する。

追加RPM2回目はRSP+0x38の8 bytesだけで、callerがntdll RVA8c2e0/8dbe1/8df44のいずれかであること。
追加RPM3回目はcaller直前5 bytesだけで、E8 rel32 CALLが固定関数先頭122204を指すことを照合する。
追加はGet最大1/RPM最大3回75 bytes。pointer walk/stack unwind/symbol queryは実childで行わない。
完全取得したCONTEXTとcode/caller/CALLの有界rawはprivate証跡へ保持し、公開要約は状態/回数/RVA等だけ。
API false/short/oversize/不一致/資源停止で後続読取りを行わない。部分bufferや一次障害を保持する。

すべて一致した後も、Continue直前にpending slot/PID/TID/例外全体・ntdll寿命・所有状態・resourceを再検査する。
transportは固定verifierの実型だけを受け、任意bool/continue status/callbackによる許可APIを追加しない。
Continue呼出し前にconsumed/uncertainを記録し、API成功後の記録まで完了した場合だけconfirmedにする。
API失敗・記録中断・後続breakpointでは再検証/再継続しない。drain transportへ許可を渡さない。
SetThreadContext、target memory/code/PEB/token/ACL/registry書換え、新規停止点設定なし。

## その後の観測と資源

初期停止点通過後、既存の最初の通常UNLOADでGet1/RPM5回3107 bytesのcollectorを用いる。
合計Get最大2/RPM最大8回3182 bytes。別DLLへの選び直し・drain時の追加取得なし。
自然EXITとowned terminationを分け、初期停止点通過やDLL loadだけをchild E2E成功とは扱わない。
新規専用fixture1個、診断fixtureは保持、cleanup/repairなし。core通常control/token/ACL/固定child等は不変。

30秒/256 normal events/親＋child512 MiB未満/temp volume空き1 GiB以上、
owned stop drain32回/5秒の既存条件を維持する。同期APIを強制中断するhard timeoutではない。
追加private metadataは4 KiB以内。既存collector各枠を全予約した試験で64 KiBを超えたため、
metadata枠を72 KiBへ8 KiB増やし、全証跡bufferは163864 bytes（1 MiB未満）とした。
これは既存512 MiBのprocess memory上限を変更するものではない。旧証跡形式もreaderで読める。
追加sourceを含む23 sourcesを保存後にindex照合する。

## 実行wrapperと検証

ignored artifacts/context-offline-2026-09-10/bootstrap-unload-once.pyを準備。
2768 bytes / SHA-256 01f6e8074f8bfc1657b2b0eed4c02b5f4bf4a35ae37ed88a754442e7e4d6350b。
構文・run呼出し1か所を確認、未実行。起動前に公開要約fileを新規openし、
driver.run()を1回だけ呼び、最終reportをstdoutへ先行flush、非資源停止時だけ公開要約を保存する。
既存のreport OOM伝播、private evidenceのwrite/flush/close確認、所有stopを維持する。
失敗しても追加起動や自動再試行なし。

設計の独立点検は新規P0〜P3=0。最初の例外の選択時消費、pending全体/ntdll寿命の再検査、
Continue直前消費と不確定記録、parameter契約を明確化した。
関係fake75/75 pass（1.608秒）。全caller、例外parameter/CONTEXT/全readの不一致・false/short/oversize/OOM、
API前後のresource停止、deferred pending改変、Continue false/OOM/成功後記録中断、
2回目breakpoint拒否、bootstrap後のUNLOADまでGet2/RPM8合計3182 bytes、証跡両collector保存を確認した。
全体回帰・独立実装レビュー・保存後preflightを追記する。
全acceptance gateはno、本流統合/formal/B2/publisherは対象外。

準備完了後、上記の固定停止点が検証できた場合だけ1回継続する、新規fixture診断1回を判断対象とする。
引継書§6の追加probeの条件に従う。具体的な問いへの「続けてください」は当該1回への了承として扱う。


## 全体回帰と独立実装レビュー

全体pure/fake245/245 pass（3.558秒）、repository safety/diff-check pass。
独立実装レビューは新規P0〜P3=0、指定fake75/75 pass（1.790秒）。
選択時消費/parameter契約/pending全体/ntdll寿命/Continue不確定時の再試行禁止、
後続breakpoint拒否・drain許可非伝播、両collectorの保存と72 KiB予約を確認した。
担当は実機・wrapper実行・private証跡参照・source変更なし、完了通知のみを利用して進捗ポーリングなし。
空きRAM8.44→8.06 GiB、C107.92/D75.36 GiB。単発値からリーク有無は未判定。
通常control/追加診断の実機再実行なし。次はsource保存後のread-only preflightを行う。


## 保存後preflightと次の1回

実装・試験・今回結果・計画を4c964c8に保存した。保存後read-only preflightは2.270秒、
23 sources/255021 bytes、verified、resource_stop=false、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
bootstrap-unload-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

準備は完了。新規fixture1個で固定初期停止点の全条件が一致した場合だけ1回DBG_CONTINUEし、
以後の最初のUNLOAD/終了まで観測する診断1回を判断対象とする。
合計Get最大2/RPM最大8回3182 bytes、Setなし、既存時間・memory・disk・owned stop条件を維持する。
この問いへの「続けてください」は当該1回への了承として扱い、clean状態とwrapper hashを照合後、同じ了承を再確認せず実行する。
RIP/code/caller等が一致しない場合も自動再試行せず、未観測/検証失敗/通常継続/強制停止/証跡保存を分けて記録する。


## 実施結果

ca6a6daで了承済み1回を実行し、bootstrapの全条件とDBG_CONTINUEを確認。UNLOADなしで自然EXIT C0000142を観測した。
[実行結果](anomaly-multiseed-v0.3-s4-b1-bootstrap-unload-result-2026-09-10.md)を参照。RIP=address+1もこのrunで確認済み。この計画の1回は消化済み。
