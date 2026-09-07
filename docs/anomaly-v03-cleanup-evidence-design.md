# S4-B1 cleanup evidence: 記録契約の設計とpure prototype

日付: 2026-09-07

状態: **candidate / cleanup + replacement trace tested / independent audit pending**

最新状態: `8cc67c6`のnative cleanupに、置換操作の事前snapshotと追記trace、child/parent接続を追加した。
93 pure/fault＋same-parent Windows native 2件がpass。最新節「置換trace checkpoint」を参照。
以下のprototype節は`068e45b`時点の設計・実測を保持する。cleanup/evidence全体のP2解消、
独立監査、restricted-child E2E、main統合、正式受入は主張しない。

基準: `0d917d9`（実装基準 `16a037f` + 引継書2 commit）。
[引継書](results/anomaly-multiseed-v0.3-s4-b1-handoff-2026-09-07.md) §6〜7に対応する。

## このcheckpointの成果と境界

清掃の途中で一部を削除した後に失敗すると、現行 `_Fixture.cleanup()` は元のSDを
上書きしており、failure resultの `known_bytes` は残存量を表さない。
削除要求・handle close・名前の消失確認も別の出来事として記録する必要がある。

そのため、IOを一切行わない [記録部品prototype](../tests/fixtures/anomaly_v03_cleanup_model.py) と
[pure/fault試験](../tests/test_anomaly_v03_cleanup.py) を追加した。
これはnative接続前の実行可能な契約prototypeであり、現行Windows harnessはまだ使用しない。
既存 `_anomaly_v03_windows.py`、child、D2 pins、科学config/schemaは変更しない。
prototypeはtests/fixturesに置く。srcへの新規file追加もD2の固定current-only path集合を
変えるため、native接続前にproduction sourceを拡張しない。

引継書の「実装前の独立threat review」は未実施である。今回の確認は作者による
設計検討とpure試験であり、独立監査と呼ばない。レビュー対象をこの具体的な契約に絞り、
native mutationへの接続はその後に行う。cleanup/evidence P2は未解消のままとする。

## 清掃前snapshot

native側で全owned tree、identity、SD、ADS、hardlink、bytesを検証し、変更を始める前に
`CapturedObject` のtupleを確定する。各objectはsafe relative name、種別、identityの
canonical bytes、変更前SD、予定する変更後SD、fileの実bytesを持つ。
operation evidenceは別のimmutable bytesとして含める。

入力は最大32 objects、file単体1 MiB、file合計4 MiB、identity/SD各64 KiB、
operation evidence 1 MiBに制限する。snapshot hashは順序を正規化し、全項目のhashと
file byte countを含めて計算する。mutable native ledgerとの参照共有はしない。
rootの存在、親子関係、directory種別、重複pathもpure側で検査する。

identity/SD/operation bytesの意味の検証はnative capture側の責務である。
prototypeはbyte列が実Win32 objectから採取されたことを認証しない。

snapshot全体は `private_snapshot` から明示的に参照できるメモリ内の証拠であり、
`repr` と `report()` は生SD、SID、file contentを出さない。ディスクへの保存、
process crashや電源断からの回復は保証しない。

## 状態遷移

| 記録 | 遷移 | 解釈 |
| --- | --- | --- |
| ACL | unchanged → pending → changed | API開始前にpending、descriptor readback成功後にchanged |
| ACL失敗 | pending → unknown | APIが失敗しても一部変更された可能性を残す |
| 削除 | not_started → pending → armed | disposition成功だけでは削除済みとしない |
| 削除失敗 | pending → unknown | 元のobjectが残ると決めつけない |
| close | not_started → confirmed / unknown | handleの解放を確認する。名前の消失とは別 |
| 消失確認 | armed + close confirmed → absent | native側の明示確認が必要 |
| 全体 | prepared → running → completed / failed | failure後は再開・再清掃を禁止 |

