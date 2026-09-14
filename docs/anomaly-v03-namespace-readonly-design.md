# S4-B2 share READ親のpath追加だけを確認する新規case

2026-09-15 JST、基準37ec1c9。[直前の診断](results/anomaly-multiseed-v0.3-s4-b2-namespace-diagnostic-2026-09-15.md)でshare3親作成が87となった。
その不適合原因を今回さらに探ることはせず、[以前のdirectory-peer](results/anomaly-multiseed-v0.3-s4-b2-directory-peer-2026-09-14.md)で作成実績のあるshare1条件に絞る。
過去の成功を今回の取得成功やpath追加の拒否根拠へ代用しない。新規取得から記録する。

ReadOnlyNamespaceContextは既存namespace caseのshare-read-only 1個だけを使う。share-read-write controlは省略とreportに明記する。
matrixが受け付けるのは既存2caseまたはこの1caseだけ。空/重複/逆順/異なる単独controlを受け付けない。
新規root1個をCreateDirectory2W、access0x1600a7/share1/redirect拒否/private SD/非継承で取得する。
同一worker/tokenから既存4peer OPEN_EXISTINGを各1回行い、既知の非作成拒否と実accessを記録する。
原root保持中にnew-empty.binをpath CREATE_NEWで1回作る。成功時だけ元handleでID/SD/空/links1/非delete-pendingを確認し、子終了後もrootを保存まで保持する。
root/child/peer応答不明は後続を止め、同じ親/祖先の保持・worker80/81を維持。peer拒否を子作成拒否へ読み替えず、作成失敗に既知no-handle例外を流用しない。
payload write/delete/renameなし、成功fileは空のまま残す。同一token試験であり独立peer/tokenの隔離試験ではない。

fake接続/保存時の親保持/選択case/既存回帰/独立レビュー/実装savepointの後、新規clean namespace-readonly-20260915/banto-aiを作る。
batch namespace-readonly-2026-09-15、max1・最大root1/child1/peer4。HEAD/全input pin/単回claimとstdout/外側監視は既存方式を維持する。
内側40秒/1024点、外側45秒/500ms・96点、private256MiB/working384MiB、空きRAM/disk2GiB、出力384KiB。
旧namespace-create/diagnostic/directory-peer等のsource・枠を再open/列挙/hash/copy/deleteせず、旧記録のfileだけを照合する。
Windows Update engineering緩和/正式pin不変、OS build/bootと資源前後記録、Python3.14.0、account/service/runtime追加なし。

成功してもshare3との対照比較完了とは扱わない。親ADD_FILE handleが拒否される一方でpath作成が通れば、親share1保持だけで新規名前追加を防げない実例として記録する。
拒否なら、その単回同一token操作の拒否にとどめ、全操作・全actor・既取得権限・全期間不変へ一般化しない。
namespace_consistency=unresolved、全isolation/受入許可flags=false、acceptance_status=not_completedを維持する。
