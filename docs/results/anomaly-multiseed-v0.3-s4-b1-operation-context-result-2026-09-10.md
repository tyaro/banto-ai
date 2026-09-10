# S4-B1 Windows engineering control成功の記録

状態: **native_control_pass / control pass / cleanup completed / teardown pass**。
ユーザー「続けてください」を[最大3候補・各1回の進行方針](anomaly-multiseed-v0.3-s4-b1-operation-context-plan-2026-09-10.md)への了承として受領。
§6の都度確認をこの範囲で緩和し、準備済み候補の1回目を実行した。成功時に停止する条件に従い、試行枠は終了。
残り2回を予約・繰越・再実行せず、追加native controlは行わない。

実装0b30e63、実行時clean HEADf15af39。wrapper4047 bytesの実行前SHAは
8dc7b3940930212f477c95b195a2960a0eac0c7bffadcea27784f77a113b0658で一致。
新規専用fixture1個、RC＋Everyoneの固定token、非昇格、flags9、起動flags0x40c、CWDはfixture.root。
保護DACL・必須期待値・資源上限は維持した。既存failure rootsや別projectへ操作していない。

## 確認できた結果

core0.9394162999960827秒、resource_stopfalse。
実child token照合、親・子AccessCheck、runtime/source確認、子の全必須操作、report照合を通過。
wrapperはprivate child reportのoperationsが固定期待値と一致することを実行中に確認した。
対象はcontrol/frozenそれぞれfile right-open5＋directory right-open6＋mutation13の合計48期待値。
controlの許可とfrozenの拒否を確認し、report上のno_impersonation/isolated/no_bytecode、
標準handle条件、固定RC＋Everyone recipeも照合した。独立したhandle全件列挙を行ったという意味ではない。

replace traceはcomplete、6 records、最終restored、2385 bytes、unconfirmed tail0。
source at_original、original destination consumedという定義済みの置換control結果を確認した。
成功cleanupのsnapshotは9対象・15616 bytes、9対象のdeletion absent/close confirmed、unknown_objects0、success_residue_count0。
15616 bytesはcleanup前の捕捉量であり、残存容量ではない。
存在確認はharnessの既定cleanupに基づく。終了後のfixture再openや追加走査は行っていない。

この候補で子のE2E成功が得られた。一方、直前の旧exit37では実API error/操作名が失われており、
その唯一原因がCWDロック/WinError32だったと遡って確定はしない。
今回の成功範囲は専用fixtureと既定操作に限定される。

## 資源・保存証跡

親＋子ピークprivate44,797,952 bytes（42.72 MiB）、working55,713,792 bytes（53.13 MiB）。
system commit34,612,957,184 / limit70,493,097,984 bytes。
実行前09:48:47Z RAM8.05 GiB/C108.16/D75.36 GiB、実行後09:49:50Z RAM7.87 GiB/C108.15/D75.36 GiB。
Windows10.0.26200.9445、boot2026-09-09T10:43:08.5+09:00、Python3.14.0、既存exe/DLL hash一致。
UBR固定緩和と実測記録を維持。点の資源量からリーク有無を断定せず、今回のowned teardown passを記録する。
実行内preflight verified、27 sources/288326 bytes。前回保存済みpure/fake293件・独立差分レビュー後、sourceの再変更はない。

公開要約operation-context-control-native-summary.jsonlは4305 bytes、
SHA830ead15ce782c023a895fc3aefe0bbfb8a433d252c3032f8e85d338ae100293。
既知pathから1回有界readして要約値・hash・48期待値の件数・cleanup状態を照合し、operation-context-result-check.jsonへ保存。
この再読はprivate reportを再取得したものではない。
private controlは実行時16494 bytes/hash5d888eaebd1cea0980c2ae66f37692fd2f46b26f8574a138e8d059e001de2af2、
private replaceは2385 bytes/hashd876cf2a222b7d63b4a02ecc86422e4bbc081989dfd4f650ddd826c38bfda66f。
公開要約に保存したのはサイズ/hash等のみで、private raw/token/SD/絶対temp pathはexportしていない。
成功cleanupによりfixture上の報告は削除済みで、公開要約から生報告を復元できるとは主張しない。

## 残る受入条件

native_accepted/s4_accepted/formal_permission/execution_authenticatedは全てfalseのまま。
この1回はengineering controlの成功であり、Windows Python3.12を含む既定受入・本流統合・S4全体の受入は未完了。
full suite/S3長期回帰を今回追加実行したものではなく、既定native unittest全体をまとめて再実行していない。
main889cfc3はcleanのまま。push/merge、formal dev/smoke/holdout、B2/publisher、Hub/PLC writeは行っていない。
次に進める場合は、保存済み成功結果を基準に受入条件・Python3.12の扱いと本流統合に必要な確認を整理する。


成功結果・公開要約・handoff最新記述の独立照合は新規P0〜P3=0。
48期待値は実行中wrapperのoperations_matchと保存sourceの期待値件数に基づく。
公開要約だけからprivate reportの個別値を独立再検証した主張はしない。
担当は指定公開資料のみをreadし、native/query/fixture再open/試験/編集なし。進捗ポーリングなし。