APIを呼ぶ**前**に `begin()` を成功させ、API/検証の成否を `confirmed()` / `failed()`
へ記録する。例外経路ではまず一次失敗を記録し、その後に所有handleのcloseを試す。
close失敗で一次mutation failureを上書きしない。childがabsentになる前のparent削除は拒否する。
foreign objectを台帳に取り込むAPIは設けない。

resource stopを一度記録すると解除できない。以後は所有handle closeの結果記録だけを許し、
新しいACL/削除/消失確認を始めない。`failed()` の正常経路ではsnapshotの再生成をしない。
`report()` はmemory-onlyだが新しいdict/listを確保するため、MemoryError handler内での
実行安全性は主張しない。native接続時はpreallocatedな停止状態を保持し、メモリの余裕を
確認できない場合は詳細reportの生成を延期する必要がある。

## 残存量とcontrol結果

`captured_bytes` は清掃前の量であり、残存量ではない。absent確認済みを差し引き、
delete pending/armed/unknownのbytesは不確定として、残存captured bytesの下限・上限を返す。
object countも同様に計算する。ACL変更だけではobjectの存在量は減らない。

これはこの清掃操作がcaptured objectsに与えた既知の影響であり、実ディスク使用量や
同時に現れたforeign objectを含むfresh inventoryではない。確認済みabsentのsnapshotも保持する。
全captured objectがabsentとなった場合だけcompletedを許し、途中失敗でresidue 0は返さない。

native接続時は `control_status`、`cleanup_status`、`teardown_status` を分離する。
control pass後のcleanup failureはcontrol evidenceを捨てず、総合statusはfailedとする。
private snapshotを返却後も所有するresult容器と、安全なJSON summaryを分離する必要がある。
digestだけ返してsnapshotを破棄する実装は「完全evidence保持」の受入を満たさない。

## native接続前のレビュー項目・残作業

1. 全snapshotの採取、固定、allocation成功が最初のACL変更より前であること。
2. 各mutation直前に保持handleのidentity、現在SD、file bytes/child集合を検証すること。
   pure recorderの `confirmed()` を観測の代用品として使わないこと。
3. native API失敗後にfilesystem診断で再構成しないこと。readback途中失敗はunknownとすること。
4. delete disposition、close、absenceを各々観測し、権限不足や共有違反をabsenceへ変換しないこと。
5. 失敗したcloseのhandle identityを保持し、他のowned handleの解放は継続すること。
6. `_replace_control()` の置換先作成・source移動・target消失・source復元を、
   operation開始前のidentityからboundedに記録すること。現状の最後の `del ledger[target_name]`
   だけでは途中失敗を説明できない。この部分はprototypeへ接続していない。
7. private evidenceをresultの寿命まで保持し、生SID/SDDL/絶対pathを公開JSONやtest failureへ出さないこと。
8. pure/faultで全境界を注入してからsame-parentの小native fixtureだけを実行すること。
   required restricted-child、追加DLL probe、B2、formal runはこのcheckpointの対象外。

## 検証

選抜コマンド:

```powershell
python -B -m unittest tests.test_anomaly_v03_cleanup tests.test_anomaly_v03_windows.PureWindowsControls -q
```

新規15 test methods（内部subtestsを含む）と既存55 pure/fault、計70件を対象とする。
最終実測は70/70 pass、0.336秒。2 Python filesのin-memory compileもpass。
追加のD2 current-only inventory試験は1/1 pass（9.187秒）、repository safetyとdiff-checkはpass。
main/candidateでformal 5 rootずつを確認し、存在数は0だった。
snapshot不変、部分削除の数量、ACL/API失敗の不確定性、closeとabsenceの分離、
resource停止後のIO禁止、foreign path拒否、親子順序、再試行禁止、証拠redactionを検査する。
native経路を変更していないためnative fixtureは実行せず、新規失敗rootも生成しない。

read-only前後inventoryはmain/candidate両方のartifactsとsystem-tempの既存B1 failure rootsを
合算した今回独自の範囲で、5,763 entries / 592,342,788 bytes、failure rootsは6件。
path/type attributes/byte count/raw SHA-256/SDDLを含む同一手順のdigestは前後とも
`0ae21dd53bd4f5a6994d720e019386e50ce4437c9cccf9b883d380b6f0964aa7`。
引継書§5の617 entriesという別範囲のinventory digestとは直接比較しない。

