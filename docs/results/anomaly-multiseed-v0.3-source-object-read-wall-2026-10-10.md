# source object 原clock・read返値と絶対期限の保持（2026-10-10 JST）

## 開始と対象

開始2026-10-09T17:27:04Z/HEAD f11aa6e9f94540f979fb74ee564579e1f4bb24ae-origin/upstream-clean、前test/doc code f9a78a68a99407cc63b94c293f6dee8811311bef、production2d66f40e0fbf0ec1e0ec251996399c59bbd2c314。先行元10helper full creation-start_token/live-execution一致・read-only CIM同original不在/helper-critical ownerなし。人の明示再開を維持してACTIVE、追加agent起動/再活性化0。

既存 _anomaly_v03_reader_dependencies.py 一つへ opt-in read_wall と同原capture holderのclock/checkpoint ledgerを追加、新test module一つ。新production module0。Reader/Archive module・旧SourceBatchContractPreparation source segment14301B/0903a855f665499d9e3eba5248ceaca09387b948a7051d42704d792db18c0b17・create_native437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7c・旧v1 schemasを保持する。

## 原wall候補と呼出し順序

capture_raw の read_wall は元(clock callable, started_ns, deadline_ns)のexact tupleを、getter/validation前に同原 SourceObjectBatchRawCapture へprivate保持する。元7field capture inputsと別に保持し、同原preparationのprivate checkpointを使う。開始/期限は非boolの0以上int・signed64範囲、開始<期限、差<=30000000000ns。各readやstderrへ移るときに期限をリセットしない。

新internal closed anomaly-v03-source-object-raw-capture-candidate-v2 は従来のrequest pin/call順/raw maxima/4096B read/各stream128attempt/検出1byteに、新read_wallの開始・期限・literal monotonic nanoseconds・clock/checkpoint原return最大1028・blocking_read_interrupted=false/clock_authenticated=falseを結ぶ。read_wallなしのv1 descriptorにfield追加0。scope全false/unresolved=trueのまま。

stdout/stderrのread getter前、各read直前、原read返値保持後に、同原checkpoint→同原clockの順で呼ぶ。各callback invocation/pendingを呼出し前にprivate保持し、原returnを型/単調性/期限/owner判定前にprivate ledgerへ保持する。checkpointは元None返値だけ、clockは元start以上・直前clock以上のintだけを受け、返値>=元deadlineなら拒否する。例外はreturn_observed=false、None等が返った場合はreturn_observed=trueとして型違反を保持する。

遅いreadの原bytesは元operations/prefixへ保存してからpost-wallを判定する。期限超過やunknown clock/checkpointでstderr/次read/retain_rawへ進まない。最後のstderr EOFでも遅い返値ならraw complete登録0。read/getter例外を別のclockで後から成功へ補わず、第一error/原stream/callable/pending/invocation/clock/checkpoint/原return-prefixを同原holderと既存ParentPublicationRetentionに保持する。close/reclose/reap/新keeper0。

callback再入・public wall ledger消去・private wall binding消去を第一errorへ固定する。callbackが再入拒否を飲んでreturnしても外側原returnを先に保持して停止する。返値保存で消されたpublic aliasを正常へ上書きしない。cached resultは同原7fieldと同原wall tupleだけ、別wall tuple/stream候補を保持して無clock/無readで拒否。failed再入はread/wall ledgerを増やさない。

これはcaller stream工程の原return後の期限フェンスであり、blocking read自体を中断しない。checkpoint/clock getterとcallback自身、metadata/proof/packing/joinの全経路wall boundも証明しない。clock/start/deadline/receipt/exitはcaller Python inputsで、実native clock・Job worker stdio・child receipt/exit/partial transport認証ではない。実same-owner native bounded-return接続は未完了。

## 局所確認と互換性訂正

初回新15method/body15を一回 0.40768930001650006 秒、15pass/failure0/error0/skip0。小FileIO+実time.monotonic_nsの原return、期限前getter拒否、遅いread/最後EOF、stderrへの期限継続、checkpoint/clock例外・型違反・逆行、再入、wall ledger/binding消去、cached field、同原親keeper保持を確認した。

差分確認で、新wall候補のためにprivate rejected_inputsを包むと旧stream参照位置が変わる点を見つけた。元7field tupleをそのまま残し、rejected_wall_inputsへ別保持する形へ訂正。影響する新cached wall case1＋wallを付けたforeign stream原tuple保持の新risk1だけ一回 0.008782100048847497 秒2pass/failure0/error0/skip0。初回他14/旧19・前19・前16/訂正済み容量1case/旧focus-suite反復0。16distinct/body17、途中production/test sourceを変更した複数source-runなので最終source単一16successではない。初回15の成功を原source/runとして保持する。

