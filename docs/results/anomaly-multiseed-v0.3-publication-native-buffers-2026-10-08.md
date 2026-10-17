# 限定launcher準備の独立buffer allocation（2026-10-08 JST）

## code保存・CI

code `d4e5f2ec90a9c17be90af4eadebadb4b769a409b` を確認後の5file一回commit/push、origin一致・cleanで保存。code-save17465B/937cf7ea09e4c4dcb804e65d92b4340171e100167f2a83b5bdb0cf679653c0a7で60working-Git/science、code commitのdocs2、原focus/component/raw、元3helper、先行native-process prep23file117256B/CI3812root38file10201722B/batch13file48794B不変を照合。新CI37743146137はgit実fullSHAで選択したPhase1CI/push/in_progress観測のみ、attempt/jobs/終端未固定。3844は3829＋新15の算術予定でjournal未確認。

元components44008/creation134359175847553688/token935c48cdf7124813e488d65862b4616283d9ed76138700c9c8d389005afe6cfd、code-save45844/134359178894658798/token08d6224715bc10e07b612f17d3f59003e340a051f5013e9b867c28d7865a7c37はlive/execution passed。doc追補3文書を一回skip ciへ集約する。保存後は全60working-Git/science/final docs3/原raw/元4helper exact creation-token/HEAD-origin-clean/旧3root不変をmetadataだけ一度照合し、専用rootを閉じる。完成15/旧suite/native/CI numerical/download/runner反復0を維持する。

doc追補の初回apply_patchはCI文書見出しの不一致で検証前拒否・tracked変更0を確認した。対象見出しを一度参照して訂正したmetadata失敗であり、production/CI/native回収失敗ではない。tool error抜粋をmetadata-edit-failure.jsonへ保持する。原process stdout/stderr byte fileの捕捉ではない。

## 保存範囲

開始HEAD `9b2cf05a8c40ef71523930e01354db7fb04b8d83` はorigin一致・clean。元先行5helperのcreation/token対応process不在、repo helper/critical ownerなしを確認した。CIMのsandbox Access deniedは許可済みread-only照合で解消し、native回収結果にはしない。CI37739862442/full1e1c900cbe8c909f28da552488c31d8dff8263b2はattempt1/push/Phase1CI、3.12job113187830209/3.14job113187830427両in_progress、compare未発行のcompact観測だけ。終端raw/journal/local回帰/runner照合は今回追加0。

専用rawは `artifacts/preformal-publication-native-buffers-20261008-prep/`。変更production2＋新test1、new production module0。完成native-process17/HANDLE_LIST22/旧suite/完成CI/13AST監査は再実行しない。正式gate=s4_acceptance_not_frozen、formal_permission=false、credit0、登録holdout観測未読。science2はhash metadataだけを読む。

## 接続した経路

`ReaderPublicationLaunchPreparation.arm_native_buffers` → 新closed `anomaly-v03-publication-native-buffer-allocation-v1` のvalue/pin → 同原entry raw pin・storage plan pin → HANDLE_LIST sizingの実返値/size → allocation照合 → 原opaque buffer/5HANDLE array/STARTUPINFOEX → native process preparationの原invocation/command/PROCESS_INFORMATION/member output、を一つのunitへまとめた。

元allocation・Python owner・拒否inputをcopy/clock/API観測前に保持する。新descriptorはformat/entry_pin/storage_pin/limits/total_bytes/formal_permissionだけのclosed形式。旧external v1-v4/request/entry/context/ack/proofへfield追加や旧pin読み替えはない。actual generate/READER_BOOTSTRAPからの発行は未接続で、既存の準備だけの形式は互換。

独立caller maximaはdescriptor/entry/invocation/command/attributes/handle_array/startup/process/memberの9枠。全将来枠の最大値合計がcaller total（最大131072B）内に収まることを最初に確認し、完了枠を割り引かない。descriptorのencoded wrapperは最大32768B、entry/invocation/attributesは各既存32768B以内。commandのlocal ctypes幅は終端NULを含め、非BMP文字を含むときもcode point数とUTF-16 unit数の大きい方で事前に確保量を計算する。これはlocal ctypes layoutの測定で、実Win ABIやnative継承の観測ではない。

原sizing returnは先行部品が元return位置で保持し、その実sizeをbuffer作成前に独立attributes最大値へ照合する。command/PI/memberもnative buffer作成・Assign/member API getter前に照合する。invocationとdescriptorのJSON bytesは既存のbounded生成後の実bytesを数える。原byte objectとnative buffer tupleを返った位置で保持し、予告幅と実sizeof/lenを照合する。前の未解決claimを第二claimで隠さず、entry→attributes→processの順序と各一回だけを認める。