全gateを維持する: `B1_READY=no`、`B1_NATIVE_ACCEPTED=no`、`S4_B_ACCEPTED=no`、
`S4_ACCEPTED=no`、`INTEGRATION_READY=no`、`FORMAL_PERMISSION=no`。

## 2026-09-07 native接続checkpoint

基準は `068e45b59202f9f6850faa1d30b28f5ca9814e72`。
記録部品を既存の [Windows implementation](../src/banto_ai/_anomaly_v03_windows.py) に移し、
新しいproduction source pathは増やさなかった。旧prototype moduleは同じ部品を参照する入口とした。
固定current-only 32 paths、historical 88、科学config/schema、child sourceは保持する。

### 実装した動作

- `capture_cleanup()` が全owned objectのidentity/SD/content/子集合/streamsを検証する。
  全snapshotの構築成功後にだけ清掃を始め、capture失敗や二度目の清掃はmutation前に拒否する。
- ACL復元と削除の直前に保持handleからidentity、SD、content、残存child集合を再検証する。
  元の `fixture.ledger` は上書きしない。変更後SDはsnapshotに先に記録したdescriptorとexact比較する。
- 各disposition/close/absenceを別に記録する。`lstat()` のWin32 error 2だけを名前の消失とし、
  access denied、parent missing、残存objectは成功にしない。失敗後のfilesystem再走査はしない。
- 清掃中のhandleはslotへ保存し、close成功まで保持する。fixture最終終了時も全owned handleを試す。
  close診断collectorはfixture作成前に確保し、終了時の再試行用collectorも別に確保する。
  再試行が一次例外へ添付済みの診断を上書きしない。
- `run_control_harness()` は `control_status` / `cleanup_status` / `teardown_status` を分離する。
  control pass後の清掃失敗でも元のcontrol evidenceを保持し、総合statusはfailedにする。
- 返却値はdict互換の `_ControlOutcome`。JSON/reprにはsafe summaryだけが現れる。
  `private_control_evidence` にimmutable control bytes、`private_evidence` にsnapshot＋遷移記録を保持する。
  利用者はこのresult object自体を保持する必要がある。`dict(result)`やJSONへの変換は安全な要約の
  複製であって、private evidenceの永続保存ではない。
- resource stop後は詳細 `report()` の生成を延期する。private snapshotと状態はresultに保持し、
  filesystemに戻らない。全体がfailedならtop-levelの `success_residue_count` は返さない。

### 検証結果

| 対象 | 結果 |
| --- | --- |
| 記録契約15＋adapter故障注入11＋既存pure/fault55 | 81/81 pass、0.167秒 |
| same-parent Windows native | 1/1 pass、0.239秒 |
| D2 current-only exact inventory | 1/1 pass、3.816秒 |
| in-memory compile | 5 files pass |
| repository safety / diff-check | pass |
| artifact / failure inventory | 5,763 entries・592,342,788 bytes・6 failure roots、前後digest一致 |
| formal roots | main/candidateとも全5種類不存在 |
| required restricted-child / Windows 3.12 / full suite | 未実施 |

[adapter故障注入](../tests/test_anomaly_v03_cleanup_native.py) は、ACL変更後のエラー、
各削除位置でのエラー、close失敗と後続teardown、identity/SD差替え、unknown child、
capture内容不一致、MemoryError＋close失敗、access denied/parent missing、再清掃拒否、
safe resultとprivate evidenceの寿命を検証する。mock成功をnative受入には換算しない。

実Windowsの小fixtureでは6 objectsすべての消失を確認し、元のledgerが不変、snapshotが
返却後も6 objects分残ること、owned handle slotが空になることを検証した。
前後inventoryはprototype節と同じ範囲・方式で、digestも
`0ae21dd53bd4f5a6994d720e019386e50ce4437c9cccf9b883d380b6f0964aa7`のまま。
新しいfailure rootは残っていない。

