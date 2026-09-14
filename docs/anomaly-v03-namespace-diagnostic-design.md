# S4-B2 親作成エラーの新規限定診断

2026-09-15 JST、基準2b865dc。[最初の比較枠](results/anomaly-multiseed-v0.3-s4-b2-namespace-create-2026-09-15.md)は親CreateDirectory2Wで停止し、WinError数値が報告から欠けたため原因未確定。
失敗したsource/attemptやprivate-evidenceへ戻らず、その値を後から復元しない。保存済みstdout/監視記録のみ利用する。

namespace限定のsnapshotへparent_create_winerrorを加える。既存取得部品がAPI失敗直後に例外へ保存した値を使う。
phase=create_pending、型OwnershipError、reason=directory_create_failed、正の32bit整数だけを値として出力し、それ以外はnull。
報告時にGetLastErrorを再呼出しせず、ownership/終了/拒否分類/実access/share/SD/API引数を変更しない。MemoryError等は既存固定resource notice/exit80を維持する。

fakeで実ParentBackendの返却失敗からsnapshotへの5/32/87/183保存と、driver→単回stdout→exit81/祖先保持・後続未実行を検証する。
独立レビューと実装savepoint後、新規clean checkout namespace-diagnostic-20260915/banto-aiへ固定し、入力pinを新規作成する。
新規batch namespace-diagnostic-2026-09-15のmax1だけを使う。閉鎖済みnamespace-create枠は再利用しない。
[前回の比較条件](anomaly-v03-namespace-create-design.md)と順序を維持し、share3最初の親が失敗してもそこで終了する。
成功した場合だけ同じ有界matrixを続ける。新規最大2root/2child/8peer、同一process/token、payload write/delete/renameなし。
親失敗数値は今回の新しい観測に限定し、前回の失敗原因や共有条件の一般則へ遡及しない。

内側40秒/1024点、外側45秒/500ms・96点、private256MiB/working384MiB、空きRAM/disk2GiB、出力384KiBの上限を維持。
返却不明の所有はworker終了まで保持。監視は起動した当該processだけを扱い、終了確認後にstdout/stderr/claim/監視記録だけを保存する。
原因判明後の対策や異なる比較条件は今回のnative枠内で試さない。追加nativeが必要なら別途仕様・回帰・レビュー・savepointを先に行う。
既存Python3.14.0、OS build/boot記録、Windows Update engineering緩和/正式pin不変。新account/service/runtimeなし。
namespace_consistency=unresolved、isolation/protected commit/future immutability/formal permission/execution authenticationはfalse、acceptance_status=not_completed。