caller descriptor改変、原ledger/pending消去、原allocation参照消去、第二allocation、size超過、unknown Update/clock/IO/割込みは、原・拒否input/buffer/原第一例外を保持して後続拒否する。known prefixや原source4・専用2・stdio3・raw Job ownerを破棄せず、relaunch/Delete/Close/reapへ落とさない。cached view/prepareはAPI/clockを反復しない。親の同entry/storage/clock/inventoryへforwardし、元保持経路からpending/errorを隠さない。

`reserved_maxima_bytes` は独立caller最大値を全枠計上した量で、OS memory予約・all-writer atomic予約ではない。計上対象は保持byte object/native bufferのpayload幅だけ。Python object/tuple/dict/コピー/一時JSON/command text/RSS、原API/output ledgerのobject overhead、実packet/gzip/frame/partial raw/archive growthとのcoupled peak/global memoryは未測定。storage/root容量の合格やnative許可を発行しない。

## 確認結果

新15distinct/body15/unique15。初回新14一回30.72744019998936秒pass/fail0/error0/skip0。その後reviewで原attribute allocation参照消去の拒否を補強し、新1だけ0.0025224999990314245秒pass。pass済み14は反復0。別source/runであり、最終source単一15success runではない。

各60source/science pin前後不変、component間の他58pin不変、先行native-process共通57pin不変、変更3file safety0。ReaderGitParent.create_native拒否method437B/0bd7b84f0a3dc0bd22a865ac8b2b4ccedc0e71ea50a177b0e6b086df07fdcc7c不変。fake API/Job record/Popen/creation＋親fixtureの実小FileIO/root/channel、正常composing snapshotは明示stub、retentionは試験専用_pause Escape。実Create/Assign/member/Close/Delete/worker/Job/pipe/exe/native0、追加agent/profile再観測0。native/atomic/capacity/ack/auth=false。

| 保存raw | bytes | SHA-256 |
|---|---:|---|
| focused.json | 23985 | 575ac92211aba36f769cb88457b43c81c31f8972b810ea02b54fd4ccb96b2776 |
| focused.log | 3211 | e1096ea61723d341d5cf55b139bc143fd2c1eef9f6786b4ff0265b66fa6f5267 |
| focused-v2.json | 23100 | f17d288c309a247ad906454689f8266e68dfc11cc5998179c80104461fe64fd6 |
| focused-v2.log | 331 | 79c0f067ee3d8caedb4db8fd2b363b60ad4d0c4a7d007c45b7d9667d41c77a19 |
| components.json | 17007 | fe6c4abe4a4456a28a935dd6a54979b6aeb601f7c872779b62bcd3432e6b1ec3 |

元focus45764/creation134359172305077886/tokenf91dce5e8dd94a81955e7334d592301a7b2e3ef6eade44e6332c8b30afa9de99と新1の18456/134359173728788127/token2791b26431514675a106accb9c776830dda9485954a224bb445d4eafcef517f5はlive/execution一致・passed。PID単独で過去processと同一扱いしない。componentsの元identityは同rootのcomponents-live/executionへ保存する。

名前30source合計820544B、最大job_tree_owner120035B/cc126fca55a0cfe128f90215283669b45f8589bbaca8103fb7233694dbddd5a5。generatedは60準備pin内・名前30外。phase32要求/予定64Git Jobは完全runtime閉包ではなく、旧profile/source capを流用しない。

## 残りと次のunit

fresh latest-clean source/runtime/profile/private policy/request/unusedroot、実control-packet/raw/partial/archive/新9buffer/object overheadのcoupled peak/global memory・全writer参加の独立予約・exclusive launcher準備は未完成。原CreateProcess BOOL/PI/Job assignment-member returnの元return位置捕捉、原raw ownerと既存Popen bridge、stdio実owner/継承性、cross-process HANDLE渡し、child原close/rename/raw witness transport認証も未接続。新descriptorとbyte viewをnative許可や容量合格へ読み替えない。

次はこれらの未完成量をfresh inventoryで束ね、実control packetと保持raw/partial/archive growthを別量のまま測る準備を進める。原return captureは原owner/attribute lifetimeへ結ぶ。準備前にnative入口を開かず、全7役whole.runを限定readerとして実起動しない。原caps/stop保全、旧raw/pin/失敗、正式5残件未完了を維持する。
