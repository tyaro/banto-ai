# S4-B2 単一呼出しのdirectory取得部品

2026-09-14、基準46b8d35。[隔離条件の設計](anomaly-v03-isolation-basis-design.md)に対応するtests/fixturesの独立部品。
DirectoryAcquisitionとWindowsDirectoryBackendを追加し、既存private sink・6工程・publisher・productionへは接続しない。
今回の確認はfake APIによる取得/観測/終了故障に限定する。実機entry・監視script・試行枠は作らない。

## 取得と終了の契約

callerは部品をacquire前に保持し、全ancestorをfinishまで保持・検査するguardを渡す。
この部品自身はancestorの所有やpathとの結合を証明しない。将来のnative driverで具体化する前提である。
acquireは1回だけ。全引数の準備後、予約済みTrackedOpenへ返却handleを記録してから観測を始める。
成功時のObservationは同じhandleの履歴であり、handleはfinishまで部品が所有する。所有移管・子作成・renameのAPIはない。
callerは返却喪失時も保持した部品のfinishを呼べる。finish前にancestorを解放しない。

| 境界 | 固定する処理 |
| --- | --- |
| prepare | API解決/ABI確認、既存private SDDLからdescriptor作成、SECURITY_ATTRIBUTESと引数tuple準備 |
| create | CreateDirectory2Wを5引数で1回。原handleを検査前にTrackedOpenへ格納 |
| access | 同じhandleのNtQueryObjectでGrantedAccessを照会、0x1600a7 exact一致を要求 |
| inspect | 同じhandleのID/type/path/local NTFS/非継承、private SD、前後ID一致を確認 |
| finish | 記録されたdirectory handleのCloseHandleを1回。続いて安全に解放できるdescriptorのLocalFreeを1回 |

要求はroot0x1600a7/share READ=1/redirect拒否=1/非継承、非NULLの既存private SDに固定。
Win64 HANDLE、DWORD/enum32、SA24 bytes・descriptor offset8・inherit offset16を照合する。
API引数は前回確認したSDKの5引数宣言を使い、6引数の文書例へ従わない。0/NULL/-1/INVALID_HANDLE_VALUEは成功にしない。
API失敗のerror codeが得られない場合も停止。衝突や失敗を「何も作成されなかった」証明にしない。
pathはlocal drive absolute、最大240文字/16成分、dot traversal/ADS/device名等を拒否する限定形とし、環境全体を走査しない。

## 同じhandleの観測

既存_Bound.check()は名前から再openするため使わず、_Bound.observe()だけを借用する。
これは明示的なpath再openをこの部品で行わないという意味であり、OS内部の名前解決を排除する主張ではない。
観測ごとにcaller guardを検査し、ID/type等とprivate SDを同じhandleから読む。識別情報の前後差や余分な権限で停止する。
記述子は最大2048 bytesの正規化JSON。新規directoryの原IDは返却handleから得るもので、外部pinとの事前一致ではない。
子inventory、directory stream、peer権限、外側parentの保護はこの部品では検証していない。

## 故障と不明所有

prepare・create・inspectの再入や、途中guardで停止を握り潰しても後続へ進ませない。
最初の例外objectを保持し、後発MemoryError等はresource stopへ昇格する。finish内の再入も停止として記録する。
検査前に記録済みのhandleは検査失敗時にもcloseを1回試す。close応答喪失後は数値が再利用され得るため再closeしない。
close失敗があっても既知のdescriptorの解放を試し、primaryを置き換えない。

作成呼出し後、返却/handle記録を確認できなければ、実directoryとhandleの所有はunknown。
入力descriptorはretained_unknownとして保持し、まだ参照される可能性を除かずworker終了を必要とする。
descriptor割当の応答喪失はunavailable、LocalFreeの返却喪失はfree_unknownであり、どちらも再取得/再freeしない。
呼出し前に記録できたdescriptorなら、引数準備の失敗時にも1回解放する。
Pythonへの返却値変換・代入までを無制限OOM/割込みに対して割当て不要にはできない。通常snapshotの割当て成功も保証しない。
callerは部品/backendを到達可能に保ち、所有unknown時のworker終了と資源停止後の固定通知を将来driverで実装する必要がある。

## 受入境界と次の実機仕様

fake APIの正常・失敗は実WindowsでのAPI成功、共有制限やnamespace隔離の証明ではない。
全snapshotでisolation_certified/protected_commit_allowed/formal_permission/execution_authenticated=false、acceptance_status=not_completed。
rootのprivate期間、既取得ADD/DELETE_CHILD、外側parent、handle移管、consumer一貫性の未解決条件を維持する。

次はこの部品だけを新規fixtureに適用する局所driverを設計する。既存祖先の元ID/SD/寿命との結合と、
停止・所有unknown時のworker終了、source/evidence保存順序、衝突時の既存object非接触を具体化して独立レビューする。
pure/fault、source固定、監視と資源上限をそろえてから別の実機枠を固定する。今回の変更から自動実行しない。
局所取得に成功してもpeer経路が未解決ならnative publisherへ進めず、旧batch/失敗source/S3/D2を操作しない。

## 後続の局所driver

3a71934で[局所driver](anomaly-v03-directory-driver-design.md)を追加し、祖先結合・保存・終了・監視を具体化した。
既存APIのdescriptor返却がctypes.c_void_p cellである点を取得部品/fakeへ反映した。
[240件passと新規max1の実機取得pass](results/anomaly-multiseed-v0.3-s4-b2-directory-driver-2026-09-14.md)、独立残件0。
この後続試行枠は閉鎖済み。元の部品単体の試験はfakeのみという履歴を維持し、局所取得成功から隔離認定は行わない。
