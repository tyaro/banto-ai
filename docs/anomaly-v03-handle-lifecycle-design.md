# S4-B2 ハンドル所有終了と権限の接続設計

日付2026-09-11、基準e3317f9。tests/fixturesの注入backend部品と、未実装のnative接続案を区別する。
[rename設計](anomaly-v03-rename-adapter-design.md)を補い、既存B1/S3/D2の実行経路は変更しない。

## 今回実装した所有終了

tests/fixtures/anomaly_v03_handle_owner.pyのHandleOwnerは、構築時に最大32個の
検証済みfile handleのpinと親indexを受け取り、初回設計では終端のcloseを担当した。
2026-09-14拡張: [公開前の証跡保存と選択解放](anomaly-v03-prepublication-design.md)により、
同期borrowと3工程内の事前解放も追加した。以下の初回設計の実native取得・権限検証は引き続き未完了。
入力はtuple、同handle/同volume-file IDの重複は禁止。親は先行indexの同volume directoryに限定する。
循環やfileを親とする登録を拒否し、全管理slotの確保が終わって構築が正常に戻るまでcaller所有のまま。
pinの型検査は本物のhandleの有効性や所有権の証明ではない。実取得・移管のbackendは未実装。

CloseHandleが適するfile/directory handleだけを渡す契約である。
FindClose/LocalFree/RegCloseKey/socket/CRT descriptorや、別ownerが所有するhandleは対象外。
native側は非継承・非重複所有・DELETE_ON_CLOSEなし・delete dispositionなしを別途保証する必要がある。
closeがファイルの削除を引き起こさないことをpinのshapeだけで証明しない。

finishは終端操作で、公開途中なら先にjournalを停止させる。
全体を取得と逆順で閉じ、各子のcloseを親より先に一度だけ試みる。
あるcloseが失敗しても、残りの別handleについてcloseを試す。
ここで許可する後続処理は所有資源の解放だけで、rename/write/再検査/path削除を再開しない。
子がunknownでも残る親のcloseを試し、以降の公開操作を行わない。

[CloseHandle](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle)の
raw signed BOOLを受け取り、0の直後だけGetLastErrorを読む。成功確認時のみclosedとする。
不正return、エラー未取得、例外、閉鎖応答喪失はunknown。
未知のhandleは記録用のidentityを残すが、番号が再利用されうるため再close・reopen・借用を認めない。
二度目や再入のfinishも拒否し、backendが拒否を握り潰しても公開成功に戻さない。
destructorや自動retryは設けない。

primaryがあれば同じ元例外を再送出し、closeや記録の二次障害で置換しない。
後発のMemoryError/既知資源WinErrorはresource_stopを昇格し、journalの既存資源停止も継承する。
分類器自体が失敗した場合も資源停止として残りのcloseを試みる。
journalのteardown記録と、その失敗を止めるstopの両方が壊れた場合も元例外を保持する。
この場合ownerのjournal_finalizationはunknownになる。壊れたjournalにcompleteが残っていても、
例外とownerのunknownを無視して成功にしない。

owner_status=finishedはこのclose巡回が終了した意味で、全close成功や公開受入ではない。
all_closes_confirmedと各slotのstate、journal_finalizationを別に確認する。
snapshotはslot/親/state/整数errorだけで、handle番号・path・例外本文を出さない。
単一threadのtrusted状態であり、無制限OOM下の記録保証、同時呼出やhostile private-field改変への保証はない。
全記録はnot_completed/formal_permissionfalse/execution_authenticatedfalseを維持する。

## nativeで取得する権限と寿命の案

次表は実装済み権限や受入の表ではなく、次のbackend設計レビューで確定する要求候補である。
新規private fixture rootだけを操作対象にする。repository/artifacts等の既存祖先は保持・観測のみでDACLを変えない。
取得前に全slot数・親子関係・固定相対pathを計算し、32を超えたら取得を始めない案とする。

