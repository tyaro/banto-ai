# S4-B2 private rootの同一token peer権限取得

2026-09-14、基準8290039。実装savepoint **13ad057c2662cd0bf67a19853602c43eeac7d42e**。
[peer取得仕様](../anomaly-v03-directory-peer-design.md)を実装・レビューし、新規max1枠directory-peer-2026-09-14で1回確認した。
**FILE_ADD_FILE/FILE_ADD_SUBDIRECTORYは共有違反で拒否されたが、FILE_DELETE_CHILDを含む別handleは取得できた。**
原rootをshare READで保持しても、この条件ではpeerの全変更権限を排除できない。実際の子作成・削除・renameはまだ検証していない。

同じprocessの同じprimary tokenによる4件のOPEN_EXISTINGであり、独立process/tokenや競合の試験ではない。
行列・保存・再確認・終了は完了、worker exit0/0.966秒。新規最大1回の枠は閉鎖した。
259件pass/0.263秒、独立P0〜P3=0。全isolation/protected commit/formal permission/execution authenticated flagsはfalse、正式B2/S4受入は未完了。

## 実機の権限別結果

原rootはCreateDirectory2W、requested/GrantedAccess0x1600a7 exact、share READ=1、redirect拒否、private SD、非継承。
rootの元handleを保持したまま、peerはshare7/OPEN_EXISTING/非継承で順に要求した。
各maskにREAD_ATTRIBUTES/READ_CONTROL/SYNCHRONIZEを加え、取得できたhandleでは元rootとのID/type/SD一致も確認した。

| ケース | requested | observed GrantedAccess | 結果 | 終了 |
| --- | --- | --- | --- | --- |
| LIST_DIRECTORY control | 0x120081 | 0x120081 | granted | closed |
| ADD_FILE | 0x120082 | 取得なし | denied、WinError32 | known no-handle denial |
| ADD_SUBDIRECTORY | 0x120084 | 取得なし | denied、WinError32 | known no-handle denial |
| DELETE_CHILD | 0x1200c0 | 0x1200c0 | granted | closed |

denied2件のTrackedOpenは元のunknown/unavailable履歴を維持するが、直後のINVALID_HANDLE_VALUE＋32が確認された非作成openなので、
peer専用のknown_no_handle_denialに分類した。これは作成失敗・返却不明を無作用と扱う規則ではない。
同じ要求を再試行せず、正常peer2本を証跡保存前にcloseした。sourceの原handleは保存後も再確認してからclose/freeした。

開始tokenはprimary type1/非昇格/medium integrity、enabled privilegesはSeChangeNotifyPrivilegeのみ。
SeBackup/SeRestoreは有効でない。query権限だけで開始profileを読み、tokenを変更/生成せずquery handleをcloseした。
期間中の外部token変更、異なるactor/token、明示的handle移管を完全に監査した結果ではない。

## 実装・故障確認

4個のpeer slotを最初のopen前に予約する。原root保持/ancestor guard/ID・SD一致/実権限exact一致を確認し、各peerを次のケース前にcloseする。
0/NULL/異常返却、文書化された拒否以外のerror、open/close応答不明、control拒否、観測差で行列を停止する。
不明peerが残る場合はroot/input descriptor/祖先も保持して専用worker終了へ進み、原rootを先に閉じない。
既知peerの検査失敗はそのpeerを閉じ、原root/祖先を通常終了する。最初の例外と後発resource stop、再入拒否を維持する。
基底driverの観測点上限をclass定数にし、既定64を維持。新規peer contextだけ96点に拡大し、時間/メモリ/空き容量の制限は変更しない。

新規19＋既存240＝259件pass/0.263秒、failure/error/skip/expected failure/unexpected successは全て0。
混合行列・全granted・変更用全denied・control拒否、権限/ID/SD差、不明返却、error採取順、close応答喪失、
元例外維持/後発MemoryError、callback再入、原root/祖先の保持、初期token制約/close故障を模擬試験で確認した。
独立レビューは実装/試験/入口/監視、続いて設計をread-onlyで照合。新規P0〜P3=0、進捗ポーリングなし。
repository safety/PowerShell構文/差分空白検査pass。レビュー後のcode変更・重複回帰実行なし。