### 残件と判定

作者による検討・故障注入・小native試験までのcandidateである。先行条件と記した独立threat reviewは
未実施のため、順序上は独立レビュー前の実装として記録する。作者確認を独立監査とは扱わない。

`_replace_control()`の途中identity遷移をchildから完全に回収する仕組みは未実装である。
今回保持するoperation evidenceは清掃前に検証済みのcontrol結果とfile内容であり、
その結果が生成される前の置換途中失敗を完全に復元するtraceではない。
また、restricted child `0xC0000142`は診断・再実行していない。

したがってcleanup/evidence P2全体は未解消、B1未完了、main統合不可、formal permissionなしを維持する。
次はこのnative adapterの独立レビューと、置換操作の証拠記録を別の限定変更として扱う。

## 2026-09-07 置換trace checkpoint

基準は `8cc67c67888421a2f30365276d8abc23be9e96cd`。
`_replace_control()` の上書きで消える置換先を、操作後のfilesystemから再構成することはできない。
そこでsourceと置換先のidentity/SD/実bytesを先に保存し、次の6段階をbounded JSONLへ追記する。

| stage | 保存する情報・状態 |
| --- | --- |
| create_pending | 検証済みsourceの完全snapshot。置換先の新規作成前に書く |
| target_captured | 実際に新規作成した置換先の完全snapshot |
| replace_pending | 上書き操作の直前。実行済みとは解釈しない |
| replaced | sourceが置換先へ移動し、元source名が消失したことを確認済み |
| restore_pending | source名へ戻す操作の直前。位置は未確認として扱う |
| restored | sourceのidentity/SD/contentが元どおりで、置換先名の消失も確認済み |

### 記録と検証

最大6 records / 合計128 KiB。各recordにversion、sequence、nonce、前recordのraw SHA-256を含める。
canonical JSON＋改行で追記し、native sinkのWriteFile/FlushFileBuffers/identity checkが成功するまで
次のmutationへ進まない。例外handlerでは追記、再読込、hash、serialization、repairを行わない。

末尾の改行がないrecordは未確認のtailとして扱い、完全prefixだけを検証する。
完全なintent recordが読めてもAPIが実行されたとは限らない。例えばflush/check失敗時には
intentが残ってもmutationを始めないため、pending段階は常にuncertainとする。
これを含め、source位置と元置換先の残存/消費状態をsafe summaryへ分けて返す。
その状態は固定producerとtraceに基づく推定であり、fresh filesystem inventoryではない。

sourceは元のparent ledgerのidentity/SD/hash/bytesと一致させる。置換先は固定content、
sourceと同じmetadata型・volume・属性・権限、別の128-bit file IDを要求する。
順序、nonce、hash chain、strict型、未知field、snapshot content/hash、旧identityへの偽装を検査する。
nonceやhash chainはowner/管理者に対する署名や改変防止を提供するものではない。

### child / parentへの接続

- parentが専用fixture内の固定 `control/replace-trace.jsonl` をexclusive createし、identity/SDをpinする。
  childはその空fileへ保持handleで追記する。新たなrepository/artifact/publication先は作らない。
- private protocolを `b1.2` とし、旧 `b1.1` reportは拒否する。parent/child source 2本のraw pinは維持する。
- child終了を確認したparentは、成功なら完全6 recordsを必須にする。通常のchild失敗時は有効prefixを
  read-onlyで回収する。writer fileのidentity/SDを照合し、完全traceを検証した場合だけ、そのfileの
  content hash/byte countをparent ledgerへ反映する。未知objectの採用やACL変更は行わない。
- `_ControlOutcome.private_replace_evidence` がraw bytesをclose/parse前から保持する。
  parseやcloseに失敗しても取得済みraw bytesは捨てず、総合statusはfailedのままにする。
  公開mapping/reprにはraw SD/SID/contentを出さず、safe summaryだけを含める。
