# S4-B2 局所directory取得driverの実装と実機確認

2026-09-14、基準982c1318。実装savepoint **3a719347e736e7770036b6b7882f0f4614774424**。
ユーザーの自走・セーブポイント作成許可を受け、[局所driverの設計](../anomaly-v03-directory-driver-design.md)を実装・レビューし、
別のclean checkoutから新規枠directory-driver-2026-09-14のattempt-1を1回実行した。

**240件pass/0.210秒、実機の局所取得はpass/0.540秒、worker exit0を確認**。
CreateDirectory2Wによる新規root取得、元handleのID/実権限/SD検査、取得証跡保存、同handle再確認、終了まで通った。
新規rootだけのengineering確認で、namespace隔離・全publisher・正式受入は未完了。全acceptance/isolation flagsはfalse/not_completed。
今回の最大1回枠は成功をもって閉鎖し、再実行・旧batch再開・sourceのclose後検査は行わない。

## 実装・模擬故障

callerがdriver/contextを接続前から保持し、evidence sinkの全ancestor leaseをsourceのparentsとexact照合する。
祖先の元ID/type/pathとowner/group/DACL/mandatory labelの自己相対SDを比較し、作成・観測・保存の境界で差を検出する。
既存ancestorは継承ACLを持てるため、新規private root専用のsecurity()を適用せず、読取り専用の有界SD比較を追加した。
既知SDはLocalFreeを1回、不明応答時は再query/freeせずancestorを保持して専用worker終了へ進む。

前回取得部品のfake APIはdescriptorを整数で返していたが、実際の既存APIはctypes.c_void_p cellを返す。
元cellを保持しアドレスを検証するよう修正し、既存fakeも実際と同じ型へ合わせた。SA/5引数/CreateDirectory2Wの仕様変更はない。

新規driver19件と既存221件を合わせ240件。failure/error/skip/expected failure/unexpected successは全て0。
保存→同handle再確認→source close/free→祖先closeの順序、衝突時の非接触、取得/close/free応答喪失、元例外維持、
後発資源停止、callback再入、不正応答、祖先ID/SD変更、SD複写/解放故障、誤ったancestor chainを確認した。
最初の記録は238件pass/0.212秒。独立レビューのP2=2を修正し、2件追加した修正後記録を最終根拠とする。

独立所見は「既知resource stop後も後続IOへ進める」と「finishだけで未実行をpassにできる」の2件。
入口・guard前後でresource stopを取り込み、成功条件にrun/保存/再確認/終了を要求した。
事前資源停止では接続もせず、callbackで停止が分かった後は終了処理だけになることを確認した。
修正差分・実機入口・監視・設計の再レビュー残件P0〜P3=0。read-only、進捗ポーリングなし。

## 実機結果

clean detached checkoutはC:\Users\TKent\.codex\worktrees\directory-driver-20260914\banto-ai。
取得/試験/入口/監視/設計等39 sourceのraw・Git blob・checkout一致を実行前後で確認した。
launch-plan.jsonは8157 bytes/hash0002fe3d6504bd710a6f082693f89c593b4c9d9ec11a2ae6638a254f8beda185。
既存C:\Python314\python.exeを-I -Bで実行し、追加runtime/account/serviceは作っていない。

| 項目 | 観測 |
| --- | --- |
| 開始/終了UTC | 12:07:48.6954047 / 12:07:49.2453203 |
| supervisor | 0.540秒、exit0、worker終了確認、stop reasonなし |
| root | CreateDirectory2W返却確認、実権限0x1600a7、元handle観測/再確認pass |
| ancestors | 10個の元ID/SD比較、SD query buffer最終freed |
| prepare.json | 1990 bytes、hashbf8747dc4c809dd8ba06152f38ae7de82fb93d42d2dea2057b0f5f7fe8e9790d、saved |
| 終了台帳 | rootを含む13 handlesとquery token1本は全てclosed、入力descriptorはfreed |
| 出力 | stdout9547 bytes、stderr0 bytes |
| worker資源 | 内部23点、最後の観測0.095秒。観測private最大20,975,616 bytes、working最大29,458,432 bytes |
| OS報告のworking peak | 35,790,848 bytes。外側1秒周期より早く終了したため外側process memory観測は0点 |

private-evidenceの既知prepare.jsonだけを成功後に読み取り、worker記録とsize/hashを照合した。
source-fixtureはclose後に列挙/open/hash/copy/deleteしない。子・payload・marker・rename操作は追加していない。
「作成後の子が空」というpostclose検査や、別actorが変更できない証明はこの結果に含めない。
既存private sinkのcreate/bind信頼制約を継承し、その保存成功を保護publisherの隔離根拠にはしない。

## 保存・残る条件

ignored artifacts/directory-driver-2026-09-14/に14 artifacts、論理478167 bytesを保存。manifest自身と別checkoutの複製はこの合計に含めない。
corrected-checks.jsonl176164 bytes/hashb976b48bcb43636f82ba20fb38faaee8413b95056165d021ab86a7060ba05fd3。
savepoint-evidence.json13060 bytes/hash94cee204de69aa67acb2444b8489a1fed200128eb08b6eccd0c6f9c139666f2e。
前回manifest/10 artifacts不変、前回34 source中32不変、上記descriptor修正2 filesだけ変更。repository safety/差分空白検査pass。

UTC12:05:46の空きRAM15.02GiB/C118.06GiB/D60.12GiB、12:09:03はRAM14.77GiB/C118.05GiB/D60.12GiB。
開始時点11:50:53のRAM13.94GiB/C118.06GiB/D62.78GiBからD空きは減少しているが、変動原因は未特定。
試験固有の記録量とPC全体の空き変動を混同せず、点観測から長期リーク不在を断定しない。他processへ介入なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。Windows Updateのengineering条件緩和を継続し、正式pinは変更しない。
今回のworker/監視は終了し、常駐処理なし。新規detached checkout1個と今回fixtureは保存して残す。

既存親policy結果書の8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3はcleanのまま不変。push/merge/CI、旧B1/失敗source/S3/D2/production、別projectへの操作なし。
次はprivate期間中のpeerのADD_FILE/ADD_SUBDIRECTORY/DELETE_CHILD取得と操作を分けて検証する仕様へ進む。
外側parentの事前権限、handle移管、consumerの共通観測期間、親全保護・marker/全publisher・独立token/競合、正式OS/VM digestは未完了。
取得成功だけでisolation_certified/protected_commit_allowedをtrueにせず、native publisherは開始しない。