| 対象 | 取得時の権限候補・共有条件 | 使用と解放の境界 |
| --- | --- | --- |
| 既存祖先directory | LIST_DIRECTORY / READ_ATTRIBUTES / READ_CONTROL、share READ+WRITE、DELETE共有なし | identityを保持し、最後に解放。ancestorのACL変更なし |
| 新規fixture root | 上記にTRAVERSE / ADD_FILE / ADD_SUBDIRECTORY / WRITE_DAC。DELETE共有なし | 子を作成し、普通の新規mutationを拒否するDACLを固定。保持親で最終名を解決できるか実証が必要 |
| payload/markerのwriter | GENERIC_READ / GENERIC_WRITE、非継承、shareなし、fileはCREATE_NEW | write完了→flush→内容照合→writer close。close未確認なら後続のseal/renameを止める |
| payloadのfile/directory検査用 | READ_DATAまたはLIST_DIRECTORY / READ_ATTRIBUTES / READ_CONTROL / WRITE_DAC、share READのみ | writer解放後にidentity/hashを照合し、DACLを固定・読戻し。子handleを解放してからdirectory renameする案 |
| stage directoryのrename用 | LIST_DIRECTORY / READ_ATTRIBUTES / READ_CONTROL / WRITE_DAC / DELETE、DELETE共有なし | 元directoryの同一handleをpayload renameへ渡す。検査用の同identity handleを重複所有しない |
| markerのrename用 | READ_DATA / READ_ATTRIBUTES / READ_CONTROL / WRITE_DAC / DELETE、DELETE共有なし | writer解放後にpinを作り、marker bytes/DACLを検証。保持した同handleから最後に.completeへrename |

各権利の意味は[File Access Rights Constants](https://learn.microsoft.com/en-us/windows/win32/fileio/file-access-rights-constants)、
共有条件とdirectory取得方法は[CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)を参照。
share条件は既存handleとの相互互換性も必要で、単に新handleへshare READを設定して成功を仮定しない。
既存_Bound既定のaccess=0x20081/share=3をrenameへそのまま流用しない。
DELETEなしのhandleからrenameしたり、DACL固定後に必要な書込み権限を名前経由で取り直す前提を置かない。
RootDirectoryへ渡す親handleの権利だけで、保護後の名前追加が可能かは未確認。実APIで拒否されたら停止する。

[FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)は
GENERIC_WRITEを持つfile handleで行う。このためwriterを閉じる前の準備工程に置き、
read-only検査handleや公開後の追加flushへ責務を移さない。
closeだけをflush成功の代わりにしない。file内容のflushとdirectory renameの電源断耐久性は別であり、
本設計は後者を保証しない。volume全体のflushや管理者権限の追加は予定しない。

DACL固定前に得たwriter/DELETE/WRITE_DAC等の権限を、DACL変更で取り消せたとは扱わない。
writerを先に閉じ、独立した通常tokenによるwrite/add/delete拒否と、保持rename handleによる
意図したcommitをそれぞれ実検証する。意図的にDACLを変えるownerや特権者へのsandbox保証はしない。
子の検査handleを閉じる前に全identity/bytes/SDをprivate証跡へ固定し、directory rename後のverify_finalでは
保持rootからの名前と元identityを改めて照合する案。選択解放の部品は2026-09-14に追加したが、実nativeへの接続は未実装。

## private証跡と実機接続の残件

marker-pending名の消失後も必要なmarker bytes、payloadの固定inventory/raw hashes、SD、pin、工程状態を
公開先外の新規private証跡に保持する。通常の成功・故障注入の両方で回収できるよう準備中に保存する案。
上限は既存modelのpayload8 files/各64KiB/合計256KiB、marker16KiB、handle32の小fixtureから始める。
これは実機試行の承認やprocess全体の資源上限ではない。time/private bytes/空きRAM/空きdisk等の
監視上限、書込証跡の予算と保存の失敗時方針をnative試行仕様で別途確定する。

[後続の取得追跡・実観測接続](anomaly-v03-observed-evidence-design.md)で、raw取得追跡、取得済み3 slotsの一括管理移管、
祖先保持、実identity/private SD/bytesからprepare証跡を保存して子を解放する範囲を限定実機で確認した。
[reader再取得](anomaly-v03-reader-reacquisition-design.md)ではwriter解放後の一時読取り世代を親borrow内で検査・終了した。
[file権限固定](anomaly-v03-file-sealing-design.md)でWRITE_DAC/marker DELETEを取得し、2 filesのfrozen DACL読戻しと
親borrow内のlive continuation・全終了を限定実機確認した。stage/root directoryの権限・固定・相対rename、
動的slot追加、API外/thread間の排他、ADS等の全検査、実故障受入は残る。
未知closeは再試行せず、限定worker終了による資源回収と終了確認をnative試行仕様へ含める。
今回のHandleOwnerに安全なfixture削除機能があるとは扱わない。
B1の終了済み試行枠を再開しない。native実行範囲を具体化・レビューしてから次の試行へ進む。
