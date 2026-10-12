# S4-B2 保持handle内の有界読取部品

2026-09-14、基準4976bb3。[保持期間model](anomaly-v03-retention-window-design.md)で整理した共通期間を、
既存SealedFilesのcontinuation内での実読取adapterへ接続する。今回はfake APIで検証し、新規native枠を開始しない。
追加はtests/fixtures/anomaly_v03_held_consumer.pyと試験のみ。既存の所有者・native入口・publisher gateを変更しない。

## 部品の境界

HeldConsumerをSealedFilesの開始前に作り、外部の元root Observation、source revision、既存plans/marker pin、資源guardを固定する。
rootのpinは元owner slotと一致必須。markerはsource revisionと全payloadから既存modelで再構築し、元journalのSHAとexact一致を要求する。
runは既存seal_and_useを1回呼ぶ。全子のfrozen SD読戻し完了後、元rootのborrow内で収集する。
collector自体には新規open/close/DACL変更/名前列挙/rename/marker write/handle移管を行う機能を持たせない。
既存SealedFilesの準備処理が行うopen・seal・path照合と、今回のconsumer内の直接読取を区別する。

外部へ返すのは収集statusとbytes/hash等のmetadataだけ。生の収集bytesはprivateな証拠として保持し、consumer_payloadは常にisolation_unresolvedで拒否する。
この部品にtest仮定で返却を許可するswitchは設けない。親/祖先namespace・全inventory・descriptor/保持者の権限行使までの一貫性根拠は未実装。
実読取部品を作ることと、全payloadを一貫したconsumer結果として返せることは別である。

## 保持中の照合順序

1. 元rootと全子のlease、view、pin、元plansのbindingを固定。全子はready、close未開始、custodian移管なし、seal verifiedが必要。
2. 元rootのsame-handle metadataを外部pin/descriptorと比較する。
3. 全子のsame-handle ID/type/descriptor/長さと実アクセス権を、sealed Observation/planと照合してから最初のreadを行う。
4. 各子を元handleで1回ずつ有界readし、型bytes・長さ・raw bytes・SHAを確認する。確認したactual bytes自体を保存する。
5. 全子のmetadata/実権限と元rootをもう一度照合する。読み終えた子もこの最終照合まで保持する。
6. callbackを返し、既存SealedFilesが全子をcloseする。すべてのclose応答と最後の資源guardが確認できた場合だけ収集complete。

guardは最初の失敗、資源停止、root borrow、全子の生存とview/plan/pinの差替えを確認する。最大512回。
新componentの再入をcallbackが握りつぶしても失敗をラッチして後続readを止める。
後から別の子やrootが変われば、先に読めたbytesも全体の候補から破棄する。成功後のcloseや最後のguard失敗も同様。
最終guardが正常に戻っても、generation/owner/journalに記録された停止・最初の例外・resourceを終了時に取り込み、失敗を伝播して候補bytesを破棄する。
既知のowner/generationの最初の例外とresourceをjournal snapshotより先に確保し、snapshotの二次障害で元の例外を隠さない。
前後一致だけでABA/全期間不変・namespace一覧の正しさを証明したとは扱わない。

## 同期Win32 backend

既存WindowsSealBackendがOPEN_REPARSE_POINT/非OVERLAPPED・share READで取得した、通常のlocal NTFS fileを前提にするtrusted adapter。
任意のdevice/pipe/asynchronous handleは対象としない。新しいDLL読み込みやbinding変更はなく、既存API instanceを借りる。
metadataは_Bound.observeとGetFileInformationByHandleEx、securityを使う。_Bound.check/readはpathを開き直すため呼ばない。
_Bound.observeの最終path/volume照会は元handleとdrive情報の確認であり、fileを名前からopenする操作ではない。

FILE_STANDARD_INFOはsize24、BOOLEAN offsets20/21。fileはdirectory=false、DeletePending=false、links1、0〜64KiBの長さ、allocation>=lengthを要求する。
[FILE_STANDARD_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_standard_info)。
単回の同期[ReadFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-readfile)を使い、
[SetFilePointerEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfilepointerex)で先頭へ移動してから期待長N+1 bytesを要求する。
返却はexact Nだけを許可し、短いread、余分bytes、異常count/BOOL、エラーを再試行しない。空fileでも1 byteを要求し、0 byteの成功応答を検査する。
file pointerは消費されるが、失敗後の追加seekによる復元は行わない。これはborrow中の排他的な同期利用の前提である。

N+1 bufferとDWORD countは開始前に各file分を確保し、最大8 files/64KiB各、既存plan総量256KiB、marker16KiBの上限を継承する。
seek前に単回attemptを消費し、seek失敗も再利用しない。返却bufferは同期read完了後だけ参照する。async/cancel/retry経路はない。
外部の資源guardを各境界で呼ぶが、native呼出し自体を中断する機構はない。将来の実機driverには従来同様の外側時間/メモリ監視が必要。

## 失敗・所有と未実装事項

最初の例外を保ち、後発MemoryError等はresource stopへ昇格する。resource停止時に通常snapshotの割当が成功するとは保証しない。
readerはhandleの所有権を取得せず、同期read失敗後のcloseは元SealedFilesが行う。既知closeを再試行しない。
子closeが不明ならrequires_exit=true。将来のcallerは元root/関連祖先を保持して専用worker終了へ進む必要がある。この新driver接続は未実装。
元rootの最終closeはcallerの担当。実行前guard失敗ではSealedFilesを開始せず、既存の元root所有も移さない。
既存security等の内部割当・cleanup全体や既存driverの完全なOOM耐性を認定する部品ではない。

今回は直接readのfake API/所有故障確認まで。新実機fixture、path再取得consumer、完了印の公開、独立process/token、競合、全inventoryの共通観測期間は未検証。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completedを維持する。
