# S4-B1 runtime修正後の実操作検証への到達

状態: **子のruntime/source/token/AccessCheck検査を通過し、実操作の期待値不一致で停止。control未合格**。
[修正候補1回の計画](anomaly-multiseed-v0.3-s4-b1-runtime-machine-plan-2026-09-10.md)へのユーザー「続けてください」を了承として実行。
実装6094466、clean HEAD60b1b70、実行前wrapper3982 bytesのSHAは
4292c3aefc011adfc7a204b76304ba3648e523c72eca2531babe11ec1413d9e9で一致。
新規fixtureのcontrol1回のみ。以前のwrapper/fixture再利用、debug collector、SetThreadContextなし。

## 実測と解釈の範囲

結果はfailed / child_failed / child_exit_code37、core0.6436681000050157秒。
固定protocolでchild_call/operation_unexpectedへ復号した。
旧実装の_needが実API errorを保持していないため、診断上のwinerror0は実API成功を意味しない。
不一致となった操作名・実WinErrorは今回の終了値から復元できない。
保存sourceの順序から、子のruntime、要求読込、source/token、子AccessCheck、trace初期確認を通過し、_operationsへ到達したと判断できる。
前のruntime_pinは観測されなかったが、前回の個別失敗条件がCPUだけだったと遡って確定はしない。

control failed / cleanup not_started / teardown pass / resource_stopfalse。
replace trace incomplete / 0 records / 0 bytes、private_controlなし、private_replace0 bytes。
全操作の合格・子report照合・成功cleanupは未完了。
known_bytes5926、失敗fixtureの存在・残存量unverified。失敗後の再open/清掃/ACL修復/移動/再利用なし。
native_accepted/s4_accepted/formal_permission/execution_authenticatedは全てfalse。
Python3.12既定受入・本流統合・formal/B2/publisherは閉じたまま。

親＋子ピークprivate44,515,328 bytes（42.45 MiB）、working55,533,568 bytes（52.96 MiB）。
system commit34,744,274,944 / limit70,493,097,984 bytes。
実行内preflight verified、27 sources/285764 bytes、Windows10.0.26200.9445/Python3.14.0、既存exe/DLL hash一致。
実行前09:28:51Zの空きRAM7.88 GiB、C108.38/D75.36 GiB、boot2026-09-09T10:43:08.5+09:00。
UBR緩和と実測記録を維持し、別projectの連続稼働試験に操作していない。
点の資源量でリーク有無を断定せず、今回のowned teardown passを記録する。

公開summary runtime-machine-control-native-summary.jsonlは2086 bytes、
SHA0568e33c6a1c40abb478cb5f0a532021c7b3cdebe4a34744c585423bde02b882。
既知pathから1回有界readして値/hashを照合し、runtime-machine-result-check.jsonへ保存。
private raw/token/SD/絶対temp pathは文書へ出していない。
次の[作業場所と操作診断の修正](anomaly-multiseed-v0.3-s4-b1-operation-context-plan-2026-09-10.md)を準備する。