## 実行・証跡・資源

clean detached checkoutはC:\Users\TKent\.codex\worktrees\directory-peer-20260914\banto-ai、HEAD13ad057。
44 sourceのraw/Git blob/両checkout一致を実行前後で確認した。
launch-plan.json9342 bytes/hash915a531ac2efe7b7feca0cc02af832ff4fe92827b8c20321fc94f1d234d8f77b。
既存C:\Python314\python.exe、3.14.0 exact、-I -Bを使用。追加install/常駐監視なし。

| 観測 | 値 |
| --- | --- |
| UTC開始/終了 | 12:38:18.4199669 / 12:38:19.3984811 |
| 外側監視 | 0.966秒、worker終了確認/exit0、停止理由なし |
| 原root/祖先 | 同handle取得/再確認pass、祖先10、入力descriptor/祖先SDはfreed |
| 終了台帳 | 実handle15本とquery token1本closed、別にknown no-handle denial2件 |
| prepare.json | 2464 bytes/hash2abd9c1f50acdf20ba77c46535ea6bca98cb237f2edd4afe1f695be65b1f7796 |
| stdout/stderr | 16854 / 0 bytes |
| 内部資源点 | 50点、最後0.433秒、観測private最大21299200/working29822976 bytes |
| OS報告working peak | 36167680 bytes。外側1秒周期の前に終了したため外側memory観測0点 |

成功した既知prepareのbytes/hashと行列/token情報をworker報告と照合した。
sourceの名前からの再openはpeer用4件だけで、原root保持中に限る。sourceをclose後/失敗後に列挙・open・hash/copy/deleteしない。
ignored artifacts/directory-peer-2026-09-14/へ12 artifacts/論理285363 bytes（manifest自身/別checkout複製を除く）。
initial-checks.jsonl190058 bytes/hash056fc8104a090291899f9fa0d3e12bfdecdb20791ddbcef34a09b5961200e4fa。
savepoint-evidence.json16763 bytes/hashb3f9b558e9700c583a657a85dd14d22c5375e9401d9c73f16a956a07162e26ce。
前回manifest/14 artifacts不変、前回39 source中38不変。変更は基底driverの観測点定数化だけ。

UTC12:29:28の空きRAM13.92GiB/C117.76GiB/D57.85GiB、12:41:01はRAM13.77GiB/C117.52GiB/D56.81GiB。
PC全体の空き変動の原因は未特定。試験固有の保存量とは分け、点観測を長期リーク不在や全期間最大の証明にはしない。他processへ操作なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Update engineering緩和/正式pin不変。
worker/監視は終了済み、新規detached checkout1個とfixtureを保存して残す。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommit対象から除外。
本流889cfc3はclean不変。旧batch/旧source/S3/D2/production、push/merge/CI、別project、新account/service/runtimeへ操作なし。

## 次に切り分ける操作

次は新規fixtureで、子自身のDELETE許可、親のDELETE_CHILD、子のDELETE共有を分け、削除操作の成否を調べる仕様を具体化する。
DeleteFileWの説明ではfile側DELETEまたはparent側DELETE_CHILDが条件となり、既存file handleのDELETE共有も影響する。
[DeleteFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-deletefilew)。
そのため単にprivate childを削除できても、今回取得したparent handleの権限を使えたとは断定できない。
path指定APIが呼出し時に再評価する権限と、保持parent handleが直接使用されるAPIを分けて設計する必要がある。
これは次の仕様の論点であり、削除試験/新規枠の開始ではない。今回のsourceと最大1回枠は再利用しない。
外側parentの事前権限、private期間/子内部open、handle移管、consumer共通観測期間、親全保護・marker/全publisher、正式OS/VM digestは未完了。
