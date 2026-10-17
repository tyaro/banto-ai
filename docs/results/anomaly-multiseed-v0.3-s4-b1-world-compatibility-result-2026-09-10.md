# S4-B1 RC＋Everyone controlの限定実行結果

状態: **子プロセスのresume後、exit1で停止。B1 control未合格**。
ユーザー「続けてください」を[具体的な1回の計画](anomaly-multiseed-v0.3-s4-b1-world-compatibility-plan-2026-09-10.md)への了承として扱い、同じ確認を挟まず実行した。
この1回を消化済みとして記録し、同じwrapper・失敗fixtureを再実行しない。

実装c0909ac77263603dab2945bc4ac8f369889178e7、実行時のclean HEAD 8c83192。
world-compatibility-control-once.pyは3891 bytes、実行直前のSHA照合一致
1c1a92734ce87ea8d3988cd2a3653fb2d096b93a074cf415e7d394607d207348。
通常controlの新規fixture1個のみで、debug collector/SetThreadContextは使っていない。

## 観測結果とその限界

safe resultはfailed / child_failed / WinError0 / child_exit_code1、core0.6294818999886047秒。
control_status failed、cleanup_status not_started、teardown_status pass、resource_stop false。
固定sourceの分岐順から、CreateRestrictedToken、実プロセスのprimary token照合、
実tokenからのduplicate、親側AccessCheck matrix、resume、終了コード取得まで完了したと判断できる。
親AccessCheckの生データを別途公開・保存したという意味ではない。

以前のDLL初期化終了C0000142は今回観測されなかった。
ただしexit1はinterpreter起動側にも固定childの汎用例外経路にもあり、
これだけでPython _child_main到達・子側の保護検証・起動全体成功を証明しない。
replace traceはincomplete / 0 records / 0 bytes。空であることだけで_operations未到達とも断定しない。
private_controlはなし、private_replaceは0 bytes。
失敗fixtureは保持方針、ledger上known_bytes5926、実際の残存量・存在はunverified。
失敗後のfixture再open、ACL修復、清掃、移動、再利用はしていない。

native_accepted / s4_accepted / formal_permission / execution_authenticatedは全てfalse。
Windows Python3.12を含む既定受入、本流統合、formal/B2/publisherは未完了・未許可。
RC＋Everyoneでホスト全体が従来同等に隔離されるとは主張しない。

## 資源・runtime・保存証跡

親＋子ピークprivate44,621,824 bytes（42.55 MiB）、working56,381,440 bytes（53.77 MiB）。
system commit34,679,246,848 bytes / limit70,493,097,984 bytes。
Windows10.0.26200.9445、Python3.14.0、既存exe/DLL hash一致。
実行内preflight verified、27 sources / 278078 bytes。
作業前08:49:27Zの空きRAM8.04 GiB、C108.45/D75.36 GiB。
診断コード検証後08:59:08ZはRAM7.61 GiB、C108.43/D75.36 GiB。
bootは2026-09-09T10:43:08.5+09:00。UBR固定緩和と実測記録を維持する。
点の資源値からメモリリークの有無は断定しない。今回所有した対象のteardown passを記録する。
別projectの連続稼働テストへ操作していない。

公開要約world-compatibility-control-native-summary.jsonlは1997 bytes、
SHA20c80de096fa753c4dbae6281c1df255f06e175f8c461d12eb95391384f477b3。
既知の要約pathを1回有界readして値/hashを照合し、world-compatibility-result-check.jsonへ保存した。
private raw/token/SD/絶対temp pathは文書へ出していない。

次は[固定終了コードの診断計画](anomaly-multiseed-v0.3-s4-b1-child-diagnostic-plan-2026-09-10.md)により、
権限や保護対象の変更を伴わず停止理由を絞り込む準備を行う。
