# S4-B2 ハンドル所有終了・権限接続設計の検証結果

日付2026-09-11。基準e3317f9b5fb7b0202664af00ef2c0cadcedef0ea。
実装savepoint **8f96f3d12b9ec2d2ec01460a28d9730b0ab80bc1**。

**最大32個の所有handleの終端解放を模擬backendで実装し、最終52 testsがpass。**
初回独立レビューのP2を修正し、再レビューの新規P0〜P3は0件。
[設計書](../anomaly-v03-handle-lifecycle-design.md)にnative接続時の権限と寿命の候補をまとめた。
native handleの取得・ACL変更・flush・公開操作は今回実行していない。

## 実装した境界

tests/fixtures/anomaly_v03_handle_owner.pyは既存のjournalとrename部品を補う。
親indexが先にある固定tupleを検証し、管理slotの確保と構築成功後に所有を引き受ける。
取得backendは別途必要であり、pinの型だけで実所有を証明しない。

- 各handleを子から親の逆順で一度だけ閉じる。
- close失敗後も残りの別handleの解放を試し、公開操作やpath削除は再開しない。
- 応答喪失はunknown。同じ数字が別handleへ再利用されても再closeしない。
- 元のprimary例外を保持し、後発の資源不足はresource_stopを昇格する。
- 元の公開停止やcommit confirmedを解放成功で消さない。
- 二重finish、再入の握り潰し、型不正、循環・重複登録を拒否する。
- 記録自体の二重故障ではjournal_finalization=unknownを残し、元例外を再送出する。

snapshotはslot/親/state/errorの限定情報で、handle値・path・例外本文を出さない。
owner_status=finishedは巡回終了を意味し、全close成功や公開受入ではない。
解放応答不明時の実資源回収は限定workerの終了確認を含むnative設計が必要。
単一threadのtrusted部品であり、無制限OOM、同時操作、借用排他の保証ではない。

## 検証・レビュー

新規17＋既存rename18＋model16＝51件は0.043秒でpass。
独立レビューで、finish_teardown失敗後の最後のstopも失敗すると元のprimaryを置き換えるP2を検出した。
最後のstopも捕捉してownerに記録し、元例外へ戻す修正を行った。
追加の1 methodはprimary有無×記録前後の4 casesで、二次stopのMemoryErrorを注入した。
**最終は新規18＋既存34＝52件、0.052秒、failure/error/skip/expected failure/unexpected success0。**

close各位置、error取得例外、raw BOOL/errorの不正、資源WinError、例外chain/group、
classifier失敗、開始時snapshot失敗、teardown記録前後の異常も含む。
前回のrename部品と実際に接続し、正常commitと応答喪失の両方でhandleを解放した。
これはメモリ内のhandle/name表の操作で、実Win32での解放・公開成功ではない。

記録失敗後にraw journalへcompleteが残る反例も試験した。
例外およびownerのunknownを無視してraw journalだけで成功判定しないことが呼出側の契約である。
再レビューは修正と設計書を確認し残件0。担当の実行/native/ネット/編集なし、進捗ポーリングなし。
repository safety / staged diff-check pass。最終試験の6 source filesは確定commitのGit blobとraw bytes一致。

ローカルCPython3.14.0の選抜試験のみ。旧Linux CIやWindows全受入の件数へ加算しない。
src/科学config/schema/registry/正式OS pinは不変。全記録not_completed/formal_permissionfalse/execution_authenticatedfalse。

## 保存記録と資源

新規ignored root artifacts/handle-owner-2026-09-11/に初回と最終を分けて保存した。

| 記録 | bytes | SHA-256 |
| --- | ---: | --- |
| initial-checks.jsonl | 36210 | a1733dcbc3ad590884da6e53c706c39a39f81df3950b646701f7c4d47a7eec18 |
| final-checks.jsonl | 36939 | 936eb7df0034d0935581306856d1eec562f54260e1d38e6311d438710071d9bb |
| resources-final.json | 444 | fb000cf05697fa1582d4e43bc7ebb8d555dc6ac06c6c0e5d83987f3adc8161f4 |

各JSONLは実test IDs/結果と実行時raw source hash、基準revision、Python版を含む。
savepoint-evidence.jsonに実装commit、raw/Git blob照合、レビュー修正と再検証理由、開始資源を保存した。

開始UTC11:00:16Z RAM空き5.52GiB/C103.02GiB/D75.20GiB。
最終11:09:53Z RAM5.49GiB/C103.02GiB/D75.20GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。
開始前から前回よりRAM/diskの空きが減っていた。原因は調べず本作業やリークへ帰属させない。
今回の短い試験・記録processは終了し、常駐処理なし。別project、旧failure fixture、共有runtimeへの操作なし。

本流889cfc3は変更なし。候補へローカル保存し、push/merge/CI起動、新runtime導入は行っていない。

## 次の作業

設計書にwriterのwrite→flush→照合→close、検査/権限固定用の取得、
子handleの事前解放、stage/markerの保持DELETE handle、private証跡の順序を具体化した。
権限/share条件は候補であり、保護後の保持親による相対renameの成功は未確認。

次は取得途中の失敗を含む所有移管、writer/子handleの事前解放とその後の操作禁止、
private証跡の保存予算を実装して、native試行の範囲・上限をレビュー可能にする。
今回の終端ownerはその事前解放やfixture清掃を実装していない。
B1終了済み試行枠の流用なし。native全受入、正式OS整合、VM image digest、
runtime closure/consumer凍結、S4受入は引き続き未完了。