- 完全traceのhashをprivate control evidenceへ含め、清掃前snapshotにはtrace file自体の実bytesも保存する。
  清掃後に置換先の実fileがなくても、操作前snapshotと段階記録がresultの寿命まで残る。
- childのresource failureは専用exit 80へ写し、parentは`child_resource_stop`としてfilesystem再読込をしない。
  timeout、未終了child、resource stop時には回収を追加せず、既に書いたprefixをfixture内に残す。
  通常child failure後のtrace回収にも失敗した場合は、元のchild failureを診断エラーで上書きしない。

### 検証結果

| 対象 | 結果 |
| --- | --- |
| 置換trace pure/fault 12＋既存81 | 93/93 pass、0.227秒 |
| 同一parent内の実Win32 trace/operation/cleanup＋既存native cleanup | 2/2 pass、0.539秒 |
| D2 current-only exact inventory | 1/1 pass、4.377秒 |
| in-memory compile | 5 files pass |
| repository safety / diff-check | pass |
| required restricted-child E2E / Windows 3.12 / full suite | 未実施 |

[置換trace試験](../tests/test_anomaly_v03_replace_trace.py) は、各mutation後の停止、追記/flush失敗、
途中record、偽snapshotと再計算済みchain、resource停止後のIO禁止、raw evidence保持、旧protocol拒否、
child wrapperのresource exitとparentの回収抑止を検証した。wrapper試験は`_child_main`をmockし、
制限付きprocessは起動していない。

実Windowsでは保持handleへの追記を全operation controlsと組み合わせ、parent相当のraw読取・pin/trace検証、
7 objectsのexact cleanup、trace bytesを含むprivate snapshotの保持を確認した。
これは同一parentの試験であり、restricted child経由のE2E合格ではない。

前後inventoryは5,763 entries / 592,342,788 bytes / 6 failure rootsで不変。
raw hash/attributes/SDDLを含むdigestも
`0ae21dd53bd4f5a6994d720e019386e50ce4437c9cccf9b883d380b6f0964aa7`のまま。
新しいfailure rootは残らず、main/candidateのformal 5 rootも全て不存在。

### 残件

置換traceの候補実装と同一parentでの限定検証まで完了した。独立レビューとrestricted-child E2Eは未完了。
したがって、cleanup/evidence P2全体の監査済み解消、B1完了、main統合、S4受入はまだ主張しない。
`0xC0000142`の追加probe、tokenの弱化、required testのskip化、formal runは行っていない。
全gateはnoを維持する。

## 2026-09-07 bootstrap resource-stop補正

child wrapperの共有module import以前のMemoryErrorもexit 80へ写す。
従来はclassifier未定義時にexit 1となり、parentの通常失敗後trace回収を許していた。
MemoryErrorを診断stage分岐より先に判定する。import前に共有定数を参照できないため、
固定値80と共有`_CHILD_RESOURCE_EXIT`の一致を回帰テストで検証する。
通常ImportErrorの扱いは変更しない。

pathlib／共有module importでのMemoryError・ImportErrorを注入し、child本体未実行と
正しいexitを確認した。関連pure/faultは94/94、D2 inventoryは1/1、repository safetyはpass。
実restricted childやsame-parent nativeは今回は起動していない。
これは候補の自己点検による修正であり、独立レビューやB1受入を意味しない。

## 2026-09-07 cleanup report二次障害の分離

cleanup／teardownのfailure後にreport生成が失敗しても、元のreasonとwinerrorを維持する。
追加診断は`cleanup_report_status=failed`と`cleanup_report_resource_stop`で表し、
private snapshotやcontrol evidenceを破棄しない。清掃がcompletedでもreport生成に失敗したら
総合結果をfailedにし、top-level success_residue_countは残さない。

mock harnessで清掃失敗／成功とreport MemoryError／ValueErrorの組合せを検証した。
resource停止済みならreportを呼ばない既存条件も確認した。関連pure/fault 94件、safetyがpass。
同一parent nativeおよびrestricted childの追加起動は行っていない。独立レビューは未完了。
