# Principal worker lifecycle model / read-only launch capability

2026-09-16 JST。準備済みj、P SID末尾1010/disabledを維持する次段階。
この変更はOSを呼ばないprotocol modelと、通常Uのtoken/linked tokenをQUERYする診断だけ。
setup実装と消費済みguard、保護root、SAM、資格情報を操作しない。

## Modelの契約

`tests/fixtures/PrincipalWorkerLifecycle.cs` は一度だけ `Begin` → `Complete` を受け取る純粋な状態機械。
native backendは存在せず、`NativeLaunchAuthorized` と `IsolationCertified` は常にfalse。
`ModelSucceeded` は仮定した応答の順序が完了したことだけ。native実行/認証/分離を証明しない。

各操作の `Confirmed` は下表の全postcondition、`NoEffectFailure` は副作用がないと証明された失敗。
状態機械は構築時に記録領域を全確保する。操作履歴は固定bitset、後発障害は固定配列で、通常のBegin/Complete/Needed経路に動的割当てを置かない。
例外、応答喪失、部分取得は `Unknown` として報告する。Beginでenable/launchの可能性を先に記録し、応答待ち中は次操作/再試行/成功を拒否する。
各Resourceは実handleではなくscope全体の記号。scopeの部分取得はUnknownであり、実adapterでhandleごとの所有台帳へ精密化する必要がある。

| 操作 | 将来adapterがConfirmedを返すために必要な条件 |
| --- | --- |
| Preflight | 固定P無効/SID/group、必要privilege、初期process/thread/token SD、U危険権限拒否、起動API、code/runtime、desktop/env/IPC/handle継承、制限値、原子的job参加の仕様が全て確定・検証済み |
| HoldAncestors / HoldCode | 固定した祖先/root、code/runtimeの全scopeを取得・照合・非継承で所有。順序と個別handle台帳をnative実装で別途固定 |
| PrepareIpc / CreateJob | 保護された有界IPCだけを明示継承。Bだけが非継承のkill-on-close job handleを保有、P/U計2・子孫生成禁止等の制約を設置 |
| AllocateSecret / ResetDisabledAccount | unmanaged専用secret bufferの所有、無効の固定Pにpasswordだけ設定。managed string/command/logへ出さない。未知のbufferを推測解放しない |
| EnableAccount / Logon | 単回有効化とtoken取得の応答。Enableの成功/失敗/不明を問わず、以後はDisable→Verify義務が残る |
| DisableAccount / VerifyDisabled | Disableは単回要求のみ。独立照会で固定Pの無効が確認できた時だけAccountDisabledConfirmed。失敗要求後の照会で既に無効と確認できる場合は区別する |
| EraseSecret | 全secret bufferのゼロ化・解放が完了。失敗/不明なら新規起動を禁止 |
| CreatePublisher / CreatePeer | suspendedで作成時からjob参加、process/thread初期SDとtoken境界が成立し、返された全handleを所有。後付けAssignProcessToJobで原子性を代用しない |
| VerifyWorkers | Bの所有handleから両workerのidentity/code/実token/SD/IPC/job状態を確認。自己申告や起動後DACL修正だけを初期境界の証明にしない |
| ResumePublisher / ResumePeer | 両worker確認後だけ再開。peer制御用IPCに許した以外の継承なし |
| ObserveWorkersExit / VerifyJobEmpty | 所有する全processの実終了観測と、子孫を含むjobの空を別々に確認。disableやkill要求だけでは成立しない |
| ClosePeer..CloseAncestors | 各scopeの全所有handleを一回だけ解放し記録。IPC/token/jobより外のcode/祖先を先に解放しない。失敗したclose以降は外側closeを止める |

通常経路は26操作。初回失敗を保存し、新規取得/enable/logon/launch/resumeを止める。
例外的に許すcontainmentは、未実施のDisable→Verify、既知secretのErase、単回TerminateJob→ObserveExitAfterStop→VerifyEmptyAfterStop、既知所有scopeの順序付き解放だけ。
通常のexit観測失敗後に行うstop後の観測は別の有界操作で、同じ呼出しの無制限retryではない。
Terminate失敗でも実終了とjob空を確認できれば解放できる。片方が不明ならworker/外側保護を保持する。
Unknownな取得handleはjob空だけで解決せず、外側保護を保持しContainmentComplete=false。
cleanup失敗はsecondaryとして保存し、primaryの工程/応答分類を上書きしない。

現在のmodelに時間、メモリ、disk、ACL、OS呼出しの強制機能はない。将来adapterで内側40秒/外側45秒、worker private256MiB/working384MiB、空きRAM/disk2GiB等を実装するまでlive worker gateは閉じる。
Bのcrash/OS終了/電源断ではaccount再無効化を保証しない。jobの仕組みもaccount/token失効の保証ではない。次回は不明状態として固定accountを照会し、既存rootを再作成・失敗rootを再訪しない。

## 起動APIと今回の読み取り診断

[CreateProcessAsUserW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessasuserw) はprocess/thread SECURITY_ATTRIBUTESを受け取る。通常SeIncreaseQuotaPrivilege、tokenがassignableでない場合SeAssignPrimaryTokenPrivilegeを要する。caller自身のrestricted primary tokenに対する例外を別user Pへ適用したとは扱わない。
[CreateProcessWithTokenW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createprocesswithtokenw) はSeImpersonatePrivilegeが必要で、process/thread SA引数がない。desktop未指定時には対象userへdesktop/window station権限を追加する挙動があるため、単純なfallbackとして使わない。
この比較は初期SD、token object SDとTokenDefaultDacl、所有者、desktop、原子的job参加の残件を解消しない。

`PrincipalLaunchCapabilityDiagnostic.cs` は自分の通常tokenをTOKEN_QUERYだけで開き、固定U SID/elevationを検査し、TokenLinkedTokenで取得したhandleを一度だけ照会する。
[TOKEN_LINKED_TOKEN](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-token_linked_token) のhandleは所有してcloseする。linked tokenのQUERYが拒否される可能性を許容し、不明をprivilege不存在へ変換しない。
固定3特権SeIncreaseQuotaPrivilege/SeAssignPrimaryTokenPrivilege/SeImpersonatePrivilegeのpresent/enabledだけを記録する。
既存の15件試験済み `PrivilegeLease.ReadEnabled` の有界parserを再使用し、1314だけをmissingと区別する。
QUERY用handleはBOOL成功と形状確認後だけ取得確定し、失敗/例外時の非zero出力を推測closeしない。未確定取得を結果へ残す。
各既知handleのcloseは一回だけ独立した例外捕捉で囲み、QUERYのprimaryと両handleのrelease errorを別々に保存する。leaseの故障試験はnativeを呼ばない。
診断はAdjustTokenPrivileges、SetTokenInformation、DuplicateToken、logon、SAM、root、起動APIを呼ばない。UACも出さない。観測したlinked tokenは将来の別UAC起動tokenの証明ではない。
不足なら権利追加や別APIへ自動fallbackしない。選択肢の具体化を次段階とする。

environment_preparation_complete=true（前回j結果）。それ以外のisolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabledはfalse、acceptance_status=not_completed。
