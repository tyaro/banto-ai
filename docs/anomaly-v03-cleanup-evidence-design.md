# S4-B1 cleanup evidence: 記録契約の設計とpure prototype

日付: 2026-09-07

状態: **candidate / native cleanup adapter tested / independent audit pending**

最新状態: `068e45b`のprototypeからnative snapshot captureとcleanupへ接続した。
81 pure/fault＋same-parent Windows native 1件がpass。詳細は末尾の「native接続checkpoint」を参照。
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
