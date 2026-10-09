# source object metadata batch 原stream/read返値保持（2026-10-10 JST）

## 保存単位と範囲

開始16:46:53Z/HEAD 01aa06df44d0ea3617a160970e073c3bf93b6724、production/test fe518101411f7af7ba3689298625f85502f4fbce。元7helperのfull saved creation-start_token/live-execution一致、read-only CIM同original不在、helper-critical ownerなしを確認。人の明示再開を維持してACTIVE。追加agent起動・再活性化0。

今回のproduction変更は既存 _anomaly_v03_reader_dependencies.py 一つ、新test一つ。ReaderGitParentの既存source object preparationと同原ParentPublicationRetentionを使用し、reader/archive moduleは変更しない。旧SourceBatchContractPreparation ASTと旧v1 schemas保持、create_native437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7c保持。新production module0。

## 閉じたread capture候補

SourceObjectBatchContractPreparation.capture_raw と SourceObjectBatchRawCapture を同unitに追加。元(preparation,call_index,stdout stream,stderr stream,opaque receipt,declared exit,partial)を getter/validation前にprivate保持。新internal anomaly-v03-source-object-raw-capture-candidate-v1 はrequest pin/順序call/独立raw maxima/4096B read chunk/各stream128attempt/検出1byte/scope全falseへ固定する。前後head/statusと全metadata groupの順序、独立全future raw maximaとstorage maximaの計算は旧source object contractを使用する。

元read getter/read callable/各invocationと要求幅をIO前に保持。原read returnをtype/len/owner validation前にprivate operationsへ保持し、原bytes prefixを独立tupleに残す。stdout後stderrの順に最大4096B、残幅+1の検出を要求し、非bytes/要求超過/独立cap超過/128attemptを拒否。read例外はreturn_observed=false、None返値はreturn_observed=trueだが型違反として別保持。EOFは当該readの返値だけでclose/native回収ではない。

原read callbackによる再入、alias消去、同callの別retain_raw挿入を原第一errorへ固定。callbackが拒否を飲んでreturnしても外側原returnを保存して停止し、stderr/再読取り/別raw登録へ進まない。ledgerを更新するときにcallbackが消したpublic aliasを上書きして正常へ戻さない。cached resultは同原stream/receipt/exit/partialだけ、別streamをprivate rejected inputsへ保持して無読取りで拒否。原capture ledger消去後の次capture候補も元inputsをprivate保持して拒否。failed再入はcapture/read ledgersを増やさない。

原stdout/stderr joinとopaque receipt/partialを既存retain_rawへ同holderだけからforwardし、元metadata proof/fullbody SHA256・別blob SHA1との照合/SOM1 memory-only literal fullraw readbackへ結ぶ。partialとreceiptは独立maxと別量、SOM1以外のframe再使用・gzip/base64・実archive append/receipt移動0。失敗又はunknown readは原stream/callable/invocation/return-prefix/第一errorを同preparationと元親keeperの下に保持し、close/reclose/reap/新keeper0。

これはcaller streamの工程captureで、実native Job workerのstdio/child transport接続ではない。receiptとexitはopaque Python inputs、実native receipt/exit認証ではない。blocking readの全経路wall bound、read callbackの実native byte bound、検出byte/一時join/tuple/ledger/native bufferの全future容量は未証明。元全14call4358432B拒否を再実行・解除せず、scope全false/unresolved=trueを維持する。

## 局所確認と原失敗

新19distinct/body20。初回16を一回 0.04820730001665652 秒、15pass/failure1/error0/skip0。失敗はpendingの元値NoneをNoneに戻すtest期待で、原focus/helper failedを保持。期待を異なるobjectへ訂正し、具体的な新risk3（read callback alias消去の上書き、次capture ledger消去、callback別raw挿入）を追加。失敗1+新3だけ一回 0.01615999999921769 秒4pass/failure0/error0/skip0。途中production/testを変更した複数source-runであり、最終source単一19successではない。完成初回15/旧focus-suite/先行新19/5metadata/容量拒否/26gzip/collector/37Git/native image/profile/基本OS-runtime probe反復0。

小発明source/metadata/receipt/exit、BytesIO・注入read callbackと小FileIO読取り。小FileIOは発明metadataをdiskへ置いてcaptureで読む試験で、先行実Git5group rawの再実行ではない。ReaderGitParent.__new__/Mock clock/retention試験専用_pause Escape。test-owned streamはtest contextが閉じるがproduction captureはcloseしない。実Job/Popen/child/native0。selected observationsはread件数・prefix幅で、原read全bytesのliteral file保存やhelper全process stdout-stderr捕捉ではない。

111source-science各run前後一致/開始110の他109不変。変更2source path safety0、Git sourceの未変更分は検証済み親tree-doc-only非交差/先行37rawから継承する。changed dependencyの原親Git bodyだけ一回別raw取得し、旧SourceBatchContractPreparation ASTと元working pinを照合。科学hashはmetadataだけ、登録holdout観測未読/credit0。

名前30source 965635 B、最大archive130691B/e5ab8de3cc7f02f6ccc9f5eb08feeb5e283a64782c2e16bc78ac8f25c6f36337/cap差381B。source幅はfull runtime閉包/global RSS/coupled peak/全32entryの容量保証ではない。旧source/profile/request/policyを新sourceへ流用しない。

## 未終端CIと次の経路

37958200991/full fe518101411f7af7ba3689298625f85502f4fbce をcompact一回、attempt1/push/Phase 1 CI/.github/workflows/ci.yml/workflow349172377/in_progress。原run11712B/cf91dc19431ffc21aea2850c3419342fc392b09718a471756acd2bb959a6006b/stderr0/exit0を保存。jobs/終端/journal/実件数未固定。待機/反復/download/verifier0。完成4043以下/旧failure/旧2minorへ再照会0、doc-only新CI追跡0。

原evidence artifacts/preformal-source-object-raw-capture-20261010-prep/、別metadata artifacts/preformal-source-object-raw-capture-post-20261010-prep/、compact artifacts/preformal-ci-source-object-current-save-20261010-prep/。各512KiB32entry/reserve128KiB/single128KiB、元failed・selected selector missを保全する。foreground focused.py missは正しいfocus.py参照前のtool excerptで、creation/full process logsNone、production/CI/native/Sol失敗へしない。

次は実同原owner worker transport/readのwall・stdio・receipt/partial認証、全future検出/一時raw/全32entry/global peak、OS排他-allwriter atomic、fresh loaded source/runtime全閉包-profile-private policy-native request-unused exclusive root。これらは未完了。create_native早期拒否/全7役whole.run限定reader起動禁止/formal gate=s4_acceptance_not_frozen/formal_permission=false/credit0/正式5残件・最終受入未完了/元caps-unknown原owner-stop/追加agent禁止/ACTIVE維持。