invented source/opaque receiptとexit/BytesIO・注入read/clock/checkpoint callback、ReaderGitParent.__new__/Mock checkpoint/retention試験専用_pause Escape。実time.monotonic_nsと小FileIOはlocal工程観測だけ。test context cleanupはproduction/native回収ではない。実Popen/Job/HANDLE/ACL/launcher/child/native0。selected observationsはread/wall件数とprefix幅で、原stream全bytes literal file又はhelper全process stdout-stderrではない。

## source・容量・CI

113source-science各run前後一致/開始112の他111不変。変更production1/newtest1 safety0、旧37Git原rawと検証済み親tree-doc-only非交差を継承し、完成37Git/collector/native image/profile/基本OS-runtime probe再実行0。科学hash metadataだけ/holdout観測未読/credit0。named30source 969644 B、最大archive130691B/e5ab8de3cc7f02f6ccc9f5eb08feeb5e283a64782c2e16bc78ac8f25c6f36337/cap差381Bはruntime/global容量ではない。

全14call4358432Bの元constructor拒否と独立raw/storage maximaは変更・再実行・解除0。clock/checkpoint ledger・検出byte・原raw prefix/一時join/tuple/decoded object/native buffers/他writer同時保持/全future32entry/global coupled peak/RSSは未証明。1028は局所callback件数上限で容量許可ではない。archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64/outer1MiB32entry depth2 reserve128KiB/global321MiB672entryの元capsを保持する。

37963486811/full2d66をcompact一回、attempt1/push/Phase1CI/.github/workflows/ci.yml/workflow349172377/in_progress。原run11702B/7fbda3bf72abcc2da8fbeb6c29dbb819b137a600c7e4d9ab0e97351edd0697fd/stderr0/exit0。f9a78実fullSHA selection一回は37965644173/push/Phase1CI/in_progress、原156B/b1b673300fdbdce74af38e372e860d6bbe3eb7895a92d6b01b83be4c3c91ea5d/stderr0/exit0。両jobs/終端/journal/count未固定、新379656のattempt未固定。待機/反復/download/verifier0。379582の4062error1/verification skippedと旧4043以下/旧failureを再照会せず保持する。doc-only新CI追跡0。

次heartbeatは379634/full2d66と379656/fullf9をcompact各一回、新unit実fullSHA selection一回だけ。終端のみ新専用rootへ未保存原raw一度、3.14単一journal/独立verification/2logsをfullHEAD-workflow-run-attempt-jobsへ結び実summary後count固定。379634が既知fixture failureなら小cause/raw保存だけで容量訂正1caseを再実行しない。未終端/空は反復・待機なしで具体的未完了経路へ進む。

## 保存と未完了

原 artifacts/preformal-source-object-read-wall-20261010-prep/、components metadata artifacts/preformal-source-object-read-wall-post-20261010-prep/、CI compact artifacts/preformal-ci-object-capacity-current-save-20261010-prep/、Git後metadata artifacts/preformal-source-object-read-wall-save-20261010-prep/。各512KiB32entry/reserve128KiB/single128KiBで閉鎖する。先行failure/prefix/rawcapture全8rootsはcount/bytes/manifest/原raw pins不変。

original components27603B/b7854b289670a5185b91e62e22526a0a43d4b785481da9156631c3eb00d3a96dとcontinuation28823B/1af13f061bff61987a646c7e7c7749ffcc57bceb858716dc137eb0c41890ff01は別に保持し、訂正前source metadataを書換えない。原foreground positional Windows wildcard rg missはtool excerpt記述だけ/creation-full process logsNone、production/CI/native/Sol failureへしない。

fresh loaded source/runtime全閉包-profile-private policy-native request-unused exclusive root、実worker read wall・stdio・receipt/partial transport、診断専用公開/parent_failure実raw/child bootstrap、OS排他-allwriter atomic/native call-return-HANDLE-child endpoint-close-rename認証は未完了。caller EOF/期限内原返値/readback/body-Git pins/manifest/cached completionをnative許可へしない。create_native早期拒否/全7役whole.run限定reader起動禁止/formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/正式5残件・最終受入未完了/元unknown原owner-stop/追加agent禁止/ACTIVE維持。code unit一回commit/push、Git後文書2path追補は一回skip ciへ集約する。
