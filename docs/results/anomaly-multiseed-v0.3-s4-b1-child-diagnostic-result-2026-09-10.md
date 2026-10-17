# S4-B1 固定終了コードによる停止箇所の確認

状態: **子の_child_main呼出後、runtime_pin検査で停止。control未合格**。
直前の[限定診断計画](anomaly-multiseed-v0.3-s4-b1-child-diagnostic-plan-2026-09-10.md)へのユーザー「続けてください」を了承として、追加診断1回を実行した。
実装911d5a5、実行時clean HEAD a429a9c。wrapper3983 bytesの実行前SHAは
31c8e05df0eba398f6a7d528250acaee5eb8e1171a6dcd4616ad61fa345a0e9eで一致。
既存fixture再利用・同じwrapper再実行・debug collector・SetThreadContextなし。

結果はfailed / child_failed / child_exit_code278331392、core0.6305790999904275秒。
保存sourceの診断プロトコルでchild_call/runtime_pin/WinError0へ復号した。
ここで初めて固定childからの理由を観測した。前のexit1を遡って同一原因とは断定しない。
_child_main冒頭の_runtimeで停止し、子側のsource/token/AccessCheck/実操作検証は未完了。
runtime_pinはOS情報・CPU種類・Python metadataの複合条件なので、失敗した個別項目は未確定。
親側の実child token確認とAccessCheck、resume完了は保存sourceの分岐順に基づく判断。

control failed / cleanup not_started / teardown pass / resource_stopfalse。
replace trace incomplete、0 records / 0 bytes、private_controlなし、private_replace0 bytes。
ledger known_bytes5926、失敗fixtureの存在・残存量はunverified。
失敗後のfixture再open、ACL修復、清掃、移動、再利用なし。
native_accepted/s4_accepted/formal_permission/execution_authenticatedは全てfalse。
Python3.12既定受入・本流統合・formal/B2/publisherは閉じたまま。

親＋子ピークprivate44,249,088 bytes（42.20 MiB）、working56,061,952 bytes（53.46 MiB）。
system commit34,343,825,408 / limit70,493,097,984 bytes。
実行内preflight verified、27 sources / 284856 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
実行前09:08:09Zの空きRAM8.16 GiB、C108.44/D75.36 GiB、boot2026-09-09T10:43:08.5+09:00。
UBR固定緩和と実測記録を維持し、別projectの連続稼働テストに操作していない。
点の資源量からリーク有無を断定せず、今回のowned teardown passを記録する。

公開要約child-diagnostic-control-native-summary.jsonlは2091 bytes、
SHAd3ee07bd86d846726d810812524676fdcaba3cbef49ad22feee63ec130544bd2。
既知pathから1回有界readして値/hashを確認し、child-diagnostic-result-check.jsonへ保存。
private raw/token/SD/絶対temp pathは文書に出していない。
次の[CPU構成の直接確認への修正](anomaly-multiseed-v0.3-s4-b1-runtime-machine-plan-2026-09-10.md)を準備する。
