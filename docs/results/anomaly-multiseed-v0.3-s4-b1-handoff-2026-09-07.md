# anomaly multi-seed v0.3 S4-B1 引継書

状態: **限定Windows engineering control成功 / Linux CI両minor成功 / no integration / no formal permission**

2026-09-11最新: §81のB2 pureモデル（e42a8e5、実機未接続）、§80のLinux CI成功と共有29 payload一致（036ecb4、各1045 pass/67 skip）、§78のWindows3.14.0一本化、§76の実機成功を最初に参照。実装0b30e63のRC＋Everyone候補で、子の全48期待値・報告照合・成功cleanup・teardownが通過した。
専用fixture9対象の削除を確認し、残存0、資源停止なし。最大3回の了承を受領し、1回目の成功でその試行枠を終了した。残り2回は実行しない。
実行前の選抜pure/fake293件と独立差分レビュー、実行内27 source preflightも通過。補完・関連78件は指定Capstone5.0.7でpass、今回の要件改訂に対応する25件もpass。全回帰ではない。
現在のruntimeはWindows10.0.26200.9445/Python3.14.0。UBR固定緩和は§31、直近の実測資源・bootは§81に記録する。
Windows Python3.12受入は要件から削除済み。3.14.0へ一本化しLinux3.12/3.14は維持する。§77の返答待ちは解消した。
B2はpureモデルの設計・検証に着手。実機publisher/本流統合/正式受入は未完了で、formal入口は閉じたまま。

以下の§1〜§10の初期結論・commit一覧・試験数・blocked表記は作成時点の履歴であり、最新のchild E2E結果ではない。
cleanup/置換traceの修正履歴は§11〜17、起動診断と逐次是正は§18〜75を参照。

作成日: 2026-09-07

本流基準: `889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e`

引継ぎ候補: `16a037f73b9033c811ba8b9f7144d7d92d464b05`

保存ブランチ: `codex/s4-b1-windows-engineering`

候補worktree: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`

## 1. 最初に読む結論

S4-A（正式試験前のinspection/resource guard）はmainへ統合済みで、独立監査P0〜P3は0件である。
現在は次段のS4-Bを、さらにB1/B2へ分けたうちの **B1 Windows engineering scaffold** を開発している。

B1候補は、専用の新規system-temp領域だけを対象に、protected DACL、restricted token、
実AccessCheck、実mutation control、source/runtime pin、資源上限、失敗証跡保持の土台を実装した。
一方、restricted childはWindowsで `0xC0000142`（DLL initialization failed）となり、
独立childのend-to-end成功は得られていない。

その後の監査修正により、temp pathの範囲外probe、UTF-16 path、replace positive control、
bounded source読込み、resource failure保持、process/token/file/stream handle teardownは改善し、
最新差分 `16a037f` の独立監査は新規P0〜P3 0件だった。

ただし、**cleanup途中失敗時の完全な証拠保持が未解決**である。このため候補は保存可能な
engineering checkpointだが、mainへ統合できない。S4受入、正式dev/smoke/holdout、性能評価、
promotion、Banto Hub/PLC writeはいずれも許可されていない。

```text
S4-A                    完了・main統合済み
S4-B1 scaffold          実装中・隔離ブランチ
S4-B1 child E2E         失敗（0xC0000142）
S4-B1 cleanup evidence  未解決
S4-B2 publisher/marker  未着手
S4全体                  未受入
formal run              禁止
```

## 2. Gitとworkspaceの状態

### main

- 作業場所: `D:\develop\banto-ai`
- HEAD: `889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e`
- `origin/main`: 同一hash
- 状態: clean
- 最新S4-A文書: `docs/results/anomaly-multiseed-v0.3-s4-a-audit-2026-09-07.md`

### S4-B1候補

- 作業場所: `C:\Users\TKent\.codex\worktrees\70b0\banto-ai`
- ブランチ: `codex/s4-b1-windows-engineering`
- 引継書作成前HEAD: `16a037f73b9033c811ba8b9f7144d7d92d464b05`
- 状態: clean
- push: 未実施
- mainへのmerge: 未実施

候補commit列は次のとおり。

| commit | 内容 | 判定 |
| --- | --- | --- |
| `2b7d8d8` | fail-closed Windows B1 scaffold | blocked。初回監査P1=1/P2=4 |
| `112351c` | scope検証前のtempfile probeを除去 | 限定修正合格 |
| `246a499` | UTF-16 path、実replace control、source/resource bound | A/B合格、resourceは部分改善 |
| `32fa209` | resource primary保持、owned teardown確認 | ambient exception回帰を検出 |
| `d681188` | teardown primary/collectorを明示化 | ambient/owned teardown合格、stream残件検出 |
| `16a037f` | FindCloseでもresource primaryを保持 | 最新差分の新規P0〜P3=0 |

引継書作成前の実装候補`16a037f`とmainとの差分は7ファイル、`+2498/-9`である。

- `examples/configs/anomaly-multiseed-failure-diagnostics-v0.1.json`
- `schemas/anomaly-multiseed-failure-diagnostics-config-v0.1.schema.json`
- `src/banto_ai/_anomaly_v03_windows.py`（新規）
- `src/banto_ai/anomaly_failure_diagnostics.py`
- `tests/fixtures/anomaly_v03_native_child.py`（新規）
- `tests/test_anomaly_failure_diagnostics.py`
- `tests/test_anomaly_v03_windows.py`（新規）

## 3. B1で実装済みの範囲

- 引数なしのengineering-only control entrypoint
- UUIDを使う新規専用system-temp root
- local fixed NTFS、volume/file ID、reparse、hardlink、ADS、path aliasの検査
- protected DACLの設定とhandle-bound readback
- owner/group/ACE、mandatory integrity labelの観測
- restricted primary tokenの作成と実child process tokenの照合
- fixed executable/source、`-B -I`、handle非継承、限定environment
- AccessCheckのAPI成功とaccess denialを分離した権限matrix
- read positive controlとwrite/append/truncate/EA/attributes/delete/rename/replace等の実操作
- file DELETEだけでなく親directory DELETE_CHILDの確認
- 1 MiB IPC/source bound、512 MiB process memory guard、timeout
- resource停止後のfilesystem再走査禁止
- primary failureをteardown failureで上書きしないcollector
- process terminate/wait、token/file/stream handle closeの全件試行と確認
- 成功時だけexact ledger cleanup、失敗時は自動repairしない基本方針
- S4-A receiptとformal gateを開かない固定status

これはhost sandbox、WORM、owner/admin/privileged writerへの完全防御、電源断耐久性を意味しない。

## 4. 最新の限定試験と監査

`16a037f`作成時の選抜試験は次のとおり。

| 範囲 | 結果 |
| --- | --- |
| pure/fault | 55/55 pass、約0.288秒 |
| same-parent native cleanup | 1/1 pass、約0.709秒 |
| 選抜合計 | 56/56 pass、約0.997秒 |
| Python in-memory compile | pass（3 files） |
| safety / diff-check | pass |
| required restricted-child | **未実行** |
| full suite / S3 long regression | **未実行** |
| Windows Python 3.12 | **runtime unavailable / 未実行** |

`tests/test_anomaly_v03_windows.py`には55 pure＋2 native、合計57 test methodがある。
2つ目のnative testがrequired restricted-childであり、既知blockerを隠すskipや成功扱いにはしていない。

最新 `16a037f` に対する独立read-only監査:

- 新規 P0=0 / P1=0 / P2=0 / P3=0
- `STREAM_PRIMARY_FIXED=yes`
- `RESOURCE_PRIMARY_FIXED=yes`
- `OWNED_TEARDOWN_FIXED=yes`
- `LIMITED_CHECKPOINT_SAFE=yes`
- `SCAFFOLD_MERGE_SAFE=no`
- `INTEGRATION_READY=no`

`LIMITED_CHECKPOINT_SAFE=yes`は候補の保存可を意味するだけで、harness全体の実行安全性、native受入、
main統合、formal permissionを意味しない。

## 5. 保全状態

候補作業中に既存artifactのpath/type/attributes/size/hash/SDDLを前後比較し、不変を確認した。

- artifact: 617 entries / 461 files / 36,352,494 bytes
- inventory digest: `4fa5a45e45bfbde1b7012a575c5d9a077fe8c578fbb87d6791e8048e10744f4d`
- 既存B1 failure roots: 6 roots / 39 objects / 15,045 bytes
- failure inventory digest: `fd1661679bd6b67f573d84bf27791cfd54265976b0806df91267a645f41cd5d3`
- formal v0.3 roots: 5種類すべて不存在
- 最終修正群による新規failure root: なし
- science configs/schemas、historical 88 pins、D2 pins: 不変
- D2 current-only: 32 paths

既存failure rootsは意図的な診断証拠である。削除、ACL復元、移動、再利用をしないこと。
repository文書や公開ログには生SID、SDDL、handle値、絶対temp pathを記録しないこと。

## 6. 未解決課題

### P2: cleanup途中失敗時の証拠保持

現在のcleanupは、既知objectのDACLをprivateへ戻しながら順に削除する。途中で失敗すると、
既に一部objectやACLが変更された後であるにもかかわらず、次を完全には表現できない。

- cleanup開始前の完全なobject/identity/SD/operation evidence
- 削除済みobject
- 残存object
- ACL変更済みobject
- replace途中のidentity遷移
- cleanup失敗後の正確なknown byte/object accounting

「失敗時は全証拠保持」と一括表現してはならない。controlの合否とcleanupの合否を分離し、
cleanup開始前の証拠snapshotを確定したうえで、各遷移をbounded ledgerへ記録する必要がある。

### restricted child `0xC0000142`

`CreateRestrictedToken`、`CreateProcessAsUserW`、親側の実child token取得、AccessCheckまでは到達したが、
childはDLL初期化失敗で終了した。

切り分け済み:

- Pythonだけでなくsystem `cmd.exe /d /c exit 0`でも同じ終了code
- minimal environmentと`CreateEnvironmentBlock`相当の環境で同じ結果
- 実WinSta0/default desktopへのrestricted token AccessCheckは必要rightsを許可
- Python/fixture固有、単純なenvironment-only、既定desktop DACL不足は支持されない
- artifact/failure roots/formal rootsはprobe前後で不変

未確認:

- faulting DLLまたは具体的な初期化object
- token default DACLと失敗の因果関係
- suspended/desktop条件の独立比較
- driver/process handle残差の分類

追加probeは承認なしに繰り返さない。restricted tokenを弱める、通常`Popen`へfallbackする、
required testをskip/passへ変える、昇格・別資格情報・account作成・既存window station/desktop ACL変更で
回避することは禁止する。

## 7. 次セッションの推奨順序

1. mainと候補worktreeのHEAD/clean、artifact/failure/formal inventoryをread-onlyで確認する。
2. この引継書とv0.3計画§8〜§9、S4-A監査結果を読む。
3. cleanup/evidence P2だけの設計を固定し、実装前の独立threat reviewを行う。
4. cleanup前snapshot、遷移ledger、partial cleanup resultをpure/fault testから実装する。
5. same-parent nativeの小fixtureだけで検証し、required restricted-childはまだ実行しない。
6. 独立read-only監査でP0〜P3、artifact不変、gate閉鎖を確認する。
7. cleanup/evidence合格後、`0xC0000142`を別savepointで診断する。
8. B1全体のrequired Windows 3.14/3.12 native acceptanceに合格してからB2へ進む。

cleanup/evidenceの実装では、次を受入条件にする。

- cleanup開始前の完全evidenceをメモリ上で確定する
- 各objectの`not_started / acl_changed / delete_armed / deleted / failed / unknown`等を曖昧なく記録する
- 一つの失敗後も、安全に確認できる所有handleのcloseは続ける
- foreign/identity不明objectを削除・re-ACLしない
- 失敗後に証拠を再生成して元状態を装わない
- resource stop後にfilesystem診断へ戻らない
- cleanup失敗をnative control失敗と分離して返す
- 成功時だけresidue 0を主張する

## 8. 再開時の安全な確認コマンド

PowerShellで次を個別に実行する。最初はread-only確認だけにする。

```powershell
git -C 'D:\develop\banto-ai' status --short --branch
git -C 'D:\develop\banto-ai' rev-parse HEAD
git -C 'D:\develop\banto-ai' rev-parse origin/main

git -C 'C:\Users\TKent\.codex\worktrees\70b0\banto-ai' status --short --branch
git -C 'C:\Users\TKent\.codex\worktrees\70b0\banto-ai' rev-parse HEAD
git -C 'C:\Users\TKent\.codex\worktrees\70b0\banto-ai' log -8 --oneline
```

期待値:

- mainと`origin/main`: `889cfc3d5e1fd6dd7fc6c9656273d16d7d56d64e`
- candidate branch: `codex/s4-b1-windows-engineering`
- 引継書作成前candidate: `16a037f73b9033c811ba8b9f7144d7d92d464b05`
- 両worktree: clean

引継書commit後はcandidate HEADが1つ進むため、本書のcommitを`git log`で確認する。

## 9. 禁止事項とgate

次の状態を維持する。

- `B1_READY=no`
- `B1_NATIVE_ACCEPTED=no`
- `S4_B_ACCEPTED=no`
- `S4_ACCEPTED=no`
- `INTEGRATION_READY=no`
- `FORMAL_PERMISSION=no`

禁止事項:

- mainへのmerge/push
- formal dev/smoke/holdout/analysis/audit rootの作成
- registered seed、960 dataset / 2,880 slot campaignの実行
- 既存artifact/failure evidenceの削除・修復・ACL変更
- science config/schema/seed/threshold/gateの変更
- 顧客データの追加
- token弱化、通常process fallback、required native testのskip化
- host desktop/window station ACL変更、account作成、昇格
- known workflow CRLF差の自動normalizeやoverride

## 10. 非専門家向け要約

現在は、本番試験を始める前に「試験結果を安全に保存し、あとから勝手に書き換えられていないか
確認する仕組み」を作っている段階である。基本部品の多くは動き、メモリ不足や終了処理で記録を
失わない改善も済んだ。

ただし、保存用の一時データを片付けている途中で故障したときに、「何を削除できて、何が残り、
どこまで権限を変更したか」を完全に説明する仕組みがまだ足りない。また、Windowsの厳しい制限を
付けた確認用processが起動直後に止まる問題も残っている。

したがって、研究の準備は進んでいるが、正式試験や製品利用を開始できる状態ではない。
次は片付け途中の記録を完成させ、その後にWindows起動問題を解決する。

## 11. 2026-09-07 再開checkpoint: cleanup記録契約

`0d917d9`から、[cleanup evidence設計とpure prototype](../anomaly-v03-cleanup-evidence-design.md)
を追加した。変更前のimmutable snapshot、ACL/deletion/close/absenceの別状態、
部分清掃のcaptured byte/object下限・上限、解除不能なresource stopを実装した。
新規15＋既存55 pure/faultの計70 test methodsがpassした。

これは実行可能な契約の準備であり、Windows harnessへの接続やcleanup/evidence P2の解消ではない。
独立threat review、native snapshot capture、replace identity遷移、private evidenceを保持する
result容器、native cleanupへの接続、same-parent native再検証は未実施である。
既存native実装・D2 pins・科学config/schemaは変更せず、全gateは引き続きno。
次は設計書のレビュー項目を確認し、native capture/result容器から接続する。

## 12. 2026-09-07 native cleanup接続checkpoint

`068e45b`から、native snapshot capture、元ledgerを変更しないcleanup、disposition/close/absenceの
別記録、private evidenceを所有するdict互換resultを実装した。81 pure/fault、same-parent native1件、
D2 inventory1件がpass。詳細・制約は[設計書の最新節](../anomaly-v03-cleanup-evidence-design.md)を参照。

清掃開始後の部分失敗とcontrol結果の保持は接続したが、置換操作の途中identity traceは未接続である。
独立レビューも未実施で、cleanup/evidence P2全体の解消とは判定しない。
restricted-child再実行、追加DLL probe、B2、正式試験、main merge/pushは未実施。全gateはnoを保持する。

## 13. 2026-09-07 置換trace checkpoint

`8cc67c6`から、source/置換先の操作前snapshotと6段階のbounded JSONL traceを追加した。
native追記、child/parent protocol `b1.2`、private raw evidence保持、resource exit後の回収抑止まで接続した。
93 pure/fault＋same-parent native2件＋D2 inventory1件がpass。
既存成果物・6 failure roots・formal領域は不変。詳細は[設計書の最新節](../anomaly-v03-cleanup-evidence-design.md)を参照。

§12で未接続だった置換traceは候補実装済みになった。ただし独立レビューとrestricted-child E2Eは未実施で、
cleanup/evidence P2の監査済み解消とは扱わない。起動障害の追加probe、main統合、正式試験は未実施。
次は候補の独立レビューと、別savepointでのchild起動障害の切り分けである。全gateは引き続きno。

## 14. 2026-09-07 child bootstrap resource-stop修正

`a66d3f5`の自己点検で、childが共有moduleをimportする前にMemoryErrorを受けると、
resource classifierが未定義のため通常exit 1となり、parentがtrace再読込へ進む経路を確認した。
wrapperでMemoryErrorを先に判定し、import前でも固定protocol exit 80を返すよう修正した。
通常のImportErrorはexit 1を維持する。独立レビューではない。

pathlib／共有moduleのimportにMemoryErrorとImportErrorを注入する回帰テストを追加した。
実childは起動せず、classifier未定義・child本体未実行・終了コードを検証する。
関連pure/fault 94件、D2 exact inventory 1件、repository safetyがpass。
変更はbootstrapの例外分岐であり、same-parent native試験は今回は再実行していない。

既存記録ではPythonとcmd.exeがともに0xC0000142で停止しているが、原因DLLは未特定。
追加probe、required restricted-child E2E、Windows 3.12、full suite、main統合、正式試験は未実施。
独立レビューと起動障害切り分けは残件。全gateは引き続きno。

## 15. 2026-09-07 cleanup report二次障害の原因保持

`b526868`の自己点検で、清掃失敗後に`CleanupJournal.report()`も失敗すると、
元のreason／Win32 errorがreportのエラーで上書きされる経路を確認した。
既存failureのreasonとwinerrorを保持し、reportの失敗は`cleanup_report_status`と
`cleanup_report_resource_stop`へ分離した。private snapshotとcontrol evidenceは保持する。
清掃成功後にreportだけ失敗した場合も総合statusはfailedとし、success_residue_countを除去する。

mock harnessの回帰試験を6ケースへ拡張し、清掃failure＋report MemoryError／ValueError、
清掃成功＋report MemoryError／ValueError、resource停止後のreport呼出抑止を確認した。
関連pure/fault 94件とrepository safetyがpass。実process・native mutationは今回は実行していない。
独立レビュー、restricted-child起動障害、Windows 3.12、full suiteは残件で、全gateはnoを維持する。
D2 current-only exact inventoryも1/1 pass（35.628秒）。

## 16. 2026-09-07 trace parserの型・末尾境界修正

`efc5a06`の自己点検で、trace snapshotの比較がPythonの等値判定に依存し、
identity／nested security内のtrue・1・1.0を区別せず受理する経路を再現した。
source identityと両snapshotのsecurityはcanonical JSON bytesで比較し、pinの型を厳密に維持する。
またsplitlinesがCRでも分割するため、未確認tailのCR以降がbyte countから抜ける経路を再現した。
record終端をLFだけに限定し、未確認tailの全bytesを保持・集計する。

修正前は追加2テストの9 subcasesが失敗。修正後は関連pure/fault 96/96 pass（1.367秒）。
同一parentの実Win32 trace／snapshot／cleanup試験1/1 pass（0.560秒）、repository safetyもpass。
追加試験は偽snapshotのchainを再計算しており、hash chainだけに依存しない拒否を検証している。
required restricted-child、Windows 3.12、full suite、独立レビューは未実施。全gateはnoを維持する。
D2 exact inventory 1/1 pass（15.646秒）。既存成果物・失敗rootのinventoryは5,763 entries／
592,342,788 bytes／6 failure rootsで不変、raw hash・属性・SDDLを含むdigestも既記録と一致した。

## 17. 2026-09-07 operation failureの即時停止

`f76687d`の自己点検で、positive controlの例外がerror 0なら成功扱いとなり、
後続operationへ進む経路を確認した。通常のOSErrorでwinerrorがNoneの場合も元例外が
operation_unexpectedへ置き換わっていた。positive controlの例外はそのまま再送出し、
frozen controlで明示的なerror 5を得た場合だけ期待する拒否として受理する。
flush／query等の失敗、teardown failure、private replacement evidence付き例外は従来どおり停止する。

rights-openは各API直後に結果を判定する。INVALID_HANDLE_VALUEとlast error 0の組合せを
失敗として扱い、無効handleをcloseしない。controlでのopen拒否もmutation開始前に停止する。

回帰試験はOSError、明示的error 0、object_open／mutation_apiのfailure、open失敗を注入し、
元例外保持と後続操作未実行を確認した。関連pure/fault 98/98 pass（0.449秒）、
同一parent実Win32 2/2 pass（2.132秒）、repository safetyもpass。
required restricted-child、Windows 3.12、full suite、独立レビューは未実施。全gateはno。
D2 exact inventory 1/1 pass（10.880秒）。既存成果物・失敗rootのinventoryは5,763 entries／
592,342,788 bytes／6 failure rootsで、raw hash・属性・SDDLを含むdigestも既記録と一致した。

## 18. 2026-09-07 起動障害のread-only切り分け

`74c42ee`を対象に既存Application/WERの直近3日分を確認し、Python/cmdの該当障害記録は得られなかった。
faulting DLLは未特定。公式仕様と照合し、空lpDesktopが非対話desktopを保証するとのコメントを訂正した。
実際の接続先は未観測であり、既存AccessCheckの結果だけでは同一objectへの接続を証明しない。
[調査記録と次に必要な証拠](anomaly-multiseed-v0.3-s4-b1-startup-triage-2026-09-07.md)を参照。
今回は実引数・動作・testsを変更せず、追加child起動／native mutation／ACL変更を行っていない。
独立レビューとrequired child E2Eは未完了。全gateはno。

## 19. 2026-09-07 独立レビューの開始

実装固定対象`f2f2d95`、比較基準`16a037f`として、ユーザー承認により別エージェント1体へ
read-only独立レビューを依頼した。依頼時点ではレビュー結果は未取得で、監査済みとは扱わない。
[レビュー用資料](anomaly-multiseed-v0.3-s4-b1-review-packet-2026-09-07.md)に対象・反証項目・
許可するpure試験・禁止するnative実行を集約した。設計書冒頭の古い最新試験数も訂正した。
レビュー中は実装を固定し、進捗の反復ポーリングを行わず完了通知を待つ。
全gateはnoを維持する。

## 20. 2026-09-07 独立レビュー指摘の是正完了

初回独立レビューはf2f2d95にP2を2件検出した。trace読取handleのclose失敗時の所有喪失と、
teardown report二次例外による一次原因・result証跡喪失を9797500で修正した。
同じ独立担当の再監査で2件の修正を確認し、今回差分の新規P0〜P3は0件だった。
[監査・是正記録](anomaly-multiseed-v0.3-s4-b1-evidence-audit-2026-09-07.md)に反例と結果を保存した。

実装担当の検証: pure/fault 100/100、同一parent実Win32 2/2、D2 1/1、safety/diff-check pass。
独立担当もpure 100/100と元の反例の解消を確認した。既存成果物・6 failure rootsのinventoryは不変。
限定checkpointの保存と次の診断準備は可。次は別savepointで起動障害の診断方法を具体化する。
required restricted-child、Windows 3.12、full suiteは未実施。起動障害0xC0000142は未解消。
main統合・native acceptance・formal permissionはnoを維持する。

## 21. 2026-09-07 startup probeのoffline準備

673f762を基準に、起動障害観測の[probe準備計画](anomaly-multiseed-v0.3-s4-b1-startup-probe-plan-2026-09-07.md)を固定した。
PATH外のWindows SDK x64にCDB/WinDbg/GFlagsがあることを確認し、CDBのversion/hashを記録した。
実行・install・registry変更はしていない。

tests/fixturesにIOなしのStartupEvents部品を追加した。固定PID、256 events、30秒未満、
pending/Continue/exit/signaledの区別、resource latch、型・容量・順序の拒否をofflineで確認した。
追加8件＋既存100件=108/108 pass（1.787秒）。production source・D2 pins・science configは変更していない。

native adapterは未実装で、probeは未実行。次はevent/file handle所有と有界teardownを含むadapter実装、
fault試験、独立レビューを行い、その後に初回probeの具体的な実行条件を確認する。
LOAD_DLLだけでfaulting DLLを断定しない。全acceptance gateはnoを維持する。
D2 exact inventory 1/1 pass（31.604秒）、repository safety/diff-checkもpass。

## 22. 2026-09-08 休眠Win32 event transportと独立再監査

09a1150からx64 DEBUG_EVENT ABIとWait/Continue/file-close接続部をtests/fixturesへ追加した。
初回9b41df5の独立レビューで、呼出前OOM停止漏れと成否不確実なcloseの再試行にP2を2件検出。
ac876b1で修正し、同じ担当の再監査で2件の解消と新規P0〜P3=0を確認した。
[transport記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。

実装担当: transport/event 21件＋既存100件=121/121 pass（0.243秒）、D2 1/1（4.603秒）、safety/diff-check pass。
独立担当: transport/event 21/21、元の反例と追加failure注入を確認した。
production harness/source pins、科学config、既存artifact/failure rootは変更していない。
child・debugger・native mutationは今回起動していない。

次は起動driverとsource/runtime pin、新規fixture、初期bootstrap breakpointの識別、
総資源上限、owned child停止と有界event drain、private結果保持を接続する。
休眠transport単体ではchildの終了処理を行わないため、実probeはまだ開始できない。
完成driverのfault試験と独立レビュー後、初回実行条件を具体化する。全acceptance gateはno。

## 23. 2026-09-08 owned-child停止と有界event drain

休眠終了controllerを34774a9で追加し、owned child停止要求→最大32回のevent drain→
EXIT Continue→process signaled→owned launch handle解放を接続した。結果はprivate_ownerで
未解放handle、raw buffer、primaryを保持する。wait/continueの不確実性はstateとは別flagに保持する。

独立レビューのP2 2件（signaled時の未解決所有見落とし、resource latch引継ぎ漏れ）を942c94aで修正した。
同じ担当の再監査で2件の修正、新規P0〜P3=0を確認。詳細は[終了controller記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。

実装担当: pure/fault 133/133（0.237秒）、D2 1/1（6.742秒）、safety/diff-check pass。
独立担当: 関連33/33と元の反例・report障害の注入を確認。今回もchild/debugger/native mutation未実行。
production harness、D2 pins、science config、既存artifact/failure rootは変更していない。

次はsource/runtimeを固定したlauncher、新規fixture、初期bootstrap breakpoint識別、
累計資源上限を持つ観測loopと今回の終了controllerを結合する。現状は起動entry未接続で実probe未実行。
完成driverのfault試験・独立レビュー後、初回probe実行条件を確認する。全acceptance gateはno。

## 24. 2026-09-08 有界観測loopと終了controllerの結合

116db41で通常event観測をStartupEventsとOwnedDebugStopへ結合した。
30秒未満・300 wait・256 event・合算memory sample 512 MiB以下で制限し、失敗時は通常Continueを止める。
exit80はresource stop、その他のexit観測もnative合格にしない。private_ownerがraw buffer、
primary/secondary、未解放handleを保持する。launcherと実memory samplerはまだ未接続。

独立監査のP2 2件（完了直後の中断時に二次例外が漏れる、owned stop中断後の通常Continue再実行）を
abaebe6で修正した。pure/faultは147/147 pass（0.506秒）。D2 1/1（13.689秒）、repository safety pass。
同じ担当の独立再監査で2件の修正と新規P0〜P3=0、関連pure 47/47 passを確認した。
詳細・再監査結果は[観測結合記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。

次は初期bootstrap breakpointの検証可能な識別方法を確定し、source/runtime pinと新規fixtureを持つ
launcherへ接続する。発生順だけで初期breakpointと見なさず、現状はすべて拒否する。
実child/debugger/probeは未実行、mainは889cfc3のままclean。全acceptance gateはno。

## 25. 2026-09-08 起動前確保とowned memory計測

38e7ebcでrecorder/observer結果をPID未確定の段階で確保できるようにし、後から一度だけbindする。
DebugMemoryを追加し、事前確保した2組のbuffer/pointerで親とowned childのピークcommitを取得する。
partial取得・API失敗・OOM・中断でbufferを保持し、通常transportと再照会を止める。
512 MiBちょうども拒否するよう既存productionの境界へ整合した。

pure/fault 156/156（0.366秒）、D2 exact inventory 1/1（4.905秒）、repository safety pass。
独立監査P2 1件（既知child peakによる上限到達確定後の再照会）をdeef50dで修正した。
修正後pure/faultは157/157（0.341秒）。確認済みprocess別peakを使って早期停止する。
独立再監査でP2修正確認、新規P0〜P3=0、関連pure 57/57 pass。繰り返しの進捗照会は行っていない。
独立監査の詳細は[観測結合記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。
今回もchild/debugger/native APIは実行せず、fake kernel/PSAPIのみを使用した。

残り: source/runtime pin、新規fixtureとCreateProcess/Resumeの所有接続、system commit情報、
初期breakpointのimage/symbol/命令位置の検証。公式仕様は固定addressを保証していないため、
DbgBreakPoint exportのRVAのみで初期breakpointを識別する案は採用しない。
全breakpoint拒否、実probe未実行、全acceptance gate noを維持する。

## 26. 2026-09-08 固定source/runtime事前検査

916f908で診断用10ファイルのdisk/index照合と既存_runtime確認を行うStartupPreflightを追加した。
固定hash/size行と部分結果を保持し、30秒・parent512 MiB未満・source累計1 MiB以下を検査する。
失敗・resource stop後の追加読込は行わない。起動entry、fixture作成、CreateProcessは呼ばない。
verifiedはdisk/index一致のみで、loaded-code認証・起動許可・native受入はすべてfalse。

独立監査のP2 1件（最終report書込みOOM後のverified残留）を05d65f8で修正した。
pure/fault 165/165（0.306秒）、D2 1/1（3.841秒）、repository safety pass。
独立再監査でP2修正確認、新規P0〜P3=0、指定pure 8/8 pass。
詳細・再監査は[事前検査記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。
実preflight・child・debugger・native APIは今回未実行。

次の接続点はlauncherの固定allowlist追加と、新規fixtureからCreateProcess/Resumeへの所有移管。
PROCESS_INFORMATIONはAPI呼出前に確保して結果ownerへ保持し、成否不確実時に捨てない設計が必要。
初期breakpointの検証方法、system commit情報、完成driverのfault試験/独立監査も残る。
実probe未実行、全acceptance gate noを維持する。

## 27. 2026-09-08 suspended createとhandle移管

a73c966で低レベルSuspendedDebugLaunchを追加した。child作成前からPROCESS_INFORMATIONと結果ownerを
保持し、API成否不確実時はraw outputを捨てず、確認成功後に既存transport/OwnedDebugStopへ移管する。
core起動条件へDEBUG_ONLY_THIS_PROCESSのみ追加し、Resumeは未接続。完成driver/CLIはない。
診断source allowlistはこの部品を含む11ファイルへ拡張し、production/D2 pinは変更しない。

pure/fault 173/173（0.328秒）、D2 1/1（5.234秒）、repository safety pass。
独立監査P2 1件（bind失敗で確定childの停止経路を失う）をed12507で修正した。
確認済みPIを先にstopへ保持し、終了時に実PIDを照合して所有を回復する。修正後174/174（0.367秒）。
再監査で成功後capture自体の中断に同じP2が残ったため、11b7efdでAPI前にowner参照を接続する構造へ変更した。
stop回復はcreation_state=createdのみ。修正後175/175（3.255秒）。
独立再監査でP2残件の修正、新規P0〜P3=0、指定pure 30/30 pass。未終了fake childの停止まで独立確認した。
独立監査の詳細は[起動接続記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。
API成否不確実時はraw所有を保持するが、child停止確認を保証しない。
作成確認済みのbind/adopt失敗と成功確認直後の中断は11b7efdで回復して停止を試みる。
実probeに進む前に、この未解決所有を含むdriver全体の終了手順を整える必要がある。

次は新規fixture/tokenと全collectorの所有をまとめ、preflight→作成→実child検証→Resume→観測へ接続する。
初期breakpoint識別、system commit情報、完成driverのfault試験/独立監査も残る。
実child/debugger/native APIは未実行、全acceptance gate no。

## 28. 2026-09-08 prepared sessionの接続

a059067でpreflight→suspended create→実child検証→Resume→観測/終了をまとめるDebugSessionを追加した。
新規fixture/親restricted tokenは外側driverが所有し、sessionは実childのprimary/duplicate tokenを所有する。
token closeの成否不確実性とprivate例外を保持する。検証失敗はResumeせず、Resume自体も1回だけ。
create前からobserver終了まで同じ30秒時計を使う。診断source allowlistは12ファイル。

pure/fault 182/182（0.410秒）、D2 1/1（3.783秒）、repository safety pass。
独立監査P2 1件（token取得成功後のhelper返却前中断による所有漏れ/teardown誤成功）をcbac022で修正した。
token出力bufferを事前所有し、成否不確実と取得確定を分離する。修正後184/184（0.351秒）。
独立再監査でP2修正確認、新規P0〜P3=0、指定pure 56/56 pass。
監査の詳細は[session統合記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。
実preflight/child/debugger/native APIは未実行。全acceptance gate no。

次は外側driverによる新規fixture/親restricted tokenの作成・証拠保持・終了時解放、
system commit情報、初期breakpoint識別を接続する。完成driverのfault試験/独立監査はまだ必要。

## 29. 2026-09-09 別プロジェクト連続稼働への配慮とsystem memory診断

ユーザー指示: 同PCで別プロジェクトの連続稼働試験中。メモリリークとディスク残容量へ配慮する。
この指示は次回以降も継続。作業の区切りで空きメモリ/C・D空きをread-only確認し、
短時間のpure/fakeテストを逐次実行する。他プロジェクトのprocess停止、設定変更、ファイル整理をしない。
実child/負荷試験/大きな生成物は現在の作業に追加しない。小さな差分の独立監査だけを委譲する。

今回開始付近: 空きRAM9.83 GiB（総量31.70）、C102.65 GiB、D75.36 GiB。
b749c08でGetPerformanceInfoの事前bufferをDebugMemoryへ追加し、system commit/limit/physical/availableを保持する。
親＋child512 MiB予算は変更なし。pure/fake186/186（0.440秒）、safety/diff-check pass。
D2対象変更なし、追加ディスク走査は省略した。独立監査詳細は[system memory記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。
独立監査は新規P0〜P3=0、関連pure25/25（1回）。終了付近は空きRAM9.45 GiB、C102.64 GiB、D75.36 GiB。
測定差は全PCの併行負荷を含み、リーク有無の結論ではない。今回の短命test processは終了済み。

残りは外側driverの新規fixture/親restricted tokenの所有と清掃、初期breakpoint識別、完成driver監査。
実preflight/child/debuggerは未実行、全acceptance gate no。

## 30. 2026-09-09 外側driver統合とOS固定条件の判断点

6d97709で親/restricted tokenとSIDの出力を事前所有する部品を追加し、独立監査は新規P0〜P3=0。
b4c1365で新規fixture・b1.2 request・preflight・session・終了を接続する外側driverを追加した。
temp空き1 GiB以上を要求し、診断fixtureは証拠として保持、終了時はhandleのみ解放する。
既存failure rootを再利用・清掃しない。source allowlistは14ファイル。production/D2 pinは変更なし。

独立監査P2 1件（child側未解決所有をouter teardownへ集約しない）を94bbdceで修正した。
再監査P2解消、新規P0〜P3=0、関連pure41/41。実装側197/197（0.674秒）、safety/diff-check pass。
詳細は[driver記録](anomaly-multiseed-v0.3-s4-b1-debug-transport-2026-09-08.md)を参照。

その後、child/fixtureを作成しないStartupPreflightだけを実行（0.502秒）。runtime_pinで停止した。
OSは26200.9445、固定条件は26200.9168。Edition/DisplayVersionとPython3.14.0のcompiler/tag/architectureは一致。
sources_checked=0でexe/DLL hash・source実照合は未到達。OSと固定条件は変更していない。
現在OS向けの別候補条件を整備するか、既存条件を維持して実機検証を保留するかがユーザー判断点。

初期breakpoint識別と実probe準備は引き続き未完了。別プロジェクト連続稼働中への資源配慮は継続する。

## 31. 2026-09-10 承認済みWindows更新条件の緩和と実状態

ユーザー指示: 「Windowsアップデート自動的にかかったのでそこの条件は緩和してください。状態としては記録してください」。
966723cでS4-B1の_runtimeについてUBR=9168一致を外し、有効なuint32値を受け入れて実buildへ記録する。
26200/Professional/25H2/AMD64、Python3.14.0のcompiler/tag/hash、非free-threaded条件は維持する。
run前後のruntime比較は実測UBRを含むため、途中の状態変化は引き続き拒否する。
旧10.0.26200.9168は当初条件の履歴として保存。formal campaignのpinや実行許可を変更するものではない。

実状態: Windows 11 Pro 25H2 / AMD64 / 10.0.26200.9445、CPython3.14.0、MSC v.1944 64 bit (AMD64)、
tags/v3.14.0 / ebf955d、free threading無効。exe/python314.dll hashは既存固定値に一致した。
初回の再検査でsrc/banto_ai/__init__.pyとtests/__init__.pyのCRLFだけがindexのLFと不一致と判明。
内容差がないことを確認して、このworktreeだけを.gitattributesのLF方針へ整合した。Gitの内容差はない。
再検査はverified、sources_checked=14、source_bytes=172259、resource_stop=false。

pure/fake200/200（1.169秒）、D2 1/1（12.838秒）、safety/diff-check pass。
独立担当のd3a53f9..966723c4bf4ddcf786aeb744288a3ca88fa96211監査は新規P0〜P3=0、指定pure60/60 pass。
実driver/child/debugger/負荷試験は未実行。別プロジェクト連続稼働への配慮を継続する。

## 32. 2026-09-10 未識別breakpointの全体停止確認と診断範囲の判断案

test_anomaly_v03_debug_driverへ、CREATE→LOAD_DLL→BREAKPOINTからouter driver全体を通す
fake統合試験を追加した。正常停止、Terminate失敗、停止後ContinueのOOMの3条件で、
bootstrap_unverifiedを一次原因として保持し、raw例外code/address、通常観測と停止drainの分離、
未解放handle、token解放、resource stop伝播を確認した。production/診断driver実装の変更はない。

関連pure/fake58/58（0.421秒）、diff-check pass。独立担当は指定test差分だけを監査し、
新規P0〜P3=0、指定fake7/7 pass（1回）。繰り返しpollはしていない。D2対象変更なし、追加走査は省略。
開始付近の空きRAM7.51 GiB、C102.89 GiB、D75.36 GiB。PC全体の単発値でリーク有無を判断しない。

残る判断は、初期breakpointの厳密な識別・継続実装を先に完成させる当初範囲を維持するか、
最初の観測を「最初の未識別breakpointまで記録して停止」に限定するかである。
後者を提案として[初回probe計画](anomaly-multiseed-v0.3-s4-b1-startup-probe-plan-2026-09-07.md)へ具体化した。
限定案ではその後のDLL初期化原因を判定しない。これは範囲の判断案であり実行承認ではない。

raw eventはprivate_ownerによるprocess内保持のみであり、fixtureを残すことと永続保存を混同しない。
限定案を選んだ場合も、取得済みbuffer/状態の有界private保存と失敗時の扱い、fault試験・独立レビューを
完成させてから実行1回の条件を提示する。実child/debugger/負荷試験は未実行、全acceptance gate no。

## 33. 2026-09-10 限定案の保存処理を接続し初回実行の確認へ

ユーザーは§32の限定案で保存処理の準備を進める提案に「続けてください」と回答した。
準備継続の承認として扱い、実childの起動は行っていない。
b916de9でDebugEvidence/EvidenceFileをdriverへ接続し、source allowlistを15ファイルへ増やした。
production source・D2 pin・formal campaign条件は変更していない。

保存先は新規fixture内のprivate control/startup-evidence.bin。空fileの作成・identity/SD/stream/sizeの確認、
書込用handleの保持を起動前に済ませる。snapshotは全512 raw枠と最大64 KiB metadata、全体155,672 bytes以内。
通常観測と停止drainを区別し、未確認枠・待機/継続の不確実性を記録する。
write/flushは各1回。resource後の再読込・再試行はしない。最後にfile closeし、未解放をouter結果へ集約する。
file内容のdriver結果は保存処理前の時点であり、保存/closeの自己証明ではない。
resource時や保存途中失敗では、process終了後の完全な記録保持を保証しない。
format・制約・実行1回の具体的な条件は[初回probe計画](anomaly-multiseed-v0.3-s4-b1-startup-probe-plan-2026-09-07.md)を参照。

独立監査でP2 1件（保存成功後の二次中断を無視してobservedへ戻す）を検出し、
最終判定へsecondary/teardown失敗を集約する修正と中断注入の回帰試験を追加した。
再監査でP2解消、新規P0〜P3=0、指定fake27/27（0.495秒）。担当の反例はfakeのみ。
実装側の最終pure/fake213/213（1.601秒）、repository safety/diff-check pass。D2対象不変のため追加走査は省略した。

commit後の実read-only preflightは15 source / 186,269 bytes / verified / resource_stop=false。
Windows10.0.26200.9445、Python3.14.0、exe/DLL hashは§31と一致。
空き資源は途中RAM7.87 GiB/C102.88 GiB/D75.36 GiB、終了付近RAM7.33 GiB/C102.84 GiB/D75.36 GiB。
他プロジェクトを含むPC全体の値であり、この差だけではメモリリークを判定しない。
短命テストは終了済み。既存rootの削除・他プロジェクトへの変更・child/debugger/負荷試験は行っていない。

次は提示済み条件で実機の限定診断1回を実行するかの確認。準備承認を実行承認へ拡張しない。
全breakpoint拒否とowned停止を維持し、結果をnative受入/main統合/formal permissionへ昇格させない。

## 34. 2026-09-10 承認済み限定実機診断1回の結果

§33の準備完了後に提示した実機診断1回の確認へ、ユーザーは「続けてください」と回答した。
HEAD963a77a（実装b916de9）でDebugDriverを1回だけ明示実行し、2.346秒で終了した。
driver/session/observerはobserved、child終了codeは0xC0000142。
CREATE_PROCESS→LOAD_DLL×3→UNLOAD_DLL×2→EXIT_PROCESSの7 eventを取得・Continue確認した。
breakpoint/exceptionは観測されず、障害DLLや原因は特定できていない。

process signaledとdebug ownership resolvedを確認し、Terminate不要、drain0回、token/driver teardownはpass。
private保存103,859 bytesのWrite/Flushとfile closeを確認した。resource stopなし、親＋child記録上peak commit約22.87 MiB。
同runのpreflightは15 source / 186,269 bytesを照合し、Windows10.0.26200.9445とPython3.14.0を記録した。
通常観測の完了をchild起動成功やrequired E2Eの合格へ読み替えない。

開始前の空きRAM6.82 GiB/C103.09 GiB/D75.36 GiB、終了後RAM7.68 GiB/C103.09 GiB/D75.36 GiB。
別プロジェクトへの操作はなく、全PCの単発値からリーク有無を判定しない。
mainは889cfc3でclean。追加probe、既存rootの削除/修復/再利用、負荷試験、main統合、formal実行は行っていない。
実行後のsource/temp/remote memoryの再読込みや保存fileのreadbackも行っていない。

詳細・証拠の限界・次の未解決点は[実行記録](anomaly-multiseed-v0.3-s4-b1-startup-probe-result-2026-09-10.md)を参照。
引き続き追加実機probeは自動再試行しない。全acceptance gate no。

## 35. 2026-09-10 保存記録だけの解析と情報不足の確認

ユーザーの継続指示を受け、eefae0fでbyte-onlyのoffline readerとpure試験を追加した。
元のdriver・保存部品・15 source pin・production sourceは変更していない。
pure5/5 pass、独立レビューの新規P0〜P3=0、指定pure5/5（0.006秒）。レビュー側は実記録を読んでいない。

別工程で前回のprivate記録1ファイルを有界にread-only解析した。103,859 bytes、OS/source数/event数/exit codeが
前回の要約に一致し、formatも正常だった。hashと限定した選択・読込手順は
[実行記録の解析追記](anomaly-multiseed-v0.3-s4-b1-startup-probe-result-2026-09-10.md)を参照。
今回のhashはread時点のもので、実行時からの無変更やnative由来の真正性を認証しない。

DLL load順の匿名module1/2/3のうち、module3、module2の順に同じbaseのunloadを確認した。
normal confirmed7、drain0、wait/continue不確実flagなし。confirmed範囲外の保存bytesはzero。
DLL名・image file identityが未保存で、pointerも追跡しないため、名前や原因の特定には進めない。
次にこの情報が必要なら、eventのfile handleをcloseする前にidentity/名前を有界に保持する部品を準備する。
現時点では追加実機probeを承認済みと扱わず、自動再起動しない。

この工程の開始時の空きRAM7.24 GiB/C103.09 GiB/D75.36 GiB、終了付近RAM8.33 GiB/C102.26 GiB/D75.36 GiB。
Cの空きは約0.83 GiB減少したが102 GiB以上残る。全PCの同時稼働を含む値で、発生元やリーク有無は未判定。
この工程で追加したのは小さいreader/test/文書だけ。child/driver/debugger/負荷試験、既存rootの変更、
他プロジェクトへの操作、大きな再走査は行っていない。main統合/native受入/formal permissionは未達のまま。

## 36. 2026-09-10 次回用image identity/name記録の準備

ユーザーの継続指示を受け、06f1e638c6f07dd1f733aa7bce0e392536e60befでDebugImagesを追加した。
observerのevent検証後、file close前に借用hFileからFileIdInfo→normalized NT path→FileIdInfo再確認を行う。
fileの再open・内容読込・remote pointer参照・collectorによるhandle closeはない。
NULL hFile、API失敗、部分取得、名前長超過、identity変化を区別し、再試行せず既存owned停止へ進む。
停止drainでは情報照会しない。volume/file IDとnameはprivate情報として保存し、公開結果へ出さない。

16枠、各name1024 wchar、各identity2bufferを起動前に確保。images全体のJSONを24 KiB以下に制限する。
独立監査P3 1件（24KiBが行合計だけで外枠等を含まない）を修正し、外枠・区切りと
未来の部分row向け各256bytesを予約する。超過する名前は確定rowへ保存しない。
再監査でP3解消、新規P0〜P3=0、指定fake50/50（0.977秒）。実装側pure/fake224/224（1.570秒）。
repository safety/diff-check pass。production/D2/formal pinに変更はなく、D2の大きな再走査は省略した。

collector sourceを追加したallowlist16件の実read-only preflightはverified、192,088 bytes、resource_stop=false。
Windows10.0.26200.9445、Python3.14.0、exe/DLL hashは前回と一致。
開始付近の空きRAM8.16 GiB/C102.25 GiB/D75.36 GiB、終了付近RAM8.13 GiB/C102.25 GiB/D75.36 GiB。
単発値からリーク有無は判断しない。今回の検査processは短命で終了済み。

既存保存記録には変更を加えていない。追加child/実driver/debugger/負荷試験、他プロジェクトへの操作は行っていない。
次回条件は[初回probe計画の追加案](anomaly-multiseed-v0.3-s4-b1-startup-probe-plan-2026-09-07.md)へ具体化した。
観測30秒/256 events、親＋child512 MiB未満、未識別breakpoint停止、drain32回/5秒は維持する。
名前の取得は原因判定ではない。追加実機診断1回の確認を次の判断点とし、準備承認を起動承認に拡張しない。

## 37. 2026-09-10 image identity/name付き実機診断1回の結果

§36の準備後に提示した実機診断1回の確認へ、ユーザーは「続けてください」と回答した。
HEAD43d05f5（実装06f1e63）で明示的に1回実行し、3.216秒で戻った。
通常event7件/Continue7件、exit0xC0000142、breakpoint/exceptionなし。
slot0 python.exe、slot1 ntdll.dll、slot2 kernel32.dll、slot3 KernelBase.dllのfile identity/nameを確認した。
python314.dllのload eventは観測されていない。最後のDLLや読み込み順から原因を判定しない。

process終了・debug所有解放・token/driver teardown=pass、Terminate不要、drain0回。
private104,807 bytesのWrite/Flushとfile closeを確認し、同process内出力bufferのhashを記録した。
fileのreadbackではない。hash・詳細・限界は[image診断結果](anomaly-multiseed-v0.3-s4-b1-startup-image-probe-result-2026-09-10.md)を参照。

同runで16 source / 192,088 bytesを照合し、OS10.0.26200.9445とPython3.14.0/既存hash一致。
記録上の親＋child peak commit約22.93 MiB、resource stopなし。
開始前の空きRAM8.14 GiB/C102.25 GiB/D75.36 GiB、終了後RAM7.97 GiB/C102.24 GiB/D75.36 GiB。
単発値からリーク有無は判定しない。他プロジェクトへの操作・負荷試験・既存rootの変更はない。
mainは889cfc3でclean、追加再試行なし。全acceptance gate no。

## 38. 2026-09-10 出力buffer hashとの照合と次の未測定項目

ユーザーの継続指示を受け、104,807 bytesの保存file1件だけを有界read-onlyで解析した。
SHA-256は§37の実行時メモリ内出力buffer hashと一致。16 source、OS、event数も一致した。
同じ記録内のevent slot/image row/base対応により、KernelBase.dll→kernel32.dllのunloadを確認した。
これは保存bytesの一致確認であり、DLL内容の認証や原因DLLの特定ではない。
詳細は[image診断結果の解析追記](anomaly-multiseed-v0.3-s4-b1-startup-image-probe-result-2026-09-10.md)を参照。

コードと公式仕様の照合では、process/thread作成のSECURITY_ATTRIBUTESはNone、
token profileにTokenDefaultDaclはなく、既存AccessCheckはテストfile/directoryが対象だった。
実child自身と初期threadのSD/default DACLは未測定。原因と断定せず、設定変更前の読取り観測候補として
[process/thread権限観測案](anomaly-multiseed-v0.3-s4-b1-process-security-plan-2026-09-10.md)を作成した。
対象5個、既存handle借用、固定buffer、NULL/空ACL/取得失敗の分離、保存容量・pointer境界検査を要件にした。
file用SD検証やgeneric mappingをkernel objectへ流用しない。collectorはまだ未実装で、実行承認も求めていない。

今回はcode変更・追加child/driver/debugger・token/ACL設定変更なし。保存file/旧rootは書換え・修復・削除していない。
解析と設計文書のみのため、テスト再実行や独立担当への再委譲は省略した。
開始時の空きRAM8.22 GiB/C102.25 GiB/D75.36 GiB、終了付近RAM8.26 GiB/C102.26 GiB/D75.36 GiB。
同時稼働中のPC全体の値であり、リーク有無の判定はしない。全acceptance gate no。

## 39. 2026-09-10 token/process/thread権限の読取り準備完了

c6fc191でDebugSecurityを実装し、driver/session/private evidenceへ接続した。
親・restricted・実child primary tokenのTokenDefaultDaclと、実child process・初期threadの
owner/group/DACL/mandatory labelを、既存ownerのhandleを借用して取得する。
親2対象はchild作成前、子3対象はResume前。handleの追加open/close、ACLや権限の変更はない。

5対象各1 KiBのbufferと状態枠をchild作成前に確保する。token情報class6、kernel情報0x17を使い、
audit SACLは要求しない。各対象1回だけ照会し、失敗・容量不足・不正pointer/SD/ACLでは停止する。
tokenのpointerは所有bufferの返却範囲内だけで解釈し、絶対pointerを保存しない。
NULL/空ACL/未知ACE/照会失敗を区別し、未知ACEは権限へ解釈せずbytesを保持する。
5対象の最大raw保存を含むsecurity JSONが16 KiB未満になることを試験した。全体64 KiB上限も維持する。

許可されたpure/fake231/231（1.321秒）、repository safety PASS。
既存の独立担当へ差分のみレビューを委譲し、新規P0〜P3=0、指定fake36/36（0.641秒）。
完了通知を利用し、進捗の繰返し照会は行っていない。
実read-only preflightは17 sources / 199,864 bytes、verified、resource_stop=false。
Windows10.0.26200.9445、Python3.14.0、既存exe/DLL hash一致。実childは追加起動していない。

検証後の空きRAM8.55 GiB/C102.25 GiB/D75.36 GiB、文書保存前RAM8.46 GiB/C102.25 GiB/D75.36 GiB。
PC全体の単発値でありリーク有無は未判定。他プロジェクトへの操作や負荷試験はない。
次の判断点は[権限観測計画](anomaly-multiseed-v0.3-s4-b1-process-security-plan-2026-09-10.md)の追加診断1回。
30秒/256 events/親＋child512 MiB未満、breakpoint停止、drain32回/5秒を維持する。
既存証跡は保持し、設定変更は行わない。main統合・native受入・formal permissionは未達。

## 40. 2026-09-10 権限観測付き実機診断1回と表示失敗後の証跡確認

§39後の1回実行確認へユーザーが「続けてください」と回答し、HEAD1af72edで1回実行した。
5対象のsecurity取得confirmed。親/restricted/child tokenのdefault ACL bytesは一致し、各ACE3件。
process/threadはowner/group、DACL ACE3件、label対象SACL ACE1件を取得した。権限変更はない。
通常7 events/Continue7件、0xC0000142、breakpoint/exceptionなし。停止記録はprocess終了・debug所有解放・teardown pass。

driver実行後の対話用要約にNone枠の扱い漏れがあり、表示前にAttributeErrorとなった。
再起動せず保存証跡107403 bytesを有界read-only解析し、上記取得・停止・保存前resource_stop=falseを確認した。
最終Write/Flush/file closeの結果、memory peak、実行時buffer hashは取得できず、不明として保持する。
読取り時SHA-256は80d7ce1c602ca04e0a6d7f3488126acd0104f1f0fbcd28577c10a3a7d49d0c1c。
詳細と確認限界は[権限観測診断結果](anomaly-multiseed-v0.3-s4-b1-startup-security-probe-result-2026-09-10.md)を参照。

17 sources、Windows10.0.26200.9445、Python3.14.0と固定hash一致。
空きRAMは開始8.25 GiB→実行後8.17 GiB、C102.25 GiB/D75.36 GiBは同値。リーク有無は未判定。
他プロジェクトへの操作、権限変更、追加試行、既存証跡の変更はない。全acceptance gate no。
次回は保存ACL/SDのoffline比較から継続可能。実機再試行は今回の承認へ含めない。

## 41. 2026-09-10 保存ACL/SDのoffline比較

保存証跡1件107403 bytesを有界read-onlyで読み、§40のSHA-256と一致した。
親/restricted/childのdefault ACLは同一。実process/threadは同じ3 SID・allow ACE順序を持つがmaskは異なる。
tokenのgeneric権限とobject固有権限は区別し、数値差だけを異常や欠落としない。
両objectのmandatory labelはmedium、NO_WRITE_UP | NO_READ_UPで一致した。
threadの匿名SID向けmaskに含まれる0x1000は公開表で意味を確認できず、未解釈として保持した。
詳細・公式参照・限界は[診断結果のoffline比較](anomaly-multiseed-v0.3-s4-b1-startup-security-probe-result-2026-09-10.md)を参照。

権限変更の根拠は得られていない。次は同じfixtureのrequestを有界read-onlyで照合し、匿名SIDのtoken所属・属性を確認可能。
今回の工程はcode変更なし、test再実行・レビュー再委譲・追加childなし。最終保存状態不明の制約も維持する。
開始時空きRAM8.55 GiB/C102.24 GiB/D75.36 GiB。全acceptance gate no。

## 42. 2026-09-10 保存requestとのtoken所属・integrity照合

§40の証跡hash一致を確認し、同じfixtureのrequest6448 bytesだけを追加で有界read-only読込みした。
version/nonce/source2行が証跡と一致、保存parent/restricted profileの既存純粋policy検査も通過した。
requestの読取り時SHA-256は71bb3fd4a20bb8ad840362ebbbf5632e58004d4f7681c2af09aa509ff264b0cf。
匿名AはログオンSIDで、両profileのgroup attributesは0xc0000007（有効、deny-onlyではない）。
userはprocess ownerと一致し、integrityは両方medium。restricting SID listは親が空、restrictedがRCのみ。
保存DACLにRCの直接ACEはないが、WRITE_RESTRICTEDの範囲や実際の要求権限を無視した拒否判定はしない。

保存情報はログオンSID無効化・integrity低下の説明を支持しない。実child全profileの独立snapshotとは区別する。
詳細・参照・残る仮説は[診断結果のprofile照合](anomaly-multiseed-v0.3-s4-b1-startup-security-probe-result-2026-09-10.md)を参照。
次の観測案は初期化で失敗したobject/操作/要求権限を特定できるかを検討する。追加実機起動の承認は未取得。
code変更・負荷試験・追加child・権限変更・旧証跡変更・レビュー再委譲なし。全acceptance gate no。
開始時空きRAM8.65 GiB/C102.24 GiB/D75.36 GiB。PC全体の単発値からリーク有無を判定しない。

## 43. 2026-09-10 最終結果の表示対策と次の観測方法

前回のNone画像枠による表示失敗を避けるため、post-run専用debug_report.write_summaryを追加した。
最終driver結果を先に1行出してflushし、任意詳細は別行。resource停止時は詳細省略、出力失敗は再試行しない。
private情報をwhitelistで除外。各行16 KiB上限。既存driverへ接続せず、追加起動も行っていない。
pure4/4、独立レビュー新規P0〜P3=0（指定pure4/4）、repository safety/diff-check pass。
独立担当の完了通知を利用し、進捗ポーリングは行っていない。

診断証跡の最終書込み時刻前後15秒、Application event ID1000/1001を有界照会したが該当0件だった。
全ログや全期間に障害記録がないという意味ではない。
次の方法は[失敗operation観測計画](anomaly-multiseed-v0.3-s4-b1-failure-observation-plan-2026-09-10.md)で比較した。
Process Monitorは候補だが表示filterだけで収集負荷が限定されると仮定せず、収集除外・容量停止の条件を先に調べる。
loader snaps/debugger breakpointは既存許可範囲外であり、自動fallbackしない。
次回実機承認を求める段階ではない。main統合・native受入・formal permissionは引き続きno。

## 44. 2026-09-10 Process Monitorの低負荷収集条件の調査

一次資料でDrop Filtered Eventsの利用、v3.70の履歴分数/データ量制限、file-backed記録と終了保存の例を確認した。
履歴制限は古いeventを破棄する方式であり、初期化の証拠を保持して上限で停止する保証ではない。
追加tool/driverの全体メモリ上限、所有instanceだけの停止、PID確定後の収集設定適用は未確認。
親＋child512 MiBの既存監視だけでProcmon込みの資源保証をしたことにしない。

[観測計画の一次資料確認](anomaly-multiseed-v0.3-s4-b1-failure-observation-plan-2026-09-10.md)に根拠と不足5項目を保存した。
次は付属helpを実行せず読む方法で設定仕様を確認する。実行案が具体化する前の承認質問は行っていない。
今回download/install/run、driver/service/registry操作、追加child、他プロジェクトへの操作はない。
文書のみのためtest再実行・レビュー再委譲は省略。全acceptance gate no。
開始時空きRAM8.22 GiB/C102.24 GiB/D75.36 GiB。リーク有無は未判定。

## 45. 2026-09-10 公式配布物の非実行確認

現行ProcessMonitor.zip（3,191,035 bytes）にはexe3個とEula.txtのみで、独立CHM/HTMLはなかった。
Procmon64.exeを実行せずメモリ内bytesから関連説明を抽出し、/Terminateが全instance終了を意味すると確認した。
/Runtimeは指定秒数で終了する説明だが、他instanceからの分離やhard deadlineは静的情報だけでは検証できない。
単純な/Terminateを、今回所有した収集だけを止める自動停止として使わない。
詳細・取得hash・残る条件は[観測計画の非実行調査](anomaly-multiseed-v0.3-s4-b1-failure-observation-plan-2026-09-10.md)へ保存。

配布物は3回の有界取得で合計約9.13 MiB転送。ZIP/exeはdisk保存せず、小さい目録・抽出文字列・EULAのみ計9,764 bytesを
artifacts/procmon-help-2026-09-10に保持（Git対象外）。この配布物の再取得は不要。
Procmon/help UI/driver/serviceの起動・設定変更・追加child・他プロジェクトへの操作なし。
開始空きRAM8.34 GiB→終了付近8.22 GiB、C102.24 GiB/D75.36 GiBは同値。リーク有無は未判定。
次は既存debugger停止条件を維持する観測と、条件変更を要する方式を比較する。全acceptance gate no。

## 46. 2026-09-10 既存停止条件を維持するunload時観測の設計

既存raw eventと公式仕様を照合し、debug通知中の停止区間で初期threadのcontextとRSPから最大2048 bytesを
各1回だけ取得する案を選んだ。最初のnormal UNLOAD_DLL限定で、別thread/通知なしは未観測として扱う。
追加breakpoint、Suspend/Resume、SetThreadContext、code/PEB/registry変更、監視toolは使わない。
取得失敗・短いread・資源停止では追加取得を止め、既存owned stopへ渡す。過去の実行承認は再利用しない。

公式説明はprocess終了時の自動unloadではUNLOAD_DLL通知を発生させないとしている。
ただし観測したunloadから原因APIやloader rollbackを断定しない。context/stackも通知時点の観測にとどめる。
詳細は[unload実行状態観測案](anomaly-multiseed-v0.3-s4-b1-unload-context-plan-2026-09-10.md)を参照。
独立設計レビュー新規P0〜P3=0。ローカルSDKのx64構造/flagsを照合したが、実装とABI試験は未実施。
次はaligned buffer、pending/identity/予算、1回制限、partial失敗、保存容量をfakeで実装検証する。

今回は文書とread-only code/SDK調査のみ。実child/native context/memory取得・権限変更・他project操作なし。
開始空きRAM8.77 GiB/C102.24 GiB/D75.36 GiB。全acceptance gate no。

## 47. 2026-09-10 最初のUNLOADでのcontext/stack観測実装

c4fe99eでDebugContextを実装し、driver/observer/evidence/preflightへ接続した。
事前確保した16-byte aligned x64 CONTEXTと2048-byte stackを使い、借用初期threadだけから各1回取得する。
対象外TID・不正identity/pending・部分read・OOM・中断を区別し、再試行せず既存停止へ引き渡す。
最初のnormal UNLOADだけで選択固定。breakpoint/EXIT/drain時の追加取得、補完open、code/権限変更はない。

保存枠は設計16 KiBから外枠込み8 KiBへ縮小。既存24 KiB画像/16 KiB security枠とmetadataを合わせた64 KiB容量試験を通過。
許可pure/fake243/243（1.425秒）、独立実装レビュー新規P0〜P3=0（指定46/46、0.801秒）。
容量試験条件強化後driver12/12（0.300秒）。repository safety/diff-check pass。
独立担当の完了通知を利用し、進捗ポーリングなし。

実read-only preflightは18 sources / 208782 bytes、verified、resource_stop=false。
Windows10.0.26200.9445、Python3.14.0、固定exe/DLL hash一致。実child/context/memory取得は追加実行していない。
実装中の空きRAM8.74 GiB/C102.31 GiB/D75.36 GiB。単発値でリーク有無を判断しない。
次の判断は[観測計画の具体条件](anomaly-multiseed-v0.3-s4-b1-unload-context-plan-2026-09-10.md)による実機診断1回。
従来の実行承認を新しい子メモリ取得へ拡張して使わない。全acceptance gate no。

## 48. 2026-09-10 context/stack付き承認済み実機診断1回

§47後の具体的1回実行確認へユーザーが「続けてください」と回答し、HEAD2b0dee1で1回実施した。
所要2.069秒、通常7 events/Continue7件、0xC0000142、breakpoint/exception等なし。
最初のUNLOAD slot4で初期threadのcontext1232 bytesとstack2048 bytesを取得confirmed。
RIP/RSPとraw context、event slot/TIDの一致も保存fileで照合した。call stackや失敗APIは未特定。

終了・debug所有解放・driver/stop teardown=pass、Terminate不要、drain0回。resource_stop=false。
最終結果を先に出す表示処理は正常動作し、Write/Flush確認とevidence file close=trueを記録できた。
保存114419 bytesは別工程のread-only読取りで実行時buffer hashと一致した。
SHA-256=c98e30a618e2933d5c206ec292e8dc4d3c5756f751c6cb541b0ea255ef0fb4fe。
詳細・限界は[context診断結果](anomaly-multiseed-v0.3-s4-b1-startup-context-probe-result-2026-09-10.md)を参照。

18 sources / 208782 bytes、Windows10.0.26200.9445、Python3.14.0と既存hash一致。
memory sampler64回、親＋child peak commit約23.65 MiB、working約33.09 MiB。
開始空きRAM8.57 GiB/C102.32 GiB/D75.36 GiB→照合後9.28 GiB/C102.31 GiB/D75.36 GiB。
PC全体の単発値でリーク有無は判定しない。権限/設定変更・他project操作・追加試行なし。
次は保存context/stackを解釈するためのimage identity/範囲/unwind情報の検証方法を検討する。全acceptance gate no。

## 49. 2026-09-10 保存RIPとntdll image範囲のoffline照合

保存証跡hash一致を確認し、現在のSystem32/ntdll.dllのvolume/file ID/normalized nameが保存image rowと一致した。
fixture向けのhardlink数1検査は変更せず、解析専用のread-only手順でhardlink2を記録した。
file infoのaccess time変化だけを別扱いとし、identity/size/write等は読取り前後で一致を確認した。
詳細な停止経緯と範囲検査は[context診断結果のRIP照合](anomaly-multiseed-v0.3-s4-b1-startup-context-probe-result-2026-09-10.md)を参照。

ntdllは2522080 bytes、SHA-256=a74f7482085eab125ccc09152ab7e0b5994bcb13e1a7b29880bdbb24179ecb8b。
保存RIPのRVA0x161304はexecutable section内で、RUNTIME_FUNCTION [0x1612f0,0x161308)、unwind RVA0x1b5630に対応。
同beginを指すexportはNtUnmapViewOfSection/ZwUnmapViewOfSection（+0x14）。元の失敗APIとは断定しない。
現在fileのbytesと実行時loaded bytesの完全一致は未証明として保持する。

次はUNWIND_INFOを確認し、保存CONTEXT/2 KiB stackの範囲内だけで呼出し元を復元できるかを調べる。
未対応の命令/chain/epilogueや保存範囲外では推測で補完しない。今回はunwind・symbol取得未実施。
追加child・remote read・code/権限設定変更・他project操作なし。全acceptance gate no。
開始空きRAM9.13 GiB/C102.31 GiB/D75.36 GiB。リーク有無は未判定。

## 50. 2026-09-10 保存stackから1段の呼出し元復元

保存証跡と現在ntdllを有界read-onlyで読み、既存hash・image identity一致を再確認した。
観測RIP0x161304の命令はRET、UNWIND_INFOはversion1/flags0/code0/prolog0。
保存RSP先頭8 bytesから復元した戻り先はntdll RVA0xa7956、関数範囲[0xa7914,0xa7962)。
直前RVA0xa7951のCALL rel32はtarget0x1612f0で、観測したNt/ZwUnmapViewOfSection beginと一致した。
現在imageを適用した条件付きの1段復元であり、loaded bytes完全一致・呼出し元の私有関数名・起動失敗原因は未確定。

詳細は[context診断結果の1段復元](anomaly-multiseed-v0.3-s4-b1-startup-context-probe-result-2026-09-10.md)を参照。
次frameのunwind情報（32-byte allocation/RBX保存に対応する形）を確認したが、2段目は未復元。
次はbody/epilogue判別・保存stack内offset・nonvolatile register・callsiteを検証し、対応できる範囲だけ進める。
追加child・remote memory・symbol取得・設定変更なし。文書のみのためtest/レビュー再実行なし。全acceptance gate no。
開始空きRAM8.80 GiB/C102.31 GiB/D75.36 GiB。リーク有無は未判定。

## 51. 2026-09-10 保存stackの限定複数段unwindと独立レビュー

実装保存commit: `1f8b300`。byte-only offline helperを実装し、保存2048-byte stackと現在ntdllを適用して2回のunwindを確認した。
観測RVA0x161304から呼出し元0xa7956、さらに0x17fdaへ復元し、両段の直前CALL targetが前frameの関数beginと一致した。
2段目はbodyの32-byte allocation/RBX保存を巻き戻し、戻り先をstack offset48から取得、次のRSP差分は56 bytes。
その先はunwind_flags_or_frame_registerで停止した。該当flags/frame registerの分類と3段目の復元は未実施。

helperはPE/命令境界/stack範囲/callsiteを検査し、version1/flags0/frame register0の限定bodyとbare RETだけを扱う。
source hashとntdll identityは再照合したが、当時loaded bytesの完全一致は未証明。関数名や起動失敗原因を断定しない。
詳しい範囲と結果は[context診断結果の複数段解析](anomaly-multiseed-v0.3-s4-b1-startup-context-probe-result-2026-09-10.md)を参照。

独立レビューP2 1件（命令operandの任意値出力）をmnemonicだけの出力に修正し、即値非出力の回帰試験を追加した。
再レビュー新規P0〜P3=0。Capstone5.0.7はoptional extraへ分離し、未導入時の任意offline試験skipも独立確認済み。
最終対象pure/fake12/12 pass（0.118秒）、未導入条件7件skip/discovery成功、repository safety/diff-check pass。
必須native試験の受入条件は変更なし。担当の完了通知を利用し、進捗ポーリングなし。

派生要約multi-unwind.jsonを保持し、operandを省いたmulti-unwind-reviewed.jsonを現在の参照要約とした（Git対象外）。
後者は元要約hashと変換内容を記録した表示修正であり、証跡取得/解析の再実行ではない。
空きRAM8.70→8.66 GiB、C102.31→102.30 GiB、D75.36 GiB。snapshotだけでリーク有無を判定しない。
追加child/remote memory/symbol取得/設定変更/他project操作なし。全acceptance gate no。
次は停止したentryのheaderを検証して未対応形式を分類し、保存範囲内で対応可能かを調べる。

## 52. 2026-09-10 限定offline解析を保存stack範囲まで進行

CHAININFO対応a647a7f、非SP宛てADD/LEAのbody判別68ea66e、handler metadata付きcontext復元b4ff9e7を保存した。
連結は最大8 records、pdata完全一致・循環/順序検査、secondary SAVE_NONVOL限定、CALL targetはprimary entryと照合する。
handlerはRVA範囲/entry検査のみで、codeやlanguage dataの解釈・実行なし。frame pointerや未対応形式での推測補完はしない。

保存2048-byte stackから観測frameを含む11 frames、呼出し元10段を復元し、10件すべての直前CALL targetを照合した。
途中の5段LEA停止と6段handler flag停止も分類・修正・再レビュー後に進めた。
最終frameはntdll RVA0x8dda6、[0x8c404,0x8e24a)、保存RSP差分1624 bytes。
次はsaved_stack_exhaustedで停止し、11回目のunwindは未成立。保存範囲外の追加memory取得は行っていない。
詳細な10段の表・制約・途中経過は[context診断結果の保存範囲解析](anomaly-multiseed-v0.3-s4-b1-startup-context-probe-result-2026-09-10.md)を参照。

最終pure/fake20/20 pass（ローカル0.122秒、独立0.125秒）、各差分の独立レビュー新規P0〜P3=0。
repository safety/diff-check pass。optional解析依存のみで、必須native試験の条件は変更なし。進捗ポーリングなし。
ntdllは段階的確認で計5回、既存証跡は適用時の計3回、有界read-onlyで読み、記録済みhash一致と全reader handle closeを確認した。
現在の参照要約はartifacts/context-offline-2026-09-10/handler-context-unwind.json。新規要約5件計16921 bytes、過去証跡は保持。
実行時loaded bytesの完全一致は未証明、私有関数名/元の失敗API/起動失敗原因は未特定。全acceptance gate no。

空きRAM8.94→9.02 GiB、C102.30 GiB/D75.36 GiBは同値。単発値からリーク有無は判定しない。
追加実child/remote memory/symbol download/設定変更/他project操作なし。
次は復元済み関数の役割を調べるsymbol資料について、imageとの同一性と有界な取得・保存方法を検討する。
これ以上のframe復元のために証跡採取を自動でやり直さない。新たな実機診断は既存の個別承認gateを維持する。

## 53. 2026-09-10 公開PDBと内部statusのoffline照合

実装保存: symbol照合3db6a98、検証済みframeのprivate register保持3e8d64d。
Microsoft公開PDB1912832 bytesを非圧縮16 MiB上限で1回取得し、現在ntdllのCodeView GUIDとDBI age/section headersを照合した。
Info age4/DBI age1/image age1はMicrosoftの検証規則で適合する。PDB hashと各ageを別々に記録した。
10個のprimary entryすべてにS_PUB32 Functionのexact一致があり、重複を含む11 framesに関数名を対応させた。
process初期化→Kernel32関連初期化→DLL読込み→module解放/unmapの呼出し経路だった。

LdrpLoadDllInternalの保存戻り先0x1ff1b近傍でCMP dword [RBX],0と解放処理へのCALLを確認した。
検証済みunwindから復元したRBXは保存stack offset584を指し、その4 bytesは0xC0000142だった。
EXIT_PROCESS値と一致したが、元の失敗API/DLLや、この値を最初に書いた命令は未特定。
比較命令が実行された過去時点の値・loaded bytesの完全一致は未証明。保存範囲外のpointer追跡なし。

詳しいsymbol表・取得条件・age規則・status解釈は[シンボルと内部statusの解析結果](anomaly-multiseed-v0.3-s4-b1-startup-symbol-analysis-2026-09-10.md)を参照。
最終pure/fake29/29 pass（0.125秒）、独立差分レビュー新規P0〜P3=0。repository safety/diff-check pass、進捗ポーリングなし。
公開PDBと新規要約は同じartifacts配下に保持済み。再download不要、元のprivate証跡も保持。
空きRAM8.69→8.78 GiB、C102.30→102.29 GiB、D75.36 GiB。リーク有無は未判定。
追加実child/remote memory/設定権限変更/他project操作なし。全acceptance gate no。
次は内部statusの静的な書込み候補と保存情報の限界を整理し、新規観測が必要なら具体化後に個別承認gateへ進める。

## 54. 2026-09-10 statusの生成・伝播候補と保存情報の限界

現在ntdllと保存PDBを再使用し、LoadDllInternal全277命令と関連する初期化関数の静的経路を確認した。
同関数の直接即値書込み0x20020は通常の関数内フローでEDI=9を必要とするが、保存frame0x1ff1bの復元EDIは9ではなかった。
現在imageとABIを前提に、この直接書込みを保存statusの生成元とする説明は整合しない。
コードの実行履歴を証明した除外ではなく、loaded bytes完全一致未証明の制約を維持する。

PrepareModuleForExecutionの戻り値をstatusに格納する箇所と、初期化処理/依存nodeの失敗状態から
0xC0000142を返す複数の候補を確認した。比較・ログを含む即値13件を、13個のstatus書込みとは数えない。
初期化callbackのfalseだけが原因とは断定せず、最初の失敗DLL/API・実行された生成箇所は未特定。
新しいunwind対応や範囲外memory読取りは追加していない。

詳細は[解析結果§5](anomaly-multiseed-v0.3-s4-b1-startup-symbol-analysis-2026-09-10.md#5-statusの静的な生成伝播候補2026-09-10追記)。
次工程は失敗対象と戻り値/失敗nodeの対応を得る観測の設計。同じstackだけの再採取では区別が増えるとは限らない。
現行の全breakpoint拒否との関係と追加取得範囲を明示し、実装・試験・レビュー後に個別の実機判断対象を提示する。
追加実child・memory書込み・breakpoint許可をこの文書や準備継続指示から読み替えない。

新規要約4件193708 bytesをignored artifactsへ保存。現在ntdllの有界read4回、保存証跡read1回、全reader handle close。
tracked変更は文書のみでtest再実行なし。追加download・設定権限変更・他project操作なし。全acceptance gate no。
公開要約の整合性/diff-check pass。文書と公開要約に限定した独立レビュー新規P0〜P3=0、private復元の再検証なし。
完了通知を利用し進捗ポーリングなし。mainは基準commitのままclean。
空きRAM8.85→8.85 GiB、C102.29 GiB/D75.36 GiB同値。リーク有無は未判定。

## 55. 2026-09-10 最初のunload対象の管理情報観測を準備

実装保存316abf5。[管理情報観測計画](anomaly-multiseed-v0.3-s4-b1-unload-entry-plan-2026-09-10.md)を次の実機判断対象とする。
保存RIP/stack戻り先/RDXとunload通知が一致し、RBXも復元済みDereferenceModule frameと一致した。
現在imageでは管理情報のbase消去と解放が観測位置の後にあるが、内容自体は既存stack保存範囲外だった。
node状態はunload中に書換わる経路があるため、今回nodeや名前pointerの追跡は追加しない。

DebugDriver(unload_entry=True)だけで有効になるcollectorを追加（既定off）。最初のnormal初期thread UNLOADのみ。
有効なimage load、RIP/戻り先/RDX、user範囲、code3 windowsのSHAを照合後、RBX先112 bytesを1回読む。
追加RPM最大4回/1059 bytes、従来stackを含めて最大5回/3107 bytes。既存GetThreadContextの追加繰返しなし。
entryのbase/sizeを照合し、[entry+0x68]の0x100000 bitとraw prefixをprivate保存する。
bitは参照imageで初期化失敗時に設定する印だが、callback戻り値・最初の失敗APIを直接観測したものとは扱わない。
全breakpoint拒否、書換えなし、API前後の所有/予算検査、失敗時停止と再試行抑止を維持する。

関連fake34/34、debug全体130/130 pass。独立レビュー新規P0〜P3=0、指定fake34/34 pass（0.540秒）。
source保存後の実read-only preflightは19 sources/215813 bytes、2.187秒、verified、resource_stop=false。
実測Windows10.0.26200.9445/Python3.14.0、既存exe/DLL hash一致。repository safety/diff-check pass。
context成功例最大幅7389 bytesで8 KiB内。19 sourceと各collector予約を含む全体64 KiB容量試験もpass。
ntdll3窓に参照PEのbase relocation重なりなし。実loaded bytesの3窓一致は次の実機時に別途確認する。

新規要約3件7430 bytes。参照image有界read4回/private証跡2回（初回集計のfield名誤り修正による再読取りを含む）、全reader close。
空きRAM8.61→9.02 GiB、C102.28 GiB/D75.36 GiB同値。リーク有無は未判定。
追加実child・実RPM/GetThreadContext・対象memory書換え・他project操作なし。mainは基準commitのままclean。
独立担当の進捗ポーリングなし。全acceptance gate no。

次は計画末尾の**追加memory読取りを含む限定実機診断1回**について判断を求める。
前回承認はその1回限りで、今回の取得を含まない。承認前にdriverを追加実行しない。

## 56. 2026-09-10 管理情報v1実機結果とサイズ前提の修正

ユーザーの「続けてください」を§55の限定診断1回への了承として、cleanなfb08c34で1回実行した。
初期reportまで2.214秒。追加1059 bytesの完全readとntdll3窓SHA一致、KernelBase.dllのbase一致を確認したが、
entry_image_sizeで停止した。v1はこの検査後にしかraw/size/flagsを保存しないため、その実値は未保存・未確定。
サイズが0だったか上限超過だったかを決めつけない。KernelBase.dllが初期化失敗したという断定もできない。

normal5件/observer Continue4件、owned stopがTerminateProcessを要求しdrain1件でEXIT code1。
今回の自然終了値は未観測。終了signal、debug ownership解消、handle close、teardown pass、failure_count0を確認した。
先行最終reportとprivate証跡write/flush/closeを確認。114763 bytes/hash36dcd18871234b76b5db32b7a258b7bf157a61f8ad3763cfbf4a9cff3a6b1a87。
保存fileの有界readbackはhash一致。保存stackの10段unwindからoffset584の内部status0xC0000142も再確認した。
詳しくは[管理情報v1実機結果](anomaly-multiseed-v0.3-s4-b1-unload-entry-result-2026-09-10.md)。

現在imageのUnloadNodeには、0x86815でサイズ[entry+0x40]を0にしてから解放する経路があった。
6 fragments/164命令のR15書込みも確認。「unload時でもサイズは正」という観測側の前提を修正する。
v2は0を許容し、完全read後のraw112/sizeをprivate保存してからfieldを検証する。不一致時はflags/bit未確定のまま停止。
追加4 reads/1059 bytes、同じcode3窓・base照合・128 MiB/user上限、既定off、全breakpoint拒否、再試行抑止は維持。
関係fake32/32、debug131/131 pass。独立新規P0〜P3=0、指定32/32 pass（0.478秒）、進捗ポーリングなし。
成功例最大幅JSON7418 bytes/8 KiB、全体64 KiB容量試験pass。repository safety/diff-check pass。

v1の同run preflightは19 sources/215813 bytes、Windows10.0.26200.9445/Python3.14.0、既存hash一致。
親＋child記録上peak commit約22.69 MiB、resource_stop=false。PC空きRAM8.68→8.38 GiB、C102.31→102.34 GiB、D75.36 GiB。
単発値からリーク有無は判断しない。追加権限/設定変更・他project操作なし。全acceptance gate no。
次はv2 source保存とread-only preflight後、[計画末尾のv2限定実機1回](anomaly-multiseed-v0.3-s4-b1-unload-entry-plan-2026-09-10.md)について判断を求める。
今回承認済みのv1は消化済み。v2の実child/実RPMはまだ行っていない。

v2修正保存3699d2e後のread-only preflightは19 sources/216179 bytes、2.256秒、verified、同じruntime/hash、resource_stop=false。
公開要約6件51469 bytesを保存。実行後の参照image有界read4回/今回証跡read2回、全reader close。
参照readには静的fragment境界の仮定誤りで停止した1回を含む。実childの追加再試行ではない。
mainは基準commitのままclean。v2で新規fixtureを使う実機診断1回について返答を待つ。

## 57. 2026-09-10 v2でKernelBaseの初期化失敗の印を観測

ユーザーの「続けてください」をv2限定診断1回への了承として、cleanなb0a81ee（実装3699d2e）で1回実行した。
初期reportまで2.365秒、driver/observer=observed、primary/secondaryなし、resource_stop=false。
ntdll3窓一致、追加1059 bytesの完全read、KernelBase.dllのLOAD/UNLOADとentry base一致を確認。
entry size=0、flags=0x38a28e、init_failure_bit=true、callback RVA0x5060を保存した。
v1の未保存値は未確定のまま。今回はnormal7/Continue7、drain0、自然EXIT0xC0000142、Terminate要求なし。
signal/ownership解消/所有handle close/teardown pass/failure_count0、先行reportと証跡write/flush/closeを確認した。
private115051 bytes/hash155215a8f0b1cb4d6dd69f29b3c2c401c3f0b741b5672b890acc69f71c23c325、保存fileの有界readback一致。

現在KernelBase.dllの保存image行とのidentity/name照合とPE entry0x5060一致を確認した。
公開PDB12521472 bytesを16 MiB上限で1件取得し、GUID/DBI age1/AMD64/section headersを既存matcherで照合。
Info age2/image age1の適合を確認し、entryにKernelBaseDllInitializeのexact公開symbol名が対応した。
通常reason1の静的経路は基本初期化のALを返す系統と、ARI::Globals::Initializeの負statusでfalseを返す系統に分かれる。
前者の分岐条件AL≠1をすべてfalseとは扱わない。どちらの実行履歴も、最初の失敗APIも未確定。

基本初期化にWORD RVA0x3aeea0の段階値100/200/400/500/600/700を発見したが、今回の取得対象外。
cleanup側の参照も確認した。全呼出し先を含む値の不変性とunmap時点での読取り可否は未証明。
この値だけで失敗APIが一意に分かるとは判断せず、追加実機を自動実行しない。
詳細な分岐表、hash、取得条件、保存物は[管理情報v2結果](anomaly-multiseed-v0.3-s4-b1-unload-entry-v2-result-2026-09-10.md)を参照。

同run preflightは19 sources/216179 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
親＋child peak commit約22.70 MiB、sample74回。PC空きRAM7.99→8.62 GiB、C102.09→101.93 GiB、D75.36 GiB。
単発値からリーク有無は未判定。Windows UpdateのUBR緩和・実測記録は維持した。
source変更なし、既存fake試験再実行なし。公開要約5件に限定した独立レビュー新規P0〜P3=0、進捗ポーリングなし。
公開要約7件104477 bytesとPDBを保存。要約値/段階値の書込み先/文書リンクを照合、repository safety/diff-check pass。
mainは基準889cfc3のままclean。
全acceptance gate no。v2の承認済み1回は消化済み。
次は全breakpoint拒否・書換えなしの条件内で、失敗後にも意味が残る値と観測位置を検討する。

## 58. 2026-09-10 初期化の戻り直前を観測する案を準備

UNLOAD通知のbaseから、解放済みDLL内の段階値を読める保証はないため、同じ位置の追加readだけを試す案は採用しない。
今回の候補はKernelBaseDllInitializeの共通return RVA0x50ba直前。
[限定観測計画](anomaly-multiseed-v0.3-s4-b1-init-return-plan-2026-09-10.md)に変更条件と上限を記録した。
DebugDriver(init_return=True)のみ、既定off、unload_entryとの同時使用不可。
LOADで固定code2窓2195 bytesを照合し、空のdebug slotを検査後、借用初期threadのSetThreadContext(DEBUG_REGISTERS)を1回だけ実施する設計。
再GetでDR0/DR7/DR6を照合してLOADを継続し、最初の一致したfirst-chance SINGLE_STEPでRIP/reason1/DR等を検査する。
ALとstage WORD2 bytesをprivate保存し、成功時もinit_return_observed_stopで既存owned stopへ進む。
通常の例外Continue/handled化やDR復元・再設定は行わず、TerminateProcess確認後だけpendingを解放する。
停止要求が失敗したらpendingと所有未解消を保持する。今回の停止EXITを自然終了とは扱わない。

追加取得はGetThreadContext最大3回、Set最大1回、RPM最大3回/2197 bytes。unload context/stack/entryは併用しない。
既存の30秒/256 events/512 MiB/空きdisk1 GiB、drain32/5秒、private証跡保持条件を維持する。
DLL code、一般register、RIP/EFLAGSは書換えないが、**debug register変更を含むので読取り専用ではない**。
この新しい設定変更は過去v2の1回承認に含まれず、実機診断は未実施のまま。

固定recipeは現在KernelBase hash一致、code2窓へのbase relocation重なりなし。
relocation表236492 bytes/117072 DIR64を有界解析した。初回64 KiB仮定で停止した分を含み、参照image read2回、reader close済み。
新規要約kernelbase-return-probe-recipe.jsonをignored artifactsへ保存。追加PDB download/過去private証跡readなし。
fake10/10（0.184秒）、debug＋preflight/event全体158/158（1.104秒）pass。
独立レビューは初回とDR6等の追加確認とも新規P0〜P3=0、最終指定fake10/10（0.197秒）pass。進捗ポーリングなし。
次はsource保存・read-only preflightを完了し、計画の限定実機1回を判断対象として提示する。全acceptance gate no。

実装保存5fc0276後のread-only preflightは2.293秒、20 sources/228061 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。init-return-preflight.jsonへ保存した。
repository safety/diff-check pass、mainは基準889cfc3のままclean。
PC空きRAM8.53→9.37 GiB、C105.06→105.04 GiB、D75.36 GiB。単発値からリーク有無は未判定。
準備は完了。新規fixture1回、debug register設定最大1回、取得最大2197 bytes、既存予算/owned stopの範囲について返答を待つ。
ユーザーがこの問いに「続けてください」と返答した場合は当該1回への了承として扱い、同じ了承を再確認しない。

## 59. 2026-09-10 return観測v1の実機停止と保存不足の修正

ユーザーの「続けてください」を§58の停止点設定を含む1回への了承として、cleanな029fb99で1回実行した。
初期reportまで2.085秒。LOADのcode2窓2195 bytes一致、初回Get・Set・2回目GetのAPI成功とflags検査通過を確認。
その後return_debug_registersで停止した。set_state=query_confirmed、設定内容検証は未成立。
元のDR0〜3/DR6/DR7はすべて0。一方、設定後の読み戻し値は検査後にしか保存しない実装だったため未保存・未確定。
DR6/DR7等のどれが不一致だったかを推測で補完しない。callback戻り値・stage値も未取得。

normal4/Continue3、owned stopのTerminateProcess確認後にpending LOADを解放、drain1件のEXIT code1をContinueした。
自然終了値は未観測。signal/ownership解消/所有handle close/teardown pass/failure_count0、先行reportと証跡write/flush/close確認済み。
private108274 bytes/hash1c6f865ff148e20d2deaf9e2f822cb70096ab32d5511393464407b870cc385cb、保存fileの有界readback1回で一致、reader close。
詳細は[return観測v1結果](anomaly-multiseed-v0.3-s4-b1-init-return-result-2026-09-10.md)。

v2はGet3回分の固定slotへAPI成功/post-budget後のdebug bytes/返却flagsを解釈前に保存する。
Set要求bytesと照合項目別bool、hitのcontextも保持し、取得と解釈を分ける。
API false/中断/資源停止を成功に補完しない。DR検査条件や追加取得上限/停止方法は変更なし、recipeのみreturn-v2へ。
関係fake11/11（0.223秒）、debug＋preflight/event159/159（1.229秒）pass。独立新規P0〜P3=0、指定11/11（0.213秒）pass。
担当の完了通知を利用し、進捗ポーリングなし。追加実機は行っていない。

同run preflightは20 sources/228061 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致、resource_stop=false。
親＋child peak commit約22.48 MiB、sample58回。PC空きRAM8.88→9.33 GiB、C105.81→105.82 GiB、D75.36 GiB。
単発値からリーク有無は未判定。追加DLL/PDB読取り・download・他project操作なし。全acceptance gate no。
次はv2保存とread-only preflight後、計画末尾の新規fixtureでの限定1回について判断を求める。v1承認は消化済み。
context/全metadata容量確認、repository safety/diff-check pass。mainは基準889cfc3のままclean。

v2修正保存e601921後のread-only preflightは1.951秒、20 sources/229087 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。init-return-v2-preflight.jsonに保存。
v2実機は未実施。新規fixture1回、Set最大1回/Get最大3回/RPM最大3回2197 bytes、同じ停止上限の範囲について返答を待つ。
この問いへの「続けてください」は当該v2の1回への了承として扱い、再確認せず実行する。

## 60. 2026-09-10 return観測v2でDR6のAPI返却表現を特定

ユーザーの「続けてください」をv2限定1回への了承として、cleanな0f19157（実装e601921）で新規fixture1回を実行した。
初期reportまで1.819秒。固定code2窓2195 bytes一致、Get2回/Set1回のAPI成功とflags一致を確認。
要求DR0=target/DR1〜3=0/DR6=0x10800/DR7=1に対し、返却はDR6だけ0、その他一致だった。
dr6_inactive_bits_setだけfalseで停止し、callback戻り値とstageは未取得。v1の未保存値は補完しない。
通常4 events/Continue3、Terminate要求確認後にpending LOADを解放、drain1件EXIT code1をContinueした。自然終了は未観測。
signal/ownership解消/所有handle close/teardown pass/failure_count0、先行reportと証跡write/flush/close確認済み。
private108952 bytes/hash27cd3c147d687b6c8ff5655476837402c49219c17739b7fa4368da1794b87103、有界readback1回で一致、reader close。
詳細は[return観測v2結果](anomaly-multiseed-v0.3-s4-b1-init-return-v2-result-2026-09-10.md)。

v3はCONTEXT.Dr6をCPU生registerと同一視する前提を修正し、B0〜3/BD/BS/BTのmask0xe00fでarm0/hit1を検査する。
baseline差分も同じmaskで比較し、全返却bytesを保持。BLD/RTM/reservedのAPI表現からhardware状態を推定しない。
最初の例外、DR0/DR7/初期thread/first-chance/address/RIP/reason1/TF=0を維持し、他の報告された標準causeは拒否する。
複合した例外原因の不存在を証明したとは扱わない。Set要求bytes/回数、RPM最大2197 bytes、通常Continueせずowned stopで終了する条件は不変。
関係fake12/12（0.349秒）、debug＋preflight/event160/160（1.470秒）pass。v3実機は未実施。

同run preflightは20 sources/229087 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致、resource_stop=false。
親＋child peak commit約22.33 MiB、sample58回。PC空きRAM8.46→9.36 GiB、C105.72→105.71 GiB、D75.36 GiB。
単発値からリーク有無は未判定。新規公開要約2件、追加DLL/PDB読取り・download・他project操作なし。全acceptance gate no。
次はv3の独立確認・保存・preflightを完了し、同じ上限で新規fixture1回の判断を求める。v2承認は消化済み。

独立差分レビュー新規P0〜P3=0、指定fake12/12（0.377秒）pass。API表現とhardware状態の区別を維持する。
担当の完了通知を利用し進捗ポーリングなし。独立担当はnative実行/private証跡参照を行っていない。


v3修正・試験・v2結果を2127527に保存。保存後read-only preflightは2.178秒、20 sources/229453 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。init-return-v3-preflight.jsonへ保存した。
今回のpreflightによるchild起動・SetThreadContextなし、全acceptance gate no。repository safety/diff-check pass、mainは基準889cfc3のままclean。
保存時のPC空きRAM9.97 GiB、C105.23 GiB、D75.36 GiB。単発値からリーク有無は未判定。

v3準備は完了。v2の1回承認は消化済みで、同じ上限（Get最大3/Set最大1/RPM最大3回2197 bytes）の新規fixture1回について返答を待つ。
この問いへの「続けてください」は当該v3の1回への了承として扱い、再確認せず実行する。失敗しても自動再試行しない。


## 61. 2026-09-10 return観測v3でAL=0・stage=600を取得

ユーザーの「お願いします。上限もう少し上げても大丈夫かと」をv3限定1回への了承として、cleanなa7cf252（実装2127527）で実施。
上限の小幅拡大を許容する意向は記録するが、今回上限不足ではないためGet3/Set1/RPM3回2197 bytes等は据え置いた。
初期reportまで1.795秒、resource_stop=false。collector completed/confirmed、primary=init_return_observed_stopによる意図的終了。
初期threadのfirst-chance SINGLE_STEP、RIP RVA0x50ba、reason1、AL0、WORD RVA0x3aeea0=600、TF0を確認。
code2窓2195 bytes一致。DR6は設定後0、hit時0xffff0ff1、DR7は1→0x401。v3のcause/地点等の条件がすべて一致した。

通常5/Continue4。例外を通常Continueせず、Terminate確認後pendingを解放、drain1件EXIT1をContinueした。
実RETと自然終了は未観測。signal/ownership解消/所有handle close/teardown pass/failure_count0。
private111847 bytes/hash147926b48ab9dee968f965bed545848b899b138d3dfcae502d5ce42796499879、write/flush/close確認済み。
有界readback1回でhash、raw events/context、AL/stage等を照合、reader close。
詳細は[return観測v3結果](anomaly-multiseed-v0.3-s4-b1-init-return-v3-result-2026-09-10.md)。

静的な600書込み→ConsoleInitialize CALL→AL0なら700を書かず戻る経路と整合し、ConsoleInitializeのfalse戻りが有力。
ただし呼出先等によるstage全書込み、異常制御移動、非介入時との同一性は未証明。ARI側を完全除外せず、API/statusも未確定。
独立確認は公開4件のみ、新規P0〜P3=0。進捗ポーリングなし、追加実行/試験なし。

現在KernelBase.dllの有界同一handle read1回、既存hashとclose確認。既存PDBのみ参照、追加downloadなし。
ConsoleInitialize [0xbeb60,0xbedaa)の139命令を静的解析し、RtlInitializeCriticalSection、ConsoleAllocate、
ConsoleCreateConnectionObject、ConsoleSanitizeStandardIoObjectsの失敗分岐候補を記録した。
ConsoleCreateConnectionObjectの負statusはlowbox条件により回復できるため、途中の負statusを最終原因と即断しない。

同run preflightは20 sources/229453 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
親＋child peak commit23420928 bytes（約22.34 MiB）、sample72回。実行前空きRAM9.90 GiB/C108.22 GiB/D75.36 GiB。
単発値からリーク有無は未判定。全acceptance gate no、他project操作なし、既存fixture・証跡は保持。

次は内部の4候補を区別する最小の診断を設計・模擬検証する。最初の失敗候補で通常Continueせず止める方式を検討する。
候補地点は0xbecc2/0xbecaf/0xbed34/0xbed9cだが、共有出口と回復可能な経路、呼出元確認、debug slots/取得上限を具体化する必要がある。
新方式は案のみで実装・実機設定・承認依頼は未実施。v3の承認済み1回は消化済みで、自動再試行しない。

保存前の空きRAM9.61 GiB、C108.21 GiB、D75.36 GiB。repository safety/diff-check pass、mainは基準889cfc3のままclean。


## 62. 2026-09-10 ConsoleInitializeの失敗候補を区別する診断を準備

[限定診断計画](anomaly-multiseed-v0.3-s4-b1-console-failure-plan-2026-09-10.md)を実装した。
DebugDriver(console_failure=True)のみ、既定off、unload_entry/init_returnとの同時使用は拒否。
DR0〜3に0xbecc2/0xbecaf/0xbed34/0xbed9cを設定するSetThreadContext1回、DR7 local enable0x55。
全4地点・DR7・標準cause clearを設定後Getで確認する。最初の例外だけを選び、対応する単一B0〜3、RIP/thread/flags/TFを検査する。
code2窓2422 bytesをLOADで照合し、hitでRSP16-byte整列/RBP=RSP+0x70/user範囲を確認する。
RSP+0x88のcaller8 bytesがbase+0x4ebe6に一致するときだけstage2 bytesへ進み、stage600/EAX負値を確認。
Get返却・CONTEXT・caller/stage生bytesを解釈前にprivate保存し、取得値と候補分類を分ける。
共有出口は先行監視地点を通過していない前提付き。connectionの負statusは回復可能で、根本原因や最終失敗とは断定しない。

Get最大3/Set最大1/RPM最大4回2432 bytes。従来2197 bytesから235 bytesだけ増。
ユーザーの上限小幅拡大の意向に沿い、時間/memory/diskや設定API回数は据え置いた。
既存scratch・contextを再利用し、pointer追跡・追加handle取得なし。
観測成立後もconsole_failure_observed_stopでowned stopへ進み、通常Continue・handled化・DR復元・再設定・自動再試行なし。
Terminate確認後のみpendingを解放。停止失敗なら未解消の所有とpendingを保持する。

現在KernelBase.dllの有界同一handle read1回、既存hashとclose確認。今回PDB読取り/download・過去private証跡参照なし。
code2窓と4命令、frame関係を照合、relocation236492 bytes/117072 DIR64にcode窓との重なりなし。
kernelbase-console-probe-recipe.jsonをignored artifactsに保存した。

関係fake11/11（0.442秒）、全体171/171（1.762秒）pass。初回のhelperオプション受渡し不足を修正済み。
独立新規P0〜P3=0、指定11/11（0.475秒）pass。担当の完了通知を利用し、進捗ポーリングなし。
21 sourcesと全collector予約枠のmetadata容量確認もpass。native実行・private証跡参照を担当へ委譲していない。
repository safety/diff-check pass、mainは基準889cfc3のままclean。
PC空きRAM9.46→9.76 GiB、C108.21→108.20 GiB、D75.36 GiB。単発値からリーク有無は未判定。他project操作なし。

次は保存後のread-only preflightを実施し、準備が整った新規fixtureでの限定1回を判断対象として提示する。
今回の新方式は実機未実施。v3の1回承認は消化済み、全acceptance gate no。


実装・試験・計画を78617f2に保存。保存後read-only preflightは1.939秒、21 sources/238228 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。console-failure-preflight.jsonへ保存。
preflightによるchild起動・SetThreadContextなし、全acceptance gate no。準備は完了。

4地点の設定最大1回、Get最大3回、RPM最大4回2432 bytes、同じ時間/memory/disk/owned stop上限の新規fixture1回について返答を待つ。
この問いへの「続けてください」は当該console_failure v1の1回への了承として扱い、再確認せず実行する。失敗しても自動再試行しない。


## 63. 2026-09-10 コンソール確保候補のアクセス拒否とDETACHED比較準備

ユーザーの「続けてください」を4地点の限定1回への了承として、cleanな67ad5ae（実装78617f2）で1回実行した。
初期reportまで1.870秒、resource_stop=false、collector completed/confirmed、primary=console_failure_observed_stop。
DR1/RVA0xbecafでEAX下位32 bits=C0000022、caller=0x4ebe6、stage600、TF0、初期threadを確認。
固定code2窓2422 bytes一致、Get3/Set1/RPM4回2432 bytes。
DR6は設定後0/hit0xffff0ff2、DR7は0x55→0x455。全4地点・B1のみ等の検査が一致した。

通常5/Continue4、Terminate確認後にpendingを解放、drain1件EXIT1をContinueした。実RET/自然終了は未観測。
signal/ownership解消/所有handle close/teardown pass/failure_count0、secondaryなし。
private112171 bytes/hash3430591eddf072ac619aa18c1a5102abf5ad22129d07cc0227fe32f83d74a812、write/flush/close確認済み。
有界readback1回でhashとraw events/CONTEXT/DR/caller/stage/statusを照合、reader close。
詳細は[console失敗候補結果](anomaly-multiseed-v0.3-s4-b1-console-failure-result-2026-09-10.md)。

C0000022はMicrosoft定義でSTATUS_ACCESS_DENIED。静的なConsoleAllocate後の負分岐と整合する。
共有出口と初回例外の前提を維持し、内部API/object/ACLや根本原因の確定とは区別する。
現在KernelBase.dllの有界同一handle read1回と既存PDB参照で、ConsoleAllocate214命令/ConsoleShouldAllocateConsole40命令を追加解析。
既存image hashとclose確認、追加downloadなし。内部にも複数の失敗候補があり、拒否されたCALLは未特定。
公開要約2件とkernelbase-console-allocation-static.jsonをignored artifactsに保存。

次の[比較診断](anomaly-multiseed-v0.3-s4-b1-detached-return-plan-2026-09-10.md)はDebugDriver(init_return=True, detached_console=True)のみ。
診断launchのNO_WINDOWをDETACHEDへ置換し、flags0x08000406→0x40e。bool検査、init_return以外との併用拒否。
token/ACL、非継承、desktop、固定child/environment、core通常launchは維持する。
実際の起動要求flagsとcreation_stateをprivate証跡へ保存し、過去の記録には補完しない。
既存return-v3でAL/stageを比較する。AL1/stage700でも実RET前の値であり、E2Eや原因確定とは扱わない。
Get3/Set1/RPM3回2197 bytes、同じ時間/memory/disk上限、通常Continueせずowned stop。比較実機は未実施。

関係fake46/46（0.874秒）、全体173/173（1.762秒）pass。独立新規P0〜P3=0、指定46/46（0.824秒）pass。
担当の完了通知のみを利用し、進捗ポーリングなし。native/private参照/source変更を委譲していない。
同run preflightは21 sources/238228 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
native親＋child peak commit24358912 bytes（約23.23 MiB）、sample74回。
PC空きRAM9.23→8.88 GiB、C108.21 GiB、D75.36 GiB。単発値からリーク有無は未判定。
repository safety/diff-check pass、mainは基準889cfc3のままclean。他project操作なし、全acceptance gate no。

次は比較修正を保存してread-only preflightを行い、新規fixtureでの限定1回を判断対象として提示する。
console_failure v1の承認済み1回は消化済み。追加の実機起動なし。


実装・試験・結果・計画をeaacd30に保存。保存後read-only preflightは1.943秒、21 sources/239171 bytes、verified、resource_stop=false。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。detached-return-preflight.jsonへ保存した。
preflightによるchild起動・SetThreadContextなし、全acceptance gate no。比較の準備は完了。

DETACHED指定、既存return観測Get最大3/Set最大1/RPM最大3回2197 bytes、同じ時間/memory/disk上限の新規fixture1回について返答を待つ。
この問いへの「続けてください」は当該比較の1回への了承として扱い、再確認せず実行する。失敗しても自動再試行しない。


## 64. 2026-09-10 DETACHED比較で成功側の値を観測し、通常child確認を準備

ユーザーの「続けてください」を比較1回への了承として、cleanな1e04198（実装eaacd30）で新規fixture1回を実行した。
初期reportまで1.990秒、resource_stop=false、collector completed/confirmed、primary=init_return_observed_stop。
起動要求flags0x40e/creation_state=created、RIP RVA0x50ba、reason1/TF0、AL1/stage700を確認。
従来NO_WINDOWのAL0/stage600との対照であるが、単発比較・RET前の観測であり、実復帰やPython起動/E2E成功を意味しない。
固定code2窓2195 bytes一致、Get3/Set1/RPM3回2197 bytes。DR6/DR7等の照合も一致。

通常5/Continue4、Terminate確認後pendingを解放、drain1件EXIT1をContinueした。自然終了は未観測。
signal/ownership解消/所有handle close/teardown pass/failure_count0、secondaryなし。
private112070 bytes/hasha6c04ef33df6b6fc2a73c2b1e20612436188b4bad115c186c72bcb8e6e94d37e、write/flush/close確認済み。
有界readback1回でhash・raw events/CONTEXT/DR/RIP/reason/AL/stage/launch flagsを照合、reader close。
詳細は[DETACHED比較結果](anomaly-multiseed-v0.3-s4-b1-detached-return-result-2026-09-10.md)。

同run preflightは21 sources/239171 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
親＋child peak commit24428544 bytes（約23.30 MiB）、sample72回。
PC空きRAM7.81→8.32 GiB、C107.93→107.94 GiB、D75.36 GiB。単発値からリーク有無は未判定。
追加DLL/PDB読取り/downloadなし、既存fixture/証跡保持、他project操作なし。

次の[通常child E2E計画](anomaly-multiseed-v0.3-s4-b1-detached-control-plan-2026-09-10.md)に向け、
core _startのNO_WINDOWをDETACHEDに置換（0x08000404→0x40c）した。
制限token・非継承・標準handle未設定・固定child/environment・suspended作成は維持し、debug APIは使わない。
関係pure61/61（0.215秒）、全体pure/fake234/234（2.074秒）pass。
独立新規P0〜P3=0、指定pure61/61（0.173秒）pass。担当の完了通知のみ、進捗ポーリングなし。

通常controlは新規fixtureだけで実child操作/拒否・report/traceを検査し、成功時のみexact-ledger cleanupまで進む。
child wait30秒/親＋child512 MiBは既存条件。30秒を準備・cleanupまで含む全体の厳密上限とは扱わない。
実行前read-only preflight/空きdisk1 GiBを確認する。wrapperはharness1回、最終report先行、
資源停止後の追加保存/hash/走査抑止、公開resultとprivate証跡の長さ/hashだけを保存する。
private rawを一般log/fileへexportせず、memory内private snapshotを永続保存したとは扱わない。
wrapper detached-control-once.pyはignored artifactsに準備した。3526 bytes / SHA-256 cae6a4ee47236fbfd8a9d024204105e5b4484e91b3154033ce2af18821f04c48。
repository safety/diff-check pass、mainは基準889cfc3のままclean。通常control実機は未実施。

次はcore修正を保存してread-only preflightを行い、新規fixtureの通常control1回を判断対象として提示する。
前回のreturn比較1回は消化済み。S4/native受入・formal/B2/publisher・main統合は未達。


core修正・試験・結果・計画をab147d5へ保存した。保存後read-only preflightは1.788秒、
21 sources/239293 bytes、verified、resource_stop=false、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
detached-control-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

通常controlの準備は完了。新規fixture内の固定child操作・拒否確認・report/trace照合・成功時exact-ledger cleanupまで、
既存child wait30秒/親＋child512 MiB条件の1回について返答を待つ。§6の追加probeの条件を引き継ぐ。
この問いへの「続けてください」は当該通常control1回への了承として扱い、再確認せず実行する。失敗時の自動再試行なし。


## 65. 2026-09-10 DETACHED通常childは初期化失敗、最初のUNLOAD観測を準備

ユーザーの「お願いします」を§64の通常control1回への了承として、cleanな6d1466a（core修正ab147d5）で1回実行した。
準備wrapper3526 bytes/hashcae6a4ee47236fbfd8a9d024204105e5b4484e91b3154033ce2af18821f04c48を照合。
status=failed/reason=child_failed/child_exit=0xC0000142、control failed、cleanup not_started、teardown pass、resource_stop=false。
core elapsed0.3133907秒、wrapper全体2.407秒。置換trace0 records/0 bytes、private_control=null、private_replace空bytes。
失敗fixtureを保持し存在確認/走査/repair/削除しない。詳細は[通常child結果](anomaly-multiseed-v0.3-s4-b1-detached-control-result-2026-09-10.md)。

公開要約2016 bytes/hashb41de63f393c01b02d4f492cb46d7bea2957cb8319147b663f43c80d7d4a40c4を1回有界readで照合。
完全control証拠を取得・保存したとは扱わない。native test classではなく同じharnessの直接1回実行である。
同run preflight21 sources/239293 bytes、verified、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
親＋child peak private23097344 bytes（22.03 MiB）、peak working32804864 bytes（31.29 MiB）。
PC空きRAM7.66→7.80 GiB、C107.93/D75.36 GiB。リーク有無は単発値から未判定。他project操作なし。

前回のdebug0x40eでAL1/stage700はRET直前の観測で、今回の非debug0x40cでのE2E成功を意味しない。
今回の失敗DLL/内部APIは未特定で、debugger有無等の因果関係も未確定。
coreのDETACHED候補は隔離保存のまま、修正完了/本流統合可能とは扱わない。

次の[DETACHED UNLOAD計画](anomaly-multiseed-v0.3-s4-b1-detached-unload-plan-2026-09-10.md)を準備する。
DebugDriverのdetached_consoleを既存unload_entryでも使えるようにし、最初の通常UNLOADで
既存Get1/stack2048 bytes＋code947/entry112 bytes（RPM最大5回3107 bytes）を取得する。
collector自体のcode/RVA/hash/解釈、token/ACL、core、停止・資源予算は変更しない。
Setなし、breakpoint拒否、必要時owned stop、診断fixture保持。追加実機は未実施。
関係fake44/44（1.136秒）pass。次は全体回帰・独立レビュー・保存後preflightで準備を完成する。
通常controlの了承済み1回は消化済み。S4/native受入・formal/B2/publisher・main統合は未達。


次の診断準備の初回独立レビューでP2=1を検出した。既存write_summaryが詳細構築MemoryErrorを通常失敗として捕捉し、
その後のreport/hash/file保存を続けられる問題で、今回の実機で資源停止したという意味ではない。
MemoryErrorをownerへlatchして再送出し、先行flush済みの最終行を残して後続処理を止める修正を追加した。
画像要約/hash/JSON構築のOOM注入回帰を追加し、関係fake49/49（0.929秒）pass。
変更したreport sourceをpreflightにも追加した。次は22 sourcesを照合する。wrapperのbyte/hashは不変、追加実機なし。


最終pure/fake235/235（2.719秒）、repository safety/diff-check pass。
独立P2は是正確認済み、追加差分の新規P0〜P3=0、report fake5/5（0.001秒）pass。
完了通知だけを利用し進捗ポーリングなし。担当のnative/private操作なし。
最終空きRAM7.74 GiB、C107.92/D75.36 GiB。本流889cfc3 clean、追加実機なし。
次は保存後read-only preflightを行い、DETACHED指定の最初のUNLOAD観測1回を提示する。


修正・試験・結果・計画を021956cへ保存した。保存後read-only preflightは2.028秒、
22 sources/242703 bytes、verified、resource_stop=false、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
detached-unload-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

準備は完了。次はDETACHED指定の最初の通常UNLOADを、新規fixture1個/Get最大1/RPM最大5回3107 bytes/Setなし、
既存時間・memory・disk・owned stop条件で1回だけ実施することへの返答を待つ。§6の追加probeの条件を引き継ぐ。
この問いへの「続けてください」は当該1回への了承として扱い、同じ了承を再確認せず実行する。自動再試行なし。
実行wrapper detached-unload-once.pyは2427 bytes/hashb8ce387f512c150804a6e4de9b6c596f2f5bc063eee7f3e004d4f83a0c8112a7。


## 66. 2026-09-10 DETACHED診断は初期停止点候補まで進み、検証付き継続を準備

ユーザーの「お願いします」を§65の1回への了承として、cleanなaf3a0b2（実装021956c）で新規fixture1回を実行。
初期reportまで2.168秒、primary=bootstrap_unverified、driver/observer failed、resource_stop=false、secondaryなし。
起動要求0x40e、通常18/Continue17、python.exe＋13 DLL load、3 create_thread、slot17で初期threadのfirst-chance BREAKPOINT。
UNLOAD未観測、context ready/not_observed、entry not_started、Get/RPM/Set各0。自然EXIT未観測。
owned termination後pendingを解放し、drain4件（thread exit3/process exit1、全code1）をContinue。
signal/ownership解消/所有handle close/teardown pass/failure_count0/driver teardown failures0を確認。
今回のcode1を自然な失敗理由とは扱わない。詳細は[DETACHED UNLOAD結果](anomaly-multiseed-v0.3-s4-b1-detached-unload-result-2026-09-10.md)。

private110163 bytes/hash051289d145635778ec9073fc44440694ffc110304af6442d770b2d427ff99cfb、write/flush/close確認済み。
有界private read1回で全events/launch/stop/hashを照合。設計レビューでparameter契約の確認が必要となり、
同じ証跡を追加1回読みparameter[0]=0を確認（計2回、各reader close）。child再実行なし。
例外80000003/first_chance1/flags0/chained null/parameters1、初期PID/TID一致、ntdll RVA122239。
現在ntdllの有界同一handle read1回/hash既存一致と既存PDB照合で、LdrpDoDebuggerBreakのint3に対応することを確認。
関数62 bytes、caller候補3件とRSP+38の静的根拠をntdll-bootstrap-static.jsonに保存。追加downloadなし。

同run preflight22 sources/242703 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory125 samples/親＋child peak commit26464256 bytes（25.24 MiB）、peak working35581952 bytes（33.93 MiB）。
実行前空きRAM8.44 GiB、C107.92/D75.36 GiB。単発値からリーク有無未判定。他project操作なし。

次の[初期停止点照合と継続計画](anomaly-multiseed-v0.3-s4-b1-bootstrap-unload-plan-2026-09-10.md)は、
DETACHED+unload専用のbootstrap=Trueで固定地点の最初の例外を検証し、同じpendingだけ1回DBG_CONTINUEする候補。
追加Get1/RPM3回75 bytes、RIP=address+1/TF0/RSP整列、固定code hash/caller/CALL/parameter0を照合する。
RIP条件は未測定の候補で、一致しなければ補完せず停止。選択/消費/不確定/継続確認を分け、drainへ許可を渡さない。
以後は既存unload collector、合計Get2/RPM8回3182 bytes。Setやtarget書換えなし。
追加metadata4 KiBを保持するためmetadata64→72 KiB（buffer163864 bytes）へ小幅拡大、process512 MiB条件は維持。
新sourceを含む23 sourcesを照合する。設計独立点検は新規P0〜P3=0、関係fake75/75（1.608秒）pass。
全体回帰・独立実装レビュー・保存後preflightで準備を完成する。今回了承された1回は消化済み。


全体pure/fake245/245（3.558秒）、repository safety/diff-check pass。
独立実装レビュー新規P0〜P3=0、指定fake75/75（1.790秒）pass。担当のnative/private/source変更なし。
完了通知のみを利用し進捗ポーリングなし。作業後RAM8.06 GiB、C107.92/D75.36 GiB。
次は候補を保存してread-only preflightを行い、検証に一致した停止点だけを継続する診断1回を提示する。


実装・試験・結果・計画を4c964c8へ保存した。保存後read-only preflightは2.270秒、23 sources/255021 bytes、
verified、resource_stop=false、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
bootstrap-unload-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

準備は完了。固定初期停止点が検証できた場合だけ1回継続し、以後の最初のUNLOAD/終了まで観測する、
新規fixture診断1回への返答を待つ。合計Get2/RPM8回3182 bytes/Setなし、既存時間・memory・disk・owned stop条件。
この問いへの「続けてください」は当該1回への了承として扱い、同じ了承を再確認せず実行する。自動再試行なし。
実行wrapper bootstrap-unload-once.pyは2768 bytes/hash01f6e8074f8bfc1657b2b0eed4c02b5f4bf4a35ae37ed88a754442e7e4d6350b。


## 67. 2026-09-10 bootstrap継続後の自然初期化失敗を観測し、失敗地点の取得を準備

ユーザーの「お願いします」を§66の1回への了承として、cleanなca6a6da（実装4c964c8）で新規fixture1回を実行。
初期reportまで2.376秒、driver/observer observed、primary/secondaryなし、resource_stop=false。
要求flags0x40e、通常22/Continue22、初期停止点slot17を検証して通常継続、slot18〜21のthread3/process1 exitはC0000142。
UNLOADなし、entry未取得。診断observedをchild E2E成功とは扱わず、失敗DLL/内部APIは未特定。

bootstrapは初期PID/TID・例外metadata/parameter0・ntdll寿命・code hash一致、
実Get RIP12223a/TF0/RSP整列、caller8df44/CALL一致。Get1/RPM3回75 bytes、continue confirmed。
Terminateなし/drain0、signal/ownership解消/所有handle close/teardown pass/failure_count0、driver teardown failures0。
private113291 bytes/hashc5aae2427953ccc3d1545fecf6a2e33e7c0d41818f022a8f99cbb3a9185c46d2、write/flush/close確認済み。
有界held-file read1回でraw全events/CONTEXT/code/caller/launch/stop/hashを照合しreader close。
詳細は[bootstrap継続結果](anomaly-multiseed-v0.3-s4-b1-bootstrap-unload-result-2026-09-10.md)。

同run preflight23 sources/255021 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory153 samples/親＋child peak commit27140096 bytes（25.88 MiB）、peak working36941824 bytes（35.23 MiB）。
実行前RAM7.48 GiB、C107.92/D75.36 GiB。単発値からリーク有無未判定。他project操作なし。
既存静的JSONから次のcode845 bytesとe86e命令を照合し、init-failure-probe-recipe.jsonに保存。追加DLL/PDB read/downloadなし。

次の[初期化失敗地点計画](anomaly-multiseed-v0.3-s4-b1-init-failure-plan-2026-09-10.md)は、
検証済みbootstrapのpendingでntdll e86eをDR0に1回設定し、hitでR14D=C0000142/R12B=0と
RDI entry112 bytes、module LOAD寿命/entrypoint=R15等を照合してDLL候補を記録する。
flagsは失敗bit書込み前の値であり、callback FALSEだけでなく例外経路も対象となり得る。
bootstrap込みGet4/Set1/RPM5回1032 bytes、同じ時間/memory/disk/metadata上限。hitは通常継続せずowned stop。
既定off/DETACHED+bootstrap必須/他collectorと排他、任意addressなし、再arm/再選択/既存fixture cleanupなし。

既存returnのdebug-register設定部分を共通methodとして再利用し、既存return/bootstrapも回帰した。
独立設計点検は新規P0〜P3=0、関係fake41/41（1.891秒）pass。
次は全体回帰・独立実装レビュー・保存後preflightを完了する。今回の了承済み1回は消化済み。


全体pure/fake252/252（5.164秒）、repository safety/diff-check pass。
独立実装レビューは新規P0〜P3=0、指定fake41/41（2.924秒）pass。担当のnative/private/source変更なし。
完了通知のみ、進捗ポーリングなし。作業後RAM8.26 GiB、C107.92/D75.36 GiB。本流889cfc3 clean。
次はsource保存後read-only preflightで準備を完了し、固定失敗地点の設定/取得を新規fixtureで1回行う範囲を提示する。


実装・試験・結果・計画を0b19750へ保存した。保存後read-only preflightは2.403秒、24 sources/262701 bytes、
verified、resource_stop=false、primary/secondaryなし、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
init-failure-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

準備は完了。検証済みbootstrapから固定失敗地点を設定し、DLL候補情報を取得して所有終了処理まで行う、
新規fixture診断1回への返答を待つ。bootstrap込みGet4/Set1/RPM5回1032 bytes、既存時間・memory・disk・終了処理条件。
この問いへの「お願いします」「続けてください」は当該1回への了承として扱い、同じ了承を再確認せず実行する。
実行wrapper init-failure-once.pyは2736 bytes/hash2de5eb72f155257271d3c7aa638abc2373713dbe6e8a9e6010bbc0e72fc408c2、未実行。
§6の追加probe条件を引き継ぎ、自動再試行なし。今回のbootstrap/unload観測1回への了承は消化済み。


## 68. 2026-09-10 初期化失敗候補はbcrypt.dll、内部の4経路を一度に調べる準備

ユーザーの「お願いします」を§67の1回への了承として、cleanなa76439b（実装0b19750）で新規fixture1回を実行。
初期reportまで2.175秒、primary=init_failure_observed_stop、driver/observer failed、
context completed/status confirmed、Set verified、secondaryなし、resource_stop=false。
要求flags0x40e、通常19/Continue18、slot17 bootstrapを検証して継続、slot18で初期threadのntdll e86eにhit。
R14D=C0000142/R12B=0、112 bytesのentryとconfirmed LOAD slot16からbcrypt.dllを候補として取得。
SizeOfImage172032、callback RVA11140、flags2ca2ec（失敗bit書込み前）。
callback FALSEや例外経路の別、特定API/根本原因は未判定。観測をchild E2E成功とは扱わない。

bootstrap込みGet4/Set1/RPM5回1032 bytes。DR6 arm0/hitffff0ff1、DR7 arm1/hit401、各code/register/load照合。
hitを通常Continueせずowned terminate→pending解放→drain4（thread3/process1、全code1）をContinue。
signal/ownership解消/owned handles close/teardown pass/failure_count0/driver teardown failures0。
自然EXIT未観測、code1は意図した終了処理の結果。fixture保持は存在unverified、cleanup/repairなし。

private117499 bytes/hash494901a58011faa315f03acd029bfe0d3cacb8f91077f8df1c8191eb03d2621a、
write/flush/file close確認済み。有界held-file read1回でevents/bootstrap/debug CONTEXT/entry/LOAD/launch/stop/hashを照合しreader close。
全inflight false、未確定buffer領域zero。詳細は[初期化失敗地点の結果](anomaly-multiseed-v0.3-s4-b1-init-failure-result-2026-09-10.md)。

同run preflight24 sources/262701 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory167 samples、親＋child peak commit26488832（25.26 MiB）/working36392960（34.71 MiB）。
作業前後RAM7.71→8.55 GiB、C107.91→107.98/D75.36 GiB。last boot2026-09-09T10:43:08.5000000+09:00。
UBR緩和を維持し状態として記録する。単発値からリーク有無は未判定。他project操作なし。

現在bcrypt.dllを保存LOADのname/volume/file IDと照合して同一handleで1回有界readし、前後不変/close確認。
file183376 bytes/hashb5691584e857caf0c6c590dda13779966b383d66be3c87d5b3cbbc2f5005495b。
参照bytesをbcrypt-reference-entry.jsonへ保存し、以後はcacheのみでPE/code/importを調査。
PDB/downloadなし。現在参照fileとの対応であり過去のloaded bytesやcallback実行の認証ではない。

次の[bcrypt内部失敗値取得計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-failure-plan-2026-09-10.md)は、
検証済みbootstrapでDR0〜3へb270/b24d/b22d/1128dを1回設定する。
前3地点は内部callからのEAX=EBX非zero値と固定caller slot8 bytes、後1地点はGetLastError後の生値を記録する。
bootstrap込みGet4/Set1/RPM最大6回805 bytes、同じ時間/memory/disk/metadata条件。
hitの通常Continueなし、所有終了処理のみ、再選択/再armなし。既定off/DETACHED+bootstrap必須/他collectorと排他。
初回fakeで待機slot=Noneの照合不具合を検出し、選択済みarm/hit中の寿命照合へ修正、追加実機なし。

関係fake47/47（2.935秒）、全体pure/fake259/259（5.006秒）、repository safety/diff-check pass。
独立設計・実装点検は新規P0〜P3=0、担当の指定fake47/47（2.818秒）pass。
担当のnative/wrapper/private参照/source変更なし、完了通知のみ、進捗ポーリングなし。
本流889cfc3 clean。次は保存後read-only preflightを行い、新規fixtureで固定4地点から最初の1hitを取得する1回を提示する。
今回のinit-failure1回への了承は消化済み。全acceptance gate no、本流統合/formal/B2/publisher未実施。



実装・試験・結果・計画を1c56b89へ保存した。保存後read-only preflightは2.871秒、
25 sources/270313 bytes、verified、resource_stop=false、primary/secondaryなし。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
bcrypt-failure-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

準備は完了。新規専用fixture1個で、検証済みbootstrapから固定4地点を設定し、
最初の1hitで候補値を取得して所有終了処理まで行う診断1回への返答を待つ。
bootstrap込みGet4/Set1/RPM最大6回805 bytes、既存時間・memory・disk・終了処理条件を維持する。
この具体的な問いへの「お願いします」「続けてください」は当該1回への了承として扱い、同じ了承を再確認しない。
実行wrapperはbcrypt-failure-once.py、2735 bytes/hash7a452b75ccfc721ecfd53ca8293b0fc9ccaae599fc6c0aec9555a57f49c1b2a8、未実行。
§6の追加probe条件を引き継ぎ、自動再試行なし。今回のinit-failure1回への了承は消化済み。


## 69. 2026-09-10 bcrypt call_59e0の戻りC0000022を確認、同期オブジェクト経路の詳細観測を準備

ユーザーの「お願いします」を§68の1回への了承として、cleanな01ba29a（実装1c56b89）で新規fixture1回を実行。
初期reportまで2.497秒、primary=bcrypt_failure_observed_stop、driver/observer failed、
context completed/status confirmed/Set verified、secondaryなし、resource_stop=false。
通常19/Continue18、slot17 bootstrapを照合継続、slot18でDR2 bcrypt b22dにhit。
EAX=EBX=C0000022、caller111cf、confirmed LOAD slot16と一致。call_59e0の非zero候補値として保持。
C0000022はNTSTATUS表ではSTATUS_ACCESS_DENIEDに対応するが、API/object/拒否権限は未特定。
詳しくは[bcrypt内部失敗値の結果](anomaly-multiseed-v0.3-s4-b1-bcrypt-failure-result-2026-09-10.md)を参照。

bootstrap込みGet4/Set1/RPM6回805 bytes。DR6 arm0/hitffff0ff4、DR7 arm55/hit455、RIP/TF/caller/load照合。
hitの通常Continueなし、owned terminate→pending解放→drain4（thread3/process1、全code1）Continue。
signal/ownership解消/owned handles close/teardown pass/failure_count0/driver teardown failures0。
自然EXIT未観測、code1は意図した終了処理。fixture存在unverified、cleanup/repairなし。child E2E未達。

private117453 bytes/hash61994b9cac08a1861dca18c3c6bcb092ee8aaa8be746ca1a580b05cc54668013、
write/flush/file close確認済み。有界held-file read1回で全events/bootstrap/debug CONTEXT/caller/LOAD/launch/stop/hashを照合。
reader close、全inflight false、未確定buffer領域zero。公開要約bcrypt-failure-native-summary.jsonl/readback json保存。
同run preflight25 sources/270313 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory169 samples、親＋child peak commit26005504（24.80 MiB）/working36855808（35.15 MiB）。
作業前後RAM8.03→8.41 GiB、C108.00→107.99/D75.36 GiB、last boot2026-09-09T10:43:08.5000000+09:00。
UBR緩和を維持して状態記録、単発値からリーク有無は未判定。他project操作なし。

前回のbcrypt-reference-entry.jsonだけから59e0/5bf4を解析、追加DLL/PDB read/downloadなし。
RtlInitializeCriticalSection、CreateEventW、後続の設定等が候補。§42の既定DACL RC ACEなしとの因果は未確認、
token/DACL/ACLを変更していない。公式CreateEventW仕様とNTSTATUS表は結果文書へリンクした。

次の[詳細経路観測計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-detail-plan-2026-09-10.md)は、
検証済みbootstrapでDR0〜3へ5af1/5daf/5dd5/b22dを1回設定する。
critical section負値、イベントGetLastError生値、混合cleanup値、外側非zero値を固定site/callerで取得。
caller offset48/128は各固定prologueに基づく。5dd5をCreateEvent失敗の直接観測とは扱わない。
code3窓1790＋caller8、bootstrap込みGet4/Set1/RPM7回1873 bytes。既存時間/memory/disk/metadata上限を維持。
通常Continue/再選択/再armなし、owned stopのみ。既定off/DETACHED+bootstrap必須/他collector排他。
既存bcrypt collectorのcode2回722/caller48・111cfは不変。新sourceで26 inputsを照合予定。

初回fakeで新option自身を排他条件に含める誤りを検出・修正。追加実機なし。
関係fake53/53（3.586秒）、全体pure/fake265/265（6.183秒）、repository safety/diff-check pass。
独立設計・実装レビューは新規P0〜P3=0、担当の指定fake53/53（3.710秒）pass。
担当のnative/wrapper/private参照/source変更/本流操作なし。完了通知だけを利用し進捗ポーリングなし。
本流889cfc3 clean。次は保存後read-only preflightを行い、新規fixture診断1回を提示する。
今回のbcrypt-failure1回への了承は消化済み、全acceptance gate no。本流統合/formal/B2/publisher未実施。



実装・試験・結果・計画を0f34eceへ保存した。保存後read-only preflightは2.547秒、
26 sources/273838 bytes、verified、resource_stop=false、primary/secondaryなし。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
bcrypt-detail-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

準備は完了。新規専用fixture1個で、検証済みbootstrapから固定4地点を設定し、
最初の1hitで詳細候補値を取得して所有終了処理まで行う診断1回への返答を待つ。
bootstrap込みGet4/Set1/RPM最大7回1873 bytes、既存時間・memory・disk・終了処理条件を維持する。
この具体的な問いへの「お願いします」「続けてください」は当該1回への了承として扱い、同じ了承を再確認しない。
実行wrapperはbcrypt-detail-once.py、2760 bytes/hash21855bf61836619d7f0aaa58a0167de136f0ba9b034cf6fbddf0cc9c5853565a、未実行。
§6の追加probe条件を引き継ぎ、自動再試行なし。今回のbcrypt-failure1回への了承は消化済み。


## 70. 2026-09-10 bcrypt後始末前のEBP負値を確認、デバイス経路の3地点を準備

ユーザーの「お願いします」を§69の1回への了承として、cleanな7fff7f8（実装0f34ece）で新規fixture1回を実行。
初期reportまで2.709秒、primary=bcrypt_detail_observed_stop、driver/observer failed、
context completed/status confirmed/Set verified、secondaryなし、resource_stop=false。
通常19/Continue18、slot17 bootstrapを照合継続、slot18でDR2 bcrypt5dd5にhit。
EAX=EBP=C0000022、EDI0、RSI=base25b10/R15=0、caller5ab5、LOAD slot16と一致。
5dafのイベント失敗値は未観測、mixed_cleanup_candidatesのまま保持。特定APIやDACL原因と断定しない。
詳細は[bcrypt詳細経路の結果](anomaly-multiseed-v0.3-s4-b1-bcrypt-detail-result-2026-09-10.md)を参照。

bootstrap込みGet4/Set1/RPM7回1873 bytes、DR6 arm0/hitffff0ff4、DR7 arm55/hit455。
hitの通常Continueなし、owned terminate→pending解放→drain4（thread3/process1、全code1）Continue。
signal/ownership解消/owned handles close/teardown pass/failure_count0/driver teardown failures0。
自然EXIT未観測、code1は意図した終了処理。fixture存在unverified、cleanup/repairなし、child E2E未達。

private117656 bytes/hash562d2d593fe971756d0b3f8d0cc39b19dbf070e00b3742a4ac7100d613ce9526、
write/flush/file close確認済み。有界held-file read1回で全events/bootstrap/CONTEXT/caller/混合値/LOAD/launch/stop/hashを照合。
reader close、全inflight false、未確定buffer領域zero。公開summary/readback保存。
同run preflight26 sources/273838 bytes、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
memory171 samples、親＋child peak commit26103808（24.89 MiB）/working36925440（35.21 MiB）。
作業前後RAM8.10→7.82 GiB、C107.99→107.98/D75.36 GiB、last boot2026-09-09T10:43:08.5000000+09:00。
UBR緩和を維持して状態記録、単発値からリーク有無は未判定。他project操作なし。

前回参照cacheのみから7f50/8154を解析、追加DLL/PDB read/downloadなし。
NtOpenFile helper8154、NtDeviceIoControlFile戻り/応答解釈が候補。固定名はRVA1f098の\\Device\\KsecDD、終端込み30 bytes。
name/要求access100003/share7/options20/control390400/command10500は静的参照値。
過去のCALL完了・実行時IAT・既存handle対象の認証ではなく、token/DACL/ACLやデバイス設定は変更していない。

次の[デバイス経路計画](anomaly-multiseed-v0.3-s4-b1-bcrypt-device-plan-2026-09-10.md)は8129/80ac/5dd5の3site。
初案の8131応答値は80acで先に停止して到達できないP2を独立設計レビューで検出し除外した。
mask15/DR3zero、全4DR照合、最初の例外で終了を維持。80000005も80acの戻り値までを記録、応答値取得を主張しない。
従来4siteはmask55を維持。候補値はR12D負値/EAX負値/mixed EAX・EDI・EBPとsite別に分ける。
caller offsetsb8/128、参照窓3回1758（文字列30含む）＋caller8、bootstrap込みGet4/Set1/RPM7回1841 bytes。
同じ時間/memory/disk/metadata条件、通常Continue/再選択/再armなし、既定off/DETACHED+bootstrap必須/他collector排他。
親から追加device open/IOCTLなし、childの既存起動経路のみを観測。27 sourcesを保存後照合する。

関係fake60/60（4.429秒）、全体pure/fake272/272（5.802秒）、repository safety/diff-check pass。
独立P2は是正確認済み、新規P0〜P3=0、担当fake60/60（4.596秒）pass。
担当のnative/wrapper/private参照/source変更/本流操作なし、完了通知のみ、進捗ポーリングなし。
本流889cfc3 clean。次は保存後read-only preflightを完了し、新規fixture診断1回を提示する。
今回のbcrypt-detail1回への了承は消化済み。全acceptance gate no、本流統合/formal/B2/publisher未実施。



実装・試験・結果・計画をd557a20へ保存した。保存後read-only preflightは2.400秒、
27 sources/277511 bytes、verified、resource_stop=false、primary/secondaryなし。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
bcrypt-device-preflight.jsonへ保存。child起動・SetThreadContextなし、全acceptance gate no。

準備は完了。新規専用fixture1個で、検証済みbootstrapから固定3地点を設定し、
最初の1hitでデバイス経路の候補値を取得して所有終了処理まで行う診断1回への返答を待つ。
bootstrap込みGet4/Set1/RPM最大7回1841 bytes、既存時間・memory・disk・終了処理条件を維持する。
この具体的な問いへの「お願いします」「続けてください」は当該1回への了承として扱い、同じ了承を再確認しない。
実行wrapperはbcrypt-device-once.py、2760 bytes/hash6ef9ba31f8ddebdf112453375f365f5cdee0f8b9f4db845bdc928b3469aee0a0、未実行。
§6の追加probe条件を引き継ぎ、自動再試行なし。今回のbcrypt-detail1回への了承は消化済み。

## 71. 2026-09-10 bcryptのKsecDD open helperでアクセス拒否の経路を確認

ユーザーの「お願いします」を§70の1回への了承として、clean be05b42（実装d557a20）で新規fixture1回を実行。
初期reportまで2.654秒、primary=bcrypt_device_observed_stop、secondaryなし、resource_stop=false。
通常19/Continue18、bootstrap slot17を照合継続、slot18でDR0/8129にhit。
R12D=C0000022、caller5d53、RSI=RSP+60/RDI・R14=0/R15=8、LOAD slot16と一致。
context completed/confirmed、Set verified。直前LeaveCriticalSection後のEAXをhelper戻り値とは扱わない。
[デバイス経路結果](anomaly-multiseed-v0.3-s4-b1-bcrypt-device-result-2026-09-10.md)を参照。

固定参照8154は \Device\KsecDD のNtOpenFileを呼び、戻りがR12Dへ保存される。
このopen helperの負値を確認した。実行時IAT/OBJECT_ATTRIBUTESやCALLそのものの直接観測ではない。
NtDeviceIoControlFile失敗や応答値、CreateEvent失敗を観測したとは扱わない。
個別拒否access、デバイスDACL、driver内条件はこのchild診断だけでは未確定。
token default DACL RC ACEなしを原因と断定せず、token/ACL/core不変。

bootstrap込みGet4/Set1/RPM7回1841 bytes、DR6 arm0/hitffff0ff1、DR7 arm15/hit415。
owned terminate→pending解放→drain4（thread3/process1、全code1）Continue、
signal/ownership解消/owned handles close/teardown pass/failure_count0/driver teardown failures0。
自然EXIT未観測、exit1は意図した終了処理。fixture存在unverified、cleanup/repairなし、child E2E未達。

private117759 bytes/hashf04e02ae4ccab8a2f0f512d612f954d11e9380be9b097d4d6ffae4fdfac31d35。
write/flush/file close確認済み。有界held-file read1回でraw全events/bootstrap/CONTEXT/R12D/frame/caller/LOAD/launch/stop/hashを照合。
reader close、全inflight false、未確定buffer zero。公開native-summary/readback保存。
同run preflight27 sources/277511 bytes verified、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
既存codeのpure/fake272件・独立レビュー結果を維持、コード変更によらない全体fake再実行なし。

memory171 samples、親＋child peak commit26034176（24.83 MiB）/working36872192（35.16 MiB）。
08:03:33Z→08:09:28Zの空きRAM8.32→7.99 GiB、C108.00→107.99/D75.36 GiB。
last boot2026-09-09 10:43:08 +09:00。Windows Update UBR緩和と状態記録を維持。
単発資源値からリーク有無を断定しない。他project操作なし。本流889cfc3 clean。

child breakpointをさらに追加する前に、作業継続指示に基づく親contextの読み取り専用メタデータ確認を準備した。
固定KsecDDのみREAD_CONTROL|SYNCHRONIZEでopen1回、owner/group/DACL query1回/4096 bytes、close。
token作成・変更/impersonation/ACL変更/IOCTL/data read-write/child/retryなし。
これはchild診断1回を繰り返すものではなく、親権限でrestricted childの処理を代替するものでもない。
AccessCheckや実行時対象identity認証・driver固有判定は行わず、匿名化DACL観測の限界を維持する。
独立事前レビューで取得未確認handleのcloseと資源停止後JSON/saveのP2 2点を検出し修正、是正確認済み・新規P0〜P3=0。
今回のchild1回への了承は消化済み。全acceptance gate no、本流統合/formal/B2/publisher未実施。


親contextの読み取りは2026-09-10T08:15:48Zに1回完了。open/query/close各1回confirmed、0.002秒、resource_stop=false。
取得188 bytes、DACL6 allow ACE、RC allow1200a9、他はEveryone1201bf/System・Administrators1f01ff/未分類2 ACE1201bf。
固定参照の要求100003との差分は書き込み権限0x2。現行flags9/RCのみという構成とopen helper拒否に整合する。
RC ACE不存在ではない。単純mask比較で、実AccessCheck・唯一原因・同時点identity認証は未実施。
生SD/SIDは新規保存せず、匿名化summary1576 bytes/hashc3227d3fdefc1adaec0c50b7211fc2444ecc7da51c705902ceff087b4b383aebを
既知pathから1回有界readし確認。script7993 bytes/hash4eff849764ccb4165b4ac5bea749b2e6d263164dd3b37c3830b2532d681921bf。
詳細と制約は結果文書末尾へ保存した。追加child/IOCTL/ACL/token変更なし。

[権限構成の判断資料](anomaly-multiseed-v0.3-s4-b1-token-compatibility-decision-2026-09-10.md)を作成した。
保護対象へのwrite禁止とRC/flags/privilege削減を維持し、Windows互換性のため制限SID構成の見直しを許容するか判断する。
追加SIDは未選定。SID追加が保護対象外の許可を広げうるため、§6の禁止条件を黙って変更しない。
現在のRCのみ維持ならB1はblockedのまま。未分類ACEを推測で命名せず、広いEveryone等の追加は自動採用しない。
具体的recipe選定・独立レビュー前に変更tokenのchild実行なし。本流統合/formal許可は含めない。

結果追記と判断資料の独立レビューは新規P0〜P3=0。担当のnative/query/試験/編集なし、完了通知のみ。
repository safety/diff-check pass、runtime/core/test source変更なしのため272件fake/preflight再実行なし。
最終08:20:29Zの空きRAM8.69 GiB、C108.47/D75.36 GiB。直前08:19:58ZはRAM7.64 GiBであり、
他processを含む環境変動から本作業のリーク有無を推測しない。確認済みの今回owned handle解放を事実として記録する。
本流889cfc3 clean、候補文書だけを保存。次の「お願いします」「続けてください」は今回の権限構成見直し方針への返答として扱い、
消化済みbcrypt-device診断を再実行する指示へ読み替えない。

## 72. 2026-09-10 ユーザー了承に基づくRC＋制限アプリ識別子の互換性候補

直前の権限構成見直し方針へのユーザー「お願いします」を了承として記録する。
[判断資料](anomaly-multiseed-v0.3-s4-b1-token-compatibility-decision-2026-09-10.md)の保護対象write禁止を維持し、
今回の限定候補を検証する範囲について§6の従来条件を更新する。同じ方針了承を再確認しない。
消化済みbcrypt-device診断の再実行ではない。

親metadata readの既存scriptに既知SIDの固定ラベル2種だけを追加し、新規出力先で1回実行。
2026-09-10T08:23:34Z、open/query/close各1回confirmed、188 bytes、0.001秒、resource_stop=false。
SD hash80855ee5cacdab07dcb48643d08ae3898dd45bef77695ab67057a08395cd8521は前回と一致。
前回未分類2 ACEはAllApplicationPackagesとAllRestrictedApplicationPackages、双方allow1201bf。
前回のraw SDは未保存のため、新たな1回のqueryで分類した。未知SIDを推測で命名したものではない。
分類script8111 bytes/hashd16bd371df2732614c75999919dd1201f5da90b09820956fb2ab245367e0e428。
child/token/ACL/IOCTL変更なし。公開要約ksecdd-security-classified.jsonを保存。
Microsoft WinSDKのauthority/base/RIDを参照し、後者1種類を候補に選定した。

[具体的候補と検証計画](anomaly-multiseed-v0.3-s4-b1-token-compatibility-plan-2026-09-10.md)を作成。
coreとDebugTokensのrestricting SIDを固定RC＋AllRestrictedApplicationPackagesに統一し、属性7まで厳密検証。
flags9、非昇格・同一user/session/integrity、privilege削減とnormal group条件を維持。
protected frozen/control DACLは不変、Everyone等の広い追加なし。
追加SIDはそのSIDへのallowがある他objectにも効く。RCが各追加grantをさらにANDで制限するものではなく、
KsecDD専用・従来同等の隔離・AppContainer化とは主張しない。

選抜pure/fake69/69（0.173秒）、全体275/275（6.274秒）pass。
不足/余分/重複/順序/属性/別package/Everyone/SYSTEM、作成flags・配列、追加SID失敗時の未作成・解放、
DebugTokens追加SIDの中断出力保持を確認。独立設計レビュー新規P0〜P3=0。実装レビュー中。

未実行wrapper token-compatibility-control-once.pyは3899 bytes、
SHA eec528b2dfdfd13b19330958efdc3ad6df97566635846a0a5dc43d6678948ead、AST run_control_harness 1箇所。
独立実装レビュー・commit・保存後preflightの後、新規fixture1個で既存control harnessを1回検証する。
child token照合→親AccessCheck→resume→child AccessCheckと全実操作→report照合→cleanup/teardownを確認する。
30秒/親＋child512 MiB未満/temp空き1 GiB以上を維持。失敗時は証跡保持、自動再試行なし。
本流889cfc3 clean、正式受入/Python3.12/本流統合/formal/B2/publisherは未完了。
作業前08:22:42Zの空きRAM8.16 GiB、C108.47/D75.36 GiB、Windows26200.9445、
last boot2026-09-09T10:43:08.5+09:00。UBR緩和と状態記録、他project無操作を維持。


実装レビューでprofile()のSID文字列ソートと期待順の不一致P2を検出。作成順はRC→制限アプリのまま、
検証・wrapper期待値をsortedへ修正し、実profile()を通すowned fake buffer回帰を追加した。
初回69/275件が非canonical fakeを返して見逃した点を記録する。
是正後選抜70/70（0.216秒）、全体276/276（7.118秒）pass。
P2是正確認済み、新規P0〜P3=0、独立担当は新回帰1件だけpass（0.002秒）。
担当のnative/query/wrapper/編集なし、進捗ポーリングなし。repository safety/diff-check pass。
最新wrapper3907 bytes/hash01fbc5015ea5fc91beaa3544cd478ab18532199f3c6ca56bb2b8b55011b97ad6、未実行。
分類summary1606 bytes/hash26be0758bdd1113c9933dc11a1fee87fb5cddc1a1576051b2b394d3488c9e915、既知pathから有界readで確認済み。


互換性候補を14e2f53へ保存。保存後preflight2.257秒、27/278074 bytes、verified。
限定control1回はrestricted_token_create/WinError87で停止、core0.234487秒、child/fixture未作成。
teardown pass/resource_stopfalse、private control/replaceなし。実行内preflightもverified、Windows10.0.26200.9445/Python3.14.0。
結果はtoken-compatibility-result文書とdf09964へ保存。再点検と独立点検に引数/配列/寿命の新規所見なし。
ARAP一般禁止や唯一原因とは断定せず、同候補の再実行なし。

[AllApplicationPackages候補](anomaly-multiseed-v0.3-s4-b1-app-package-plan-2026-09-10.md)を準備する。
実測されたもう一方の非特権ACEに対応し、RC＋追加1種を維持。flags/属性/canonical順序/非昇格/保護DACLは不変。
前計画のARAP優先選定を、ユーザー了承済み見直し範囲で更新する。広いEveryone/user/admin/system追加はしない。
変更3ファイル、選抜70/70(0.237秒)pass、独立確認中。新規device queryなし。
この候補もtoken作成に失敗ならSID試行を打ち切る。本流/formal gateは閉鎖を維持する。


AllApplicationPackages候補はc795b05へ保存。独立差分レビュー新規P0〜P3=0、
保存後preflight2.651秒、27/278084 bytes、verified。新規control1回は再びrestricted_token_create/WinError87。
core0.221246秒、child/fixture未作成、teardown pass/resource_stopfalse、private control/replaceなし。
実行内preflightもverified、runtime hash一致。ここでSIDを替える実機試行を打ち切った。
2候補のsummaryは各1444 bytes、ARAP hashadc2b952ff73a399b52f2ad0263606eaa9818b66f552f1257a78dcd4138b5ee0、
AAP hash9e6d0545dddc5e4f101bb1ac986b8349a3204598b3cb281615983986848fea16。
既知pathから各1回有界readで結果照合、package-candidates-result-check.jsonへ保存。
fixture再open/追加native/新規ACL操作なし。[2候補の結果](anomaly-multiseed-v0.3-s4-b1-token-compatibility-result-2026-09-10.md)を参照。

[RC＋Everyoneの判断資料](anomaly-multiseed-v0.3-s4-b1-world-compatibility-plan-2026-09-10.md)と未実行candidateを準備した。
これは前判断資料の「Everyoneのような広いgrantを自動採用しない」範囲なので、新しいユーザー判断が必要。
固定RC＋Everyone、属性7/canonical順序、flags9、normal groups/privilege削減/非昇格、protected DACLを維持。
既存Everyone allowにより他objectへの許可が広がりうること、KsecDD専用・RCとのAND・隔離同等ではないことを明記した。
core定数名/値と対応fakeを更新、選抜70/70（0.219秒）pass。新規nativeは実行していない。
独立差分・計画レビュー新規P0〜P3=0、担当のnative/query/再試験/編集なし、進捗ポーリングなし。
未実行world-compatibility-control-once.pyは3891 bytes/hash1c1a92734ce87ea8d3988cd2a3653fb2d096b93a074cf415e7d394607d207348。
保存後preflightを完了した具体的候補で、専用fixture1個のcontrolを1回行うか判断を求める。
この問いへの「お願いします」「続けてください」は当該1回への了承として扱い、同じ了承を再確認しない。
前2候補を再実行する指示へ読み替えない。本流統合・formal/B2/publisherの許可を含まない。


候補コードをc0909ac77263603dab2945bc4ac8f369889178e7へ保存した。
保存後read-only preflightはverified、2.843秒、27 sources/278078 bytes、resource_stopfalse、primary/secondaryなし。
Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
world-compatibility-preflight.jsonへ保存。World token作成・child・SetThreadContextは未実施。
今回の広い候補はユーザー判断待ちで、承認前にnativeを進めない。
作業後08:46:53Zの空きRAM8.45 GiB、C108.46/D75.36 GiB、last bootは作業前と同じ。
別projectの連続試験や既存failure rootsを操作していない。単発の資源値からリーク有無を断定しない。
本流889cfc3 clean、repository safety/diff-check pass。記録だけの更新でsource preflightや試験を再実行しない。


## 73. 2026-09-10 RC＋Everyone実行結果と固定終了コード診断

ユーザー「続けてください」を直前のWorld候補control1回への了承として実行済み。
実装c0909ac、clean HEAD8c83192、既知wrapper3891 bytes/hash
1c1a92734ce87ea8d3988cd2a3653fb2d096b93a074cf415e7d394607d207348を実行前照合した。
新規fixtureのcontrol1回のみ、debug collector/SetThreadContextなし、再実行なし。
[実行結果](anomaly-multiseed-v0.3-s4-b1-world-compatibility-result-2026-09-10.md)へ保存。

failed/child_failed/WinError0/child_exit_code1、core0.6294818999886047秒。
固定sourceの分岐順からtoken作成、実child primary/duplicate profile照合、親AccessCheck、resumeを通過。
親AccessCheckの生データを別途保存した主張ではない。今回はC0000142を観測しなかったが、
exit1からPython _child_main到達・保護検証・起動全体成功を断定しない。
replace trace incomplete/0 records/0 bytes、private_controlなし、private_replace0 bytes。
known_bytes5926、fixtureの存在・残存量unverified、failed fixture再open/cleanup/ACL修復/再利用なし。
control failed/cleanup not_started/teardown pass/resource_stopfalse。
親＋子ピークprivate42.55 MiB/working53.77 MiB、system commit34,679,246,848/limit70,493,097,984 bytes。
実行内preflight verified、27/278078 bytes、Windows10.0.26200.9445/Python3.14.0、runtime hash一致。
summary1997 bytes/hash20c80de096fa753c4dbae6281c1df255f06e175f8c461d12eb95391384f477b3を
既知pathから1回有界readし、world-compatibility-result-check.jsonへ照合保存した。

[次の固定診断計画](anomaly-multiseed-v0.3-s4-b1-child-diagnostic-plan-2026-09-10.md)を準備。
coreと固定childにappend-only202理由ID＋WinError16bitの数値診断、bootstrap/child_callの区別を追加。
成功0/legacy32〜40/resource80を維持し、CPython最終処理の120は割当てず未知扱い。
例外文/traceback/パス/token/SDを出さず、例外処理からの書込み・標準出力を増やさない。
初回選抜76/76（0.357秒）、全体282/282（5.605秒）pass。
独立レビューP2のOSError.winerror資源停止漏れを両経路で是正し、派生クラス含む全7番号の回帰を追加。
修正後全体283/283（5.982秒）pass。独立是正・文書・wrapperレビュー新規P0〜P3=0。
担当のnative/query/再試験/編集なし、完了通知だけを受け進捗ポーリングなし。
repository safety/diff-check pass。

未実行child-diagnostic-control-once.pyは3983 bytes/hash
31c8e05df0eba398f6a7d528250acaee5eb8e1171a6dcd4616ad61fa345a0e9e、harness呼出1箇所。
同じRC＋Everyone/保護DACL/全必須control/30秒/512 MiB未満/temp空き1 GiB以上を維持。
既存fixtureの再利用なし、新規fixture1個の次の診断1回を具体化し、source保存後preflightを行う。
今回のWorld1回の了承は消化済み。§6の追加probe無断反復禁止により、新たな診断1回への返答を待つ。
次の「お願いします」「続けてください」はこの診断1回への了承と扱い、同じ了承を再確認しない。
成功時もnative_accepted/s4_accepted/formal_permission/execution_authenticated=false。
Python3.12既定受入・本流統合・formal/B2/publisherは閉じたまま。

作業前08:49:27Z RAM8.04 GiB/C108.45/D75.36 GiB、検証後08:59:08Z RAM7.61 GiB/C108.43/D75.36 GiB。
build26200.9445、boot2026-09-09T10:43:08.5+09:00。UBR緩和と実測記録を維持。
点の資源量からリーク有無は断定しない。今回のowned teardown passを記録する。
本流889cfc3 clean、別projectの連続稼働試験へ操作していない。


診断コードを911d5a5へ保存。保存後read-only preflightは2.572秒、27 sources/284856 bytes、verified。
resource_stopfalse、primary/secondaryなし、Windows10.0.26200.9445/Python3.14.0、既存runtime hash一致。
child-diagnostic-preflight.jsonへ保存。新しいchild/control/token作成、SetThreadContextは未実施。
最終09:04:47Zの空きRAM8.52 GiB、C108.44/D75.36 GiB、last bootは作業前と同じ。
本流889cfc3 clean、別projectの連続稼働テスト・失敗fixtureへ追加操作なし。
この追記は記録のみでsource/試験対象を変更していないため、fake試験・preflightを再実行しない。


## 74. 2026-09-10 child runtime_pin特定とCPU構成の直接確認

ユーザー「続けてください」を直前の準備済みchild-diagnostic1回への了承として実行した。
実装911d5a5、clean HEAD a429a9c、wrapper3983 bytes/hash31c8e05df0eba398f6a7d528250acaee5eb8e1171a6dcd4616ad61fa345a0e9eを実行前照合。
新規fixtureのcontrol1回だけ、既存fixture/消化済みwrapper再実行・debug collector・SetThreadContextなし。
[結果](anomaly-multiseed-v0.3-s4-b1-child-diagnostic-result-2026-09-10.md)はchild_exit_code278331392、
保存protocolでchild_call/runtime_pin/WinError0。core0.6305790999904275秒、teardown pass/resource_stopfalse。
ここで子側の固定理由を観測。_child_main冒頭_runtimeで停止、子のsource/token/AccessCheck/実操作検証は未完了。
OS/CPU/Python metadataの複合条件のため、失敗した個別項目は未確定。以前のexit1を同一原因と断定しない。
trace incomplete/0 records/0 bytes、private_controlなし、private_replace0 bytes、known_bytes5926、存在・残量unverified。
公開summary2091 bytes/hashd3ee07bd86d846726d810812524676fdcaba3cbef49ad22feee63ec130544bd2を既知pathから1回有界readして確認。
child-diagnostic-result-check.jsonへ保存。failed fixture再open/ACL修復/cleanup/再利用なし。
親＋子ピークprivate42.20 MiB/working53.46 MiB、実行内preflight27/284856 bytes verified、runtime hash一致。
実行前09:08:09Z RAM8.16 GiB/C108.44/D75.36 GiB、build26200.9445/boot2026-09-09T10:43:08.5+09:00。

[CPU構成の直接確認への修正](anomaly-multiseed-v0.3-s4-b1-runtime-machine-plan-2026-09-10.md)を準備。
固定stdlibはWMIが失敗しCPU環境変数もなければmachine名を空にする。実WMIなしの模擬入力で再現した。
実childのWMI失敗・単独原因を確定したという意味ではない。
platform.machine()をIsWow64Process2によるnative AMD64/process非WOW64の厳密照合へ置換。
環境変数追加・token/ACL変更なし。OS/UBR/Python metadata/hash条件を維持し、理由4個を末尾追加して区別する。
選抜82/82（0.470秒）pass後、実測旧exitのID維持回帰を追加。全pure/fake289/289（9.282秒）pass。
独立差分レビュー新規P0〜P3=0、担当のnative/query/再試験/編集なし、進捗ポーリングなし。
repository safety/diff-check pass、本流889cfc3 clean。

未実行runtime-machine-control-once.pyは3982 bytes/hash4292c3aefc011adfc7a204b76304ba3648e523c72eca2531babe11ec1413d9e9。
新規summary先のみ変更、harness呼出1箇所。同じtoken/保護DACL/全必須検証と30秒/512 MiB未満/temp空き1 GiB以上を維持。
source保存後read-only preflightを完了し、次の新規fixture control1回への返答を待つ。
今回のchild-diagnostic1回は消化済み。§6に従い自動反復せず、次の「お願いします」「続けてください」を次の1回への了承として扱う。
追加権限・既存fixture操作・別project操作を含まない。成功時も受入/認証/formal各flagはfalse。
Python3.12既定受入・本流統合・formal/B2/publisherは閉じたまま。UBR緩和と状態記録を維持する。


修正コードを6094466へ保存。保存後preflight2.822秒、27 sources/285764 bytes、verified。
resource_stopfalse、primary/secondaryなし、Windows10.0.26200.9445/Python3.14.0、既存exe/DLL hash一致。
保存sourceの分岐順から、親側のIsWow64Process2によるnative AMD64照合も通過したと判断できる。
修正後のrestricted childで成功した証拠ではない。runtime-machine-preflight.jsonへ保存。
最終09:17:16Zの空きRAM8.06 GiB、C108.38/D75.36 GiB、last bootは同じ。
点の資源量からリーク有無を断定せず、別projectや既存失敗fixtureへの操作なしを維持。
本流889cfc3 clean。今回追記は文書のみであり、source preflight・fake試験を再実行しない。


## 75. 2026-09-10 子の実操作検証への到達とCWD/操作診断の修正

ユーザー「続けてください」を準備済みruntime-machine control1回への了承として実行。
実装6094466、clean HEAD60b1b70、wrapper3982 bytes/hash4292c3aefc011adfc7a204b76304ba3648e523c72eca2531babe11ec1413d9e9を実行前照合した。
新規fixtureの1回だけで、既存fixture/同wrapper再利用・debug collector・SetThreadContextなし。
[結果](anomaly-multiseed-v0.3-s4-b1-runtime-machine-result-2026-09-10.md)はexit37/operation_unexpected、core0.6436681000050157秒。
保存sourceの順序から子のruntime/source/token/AccessCheck/trace初期確認を通過し_operationsへ到達。
旧_needは実API errorを保持しないため、診断winerror0を実API成功とは解釈しない。操作名・実WinErrorは未確定。
前回runtime_pinは観測されなかったが、前回の個別原因がCPUだけだったと遡って断定しない。
control failed/cleanup not_started/teardown pass/resource_stopfalse、trace incomplete/0 records/0 bytes。
private_controlなし/private_replace0 bytes、known_bytes5926、fixture存在・残量unverified。
公開summary2086 bytes/hash0568e33c6a1c40abb478cb5f0a532021c7b3cdebe4a34744c585423bde02b882を既知pathから1回有界readして照合。
runtime-machine-result-check.jsonへ保存。failed fixture再open/ACL修復/清掃/再利用なし。
親＋子ピークprivate42.45 MiB/working52.96 MiB、実行内preflight27/285764 bytes verified、runtime hash一致。
実行前09:28:51Z RAM7.88 GiB/C108.38/D75.36 GiB、Windows26200.9445、boot2026-09-09T10:43:08.5+09:00。

[次候補](anomaly-multiseed-v0.3-s4-b1-operation-context-plan-2026-09-10.md)ではchildのCWDをcontrolから専用fixture.rootへ変更。
親CWD・操作対象・全期待値・token・ACL・環境は維持。Microsoftのcurrent directory lock仕様に基づく干渉回避であり、
旧37の唯一原因をCWD/WinError32と実測した主張ではない。
operation_unexpectedだけ固定48操作IDの独立数値領域と実WinErrorで診断し、既存206理由ID/旧37を維持。
資源errorを80へ優先し、任意case/パス/token/例外文を公開しない。
positive mutation自体が例外を出す場合などは旧理由のままで操作IDが付かない場合がある。
選抜87/87（0.557秒）、全pure/fake293/293（10.843秒）pass。
独立差分レビュー新規P0〜P3=0、担当のnative/query/再試験/編集なし、進捗ポーリングなし。
repository safety/diff-check pass。

未実行operation-context-control-once.pyは4047 bytes/hash8dc7b3940930212f477c95b195a2960a0eac0c7bffadcea27784f77a113b0658。
AST上harness呼出1箇所、新規summary先と保存source上CWDラベルの変更のみ。
source保存後read-only preflightを完了した新規fixtureの次のcontrol1回を準備する。
今回のruntime-machine1回の了承は消化済み。§6に従い自動反復せず、次の「お願いします」「続けてください」を次の1回への了承として扱う。
RC＋Everyone/非昇格/必須操作/保護DACL、30秒/512 MiB未満/temp空き1 GiB以上と資源停止後の追加hash/save/scan禁止を維持。
別project操作・既存fixture操作・追加権限は含まない。成功時もnative_accepted/s4_accepted/formal_permission/execution_authenticated=false。
Python3.12既定受入・本流統合・formal/B2/publisherは閉じたまま。UBR緩和と状態記録を維持する。


修正コードを0b30e63へ保存。保存後preflight2.884秒、27 sources/288326 bytes、verified。
resource_stopfalse、primary/secondaryなし、Windows10.0.26200.9445/Python3.14.0、既存exe/DLL hash一致。
operation-context-preflight.jsonへ保存。修正後のrestricted child/controlは未実施。
最終09:40:09Zの空きRAM8.24 GiB、C108.16/D75.36 GiB、last bootは作業前と同じ。
本流889cfc3 clean、別project・失敗fixtureへの追加操作なし。点の資源量でリーク有無は断定しない。
この追記は文書のみでsourceを変えないため、fake試験・preflightを再実行しない。

## 今回提示する進行方針（未承認）

準備済み0b30e63候補を含む最大3候補について、各候補control harness1回、合計最大3回まで進める。
child作成前に失敗した呼出も1回と数える。同じcandidateの再実行はしない。
次の候補は観測結果に基づく修正・診断改善が必要な場合だけ準備し、各候補の適切なpure/fake検証、
独立差分レビュー、source保存、read-only preflightと空き資源確認を終えてから1回実行する。
権限/token/保護DACL/必須期待値/起動隔離条件/資源上限は変更しない。既存failure rootsや別projectを操作しない。
成功、資源停止、所有後処理の不確実性、許可条件外の変更が必要な場合、または3回消化で停止して記録する。
各結果・修正は保存する。正式受入/本流統合/formal/B2/publisherの許可を含まない。

この問いへの「お願いします」「続けてください」を上記最大3回への了承として扱い、受領後は§6の都度確認をこの範囲だけ緩和する。
現時点では未承認であり、今回実施済みのruntime-machine1回を再実行する意味ではない。
§75の先の「次の1回への返答待ち」は準備途中の記録で、今回最終提示する対象はこの限定した最大3回の方針とする。


## 76. 2026-09-10 限定engineering control成功・最大3回枠を1回で終了

ユーザー「続けてください」を§75の最大3候補・各1回の提案への了承として記録する。
§6の都度確認をこの範囲で緩和し、準備済み候補1回を実行。成功時停止の条件に従い、この試行枠は終了した。
残り2回は実行・予約・繰越しない。以前の単独診断の再実行ではない。
[成功結果](anomaly-multiseed-v0.3-s4-b1-operation-context-result-2026-09-10.md)を新たな基準とする。
実装0b30e63、clean HEADf15af39、実行前wrapper4047 bytes/hash8dc7b3940930212f477c95b195a2960a0eac0c7bffadcea27784f77a113b0658一致。
新規専用fixture1個、固定RC＋Everyone、起動flags0x40c/child CWDfixture.root。token/ACL/必須期待値/資源上限は維持した。

native_control_pass、control pass/cleanup completed/teardown pass、resource_stopfalse、core0.9394162999960827秒。
実child token、親子AccessCheck、runtime/source、子の全48期待値、private report照合を通過した。
48は両modeのfile right-open5＋directory right-open6＋mutation13。各private report条件も実行wrapperで確認済み。
replace trace complete/6 records/2385 bytes、最終restored、未確認tail0。
成功cleanupは9対象/15616 bytesを捕捉し、9対象すべてabsent/close confirmed、unknown0/residue0。
15616 bytesはcleanup前の捕捉量であり残存容量ではない。終了後fixtureの再open・追加走査なし。
公開summary4305 bytes/hash830ead15ce782c023a895fc3aefe0bbfb8a433d252c3032f8e85d338ae100293を既知pathから1回有界readして照合。
operation-context-result-check.jsonへ最大3/消化1/成功終了も保存。
private control16494 bytes/hash5d888eaebd1cea0980c2ae66f37692fd2f46b26f8574a138e8d059e001de2af2、
private replace2385 bytes/hashd876cf2a222b7d63b4a02ecc86422e4bbc081989dfd4f650ddd826c38bfda66f。
private rawはexportせず、fixture上の報告も成功cleanupで削除済み。公開要約から生報告を復元できるという主張はしない。
旧exit37の実API error/操作名は失われているため、唯一原因をCWD/WinError32と遡って確定しない。

親＋子ピークprivate42.72 MiB/working53.13 MiB。実行前09:48:47Z RAM8.05 GiB/C108.16/D75.36 GiB、
実行後09:49:50Z RAM7.87 GiB/C108.15/D75.36 GiB。Windows26200.9445、boot2026-09-09T10:43:08.5+09:00。
点の資源量からリーク有無を断定せず、今回のowned teardown passを記録する。UBR緩和と実測記録を維持。
実行内preflight27/288326 bytes verified、Python3.14.0、既存exe/DLL hash一致。
前回pure/fake293件・独立差分レビュー後のsource変更なし。結果文書のみを保存するため、fake/preflight/nativeを繰り返さない。

全受入/認証/formal各flagはfalse。本流889cfc3 clean、push/merge・formal/B2/publisher/Hub/PLC writeなし。
Windows Python3.12を含む既定受入・本流統合・S4全体は未完了。full suite/S3長期回帰の追加実行なし。
次の作業はこの成功結果を基準に、受入条件・Python3.12の扱いと本流統合に必要な確認を整理する。
今回の成功を既存failure rootsの清掃・追加試験・formal許可へ読み替えない。


成功結果・公開要約・handoff最新記述の独立照合は新規P0〜P3=0。
48期待値は実行中wrapperのoperations_matchと保存sourceの期待値件数に基づく。
公開要約だけからprivate reportの個別値を独立再検証した主張はしない。
担当は指定公開資料のみをreadし、native/query/fixture再open/試験/編集なし。進捗ポーリングなし。

## 77. 2026-09-10 受入条件の照合・追加回帰・Windows 3.12要件の確認

[受入整理と実行記録](anomaly-multiseed-v0.3-s4-b1-acceptance-readiness-2026-09-10.md)を参照。
基準f9244a7、実機controlの追加実行なし。前回の成功で最大3回枠は終了したまま。
既定計画ではLinux Ubuntu24.04/Python3.12・3.14と、Windows3.12・正式3.14.0の受入が必要。
現CIはubuntu-latestのLinux2jobs、Windows jobなし。候補source上の既存stdlib全回帰・所定のruntime/image証跡は未完了。
現B1 coreは3.14.0限定のため、3.12の導入だけでは受入不可。B2 publisher/markerとS4完全inventory・consumer凍結は別残件。
独立read-onlyの条件照合で、限定control成功と全受入の区別、正式OS pin9168が未変更であることを確認した。
UBR緩和と9445でのengineering成功を、正式計画・registry・S3 runtimeの更新として扱わない。

従来の「全pure/fake293件」はdebug群・child diagnostics・startup events/preflight・PureWindowsControlsの選抜数であり、
全repository回帰や他のcleanup/replace/offline群まで網羅した数ではない。
今回5つの明示pure/fakeクラス67件を補完し、旧ImportError exit1期待のテスト1件がfail、他66pass。
固定bootstrap ImportError97へ期待値を更新し、共有classifier不在確認を_child_failure_exitへ修正した。
現runtime/child wrapper/token/ACL/正式入口は変更なし。修正はcdbc0a1へ保存。
上記67＋既存child diagnostics10＋D2 exact inventory1の78件を実行してpass。
共有環境Capstone5.0.9とoptional pin5.0.7の差を発見し、専用ignored領域へ5.0.7を配置して再確認。
PyPI wheel1272204 bytes/hash4ab8bcb7da8f221ff45926ca168ca33e76f7237d06fbf3c10780002faa2670e1一致、展開63members/8409204bytes。
import版と専用pathを確認した最終78/78は10.504489秒、failure/error/skip0。
exact test IDs・source/差分hash・依存版・結果はacceptance-supplement-pure-pinned.json（11269 bytes）へ保存。
共有Capstone・PATH・registry変更なし。初回失敗/5.0.9条件の記録も別に保持した。
独立テスト差分レビューは新規P0〜P3=0。担当のnative/query/試験/編集なし、進捗ポーリングなし。
repository safety/diff-check pass。D2の1件はsource inventoryの読み取りだけで、artifact再読や全長期回帰ではない。

ユーザー「3.12必要？」を受領。現在の動作には不要で、既定の互換性受入条件のため残件に挙げたと回答。
Windowsは3.14.0に一本化しLinux3.12/3.14 CIを維持する案を提示して返答待ち。
要件削除は未実施。受領した場合は計画§8・acceptance_requirements・対応契約テストを合わせて変更し、
pure/fake拒否経路・独立レビューを確認する。Windows必須native検査やB2/S4残件の削除と混同しない。
py -0pは3.14/3.11のみ。3.12は未導入・未起動、PC全体のportable runtime探索なし。

資源10:10:49Z RAM8.28 GiB/C108.16/D75.36、10:18:24Z RAM7.82/C107.66/D75.36。
最終10:25:02Z RAM8.33 GiB/C107.66/D75.36。acceptance-resources-final.jsonへ保存した。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。点の変化をリークと断定しない。
各検証process終了確認済み。別project・既存failure fixture・旧artifactへの操作、本流変更/push/merge/formal実行なし。

## 78. 2026-09-10 Windows受入をPython3.14.0へ一本化

ユーザー「3.12必要？」への一本化提案に続く「続けてください」を方針への了承として記録する。
§77の返答待ちは解消し、[現行受入記録](anomaly-multiseed-v0.3-s4-b1-acceptance-readiness-2026-09-10.md)を更新した。
Windows3.12の追加導入・互換性実装・実機試験は不要となった。Linuxの3.12/3.14 CIは維持する。

実装9fd3490（基準56f6a69）。計画§8、runtime受入リスト、S4-Aの要件/schema/validator/collector、
対応テストと評価tool説明を同期。receiptはs4-a.2へ更新し、旧s4-a.1/旧windows-3.12要件を現validatorで拒否する。
schemaのpathは据置き、D2のhistorical88/current-only32と科学config/schema/registry・歴史plan pinを維持した。
過去のreceiptを変換・上書きしない。fresh receiptも全項目not_completed、formal_permissionfalseである。
Windows collectorは3.12/3.14.1などを対象path・source・native inventory検査前に拒否し、3.14.0では従来の基本pinを要求。
Linux両minorのcompatibility-only観測を維持。正式OS pin9168・exe/DLL hash・campaign無条件拒否は変更なし。
B1の9445でのcontrol成功を正式受入に読み替えない。Windows必須nativeの権限・競合・失敗証跡条件を減らさない。

関連25/25 pass、10.286753秒、failure/error/skip0。旧形式拒否・非対応Windowsの早期停止、Linux両minor、
collectorの新形式出力、正式入口拒否、科学planとD2 exact inventoryを選抜して確認。
通常の小さなowned-temp fixtureだけを終了時清掃。native control、全suite、正式campaignの実行なし。
windows314-acceptance-tests.json（6268 bytes/hashdbcc0b679aebae32423d5fe83cef65f3506ea2d6fbb685f804ad34c82da8c0c5）へ保存。
各test ID/source hash・検証差分hashを記録し、検証済み8ファイルを9fd3490へcommitした。
独立差分レビュー新規P0〜P3=0、担当の試験/native/編集なし。進捗ポーリングなし。
repository safety/diff-check pass。B1の既存failure rootsや別projectへの操作なし。

作業前11:07:49Z RAM8.60 GiB/C107.64/D75.36、build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。
検証後11:17:01Z RAM7.64 GiB/C107.63/D75.36、同build/boot。windows314-resources-final.jsonへ保存。
今回のPython検証processは終了確認済み。点の変化をリークと断定しない。
3.12インストール・起動なし、主環境変更なし。本流889cfc3はclean、push/mergeなし。
追加native枠は前回成功で終了したまま。本流統合・B2 publisher/marker・S4完全受入は未完了。
次の残件はLinux所定CI環境/全回帰証跡、Windows3.14.0の全回帰・native受入範囲と正式OS条件の整合、
B2公開部品・完全runtime inventory・producer/consumer revision凍結である。

## 79. 2026-09-11 Linux CI固定・unittest記録の実装と候補CI

ユーザー「続けてください」を受け、§78の残件であるLinux CIの整備を実施。
基準e9588dc、実装3c69f9ea3203313ac1b300e3e74e6607cf891262。
[詳細記録](anomaly-multiseed-v0.3-s4-b1-ci-evidence-2026-09-11.md)を参照。
ubuntu-24.04 x86_64 / CPython3.12・3.14の2 jobs、fail-fast falseを設定。
従来の全unittest discoveryを維持し、実runtime/source/各予定test ID・開始・結果・終了をJSONLへ逐次保存する。
Windowsではdiscovery前に拒否するため、このPCの全suite/native controlは実行していない。
失敗後もsafetyを試行し、unittest JSONL1個だけをminor/run/attempt別に14日保存する。
記録は新規作成のみ・16MiB上限。これは全processメモリの上限ではない。
途中中断でrun_finishedがなければ未完了。ImageOS/ImageVersionは観測値でありimage digestに代用しない。
runner_image_digest=null/not_collected、S4受入/formal許可はfalseのまま。

初回合成テスト12pass後、独立レビューP2「unittest.stop後に未実行を残して成功扱い」を検出。
shouldStopを成功条件から除外し、停止フラグも記録。未実行維持・exit1と通常failureのexit1を回帰で確認。
修正後14/14 pass（1.037秒）、既存SourceCollectorTests2/2 pass（0.550728秒）。
Windows実CLIは想定exit2、stdoutなし、report領域追加なし。workflow YAML/safety/diff-checkもpass。
再レビューでP2是正・新規P0〜P3=0。担当の実行/試験/native/編集なし、進捗ポーリングなし。
local-checks.jsonに16個の異なるtest IDsと各source hash・条件を保存した。

保存済み候補branch codex/s4-b1-windows-engineeringをGitHubへ新規pushし、
CI https://github.com/tyaro/banto-ai/actions/runs/34514721185 が3c69f9eに対して開始された。
本流mainの変更・merge・force push・Windows追加native枠の再開ではない。
初回は両jobともfailureで終了。1099 methods中966 pass/67 skip/66異常、unittest集計failure1/errors261。
259件の直接原因はLinuxにないctypes.get_last_errorを既存と仮定したfake mock、残り3件は後続assertの連鎖。
compile/safety/artifact保存pass、smoke/dataset quality/benchmarkは前段失敗によりskip。
両jobの単一JSONLを取得し、ZIPのAPI digest・source/workflow/run・全1099予定/開始/終了ID・集計を照合した。
未開始0、両minorの予定ID/順序・終了結果・skip ID/reasonがexact一致。失敗記録は保持する。

修正9846f52775cc5841fca63430adac7216cfbe516cは5ファイル8箇所のmockへcreate=Trueを追加。
実装・期待値・native skipの変更なし。関数を一時除去しWinDLL生成を拒否した専用processで、
初回異常66 methodsが66/66 pass、5.648702秒、failure/error/skip0。mock残留なし・元の関数を復元した。
linux-mock-regression.json（9393 bytes/hash e60b1b29b00b37fc150fc8a4bf3157f13352dc767b44a4c8a4fc254558e8eb2c）へ保存。
独立レビュー新規P0〜P3=0、担当の試験/native/ネット接続/編集なし。進捗ポーリングなし。
safety/diff-check pass。9846f52のCI34516991115もfailure。1099 methods中979 pass/67 skip/53異常、
unittest集計failure174/error42。関数mock欠落は解消したが、その先のfake launchでSystemRoot環境変数欠落が発生。
3.14 job logで原因と後続波及を確認。全ID・集計・source不変・未受入flag、両minor結果/skip記録の一致を照合。
新runの証拠は初回と別のartifacts/ci-evidence-2026-09-11/run-34516991115/へ保存した。

追加修正7870362d76eb26a6086222b3947aaa102bd22c79は共通fake driverの2行だけ。
ExitStack内でSystemRoot=C:\Windowsを仮設定し、終了時に元へ戻す。実装/native/恒久環境設定への変更なし。
get_last_error不存在・空の環境変数・WinDLL生成拒否の条件でも既失敗66 methodsが66/66 pass、5.652595秒。
mock属性/環境の残留なし、元の状態を復元。linux-host-independent-regression.jsonへ保存
（8961 bytes/hash eb810beb5b9c0f8b0131b3457598fda9f5e2b35debd5540a686be4db747807f5）。
独立レビュー新規P0〜P3=0、担当の試験/native/ネット接続/編集なし、進捗ポーリングなし。safety/diff-check pass。
7870362の3回目CI34518948145は両job成功で終了。
URL https://github.com/tyaro/banto-ai/actions/runs/34518948145 。Python3.12.14/3.14.7、各1099 methods実行、
1032 pass/67 skip、failure/error/expected failure/unexpected success0、stopped=false、source_unchanged=true。
compile/smoke/dataset quality/benchmark/safety/artifact保存もpass。全予定/開始/終了IDの重複・欠落なし。
両minorの予定ID/順序・終了結果・skip ID/reasonを照合。3回とも対象・skipは同一で、初回異常66件すべて最終pass。
新runのZIPはAPI digestと実SHA-256を照合してから単一JSONLを展開し、source/workflow/run/attempt/集計を確認した。
保存先artifacts/ci-evidence-2026-09-11/run-34518948145/。3.12の取得時EOFは別名の正しいZIPで回復し、CI再実行なし。
recovery-comparison.json（25642 bytes/hash 7bb1ab77ea30dbd886d93af8b1dbce64af83ba7e61f01a5322b32551e7edff13）へ
3回の条件・結果・修復66 IDsを保存。後続doc-only commitをCI実行revisionと混同しない。
このCI回数は終了済みWindows native試行枠とは別である。

初回実runtimeはUbuntu24.04 x86_64、Python3.12.14/3.14.7、GCC13.3.0、kernel6.17.0-1022-azure。
ImageVersion20260907.300.1は観測値、VM image digestではない。
skip67はWindows固有49、optional Capstone16、Toto2ローカルartifact不存在2。いずれもpassに数えない。
共有fixture payload自体のplatform間exact一致とS4完全受入は未完了のまま。
初回待機のunexpected EOFは接続エラーとして保持。CIを再実行する根拠には使っていない。
待機は60秒間隔/query timeout30秒/最大24回の単一API processで行い、すべて終了済み。
次の残件はVM image digest、共有fixture payloadのplatform間照合、Windows3.14.0の全native受入と正式OS条件、
B2 publisher/marker、runtime closureとconsumer凍結である。今回のCI成功でこれらを完了扱いにしない。

資源UTC2026-09-10T18:16:03Z RAM7.73 GiB/C107.94/D75.36、18:31:02Z RAM8.09/C107.93/D75.36。
修正選抜検証後18:55:08Z RAM8.13 GiB/C107.91/D75.36。
追加修正検証後19:15:10Z RAM7.19 GiB/C107.91/D75.36。owned待機Python private11.27MiB/working15.30MiB。
19:26:08Z RAM7.85 GiB/C107.90/D75.36、待機Python private11.27MiB/working15.40MiB。
最終19:30:17Z RAM7.68 GiB/C107.91/D75.36。待機exit0、今回の検証・取得・照合process終了。resources-final.jsonへ保存。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。点の変化でリーク有無を断定しない。
ローカル検証Pythonは終了済み。別project・既存失敗fixture・旧artifact操作、新runtime導入なし。

## 80. 2026-09-11 共有手計算fixtureの採取とLinux両minor比較

ユーザー「続けてください」を受け、§79の共有fixture payload照合を進めた。
基準3f3f7ad、実装036ecb474dc8fd975263e0ddbb387f5763750109。
[詳細記録](anomaly-multiseed-v0.3-s4-b1-shared-fixtures-2026-09-11.md)を参照。
既存19 methodsの試験中に29 payloadを採取。23はID・判定・保存JSON等の完全一致、
6はprofile/scoreの未丸め数値で、同じ型・構造とfloat相対/絶対許容差1e-12を要求する。
通常試験の計算を再利用し、非capture時はfactoryを評価しない。
payload各512KiB/合計4MiB、JSONL16MiB上限。process全体やfactory構築のメモリ制限ではない。
新形式ci-unittest.2のみ比較し、29件採取完了・各ownerのpassを必須にした。
別source/workflow/run/attempt、欠落・重複・不正hash・不正JSON・未完了・不一致を拒否する。
予定methodが未開始になるclass/module単位skipも保守的に拒否する。
両Linux試験jobの成功後に第3 jobが小さな2 JSONLを比較し、限定receiptを14日保存する。
全receiptはnot_completed/formal_permissionfalse/execution_authenticatedfalse。正式入口は閉鎖のまま。

新規13＋既存14の27 tests pass、1.355秒。実所有19 methods選抜も19/19 pass、37.531秒、skip0。
Windows3.14.0の実採取29/29、payload合計1,178,567 bytes、JSONL1,256,529 bytes。
local-hand-fixtures.jsonlには基準HEAD・未commit実装raw hash・Windows runtimeを明記。
保存先artifacts/ci-shared-fixtures-2026-09-11/。テストprocess終了0。
独立差分レビュー新規P0〜P3=0、担当の試験/native/ネット接続/編集なし、進捗ポーリングなし。
YAML構造/safety/diff-check pass。科学config/schema/registry、src実装、正式OS pinの変更なし。

036ecb4を候補branchへpush。CI34546440692は3 jobsすべてsuccessで終了。
URL https://github.com/tyaro/banto-ai/actions/runs/34546440692 。本流889cfc3は変更なし。
初回状態取得のunexpected EOFは接続障害でありCI再実行の根拠にしない。
待機は60秒/query timeout30秒/最大24回の単一process。完了metadata保存後にjobs取得で接続エラーとなりexit1。
取得だけを再開し、3 ZIPのAPI digest/bytes照合と単一member限定展開後に、raw JSONL/source/全ID/集計を再検証。
最終取得/照合processはexit0。CI receiptと手元再計算の全内容が一致した。
comparison-attempt1、python3.14-attempt1/2の0-byte失敗ZIPは保持するが証拠には使用しない。
検証済みZIPはcomparison-attempt2、python3.12-attempt1、python3.14-attempt3。CI再実行なし。

実LinuxはUbuntu24.04 x86_64/Python3.12.14・3.14.7、GCC13.3.0、kernel6.17.0-1022-azure。
各1112 methods中1045 pass/67 skip、failure/error/expected failure/unexpected success0、未開始・重複0。
compile/manifests/smoke/quality/benchmark/safety/upload、比較job各工程もpass。
前回成功1099 methodsの相対順序・結果・skip ID/reasonは同じで、追加13 methodsが両minor全pass。
skip67はWindows固有49/optional Capstone16/Toto2 artifact不存在2。各testと全29 payloadのowner/hashを照合済み。
両minorのpayload合計各1,178,567 bytes/最大249,753 bytes、29件すべてraw SHA-256も一致。
記録JSONLは3.12が1,992,469 bytes/hash df8351ae7258d5196c693f35bc90666e3b254fca8aa131abbd6a25ae3dd90b99、
3.14が1,992,511 bytes/hash 3390a4e74c6ab1722eaa7fb7fc779c1ad450fd7c95bbe9b8e3b7cb7496064517。
比較receiptは11,842 bytes/hash d04d10961ae7d9b14122c3a5e9798e1faa51e060ef13ccb53adea10b850702f3。
raw evidenceは同rootのrun-34546440692/へ保存。ImageVersion20260907.300.1は観測値でVM digestではない。

採取済みWindows19 methods/29 payloadも読取専用で比較し、両Linux minorへの58件すべてraw bytes一致。
採取時の5ファイルraw hashは036ecb4のGit blobと一致し、基準3f3f7adからの10ファイル差分にsrc変更なし。
windows-linux-selected-comparison.json（15,786 bytes/hash 79bb4603018b0f8c21f5d6d460c36dd40380ce15a77fe3b1f54505c8c63b72b6）へ保存。
これは選抜Windows fixtureの照合であり、Windows全回帰/native受入へ算入しない。
production比較器のLinux制限・未受入flagは維持。docs-only保存を実CI revisionと混同しない。

UTC00:25:35Z RAM空き7.97GiB/C107.66GiB/D75.36GiB、build26200.9445、
boot2026-09-09T10:43:08.5000000+09:00。resources-local.jsonへ保存。
00:30:09Z待機Python private18.61MiB/working25.22MiB。点の変化でリークを断定しない。
00:36:01Z RAM7.47GiB/C107.67GiB/D75.36GiB、待機Python private18.64MiB/working25.33MiB。
最終00:46:47Z RAM8.55GiB/C107.67GiB/D75.36GiB、build/boot同一。resources-final.jsonへ保存。
今回のローカル試験・待機・取得・照合processすべて終了し、追加バックグラウンド処理なし。
追加Windows native枠は以前の成功で終了したまま。B2/全Windows native/正式OS条件/VM image digest/
runtime closure/consumer凍結が残る。別projectや既存失敗fixtureは操作していない。

## 81. 2026-09-11 B2公開状態・完了印のpureモデル

ユーザー「続けてください」を受け、基準f9f3ea5からB2の実機接続前の契約モデルを具体化した。
実装savepoint e42a8e55768278ad10388b8f4017a308aa74ebd8。
[結果](anomaly-multiseed-v0.3-s4-b2-model-2026-09-11.md)と[設計](../anomaly-v03-publication-model-design.md)を参照。
tests/fixtures/anomaly_v03_publication_model.pyはI/Oなしの単一attempt journalとtoy marker部品。
prepare/verify_prepared/seal_payload/rename_payload/verify_final/commit_markerを固定順序で扱い、
別のteardown成功までcompleteにしない。操作を実行したことは証明せず、trusted callerの観測をモデル化する。
mutationの成功応答不明はunknown、検査失敗はfailed、未来slotはnot_startedを残す。
commit後teardown失敗はcommit confirmed/model stopped。未公開へ巻き戻さず再試行を認めない。
順序違反の握り潰し、二重操作、早い完了、後発resource stop、snapshot参照共有を反証試験した。

toy markerはsource revisionと全payloadのpath/bytes/hashから構成し、external marker pinとexact再構成で照合。
最大8 files、各64KiB/合計256KiB、path128文字、marker16KiB。case aliasとfile/ancestor衝突も拒否。
trusted inputsとpinを両方交換できるcallerには独立意味検査が必要。semantic検査・実行認証の主張なし。
全出力not_completed/formal_permissionfalse/execution_authenticatedfalse。
src、科学config/schema/registry、D2 current-only32/historical88、正式OS pinは変更していない。
既存S3 markerや本番publisherへ接続せず、native/ACL/token操作、正式campaign、B1枠の再開なし。

pure/fault16件pass、0.009秒。SourceCollector2＋D2 exact inventory1も3/3 pass、11.024秒。failure/error/skip0。
独立read-onlyレビュー2範囲とも新規P0〜P3=0。担当の試験/native/ネット/編集なし、進捗ポーリングなし。
最初のdiff-checkがtest末尾の空行を検出して除去。試験後の差はその1行だけとhashで照合。
repository safety/最終diff-check pass。小さな記録はartifacts/publication-model-2026-09-11/。
local-checks.json（3372 bytes/hash7071316a99db3707d7cbbd0b3e6ba2b5a968907a711b53c1610a6beef8740fb4）、
source-boundary-checks.jsonl、model-examples.json（8個のin-memory例）、savepoint-evidence.jsonへ保存した。
今回はローカルWindows3.14.0のみの検証。前回CIのpass数へ足さない。push/merge/CI起動なし、本流889cfc3不変。

開始UTC01:12:08Z RAM8.32GiB/C105.51GiB/D75.36GiB、最終01:28:35Z RAM8.38GiB/C105.56GiB/D75.36GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。resources-final.jsonへ保存。
C空きは今回開始前から前回107.67GiBより減少。原因は未調査で、この作業やリークへ帰属させない。
今回の検証/記録processは終了、常駐処理なし。別project・既存failure roots・共有runtimeへの操作なし。
次はnative adapterの具体設計、marker/親directoryの保護、保持handleによる同一物とno-replace、
競合/flush/close/resource失敗証跡を詰める。実機受入・正式OS整合・VM digest・runtime closure/consumerは未完了。

## 82. 2026-09-11 B2保持handle renameの注入backend部品

ユーザー「続けてください」を受け、基準be61da8から2つの固定renameの接続面を具体化した。
実装savepoint dd318aec56f8e43909ff6df6192d62e11aa914bd。
[結果](anomaly-multiseed-v0.3-s4-b2-rename-adapter-2026-09-11.md)と[設計](../anomaly-v03-rename-adapter-design.md)を参照。
tests/fixturesにのみ実装し、DLLロード/実Win32 backend/production入口は追加していない。

stage→payload、marker-pending.json→.completeは借用source handleからno-replace renameを要求する案。
親/sourceのvolume/file ID・種別・marker hashを固定し、begin前や再検査失敗後はbackendを呼ばない。
backendが停止・再入エラーを握り潰した場合もpendingの再確認で次操作を止める。
応答喪失はunknown、記録済みcommit後の異常はconfirmedのまま全体停止。再試行・自動cleanupなし。
既存S3 hardlink marker、D2のabsolute target経路は不変。handle所有終了は呼出側の別工程。
Win64要求のABIと公式RootDirectory記述を照合したが、相対renameの実API挙動は未確認。

独立したhandle/object/name表と別decoderによる新規18件＋既存model16件の34件がpass。
初回0.028秒、既知資源WinError1451〜1454の追加後は0.021秒。両回failure/error/skip0。
独立レビュー初回P2（WinErrorの資源分類漏れ）を是正。再レビューと最終小差分確認の新規P0〜P3は0。
資源分類は8/14/39/112/1450〜1455/1816、MemoryError/BudgetStop、cause/context/groupを含む。
既知集合の網羅範囲を限定し、未知エラーでも停止する。担当の試験/native/ネット/編集なし、進捗ポーリングなし。
repository safety / staged diff-check pass。試験対象4ファイルは確定Git blobとraw bytes一致。
全記録not_completed/formal_permissionfalse/execution_authenticatedfalse。旧Linux CIへ件数加算しない。

小さな記録はartifacts/rename-adapter-2026-09-11/へ新規保存。
initial-checks.jsonl 24222 bytes、final-checks.jsonl 24224 bytes/hash63cfad456db4af0c3f6a9e56fcef7619e358bd958094ebbafa1e4dde71ca846f。
savepoint-evidence.jsonにsource/hash一致、確定commit、初回と最終の区別、レビュー是正を記録した。
開始UTC02:46:02Z RAM8.54GiB/C105.38GiB/D75.36GiB、最終03:04:14Z RAM7.60GiB/C105.37GiB/D75.36GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。resources-final.jsonへ保存。
点のRAM変化を本作業のリークへ帰属させない。試験・記録process終了、常駐処理なし。
別project/旧failure fixture/共有runtimeへの操作、新runtime導入、push/merge/CI起動なし。本流889cfc3不変。

次はnative backendのfixture/全ancestorの保持と所有終了、marker/親directory保護、
payload子handleとdirectory renameの両立、flush/close失敗時のprivate bytes保持を具体化する。
実機試行の範囲・資源上限を具体化してから接続し、前回成功で終了したB1枠を流用しない。
実Win32受入、正式OS整合、VM image digest、runtime closure/consumer、S4受入は未完了。

## 83. 2026-09-11 B2終端handle解放・権限接続設計

ユーザー「続けてください」を受け、基準e3317f9から最大32の所有handleの終端解放を実装した。
実装savepoint 8f96f3d12b9ec2d2ec01460a28d9730b0ab80bc1。
[結果](anomaly-multiseed-v0.3-s4-b2-handle-owner-2026-09-11.md)と[設計](../anomaly-v03-handle-lifecycle-design.md)を参照。
tests/fixtures/anomaly_v03_handle_owner.pyは注入CloseHandle backendのみ。実取得/ACL/flush/native操作なし。

構築成功までcaller所有。親indexの順序・同volume・同handle/identity重複なしを検証して管理slotを確保する。
終端finishは公開途中なら先に停止し、子から親へ各handleのcloseを1回ずつ試す。
失敗後も別handleの解放は試みるが、公開・再検査・path削除・未知handleの再closeを行わない。
close応答喪失後に同じ数字が別handleへ再利用される反例を試験し、二度目のcloseを抑止した。
元primaryは同じ例外を再送出、後発resource stopは昇格。commit確定と公開停止は保持する。

新規17＋既存34＝51件pass、0.043秒。独立レビューP2は、teardown記録失敗後のstopも失敗すると
元primaryを隠す経路。二次障害も捕捉し、ownerのjournal_finalization=unknownを残すよう是正。
primary有無×記録前後の4 casesを1 methodとして追加し、最終18＋34＝52件pass、0.052秒。
両回failure/error/skip0。raw journalにcompleteが残る故障でも例外とowner unknownを無視して成功にしない。
再レビュー新規P0〜P3=0、担当の実行/native/ネット/編集なし、進捗ポーリングなし。
repository safety/staged diff-check pass。最終試験の6 source filesは確定Git blobとraw bytes一致。

設計書にwriterのGENERIC_WRITEによるflush→照合→close、検査pin取得とDACL固定、
子handle事前解放、stage/markerの保持DELETE handle、最終名確定、private証跡を具体化した。
権限/share条件は候補で、保護後の相対renameは実機未確認。既存祖先のDACLを変える案ではない。
今回の終端ownerに取得途中の失敗追跡・事前close・借用排他・安全なfixture清掃があるとは扱わない。
全記録not_completed/formal_permissionfalse/execution_authenticatedfalse。旧Linux CIへ件数加算なし。

新規ignored root artifacts/handle-owner-2026-09-11/に初回/最終JSONLとsavepoint-evidence.jsonを保存。
最終JSONL36939 bytes/hash936eb7df0034d0935581306856d1eec562f54260e1d38e6311d438710071d9bb。
開始UTC11:00:16Z RAM5.52GiB/C103.02GiB/D75.20GiB、最終11:09:53Z RAM5.49GiB/C103.02GiB/D75.20GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00を記録。resources-final.jsonへ保存。
開始前から前回より空きが減っていたが、本作業やリークへ帰属させない。短い試験processはすべて終了。
常駐処理・別project/旧failure fixture/共有runtime操作なし。push/merge/CI起動なし。本流889cfc3不変。

次は取得途中失敗の所有移管、writer/子handle事前解放と後続操作禁止、private証跡の保存予算を実装し、
native試行の具体的な対象・時間/メモリ/空きdisk等の上限をレビュー可能にする。
B1終了済み試行枠を流用しない。native全受入、正式OS整合、VM digest、runtime closure/consumer、S4は未完了。

## 84. 2026-09-14 連続稼働終了とB2公開前の保存・選択解放

ユーザー「連続稼働テスト終わりましたので進めましょう」を受領。
別projectとの同時負荷を避ける追加抑制は解除し、通常のRAM/disk確認と各所のsavepointを継続する。
B1の終了済み試行枠や正式受入条件を更新・再開する通知とは扱わない。

基準5c76c58、実装savepoint b9b7fb168641cf078dcb5fa5692f13e709fabedf。
[結果](anomaly-multiseed-v0.3-s4-b2-prepublication-2026-09-14.md)と[設計](../anomaly-v03-prepublication-design.md)を参照。
ownerへ同期borrow排他とprepare/seal_payload/verify_final中の各1回の選択解放を追加した。
終端finishはclosed/unknownを再closeせず、残るownedのみを解放する。
証跡barrierはmarkerと全payload bytes、pin/descriptor観測を固定し、journalの期待marker hashと全owner pinへ
exact再構成照合してから保存する。保存確認前に解放せず、root/rename等のprotected slotは解放しない。
各記録512KiB/3記録合計1.5MiBまで。観測/実保存の認証ではなく、全受入flagは未完了のまま。

新規19＋既存52＝71件pass、0.079秒。独立レビュー欠陥0、補強案により同じowner/barrierで3段階の保存・解放、
既存BoundRenameのpayload/.complete両操作、終端finishを通す1 methodを追加した。
最終20＋既存52＝72件pass、0.050秒。両回failure/error/skip0、最終レビュー指摘0、進捗ポーリングなし。
1 methodだけ通常tempfileのexclusive保存/readbackを実施し、終了時に清掃。native private DACL/flushの証拠ではない。
repository safety/staged diff-check pass。最終試験の8 source filesは確定Git blobとraw bytes一致。
src/科学config/schema/registry/正式OS pinは不変。旧Linux CIへ件数加算なし。

新規ignored root artifacts/prepublication-2026-09-14/へ初回/最終JSONL、資源、savepoint-evidence.jsonを保存。
最終JSONL51679 bytes/hash160e9ea2f21cfefc0becc008fcce22a72ea111f3f2e8d1bd4ca6fd9fc9158b34。
開始UTC06:45:05Z RAM8.37GiB/C105.24GiB/D59.78GiB、最終06:55:54Z RAM8.39GiB/C105.21GiB/D59.78GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00を記録。
D空きは開始前から減少していたが原因未調査で、本作業やリークへ帰属させない。
試験・記録processは終了。常駐処理、別project/旧failure fixture/共有環境操作、push/merge/CI起動なし。本流889cfc3不変。

次は取得途中失敗の所有移管とwriter解放後の再取得、新規native private sinkの保存・途中失敗証跡を実装する。
今回のownerは構築時に固定slotを渡す前提で、実取得途中の追跡やnative private保存を実装したものではない。
限定native試行の対象・時間・資源上限を具体化して接続する。B1終了枠の流用なし。
native全受入、正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。

## 85. 2026-09-14 B2取得追跡とprivate保存の限定実機確認

ユーザー「続けてください」を受け、基準af97323から取得途中の追跡と実private保存を追加した。
実装・実行savepoint **847de63d63e3ec0cdc9b2063401c19be63533241**。
[結果](anomaly-multiseed-v0.3-s4-b2-private-sink-2026-09-14.md)と[設計](../anomaly-v03-private-sink-design.md)を参照。
別project連続稼働の追加負荷制約は解除済み、通常のRAM/disk確認とsavepointを継続する。

TrackedOpenはraw handleを観測前に記録し、取得後失敗を一度だけcloseする。
未取得/未記録のraw値を推測せず、応答喪失時も再closeしない。動的な既存ownerへの移管は未実装。
WindowsPrivateSinkは保持祖先の下で新規private root/fileを作成し、
SD検証→全量write→flush→同handle読戻し→SD再検証→closeを追跡する。
記録は3個まで・各512KiB/計1.5MiB。既存root/fileの上書きや自動清掃なし。

新規14＋既存72＝86件pass、3件補強後89件、資源停止回帰追加後は新規18＋既存72＝90件pass。
全回failure/error/skip0。最終正本corrected-checks.jsonl、final-checks.jsonlは89件時点の中間記録。
独立レビューP2計5件（資源WinError分類、失敗token出力所有、close再入停止の握り潰し、
資源停止後の通常報告、監視起動直後の所有空白）を是正。最終再確認の新規P0〜P3=0。
担当はread-only、試験/native/編集なし、進捗ポーリングなし。
repository safety/staged diff-check pass。最終試験source等14 filesを確定Git blobとraw bytes一致確認した。

clean HEADと監視script hashをlaunch-plan.jsonへ固定し、別の最大2回枠で1回目だけ実行。
UTC07:37:55、Windows26200.9445/CPython3.14.0 Win64、外側0.400秒で成功。
新規artifacts/private-sink-2026-09-14/attempt-1/private-evidenceに合成JSON3個/計478 bytesを保持。
private SD、exact inventory/bytes/hash、追跡14 handlesと照会tokenのclose、worker exit0を確認した。
観測private最大17.84MiB/OS peak working25.64MiB、資源停止なし。
成功で今回枠を終了し、2回目の未使用枠を繰り越さない。B1終了枠も再開しない。

workerが1秒未満で終了したため外側samplesは0、worker内5境界の観測を保存。
stderrにfinally内returnのSyntaxWarning2件を保持。監視console要約のnull表示も記録した。
成功判定は実値の入ったsupervision JSONとprobe-resultの別途照合による。表示修正のための再試行はしない。
Start-Process内部で起動後に返却が失われる場合や、全期間の最大メモリ/長期リーク不在の保証はない。

ignored root artifacts/private-sink-2026-09-14/に初回/中間/最終JSONL、native/監視/資源/各private bytesを保存。
corrected-checks.jsonl 64466 bytes/hash e2b4457c040ab38acdbd2314e977071880a395dfe5a80860631b6825f15bdd93。
savepoint-evidence.json 7624 bytes/hash f5b19ea0da77f228472fccaf7ac98fb0b8d9f9c9639ddbaaefb6cd59d01e5acf。
manifest以外の16記録は計210654 bytes、記録用scriptを含む。実記録のhash表は結果書を参照。

開始UTC07:13:01 RAM5.37GiB/C106.74GiB/D71.08GiBは当時の取得値から転記。
実機前の保存07:34:32 RAM9.13GiB/C108.01GiB/D87.12GiB、
最終保存07:38:45 RAM8.15GiB/C107.45GiB/D87.12GiB。
build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。
点の増減を本作業やリークへ帰属させない。worker・短い検証process終了、常駐処理なし。

今回は正常private保存の実機確認。実nativeの失敗/競合試行、rename/.complete、token変更は実行していない。
全acceptance/formal/authenticated flagsは未受入のまま。src/科学config/schema/registry/正式OS pin不変。
旧Linux CIへ件数加算なし。新runtime/共有環境/別project/旧failure roots操作なし。
push/merge/CI起動なし、本流889cfc3 cleanを維持。

次は取得済みpinの既存ownerへの移管、writer解放後の再取得、実pin/descriptor観測からの証跡構築と
EvidenceBarrier→今回sinkの接続を具体化する。probeの構文警告・監視console要約は次の改修時に整備する。
native全受入、正式OS整合、VM digest、runtime closure/consumer凍結、S4受入は未完了。

## 86. 2026-09-14 B2管理移管と実観測prepare証跡

ユーザー「続けてください」を受け、基準19e474bから取得済みハンドル管理と実観測保存を接続した。
実装・実行savepoint **9172afb13d1d2b2afc9034c6d352639d47d7c3ec**。
[結果](anomaly-multiseed-v0.3-s4-b2-observed-evidence-2026-09-14.md)と[設計](../anomaly-v03-observed-evidence-design.md)を参照。

AcquiredOwnerはcaller保持receiverに全状態を確保し、単一active切替で固定batchを管理移管する。
切替前の失敗はcaller所有、切替後の返却喪失も保持receiverで終了できる。
raw close主体は各TrackedOpenで一元化し、移管元のclose/acquire・二度目adoptを拒否/停止する。
capture_recordは全live slotsを借用し、実bytes/identity/private SDと採用時pinを照合して
build_evidence→EvidenceBarrier→WindowsPrivateSinkへ接続した。

独立レビューP2（停止後にも観測IOが継続）を是正し、各境界とownerのみのresource stopを回帰確認した。
再adopt拒否の握り潰しも補強。最終独立確認の新規P0〜P3=0、担当はread-only、進捗ポーリングなし。
記録済み初回107件pass/0.102秒、最終は新規18＋既存90＝108件pass/0.084秒、両回failure/error/skip0。
その前のテスト整備時の配置ミスNameErrorは是正済み。最終source等17 filesを確定Git blobとraw bytes照合。
repository safety/staged diff-check/PowerShell構文確認pass。

clean HEADと監視hash固定後、新規artifacts/observed-evidence-2026-09-14/attempt-1だけで限定実機を実行した。
source-fixtureにfacts.json45 bytes＋marker-pending.json415 bytes、実観測を含むprepare.json2880 bytesを別private領域へ保存。
source root/file3 slotsを管理移管し、barrier保存後のfile選択解放、残るroot/祖先/sinkの終了を確認。
source13＋sink12＝25 tracked handles、照会token2個close、worker exit0、外側0.355秒。
終了後source exact2 files/証跡exact1 file・raw bytes/hash一致。stderr0 bytes、監視console要約のnull表示を修正済み。
旧probeのfinally内return警告も解消。旧実行済みscript/原記録は不変で、前回manifestの全artifact hashを照合した。

journalはprepare=unknown/model_status=stopped/failure_reason=operation_error、teardown=succeeded、
commit_observation=not_started。prepare中の局所確認後に意図的に停止した結果で、全公開工程の成功ではない。
今回の最大2回枠は1回目成功で終了、未使用枠の繰越なし。前回private保存枠/B1終了枠の再開なし。
DACL seal・writer再取得・rename/.complete・独立token操作・native実故障/競合試験は行っていない。

新規ignored rootに初回/最終JSONL、native/監視/資源/各bytes/manifestを保存。
final-checks.jsonl78019 bytes/hash4befd0bdc4898dafd641896805db9c45a4e969abcd83f03802096a4999306c02。
savepoint-evidence.json7495 bytes/hash2b86f64832772d21e6640ec1dd0c4cd97c6c1cbb13fc46d5a7aacf4515e67e95。
manifest以外16記録の論理bytesは205392。全hash表は結果書を参照。

開始UTC07:55:38 RAM8.42GiB/C107.75GiB/D87.12GiBは当時取得値から転記。
実機前保存08:07:10 RAM8.66GiB/C107.75GiB/D87.12GiB、最終08:09:16 RAM7.86GiB/C108.28GiB/D87.12GiB。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00。観測private最大18.43MiB/peak working26.26MiB。
worker内4境界の観測、外側は1秒未満のためsamples0。長期リーク不在・全期間最大メモリは保証しない。
点の増減を本作業へ帰属させない。worker・検証process終了、常駐処理なし。

次はwriter解放後に権限を変えた再取得、元identity/bytesとの対応、slot寿命設計を進める。
固定batch管理移管を動的slot追加と混同しない。後続phaseの実観測、seal/相対rename・実故障受入は残る。
全acceptance/formal/authenticated flagsは未受入。正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
src/科学config/schema/registry/正式pin、本流889cfc3不変。旧CIへ件数加算なし。
push/merge/CI起動、新runtime/共有環境/別project/旧failure roots操作なし。

## 87. 2026-09-14 B2 writer解放後のreader再取得

ユーザー「続けてください」を受け、基準c50aabcから読取り専用の再取得と実権限観測を接続した。
実装・実行savepoint **cbb5a8263eef1be110ab86333a986dca9f4e87ba**。
[結果](anomaly-multiseed-v0.3-s4-b2-reader-reacquisition-2026-09-14.md)と[設計](../anomaly-v03-reader-reacquisition-design.md)を参照。

ReacquiredReadersは元writerの確定closeを条件に別世代のTrackedOpenを取得し、
元identity/bytes/private SDと照合する。親root借用中に新readerを全終了する。
既存ownerのclosed slotは復活させず、raw番号再利用でも世代別にclose主体を保つ。
要求値に加えてNtQueryObjectで実GrantedAccessを確認する。DACL変更なし。
新readerのlive handleを後続seal/renameへ移管する機能や動的slot追加は今回の範囲外。

記録済み初回123件pass/0.116秒、最終は新規16＋既存108＝124件pass/0.119秒。
両回failure/error/skip/expected failure/unexpected success0。
componentとscenario接続の独立レビューは各新規P0〜P3=0、read-only、進捗ポーリングなし。
最終source等20 filesを確定Git blobとraw bytes照合。repository safety/staged diff-check/監視構文確認pass。

clean HEADと監視hash固定後、新規artifacts/reader-reacquisition-2026-09-14/attempt-1で限定実機確認。
writer2個の実権限0x12019fからreader2個の0x120081へ縮小し、同じidentity/bytes/SDとの照合に成功。
source13＋sink12＋new reader2＝27 tracked handlesと照会token2個close、worker exit0、外側0.400秒、stderr0 bytes。
source exact2 files計460 bytes、private prepare.json2880 bytes、終了後inventory/raw/hash一致。
journalはprepare=unknown/model_status=stopped、teardown=succeeded、commit=not_startedの局所確認。
今回の最大2回枠は1回目成功で終了、未使用枠の繰越なし。旧batch/B1終了枠の再開なし。

新規ignored rootにJSONL/native/監視/資源/実bytes/manifestを保存し、前回manifest全artifact不変も確認した。
final-checks.jsonl90397 bytes/hash e400e7c0c2f5cb8c2f881bbee3eaa2506fab1eb9cc040fb6ebf230b4a4d8f5d8。
savepoint-evidence.json8320 bytes/hash 11fbba243086a44670ffe23f3000ab673299b99447b084fd4a0a6db613bbbb4a。
manifest以外17記録の論理bytesは259832。その他hash・観測範囲は結果書を参照。

開始UTC08:15:31 RAM8.64GiB/C109.48GiB/D87.12GiBは当時取得値から転記。
実機前保存08:26:21 RAM7.61GiB/C119.94GiB/D87.12GiB、最終08:28:08 RAM7.78GiB/C119.96GiB/D87.12GiB。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、正式OS pinは変更していない。
worker内4境界でprivate最大18.17MiB/working・peak working25.94MiB、外側は1秒未満でsamples0。
C空きの増加原因は未調査。点の増減を本作業・リーク不在へ帰属させない。
worker・短い検証processは終了、常駐処理なし。長期リーク不在や全期間最大メモリの証明ではない。

次はseal/相対renameに必要な権限とlive handle寿命、DACL固定後のreadbackを具体化する。
短いreader世代の正常実機確認と、後続公開phase・実native故障/競合の受入を分ける。
全acceptance/formal/authenticated flagsは未受入。正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
src/科学config/schema/registry/正式pin、本流889cfc3不変。旧CIへ件数加算なし。
push/merge/CI起動、新runtime/共有環境/別project/旧failure roots操作なし。

## 88. 2026-09-14 B2 file権限固定と保持世代

ユーザー「続けてください」を受け、基準c73a602からfileのDACL固定と保持handleでの継続処理を接続した。
実装・実行savepoint **48f701f51fdf3d8e4312dc097b9a6d8bc18066f8**。
[結果](anomaly-multiseed-v0.3-s4-b2-file-sealing-2026-09-14.md)と[設計](../anomaly-v03-file-sealing-design.md)を参照。

SealedFilesはwriter確定close後、payload0x160081/marker0x170081を別世代で取得する。
全対象の元ID/bytes/private SD・実権限を検査してから、各対象再検査→同handleでfrozen DACL設定→読戻し。
ID/bytes・owner/group/integrity/policy不変と、固定後もWRITE_DAC/marker DELETEを保持することを確認する。
全検査後だけ、親borrowと新世代handleがliveの同期continuationへ進み、戻って全新世代をcloseする。
旧closed writer slotsは復活せず、動的slot追加/恒久移管は導入しない。今回continuationは観測だけでrenameなし。

SetSecurityInfoのDWORD結果、NULL/defaulted DACL拒否、内部native境界guardとLocalFree1回を追加。
応答喪失/途中失敗/親停止/再入後は後続IOを止め、元例外・後発資源停止を保持する。
部品52件pass/0.075秒、記録済み新規19＋既存124＝143件pass/0.168秒、failure/error/skip等0。
initial-checks.jsonlを最終根拠とする。以後コード変更なし、重複試験なし。source等23 filesをGit blob/raw照合。
本体/追加scenario・監視・仕様の独立レビューは各新規P0〜P3=0、read-only、進捗ポーリングなし。
repository safety/staged diff-check/PowerShell構文確認pass。

clean HEADと監視hash固定後、新規artifacts/file-sealing-2026-09-14/attempt-1だけで限定実機成功。
新規2 filesでfrozen DACL設定/同一物・bytes・SD読戻し、親root不変、固定前後の実権限一致を確認した。
source13＋sink12＋new files2＝27 tracked handlesと照会token2個close、worker exit0、外側0.555秒、stderr0 bytes。
source exact2 files計460 bytes、prepare証跡2880 bytes、終了後inventory/raw/hash一致。
journalはprepare unknown/stopped、teardown succeeded、commit not_started。全公開phaseの成功に読み替えない。
最大2回枠は1回目成功で終了、未使用繰越なし。旧batch/B1枠再開なし。

新規ignored rootに試験/native/監視/資源/原bytes/manifestを保存、前回reader manifest全artifact不変を照合。
initial-checks.jsonl103693 bytes/hash 3f78ca2784357f6868a644b65b62fd4879b5f8636b29ae9b47cd9907d44f3b9d。
savepoint-evidence.json8005 bytes/hash e9809b687bcf368f13720e9b0bdba6bdd10f3e1ee3da872ec862294445a92edb。
manifest以外15記録の論理bytesは166713。全hash表は結果書を参照。

開始UTC08:38:48 RAM7.56GiB/C119.96GiB/D87.07GiBは取得結果から転記。
実機前08:49:04/最終08:49:37はともにRAM7.83GiB/C119.95GiB/D91.03GiB。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、正式pin不変。
worker4境界でprivate最大18.05MiB/working・peak25.83MiB、最後0.084秒。外側samples0。
D空き増加の原因は未調査。資源の増減を本作業/リーク不在へ帰属させない。worker・検証process終了、常駐なし。

次はstage/root directoryの権限取得/DACL固定と保持source/parentでの相対renameを進める。
今回rootはprivateのまま。親経由delete等の全保護、独立token実操作、子解放後directory rename、
後続phase証跡更新、実native故障/競合は未完了。全acceptance/formal/authenticated flagsは未受入。
正式OS整合、VM digest、runtime closure/consumer、S4受入は残る。
src/科学config/schema/registry/正式pin、本流889cfc3不変。旧CIへ件数加算なし。
push/merge/CI起動、新runtime/共有環境/別project/旧failure roots操作なし。

## 89. 2026-09-14 B2 directory固定と相対renameの2回枠終了

ユーザー「続けてください」を受け、基準9375b3eからstage/rootのDACL固定と保持親からの相対renameを接続した。
初回実装・実行 **a20988688e65d829a6619c399813da2a319d22a2**、修正実装・実行 **91cd5acfc29b9186739d3e99831f6f19ede08502**。
[結果](anomaly-multiseed-v0.3-s4-b2-directory-rename-2026-09-14.md)と[設計](../anomaly-v03-directory-rename-design.md)を参照。

新規root0x1600a7/stage0x1700a1を初回から保持し、stage内facts.json45 bytesだけを作成。
prepare保存→writer close→payload-only SealedFiles0x160081でfile固定/読戻し→証跡保存→全子close→
stage/root固定/同一物・SD・実権限読戻し→第3証跡保存→同じ保持親を使うstage→payloadの順で実行した。
require_marker=Falseの明示利用だけ1〜8 payloadを許し、既定marker必須は維持する。marker file/.completeは作っていない。
CWDは新規attempt親で、保持source-fixture rootとは別。3証跡は2817/2886/3014 bytesで、verify_final名もrename前記録。

初回SetFileInformationByHandle(class3/36 bytes)はWinError87。
インストール済みKernelBase.dllの静的解析でDOS→NT名変換と入力RootDirectory複写を確認し、
絶対名＋非NULL親の組合せが87を説明するという推定を記録。動的内部引数/NTSTATUSの証明ではない。
解析version10.0.26100.9278/SHA becad014fb8efa8cb5e314931cca92778ad42c649b12a6909632cacd68af4f40。
追加のDLL関数/renameは呼ばず、既存Capstoneを使用して新runtimeは追加しなかった。

2回目は明示WindowsNtDirectoryBackend(class10/40 bytes/IOSB16)に切替え、新規attempt-2でNTSTATUS0xc0000022→WinError5。
native pending=false/completion_unknown=falseで同期失敗を受領。operation.renameは成功未確認のpendingで停止した。
両回ともfile/stage/root固定と3証跡保存は成功し、実権限0x1600a7/0x1700a1が固定前後一致。
各source13＋sink14＋file1＝28 tracked handlesとtoken2個close、worker exit1。外側初回1.208秒/2回目0.441秒、stderr0。
終了後source検査・hash取得・削除を行わず、最終読取りhandles0/postclose一致0。
journalはprepare unknown/stopped、teardown succeeded、commit not_started。全公開やrename成功として記録しない。
**最大2回枠は使用済みで終了。3回目・初回fixture再操作・旧batch/B1再開・自動fallbackなし。**

初期部品確認のowned import漏れ12 NameErrorを修正後54件pass/0.068秒。
記録済み162件pass/0.220秒→NT切替166件pass/0.218秒→中断時寿命修正167件pass/0.366秒。
最終新規24＋既存143、failure/error/skip等0。final-checks.jsonlが最終根拠。
独立レビューP2はNT呼出直後の中断で入出力buffer寿命を失う可能性。呼出前completion_unknownを追加し、
正常非pending返却の検証後だけ解除、それ以外はbuffer保持・固定通知・所有終了後worker exit80へ接続した。
再レビュー新規P0〜P3=0。本体/scenario先行レビューも各0、read-only、進捗ポーリングなし。
source24＋補助2 filesは最終raw/Git一致、初回sourceは初回Gitへ照合。166件の中間hashは最終Git一致を主張しない。
repository safety/差分検査/PowerShell構文確認pass。コード変更のない重複試験は省略した。

ignored artifacts/directory-rename-2026-09-14/へ保存。初回receipt12 artifacts・前回file-sealing15 artifactsの不変を照合。
final-checks.jsonl120883 bytes/hash c22784dfc37249bd233229ff3ac148ab53cb311b7f3e0737fe2787ec5491ba26。
savepoint-evidence.json27893 bytes/hash 4aa5e974f3211bf328c2c388818c01f0fcdf0eeff3df18562568280ad91edfbe。
manifest以外34記録の論理bytes548113。失敗source treeを走査せず明示証跡だけ保存した。

初回前UTC09:08:09 RAM7.40GiB/C119.67GiB/D90.94GiB、2回目前09:21:30 RAM9.50GiB/C119.70GiB/D87.92GiB。
終了後09:22:23 RAM9.49GiB/C119.71GiB/D87.92GiB。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、正式pin不変。
各worker2境界、private最大初回18.71MiB/2回目18.68MiB、working26.61/26.60MiB。初回外側1 sample working26.68MiB、2回目samples0。
資源停止なし、worker・検証process終了、常駐なし。空きの変化原因は未調査で、本作業やリーク不在へ帰属させない。

次は親保護とpayload rename/marker commitの順序を再設計する。
親frozenの内部target open拒否が候補だが、同じNT要求で親private/frozenだけを比較した証明はまだない。
その小比較仕様と、親private時間帯のadd/delete競合・完了印前保護をpure modelで具体化し、
実装/review/source固定を経て新しい別枠を作る。root固定を遅らせるだけで受入にしない。
既存6工程/S3 hardlink marker/D2 rename契約を変える必要がある場合は具体案として判断点を示す。
rename後検査、marker/全phase、独立token実操作、native故障/競合、正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
全acceptance/formal/authenticated flagsは未受入。src/科学config/schema/registry/正式pin、本流889cfc3不変、旧CIへ件数加算なし。
push/merge/CI起動、新runtime/共有環境/別project/旧failure roots操作なし。

## 90. 2026-09-14 B2 親policy比較の成立と2条件枠終了

ユーザー「続けてください」を受け、基準594bf1dから親DACLの条件差を比較した。
実装・2条件の実行savepoint **a31ae9b5119ed28c5271502d252ce2425c4b448e**。
[結果](anomaly-multiseed-v0.3-s4-b2-parent-policy-rename-2026-09-14.md)と[設計](../anomaly-v03-parent-policy-rename-design.md)を参照。

DirectoryRenameの既定frozenは維持し、privateを明示する比較modeを追加した。
親DACL設定だけを省き、stage/file固定、全子close、親元ID/private SD完全一致、実権限、証跡後再検査を残す。
親状態はprivate_verified。終了後読取りもrootは選択policy、payload/factsはfrozenとして元ID/bytes/SDを照合する。
新規parent_policy_probeは条件1private/条件2frozenを固定し、監視側が1の完全成功・同一revision・終了を確認したときだけ2を許す。

初期29件の故障後finish再送出の期待漏れ2件を修正し29件pass/0.045秒。
記録済み新規5＋既存167＝172件pass/0.181秒、failure/error/skip等0。initial-checks.jsonlが最終根拠。
コード/probe/監視/仕様の独立レビューはP0〜P3=0、read-only、進捗ポーリングなし。
25 source＋補助2 filesのraw/Git blob一致、repository safety/差分/PowerShell構文確認pass。以後コード変更・重複試験なし。

clean HEAD・source/監視hash固定後、新規artifacts/parent-policy-rename-2026-09-14/で2条件を順次実行。
root0x1600a7/stage0x1700a1、writer0x12019f→file0x160081、facts.json45 bytes、同じNtSetInformationFile/class10/40 bytes。
非NULL保持親・leaf payload・no-replace、CWDは別の新規attempt親、stage/fileは両方frozen。
条件1privateはNTSTATUS0/rename confirmed、終了後root/payload/factsの3 objects一致、31 tracked handles/token2個close、worker exit0/0.454秒。
条件2frozenはNTSTATUS0xc0000022/WinError5を再現、rename pendingで停止、28 tracked handles/token2個close、worker exit1/0.392秒。
両方native非pending/completion_unknown=false、stderr0、資源停止なし。条件2sourceの終了後再検査なし。
証跡3個はprivate2817/2886/2950＝8653 bytes、frozen2817/2886/3014＝8717 bytes。第3予約名もrename前記録。
marker file/.completeなし、journalはprepare unknown/stopped・teardown succeeded・commit not_started。
親policyと成否の差を観測したが、内部拒否箇所のtraceや親private期間のadd/delete拒否の証明ではない。
**各条件1回、最大2条件枠は終了。再試行・第3条件・繰越・前回batch/B1再開なし。**

ignored新規rootへ原記録/監視/資源/manifestを保存。成功条件1だけ原bytesを再照合し、条件2/前回失敗sourceは再検査・再利用・削除なし。
前回directory-rename manifestと34 artifactsのhash不変を照合した。
initial-checks.jsonl124681 bytes/hash 4b3cc498c2c47b88e4f4e04d23ee02df157130f02e7d8fd8f3119657cb049a03。
savepoint-evidence.json13938 bytes/hash 3949580d5f6b81787b7d9aad4d8bba10bd7101edc3b712b63ddd7975aa0ac93c。
manifest以外24 artifactsの論理bytes226568。失敗source走査なし。

開始前UTC09:40:05 RAM9.25GiB/C119.70GiB/D87.92GiB、条件2前09:40:36 RAM9.24GiB、終了後09:41:28 RAM9.25GiB。
C/Dは各点で同じ丸め値。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和・正式pin不変。
private最大18.03MiB、working最大26.04/25.98MiB、各4/2境界、外側samples0。両worker・検証process終了、常駐なし。
点観測を全期間最大値・長期リーク不在の証明にしない。

次は公式の同一親内NT rename（単一leaf/RootDirectory=NULL）を別adapter候補として設計する。
保持rootの同一物・寿命検査を残し、元source/親結合、固定wire、異なるCWD、非上書き、故障後停止をpure/faultで具体化する。
親frozen下での成功・競合耐性は未確認。新規仕様/review/source固定後の別枠とし、今回枠への3回目・失敗後fallbackは行わない。
既定保持親形式・既存6工程/S3 hardlink marker/D2契約を変更しない。この候補が不成立なら親保護/marker順序と競合の具体案を判断点として示す。
親全保護、marker/全publisher、独立token、native故障/競合、正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
全formal/authenticated flags=false、acceptance=not_completed。src/科学config/schema/registry/正式pin、本流889cfc3不変、旧CIへ件数加算なし。
push/merge/CI、新runtime、共有環境、別project、旧failure rootsへの操作なし。

## 91. 2026-09-14 B2 同一親内NT leafも拒否、1回枠終了

ユーザー「続けてください」を受け、基準7aa4d30から親frozenを維持する別adapterを実装した。
実装・native savepoint **685d670499cdc42e72d3f3ab948349fea2f4281c**。
[結果](anomaly-multiseed-v0.3-s4-b2-same-parent-rename-2026-09-14.md)、[設計](../anomaly-v03-same-parent-rename-design.md)、
[次の未採用順序案](../anomaly-v03-publication-order-options.md)を参照。

SameParentDirectoryRenameは親/source/全子の結合、全子close、stage/root固定・実権限・元ID/SD、証跡後再検査を継承する。
parent_policy=frozen固定、wireだけNULL RootDirectory＋固定payload leaf、直接NtSetInformationFile/class10/40 bytesへ渡す。
専用backendと旧保持親backendは互いのwireを拒否し、旧encoder/BoundRename/S3/D2/6工程/productionは不変。
親private比較modeとの併用不可、entry/監視ともattempt-2不可。completion_unknown/buffer寿命・資源停止は既存と共用。
部品39件pass/0.041秒、記録済み新規10＋既存172＝182件pass/0.186秒、failure/error/skip等0。
initial-checks.jsonlが最終根拠、以後コード変更・重複試験なし。実装/probe/監視/仕様の独立P0〜P3=0、read-only、ポーリングなし。

実装commit後のclean検査で、前回親policy結果書に今回の変更外の文書差分を検出した。
元70b0ではworkerを起動せず、原bytes/patchを保存し差分を上書きしなかった。その差分は今回commitに含めない。
C:\Users\TKent\.codex\worktrees\same-parent-685d670\banto-ai を同じ685d670のclean detached checkoutとして新規作成し、nativeだけ分離した。
テストは70b0、nativeは別領域。28 source＋補助2 filesが両領域/Git blobに一致し、clean HEAD/監視hashを固定。
追加tracked448 files/論理5603301 bytes。原文保存8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621。

新規artifacts/same-parent-rename-2026-09-14/attempt-1を1回実行。facts.json45 bytes、marker file/.completeなし。
file/stage/root固定と保持権限0x160081/0x1700a1/0x1600a7、証跡2817/2886/3014＝8717 bytesの保存は成功した。
renameはNTSTATUSとIOSBとも0xc0000022→WinError5。native非pending/completion_unknown=false、operation.renameはpendingで停止。
全28 tracked handles/token2個close、worker exit1/0.562秒、stderr0、資源停止なし。終了後source読取り0、再検査/複製/削除なし。
CWDは保持source-fixtureとは異なる新規attempt親だが、拒否結果から名前解決成功は主張しない。内部拒否箇所も未trace。
1回枠は終了。追加試行・旧batch/B1再開・API/名前/親policy fallbackなし。
journalはprepare unknown/stopped・teardown succeeded・commit not_started。第3証跡名をmodelの完了に読み替えない。

元70b0のignored同名rootへ試験・文書差分・manifestを保存。別checkoutのnative原記録10個をnative-run/へ明示複製して一致を検査した。
失敗sourceは触らず、前回親policy manifest/24 artifactsの不変も照合した。
initial-checks.jsonl132318 bytes/hash ed7c7bf5b7474c7ff324e2a7c9a1034552cf7ea260ae7246786967587aac58bd。
savepoint-evidence.json11246 bytes/hash e3eba37e48436c02918e4214d8417f410b1932992c0c375a06d60b584979b719。
manifest以外18 artifactsの論理bytes219345。native側原記録/checkout等を含む全disk占有量ではない。

実機前UTC10:24:10 RAM13.44GiB/C119.18GiB/D76.44GiB、終了後10:27:17 RAM13.49GiB/C119.17GiB/D76.44GiB。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和と正式pin不変を維持。
worker2境界でprivate20.79MiB/working28.04MiB/peak working35.24MiB、外側samples0。worker・検証process終了、常駐なし。
点観測を全期間最大値・長期リーク不在の証明にしない。

次の案は親privateでpayload rename→親固定→最終検査→予約した空.completeへ保持writerでwrite/flush/closeだが、未実装・未採用。
案の独立P2は別actorの親private中の既取得ADD/DELETE_CHILD等の残存権限。sealで消去せず、検査後/公開後変更をmodel化し、
隔離根拠なし/不明なら保護済みcommitを拒否する条件を追記、再レビュー新規P0〜P3=0。
consumerの一致は時点観測であり将来の不変性ではない。自分のmarker writer以外が変更不能とは保証しない。
次は残存権限を含む小modelとconsumer条件を具体化する。別actorを脅威範囲から除外しない。
事前取得の防止/隔離条件が固まるまで候補のnative実装へ進まない。正式契約に触れる点は具体的な判断材料を作る。
全publisher、独立token、native故障/競合、正式OS整合、VM digest、runtime closure/consumer、S4受入は未完了。
全formal/authenticated flags=false、acceptance=not_completed。src/科学config/schema/registry/正式pin、本流889cfc3不変、旧CI加算なし。
push/merge/CI、新runtime/サービス/account、別project、旧failure roots操作なし。元の文書差分を消してcleanにしないこと。

## 92. 2026-09-14 B2 残存権限・完了印のpure modelを保存

ユーザー「続けてください」を受け、基準5826995からIOしない別modelを実装した。
実装savepoint **39cac0d947bbb51cd2079af416edce1c01fc23b9**。
[結果](anomaly-multiseed-v0.3-s4-b2-publication-order-model-2026-09-14.md)、[設計](../anomaly-v03-publication-order-model-design.md)、
[未採用の順序案](../anomaly-v03-publication-order-options.md)を参照。

最大8 peer handleのadd_child/delete_childを親固定で消さず、発見/外部変更を合計32件まで追跡する。
epochと最終照合を結び、検査後・停止後・仮想公開後の変更を記録して現在の照合を失効させる。
隔離の既定はunresolved。既知peerが0・inventory/ID/bytes/SD全一致でもmarker writeを拒否する。
assume_isolated_for_testは後段故障を試す反実仮想で、実OSの隔離根拠ではない。既知peerがあれば仮定付きでも拒否。
rename応答不明は後続禁止、write intent後からclose応答前までの停止はunknown。部分write/全量/flush/closeを分けた。
最初の失敗を保ち資源停止を昇格、工程skip/repeat/停止後再開を拒否する。仮想closeの履歴も将来不変性とは区別する。
consumerは単発synthetic観測のみ。共有違反/空/部分/読取り失敗/不正を分け、exact markerと4照合一致もsnapshot_matchesに限定。
producerが完全writeの応答を失った場合、consumerで完全bytesが見えても隔離成立・正式受入としない。
最大16KiBのtoy markerとsynthetic応答を使うmodelであり、実権限・所有終了・観測の真正性/同時性を証明しない。

新規20＋既存182＝202件pass/0.205秒、failure/error/skip等0、initial-checks.jsonlが最終根拠。
実装/試験/設計の独立P0〜P3=0、read-only、進捗ポーリングなし。30 source＋補助2 filesの記録/raw/Git blob一致。
repository safety/差分空白検査pass、以後コード変更・重複試験なし。既存6工程/native entry/S3/D2/productionは不変。
今回native0、監視/別checkout/常駐処理の追加なし。前回batch/B1は再開せず、失敗sourceの再検査/複製/hash取得/削除なし。
ignored artifacts/publication-order-model-2026-09-14/へ保存し、前回same-parent manifest/18 artifactsの不変も確認した。
initial-checks.jsonl147351 bytes/hash a58d9f063229a26004e87a5a190aa84d697bf4ea8966c8f3dc3d870804875407。
savepoint-evidence.json9006 bytes/hash c5f2844abdf7bbbc9fdcaf32497e8819b64e17c40fc1fc72eeceb5ee936896e6。
manifest以外6 artifacts/論理193851 bytes。filesystem総占有量ではない。
既存親policy結果書の差分8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は維持しcommitへ含めない。

試験前UTC10:48:30 RAM13.55GiB/C118.93GiB/D74.23GiB、試験後10:52:01 RAM13.38GiB/C118.92GiB/D74.23GiB。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和・正式pin不変を維持。
試験processは終了。点観測をprocessピーク/長期リーク不在の証明にせず、空き容量変動の原因を特定しない。

次は別actorの事前取得を防ぐ生成/隔離条件、または残存権限下でも変更できない操作境界の根拠を具体化する。
consumerの一貫した実観測/共有違反の有界処理、marker writerの権限/寿命も未実装。別actorを脅威範囲から除外しない。
隔離根拠不明のまま候補のnative publisherへ進まず、正式契約に触れる点は具体案を作って判断対象にする。
親全保護、marker/全publisher、独立token、native故障/競合、正式OS整合、VM digest、runtime closure/consumer、B2/S4受入は未完了。
protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。
本流889cfc3・正式pin不変、旧CI加算/push/merge/CI、新runtime/サービス/account、別project操作なし。既存文書差分を消してcleanにしない。

## 93. 2026-09-14 B2 隔離条件と単一呼出し取得候補

ユーザー「続けてください」を受け、基準1f70faaから実際の隔離の必要条件を具体化した。
設計savepoint **5b81bf032768d0ac486aff48143b77268ab36158**。
[設計](../anomaly-v03-isolation-basis-design.md)と[結果](anomaly-multiseed-v0.3-s4-b2-isolation-basis-2026-09-14.md)を参照。

現行private DACL/作成後の別openを確認し、次の部品にCreateDirectory2Wの作成＋初回handle取得を選んだ。
既存SDK10.0.26100.0とMicrosoft headerの5引数HANDLE宣言、redirect拒否flag=1、ローカルkernel32 export存在を確認した。
API本体の呼出しは0。公式ページの5引数syntax/6引数例・失敗0本文/INVALID_HANDLE_VALUE例の不整合を記録した。
6引数例を転写せず、0/-1を成功にせず、返却喪失・記録前割込みを所有unknownとして扱う取得仕様を固定した。
候補要求はroot0x1600a7/share READ=1/redirect拒否=1/既存private SD/非継承。原handleの先行記録、元ID/実権限/SD検査、単回closeが必要。

取得間隙の縮小はnamespace隔離の証明ではない。外側parentの既取得権限、private期間のADD/DELETE_CHILD、子の内部open、writer移管は未解決。
rootのDELETE共有拒否をDELETE_CHILDや子全体のmutexへ読み替えず、同じuserのpeerを新たに除外しない。
consumerの共通の変更不能期間/同じpin・handle・bytesが必要で、二度の一致だけでは同時性やABA不在を証明しない。
前回modelのunresolved→write拒否は維持。仮想隔離flagを実機認定に転用しない。
新規設計1ファイルの独立P0〜P3=0、read-only、進捗ポーリングなし。reviewerのAPI再照合・実機実行はない。

今回はcode変更/新規テスト/前回202件の再実行0。32 source/Git blob一致、前回manifest/6 artifacts不変を確認した。
ignored artifacts/isolation-basis-2026-09-14/へ保存。local-api-basis.json993 bytes/hash261decf99e6fbd0e9495008427a3500ad932812a24ddd9e48b208640237a9780。
savepoint-evidence.json9337 bytes/hashbb10fdd7744db58c7e0b87e04e85fdea5f8864b73089c1966fbf4d868aa2d7f6、manifest以外5 artifacts/論理7725 bytes。
開始UTC11:05:49 RAM13.30GiB/C118.92GiB/D74.23GiB、終了11:12:38 RAM12.77GiB/C118.91GiB/D74.02GiB。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和・正式pin不変。点観測を長期リーク/変動原因の証明にしない。
記録用process終了、常駐/監視/別checkout追加なし。既存親policy結果書の8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。

次は新規取得部品をtests/fixturesへ分離し、fake backendで0/-1/衝突/検査失敗/権限差/close応答喪失/資源停止/再入を確認して独立レビューする。
局所実機仕様はその後に別途固定。隔離条件未確認ならnative publisherへは進まない。専用account等の追加判断は現在不要。
既存6工程/native入口/S3/D2/production、本流889cfc3は不変。旧batch/B1/失敗source、push/merge/CI、別projectへの操作なし。
親全保護、marker/全publisher、独立token/native競合、consumer/runtime closure、正式OS整合/VM digest、B2/S4受入は未完了。
formal_permission/execution_authenticated/protected_commit_allowed=false、acceptance_status=not_completed。既存文書差分を消してcleanにしない。

## 94. 2026-09-14 B2 単一呼出しdirectory取得部品と故障確認

ユーザー「続けてください」を受け、基準46b8d35から独立した取得部品を実装した。
実装savepoint **7f9332289494f9b24e9e5e786737864ac88b0ae3**。
[設計](../anomaly-v03-directory-acquisition-design.md)と[結果](anomaly-multiseed-v0.3-s4-b2-directory-acquisition-2026-09-14.md)を参照。

DirectoryAcquisitionは予約TrackedOpenへCreateDirectory2Wの原handleを先行記録する。API/descriptor/SA/引数は事前準備。
5引数HANDLE/root0x1600a7/share READ=1/redirect拒否=1/private SD/非継承。0/NULL/-1等を成功にしない。
同handleのGrantedAccess/ID/type/private SDを確認し、明示的path再openを行う_Bound.checkを避けobserveだけを借用する。
成功handleはfinishまで保持し、CloseHandle→LocalFreeを各1回。再入・元例外保持・後発resource昇格、unknown時の再試行禁止を扱う。
作成返却/記録前の喪失は所有unknown、descriptorを保持しworker終了が必要。free応答不明も再freeしない。
callerはancestorをfinishまで保持する前提で、この部品は祖先結合やpeer/外側parent/consumer隔離を証明しない。
既存private sink/6工程/S3/D2/productionは不変。今回native0、entry/監視/新規枠追加なし。

新規19＋既存202＝221件pass/0.361秒、failure/error/skip等0。corrected-checks.jsonlが最終根拠。
初回全体も221件pass/3.101秒。独立P2はfake試験のホストPython版依存で、本体を緩めずsetUpのruntime固定/cleanup復元3行で修正。
外側synthetic3.12.9/posix下の正常系1件と外側復元も確認。実Python3.12の実行や追加installではない。
修正差分の再レビュー残件P0〜P3=0、read-only、進捗ポーリングなし。以後コード変更・重複試験なし。
32 source＋補助2 filesのraw/Git blob一致、前回isolation-basis manifest/5 artifacts・既存32 source不変を照合した。
repository safety/差分空白検査pass。ignored artifacts/directory-acquisition-2026-09-14/へ原記録を保存。
corrected-checks.jsonl162016 bytes/hashcdb64fe52b37b0c645599d942687193086fa10e09cba93c95fbeba2d7916c3f3。
savepoint-evidence.json11031 bytes/hash45084efd046a472c889a9bad65124046e1d033ecdd8ffb3985261511dd443591。
manifest以外10 artifacts/論理419071 bytes。filesystem全占有量ではない。

開始UTC11:26:41 RAM12.50GiB/C118.49GiB/D73.73GiB、試験後11:39:00 RAM4.50GiB/C118.16GiB/D66.77GiB。
低下を受け文書保存に作業を絞り、11:40:40再観測はRAM16.00GiB/C118.16GiB/D64.04GiB。上位6 processの資源を読取りだけで保存した。
RAMは回復、disk減少を含む変動原因は未特定。他processを停止せず、点観測を長期リーク不在/最大使用量の証明にしない。
今回の試験/記録process終了、常駐/監視/checkout追加なし。次の局所実機検討でも先に資源を再確認する。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和・正式pin不変。
既存親policy結果書の8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。

次は局所driverの祖先元ID/SD/寿命との結合、所有unknown時の終了、保存順序、衝突時の既存object非接触を具体化し独立レビューする。
その検証・source固定・監視と上限の準備後に別の実機仕様を定める。取得成功だけで隔離やnative publisher開始を認定しない。
旧batch/B1/失敗source、push/merge/CI、新runtime/account/service、別projectに操作なし。本流889cfc3不変、旧CI件数加算なし。
親全保護、marker/全publisher、独立token/競合、consumer/runtime closure、正式OS/VM digest、B2/S4受入は未完了。
isolation_certified/protected_commit_allowed/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 95. 2026-09-14 B2 局所directory取得driverと新規実機確認

ユーザー「許可するのでセーブポイント作りながら暫く自走してください」を受け、実装・独立レビュー・固定した新規1回の実機確認まで進めた。
実装savepoint **3a719347e736e7770036b6b7882f0f4614774424**。
[局所driver設計](../anomaly-v03-directory-driver-design.md)と[結果](anomaly-multiseed-v0.3-s4-b2-directory-driver-2026-09-14.md)を参照。

callerがdriver/contextを先行保持し、private sinkの全祖先leaseをsource.parentsへexact結合する。
既存祖先の元ID/type/pathとowner/group/DACL/labelの自己相対SDを読取り比較し、継承ACLへ新規private root専用制約を誤適用しない。
SDは8192 bytes上限、既知pointerを1回free、不明応答では再取得/freeせず祖先保持とworker終了が必要。
既存APIのdescriptor返却がc_void_p cellである点を取得部品/fakeへ修正した。原cellの先行保持は維持。
保存→原handle再観測→source close/free→祖先closeの順。resource stop後は固定通知/exit80、通常snapshotを作らない。

初回238件pass/0.212秒。独立P2=2（既知resource後の後続IO、finishだけでpass）を修正し、最終240件pass/0.210秒。
新規19＋既存221、failure/error/skip等0。入口/guard前後で資源停止を取り込み、成功にはrun/保存/再確認/終了が必要。
修正差分・入口・監視・設計の独立再レビュー残件P0〜P3=0、read-only、進捗ポーリングなし。
corrected-checks.jsonl176164 bytes/hashb976b48bcb43636f82ba20fb38faaee8413b95056165d021ab86a7060ba05fd3。

nativeは別clean detached checkout C:\Users\TKent\.codex\worktrees\directory-driver-20260914\banto-ai の固定HEAD3a71934から実行。
39 sourceのraw/Git blob/checkout一致、launch-plan.json8157 bytes/hash0002fe3d6504bd710a6f082693f89c593b4c9d9ec11a2ae6638a254f8beda185を実行前後で照合。
新規directory-driver-2026-09-14枠のattempt-1だけ、CreateDirectory2W/root0x1600a7/share READ/redirect拒否/private SD/非継承。
UTC12:07:48.6954047〜12:07:49.2453203、実機pass/0.540秒、worker exit0/終了確認、stop reasonなし。
元handleで取得/ID/実権限/SD/再観測pass、祖先10、台帳上13 handles/query token1本closed、入力descriptorと祖先SDはfreed。
prepare.json1990 bytes/hashbf8747dc4c809dd8ba06152f38ae7de82fb93d42d2dea2057b0f5f7fe8e9790d、saved。
stdout9547/stderr0 bytes。内部23資源点、最後0.095秒、観測private最大20975616/working29458432 bytes、OS報告working peak35790848 bytes。
外側1秒周期より早く終了し外側process memory観測0点。点観測を全期間最大や長期リーク不在としない。

今回max1枠は閉鎖。source-fixtureをclose後に列挙/open/hash/copy/deleteしない。成功した既知prepareだけworker記録と照合した。
子/payload/marker/rename操作なし。private sinkのbootstrap信頼制約とpeer/外側parent/consumer未解決を維持し、取得成功を隔離認定にしない。
ignored artifacts/directory-driver-2026-09-14/へ14 artifacts/論理478167 bytes（manifest/別checkout複製を除く）。
savepoint-evidence.json13060 bytes/hash94cee204de69aa67acb2444b8489a1fed200128eb08b6eccd0c6f9c139666f2e。
前回manifest/10 artifacts不変、34 source中32不変、descriptor修正2 filesだけ更新。repository safety/差分空白検査pass。

UTC12:05:46の空きRAM15.02GiB/C118.06GiB/D60.12GiB、12:09:03はRAM14.77GiB/C118.05GiB/D60.12GiB。
開始11:50:53からのdisk変動は別途観測され原因未特定。他processへ介入なし。build26200.9445、boot2026-09-09T10:43:08.5000000+09:00。
Windows Update engineering緩和/正式pin不変。worker/監視終了、常駐なし、新規detached checkout1個とfixtureを保存。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変。旧batch/B1/失敗source/S3/D2/production、push/merge/CI、別project、新runtime/account/serviceへの操作なし。

次はprivate期間中のpeerのADD_FILE/ADD_SUBDIRECTORY/DELETE_CHILD取得と実操作を分ける検証仕様を具体化する。
この成功fixtureや試行枠を再利用しない。source作成と取得の成功だけではpeer権限を排除できず、native publisherへ進めない。
親全保護・marker/全publisher・独立token/競合、handle移管・consumer/runtime closure・正式OS/VM digest・B2/S4受入は未完了。
isolation_certified/protected_commit_allowed/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 96. 2026-09-14 B2 同一token peerの変更権限取得

ユーザー「進めて下さい」と継続中の自走/セーブポイント許可を受け、private期間の別handle権限取得を実装・レビュー・実機確認した。
実装savepoint **13ad057c2662cd0bf67a19853602c43eeac7d42e**。
[peer設計](../anomaly-v03-directory-peer-design.md)と[結果](anomaly-multiseed-v0.3-s4-b2-directory-peer-2026-09-14.md)を参照。

新規rootをCreateDirectory2W/root0x1600a7/share READ/private SD/redirect拒否/非継承で取得し、原handleを保持。
同じprocess/primary tokenのpeerでOPEN_EXISTINGを4件。全requestedにREAD_ATTRIBUTES/READ_CONTROL/SYNCHRONIZEを含める。
LIST control0x120081はgranted、ADD_FILE0x120082とADD_SUBDIRECTORY0x120084はWinError32、DELETE_CHILD0x1200c0はgranted。
成功peerのGrantedAccessは各requested exact、原rootのID/type/SDに一致。share READだけで全変更用handle取得を排除できない。
実際の子作成/削除/rename、独立process/token、外側parentの事前権限はこの確認に含まれない。

4 slotを先行予約し、返却値を観測前に保持。文書化されたINVALID_HANDLE_VALUE＋直後error5/32だけを非作成openのknown denialに分類。
TrackedOpenのunknown/unavailable履歴は書き換えず、known_no_handle_denialを別記録にする。作成失敗や不明応答に一般化しない。
control拒否/他error/異常値/観測差/不明返却で打切る。正常peerは次のケース/保存前にclose。
不明peer時は原root/input descriptor/祖先も保持してworker終了。既知peerの検査失敗は通常終了し、primary/resource/reentry契約を維持。
初期tokenはquery slotを使って読み、primary/非昇格/medium/BackupRestore無効を要求。実機のenabled privilegeはSeChangeNotifyPrivilegeのみ。
token変更/生成/impersonationは行わない。期間中の外部token変更や独立actorの完全な再現を主張しない。

新規19＋既存240＝259件pass/0.263秒。failure/error/skip等0、initial-checks.jsonlが最終根拠。
独立code/試験/入口/監視と設計のP0〜P3=0、read-only、進捗ポーリングなし。review後code変更/重複回帰なし。
repository safety/PowerShell構文/差分空白検査pass。基底driverは観測点定数化だけ変更し既定64維持、新peerだけ96点。
時間40秒/外側45秒、private256MiB/working384MiB、空きRAM/disk各2GiBの制限は不変。

nativeは別clean detached checkout C:\Users\TKent\.codex\worktrees\directory-peer-20260914\banto-ai、HEAD13ad057から実行。
44 sourceのraw/Git blob/両checkout一致を実行前後で照合。launch-plan.json9342 bytes/hash915a531ac2efe7b7feca0cc02af832ff4fe92827b8c20321fc94f1d234d8f77b。
新規directory-peer-2026-09-14のattempt-1だけ。UTC12:38:18.4199669〜12:38:19.3984811、行列完了/0.966秒、worker exit0/終了確認。
原rootの取得/再確認pass、祖先10、台帳上実handle15本とquery token1本closed、別にknown no-handle denial2件。
input descriptor/祖先SDはfreed、prepare.json2464 bytes/hash2abd9c1f50acdf20ba77c46535ea6bca98cb237f2edd4afe1f695be65b1f7796。
stdout16854/stderr0 bytes。内部50資源点、最終0.433秒、観測private最大21299200/working29822976 bytes、OS報告working peak36167680 bytes。
外側1秒周期より早く終了し外側memory観測0点。max1枠は閉鎖。sourceはclose後/失敗後に再検査・再open・hash/copy/deleteしない。
成功した既知prepareだけをbytes/hash・行列/token報告と照合し、sourceの名前からの再openは原root保持中のpeer4件だけ。

ignored artifacts/directory-peer-2026-09-14/へ12 artifacts/論理285363 bytes（manifest自身/別checkout複製を除く）。
initial-checks.jsonl190058 bytes/hash056fc8104a090291899f9fa0d3e12bfdecdb20791ddbcef34a09b5961200e4fa。
savepoint-evidence.json16763 bytes/hashb3f9b558e9700c583a657a85dd14d22c5375e9401d9c73f16a956a07162e26ce。
前回manifest/14 artifacts不変、39 source中38不変、変更は上記driver定数化のみ。
UTC12:29:28 RAM13.92GiB/C117.76GiB/D57.85GiB、12:41:01 RAM13.77GiB/C117.52GiB/D56.81GiB。
空き容量変動の原因は未特定。点観測を長期リーク不在/全期間最大や試験の全占有量へ読み替えず、他processへ操作なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。
worker/監視終了、常駐なし、新規detached checkout1個とfixtureを保存。既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変。旧batch/旧source/B1/S3/D2/production、push/merge/CI、別project、新runtime/account/serviceへ操作なし。

次は新規fixtureの子DELETE許可、親DELETE_CHILD、子DELETE共有を分け、削除操作の成否を調べる仕様へ進む。
private childの削除成功だけでは保持parent handleの権限使用の証明にならず、path APIの再評価と保持parentを直接使う操作を区別する。
今回取得できたDELETE_CHILDを削除実行成功へ昇格しない。この成功sourceやmax1枠を再利用しない。
親全保護・marker/全publisher・独立token/競合、外側parent/handle移管/consumer/runtime closure、正式OS/VM digest・B2/S4受入は未完了。
isolation_certified/protected_commit_allowed/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 97. 2026-09-14 B2 新規空ファイルの削除条件

ユーザー「次に進めて下さい」と継続中の自走/セーブポイント許可で、新規4ケースのDeleteFileW行列を実装・レビュー・実機確認した。
実装savepoint **26bc403836a2b191e7e8344716c50cf49be50f47**。
[設計](../anomaly-v03-delete-matrix-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-delete-matrix-2026-09-14.md)を参照。

各新規case親はCreateDirectory2W/access0x1600a7/share READ/非継承。新規空子はCREATE_NEW/access0x120081/非継承、作成後ACL変更なし。
file-permission（親DELETE_CHILD拒否/子DELETE許可/share7）は受理、parent-permission（親許可/子拒否/share7）も受理。
双方とも保持childのDeletePending=true/links0、元ID/SD一致。sharing-block（親許可/子拒否/share3）はWinError32、both-denied/share7はWinError5、pending=false/links1。
親share READだけでは子削除を防げない。子DELETE共有拒否は保持期間中の局所条件であり、close後/公開後へ一般化しない。
同process/primary非昇格medium token、有効privilegeはSeChangeNotifyPrivilegeのみ。token変更/生成/impersonation/AccessCheckなし。
path指定であり、保持parent handleの権限使用や独立process/token/競合の証明ではない。close後の名前消滅や外部handle不存在も未検査。

新規24＋既存259＝283件pass/0.205秒。初回独立P2 1件は終了判定snapshot失敗時の一次例外/親保持の欠落。
報告生成と状態判定を分離し、query故障時は元例外/resourceを維持、未終了root/祖先を保守保持。追加4故障試験・再レビューP0〜P3=0。
最終根拠はcorrected-checks.jsonl。read-only独立レビュー、進捗ポーリングなし。safety/PowerShell構文/diff検査pass、再レビュー後code変更なし。

nativeは別clean detached C:\Users\TKent\.codex\worktrees\delete-matrix-20260914\banto-ai、HEAD26bc403。49 sourceのraw/Git blob/両checkoutを前後照合。
新規attempt-1だけ、UTC13:11:17.5783595〜13:11:18.4303207、0.843秒、worker exit0/終了確認、max1枠閉鎖。
case親4/子4とsink等12のhandle20本＋query token1本closed、入力descriptor/祖先SDはfreed。
prepare9118 bytes/hash26c2c3ab9ad4696ea4e44886ed2510a4082bebd0b36189aa39f64abb183b7ce3。stdout52366/stderr0。
内部209資源点/上限256、最後0.413秒、private最大21422080/working29589504、OS working peak35758080 bytes。
40秒/外側45秒、private256MiB/working384MiB、空きRAM/disk各2GiBを維持。

ignored artifacts/delete-matrix-2026-09-14/へ14 artifacts/論理610560 bytes（manifest自身/別checkout複製を除く）。
savepoint-evidence.json28705 bytes/hash5e4755ba021b5221d12cd1cb1da5e3d2d1e7eba32262fe7da587ce35d525df5a。
前回peer manifest/12 artifacts不変、44 source中43不変、既存source変更はacquisition backendのhookのみ。
UTC12:56:23 RAM16.44GiB/C117.52GiB/D53.16GiB、13:11:51 RAM15.54GiB/C117.51GiB/D53.16GiB。PC全体変動の原因は未特定、長期リーク不在の主張なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。
worker/監視終了、常駐なし。caseのclose後/失敗後列挙・open・hash/copy/deleteなし。既知の成功prepareだけを照合し、拒否された新規空ファイルも保存して残す。
旧batch/旧source、別project、新runtime/account/service、push/merge/CIへ操作なし。本流889cfc3 clean不変、既存親policy結果書は保存時の8461 bytes/hashを保持しcommitから除外。

次はsealed-file保持と公開順序modelへ、子handleの全期間保持、close/移管の間隙、consumer共通観測期間を接続する。
条件が閉じない場合に専用principal等の運用変更を判断材料へ出す。新accountは現時点で作らない。
保持parentを直接使うAPI、外側parentの事前権限、独立token/競合、marker/全publisher、正式OS/VM digest・B2/S4受入は未完了。
今回のcase/max1枠を再利用せず、isolation_certified/protected_commit_allowed/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 98. 2026-09-14 B2 公開前後の保持とconsumer共通観測期間

ユーザー「次に進めて下さい」により、前回削除条件をpureな保持期間modelへ接続した。
実装savepoint **1c03cfece1464f8231b7d223c7f91828a639bd97**。
[設計](../anomaly-v03-retention-window-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-retention-window-2026-09-14.md)を参照。

2〜8fileの初期pin、24世代slot/128events。DELETE共有拒否とdata WRITE共有拒否を別追跡し、公開開始から観測完了までとconsumer全fileの共通期間を分離。
open確認前はguardでなく、close intent以降は依存しない。再取得の同ID/同bytesで欠落履歴を消さず、観測済fileも完了まで保持する。
既存SealedFilesはcallback内で全子を保持し、戻る前にcloseすることをfake backendで照合。
payload sealer0x160081/share1とreader/share1は共有条件が両立。一方marker0x170081のDELETEと新reader/share1は衝突する仕様上の予測。
marker readerをshare5にすると共有条件は両立するが、旧guardのclose後のDELETE拒否を維持できない。追加native実証ではない。

既定の他境界unresolvedでは全照合一致でもobservations_match_only、bytes返却不可。
明示的test仮定と共有条件の共通期間がある場合のみcommon_interval_model_only、同じ照合済immutable bytesを返せる。
親/祖先namespace・inventory・descriptor・保持者の権限行使/移管は共有条件から導かず、実隔離・将来不変性は主張しない。
consumerのmodel一致で既存PublicationOrderのwrite gateやproducer unknownを変えない。

新規23＋既存283＝306件pass/0.219秒。初回304件pass後、独立P2で余分なslotの未確定open/closeを残した完了・返却を検出。
完了前と返却前に全slotを検査して拒否するよう修正し、2故障試験追加。再レビューP0〜P3=0、read-only/進捗ポーリングなし、再レビュー後code変更なし。
最終根拠corrected-checks.jsonl224673 bytes/hash9c614996c3ab2715be80c817f5165e4af4e54b0902760e8641e5c2a133d08b81。repository safety/diff検査pass。

54sourceのraw/Git blob/候補一致。前回delete-matrixの49source/14artifactsは全て不変。
ignored artifacts/retention-window-2026-09-14/へ8artifacts/論理574370 bytes（manifest自身除外）。
savepoint-evidence.json12370 bytes/hash8c43033877fd80b3fac04c6155e5c11e7bfb915c64959b052078db5879eb0ee7。
UTC13:26:58 RAM14.73GiB/C117.51GiB/D53.16GiB、13:29:45 RAM14.32GiB/C117.51GiB/D52.96GiB。PC全体変動の原因は未特定、長期リーク不在の主張なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。
実機追加0回、新worker/監視/checkout/常駐なし、旧caseへの読取/再open/cleanupなし。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変、S3/D2/production、push/merge/CI、新runtime/account/serviceへ操作なし。

次は元root/全sealed fileのborrow内で有界consumer読取を完了し、照合したbytesを返す部品を具体化する。
marker write/rename・全publisher、親/祖先/全inventoryの共通期間、独立process/token・競合、正式OS/VM digest・B2/S4受入は未完了。
別account/サービスや受入契約の変更が必要になれば具体的な差分と運用負担を判断材料にする。現時点で追加accountやnative publisherの開始はしない。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 99. 2026-09-14 B2 保持handle内の有界consumer読取

ユーザー「次に進めて下さい」により、元root/全sealed fileを保持中の実読取adapterを具体化した。
実装savepoint **8c35fce85ced37c8d3edf2d9bde9b4f5487ecae1**。
[設計](../anomaly-v03-held-consumer-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-held-consumer-2026-09-14.md)を参照。

開始前に元root Observation、plans/marker/source revisionを照合しbufferを確保する。
既存SealedFiles continuation内で全子を保持し、全metadata/実権限の先行照合、同handle単回read、全子/元rootの再照合を行う。
consumer内のpath再open/close/ACL変更/名前列挙/renameなし。周囲の既存SealedFiles準備open/seal/path照合は維持する。
同期local NTFS/非OVERLAPPED、N+1要求/exact N返却、file64KiB、最大8file/plan総量256KiB、marker16KiB、descriptor8KiB、guard512回。
actual read bytesを保存し、plan bytesで代用しない。全子close応答、最終guardとowner/generation/journal停止確認後だけ収集complete。
途中変更、上位停止、一次例外と後発resource停止、close不明、再入・差替えで全候補を破棄する。
子close不明のrequires_exitを受けて元root/関連祖先を保持しworker終了へ進むcallerの接続は未実装。root最終closeもcallerの責任。
生bytesはprivate証拠であり外部返却は常にisolation_unresolved。modelのtest仮定による返却switchを実部品に設けていない。

新規25＋既存306＝331件pass/0.286秒。初回327件後の独立P2は最終guardが正常returnした場合の上位停止の取りこぼし。
3回帰追加/330件後の再レビューP2はjournal snapshotの二次障害による元例外の欠落。既知一次例外/resourceを先に確保し1回帰追加。
最終P0〜P3残件0、read-only/進捗ポーリングなし、最終再レビュー後code変更なし。repository safety/diff検査pass。
最終根拠final-checks.jsonl242599 bytes/hash95cc1f9bf25ce8840916f25c1874abf2a9f6054ad91a9cb88bcfdb9f6d5266cf。

57sourceのraw/Git blob/候補一致。前回retention-windowの54source/8artifactsは全て不変。
ignored artifacts/held-consumer-2026-09-14/へ10artifacts/論理924883 bytes（manifest自身除外）、3テスト記録保持。
savepoint-evidence.json13272 bytes/hashba126b80b360bfa4ac84d1a47415ff61065df92101a2e9d44cfdca5ebd2f55a0。
UTC13:46:18 RAM14.55GiB/C117.56GiB/D52.68GiB、13:57:20 RAM14.36GiB/C117.56GiB/D52.68GiB。PC全体変動の原因は未特定、長期リーク不在の主張なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。
実機追加0回、新worker/監視/checkout/常駐なし、旧caseへの読取/再open/cleanupなし。既存Python3.14.0を使用。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変、S3/D2/production、push/merge/CI、新runtime/account/serviceへ操作なし。

次はこの部品を新規fixture専用の有界driverへ接続し、元root/祖先の保持、子close不明時のworker終了、資源監視、結果保存をfake故障で固定する。
新規限定native仕様はその後に別途固定する。旧source/閉鎖済み枠を再利用しない。
親/祖先/全inventoryの共通期間、marker write/rename・全publisher、独立process/token・競合、正式OS/VM digest・B2/S4受入は未完了。
別account/サービスや受入条件変更が必要なら具体的な差分と運用負担を判断材料にする。現時点で追加accountやnative publisher開始はしない。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 100. 2026-09-14 B2 保持consumerの準備・保存・終了接続

ユーザー「次に進めて下さい」により、新規fixtureの準備とheld consumer、証拠保存、親/祖先保持を有界driverへ接続した。
実装savepoint **fe6f7a8cce80476396ba8eea573a9b1812fc1747**。
[設計](../anomaly-v03-held-driver-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-held-driver-2026-09-14.md)を参照。

元root/新規facts.json/marker-pending.jsonのObservationを固定し、prepare証拠保存後にwriterをreleaseして既存HeldConsumerを1回実行する。
収集状態・byte count・hashをprivate-evidenceのseal_payload.jsonへ保存するが、publication journalの同名工程は進めない。
生bytes返却は常にisolation_unresolved。準備/path確認/sealer再openとconsumer内の直接readを区別する。
source rootは既存WindowsPrivateSinkのCreateDirectoryW/再open方式。単一呼出しdirectory取得部品の保証を組み合わせていない。

RetainedSinkがbootstrap自動finishを保留し、子→root→source祖先→evidence側の終了をdriverが制御する。
writer release未確認のadopted treeや子close不明はroot/祖先ごと保持。root/祖先close不明でも上位を閉じず、lifetime query例外/異常応答は保守保持。
一次例外をstatus/report割当から独立して記録し、後発resourceを昇格。exit80/81/1/0はcacheだけから選ぶ。
再入・報告中の停止を検査し古いcompleteを出さない。reader/driver完了は隔離・全期間不変・B2/S4受入を与えない。

新規29＋既存331＝360件pass/0.416秒。初回359件後、prepare証拠をdriverで64KiBに制限し、保存/writer release前の上限停止回帰を追加。
既存barrier自体は512KiB。収集証拠16KiB/report256KiB、新規2file/各write4096 bytes、資源1024点/40秒/private256MiB/working384MiB/空きRAM・disk各2GiB。
fake Win32で実prepare barrier/collector/所有部品を通し、終了喪失・未release・query/report故障・再入・resource/容量/時間上限を確認。
独立P0〜P3所見0件、read-only/進捗ポーリングなし、最終差分再レビュー後code変更なし。repository safety/diff検査pass。
corrected-checks.jsonl261905 bytes/hash4fdff65547449a40072b7ff3df79775ec5037fdf36b7c8774d926513d9c7f41fが最終根拠。

60sourceのraw/Git blob/候補一致。前回held-consumerの57source/10artifactsは全て不変。
ignored artifacts/held-driver-2026-09-14/へ8artifacts/論理670411 bytes（manifest自身除外）、初回/修正後記録保持。
savepoint-evidence.json13498 bytes/hash2ebaa67b936e5e8cfbe969ab46520f13520d644f89fd9be68cea42c619f9e6c1。
UTC14:12:23 RAM14.29GiB/C117.55GiB/D52.68GiB、14:14:26 RAM13.62GiB/C117.50GiB/D51.39GiB。PC全体の減少原因は未特定、今回記録量と分離し長期リーク不在を主張しない。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。
実機追加0回、新worker/監視/checkout/常駐なし、旧caseへの読取/再open/cleanupなし。既存Python3.14.0使用。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。
本流889cfc3 clean不変、S3/D2/production、push/merge/CI、新runtime/account/serviceへ操作なし。

次は新規max1専用launcher/外側監視の仕様を固定する。clean revision/入力hash、排他的attempt、40秒内側/45秒外側、context保持、worker終了確認、stdout単回保存を接続する。
報告/出力失敗時も終了状態を失わず失敗sourceへ戻らないことをfake/構文で先に確認し、その後に別clean checkoutで新規限定nativeを実施する。
既存bootstrap競合/内部割当、親/祖先/全inventoryの共通期間、独立process/token・競合、marker write/renameと全publisher、正式OS/VM digest・B2/S4受入は未完了。
isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 101. 2026-09-14 B2 保持consumerの専用worker・限定実機

ユーザー「次に進めて下さい」により専用起動と外側監視を接続し、新規max1限定実機を完了した。
実装savepoint **9cc926f3c2c6cadff10c041ec0d0521c32016d3e**。
[設計](../anomaly-v03-held-launch-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-held-launch-2026-09-14.md)を参照。

HEAD/入力pin SHA/追跡py・ps1全inventory/bytes/hash照合後だけ取得。排他claim/attempt、module参照で終了までcontext保持、stdout単回と80/81維持を接続。
既存driver変更はsnapshotへのreader metadata追加のみ。report/出力MemoryErrorは80へ昇格し、一次例外/保持を保つ。出力失敗後の再試行なし。
新規17＋既存360＝377件pass/0.508秒、全failure/error/skip等0。独立P0〜P3所見0件、read-only/進捗ポーリングなし、レビュー後code変更なし。
PowerShell構文/repository safety/diff検査pass。initial-checks.jsonl273518 bytes/hashf12b722db71d77b58a6da440bcde5766adf7ab58b0cefe4329acd7d36c903c68が回帰根拠。

別clean detached C:\Users\TKent\.codex\worktrees\held-launch-20260914\banto-ai、HEAD9cc926f。
新規attempt-1、UTC14:43:21.2087356〜14:43:22.0892657、0.860秒。worker PID43324/exit0/終了確認、stopなし、max1枠閉鎖。
facts.json42 bytes/hashbe793aa97ba27ec1a79877d13399612d07a66fcd6d45848664964a193591e09b、marker-pending.json415 bytes/hashc67f80da25b921237b5603d6cb330fd741597383fbbf5dcbecf4cddf5aff0c71。
consumer complete/61 guards/2file closed、元source13＋sink13＋sealed reader2＝28 handle、query token2 closed。生bytes返却は拒否。
prepare報告2876 bytes/hash3a6eefc745936247fd9e174ceb19b759f8de3d13e7aa2d519f186f10e5cd2778、収集証拠1063 bytes/hash84983d51e4314e6dd7a4f734cdd440881242e113d1c68ccdbab962d514a59181。
証拠値はworker内の保存/読戻し報告に基づき、終了後source/private-evidenceを再openして独立照合していない。stdout27846/stderr0。
内部資源100点/最後0.266秒、private最大21245952/working29495296、OS working peak報告36118528 bytes。
外側1点/0.599秒でprivate28524544/working35942400 bytes。40秒内側/45秒外側、private256MiB/working384MiB、空きRAM/disk各2GiBの範囲。
worker/監視終了、常駐なし。取得後/失敗後のsource列挙・再open・hash/copy/deleteなし。

選抜65 sourceはraw/Git blob/候補・nativeを前後照合。input pin106 sourceを含むunion134 sourceはnative raw/Git blob一致。
input-pin.json17176 bytes/hash0aaa69ce665e9af43f2ee6d29808453081fe4e009af7325c00e4a4450f7f8026。
候補追加runtime source22件は既存CRLF、Git/nativeはLF。改行正規化だけの一致を記録し、候補fileを変更せずnative bytesをpinに採用。検出時はattempt未作成で実機再試行ではない。
前回held-driverの60 source中59不変、変更はdriver snapshotの1件。前回manifest/8artifactsは不変。
ignored artifacts/held-launch-2026-09-14/へ13artifacts/論理440266 bytes（manifest自身/別checkout複製/実fixture除外）。
savepoint-evidence.json40219 bytes/hash1eaba249cdbd404120bb8671f8112876e6f26cd0fddc71bee399016266cd667d。
UTC14:41:05 RAM13.94GiB/C117.29GiB/D51.39GiB、14:45:23 RAM14.03GiB/C117.29GiB/D51.39GiB。PC全体変動原因は未特定、長期リーク不在の主張なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。既存Python3.14.0使用。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommitから除外。本流889cfc3 clean不変。
旧case/旧source、S3/D2/production、push/merge/CI、新runtime/account/serviceへ操作なし。

次は親フォルダー保持中の名前一覧への追加条件を具体化する。新規fixtureで親share条件とpath指定の新規file作成を分ける。
ADD_FILE用handle取得拒否だけでpath追加も拒否されると推定せず、別の有界仕様/fake故障/独立レビューを先に行う。今回のsource/成功枠を再利用しない。
親/祖先/全inventoryの共通期間、bootstrap競合/内部割当、独立process/tokenのpeer・競合、marker write/renameと全publisher、正式OS/VM digest・B2/S4受入は未完了。
運用変更が必要なら具体的な差分と負担を判断材料にする。isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated=false、acceptance_status=not_completed。

## 102. 2026-09-15 B2 親共有とpath新規作成の比較準備・実機停止

ユーザーは適度なsavepointを伴う自走を許可。実装savepoint **2ec193adf8f81bed5685de0ff0cc09276e2741f7**。
[設計](../anomaly-v03-namespace-create-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-namespace-create-2026-09-15.md)を参照。
新規20＋既存377＝397件pass/0.727秒、独立P0〜P3所見0件、read-only/進捗ポーリングなし。構文/safety/diff検査pass。
親share3/1下のpeer取得とpath CREATE_NEWを独立比較する実装だが、新規max1は最初の親CreateDirectory2Wでdirectory_create_failed。
peer/child/第2root未開始、名前追加の比較結果なし。root close=unavailable、入力descriptor freed、祖先/evidence root11 leaseはworker終了まで保持、query token closed。
worker PID41196/exit81/終了確認、UTC2026-09-14T15:43:06.7531569Z〜15:43:07.4616119Z、0.689秒、stopなし、stdout10369/stderr0。
失敗のWinError数値はreportに未保存で原因未確定。share3固有問題・ACL拒否・namespace保護の証明とは扱わない。枠閉鎖、失敗後sourceアクセス/再試行なし。

新規clean detached namespace-create-20260915/banto-ai、input109/選抜70/union139 sourceを固定・前後照合。既存CRLFのみ22件は候補を変更せず記録。
input pin17695 bytes/hash82a3fa6e08bfbb6b3ae1fc1bd4c5b4202d2e62d2406681d0986667a84d56ffba。
前回held-launchの65 source中64不変、変更はlauncher scope1件。旧manifest/13 artifactsは不変。
artifacts/namespace-create-2026-09-15に13 artifacts/論理443868 bytes、manifest45792 bytes/hashcb146bf4aebab18e24dacd4ea3eb5e222ec6758f270cad4756bce7d924de981a。
内部8資源点/private最大21127168/working29368320、外側1点/private20918272/working28045312 bytes。全上限内。
UTC15:45:07 RAM16178049024/C125442588672/D48269496320 bytes。前後のPC全体変動の原因は未特定、長期リーク不在は主張しない。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変、Python3.14.0。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommit除外。本流889cfc3不変。

次は親作成エラー数値をnamespace報告に加えてfake故障を確認し、別の新規max1診断仕様を固定する。今回の失われたエラー値は復元したと扱わない。
親/祖先/全inventoryの共通期間、独立process/token・競合、全publisherと正式B2/S4受入は未完了。全許可flags=false。

## 103. 2026-09-15 B2 親作成エラー87の新規診断

実装savepoint **c0f17d8e4dd8b9835215869633bd55c6c2536402**。
[診断仕様](../anomaly-v03-namespace-diagnostic-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-namespace-diagnostic-2026-09-15.md)を参照。
親作成例外の数値をreportへ伝える修正後、新規max1でshare3最初の親がWinError87/ERROR_INVALID_PARAMETER。具体的不適合引数は未確定。
peer/child/第2root未開始。11 lease保持、query token closed、worker PID25756/exit81/0.661秒/終了確認、stopなし、stdout10432/stderr0。
前回失敗の数値を復元したとは扱わない。両旧枠閉鎖、失敗sourceへ再アクセスなし。
399件pass/修正後0.487秒、独立P2総1件（fakeテストLinux互換）修正済み/残0、進捗ポーリングなし。
input109/選抜71/union140 source、既存CRLFのみ22件を記録。前回manifest/13 artifacts不変、70 source中66不変。
artifacts/namespace-diagnostic-2026-09-15に15 artifacts/論理812764 bytes、manifest46686 bytes/hashe5b4255afc638c015daf3246fa6227be7f126a9bb69dab3410d8a2940018aa6f。
UTC15:51:50 RAM15885922304/C125462380544/D47691575296 bytes、上限超過なし。他process操作なし。build26200.9445/boot不変、Windows Update engineering緩和/正式pin不変。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommit除外。
次は過去に作成実績のあるshare1だけの新規有界caseへ限定し、peer要求とpath追加を確認する。share3不適合の再試行や一般化を行わない。
namespace/全期間/独立token/全publisher/B2/S4未完了、全許可flags=false。

## 104. 2026-09-15 B2 親share READ中のpath追加を確認

ユーザーのsavepoint付き自走許可の範囲で、比較準備2ec193a→失敗保存2b865dc→エラー記録c0f17d8→診断保存37ec1c9→単独case実装 **674d1193711334fefd21bc56c11ffa8000943e6a** まで進めた。
[単独case仕様](../anomaly-v03-namespace-readonly-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-namespace-readonly-2026-09-15.md)を参照。
親share3の作成停止（初回数値なし、別新規診断87）を反復せず、実績あるshare1へ限定した新規max1を実施。
親access0x1600a7/share1/private SD/非継承で作成・保持。LIST0x120081/DELETE_CHILD0x1200c0 peerはgranted/closed、ADD_FILE0x120082/ADD_SUBDIRECTORY0x120084は32でknown no-handle denied。
同じworker/primary tokenによるpath CREATE_NEW/子0x120081/share7でnew-empty.bin作成はaccepted、空/links1/非delete-pending/ID/SD/実accessを同handleで確認。
親ID86690d00000080000000000000000000、子ID0f6b0d00000034000000000000000000。親ID/SD再確認・保存まで保持、親1＋子1＋peer2＋sink12＝16 handle/query token1 closed。
親share READとADD用open拒否だけで名前追加を防げない実例。独立peer/token干渉、share3対照比較、全namespace/全期間不変の証明ではない。

401件pass/2.278秒、全failure/error/skip等0、独立所見0件/進捗ポーリングなし。repository safety/PowerShell構文/diff pass。
新規clean namespace-readonly-20260915/banto-ai、input109/選抜72/union141 source、既存CRLFのみ22件を記録し候補を保全。
input17695 bytes/hashf039debbb0b99a2ebebfc398681f7b8912b341b1fa686521614d6f6515f4805e。
UTC2026-09-14T15:56:31.4716823Z〜15:56:32.2623011Z、0.770秒、worker PID25500/exit0/終了確認/stopなし、stdout23949/stderr0。
prepare.json slotへmetadata4082 bytes/hash6e066529de9207b26f87ed8533ce7ee25958e704ab73152e1fe578321feac59e保存。reportではcollection_evidence_*、prepare_*はnull。worker内readback報告であり終了後の独立再openなし。
前回namespace-diagnostic manifest/15 artifacts不変、71 source中67不変。artifacts/namespace-readonly-2026-09-15へ13 artifacts/論理462313 bytes、manifest47676 bytes/hash4b26123e10ba815ea10e8f1e809991609e669a2c34e4fa0d7a0920f149317f6c。
内部79点/最後0.189秒、private最大21180416/working29548544、外側1点/private21184512/working29007872 bytes。全上限内。
UTC15:57:35 RAM15456075776/C125327585280/D45614665728 bytes。D空きは作業開始時ツール観測55098978304 bytesから約8.83GiB減少、原因未特定・他process操作なし。3工程記録はmanifest込み1859099 bytes（複製/Git/worktree/実fixture除外）。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変、Python3.14.0。長期リーク不在の主張なし。
全新worker/監視終了、各max1枠閉鎖。旧source/枠への再open/列挙/hash/copy/deleteなし。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommit除外。本流889cfc3、push/merge/CI、runtime/account/service不変。

次はpublisherの追加/renameと通常peerへ与えない権限、取得前/保持中/公開後、外側親・process handle移管を一覧化し、権限境界の具体案を作る。
専用principalが必要ならlocal account/隔離VM、資格情報と起動・consumer読取の運用差を具体化してからユーザー判断へ出す。無断でaccount/serviceを追加しない。
同じ結果の反復や親shareの設定名を隔離成立の根拠にしない。生bytes返却・全期間・全publisher・正式B2/S4受入未完了、全許可flags=false。

## 105. 2026-09-15 B2 公開側と通常peerの権限分離案

ユーザー「次に進めて下さい」により、次の権限境界を方式判断できる設計へ具体化した。
設計savepoint **60ac6c45c737c0785540f976de1dfb16abb4d7f0**。
[設計](../anomaly-v03-principal-boundary-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-principal-boundary-2026-09-15.md)を参照。
専用標準local account Pと現在userのordinary peer U、管理者側bootstrap B、consumer Rを区別。各object/期間の必要権限とUの禁止操作、外側祖先・既取得handle・process/thread/token/IPC・code/資格情報を一覧化した。
同一userのrestricted token/AppContainer ACE追加だけで通常peer排除が成立とはしない。P/Uの別SIDだけでも成立としない。
候補account BantoS4Publisher、root C:\ProgramData\BantoAI-S4B2-principal-20260915 はUTC2026-09-14T16:09:00Zの読取確認で未存在。OS設定は変更していない。
このPCに標準accountと保護rootを追加する環境案についてユーザー判断を受ける。理由は永続設定・管理者承認・資格情報/起動管理の追加。skillや自動審査による停止ではない。
ユーザーの方式選択前にaccount/profile/service/VMを作らない。選択後は実装・故障確認・レビュー・savepointを経て新規max1だけに進む。追加承認を求める場合も、既に許可された範囲を再確認しない。

初回harnessはPの新規root/空file作成と、独立U workerの読取control/変更open/path CREATE_NEWを比較する案。
SDDL/mask、保護された起動、code/runtime配置、IPC、作成失敗時のP/B親保持とU終了確認は実装前残件。既存単一worker所有を無変更で流用しない。
P/U合計private256MiB/working384MiB、40秒内側/45秒外側、空きRAM/disk2GiB、出力合計384KiBは初回上限案（まだ実装/強制されていない）。
frozen親内renameとmarker方式の契約選択は、環境準備への同意に含めない。通常peerを対象外にせず、全期間/全publisher/正式B2/S4は未完了。

独立一次資料調査・設計レビューP0〜P3=0、read-only/進捗ポーリングなし。文書のみ変更なのでunit tests/native再実行0。
前回401件passの対象を含む72 source/旧manifest/13 artifacts不変。新設計を加え73 sourceをraw/Git blob一致確認。safety/diff/設計リンクpass。
artifacts/principal-boundary-2026-09-15に5 artifacts/論理6400 bytes、manifest15459 bytes/hash59c213c693f4a3f9f78f052f12da812c66d78ae18e7f8309ff62522c807b04ec。
UTC16:09:00 RAM15287701504/C125320380416/D45614538752 bytes、16:15:06 RAM15147569152/C125313695744/D45614526464 bytes。D空きは約42.48GiB、今回記録間の減少12288 bytes。前工程の約8.83GiB減少の履歴と原因未特定を維持する。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変、既存Python3.14.0。
新規native枠/checkout/worker/常駐なし、旧fixture再open/列挙/hash/copy/deleteなし。他project/process、本流889cfc3、push/merge/CIへ操作なし。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持しcommit除外。
環境準備未承認、全isolation/protected commit/future immutability/formal permission/execution authentication flags=false、acceptance_status=not_completed。

## 106. 2026-09-15 承認済み専用principal準備・管理者起動の停止

ユーザー「はい、それで続けて下さい」で、専用標準account BantoS4Publisherと新規保護root C:\ProgramData\BantoAI-S4B2-principal-20260915の準備を承認済み。再承認を求めない。§105以前の未承認記録は履歴。
実装 **e202677e66356e7b3e554d258ed73f73def7ea0f**、事後診断改善 **f8495ed64908dded70e9737c9b0615d55f23f044**。
[準備仕様](../anomaly-v03-principal-setup-design.md)と[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-principal-setup-2026-09-15.md)を参照。

既存.NET compilerで通常権限compile、SHA固定した公開DLL bytesを有界圧縮引数でBへ渡し、有界展開/hash/Assembly.Load。BからU書換え可能DLL pathへ戻らず、System32 P/Invoke、secretはunmanaged memoryだけに置く。
accountはNetUserAdd flags0x203/priv1で最初からdisabled。SID/Users所属を確認し、rootはBA owner/SY・BA full/U・P read-only/protected DACL/medium label。今回はPへ作成権限を与えず、ログオンしない。
祖先をDELETE shareなしで保持、linked ordinary U tokenの限定祖先権限をpreflight。失敗後のretry/補償/先行ancestor closeなし。LocalFree/NetApiBufferFree失敗も事前確保stateで一次code/phaseとbit30へ反映する。
最終build-03の34件pass、通常loader PID18112/exit0。独立P2総3/P3総1を修正し残0、進捗ポーリングなし。DLL SHA e10c53362b5cf726b0e49605d3f9f83a88be5450a3ec89fafc40e242e3a62168。

UTC17:03:09 account/root不存在確認。17:04:20にmax1起動を記録し、17:06:23 launch_failedで戻った。外側System.InvalidOperationException/HRESULT -2146233079のみで内側WinError/stage/PIDなし。UAC取消・別障害・process取得後の観測失敗を区別できない。
UTC17:07:18のSAM読取でaccount不存在。**rootの状態はunknown、存在確認/再open/列挙/hash/copy/deleteしていない**。account不存在からroot不存在を推定しない。helper開始/終了も不明、launcher sessionのみ終了確認。環境準備は未完了。
作成attemptは閉鎖し再実行なし。launch-attempt.jsonの存在guardを解除しない。旧test source/枠への再訪もない。
f8495edでは将来の失敗を最大4段のexception type/HRESULT/native code、起動stage、取得済みPIDだけで記録する。Message/commandは保存しない。純粋記録関数の追加6項目pass/独立所見0。今回の失敗原因を遡及確定しない。

ignored artifacts/principal-setup-2026-09-15に27 artifacts/論理437818 bytes、最終manifest22001 bytes/hash e5acb7c762bac4f91f59c879eebd5e115a5d41e9f97aa58c00e6379efa898e21。
native input18733 bytes/hash34e49c942f16123745fd9ac62dabc013d0871d72f66fef35695077091adf06c7とinput時20 artifactsは不変。最終78 sourceを診断revisionでGit/raw一致確認、前回73 source/5 artifacts不変。既存401件は対象実装不変のため再実行なし。
UTC16:40:36 RAM16880279552/C125132517376/D37115596800 bytes→17:09:46 RAM15485636608/C125072465920/D27387604992 bytes。D約25.51GiB、今回約9.06GiB減少の原因未特定、17:03以降ほぼ横ばい。他project/processの走査・停止なし。長期リーク不在の主張なし。
build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変、Python3.14.0。新runtime/service/task/VM/profile追加なし、本流889cfc3/clean不変、push/merge/CIなし。
既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全しcommit除外。

次はWindowsの管理者確認を操作できる状態で、OS設定を変更しない独立の昇格診断を先に実装・確認する。閉鎖attemptのretryや不明rootへの再訪を診断と呼ばない。実際の起動を確認してから新規対象と保全状態を仕様へ固定する。
専用環境方式への許可は継続。Pのactivation/reset/logon/disable、protected code/process/thread/token/IPC、P/U試験、namespace共通期間、全publisher/frozen/marker/正式B2/S4は未完了。全許可flags=false、acceptance_status=not_completed。

## 107. 2026-09-15 容量整理後の復帰・管理者起動診断成功

ユーザー「容量余裕がでましたので再開しましょう」により本来の権限分離へ復帰。実装d7253c8dd16ece6c128656e716371863d4e5bc2f、[結果・正本hash](anomaly-multiseed-v0.3-s4-b2-elevation-diagnostic-2026-09-15.md)。
通常control PID37092/exit41/492ms、RunAs PID39144/exit40/5958ms、固定U SIDでadmin切替を自己照会。Handle確保・終了code・解放を観測、例外なし。UACを含む起動要求は5260ms、返却後待機650ms。
OS設定変更・準備Entry・P logon・旧rootアクセスなし。前回原因unknown/旧attempt閉鎖を維持する。今回の2診断guardも閉鎖し再試行しない。
13故障ケースpass/独立所見0/進捗ポーリングなし。前回78 source不変、新規を含む81 source Git/raw一致。manifest17286 bytes/hash9e4c0c8fb6f45208820c590fc5d7141fd03b62de45512dd3e3be45e26ef1bf89、9 artifacts/論理18269 bytes。
UTC02:38:48 RAM10558652416/C130972598272/D203548774400 bytes。build26200.9445/boot不変、Windows Update engineering緩和/正式pin不変。既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全。本流889cfc3/clean不変。
次は新規root/記録場所を仕様に固定し、観測処理を準備launcherへ適用して確認・保存後に承認済み準備を進める。環境準備/P-U/正式B2-S4未完了、全許可flags=false。

## 108. 2026-09-15 新規準備bの起動停止・直接Shell診断の通常control完了

準備b実装4bdeaeda871ac5d65b27ae1b45f564f609b89b6d、[停止結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-b-2026-09-15.md)。rootをC:\ProgramData\BantoAI-S4B2-principal-20260915b、記録をartifacts/principal-setup-b-2026-09-15へ固定した新規max1。account名BantoS4Publisher/同名不存在条件は維持。
34件＋共有observer13ケースpass/独立0。通常load-only PID37216/exit0、DLL SHA4ea7c99167a71c9ba6e26f2d6d3a74ad16226d8209dc3535d19660696440a88a。UTC02:57:08 account/root不存在確認。
02:58:09〜03:00:12 request-launch段階で123158ms後に失敗、PID/Handle/exit不明、InvalidOperationException/HRESULT -2146233079/innerなし。03:01:00 SAM2221でaccount不存在、新rootもunknownとして閉鎖。末尾bなし/ありの両rootへ再訪しない。両作成guardを再利用しない。manifest19470 bytes/hash3813fb07fcb1ece244c094cacfdcf17d89393d1984865e9516f7da91258e46ab、83 source/11 artifacts/論理61089 bytes。

このPCのWindowsPowerShell Management assembly/StartWithShellExecute IL63 bytesをread-onlyで確認し、Win32ExceptionをMessage-only InvalidOperationExceptionへ置き換えることを特定。起動原因は未確定のまま。
新しい[Shell診断仕様](../anomaly-v03-shell-launch-diagnostic-design.md)と[通常control結果・正本hash](anomaly-multiseed-v0.3-s4-b2-shell-launch-diagnostic-2026-09-15.md)、実装558b118a378d0819f0776e727e9a78cb125f289a。
Process.Start(ProcessStartInfo)を直接呼び、UseShellExecute=true/Runだけrunas/Hiddenを維持。OS変更なしの固定SID/admin自己照会をASCII Command＋commentで15331文字へ固定。DLL/準備Entry/旧rootを含まない。
新規3ケースpass（非Shellの実missing-exe error2保持含む）/独立0。通常ControlはUTC03:08:52〜53/PID43368/exit41/532ms、Handle・終了・解放確認、例外なし。Control枠閉鎖、Run枠は未使用。
ユーザーへ「直前のアカウント準備でWindowsの確認画面が表示されたか」をasync質問中。返答まで新診断Runを保留し、未回答を承認/画面なしと扱わない。専用環境準備の許可は継続、方式再承認を求めない。
input16278 bytes/hash90da7ba37f5a9c71652d60e1bb562c4d3812e418fd31f1159b3c3ac8329740f1、86 source、前回83 source/11 artifacts不変。checkpoint17947 bytes/hash57d8b1e198c1ea5ffa90ffc31fea7242e3f858bffeb2b3fa25b04716d2a3fa9c、6 artifacts/論理18438 bytes。途中checkpointは上書きせず、Run後は別の最終manifestへ記録する。
記録追記＋commit複合操作に自動審査blocked by policy（詳細なし）があった。副次的な個別記録を省いて対象4ファイルのstage/差分確認/commitへ限定し保存成功。同じ複合操作は再実行せず、レビュー/IL要約を後続inputへ記録した。
UTC03:09:42 RAM10321457152/C130921562112/D202743402496 bytes、D約188.82GiB。build26200.9445/boot不変、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全しcommit除外。
次は質問への回答を踏まえ、新Shell診断Runだけを新規max1実行する。さらに別の準備rootは未定で、設定作成へ直行しない。P-U/全期間/全publisher/frozen/marker/B2-S4未完了、全許可flags=false。

## 109. 2026-09-15 管理者画面表示の回答・直接Shell診断Run成功

ユーザー「管理者確認画面でました」を受け、直前の準備bのUAC表示をuser reportとして記録。「はい」操作の有無は未報告、以前の失敗を取消と断定しない。既存環境方式への許可を再確認せず、用意済みの読取専用Shell診断Runだけを一度実行した。
[結果](anomaly-multiseed-v0.3-s4-b2-shell-launch-diagnostic-2026-09-15.md)。実行前に86 source/途中6 artifacts/checkpoint/既存親policy結果書不変を確認し、新規resume-inputを保存。
UTC03:21:34.6280050Z〜03:21:38.8898553Z、PID26600/exit40/合計4256ms、起動要求3715ms/終了待機493ms。固定U SID/admin、Handle確保・終了・解放成功、例外なし。15331文字/引数hash21d6c88f3189451971464c90615fa7c7d2a54af9db2fc4c9eb5063d7e822ec44は通常Controlと同一。今回形式で起動可能という結果で、準備の実内容や以前の失敗原因を確定しない。
設定変更・準備Entry・account/root APIなし。旧root2件はunknownのまま再訪なし。Shell診断Control/Run両guardも閉鎖し再使用しない。観測した今回process終了済み、以前の不明helperまで終了済みとはしない。
最終manifest20428 bytes/hash313d3ac89b1b5d92d803920aee8cf2a4a105cec19151018292fb1149dff8bb0d、11 artifacts/論理38536 bytes。途中checkpoint/inputは上書きせず保全。実装変更なし、既存3ケース/共有13ケース/C#34件は対象不変のため再実行なし。
UTC03:22:55 RAM9855365120/C130778591232/D202743259136 bytes、D約188.82GiB。build26200.9445/boot不変、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全しcommit除外。
次は公開DLLの有界展開/hash/Assembly.Loadだけを管理者側で行う読取専用の新規診断を仕様化・確認・レビュー・保存する。準備bの公開build-01 DLLを使用する場合はSHA4ea7c99167a71c9ba6e26f2d6d3a74ad16226d8209dc3535d19660696440a88aを固定する。準備Entry.Runを呼ばず、新規診断guardを用い、旧Control/Run/準備の再実行やさらに別root作成へ直行しない。質問は回答済みで同じ表示確認を再質問しない。P-U/全期間/全publisher/frozen/marker/B2-S4未完了、全許可flags=false。

## 110. 2026-09-15 公開DLL読込み成功・準備cの停止・token照会長の修正

公開DLL読込み専用診断を64307e50aef7d48902e3a5db76a78d1bec7d377eで保存。[結果](anomaly-multiseed-v0.3-s4-b2-principal-loader-diagnostic-2026-09-15.md)。8ケースpass/独立0。通常Control PID4592/exit41/2980ms、管理者Run PID33600/exit40/6951msで終了・解放を確認。既存b公開DLLを有界読取り/hash照合後にAssembly.Loadし、Entry.Runは呼んでいない。両guard閉鎖。manifest19096 bytes/hash e0698abf81077fcca1828c00534bbb6d0f1814102bbbc41b0109f539465fe2bf、89 source/9 artifacts/論理20661 bytes。

既存許可の範囲で新規準備cを9fec67862b1629193b47bac2f1bcfbcebaa0dfd0に固定。[結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-c-2026-09-15.md)。rootはC:\ProgramData\BantoAI-S4B2-principal-20260915c、記録はartifacts/principal-setup-c-2026-09-15。直接Process.Startを適用し、34件pass/独立0、実行前SAM/root不存在を確認した。
UTC03:37:25.6325778Z〜03:37:54.4438124Z、PID26584/exit65560（phase1 Preflight＋native24）、起動25947ms/待機2814ms/合計28808ms。今回helper開始・終了・Handle解放を確認。固定コードの順序ではHoldAncestors/root/account作成前に停止したという推論であり、終了後rootの実観測ではない。UTC03:39:29のSAM2221でaccount不存在を確認したが、rootは再確認せず閉鎖した。旧3 rootの存在確認/再open/列挙/hash/copy/delete、作成guard解除・retryなし。
準備c manifest20120 bytes/hash c6be745af63eb0bc79e5d48170b3fd40f38f8e1d7727e1c56fb438e70a3ead7b、90 source/9 artifacts/論理60750 bytes。現在の準備Runは閉鎖済みc定数/guardのままなので再使用しない。

通常の自process tokenだけを比較する読取診断を79a8ef302016ace8514cce03767aa10419204396で保存。[結果と修正](anomaly-multiseed-v0.3-s4-b2-token-length-2026-09-15.md)。UTC03:51:53、class19/長さ64はerror24/必要8、長さ8は成功、class20/長さ64はerror24/必要4、長さ4は成功/elevation0。成功取得したown/linked handleは解放成功、一次/解放例外なし。UAC・impersonation・Entry・SAM/root操作なし。独立レビューP2一件と結果保持を修正し残0で実施、進捗ポーリングなし。診断guard閉鎖。
診断manifest18201 bytes/hash7cd7fa72532618593a34421881b786353847c0e8a282dae1312a9e98946900e0、92 source/2 artifacts/論理2195 bytes。source照合は観測後に行った。通常tokenでの結果なので管理者Preflight全体や旧起動障害の原因まで確定しない。

7a2f066ff36e90abe4f88c5103cd2a665bc97c59でPrincipalSetup.csの要求長2行だけをIntPtr.Size/4へ修正。64-byte確保と返却長・所有権・解放・他phaseは維持。独立追加所見0、絶対source pathによる別名build-02で34件pass。最初の相対path compileはCS1504でDLL出力前に停止した。修正buildの管理者Preflight/Entryは未実行。
artifacts/principal-token-fix-2026-09-15のmanifest17683 bytes/hash1958f45e3c14f41b04e6027a10c057c83460a378aa964ba707798ed6f5efda7b、4 artifacts/論理40531 bytes。92 sourceをGit/raw照合、前回91不変/C#一件変更、前回2 artifacts不変。新規常駐/runtime/service/task/VM/profileなし、閉鎖rootアクセスなし。
UTC04:24:07 RAM7059361792/C148160946176/D219494100992 bytes、D約204.42GiB。空き増加の原因は今回と関連付けず、長期リーク不在の主張なし。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean不変、push/merge/CIなし。既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全しcommit除外。

次は修正buildを使う**管理者Preflight専用**の新規読取診断を仕様化・確認する。root/account作成phaseやEntry.Runを呼ばず、取得tokenと自己watchdogを終了まで管理する。新規guardを使用し、旧root/guardは再使用しない。NativeBackend.Execute(Preflight)だけを呼んで終了管理を省略してはいけない。この事前確認が通ってから次の新規環境準備を具体化する。専用環境準備の許可は継続、UAC表示は回答済みで再質問不要。
環境準備/P-U/IPC/namespace共通期間/全publisher/frozen/marker/正式B2-S4は未完了。isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。

## 111. 2026-09-15 管理者Preflight成功・準備dの特権不足停止

d025f4bbd83a9e928c3b93ecdae373605c47459bで5 phase限定のPreflight診断を追加。[最初の結果](anomaly-multiseed-v0.3-s4-b2-principal-preflight-2026-09-15.md)。既存34件/新診断9件/loader10件pass、独立P2一件を修正して残0。Entry前にidentity解放を完了し、診断codeを二次例外で失わない。通常Control PID41156/exit41、管理者Run PID39304/exit66882（phase1/native1346）で終了。manifest21180 bytes/hash46fa0a7d1e4a882d4d8e31d2fcdb43ed305057a7956d1bcaa406a52c3fe405c4、97 source/17 artifacts/論理75892 bytes。

35c46670f560bff054af63ffe0ac7c346404b01aでAccessCheck専用peerTokenのDuplicateToken要求level2→1へ一行修正。[結果](anomaly-multiseed-v0.3-s4-b2-principal-identification-2026-09-15.md)。SID/非昇格/危険権限mask/予算を緩めず、34/9/10件pass/独立0。新DLL24576 bytes/hash05a77ce8bfe3c16d166eabd14c614ce85040f2f0089cdfc673c611ae161d6e6f、command16754文字/hash9694e60e2c6fcac316aeaeab5c862176e0d77711d93f7cff18fbd4d24826876c。
通常Control PID18720/exit41/2603ms成功。管理者Runは05:09:45〜05:11:49、123261ms後request-launchで内側Win32 error1223、PID/Handle/exit未取得。Windowsの取消扱いを記録し、手動操作と時間経過を区別しない。両guard閉鎖、旧rootアクセスなし。manifest21412 bytes/hash55b53f9d0125575392a8752ef939c94133995c3606fce138e869341281fea7ec、98 source/14 artifacts/論理75372 bytes。

管理者画面を操作できる都合を質問し、ユーザー「今なら操作できます」と回答。方式の再承認ではない。57904679ef4b11c401fa176f04012f6c513a8e52で記録先一行だけを新規principal-identification-confirmation枠へ変更、公開DLL/commandは同一。既存Controlを参照し再実行せず、新規Runのみ実施、差分独立0。
[成功結果](anomaly-multiseed-v0.3-s4-b2-principal-identification-confirmation-2026-09-15.md)。UTC05:16:32.0030613Z〜05:16:40.5498031Z、PID43308/exit0、起動4715ms/待機3754ms/合計8541ms、Handle・終了・observer解放成功、例外なし。修正Preflightと3 token close/StopWatchdog完了を確認した。SAM/root/作成Entryなし、当該guard閉鎖。manifest18985 bytes/hash92de13846a4f7208994ee1a2b9606f84333a3bdca3f6a2497d92d8e29be21d76、98 source/6 artifacts/論理22240 bytes。

f5ad7c21389e7ae26eb48858b6017691fecedb22で承認済みの[新規準備d](../anomaly-v03-principal-setup-d-design.md)を保存。新規root C:\ProgramData\BantoAI-S4B2-principal-20260915d、artifacts/principal-setup-d-2026-09-15。root/記録固定値のみ変更、34件pass/独立0、通常load-only PID20872/exit0。DLL22528 bytes/hashfc88778d472098160f81302b8058b4b8cabcfa015119098b585fd03cce57007e。
UTC05:20:34 SAM2221/root attributes0xffffffff/error2で新規対象不存在を確認。[実行結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-d-2026-09-15.md)。05:21:30.6208593Z〜05:23:38.6962403Z、PID22336/exit263458（phase4 CreateRoot/native1314）、起動124066ms/待機3952ms/合計128068ms。Handle・終了・observer解放成功、観測例外なし、release_failed=false。
固定codeではPreflight/祖先保持とpeer AccessCheck/不存在確認を通過し、root作成phaseで停止。個別API名の記録ではない。account作成phaseへ未到達、05:25:12のSAMは2221/free0でaccount不存在。**root dは再確認せずunknown、末尾なし/b/c/dの4 rootを閉鎖。存在確認/再open/列挙/hash/copy/deleteしない。** 作成guardを再利用せず、account不存在からroot不存在を推定しない。
準備d input19396 bytes/hash45bc965885a1335787546854b06d077ece3f72172bc1f17ca43a4e885de8c725、99 source、前回96 source/6 artifacts不変・2変更/新規1。最終manifest20341 bytes/hashd009f150c6cfbeb3796517ca6dda2390669884b7a870766bcae817a18059a989、9 artifacts/論理62344 bytes。

終了UTC05:25:12 RAM6053531648/C148569583616/D218658721792 bytes、D約203.64GiB。長期リーク不在や他の空き変動原因は断定しない。build26200.9445/boot2026-09-09T10:43:08.5000000+09:00、Windows Update engineering緩和/正式pin不変。新runtime/service/task/VM/profileなし、本流889cfc3/clean不変、push/merge/CIなし。既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全しcommit除外。独立レビューは既存1体へ差分だけ委譲し、進捗ポーリングなし。
次は明示SACLに必要な特権の事前確認と、B process内の一時有効化/元状態復元を設計・故障検証する。公式SACL仕様はSeSecurityPrivilege有効化を要求するが、今回失敗processの特権一覧/有効状態は未観測なので原因確定とはしない。OSへ追加の特権付与を行わず、SACL/medium labelや初期保護条件も省かない。確認用の新規診断枠で検証してから次の新規環境準備へ進み、閉鎖dをretryしない。専用環境の許可と画面操作可能の回答は記録済み。
環境準備、P activation/reset/logon/disable、protected code/process/thread/token/IPC、P/U、namespace共通期間、全publisher/frozen/marker/正式B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。

## 112. 2026-09-15 既存特権の復元成功・準備e取消・f通常側準備済み

ec94a5920f08a824cbf35bb1433f61b0e9b68c30でB processの既存SeSecurityPrivilege一件のscopeを実装。[仕様](../anomaly-v03-principal-security-privilege-design.md)/[結果](anomaly-multiseed-v0.3-s4-b2-security-privilege-2026-09-15.md)。4096-byte上限で存在と初期有効ビットを読み、必要時だけenableし再照会。CloseAdminTokenでは元の有効ビットへ復元・再照会してから閉じる。TRUE+ERROR_NOT_ALL_ASSIGNEDも失敗、同一backendへ固定、失敗時は後続/再試行なしでprocess終了。新たなOS特権付与や他の特権変更はない。34＋9＋15＋10の68件pass/独立0。
DLL25600 bytes/hashcc7a3d42b26ea79015955cb76047d90ced4bd7dc109e74b1bec5898548b6ac1d、同command17566文字/hash82e9b02eee0c24ced40b6c087e2c9506dba9337ca01e76af23df39dab0bb26a3。通常Control PID9756/exit41/8855ms、管理者Run UTC08:27:17.4000397Z〜08:27:25.3555877Z/PID33600/exit0/7950ms。Handle・終了・observer解放成功、例外なし。特権の存在/有効/復元確認と3 token close/StopWatchdog完了を確認した。初期enabledbitの値は未記録なので、元から有効か今回enableしたかを断定しない。作成Entry/SAM/rootなし、両guard閉鎖。
診断input20660 bytes/hash7f478085abb6b7063d720aa14e553b11e931c4ded2001aed3792e6a40c7b4782、101 source、前回96不変/3変更/新規2。最終manifest21910 bytes/hash4ebea15097d1a5d1e5a53461875412bc99e41f7ff62aa6e8a337a15eb7bd10ef、16 artifacts/論理87900 bytes。

e23564c43e7a3c50101c07e38b9c4da052be4c38で[準備e](../anomaly-v03-principal-setup-e-design.md)を保存。root/記録をeへ固定しBuildが特権15件も必ず実行するよう変更、34＋15件pass/独立0。DLL25088 bytes/hash734e654339aa46e4f66cd86e98be1a3ba5585a0ebda4b4bea45d0ce04e09e88b、通常load-only PID33788/exit0。08:31:35 SAM2221/root error2で新規対象不存在を確認。
[停止結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-e-2026-09-15.md)。Run UTC08:32:27.5162967Z〜08:34:30.9979697Z、request-launchで123472ms/合計123474ms後に内側Win32 error1223、PID/Handle/exit未取得。Windowsの取消扱いを記録し、手動操作/時間経過を区別しない。helper開始・終了/作成phaseは未確認。08:35:30 SAM2221/free0でaccount不存在、**e rootは再確認せずunknown・閉鎖。旧末尾なし/b/c/d/eの5 rootへ存在確認/再open/列挙/hash/copy/deleteしない。** 今回guardも再使用せず、account不存在からroot不存在を推定しない。
準備e input20101 bytes/hash6d03fa689ea51fa3db02bdcdab79d6ecc077179e510fec16017f9cd935e9efb4、102 source、最終manifest21481 bytes/hash24a21c73c965c3b489b85b042fa2d650d371ad4329048f072bfa7b9633765c60、10 artifacts/論理78182 bytes。

今回の管理者画面操作の都合をasync質問し、**回答待ち**。既存方式への再承認ではない。以前の「今なら操作できます」は以前の枠の回答なので、今回の未回答を操作可能と扱わない。d2bdb66a88a51ee7cdc25afc9605c9a11097ae46で[新規f仕様](../anomaly-v03-principal-setup-f-design.md)と実装を保存し、[通常側準備結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-f-ready-2026-09-15.md)を別途記録した。新root C:\ProgramData\BantoAI-S4B2-principal-20260915f、artifacts/principal-setup-f-2026-09-15。C#とlauncherは固定値だけ変更、34＋15件pass/通常load-only PID33568/exit0/独立0。新DLL25088 bytes/hash3d236d9b2b920a4bbbf0550839bac94abd551f7debee73c02ec531a086d6f1bf、command16727文字。
新規Runも直前のSAM/f不存在照会も未実施。ready-evidence.json20120 bytes/hash4e77c062459bcd2b9e0d646afd7b0f3492732092fcc2eb09bb8e71d00c07688b、103 source、前回100不変/2変更/新規1、旧e10 artifacts不変。6 artifacts/論理55047 bytes。これは実行前savepointで、Runの成功や閉鎖を示さない。
再開時は回答を確認後、ready/source/DLL/旧e証拠の不変と直前資源を確認し、対象SAM・新規f不存在を照会して新しいinputを保存する。ready記録を上書きせず新規guardでRun一度。成功時のみfの既知receipt/SAM確認、失敗時はfも閉鎖する。

最終UTC08:40:41 RAM13034573824/C144674852864/D204764569600 bytes、D約190.70GiB。開始08:26:44 D211023683584からのPC全体の変動原因は未確認で、今回の小規模出力と区別する。長期リーク不在の主張なし。build26200.9445、bootは**2026-09-15T14:30:24.5000000+09:00**へ変化（前回9/9起動、原因未確認）。Windows Update engineering緩和/正式pin不変を維持する。
本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。新runtime/service/task/VM/profile、push/merge/CIなし。独立レビューは既存1体へ差分限定、進捗ポーリングなし。
環境準備、P activation/reset/logon/disable、protected code/process/thread/token/IPC、P/U、namespace共通期間/全publisher/frozen/marker/正式B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。

## 113. 2026-09-16 初期policy通過・無効P作成・最終検査の診断待ち

2026-09-16 JSTの「次に進めてください」で再開した。管理者画面操作への回答待ちは今回の再開指示と実際の起動成功で解消。c8c4a36の準備fはsource103/ready6/旧e公開artifact10の不変と不存在を確認後、一度実行。PID12448/exit393215、phase5/detail65535、終了・observer解放確認。後続SAM2221/free0、f rootへ再訪せず閉鎖。[f結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-f-2026-09-16.md)。最終manifest22508 bytes/hash541dfa7c139626693e011668f2ea32f52a1a73f83c687815c952c1866abd0553、12 artifacts/論理97805 bytes。

5fe02878bd75911a56878406f081db8c28bc08a6で[固定診断g](../anomaly-v03-principal-setup-g-design.md)を保存。phase5のunknownのみbit29で細分化し、事前確保step/SD差を返す。保護条件・厳密比較・失敗停止を維持。build01でGetSddlForm(Audit)のlabel省略を試験検出、raw ACL比較を加えたbuild02で43＋15＋launcher12件pass/独立0。[g結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-g-2026-09-16.md)はPID10092/exit537209480、phase5/kind1/step10/差136=8+128。初期policyのSACL部分とauto flags差を観測したが、AI/ARやlabel自体の差まで特定せず、fの原因にも遡及しない。後続SAM2221/free0、g閉鎖。最終manifest23630 bytes/hash753f2f440a0f8edfb4b9f43668ca2de736fbb634e25c10dce2f8cf20cda95912、14 artifacts/論理135727 bytes。

aa0bc5e16010e8fd3a61239359ed1f67f41df5faで[新規h](../anomaly-v03-principal-setup-h-design.md)を保存。要求SDDLをS:PAIへ限定変更し、旧descriptorとのbinary差が0x0800だけである試験を追加。owner/group/全ACL bytes、両protectedとmedium/no-write-upを維持し、差の無視はしない。44＋15＋launcher12の71件pass、独立0、safety/diff pass、通常load-only PID11952/exit0/command17859文字。
採用DLL26624 bytes/hash4b04ed4b32a6e1713cc806804c8532fca22a7e9f32685bf087b4c345b7e93c0f。105 source（前回101不変/3変更/新規1）と旧g14 artifacts不変。直前SAM2221/root error2、input20709 bytes/hash1784e62199d216d66551e0fa7240a44cc2a055f4997507d41b5a31705685bc19。
[h実行結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-h-2026-09-16.md)。UTC2026-09-15T15:25:59.3588285Z〜15:26:07.5741839Z、PID26248/exit786431=phase11/detail65535、launch3842/wait4330/total8215ms。Handle/終了/observer解放確認、例外なし。初期root厳密検査、disabled account作成、Users確認、最終DACL設定を通過。phase11はBudget/祖先/root identity/policy/account/groupを含むため具体的停止条件は未特定。失敗後の特権復元や通常teardown完了は認定しない。

終了後UTC15:28:37 SAM/status/free各0、P **BantoS4Publisher/S-1-5-21-2169670816-255940906-2713565042-1010/flags515=0x203/disabled=true**。group照会/解放各0、read=total1、Usersだけ。enable/reset/logonなし。h rootとreceiptへ再訪なし。**旧末尾なし/b/c/d/e/f/g/hの8 rootはunknown/閉鎖。存在確認/再open/列挙/hash/copy/delete、旧guard再使用をしない。** accountは存在するので従来の同名不存在→作成経路も再実行しない。
h最終manifest23372 bytes/hash0540df3b7945f65f7e6a641af7c0f96bb79f4694d7f31a13804df242b654fef4、11 artifacts/論理86253 bytes。105 source/保存artifact/既存親policy結果書不変、本流889cfc3/cleanを確認。

次は、既存の無効Pを変更せず使う新規root準備経路を設計する。name/SID/flags/Usersを通常側とhelper側で固定検査し、NetUserAdd/所属追加/reset/enable/logonを呼ばない専用経路が候補。Pへの権限は新規rootのreadonly ACEのみ。新規失敗枠でphase11の停止substepを返し、現rootやaccountの削除・補償で解決しない。DACL auto flagsの差は仮説であり、実観測前に最終SDDL条件を緩めない。設計・故障試験・独立レビュー・savepoint後に新規管理者実行へ進む。
最終RAM4387188736/C149664280576/D198225702912 bytes、D約184.61GiB。PC全体の変動原因や長期リーク不在は未確認。OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。新runtime/service/task/VM/profile、push/merge/CIなし。独立レビューは既存1体に差分限定、進捗ポーリングなし。
環境準備/P activation/reset/logon/disable、protected code/process/thread/token/IPC、P-U/namespace共通期間/全publisher/frozen/marker/正式B2-S4未完了。全許可flags=false、acceptance_status=not_completed。

## 114. 2026-09-16 既存P維持経路・専用環境準備j成功

092fb4b7b83e2467b2f26b4258a30ecd94c8b682で[既存P専用i](../anomaly-v03-principal-setup-i-design.md)を実装。ExistingEntryはphase6/8を省く20phase、作成/所属変更/RNGの実装とimportを削除。phase3でP name/SID末尾1010/flags0x203/Usersを固定照会し、新規root不存在だけ確認して進む。phase7/9/11でも再検査。phase11へ固定step診断を拡張し、77件pass/独立0。
[i結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-i-2026-09-16.md)はPID31244/exit537602628/phase11 kind1 step10差68(DACL4+auto64)。終了/observer解放確認、SAMのP無効/Users不変。iへ再訪せず閉鎖した。最終manifest24200 bytes/hash3bde24e28de4a1c0076c0ebf0e5826577179fe3217ac4864f4f82ad3a47b2524、11 artifacts/論理90815 bytes。iの差からAI/ARや実ACEの一致を遡って断定しない。

1f253cc4fa984462a3d0bf7d4e66d23d230eaf56で[新規j](../anomaly-v03-principal-setup-j-design.md)の最終要求をD:PAIへ限定変更。初期D:P/S:PAIは不変、最終descriptor binary差は0x0400のみで全権限/両protectedを維持。50＋15＋launcher13の78件pass、独立指摘0、safety/diff pass。通常load-only PID20772/exit0/command17271文字。DLL26112 bytes/hash4d6b2fa835176986faa4791a62865144451fd4a6b6823dc95a711a5b9a34be25。
107 source（前回103不変/3変更/新規1）と旧i11 artifacts不変。直前SAM固定条件/root error2確認、input21338 bytes/hash5fe087c324fa68b2882908c3d3bced0b4d01f7c780a9dbadd466850e4ee92b17。
[j成功結果](anomaly-multiseed-v0.3-s4-b2-principal-setup-j-2026-09-16.md)。UTC2026-09-15T15:44:08.8914053Z〜15:44:17.7382677Z、PID3284/exit0、launch4125/wait4680/total8841ms。Handle/終了/observer解放確認、例外なし。初期/最終の厳密policy、receipt write/flush、child/root/ancestor/token close、元の特権有効bit復元・再照会、watchdog終了まで完了。

**準備済みroot C:\ProgramData\BantoAI-S4B2-principal-20260916j を保存。旧末尾なし/b/c/d/e/f/g/h/iの9 rootは閉鎖し、存在確認/再open/列挙/hash/copy/deleteしない。jも作成guard消費済みでRun再使用不可。** 成功後だけjの既知bootstrap-result.jsonを有界読取・publicへコピーして確認。1128 bytes/hashf736744e7870f492f6913cba9476327246d0b82babc5a9f198ec6e58224a06d4、state=prepared-preclose、account作成/変更/logon=false。receipt単体ではなくexit0と組み合わせて正常終了を認定した。
root identity部分はtaBg2tdg2iouDAAAAABPAAAAAAAAAAAA（24 bytes）。実SDDLはO:BAG:BAD:PAI、SY/BA full、U SID末尾1001とP SID末尾1010各0x1200a9、S:PAI(ML;;NW;;;ME)。完全な文字列は結果書/public receiptに保存。取得範囲0x17はowner/group/DACL/mandatory labelで、全audit SACLや将来不変性の認定ではない。
終了後UTC15:45:24、P BantoS4Publisher/S-1-5-21-2169670816-255940906-2713565042-1010/flags515/disabled、Usersだけ（SAM/group/status/free全0、read=total1）。今回accountの作成/変更/reset/enable/logonなし。

成功verification953 bytes/hash1d70cd4dd4ab95a2be7a472a4506a51554548920357185ff4d6eb521826a6eb2、最終manifest26606 bytes/hash03a60920912a2157ea3183f2645829a2f0211dbc4a42c736c37cd2b11c4b3afe、13 artifacts/論理93657 bytes（自身除外）。107 source/inputartifact不変、本流889cfc3/clean。既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。
preclose記録elapsed148ms、観測peak private63029248/working73957376 bytes、minimum RAM5974740992/C149730889728。process全寿命の厳密peakや長期リーク不在ではない。最終RAM6247051264/C149730881536/D198225158144 bytes、D約184.61GiB。OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。新runtime/service/task/VM/profile、push/merge/CIなし。独立レビューは既存1体へ差分限定、進捗ポーリングなし。

**専用principal環境の準備は完了。** 次はprincipal境界案の保護code/runtime、B/P/U process/thread/tokenの初期SDと起動経路、IPC/所有台帳、単回有効化/ログオン/再無効化と全process終了を具体化して故障試験する。準備済みP/rootを再作成せず、現在のPを有効化して試す前にこの残件の実装・レビューを済ませる。P-U干渉/namespace共通期間/全publisher/frozen/marker/正式B2-S4は未完了。全許可flags=false、acceptance_status=not_completed。

## 115. 2026-09-16 worker lifecycle model・起動特権の読み取り診断

「次に進めてください」で再開し、**cbd3df9a61348562019a2c4ae9113e17e122dd96** に[起動・終了modelと読み取り診断](../anomaly-v03-principal-worker-lifecycle-design.md)を保存。[結果書](anomaly-multiseed-v0.3-s4-b2-worker-lifecycle-2026-09-16.md)。setup jのsource/guardを変更せず、新規6 sourceを追加した。
26操作の純粋modelはenable応答前にriskを記録、logonの成否に関わらずDisable→Verify、既知secretのゼロ化/解放後だけlaunch。未知取得は推測closeせず、job停止要求と所有process終了/job空確認を区別し、外側code/祖先を保持する。primary/secondary障害を別保存、同じ操作は再試行しない。実handle台帳・時間/メモリ制限・ACL/jobを強制するnative backendは未実装。
レビューでmodelの動的HashSet記録のOOM時工程飛ばしP2 1件を固定bitset/配列へ修正。診断の未確定out handle closeとclose例外によるprimary/他方close喪失P2 2件をQueryHandleLeaseへ修正。既存Maxwell 1体、進捗poll0、最終残存P0〜P3所見0。
採用build-03は**65 model＋8 query lease＋15 privilege/parser＝88件pass**、safety/diff pass。最初の手動csc相対path解決失敗は出力生成前に停止、固定launcherは絶対pathを使用。中間build-01/02は未採用として証跡だけ保存。

診断exe32768 bytes/hash **5f4f4ae2fa623067f7d4f05d3a4b1782f8fbcb7a11980de2ad3a4f54ab731a33**。通常Windows PowerShellで有界read/hash後の同一bytesをLoadし、一度だけMain実行。own tokenをTOKEN_QUERYで開き固定U SID末尾1001/elevation0/typeLimited、linked tokenも同SID/elevation1/typeFullを確認し固定3特権を読んだ。UAC/調整/権利付与なし。
UTC **2026-09-15T16:11:05.2815534Z**、query_complete=true、launcher exit0、own/linked close=true、acquisition_unknown=false、primary/release/両個別release error=null。
**SeIncreaseQuotaPrivilege: present=true/enabled=false、SeAssignPrimaryTokenPrivilege: present=false/enabled=null、SeImpersonatePrivilege: present=true/enabled=true。** このlinked tokenから将来のP token assignabilityや別UAC起動tokenを認定しない。不足特権からAPI失敗を断定せず、別user Pにcallerのrestricted-token例外を適用したとも扱わない。

公開artifact `artifacts/principal-worker-lifecycle-2026-09-16`。診断結果614 bytes/hash **9d44ebe97433f9ef71b86f71a6d32618c7dbd0022b3fa9cc2cc094a689ee8cee**、**launch-capability.jsonはCREATE_NEW guard消費済み・Diagnose再実行不可**。
input19627 bytes/hash **d4ccd4546b5fb26d61030de7795b8b8f1d6211ba8381c15b04b628a3d9bb41b2**。113 source（前回107不変/新規6）のworkspace/git blob一致と旧j13公開artifact不変を実行前後に確認。
最終manifest24645 bytes/hash **1cae772d518ca0d62cb91a44deacc87560910ecc2e4b5159dfa3b088c2e0959a**、自身を除く16 artifacts/論理249764 bytes。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。
今回**旧9 rootと準備済みjを含む全保護rootへのアクセス、SAM照会/変更、P reset/enable/logon、worker起動なし**。P無効/Usersという最後の確認は前回j成功後SAMの記録。j準備成功は維持し、全rootの消費済みguard・閉鎖条件を継続する。
終了後UTC16:12:57、空きRAM6608343040/C149446660096/D198224842752 bytes、D約184.61GiB。観測点だけで長期リーク不在や変動原因、process全寿命peakを断定しない。OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。新runtime/service/task/VM/profile、push/merge/CIなし。

**次は追加のOS権利を付与せず成立する起動API条件を確定する。** CreateProcessAsUserWのtoken条件、process/thread/tokenの初期SD、desktop/環境/IPC、作成時job参加を結び付ける。既存privilege有効化と新しい権利付与は別。SeAssignPrimaryTokenPrivilegeを勝手に追加せず、SA引数のないAPIへ自動fallbackしない。既存権利で成立しない場合は必要権利/構成変更と影響を具体化してユーザー判断を求める。その後に実所有台帳/制限/containment adapterを実装・故障試験・レビューし、仕事をしないsuspended workerから進める。
environment_preparation_complete=trueは前回j結果のみ。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。P-U/全publisher/namespace共通期間/frozen/marker/正式B2-S4は未完了。

## 116. 2026-09-16 単一writer運用を優先・厳密な権限分離試験を保留

ユーザーが試験の目的と必要性を確認し、「同時に同じ個所を進めない限りは不要な気がします」と運用前提を示した。現在の開発は**同じ出力先への書込みを一度に1処理だけに限定する運用**を優先し、§115末尾の起動API/特権/専用P-U worker検証を次工程から外して保留する。単一writerは意図的な改ざんへの耐性の証明ではなく、その保証を今回の通常開発の前提にしないという範囲の整理である。

残す保存要件は、実行ごとの出力先分離、既存出力の非上書き、同じ出力先の重複使用拒否、失敗/途中終了した出力を完了扱いしないこと、完成を確認してから読むこと。これらの事故対策まで不要とは扱わない。既存 `tests/test_anomaly_v03_publication.py` に既存root/二重claim/完了印/非上書きのfixture試験があるため、再開時はこれを棚卸しし、通常アカウント・単一writer向けの最小保存契約と不足する処理だけを具体化する。今回fixture/native試験は追加実行していない。

**次の「続けて」では、専用principal試験を自動再開しない。** まず上記の通常保存経路を整理して機能開発へ戻る。既存の科学的評価条件・S4受入契約に影響する差分は明示し、未実施native試験をpassへ置換したり、`require_campaign_acceptance()`を黙って開放したりしない。隔離/将来不変性/正式受入は未完了の記録を維持する。

準備済みPとroot、既存証跡は保存する。今回SAM/rootアクセス、account reset/enable/logon、追加特権、UAC、worker/service/task起動、削除は行わない。P無効という最後の確認は§114のSAM記録であり、今回の再照会ではない。旧9 root閉鎖、jと診断の消費済みguard、既存親policy結果書の保全、本流不変更を継続する。厳密な分離試験の再開やOS資源の削除は今回の方針変更に含めない。

## 117. 2026-09-16 通常保存API・実ファイルの順次保存/読取り成功

§116の単一writer方針で再開し、**75a245ac190b944426371118ebda3fe820391f5c** に通常保存APIを実装。[使い方](../anomaly-v03-local-publication.md) / [結果](anomaly-multiseed-v0.3-local-publication-2026-09-16.md)。既存 `_anomaly_v03_io` の排他作成/非上書き/完了印/readbackを共用するLocalPublication・publish_local_result・verify_local_publicationを追加。新しい `anomaly-v03-local-complete` markerでfixtureと区別する。通常権限だけで動作し、temp外の明示した既存親の新規実行名へ保存可能。
writeが作成前に失敗した後やclose後でも再使用できる穴をfailed/closedで修正。commit試行を先に記録し、応答喪失後の失敗記録追記を拒否。独立レビューのcallback内失敗握りつぶしP2 1件はcommit前のfailed再確認・回帰で修正し、残存P0〜P3=0。既存1体、進捗poll0。
最終 **12 local＋15既存PublicationTests＝27件pass / failure・error・skip0 / 3.715秒**、safety/diff pass。実際の通常Python子processを保存途中で終了させ、完了印なし、reader拒否、同じroot再使用拒否を確認した。
最初の修正途中の4 module回帰は重い評価データ生成を含み、対象PID23824のcommand/start時刻照合後UTC16:34:06に停止。CPU320.8125秒/private104050688/working115589120。**中断でありpassに数えない。TemporaryDirectory cleanup完了は未確認で、個別path記録がなかったため古いfixtureと混同する探索/削除は行わない。** 最終変更は上記27件で検証済み。次回も必要な試験を選び、広い評価moduleを無条件に回さない。

公開実演 `artifacts/local-publication-2026-09-16/results/demo-01`。手書き2ファイル/合計28 bytesを通常writer PID6436（UTC16:35:46/exit0）が保存・readbackし、同じ名前への2回目をFileExistsErrorで拒否。元の結果も再検証成功。writer終了後、通常reader PID18180（UTC16:37:05/exit0）が開き直し、local_verified=true/payloads2。P-U分離試験ではない。
marker hash64e214f17417960928cd9d517d66414c97a22e8413162074ae2ef7d29b154df1、実演943 bytes/hashd4690ba3b30dd30a370abc01c6346bfe94485376f4636bab80a35616b3479178、別reader274 bytes/hash0ccc5803ca842153412fe474f00a640a20a7434b02b8a6b0998061686588d3cf。保存済みdemo-01へ再実行せず新しい実行名を使う。
input24101 bytes/hasha6f0cf63d0cf944097747b20bad74516b980aa9516207cda7ef774debeaceeb4。前回選抜113不変＋新規選抜4（既存改修2/新規ファイル2）、計117 source workspace/git blob一致、前回16 artifact不変。最終manifest27900 bytes/hash7504a0c6d241e22b35a0891acfcfd0e6dae3715acc8d84d822955deb3b512d81、自身除外8 artifacts/論理26958 bytes（中断テスト一時出力を含まない）。
終了後RAM6307483648/C149470707712/D198224175104 bytes、D約184.6GiB。OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。リーク不在やPC全体の変動原因は断定しない。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。
専用principal/SAM/全保護rootへのアクセス、account reset/enable/logon、特権追加/UAC/ACL変更、service/task/VM/profile追加、push/merge/CIなし。旧9 root閉鎖とj/診断の消費済みguardを継続。

**次は、結果を作る側から通常保存APIへ接続する小さな開発用経路を進める。** 保存APIの作り直しや厳密なprincipal試験を自動再開しない。同じ出力先を並列更新せず、計算結果と保存検査をつなぐ。既存formal campaign entry/科学的評価条件/受入gateは今回未変更で、正式契約への接続は通常保存の成功とは別に扱う。
local_publication_performed=true。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。

## 118. 2026-09-16 保存済み観測のローカル計算CLI・順次再計算検証成功

§116を継続し、**8f42c9e18e533e85afb5e2be0b7b5aede17dcc9f** に結果生成側と通常保存APIの接続を実装。[使い方](../anomaly-v03-local-preview.md) / [結果](anomaly-multiseed-v0.3-local-preview-2026-09-16.md)。`preview_anomaly_v03.py run/verify` が入力snapshot→既存S2計算→4 payload保存→保存済み入力から再計算照合を行う。C0/C1/C2を1候補ずつ扱い、campaign identityを作らない。重複実行名を計算前に拒否し、部分入力の不足理由をinconclusiveとして残す。

新規8件＋通常保存12件＋既存QuantizationAndCaptureTests 10件＝**30件pass**（4.406＋1.562秒）、独立P0〜P3所見0/進捗poll0、safety/diff-check pass。変更前2f5a147のscorerと、代数的14,410行で3候補すべての48 profile全ledger・40行の全score dictionary・ローカル射影が一致（32.230秒）。広い評価module回帰は再実行しない。

実演 `artifacts/local-preview-2026-09-16/results/demo-c0-01` は両設備sample0〜7204の14,410行、motor-01/sample7202のmotor_currentに15を加えた代数的入力。登録seed/データ生成器/性能評価なし。入力7664634 bytes/hashe104d67861c37870af170a3e74aed987f3ba402a04181cf80af9cf1bf252dbc0。
通常C0 run PID8720/17.546秒/exit0（UTC16:59:06〜23）、writer終了後にverify PID13064/6.467秒/exit0（UTC16:59:23〜30）。computed、48 calibrated、40 score行/利用可能32/不能8/瞬間的閾値超過2、normal-prefix issuesなし。別CLI再計算でlocal_verified=true/payloads4・集計一致。超過2を異常イベント数や性能成功と扱わない。marker hash0dd554fe9f6800dc6bd13f2abb96f1d2dac5d89c4c4b14e45c05ea5b704ddf4f。保存済み実行名は再使用しない。

選抜128 source workspace/Git blob一致（前回116不変/README変更1/新規選抜11）、前回公開8 artifact不変。選抜は完全な依存閉包ではない。input22421 bytes/hasha9a400edb41c1f8026e6ee7d3a0ccdbbc5ccd834a2a73bd50c4de93dd304a6ad。最終manifest31342 bytes/hash93afbcfbd61ab3222addda92812a6dc671fc03b2056694df72c9e244386c908d、自身除外18 artifacts/論理15394076 bytes。
終了後UTC16:59:57、RAM6084988928/C149202980864/D198223626240 bytes（D約184.6GiB）。入力上限16MiB/18000行はprocess全体のメモリ上限ではなく、長期リーク不在の確認ではない。OS26200.9445/boot2026-09-15T14:30:24.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。

**次は、CLI出力を使う小さな開発用比較・表示へ進む。** 既存decoderの固定capture時刻/設備/canonical入力条件を維持しており、任意の実設備データを直接扱えるとはしない。保存APIの作り直し・厳密なprincipal試験・広い重い評価moduleを自動再開せず、必要な対象試験を選ぶ。§116の旧root閉鎖とj/診断の消費済みguardを維持し、今回専用principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
local_publication_performed/local_preview_computed=true。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。正式campaign entry/科学的評価条件/受入gateは未変更。

## 119. 2026-09-16 保存済み候補の比較CLI・実3候補比較成功

**204e8e8e9397e3276441a682a3283ff78bf3a0a8** に `preview_anomaly_v03.py compare` を追加。[使い方](../anomaly-v03-local-preview.md#保存済み候補の比較) / [結果](anomaly-multiseed-v0.3-local-comparison-2026-09-16.md)。同一入力bytesの異なる2〜3候補をmarker hash付きで指定し、順番に再計算検証してMarkdown/JSON表示する。比較は結果ファイルを書き換えず、既存保存API・数式も変更なし。
候補別/target別件数・不足理由を表示し、判定一致/不一致は両側利用可能な行だけ。片側のみ可能・両側不能を別集計し、不能を「異常なし」に含めない。生スコアの大小や超過件数で性能順位を付けない。
新規比較7＋既存preview8＝**15件pass/6.929秒/failure・error・skip0**、独立P0〜P3所見0/進捗poll0、safety/diff-check pass。初回7件の1 errorはテスト側の引数切出しミスで修正済み。広い評価module・principal試験は追加しない。

前回C0と保存済み入力14410行/7664634 bytes/hashe104d67861c37870af170a3e74aed987f3ba402a04181cf80af9cf1bf252dbc0を再利用。新規 `artifacts/local-comparison-2026-09-16/results/c1-01`、`c2-01` を通常権限で順次作成。UTC00:05:18〜00:06:19、C1 PID31080/16.569秒、C2 PID18640/24.510秒、compare PID16436/20.037秒、全exit0。
3候補ともcomputed/48 calibrated/40 score行（可能32/不能8）。瞬間的超過C0=2/C1=1/C2=2。共通32行の判定差はC0–C1=1/C0–C2=2/C1–C2=1、両側不能8は一致件数に含めない。C2のmotor-01.vibration_featureにも超過1があり、超過総数だけでは同じ判定とはいえない。性能やイベント数の評価ではない。
比較表 `artifacts/local-comparison-2026-09-16/comparison.md` は3193 bytes/hash989ec54ad6b9b64416cbf93081fc074ddc101843abba28e1fec8fc11e5b20ec2。保存済み実行名は再使用しない。

選抜130 source workspace/Git blob一致（前回125不変/preview・guide・READMEの3変更/新規選抜2）、前回公開18 artifact不変。input22866 bytes/hashcb5e5c788162053bd1616c5129fbb9962895afab460482de5162f3800857d718。最終manifest38826 bytes/hash3ea72ca950f2aa67d161b2a03c26e566f3a1018c26f2ea6985e620adf8024487、自身除外26 artifacts/論理15437207 bytes（約14.7MiB）。選抜は完全な依存閉包ではない。
実行後UTC00:06:44 RAM12520452096/C154338992128/D197797593088 bytes、D約184.2GiB。OS26200.9445、**boot2026-09-16T08:46:30.5000000+09:00へ変化**を記録し、再起動理由は未確認。Windows Update engineering緩和/正式pin不変。容量変動原因や長期リーク不在は断定しない。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。

**次は、判定が分かれたsample/targetを具体的に追える表示を検討する。** 保存済み観測・スコアを活用し、性能順位やイベント数には読み替えない。§116の方針、旧root閉鎖とj/診断の消費済みguardを継続。保存APIや厳密なprincipal試験を作り直さず、必要な対象試験だけを選ぶ。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
local_publication_performed/local_comparison_computed=true。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。正式campaign entry/科学的評価条件/受入gateは未変更。

## 120. 2026-09-16 判定差の時点・対象別詳細表示

**47f5367b64ef41ef0ef263dbcf0a628fcbd164a0** にcompareの詳細表示を追加。[使い方](../anomaly-v03-local-preview.md#判定差の詳細) / [結果](anomaly-multiseed-v0.3-local-comparison-details-2026-09-16.md)。判定/利用可否が分かれたsample/targetごとにUTC時刻・候補別score/residual/phase/mode/recipe/除外理由を表示。既定20組/max100、details-offset、全体組数/表示数/前後省略数を追加。同じ組をペア間で重複計上せず、unavailableを陰性に含めない。全体集計と旧detailsなしJSONの描画を維持。保存API・数式変更なし。
**関連19件pass/11.572秒/failure・error・skip0**、独立P0〜P3所見0/進捗poll0、safety/diff-check pass。重複・全availability組合せ・値の一致・順序・ページ境界/非表示・上限・旧JSON・CLIを確認した。広い評価moduleやprincipal試験は実施しない。

保存済みC0/C1/C2を再利用したcompare PID25968、UTC00:42:56.153678〜00:43:10.371583、14.218秒/exit0。入力・候補payloadの新規生成0。前回比較からdetails以外の全項目不変、各詳細値・判定・理由は保存済みscores.jsonlに一致。
差は2組：sample7202/UTC02:00:02のmotor-01.vibration_featureはC2だけ閾値超過、sample7203/UTC02:00:03のmotor-01.motor_currentはC0だけ閾値超過。日付は入力の2026-01-01 UTC。全件表示/省略0、性能順位や異常イベント数の主張なし。
表 `artifacts/local-comparison-details-2026-09-16/comparison-details.md` は4653 bytes/hash7d65e23198da9fd6f9a884af3e079c6841aa738935d7dcb3e9e4f9695e5f04c4。

選抜130 source workspace/Git blob一致（125不変/5変更）、前回公開26 artifact不変。input22799 bytes/hashfd26747971d304f0bc5b0dca4db0bd2f6545e8e1519fc32d0235314db1e2db16。最終manifest26948 bytes/hashbffef1a360356453ce5ff4f1061aaecceaac2652063d8c1e922a4d44bf638b0a、自身除外8 artifacts/41857 bytes、manifest込み68805 bytes（約67KiB）。選抜は完全な依存閉包ではない。
終了後UTC00:44:16 RAM16581005312/C153473536000/D172064628736 bytes（D約160.2GiB）。開始時D173141708800との容量差をこの処理に帰属させず、長期リーク不在も断定しない。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。

**次は、差のある時点前後の保存済み観測値を併記し、入力と残差の対応を追える表示を検討する。** 既存3候補を再利用し、常駐処理や大きなデータ生成を追加しない。§116方針、旧root閉鎖・j/診断の消費済みguardを継続。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
local_comparison_computed=true、今回local publication0。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。正式campaign entry/科学的評価条件/受入gateは未変更。

## 121. 2026-09-16 判定差と保存済み観測値の対応表示

**a013ec2c4175725b091702ad9d6e0fa7804bac31** に観測contextを追加。[使い方](../anomaly-v03-local-preview.md#判定差の詳細) / [結果](anomaly-multiseed-v0.3-local-observation-context-2026-09-16.md)。各詳細の同一設備・t-1/t/t+1で4 targetの値/unit/quality/mode/recipeを表示。正確な時点の欠測は補間せずpresent=falseとし、null値と区別する。t+1は計算後の閲覧専用。最初の検証済み入力bytesだけ保持し、展開済み観測は表示対象の時点に限定、詳細0件なら解析を省く。自由文字列をMarkdownでescapeし、旧observationsなしJSONも描画可能。scorer/storage/CLI引数変更なし。
**関連22件pass/9.334秒/failure・error・skip0**、独立P0〜P3所見0/進捗poll0、safety/diff-check pass。初回22件/10.146秒の1 errorは、gapでphaseがリセットされた後にも詳細行があると仮定したfixtureの誤りで、通常phaseの統合確認と欠測表示を分けて修正した。初回をpassには数えない。

保存済み3候補を再利用したcompare PID26676、UTC01:32:17.597939〜01:32:30.144467、12.547秒/exit0。入力・候補payload新規生成0。observationsを除く前回比較/詳細の全項目不変、2組×3時点×4信号＝24セルが保存済み値・単位・品質に一致。重複除外で設備/時点4組。
sample7202/vibration_featureの130.03→130.28、差0.25とC0 residual一致。sample7203/motor_currentの115.28→100.83、差-14.450000000000003とC0 residual一致。他信号も表示するため、C2判定と同時点の電流変化を並べて確認できる。因果寄与分解・性能順位・イベント数の主張はしない。
表 `artifacts/local-observation-context-2026-09-16/comparison-observations.md` は7235 bytes/hash998a218610d2f6a69e2c6d9674927097976e122df4fb705e79a71bce91110b83。

選抜130 source workspace/Git blob一致（126不変/4変更）、前回公開8 artifact不変。input22971 bytes/hash3c627452322f07ad7b934bb7bb3242f0895e540b9e9bf46f6b5cbcf8fda348b1。最終manifest27542 bytes/hashb0ee357476fc5ee380fd5c4f27b776fc45772954d1f91615f3c4d596171b6971、自身除外8 artifacts/49617 bytes、manifest込み77159 bytes（約75KiB）。選抜は完全な依存閉包ではない。
終了後UTC01:34:12 RAM16946081792/C153028853760/D171638452224 bytes（D約159.9GiB）。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00、Windows Update engineering緩和/正式pin不変。容量変動原因や長期リーク不在は断定しない。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。

ローカルの計算・保存・比較・観測照合が一通り揃った。**次は、単一writerでの評価実行経路と、現行計画§8/9・runtime gateの差分を整理し、必要な契約判断を具体化する。** 科学的な候補式/seed/閾値/評価条件を維持し、正式未実施をpassへ置換しない。§116方針と旧root閉鎖・j/診断の消費済みguardを継続し、専用principal試験は自動再開しない。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
local_comparison_computed=true、今回local publication0。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。正式campaign entry/科学的評価条件/受入gateは未変更。
## 122. 2026-09-16 単一writer評価経路の接続案・運用改訂の判断

**7f1708a7450857517f28fe3b23dd05404088b73b** に[移行案](../anomaly-v03-single-writer-evaluation-proposal.md)とREADME案内を保存。[照合結果](anomaly-multiseed-v0.3-single-writer-route-2026-09-16.md)。現行公開runnerはruntime/受入gate後も未接続。既存計算には完全18,000行と全metadata/events・登録identityが必要で、部分previewを性能評価へ読み替えない。別clean作業コピーと、新scopeのcontroller/manifest/runtime captureが必要。

提案 `anomaly-v03-single-writer-v1` / engineering-dev は、最初のdev seed・layout 0・2層×3候補＝固定6件（2 dataset/288 profile/86400 score行）。科学的な式・seed・閾値等を維持し、保存とOS更新の扱いを運用改訂する。15分/所有worker private 2GiB/新出力1GiB、開始時空きRAM4GiB/volume20GiBを上限案とした。旧gateを解除せず、全dev/smokeやholdoutの代替にしない。
独立レビュー所見0/進捗poll0。既存CLIのvalidate-onlyはdev576/smoke144枠でexit0/configuration_valid、両方not_run/output_created=false。今回は文書のみで登録データ生成0/evaluation0。重い評価moduleやprincipal試験なし。

選抜131 source workspace/Git blob一致（前回129不変/README変更1/新提案1）、前回公開8 artifact不変。選抜は完全な依存閉包ではない。証拠 `artifacts/local-evaluation-route-2026-09-16`、manifest26953 bytes/hash4da69a1b957a701be90f9bd2ed0851f67d6641d2bac8601bcb82c823cf04e32c、manifest込み34572 bytes。UTC01:50:17の空きRAM16886415360/C153019449344/D171638751232 bytes（D約159.9GiB）。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00、Windows Update engineering緩和/正式pin不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。

**この時点の次工程は運用改訂の採択判断だった（§123で採択・初回試行完了）。** 凍結計画§9の「条件削減は新登録」に対応し、承認後は新policy/manifest validatorと固定6枠planの実装から進む。§122の時点では改訂採択や6件試行は未完了。§116の専用principal試験保留、旧root閉鎖とj/診断の消費済みguardを継続し、自動再開しない。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed。正式campaign entry/科学的評価条件/受入gateは未変更。

## 123. 2026-09-16 運用改訂採択・固定6件の計算保存と両再計算成功

提案確認後の「次に進めてください」を受け `anomaly-v03-single-writer-v1` を採択し、**0086ffe226ed58c618f6bc001ebd0c99a90e66e9** に実装。[ガイド](../anomaly-v03-engineering-evaluation.md) / [結果と概算](anomaly-multiseed-v0.3-engineering-trial-2026-09-16.md)。固定plan/manifest、Windows更新実値記録、1 worker/15分/2GiB/出力1GiB監視、全pair保存後の順次計算・公開前再計算・writer終了後readerを追加した。新規25＋通常保存12＝37件pass/7.941秒。独立P2/P3各1件是正・再レビュー0/進捗poll0。safety/diff-check pass。既存科学計画/config/schema/数式/旧gate/保存API変更なし。

同commitのclean detached worktree **C:/Users/TKent/.codex/worktrees/engineering-v03-20260916** を新設。実行と生成物はこのコピーの `artifacts/anomaly-v03-engineering-dev/trial-01` と `trial-01-control`。**同名を再使用せず、削除・cleanup対象にも自動追加しない。** 1回の実試行は最初のdev seed/layout 0/core・quality-stress/全候補の6件成功、0 inconclusive/failed/not_started。360 source Git/作業コピー一致、2 dataset/288 profile/86400 score行、payload41件。両再計算・local_verified=true。marker hash ebe96bacce7ec85bf032fc196c383efa3a5a01a09a99f0d23521e9a60b615106。
PID31828/exit0/終了確認済み、全体572.048秒、peak private337215488 bytes（321.59MiB）、出力46 files/132553275 bytes（126.41MiB）、stop_reasonなし/観測エラー0。manifestのresourcesは計算保存段階まで（189.136秒）であり、全体実測はsupervision.jsonを使う。公開後の異常では既存markerを撤回せずsupervision failedとして判定する。

概算は全dev576件で15.3時間/11.9GiB、smoke144件で3.8時間/3.0GiB、合計19.1時間/14.8GiB。1条件の線形外挿で上限保証ではなく、bootstrap/独立consumer等は含まない。6件の完了は検出性能の合格ではない。各保存済みmetricは結果書に分子/分母で記録し、この1条件だけで候補選択・閾値変更をしない。

候補側証拠 `artifacts/engineering-evaluation-2026-09-16` は6 files/54234 bytes。trial-evidence44532 bytes/hash1ca9c3a33eca0adc60a36526dcfb12c8d336542d9dc48b67ead80969fbb478a2、最終manifest1060 bytes/hasha22b4bd142a046b7833556a6c3dbe2e535df48849f2c8aa127e5ba854396cb58。前回公開3 artifacts＋manifest不変。本流889cfc3/clean、既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。
UTC02:24:22の空きRAM17062436864/C152602251264/D171823501312 bytes（D約160.0GiB）、OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00。Windows Update engineering緩和/正式pin不変。長期リーク不在は未評価。

**次は、保存済み6件を使う独立consumerの検査項目と、全dev/smokeへ拡張する固定inventory・中断時進行記録を設計する。** 現CLIの対象・上限をその場で拡大せず、新scope受入/consumer revision/runtime inventoryを整備してから長時間実行へ進む。今回の完了だけでholdoutを開かない。§116の専用principal試験保留、旧root閉鎖とj/診断の消費済みguardを継続し、自動再開しない。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
engineering_trial_completed=true。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。

## 124. 2026-09-16 保存済み6件の独立ledger検算成功・checkpoint設計

**0c8377d0d55fc2813f2c18fa618c33646bc6666c** に保存scoreからepisode/matching/metricsを別実装で再構成するconsumerを追加。[範囲・使い方・進行記録設計](../anomaly-v03-independent-audit-and-checkpoints.md) / [結果](anomaly-multiseed-v0.3-independent-ledger-audit-2026-09-16.md)。数式側はstdlibのみ。JSON/schema・登録event・保存hash・source検査は共用する。18件pass/1.516秒、計算・設計の独立レビュー各0/進捗poll0、safety/diff-check pass。

新clean detached worktree **C:/Users/TKent/.codex/worktrees/engineering-audit-20260916** / 0c8377dから、既存producer **C:/Users/TKent/.codex/worktrees/engineering-v03-20260916** / 0086ffeのtrial-01を読取り。producer360/consumer365 sourceを個別に固定revisionへ照合した。全6件の保存score計86400行から再構成し、全source/equipment episode・incident・metrics一致。source episode件数はcore C0/C1/C2=3/30/42、stress=3/29/39。equipment episode=3/20/20、3/19/19。incidentは各20行で、候補間共有イベントを独立母数として3倍にしない。
PID30824、UTC04:18:09.387366〜04:19:42.422194、92.828秒/peak private186466304 bytes（177.83MiB）/exit0/終了確認済み。CLI内の資源検査は終了時なので、今回の所有processへ別監視helperで10分/1GiB/ログ8MiB上限を付与。stop_reasonなし/観測エラー0。入力46 filesの実行前後pin一致、登録dataset生成0、producer score再計算0。

**独立性の範囲は保存score以降。** availabilityは保存されたavailableの集計検算。正常生成・丸め・profile fit/calibration・残差/score導出・bootstrap・性能gate・全campaignは未検算。score_derivation_verified=false/independent_s6_complete=falseを明示し、完全S6受入と扱わない。
全dev/smokeのmetadata予定表はdev96 chunks/576 evaluations、smoke24 chunks/144 evaluations、合計120/720で順序・件数・一意性を確認。state=design_only/execution_authorized=false、全not_started、producer/consumer not_frozen。1 chunk=同一seed/layoutの2層×全候補。完了済みchunkを不変journalと各hashで確定し、markerのみや途中失敗を完了扱いせず、新attemptを関連付ける設計。全範囲のcontroller実装/実行はまだない。

候補側証拠 `artifacts/independent-ledger-audit-2026-09-16` は9 files/231008 bytes。audit136370 bytes/hashe61d7d14ac6739db8d648901d2fbdeda9bdae44b922db1da852e05146bd0f021、最終manifest2479 bytes/hash99cc2f94a5e3adfafd671e2e7e9b30dddf0bf1ad005c339fbac20c7578f3e96e。前回公開5 artifacts＋manifest不変。本流889cfc3/clean、producer/consumer clean。既存親policy結果書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。§120/122/123/121の並びを本文bytes不変で§120/121/122/123へ訂正後、本節を追加した。
UTC04:20:34、空きRAM16154693632/C151848161280/D171825594368 bytes（D約160.0GiB）。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00、Windows Update engineering緩和/正式pin不変。長期リーク不在は未評価。

**次はデータ生成なしで、固定campaign plan/validatorとjournalから状態を復元する処理を実装する。** 独立consumerのprofile/score導出・runtime inventoryは受入残件として維持。全dev/smokeの予算・source/consumer freezeを整える前に長時間実行やholdoutを開始しない。§116の専用principal試験保留、旧root閉鎖とj/診断の消費済みguardを継続し、自動再開しない。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
independent_ledger_audit_completed=true。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。

## 125. 2026-09-16 固定campaign planとjournal状態復元を実装

**9c9975294fe4c22c1cc8dbffbcc140cf00c687e1** にmetadata-onlyのplan builder/validator、hash-linked journal reader/reducerを追加。[使い方](../anomaly-v03-independent-audit-and-checkpoints.md#実装済みのmetadata-cli) / [結果](anomaly-multiseed-v0.3-checkpoint-metadata-2026-09-16.md)。dev96 chunks/576 evaluations→smoke24/144の固定120/720。planのsource参照revision・runtime方針・identity/order/hashを検査し、予算未確定/実行未許可を維持する。

外部plan hash・record件数・head hashを必須にし、欠落/重複/順序違反/途中JSON/source差分/markerだけの偽完了を拒否。失敗・中断後は新attempt、integrity失敗後は停止。失敗時の監視hash/context/理由を復元結果にも残す。120 chunksがverifiedと宣言されても、成果物はまだ照合せずevidence_revalidated/resume_authorized/campaign_completed/independent_s6_complete=false。全範囲のwriter/controllerを実行できる状態ではない。

初回19件pass/1.530秒。独立P2指摘1件（公開前失敗のmarkerなしsupervision pinを拒否）を修正し、最終**21件pass/1.993秒/failure・error・skip0**、再レビュー0/進捗poll0。safety/diff-check pass。小規模CLI実演はplan PID22784/0.224秒/peak private19853312 bytes、inspect PID8076/0.310秒/21057536 bytes、両exit0/終了確認。各60秒/256MiB/出力2MiB監視で停止理由なし。架空hashのfixture4 recordsから失敗attempt1と保存済み検証待ちattempt2を復元、旧監視hash保持、not_started119。登録dataset生成0/evaluation0。

証拠 `artifacts/checkpoint-metadata-2026-09-16` の実演11 files/308504 bytes（最終manifest除く）。demo-evidence SHA256 e551aa7751d8edcd2cda0efc16c0c649f95f69040039b1ce6cdf220484dea3d2。実演入力6 filesと前回証拠9 files不変。本流889cfc3・producer0086ffe・consumer0c8377dはclean。既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621の未commit変更を保全・commit除外。
UTC04:46:36空きRAM15625842688/C151835779072/D171825303552 bytes（D約160.0GiB）。OS26200.9445/boot2026-09-16T08:46:30.5000000+09:00。Windows Update engineering緩和/正式pin不変、長期リーク不在は未評価。

**次は保存済み6件を読取り専用で参照し、journal宣言と実ファイルのhash/来歴/監視/検算を結び付ける証拠照合を接続する。** 旧trialを新campaign coverageへ流用しない。追記writer/controller、profile/score導出の独立検算、runtime inventory、予算とsource/consumer freezeは残件。全dev/smokeやholdout実行を自動開始しない。§116の専用principal追加試験保留、旧root閉鎖・j/診断消費済みguardを継続。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
checkpoint_metadata_implemented=true。native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。

## 126. 2026-09-16 参照journalと保存済み6件の実証拠照合に成功

**6b77db9bf603aceb09f73a72241a57992c64716d** に `checkpoint_anomaly_v03.py preflight-trial` を追加。[使い方](../anomaly-v03-independent-audit-and-checkpoints.md#保存済み6件とのpreflight証拠照合) / [結果](anomaly-multiseed-v0.3-checkpoint-evidence-binding-2026-09-16.md)。外部reference hashから固定plan/3-record参照journal、旧trialのmarker/supervision/audit/audit-monitorを結び付け、6件ledgerを再検算して保存auditと照合する。旧consumerと新verifierを個別に固定し、長い読取りの後にjournal/reference/証拠を再読取りする。

新規12＋既存checkpoint21＋saved-audit6＝**39件pass/5.393秒/failure・error・skip0**。初回33件/7.166秒の1 failureはfixtureの比較元/先object共有によるテスト不備で、独立copyへ修正後pass。独立P0〜P3所見0/進捗poll0、safety/diff-check pass。広い重い評価moduleは実行していない。
新clean detached worktree **C:/Users/TKent/.codex/worktrees/engineering-binding-20260916** / 6b77db9から、既存producer0086ffe/旧consumer0c8377d/trial-01と保存auditを読取り。PID16484、UTC10:45:38.194649〜10:47:34.778884、116.420秒/peak private195002368 bytes（185.97MiB）/exit0/終了確認。所有processを10分/1GiB/ログ8MiBで監視し、停止理由なし・観測エラー0。binding.resourcesの96.628秒は既存audit部分で、全体はbinding-process.jsonを参照する。

参照/旧audit7 files、既存trial46 files、前回証拠12 filesは不変。登録dataset生成0/producer score計算0/保存ledger再検算6件。証拠 `artifacts/checkpoint-evidence-binding-2026-09-16` は9 files/383006 bytes（最終manifest除く）。binding3449 bytes/hash5e680d45ed08cf645169372e193d66d5d744dd26cf38091b132b61567f0cd8d1、reference hasha2ccef6286fc8e4343957278c978a9851115a3679a8ce920716a26b017491f86。
終了後空きRAM14151684096/C152356487168/D169743474688 bytes（D約158.1GiB）。3 runtimeはOS26200.9445、開始時boot2026-09-16T08:46:30.5000000+09:00。Windows Update engineering緩和/正式pin不変、長期リーク不在未評価。本流889cfc3とproducer/旧consumer/verifierはclean。既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。

**これは旧trial専用のpreflight。** 参照journalは今回の宣言であり、新campaignの実行履歴として採用しない。preflight_evidence_revalidated=true、campaign_evaluations_credited=0、campaign_attempt_roots_verified/resume_authorized/campaign_completed/independent_s6_complete/score_derivation_verified=false。
**次はplan/journalを上書きせず追記するwriterと、新campaignのattempt保存先・終了監視・検算出力の契約を整える。** まずmetadata fixtureで中断/再開を確認。profile/score導出の独立検算、runtime inventory、予算・source/consumer freezeは残件で、全dev/smokeやholdout実行は自動開始しない。§116の専用principal試験保留、旧root閉鎖・j/診断消費済みguardを維持。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。

## 127. 2026-09-16 metadataの追記保存とreceipt回復を実装

**d8ceed423e9ccd36540e88aa2bf559351366ad2e** にmetadata専用store APIと `store-init/append/inspect/recover-init/recover-append` を追加。[使い方と次の契約案](../anomaly-v03-independent-audit-and-checkpoints.md#metadataを上書きせず保存追記する) / [結果](anomaly-multiseed-v0.3-checkpoint-store-2026-09-16.md)。通常単一writer、既存exclusive/flush/読戻し/no-replace renameを再利用し、旧recordを上書きしない。外部receipt/intent pinsを必須にし、全prefix・次状態・上限を検査後に1件を確定。確定後のreceipt喪失は旧prefix＋厳密1件を読取り回復する。partial pending/初期化失敗は残して拒否し、自動cleanupや自動公開を行わない。

新規store16＋既存checkpoint21＋evidence12＝**49件pass/11.620秒/failure・error・skip0**、独立P0〜P3所見0/進捗poll0、safety/diff-check pass。reader共通化の回帰、中断/flush/rename境界・二重追記・余分な末尾・誤intent/receipt・上限を小規模fixtureで確認。専用principal/同時writerの追加試験なし。
実CLIは候補のcommit済み実装から `artifacts/checkpoint-store-2026-09-16/store-demo` を新設。新worktreeなし、metadata fixture4 recordsだけ。9 process合計3.004秒、1回0.208〜0.412秒、peak private21671936 bytes（20.67MiB）、通常8回exit0/二重追記拒否1回expected exit2。各60秒/256MiB/ログ2MiB監視で全終了確認・停止理由なし。receipt回復/二重追記拒否時はstore bytes不変、各追記でも既存prefix不変。最終attempts2/interrupted履歴1/saved_pending_verification1/not_started119。markerは架空値で、実評価完了の主張ではない。

証拠30 files/576625 bytes（最終manifest除く）、demo-evidence4035 bytes/hash27b73abe6731633482722841300b3dc23c4dca16405c5ff261101fced87633c5。前回証拠10 files不変。登録dataset生成0/evaluation0/ledger再検算0。本流889cfc3/clean、既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。
UTC12:37:26空きRAM14465695744/C151697453056/D169742598144 bytes（D約158.1GiB）。OS26200.9445、開始時boot2026-09-16T08:46:30.5000000+09:00。Windows Update engineering緩和/正式pin維持、長期リーク不在未評価。

**次は新campaignのattempt descriptorと固定path/hashのvalidatorをmetadata fixtureで実装する。** 案は固定chunks/attempt基点のresult・producer-control・auditを別formatで束ね、metadata専用storeに混在させない。まだattempt/監視process/controllerを起動しない。予算・source/consumer freeze・runtime inventory・profile/score導出独立検算は残件で、全dev/smoke/holdoutを自動開始しない。§116の専用principal試験保留、旧root閉鎖・j消費済みguardを維持。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
checkpoint_metadata_writer_implemented=true。execution_authorized/resume_authorized/campaign_completed/native_launch_authorized/isolation_certified/protected_commit_allowed/future_immutability_proven/formal_permission/execution_authenticated/native_publication_performed/raw_consumer_payload_release_enabled=false、acceptance_status=not_completed、performance_status=not_evaluated。

## 128. 2026-09-17 attempt保存先と証拠metadataのvalidatorを実装

**92772268ce968d9a4c74cb5d1811fddffb709c83** にpure descriptor builder/validatorと `attempt-layout/attempt-validate` CLIを追加。[使い方](../anomaly-v03-independent-audit-and-checkpoints.md#attemptの保存先と証拠metadataを検査する) / [結果](anomaly-multiseed-v0.3-attempt-descriptor-2026-09-17.md)。外部plan/head hashと件数から最後のrecordを選び、固定chunk/attempt path、6件identity、source/runtime/outcome、marker/producer監視/audit/その監視の宣言を結び付ける。descriptorは外部raw hash/64KiB上限で読み、journalとともに読戻し確認。3証拠hashはjournalと一致必須。verifiedには4証拠とaudit前後runtime一致を要求し、失敗時の欠落や監視のみの証拠は保持する。

新規descriptor15＋既存store16＋checkpoint21＝**52件pass/11.693秒/failure・error・skip0**、独立P0〜P3所見0/進捗poll0、safety/diff-check pass。4回の実CLIはmetadata fixtureだけで合計0.934秒/peak private22265856 bytes（21.23MiB）。正常2回exit0、別attempt path/audit監視欠落の拒否2回expected exit2。各60秒/256MiB/出力2MiB監視で全終了確認・停止理由なし。新worktreeなし、attempt directory作成0、dataset/evaluation/ledger再検算0。入力7 files不変、前回checkpoint-store証拠31 files不変。

証拠 `artifacts/attempt-descriptor-2026-09-17` は17 files/310739 bytes（最終manifest除く）。demo-evidence3087 bytes/hashd01ba9162c32f313e84e61d94ff584ea77732eceb5d587eb7011915847d22808。本流889cfc3/clean、既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。
UTC2026-09-16T16:49:40、空きRAM14423298048/C151299223552/D169709887488 bytes（D約158.1GiB）。OS26200.9445/boot2026-09-16T08:46:30.5+09:00。実演前後runtime一致。Windows Update engineering緩和/正式pin維持、長期リーク不在未評価。

**次は固定pathにある実ファイルの読取りとhash/サイズ照合を実装し、descriptor・保存済み結果・終了監視・検算本文を結び付ける。** 既存reader/auditを再利用し、小規模fixtureで確認する。今回の宣言validatorはdescriptor実配置・directory topology・証拠本文・clean sourceをまだ検証しない。controller、予算・source/consumer freeze、runtime inventory、profile/score導出独立検算は残件。全dev/smoke/holdoutを自動開始しない。§116の専用principal試験保留、旧root閉鎖・j消費済みguardを維持。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
attempt_descriptor_metadata_implemented=true。artifact_bytes_verified/filesystem_containment_verified/execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false、campaign_evaluations_credited=0、acceptance_status=not_completed、performance_status=not_evaluated。

## 129. 2026-09-21 attempt実ファイル読取りと先頭chunk検算を接続

**072773e181a17135a34de5c662b377281352f568** に `attempt-files/attempt-audit` を追加。[使い方](../anomaly-v03-independent-audit-and-checkpoints.md#attemptの実ファイルを読取り照合する) / [結果](anomaly-multiseed-v0.3-attempt-files-2026-09-21.md)。固定位置のdescriptorを外部hashで読み、宣言した証拠サイズ/hash・不在と、markerのpayload inventoryを照合する。reparse/通常file hardlink別名・上限超過・未記録の証拠を拒否。directory保持と処理後のcontrol/payload/journal再照合を行う。file検査のbody/numeric/source検証flagはfalseのまま。

auditはverifiedのchunk 0だけ、既存 `audit_saved` を再実行して旧preflightと共用の本文照合へ接続。producer/過去consumer/今回verifier、manifest/journal outcome、保存audit、両監視、runtimeを結び付ける。明示supervision引数はresultの兄弟producer-control/supervision.jsonだけで、旧既定位置は不変。全120へ旧6件契約を緩和しない。旧trialのコピー/再ラベル化や新campaign加算はしない。

初回47件pass/11.817秒、追加後は新規16＋descriptor15＋preflight12＋saved-audit6＝**49件pass/12.266秒/failure・error・skip0**。独立P0〜P3所見0/進捗poll0、safety/diff-check pass。audit接続の数値/source処理はmockを明示した検査。実CLIは小規模fixture4回、合計1.441秒/peak private22622208 bytes（21.57MiB）。正常1回exit0、未記録監視/変更payload/検証待ちaudit拒否3回expected exit2。各60秒/256MiB/出力2MiB監視で全終了確認・停止理由なし。入力16 files不変、前回証拠18 files不変。新worktree/登録dataset/evaluation/実演ledger再計算0。

証拠 `artifacts/attempt-files-2026-09-21` は26 files/332098 bytes（最終manifest除く）。demo-evidence4633 bytes/hashdb718e6da385f1b5a3d9019d2ca65dc1e39c9c86354b8d95e5fcf57c7f1b263c。本流889cfc3/clean、既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。
UTC2026-09-21T09:34:30、空きRAM13215277056/C170894483456/D119515004928 bytes（D約111.3GiB）。前回以降boot2026-09-19T03:46:06.5+09:00/OS26200.9457へ変化を記録。Python3.14.0と実行file hashは不変、今回実演前後runtime一致。Windows Update engineering緩和/正式pin維持、長期リーク不在未評価。

**次は登録inventoryの1 chunkを引数として扱う新scopeの結果契約を整え、旧6件用契約を変更せずreader/consumerを全120 chunksへ接続する。** 対象・source/runtime・6 slot・結果/監視の対応を小規模fixtureで検証し、実行側の接続へ進む。controller、予算・source/consumer freeze、runtime inventory、profile/score導出独立検算は残件。新配置の実6件と全dev/smoke/holdoutは未実施。§116の専用principal試験保留、旧root閉鎖・j消費済みguardを維持。今回principal/SAM/保護rootアクセス、UAC/ACL変更、service/task追加、push/merge/CIなし。
attempt_file_reader_implemented=true。実演artifact_bytes_verified/payload_inventory_verified=true、実演evidence_body_bindings_verified/saved_ledgers_revalidated/source_checkouts_verified=false。execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false、campaign_evaluations_credited=0、acceptance_status=not_completed、performance_status=not_evaluated。

## 130. 2026-09-21 全dev/smoke区切りの結果契約とpayload検算APIを実装

**60b2bdb3d2556b280b10991a2fd1d47d4566714d** に `anomaly_v03_chunk_contract.py` を追加。[結果](anomaly-multiseed-v0.3-chunk-contract-2026-09-21.md) / [API仕様](../anomaly-v03-independent-audit-and-checkpoints.md#全120区切りの結果形式とpayload検算api)。外部campaign・chunk index・attempt番号から登録6件を選び、campaign/identity hash、producer source、runtime、dataset/slot、入力共有、順序、failure/判定保留、coverage/resourcesを固定する。新format/scopeとし、旧engineering-devの6件用public APIを変えず、新旧形式はchunk 0でも相互拒否する。

新 `audit_chunk_payloads` は保存bytesのmappingから既存独立ledger検算へ6件を渡す。planned/context、dataset/evaluation hash、identity/input/events/source、profile状態、開始/終了journal、exact inventoryを照合。IO/公開marker/source capture/consumer pin/監視/campaign journalは呼出側責務。**現行attempt-audit CLIは旧形式のchunk 0専用のまま**。profile/score導出の独立性や完全S6は追加しない。旧上限はprovisional validation capsで、campaign実行予算は未確定。

新14件pass/5.936秒。最終は新14＋旧契約10＋saved-audit6＋ledger実計算12＋attempt-files16＋preflight12＝**70件pass/failure・error・skip0**。新接続のschema/数値mockを明示し、別の小規模ledger12件は実計算。記録helper初回はrepo import path不足の6 module読込みエラーで試験本体未実行、helper修正後の最終結果と初回ログを両方保存。広い評価moduleは実行していない。独立P0〜P3所見0/進捗poll0、safety/diff-check pass。

最終PID4640/exit0、約15.981秒/peak private53411840 bytes（50.94MiB）。UTC2026-09-21T09:56:53.988620、空きRAM13260976128/C170882428928/D119514677248 bytes（D約111.3GiB、着手時と同値）。OS26200.9457/boot2026-09-19T03:46:06.5+09:00、Python3.14.0/exe・DLL hash不変、前後runtime一致。Windows Update engineering緩和/正式pin不変。長期リーク不在は未評価。

証拠は `artifacts/chunk-contract-2026-09-21`。前回attempt-files証拠27 filesをpinへ再照合し全不変、最終manifestにも記録する。本流889cfc3/clean、既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。新worktree/登録dataset/evaluation/全campaign実行0。

**次は新形式を実ファイル読取り・producer/audit終了監視・audit report・journal/descriptor照合へ接続する。** 続いてcontroller、予算・source/consumer freeze、runtime inventoryを整える。§116の専用principal保留、旧保護root参照禁止・j消費済みguardを維持。今回principal/SAM/保護root参照、UAC/ACL変更、service/task追加、push/merge/CIなし。

再開用入口を **[短い引継ぎ](../current-handoff.md)** に整理した。新しいタスクはユーザーが選んだ場合にこの文書から再開できる。研究ロードマップPhase 3の全条件実行の準備を進めたもので、Phase 2/3全体の完了数は今回増やさない。execution_authorized/resume_authorized/budgets_frozen/campaign_completed/independent_s6_complete/formal_permission=false、campaign_evaluations_credited=0、acceptance_status=not_completed、performance_status=not_evaluated。

## 131. 2026-09-21 新形式の実ファイル・終了監視・journal照合を接続

**04630e436d7b99a97005944fe7cf7b8ec4687701** に専用 `audit_anomaly_v03_chunk.py` と `checkpoint_anomaly_v03.py attempt-chunk-audit` を追加。[結果](anomaly-multiseed-v0.3-chunk-audit-2026-09-21.md) / [CLI仕様](../anomaly-v03-independent-audit-and-checkpoints.md#新形式の区切りを実ファイルから検算する)。外部plan/hash/chunk/attemptから新形式の保存6件を選び、固定位置・公開hash/inventory・source・producer監視・保存audit・新検算・audit監視・journal outcomeを結合する。全120区切りに対応し、旧attempt-auditは旧形式chunk 0専用を維持する。

producer監視はmanifestと同じbindingとruntime_after、audit監視は保存report出力hash/サイズ・正常終了・600秒/1GiB/8MiB上限と実測・専用CLI exact argv・runtime_before/afterが必須。過去consumerと今回verifierはsource/runtimeを別々に固定する。終了前にcontrol/payload/source/plan/journalを再照合。新status=attempt_chunk_ledgers_verified、evaluations_checked=6。profile/score導出の独立性は追加しない。監視process起動と実行controllerはまだない。

初回新12件pass/56.731秒。単独readerへの既存入力上限適用と拒否テストを補足し、最終は新13＋chunk契約14＋saved-audit6＋attempt-files16＋preflight12＝**61件pass/failure・error・skip0**。独立P0〜P3所見0/進捗poll0、入力上限追加1行は親側で確認、safety/diff-check pass。小規模な実ファイルを公開・読取りし、source/runtime/schema/数値処理は明示mock。CLI入口はテスト内呼出しで確認し、別processの実データ実演は繰り返していない。広い数値module、登録dataset/evaluation生成、全campaign実行、新worktreeなし。

最終PID30140/exit0、80.642秒/peak private60731392 bytes（57.92MiB）。UTC2026-09-21T10:21:18.662914、空きRAM13440172032/C170884177920/D119514456064 bytes（D約111.3GiB、着手時と同値）。OS26200.9457/boot2026-09-19T03:46:06.5+09:00、CPython3.14.0/exe・DLL hash不変、試験前後runtime一致。Windows Update engineering緩和/旧正式pin不変。長期リーク不在は未評価。

証拠は `artifacts/chunk-audit-2026-09-21`。前回chunk-contract証拠7 filesは全pin一致。本流889cfc3/clean、既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621保全・commit除外。§116の専用principal保留・旧保護root参照禁止・j/診断guard消費済みを維持。principal/SAM/保護root参照、UAC/ACL変更、service/task追加、push/merge/CIなし。

**次はproducer→保存→独立audit→監視→journal確定を結ぶ単一writer controllerと失敗attempt保持を実装する。** まず小規模fixtureで確認し、予算/source/consumer freeze・runtime inventoryを整えてから実データ実行を判断する。[短い引継ぎ](../current-handoff.md)をこの工程へ更新した。研究ロードマップPhase 3の全条件実行に向けた読取り側接続が完了した段階で、Phase 2/3全体の完了ではない。budgets_frozen/execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false、campaign_evaluations_credited=0、acceptance_status=not_completed、performance_status=not_evaluated。

## 132. 2026-09-21 producer・実行管理・所有process監視を連続実装

ユーザーの連続自走依頼に基づき、producerを **8a38a134653d237c2cdbffdd1d6dbf59caa6f3e6**、controller/監視を **bc5f18bb3347fe5f14e60b5381c98d63d5fa6072** へ保存した。[詳細結果](anomaly-multiseed-v0.3-attempt-controller-2026-09-21.md) / [API仕様](../anomaly-v03-independent-audit-and-checkpoints.md#producer単一writer-controller所有process監視)。既存逐次producerと公開前再計算を新chunk契約へ適用し、旧固定6件の入口は維持する。

controllerは新attempt確保→running→producer保存→saved_pending_verification→audit→fresh照合→verifiedの順で処理する。遷移ごとに排他的intent/descriptor/receiptを残し、失敗attemptを上書きしない。外部保持のverified descriptor mapを必須とし、再起動後に証拠を再照合する。同じsessionでは検証済み区切りの再計算を省く。確定後のreceipt喪失は外部intent hashを使う読取り回復のみ。未確定intentは保持して止める。

所有Windows子process 1個の時間/private bytes/stdout・stderr合計を監視し、停止・終了確認・最終観測・handle解放を行う。終了不明時はログを読まず元のprocessを例外に保持する。終了済みログの読取りも有界。controllerは同期callbackを受け取るcoreで、worker/audit CLIとのadapterはまだない。子孫processの管理は対象外。

producer/旧engineering **31件pass/20.300秒**、controller/store/監視の最終 **41件pass/47.925秒/failure・error・skip0**、safety/diff-check pass。小規模実ファイルIOと明示source/runtime/schema/数値mockを使用。実processはprintだけの子1個。独立レビューで一次例外保持・cleanup中断・ログ上限・Linux discoveryを修正し、再レビュー残存0/進捗poll0。登録dataset/全campaign/広い数値試験は未実行。

最終PID17900/exit0、peak private57409536 bytes（54.75MiB）。UTC2026-09-21T11:21:01.302150+00:00、空きRAM13312098304/C174401413120/D119514165248 bytes（D約111.3GiB）。OS26200.9457/CPython3.14.0とexe・DLL hash、試験前後runtime一致。boot既存観測2026-09-19T03:46:06.5+09:00、Windows Update engineering緩和・旧正式pin不変。短時間観測で長期リーク不在は未評価。

証拠は `artifacts/attempt-controller-2026-09-21`。前回chunk-auditのmanifest＋4証拠を保持・照合する。本流889cfc3/clean、既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は保持・commit除外。§116の専用principal保留・保護root参照禁止・j/診断guard消費済みを維持。principal/SAM/保護root参照、UAC/ACL変更、service/task追加、push/merge/CIなし。

**次はproducer worker/独立audit CLIを監視/controllerへ接続するadapter。** 専用監視format/binding/limits、全体予算/source/consumer freeze/runtime inventoryを整えてから実データ実行を判断する。[短い引継ぎ](../current-handoff.md)を更新。今回の3 componentはPhase 3全条件実行の準備で、Phase 2/3全体の完了追加ではない。budgets_frozen/execution_authorized/resume_authorized/campaign_completed/independent_s6_complete/formal_permission=false、campaign_evaluations_credited=0。

## 133. 2026-09-21 native接続と新しい実6評価を完走

ユーザーからこのPCで他作業なし・大きめ作業OKの許可を受領。native callbacks/接続試行CLIを **8b343873e052103fb78fd304551eba09c8015bfc**、実試行で判明したpath長の事前検査を **25d1084ecf8f24f17fe6f8f5b253c317bc80daa7** へ保存した。[結果と実測](anomaly-multiseed-v0.3-chunk-execution-2026-09-21.md) / [実行方法](../anomaly-v03-independent-audit-and-checkpoints.md#新しい6評価を別processの監査まで通す)。

producer worker→保存確定→別processのledger audit→controllerのfresh照合→journal確定を接続し、各監視を対象/argv/source/runtimeと結合した。外部receiptを3遷移それぞれ保存する。未終了workerは元ownerを保持し、失敗・再試行可能なjournalへ進めない。監視記録や診断出力が書けない場合も元の停止理由・ownerを失わない。controller内fresh検算の資源検査は開始/終了時で、全controllerの強制停止予算は未整備。

関連42件pass/77.920秒/peak private67751936 bytes、path修正後13件pass/22.771秒。独立指摘解消後0/進捗poll0、safety/diff-check pass。初回新10件のfixture PIDとResourceStop誤分類、レビューでの一次停止保持を修正した。小規模mock試験と下記のmockなし実計算は分けて記録する。

初回clean root `C:/Users/TKent/.codex/worktrees/engineering-chunk-20260921/banto-ai` / 8b34387では、6件目quality-stress/C2の261文字pathがFileNotFoundErrorとなった。producer PID17252/exit2/終了確認、258.007秒/249008128 bytes、5 success/1 failed。running→failed、完了印なし、54 files/107889570 bytesを保持。OS設定や共通IOを変えず、登録stage/payload pathが248 UTF-16文字未満か計算前に確認する修正を追加した。

短いclean root **`C:/Users/TKent/.codex/worktrees/v03/banto-ai`** / 25d1084で、同じ登録6枠を新たに生成した。`artifacts/anomaly-v03-chunk-trials/trial-01` は **connection_trial_verified/exit0/6 success・0 failed・inconclusive・not_started**。source390 files、payload41 files、全体68 files/133323148 bytes。journalはrunning→saved_pending_verification→verified_complete、外部receipt3件。最終descriptor hash **3aa4f1a0511f3671afa093145c34f01c17435781771ede4963d53e8a76b5b8ca**。旧失敗出力の再使用なし。

全体1008.679秒（16分49秒）。producer PID15676/666.089秒/peak341819392 bytes（326.0MiB）、audit PID23244/91.316秒/189100032 bytes（180.34MiB）、controller peak221065216 bytes（210.82MiB）。両worker正常終了・停止理由なし・観測エラー空。Gitの同期読取りsubprocessを含むtree全体のメモリ値ではない。終了後にdocstringの説明だけを修正し、実行sourceは25d1084として保持する。

UTC2026-09-21T12:32:07.339235+00:00、空きRAM13116989440/C174142107648/D119513669632 bytes（D約111.3GiB）。OS26200.9457/CPython3.14.0/exe・DLL hashと試行前後runtime一致。Windows Update engineering緩和・正式pin不変、長期リーク不在は未評価。

証拠は候補の `artifacts/chunk-execution-2026-09-21`。実試行の終了後は数値再計算を繰り返さず、journal/descriptor/receiptと成功68 files・失敗54 filesをpinした。前回attempt-controller証拠と本流889cfc3/clean、既存親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。保護root参照、principal/SAM、UAC/ACL変更、service/task追加、push/merge/CIなし。

**次は全dev/smokeの予算・source/consumer・完全runtime inventoryと、複数区切りの継続入口。** 初期callback setup後935.916秒の120倍は約31.2時間、保存量は約14.9GiB。初期source照合も毎回含む単純換算は約33.6時間。seed/layout差・再試行・余裕・bootstrap等を含む保証ではない。今回の接続試行を全campaignのcoverageへ読み替えない。profile/score導出等の独立検算、全dev/smoke/holdout、性能評価は残件。Phase 2/3全体の完了は追加せず、campaign_evaluations_credited=0、formal_permission/independent_s6_complete=falseを維持する。

## 134. 全体予算候補と閉鎖記録からの逐次継続（2026-09-21）

実装保存点 **eee93cfa8162e3e161f3b22cf1644a79b02b5a52**。[結果記録](anomaly-multiseed-v0.3-budgeted-run-2026-09-21.md)。`anomaly_v03_budgeted_run.py` に新規metadata準備と閉鎖記録からの継続APIを追加した。外部request/closed hash、receipt、全verified descriptor pinsと累積活動時間を引き継ぐ。呼出しごとに新しいcontrol番号を確保し、区間単位で進む。未終了worker・未確定transitionはclosed記録を作らず、元のprocess owner/例外を返す。旧trialや未閉鎖呼出しを自動再使用しない。

48時間/32GiBを全体予算候補として別requestに記録する。残り2460秒/1GiB＋32MiBの開始余裕、controller private2GiB、空きRAM4GiB/disk20GiBを境界で検査する。累積時間は各run呼出しの活動時間で、準備・休止・最終closed書込みを含まない。全体の強制上限やprocess tree監視ではない。再開時の過去verified証拠の一連の再照合にはwrapperの途中予算検査が入らない。所有producer/auditの既存監視は維持する。

初回15件pass/76.956秒。独立P2指摘1件（最終chunk/最終inventoryの時間超過表示）を修正し、**最終17件pass/78.522秒/peak66396160 bytes**。再レビュー残存0/進捗poll0、safety/diff-check pass。小規模実IOでnative/source/runtime/数値/時計のmockを明示し、新規実データworkerや全120区間は起動していない。初回証拠driverのimport path不足によるloader errorは修正し、失敗記録も保持する。

UTC2026-09-21T12:57:49.595269+00:00、空きRAM13260709888/C174123429888/D119513456640 bytes、試験process終了済み。Windows26200.9457/CPython3.14.0/exe・DLL hashは前回同値、runtime前後一致。Windows Update engineering緩和を維持する。

次は全体source/consumerと完全runtime inventory、予算確定の材料、元worker ownerの保持を含むlauncher接続。全体起動・正式gate・S6・Phase 2/3完了を追加しない。証拠は `artifacts/budgeted-run-2026-09-21/savepoint-evidence.json`。前回chunk-executionのmanifestと18ファイル、本流889cfc3/clean、既存dirty8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持する。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。

## 135. 実行環境snapshotと明示起動CLI（2026-09-21）

実装保存点 **c01d1c978f78bab51391392d56cdcb7aab5afaab**。[結果と操作](anomaly-multiseed-v0.3-campaign-launcher-2026-09-21.md)。engineeringのWindows実値でsource/stdlib/native/extension/CPU/起動条件を収集・再読する別snapshotと、`run_anomaly_v03_campaign.py prepare/continue`を追加した。旧正式collector/schema/pinは不変。snapshotはinspection processの時点観測で、worker/auditorのruntime closureや完全S6ではない。

prepareは新しいrootに所有inspection worker（300秒/512MiB/log16MiB）と固定plan/空journal/初期closed記録を作り、外部prepared/state pinを返す。continueは同じsource/consumer/controller revision、外部pin、明示max-chunksを必須にし、活動時間内でfresh inspection後にNativeCallbacksへ接続する。未終了owner保持を共通helperにし、旧trial CLIも動作を維持した。全120の自動起動、予算の最終freeze、正式受入の許可は追加しない。

17件pass/6.691秒/peak42209280 bytes、独立P0〜P2指摘0/進捗poll0、safety/diff-check pass。小規模実IOでOS/source/native/数値mockを明示し、初期のtuple比較、API参照とfixtureの不一致は修正した。実prepareはclean **`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`** / c01d1c9 の **`artifacts/v03-runs/r1`** で成功。全体67.650秒、inspection PID6136/60.791秒/peak39006208 bytes、正常終了確認。source397/stdlib2559（51017552 bytes）/native48/extension8を収集・再読。出力7 files/749075 bytes、journal0/next0/ready、実データ計算は未開始。

prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7**、初期`run/control/000000/closed.json` raw hash **85a6163034c5392ce1ef78f4cbaa6da0faf9c06a66faae03c8c0f8df0c8ebf39**。外部stdoutからopen_runで再照合済み。次はこのr1で3区間/18評価のengineering連続運転とclosed記録を確認する。prepareを同じrootで再実行せず、latest pinからcontinueする。

UTC2026-09-21T13:18:09.894216+00:00、空きRAM13306019840/C174107738112/D119513100288 bytes。OS26200.9457/CPython3.14.0/exe・DLL hashは前回同値、前後runtime一致、全所有process終了済み。Windows Updateのengineering実値記録を維持する。既存dirty8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621と本流889cfc3/clean、過去trialは保持。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。証拠は候補`artifacts/campaign-launcher-2026-09-21/savepoint-evidence.json`。Phase 2/3、全120実行、完全runtime inventory/独立S6の完了は追加しない。

## 136. 3区間・18評価の連続運転と閉鎖記録（2026-09-21）

ユーザー了承に基づき、clean **`C:/Users/TKent/.codex/worktrees/v03p/banto-ai`** / **c01d1c978f78bab51391392d56cdcb7aab5afaab** の`artifacts/v03-runs/r1`を実CLI `continue --max-chunks 3`で継続した。[最終結果](anomaly-multiseed-v0.3-three-chunk-run-2026-09-21.md)。登録dev seed2486912926863618161/layout0〜2の新規18評価がすべて成功。区間ごとの生成・保存・両再計算・別process ledger監査・fresh照合・journal確定まで完走し、exit0/yielded/stop_reason=null。journal9/next chunk3、全所有process終了確認済み。開始6aff0c1、中間12件3d4f91cで保存した。実装変更や追加agent、回帰試験の繰返しなし。

全体2563.527295秒（約42分43秒）、累積活動時間2563.286712秒。205 files/399625685 logical bytes（約381.1MiB）、初期7ファイルは不変。各区間のauditは`ledger_checks_passed`。終了後にclosed/request/inspection、journal/descriptor、保存auditとmarker/payload inventoryをIO/hash照合し、205ファイルを外部pinした。数値計算は繰り返していない。

prepared hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。最新closedは **`run/control/000001/closed.json`** / raw SHA-256 **bfa729b447de0ce57d32439acb65ce025e718e82e7c40ebd55dda5d316d9c2da**。次回はこのpinと同じclean c01d1c9から、明示上限を決めて残り117区間/702評価を段階的に進める。初期closedや中間receiptを再使用しない。全120区間の自動起動は行わない。48時間/32GiBは境界での協調停止による候補で、再開時の過去verified照合・seed/layout差・再試行等の費用は残る。

producer最大349065216 bytes（332.9MiB）、audit最大195768320 bytes（186.7MiB）、controller peak226635776 bytes（216.1MiB）/終了時82321408 bytes（78.5MiB）。60秒間隔42標本で空きRAM最小12900720640 bytes（約12.0GiB）、観測エラーなし。区間確定後のcontroller privateは増加し続けておらず、長期リーク不在は未評価。UTC2026-09-21T14:10:40.410982+00:00、空きRAM13235781632/C173706485760/D119512846336 bytes。OS26200.9457/CPython3.14.0/exe・DLL hashは開始・終了・workerで一致、Windows Update engineering緩和を維持。

証拠は候補`artifacts/three-chunk-run-2026-09-21/savepoint-evidence.json`。前回campaign-launcher manifest5681 bytes/SHA-256 aa90c244104a2d83e444407f7f38914ac2e2d80c23587154ca3bf9d9877ab55fと記載11ファイル、本流889cfc3/clean、既存dirty8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。独立監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory、profile/score導出・bootstrapの独立検算、全dev/smoke/holdout、性能評価、Phase 2/3全体は未完了。

## 137. 完了済み3区間からの6区間継続（2026-09-22 JST）

ユーザーの継続指示に基づき、同じclean **c01d1c978f78bab51391392d56cdcb7aab5afaab** / `C:/Users/TKent/.codex/worktrees/v03p/banto-ai` のr1を`continue --max-chunks 6`で継続した。[最終結果と次回の試算](anomaly-multiseed-v0.3-six-chunk-continuation-2026-09-21.md)。chunk3〜8の新規36評価がすべて成功し、累計9区間/54評価。実時間5442.063274秒（90分42秒）、累積活動8005.085221秒。exit0/yielded/stop_reason=null、journal27/next chunk9、全所有process正常終了確認済み。開始1873c37、中間18評価追加ed28579で保存し、sequence12/15/18/21/24のreceiptも外部保持した。

最新closedは **`run/control/000002/closed.json`** / raw SHA-256 **37b94e035b4468b18ff6381e0a17ed7ca6aaedb99cccb14cfaebcb10d8597501**。prepared hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。全595 files/1196786729 logical bytesを照合し、既存205ファイルは完全一致。collectorは128.340秒のIO/hash照合のみ、数値計算の再実行なし。証拠は候補`artifacts/six-chunk-continuation-2026-09-21/savepoint-evidence.json`。前回three-chunk-run manifest4953 bytes/hashadf08b7f2f32907c45c94bf8e9656a91292137efe02f83a00f6cb0d68ff1d5aaと記載11ファイルを保全する。

producer最大333.3MiB、audit最大185.9MiB、controller peak216.6MiB/終了時77.3MiB。60秒間隔90標本の空きRAM最小約11.88GiB、診断エラーなし。UTC2026-09-21T15:55:10.529690+00:00、空きRAM13211693056/C173294256128/D119512580096 bytes。OS26200.9457/CPython3.14.0/exe・DLL hashは開始・終了・各workerで一致、Windows Update engineering緩和を維持。長期リーク不在は未評価。

残り111区間/666評価。再開時の既存3区間確認を含む起動に約9〜10分かかり、細分化した再開が全体予算に響くことが分かった。1回の再開実測による線形試算では、残りを6区間単位で進めると累積約81〜88時間、24区間単位なら約40〜42時間。**次の候補は24区間/144評価、約6時間/追加約3GiB**とし、途中保存は同じinvocation内で続ける。固定起動費、seed/layout差、inventory増加、再試行など未分離の費用があり、48時間/32GiBへの収束保証ではない。次の実行・全残区間の自動起動はしていない。

実装変更・追加agent・広い回帰試験の再実行なし、repository safety/diff-check pass。本流889cfc3/clean、既存dirty8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621は保全・commit除外。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory/独立S6、全dev/smoke/holdout、性能評価、Phase 2/3全体の完了は追加しない。

## 138. 完了済み9区間からの24区間継続（2026-09-22 JST）

同じclean **c01d1c978f78bab51391392d56cdcb7aab5afaab** / `C:/Users/TKent/.codex/worktrees/v03p/banto-ai` のr1を`continue --max-chunks 24`で継続し、chunk9〜32の新規144評価がすべて成功した。[最終結果](anomaly-multiseed-v0.3-twenty-four-chunk-continuation-2026-09-22.md)。累計33区間/198評価、exit0/yielded/stop_reason=null、journal99/next chunk33、controllerと全所有processの終了を確認済み。今回20851.249秒（約5時間48分）、累積活動28855.997764秒。開始af393cb、中間dad47ee/82e69de/55faa8dを保存し、区間ごとの外部receipt24件を保持した。

最新closedは **`run/control/000003/closed.json`** / raw SHA-256 **af04684d25c99f69e64a2ac5aacffd92be930d6325ceddd5d9a0ee254f5fa7a0**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。2137 files/4384532669 logical bytesを照合し、開始前595ファイルはすべて不変。各監査は`ledger_checks_passed`、collectorは456.468秒のIO/hash照合のみ。証拠は候補`artifacts/twenty-four-chunk-continuation-2026-09-22/savepoint-evidence.json`。前回manifest6331 bytes/hashf16e7470bac1ef637f2bb019f80ebe36ffcc7499c4c07844699d1a2a969d4754と記載20ファイルを保全。

producer最大333.3MiB、audit最大186.3MiB、controller peak218.5MiB/終了時88.5MiB。60秒間隔346標本の空きRAM最小12526116864 bytes（約11.67GiB）、診断エラーなし。終了UTC2026-09-21T23:24:06.304847+00:00（JST08:24）、空きRAM13213487104/C169208168448/D119512244224 bytes。OS26200.9457/CPython3.14.0/exe・DLL hashと各workerのruntimeは開始・終了で一致。Windows Update engineering実値記録、旧正式pin不変を維持。長期リーク不在は未評価。

残り87区間/522評価、48時間候補予算の残り活動時間143944.002236秒（約39.98時間）。次回は既存33区間の照合費用も含めて明示上限を判断する。今回の30分間隔heartbeat banto-24は最終保存後に停止し、追加invocationは起動しない。実装変更・追加agent・合格済み回帰試験の再実行なし、diff-check pass。本流889cfc3/clean、実計算c01d1c9/clean、既存dirty8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全・commit除外。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory/独立S6、全dev/smoke/holdout、性能評価、Phase 2/3全体は未完了。

## 139. 完了済み33区間からの24区間継続（2026-09-22 JST）

同じclean c01d1c9/r1の`continue --max-chunks 24`でchunk33〜56の新規144評価がすべて成功し、累計57区間/342評価となった。27346.369秒（約7時間36分）、累積活動56201.874418秒、journal171/next57/yielded。各監査は`ledger_checks_passed`、controllerと全所有process終了済み。3679 files/7572651569 logical bytesを照合し、開始前2137ファイルはすべて不変。終了後のcollectorは553.670秒のIO/hash照合のみで、数値計算は繰り返していない。 [最終結果](anomaly-multiseed-v0.3-chunks-33-56-continuation-2026-09-22.md)。開始3859efc、中間85c2f2b/41dd75d/dfb4107を保存し、外部receipt24件を保持した。

最新closedは **`run/control/000004/closed.json`** / raw SHA-256 **f21ca40084af17fc0d961c529963c984ccd80d2b0cfea7803fab30c1ce7382a6**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。旧000003以前のclosedや中間receiptは再開pinに使わない。 証拠は候補`artifacts/chunks-33-56-continuation-2026-09-22/savepoint-evidence.json`。

producer最大335.5MiB、audit最大188.3MiB、controller peak220.9MiB/終了時83.7MiB。60秒間隔454標本の空きRAM最小11128786944 bytes（約10.36GiB）、診断エラーなし。終了UTC2026-09-22T09:00:09.756724+00:00（JST18:00）、空きRAM13120614400/C165132275712/D119511928832 bytes。OS26200.9457/CPython3.14.0/exe・DLL hashと各workerのruntimeは開始・終了で一致。Windows Updateのengineering実値記録と旧正式pin不変を維持。controller privateは終了時に低下したが、長期リーク不在は未評価。

残り63区間/378評価、48時間候補予算の残り活動時間116598.125582秒（約32.39時間）。次回は完了済み57区間の再照合費用も含めて明示上限を判断する。今回のheartbeat banto-24は最終保存後に停止し、追加invocationは起動しない。 前回manifest10289 bytes/SHA-256 ddbb32983dadb84fbdca50d990f346c02cdaa5bedc8949d016504562e6d48ec8と記載48ファイルを保全。本流889cfc3/clean、実計算c01d1c9/clean、既存dirty親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。実装変更・追加agent・合格済み回帰試験の再実行なし。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。 監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory、profile/score導出・bootstrapの独立検算、全dev/smoke/holdout、性能評価、Phase 2/3全体は未完了。

## 140. 完了済み57区間からの24区間継続（2026-09-23 JST）

同じclean c01d1c9/r1の`continue --max-chunks 24`でchunk57〜80の新規144評価がすべて成功し、累計81区間/486評価となった。30205.374秒（約8時間23分）、累積活動86406.475041秒、journal243/next81/yielded。各監査は`ledger_checks_passed`、controllerと全所有process終了済み。5221 files/10761163678 logical bytesを照合し、開始前3679ファイルはすべて不変。終了後のcollectorは522.586秒のIO/hash照合のみで、数値計算は繰り返していない。 [最終結果](anomaly-multiseed-v0.3-chunks-57-80-continuation-2026-09-22.md)。開始09eb51f、中間8f23587/ba25ca0/26e0d0aを保存し、外部receipt24件を保持した。

最新closedは **`run/control/000005/closed.json`** / raw SHA-256 **a6b8fd6160b496d9a7dea83cef3ec22814c8b12676df273eb591fb5368384758**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。旧000004以前のclosedや中間receiptは再開pinに使わない。 証拠は候補`artifacts/chunks-57-80-continuation-2026-09-22/savepoint-evidence.json`。

producer最大334.3MiB、audit最大188.6MiB、controller peak225.6MiB/終了時90.2MiB。60秒間隔501標本の空きRAM最小9602994176 bytes（約8.94GiB）、診断エラーなし。終了UTC2026-09-22T18:08:59.297124+00:00（JST2026-09-23 03:08）、空きRAM11659157504/C161118416896/D119168434176 bytes。OS26200.9457/CPython3.14.0/exe・DLL hashと各workerのruntimeは開始・終了で一致。Windows Updateのengineering実値記録と旧正式pin不変を維持。controller privateは終了時に低下したが、長期リーク不在は未評価。

残り39区間/234評価、48時間候補予算の残り活動時間86393.524959秒（約24.00時間）。次回は完了済み81区間の再照合費用も含めて明示上限を判断する。今回のheartbeat banto-24は最終保存後に停止し、追加invocationは起動しない。 前回manifest10290 bytes/SHA-256 6f734135d9712a477fef2b2a88b5b234e47701737139324e7c941f8a8a21ef77と記載48ファイルを保全。本流889cfc3/clean、実計算c01d1c9/clean、既存dirty親policy文書8461 bytes/hash443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保持・commit除外。実装変更・追加agent・合格済み回帰試験の再実行なし。保護root/principal参照、UAC/ACL/service/task変更、push/merge/CIなし。 監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory、profile/score導出・bootstrapの独立検算、全dev/smoke/holdout、性能評価、Phase 2/3全体は未完了。

## 141. 区間81〜104呼出しのMemoryError停止（2026-09-23 JST）

区間81〜104を対象に起動したcontrol000006は、既存区間の再照合中とみられる段階でMemoryErrorによりexit2で終了した。新規区間の開始記録・確定は0、journal243/前回checkpointと完全一致。累計81区間/486評価、残り39区間/234評価を維持する。今回の24区間成功は追加しない。 [停止記録](anomaly-multiseed-v0.3-chunks-81-104-continuation-2026-09-23.md)。

失敗時の最新closedは **`run/control/000006/closed.json`** / raw SHA-256 **18af12a119e3acc0600594d8eaf6263607f5f7c85d68ff3acbda31931d4b9e4c**、status=failed/stop_reason=exception。直前000005は開始pinとして保持し、現在の再開pinとして使い回さない。

終了UTC2026-09-23T02:57:30.180163+00:00（JST2026-09-23 11:57）、今回11198.201秒（約3時間7分）、累積活動97603.864249秒、48時間候補の残り75196.135751秒（約20.89時間）。終了時の空きRAM7879757824/C131049820160/D116994351104 bytes、controller peak232960000/終了時private159330304 bytes。

controller PID29852の消失、診断threadの終了、inspection worker PID35784のexit0/終了確認を記録した。新規producer/auditは起動記録なし。前回manifestと記載49ファイルの計50件、既存journal243ファイルのpinを照合済み。runの名前一覧は前回5221ファイル＋今回control6ファイルの5227件で一致。既存の数値payload全体は再hashしていない。今回controlの6ファイルはfailure-controlへコピーし原本とhash一致。成功用collect.py/finalize_evidence.pyと数値計算は再実行していない。

原因は未特定。最後の診断から終了まで約26秒の間にC空き容量が161239666688→131049820160 bytesへ減ったことも記録するが、pagefile増加や他processとの因果関係は未確認。空き物理RAMだけから原因やリーク有無を断定しない。自動再起動せず、割当失敗とシステム全体のメモリ状況を切り分けてから再開条件を判断する。

次の判断点はMemoryError原因の切り分けと再開条件の見直し。今回のheartbeat banto-24はPAUSEDに変更済み。追加区間や同じinvocationを自動再起動しない。 起動21860d5、失敗保存は候補`artifacts/chunks-81-104-continuation-2026-09-23/failure-savepoint-evidence.json`。campaign加算0/正式許可false、監査は保存score以降のみ。Phase 2/3、完全runtime inventory/独立S6、全120/holdout/性能評価は未完了。実装変更・追加agent・push/merge/CI・OS/権限設定変更なし。

## 142. MemoryErrorの読取り調査（2026-09-23 JST）

[調査結果](anomaly-multiseed-v0.3-memory-error-diagnosis-2026-09-23.md)。保存185標本、停止前後のWindowsイベント、現在のpagefile/system commit、c01d1c9の再照合・例外処理を確認した。controller peak約222.17MiBは途中で頭打ちとなり、持続的増大は観測なし。OSのメモリ枯渇イベントも見つからなかったが、これだけで一時的不足を否定しない。コミット余力不足・pagefile拡張遅延は仮説で、原因は未確定。C空き容量約28.12GiBの急減がpagefileだったとは断定できない。

現在の診断は停止約7時間後。空きRAM約14.16GiB、commit約28.98/44.42GiB、C空き約144.83GiB、D空き約49.35GiB。自動pagefileの現在値や現在のprocess一覧を停止時へ逆算しない。既存コードはコミット量・上限、失敗traceback、再照合中chunkを保存していないため、次はこの記録を追加する最小限の診断と短い確認を準備する。今回の調査で数値計算・81区間再照合・追加起動・OS変更は実行していない。

証拠は別folder `artifacts/memory-error-diagnosis-2026-09-23/`、文書保存点とpinは同folder `savepoint-evidence.json`。失敗証拠は変更せず、最新closed000006と累積活動97603.864249秒/残り75196.135751秒を維持する。累計81区間/486評価、heartbeat PAUSED、実装c01d1c9、formal_permission=falseは不変。既存dirty文書は保全しcommit除外する。

## 143. 外部メモリ診断の準備と短い確認（2026-09-23 JST）

[確認結果と次回組込み手順](anomaly-multiseed-v0.3-memory-diagnostics-validation-2026-09-23.md)。固定sourceを変更せず使える外部helperを `tools/evaluator/anomaly_v03_memory_diagnostics.py` へ追加した。コミット量/上限・pagefile量、監査中chunk、例外のfile/function/lineを記録する。controllerの作り直しを含めて一時的に観測し、元の引数/結果/例外と未終了workerの所有権を維持して復元する。新しい監視threadは作らず、記録は最大16MiB、エラー/欠落を明示する。

診断12件は6.237秒で合格、既存launcher16件も合格。実Windows APIの短い確認は注入MemoryErrorを記録し、エラー/欠落0・元例外の保持・method復元を確認した。実際のメモリ枯渇や評価計算は発生させていない。実source c01d1c9からfailed closed000006を `open_run` で読む確認も1.251秒/peak約26.98MiBで成功。journal243/next81/累積活動97603.864249秒、closed原本とcontrol一覧は不変。continue/run・旧81区間の再照合・新規invocationは未実行。

UTC10:51:58（JST19:51）の空きRAM約14.25GiB/C144.77GiB/D47.95GiB、runtime pin不変。次はhelperのhash/保存commitを明示して新しいwrapperへ組み込む。既存の失敗・原因調査証拠を保全し、heartbeat PAUSED、累計81区間/486評価、formal_permission=falseを維持する。今回の証拠は `artifacts/memory-diagnostics-validation-2026-09-23/savepoint-evidence.json`。本流・実計算source・既存dirtyを保全し、push/merge/OS設定変更なし。

## 144. 診断付き区間81〜104の完走と最終照合（2026-09-24 JST）

[最終結果](anomaly-multiseed-v0.3-chunks-81-104-retry-2026-09-23.md)。診断付きcontrol000007で区間81〜104の24区間/144評価がすべて成功し、累計105区間/630評価となった。終了UTC **2026-09-23T21:17:02.345893+00:00**（JST2026-09-24 06:17）、exit0/yielded/stop_reason=null、journal315/next105。controller PID40372の消失と全所有workerの終了を確認した。今回36639.971秒（約10時間11分）、累積活動134242.935420秒（前回失敗分を含む）。

保存済み6769 files/13947570419 logical bytesを照合し、開始前5227ファイルはすべて不変。各区間の監査はledger_checks_passed。終了後のcollectorは574.907秒のIO/hash照合のみで、数値計算を繰り返していない。latest.jsonは最後の60秒標本で23件のままだが、最終run-report/stdout/closed/24件の保持receiptとjournal315で全24件の完了を照合した。

最新closedは **`run/control/000007/closed.json`** / raw SHA-256 **04f198137bbcace5176734e594e5cf3fb9a19c422a7186c002b50a78ab52035c**。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は不変。旧control000006は失敗履歴として保全し、古いclosedや中間receiptを次回の再開pinに使わない。

診断は608標本/824イベント、audit_begin/end各105件（既存81＋新規24）の順序が一致。観測エラー0/欠落0/無効化なし、例外イベントなし、診断thread終了済み。controller peak235261952 bytes（約224.4MiB）、終了時private95719424 bytes（約91.3MiB）。producer最大333.0MiB、audit最大187.3MiB。空きRAM標本最小10996932608 bytes（約10.24GiB）、commit余力標本最小10455838720 bytes（約9.74GiB）。今回MemoryErrorは再発しなかったが、前回の原因解明や長期リーク不在の証明にはしない。

終了時空きRAM14128013312/C153025306624/D441718030336 bytes。最後のrun_end診断はcommit30933463040/limit47691886592/余力16758423552 bytes。Windows26200.9457/CPython3.14.0・exe/DLL hashは開始/終了・各workerで一致。Windows Updateはengineering実値を記録し旧正式pinを維持した。OS/pagefile/Python設定変更なし。

起動9340199、中間0c98a7d/28ca9f7/1bcbcbeを保持。今回OUTのevidence.json、diagnostics-summary.json、controller-exit-check.json、24件のreceiptと最終savepoint-evidence.jsonへ保存する。旧成功/失敗/原因調査/診断検証の94保持pin、既存dirty親policy文書と本流889cfc3/cleanを保全する。今回5文書だけを更新し、追加agent・広い回帰試験・push/merge/CI・OS/権限設定変更なし。

全120区間の残りは15区間/90評価。48時間候補の残り活動時間は38557.064580秒（約10.71時間）。次回は完了済み105区間の再照合費用も含め、最新closedからの明示上限を判断する。今回のheartbeat banto-24は最終保存後に停止し、追加invocationは起動しない。

実計算source c01d1c9は不変、外部診断helper27346e9を使用。監査は保存score以降のみ、campaign加算0/正式許可false。完全runtime inventory、profile/score導出・bootstrapの独立検算、全120/holdout/性能評価、Phase 2/3全体は未完了。

## 145. 残り15区間の呼出しでMemoryError再発（2026-09-24 JST）

[停止記録](anomaly-multiseed-v0.3-chunks-105-119-continuation-2026-09-24.md)。control000008は既存区間58の保存データを再照合中、MemoryErrorでexit2となった。終了UTC **2026-09-24T00:55:23.946366+00:00**（JST **09:55:23**）。新規区間の開始・確定は0、journal315/next105とcheckpointは前回のclosed000007と同一。累計**105区間/630評価**、残り**15区間/90評価**を維持する。

今回はtracebackを保存でき、最深部は実計算sourceの `_anomaly_v03_io.py:101` / `read_regular` の `stream.read()`。呼出し元は保存datasetの読込み（`anomaly_v03_saved_audit.py:60`）。失敗したpayloadの個別path・割当要求サイズは記録されていない。既存区間0〜57の再照合を終え、58で失敗した（audit_begin59件/end58件）。例外2イベントは同じMemoryErrorが監査とcontinue_runへ伝播した記録であり、別々の2回の停止ではない。

診断は177周期標本/303イベント、観測エラー0/欠落0/無効化なし、診断thread終了済み。直前周期標本から最初の例外資源標本まで52.417秒で、system commitが30.79→57.35GiB（+26.56GiB）、pagefile確保量が12.72→29.40GiB（+16.68GiB）へ変化した。例外直後標本のcommit上限は61.10GiB、余力3.75GiB、空き物理RAM12.56GiB。標本は割当失敗そのものより後であり、失敗瞬間の余力を確定するものではない。

controllerのOS peak privateは233918464 bytes（約223.08MiB）、終了時private143798272 bytes。大きなsystem commit変動とpagefile拡張は実測したが、急増分を割り当てたprocessは診断対象に含まれていない。Bantoのメモリリークや特定の他process、pagefile拡張遅延のどれかを原因と断定しない。

今回10751.957秒（約2時間59分）、closed記録の累積活動144993.320914秒（約40.28時間）。48時間候補の残り27806.679086秒（約7.72時間）は、再開前の既存105区間再照合＋残り15区間の約9.03〜9.06時間の見積りを下回る。原因の切り分けとともに再開方法・累積予算を見直す判断が必要であり、上限変更/追加invocationを自動実施しない。

最新closedは **`run/control/000008/closed.json`** / raw SHA256 **02531b247b12b1275a57c8907924f5ac710c90c4d8dfd079f885d0fd2d5c9211**、status=failed/stop_reason=exception。prepared raw hash **be582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7** は開始時のpinを維持し、最新再開pinに旧000007や中間receiptを使い回さない。

controller PID36728の消失とdiagnostic threadの終了、inspection worker PID20240のexit0/終了確認を記録した。新規producer/audit試行は作成されていない。前回成果物154保持pinと起動時18immutable artifacts、journal315ファイルのhashを照合。既存6769ファイルの一覧・サイズは不変で、今回controlの6ファイルが増えた計6775ファイルとなった。旧数値payload全体の再hashは行っていない。control8の6ファイルをOUT/failure-controlへコピーして原本とhash照合し、元の診断/ログは保持した。成功用collect.py/finalize_evidence.py・数値再計算・追加起動は行っていない。

本流889cfc3/clean、実計算source c01d1c9/clean、候補の既存dirty親policy文書8461 bytes/SHA256443a78357625903a44e98d31cc592176a1dfed0497dfdc42a252200f8a2f3621を保全しcommit除外。Windows26200.9457/CPython3.14.0・exe/DLL hashは開始/終了で一致した。OS/pagefile/Python設定は変更していない。終了時空きRAM/C/Dは約12.55/132.50/392.11GiB。

heartbeat **banto-24はPAUSED**。失敗証拠は今回OUTのfailure-evidence.json、diagnostics-summary.json、controller-exit-check.json、automation-stop.json、最終文書commitと保全pinはfailure-savepoint-evidence.jsonに保持する。起動保存点5bcb3cfを保全。次の判断点は一時的なsystem commit急増の発生元/読込み割当経路の切り分けと、残り予算を踏まえた再開条件の見直し。

campaign加算0/正式許可falseを維持。監査は保存score以降のみ。完全runtime inventory、profile/score導出・bootstrapの独立S6、全120/holdout/性能評価、研究ロードマップPhase 2/3全体は未完了。実装変更・追加agent・回帰試験・push/merge/CI・OS/権限設定変更なし。

## 146. 既存監査のbyte照合による再利用（2026-09-24 JST）

[再開方針と検証](anomaly-multiseed-v0.3-verified-resume-2026-09-24.md)。ユーザーの再開指示と既存照合の必要性への質問を受け、外部helperで全6775ファイルの保存pin/source/runtime/checkpointを照合して既存105区間の監査cacheだけを初期化する。数値algorithm・固定計算source c01d1c9は変更せず、新しい15区間の監査は元の実装を使う。実データ13,948,054,577 bytesを65.357秒で読取検証、peak private約65.3MiB、新規13試験/既存関連45試験通過。前回成功/失敗の196artifactpinsを保全。

control000008の失敗保存点daf17f2を起点に新しいcontrol000009として105〜119だけを再開する。累積失敗時間を維持し48h/32GiBは変更しない。残り約7.72hに対し約4hの見積り。既存105再利用はresume-verification.json、新規audit_begin/endは各15件が期待値。単一writerの通常運用に限定し、正式許可/完全S6を追加しない。起動状況はcurrent-handoffと今回OUT/followup-state.jsonを優先する。

## 147. 最後の区間のproducer時間上限と119区間保全（2026-09-24 JST）

[停止・保全記録](anomaly-multiseed-v0.3-verified-resume-2026-09-24.md)。control000009は最後の区間119/attempt1のproducerが900秒（15分）の上限に達し、ResourceStop/time_limitでexit2となった。producer実測909.083秒、worker PID17908/exit1/終了確認済み。終了UTC **2026-09-24T05:46:49.451914+00:00**（JST **2026-09-24 14:46:49**）。新規14区間/84評価が確定し、累計**119区間/714評価**。残り**1区間/6評価**。journal359/next119、最終recordはfailed/resource_limit。全120区間の完了ではない。

診断は238周期標本/273イベント、audit_begin/end各14件（105〜118）、ResourceStop例外1件、観測error/drop=0、無効化なし、診断thread終了済み。今回の停止はMemoryErrorではなくproducerの時間上限。標本UTC **2026-09-24T05:44:43.907054+00:00** でsystem commit 54.90/54.96GiB、割当余力**52.73MiB**を記録した。同時刻のpagefile確保量は23.26GiB。空きRAM最小標本は3.38GiB。controller peak 0.22GiB、失敗producer peak 326.05MiB。システム全体の資源逼迫は観測したが、割当元process・時間超過への因果寄与・実際のCPU/I/O競合は未確定。メモリリークの有無を断定しない。

既存105区間は起動時の全byte/source/runtime照合（56.252秒）で監査を再利用し、新規105〜118の14区間は元の独立監査とcontroller監査を通過した。今回保全では新規14区間のdescriptor/control pin、完了markerが示すpayload raw hash、全6件success、producer/audit workerの終了を照合した。新規runファイル955件/1999730138 bytesをstreaming hashし、前回6775ファイルの一覧/サイズと旧journal315件のhashを確認。旧payload全体の再hashや数値再計算はしていない。全体は7730 files/15947784715 logical bytes。過去196artifact pinsと起動時24immutable artifactsも保持。小さなcontrol/journal/失敗worker記録98ファイルをOUT/failure-controlへ複製してhash照合した。成功用collector/finalizerは実行していない。

最新closedは **run/control/000009/closed.json** / raw SHA256 **362c2ed425d38a6a6ae3436518fa4cafa0cc4d9a017b012f15de4816fa44156d**、status=failed/stop_reason=exception。累積活動**159294.585066秒（44.25時間）**、48時間候補の残り**13505.414934秒（3.75時間）**。失敗時間を含めて保持し、48h/32GiBとworker上限は変更していない。prepared pinはbe582d48faf61a764cd0341d742af2112fd9cd0e7e9d16e979aff8770d2538c7。旧control8や中間receiptを最新closedの代わりに使わない。

次の判断は、システムの負荷が落ち着いた状態で、残り1区間だけを別の試行として再実行するか。今回の失敗attempt1は未公開stageを含めそのまま保持し、再使用・削除しない。現在の高速再開helperは「完了数×3＝journal件数」を要求するため、今回のfailed末尾2recordを含む359件をそのまま受け入れない。再開する場合は外部pinに基づく失敗末尾の扱いを検証する必要がある。無条件にcacheへ追加したり、上限引上げ・新しいinvocationを自動実施したりしない。

heartbeat banto-24はPAUSED、追加起動なし。最終保存commit/pinは今回OUT/failure-savepoint-evidence.json。

formal_permission=false/campaign加算0、保存score以降の監査という範囲を維持。完全runtime inventory・profile/score導出/全bootstrapの独立S6・全120/holdout/性能評価・研究Phase 2/3全体は未完了。実計算source c01d1c9と本流889cfc3は変更せず、既存dirty親policy文書を保全しcommit除外。OS/pagefile/Python設定変更、追加agent、回帰試験、push/merge/CIなし。

## 148. 最後の1区間だけの再試行（2026-09-24 JST）

[再試行記録](anomaly-multiseed-v0.3-final-chunk-retry-2026-09-24.md)。ユーザーの明示指示を受け、119区間/714評価と失敗attempt1を保存したまま再開した。外部helperはpin済みの失敗末尾2記録を受け入れるが、cache/成功件数に加算しない。18テスト通過。7730 filesのbyte/source/runtime確認後に既存119監査だけを再利用し、attempt2は元の独立監査/controller監査を行う。成功時journal362/全120区間720評価/next=null。

control000010をUTC 2026-09-24T08:36:21.2971453Z（JST 17:36:21、PID 35264）に非表示で起動。対象はchunk119/attempt2、最大1区間/6評価。起動前の空きRAM/C/Dは13.17/140.76/397.33GiB、system commit余力14.99GiB。実装保存点f4cda3bc5abf3e437b32037d4607564083669a18。既存Banto Pythonなしを確認して起動し、PID/作成UTC/絶対wrapperを照合した。30分heartbeat banto-24を今回1区間だけに更新してACTIVE。起動保存点はOUT/launch-savepoint.jsonに保持する。

実計算source c01d1c9、worker900秒/候補48h/32GiBは不変。失敗時間も引き継ぐ。再失敗時は保存・heartbeat停止しattempt3は起動しない。正式許可false/campaign加算0、完全S6/holdout/Phase2/3完了とは区別する。

## 149. 最後の区間の再試行成功・全120区間の照合完了（2026-09-24 JST）

[結果記録](anomaly-multiseed-v0.3-final-chunk-retry-2026-09-24.md)。control000010のchunk119/attempt2は正常終了し、最後の6評価がすべてsuccess、累計**120区間/720評価**の保存結果を照合した。status=completed/next_unverified_chunk=null、journal362件。失敗したattempt1の2記録とstageは保持した。終了UTC **2026-09-24T08:54:05.861275+00:00**（JST **2026-09-24 17:54:05**）、exit0、所要1063.882秒（約17分44秒）。

producer 558.891秒、独立audit 91.668秒、audit_status=ledger_checks_passed。controller PID35264の消失をUTC2026-09-24T09:11:55.6213023Zに確認。producer/audit/inspectionの所有workerはすべてexit0/終了確認済み。既存119区間は全7730ファイルのbyte/source/runtime一致（75.222秒）後に監査を再利用し、新規attempt2は元の監査を完了した。

終了後のcollectorは7800 files/16081676236 logical bytesをhash照合し、前回7730ファイルと過去356artifact pinsの不変、最新receipt000362/descriptor/marker/全6successを確認した。所要50.227秒。数値再計算は行わず、最終manifest作成時の全payload再hashも省く。証拠は新OUTのevidence.jsonとdiagnostics-summary.json、最終commit/pinはsavepoint-evidence.jsonに保存する。

診断は17周期標本/25イベント、新規audit_begin/end各1件、観測error/drop=0、無効化なし、診断thread終了済み。system commit余力の最小標本14.50GiB、空き物理RAMの最小標本12.62GiB。controller peak private 218.80MiB、producer peak 330.73MiB。終了時空きRAM/C/Dは13.52/140.62/402.76GiB。今回の標本は安定していたが、前回失敗の原因やリーク不在は断定しない。

最新closedはrun/control/000010/closed.json / SHA256 **a716478fa46eddcab2300de2d1f06ba6982eb94f738ca794cfc4fc931b33028a**。累積活動160357.173828秒（44.54時間）、48hまで残り12442.826172秒。失敗時間・worker900秒/48h/32GiBは維持。追加invocationは起動しない。heartbeat banto-24はPAUSEDに変更済み。今回の継続確認は停止した。

今回予定の120区間の実行と保存score以降の監査は完了。formal_permission=false/campaign加算0を維持し、完全runtime inventory・profile/score導出/全bootstrapの独立S6・正式gate/holdout/性能評価・研究Phase2/3全体の完了とは区別する。次はこの結果を根拠に研究計画の残項目を整理する判断であり、新たな評価はこのheartbeatでは開始しない。

## 150. 保存済み720評価の比較・上司向け資料（2026-09-24 JST）

[比較結果](anomaly-multiseed-v0.3-dev-smoke-comparison-2026-09-24.md)と[上司向け報告](banto-ai-anomaly-briefing-2026-09-24.md)を作成。完走保存点0e02d04を起点に、120監査reportとplan/closed/evidence等124ファイル約20.18MBをhash確認し、720 identityを照合して0.602秒で集計。raw分子/分母を合算し、dev/smoke・欠損なし/あり・seed/layout別を保持する。集計器7テスト通過、実装保存点eb3f4cc。失敗attempt1は除外し監査済みattempt2を採用。追加producer/score計算/数値監査/holdout/CIは実行していない。

両条件合算でC1は機械91.67%、センサー95.00%、警報正解率95.73%、検知済み平均delay1.26秒。C2は機械89.92%、センサー95.00%、正解率94.83%。正常区間の誤警報は両者0だが全区間の未対応警報は200/242件。C1/C2はコンベヤー停止条件、C2はモーター停止条件に追加見逃しがあり、欠損条件のsensor recallは100%→90%。3件の保存評価例のhashと失敗reasonも読んだが、全原因の断定ではない。

今回は記述統計のみ。formal_permission=false/performance_status=not_evaluated/promotion_allowed=falseを維持。既存正式gate・閾値・対象方式は変更しない。次は停止条件/欠損重複の原因切り分けと独立score検算の具体化。Phase2/3全体、運用受入/runtime inventory、bootstrap/CI、holdoutは別の残件として整理した。heartbeat PAUSEDを維持する。今回OUT artifacts/dev-smoke-comparison-2026-09-24のsavepoint-evidence.jsonへ最終保存点を保持。

## 151. 停止中・欠損重複の見逃し原因調査（2026-09-24 JST）

[原因調査](anomaly-multiseed-v0.3-failure-analysis-2026-09-24.md)を保存し、上司向け報告を更新。前段保存点b5b9403を起点に、全10 seedsのcore停止2 layouts×C1/C2を40評価、最初のdev seedのquality-stress全12 layouts×C1/C2を24評価、合計64評価を読んだ。68入力約1.295GB、約40秒、680 incidentを確認。3,704点の残差/scoreが保存profile・依存値からの別途算出と各1e-12以内で一致し、元観測4ファイルと1,680依存セルも一致した。profile自体の独立推定は未実施。

コンベヤー停止はC1/C2各100件の速度scoreが窓全体で閾値6以下（最大3.5862/4.3225）。振動警報はあるが、正解対象の速度にonsetがないため全件miss。停止時速度ほぼ0に55%低下を加える合成条件の限界と整理した。C2モーター停止は21/100 miss、3 seedsへ6/10/5件。利用可能なoffset1/2のうち28点が閾値以下で、主に振動の補正項が電流の残差を相殺した。後続の対象onsetを拾い損ねたケースではなかった。

欠損重複のsensor missは計画§3.3の構造的上限90%に対応する。offset1..3欠損、offset4は直前qualityで利用不可となり、2点連続を作れない。最初のseedの12 layouts×2方式で最初9回検知・10回目missを確認。「原因未解明の不具合」という扱いを解消し、閾値/分母の変更・新しい長時間試験は行わない。

次は観測からphase/availability、正常profile、残差/scoreを別実装で復元するconsumerの不足分。正常生成/丸め、bootstrap/CI/gate、単一writer受入/runtime inventory/資源見積りも残る。formal_permission/promotion_allowed/independent_s6_complete=false、holdout未参照、heartbeat PAUSED。今回OUT artifacts/dev-smoke-failure-analysis-2026-09-24のsavepoint-evidence.jsonに最終保存点を残す。資源終了時の空きRAM約13.64GiB、commit余裕13.05GiB、C/D空き139.61/374.40GiB。D空きが調査中約1.21GiB減った原因は未特定。本処理の新規出力はC上約4.8MB、原本を書き換えていない。


## 152. 正常profile・score導出の独立検算器（2026-09-24 JST）

[実装・検証記録](anomaly-multiseed-v0.3-independent-score-audit-2026-09-24.md)。新規anomaly_v03_score_audit.pyはstdlibのみで保存観測からphase/availability、C0/C1/C2の正常profile、残差/scoreを復元する。producerの数値関数・契約定数を共有せず、逆行列はpivot付きGauss-Jordan。浮動小数abs/rel各1e-12、状態/ID/整数/判定と依存値はexact。保存score自身と超過フラグの矛盾も拒否。実装14e6c33985c63a649c7a89c60ccb4e8ab680d601、12テスト/21.716秒で通過。

最初のdev seedのlayout0/6×全3方式×両条件、計12保存評価の576 profiles/172800 score行を元観測から検算し一致。16入力252536767bytes、最終実装で21.48秒。初回f3c1992の数値検証26.20秒を保持し、閾値境界の検査補強後の結果をverified-finalへ分離した。新規登録seed生成・producer/controller・holdout起動は0。同じ12件の検証を24評価には加算しない。

完全でcalibratedなdev/smokeだけに対応し、判定不能/partial/holdoutは拒否。APIだけでは登録identityや入力ファイルの出所を認証せず、今回IO側で完走保存点からpinを照合した。既存監査CLI/controllerには未接続、旧720評価のaudit不変。profile/score_derivation_verified=trueは検算した対象だけ。完全S6/formal/promotion=false。次は判定不能の理由・状態と、外部pin/identity/既存ledger監査を結ぶ入口を整える。正常生成/丸め、bootstrap/CI/gate、runtime/単一writer受入も残る。

OUT artifacts/independent-score-audit-2026-09-24、最終実行はverified-final/配下、最終文書commit/pinはsavepoint-evidence.json。終了時RAM空き15.57GiB、commit余裕15.60GiB、C/D空き139.26/361.71GiB。前後観測だけでpeak/リーク証明ではない。過去artifact・既存dirty guard・本流・実計算sourceを保持する。

## 153. 判定不能profileの独立検算と保存済み監査の接続（2026-09-24）

[接続記録](anomaly-multiseed-v0.3-connected-observation-audit-2026-09-24.md)。正常prefix健全・完全なdev/smoke入力について数値的な判定不能の理由・null状態・途中までの校正sample・score利用不能を別実装で照合する。ゼロMAD/非有限演算、C2の設備・運転段階内への影響、全利用不能時のledger指標も試験。部分capture/正常prefix品質不良/holdoutは対象外。照合が通ったことと評価success/inconclusiveを別に報告する。

新CLI audit_anomaly_v03_observations.pyは外部pin付き完走savepointから1区間の最後のverified attemptだけを読む。固定計画・登録identity/event・入力pin照合後、同じ評価を独立profile/score→既存独立ledger監査へ渡す。旧controller/旧CLI/旧reportを変更しない。旧publication/source/runtime/supervisionの検査は保存点を前提とする。数値検算器はproducer関数を呼ばず、IO入口だけが共有metadata helperを使用する。

実装26296b8で関連40試験/120.120秒通過後、実入力接続がevents hashの参照先違いを検出して数値計算前に停止した。正しいevent-ledger.jsonlへ修正し、別のevents.jsonlがある回帰fixtureを追加。入口13試験/13.510秒通過（重複除外41項目）。最終実装保存点2505fed6527a00891b9991720421b504a678899f。初回記録は上書きせず保持した。

最終実装でchunk0/attempt1、最初のdev seed・layout0×3方式×2条件の6評価を接続検算。288 profiles/86400 scores、source146/equipment84 episodes、120 incidentsと指標が一致。20 files/132760979bytes、10.061610秒、検証process peak private159862784bytes（152.46MiB）。前回12評価中の6件と重複し、profile/scoreのユニーク検算済み実データは12件のまま。

OUT artifacts/connected-observation-audit-2026-09-24、最終成功はverified-final/、文書commit/pinはsavepoint-evidence.json。終了時RAM空き16.79GiB、commit余裕15.73GiB、C/D空き138.31/332.30GiB、10秒の照合前後でD空き同値。継続的なリーク不在・PC全体の容量変動原因の保証ではない。本流889cfc3/fixed c01d1c9 clean、過去4保存点・closed・既存dirty guardのpin不変。banto-24 PAUSED維持。追加producer/holdout/push/mergeなし。

次は保存済み全120区間/720評価への接続監査の適用範囲・区切り・保存方法を決める。正常生成/overlay/丸め、bootstrap/CI/gate、runtime/単一writer受入も残る。対象6評価のprofile/score/ledger導出検算完了と、完全S6/formal/promotion=false/campaign加算0を区別する。

## 154. 全720保存評価の観測→profile/score→ledger検算完了（2026-09-24）

[全件検算記録](anomaly-multiseed-v0.3-full-connected-audit-2026-09-24.md)。前回実装2505fedを変更せず、HEAD f727be6bfb02b8fb7385bd34ce1121a866d8f64fで区間1〜119の714評価を順次検算。区間0の6評価は前回保存点SHA256 5a79114f8af267688e942b52763ad0d70b5cb8c55b650b3a1dcdf91ffe94d089と全対象入力hash一致後に再利用した。失敗区間119/attempt1を保持し、verified attempt2のみ検算する。

全120区間/720評価（dev576/smoke144）、240datasetsに重複・欠落なし。34560 profiles/10368000 scores、source17272/equipment9949 episodes、14400 incidentsと指標が一致。保存上の評価結果success720。前回比較表の全720元記録ともidentity/attempt/件数/指標が一致し、C1機械2200/2400、センサー2280/2400、precision4480/4680、未対応警報200件などの記述統計は変わらない。

検算済み実データのユニーク数は720へ更新。前回の12評価を別加算しない。新規6区間ごとの中間保存19回、所要1196.095751秒（19分56秒）。実行補助4試験通過、前回41項目を通過した本体はcode pin不変。照合対象は重複除外2281files/15903023776bytes、savepoint/evidenceの繰返し読取り等は別。

OUT artifacts/full-connected-audit-2026-09-24。区間別report、checkpoint-120-completed.json、summary.json、119区間の資源記録を保存。最終文書commit/pinはsavepoint-evidence.json。process peak private187.53MiB、処理後private83.82→129.47MiB/最大129.89MiB、最小空きRAM14.59GiB/commit余裕13.42GiB。終了時RAM15.47GiB/commit15.58GiB、C/D空き137.72/323.55GiB、新OUT約7.96MB。継続的なリーク不在の証明ではない。

新producer/登録seed生成/追加attempt/holdout起動0。固定source c01d1c9と本流889cfc3 clean、過去保存点・closed・dirty guard不変。banto-24 PAUSED維持。旧controller/旧audit reportを変更せず、歴史的なpublication/source/runtime/supervisionは完走保存点を前提とする。

次は正常生成/overlay/丸めの独立検算の設計・実装。bootstrap/CI/gate、runtime/単一writer受入も残る。全720件のprofile/score/ledger導出検証済みと、完全S6/formal/promotion=false/campaign加算0を区別する。Phase 2/3全体は未完了。

## 155. 全240datasetsの正常生成/overlay/丸め検算完了（2026-09-24）

[検算記録](anomaly-multiseed-v0.3-independent-generation-audit-2026-09-24.md)。実装/実行 `47dbc165f12fb1ce7608bb57625cb498bc4a4d04`。stdlibのみの独立consumerを追加し、全120 pairsの正常系列を既存10 seedからメモリ内で再構成した。保存観測4,320,000行/21,600,000cells、quality-mask、計画/有効eventが完全bytes一致。前回全720評価のprofile/score/ledger報告とも共通入力pin・identity・attemptで接続した。失敗chunk119/attempt1は保全し、attempt2のみ使用。

consumer/IO22試験、実行補助6試験通過。準備中のWindows文字コード/組込みmodule記録での停止2件はdataset読取り前であり、旧runner/logを保全した。OUT artifacts/independent-generation-audit-2026-09-24、成功結果verified/。最終文書revision/pinはsavepoint-evidence.json。

所要113.560秒、peak private57.41MiB、最小空きRAM14.57GiB/commit余裕14.84GiB、終了時C/D空き136.81/315.18GiB。pilotと6区間ごと19中間保存。生成primitiveのRandom/gauss/binary64/round/JSONは共有仕様で、独立PRNGを実装した意味ではない。新規producer/検出器評価/追加attempt/holdout/保存datasetは0、既存seedの検算再構成は120回。旧score計算を繰り返していない。

normal_generation/pre_rounding_overlay/rounding_verifiedは全240datasetsでtrue。完全S6/formal/promotionはfalse、performance=not_evaluated、campaign加算0。次はbootstrap/信頼区間/候補比較の独立実装と手計算fixtureを整理する。正式40 holdout seedを現10 seedで代用せず、holdoutは開かない。単一writer/runtime受入とPhase 2/3全体は残る。実計算source・本流clean、既存dirty guard・旧anchor不変、banto-24 PAUSED維持。

## 156. 独立bootstrap/CI/候補比較の算術検証（2026-09-24）

[検証記録](anomaly-multiseed-v0.3-independent-inference-math-2026-09-24.md)。実装/実行 `4dd9795c347fc5d00a38c4dfb42379ffc1f8337d`。stdlibのみで固定rejection draw、ratio-of-sums、paired差、type-7、null replicate、全層/target gates、C1優先選択を実装した。21試験通過。全200万個のindex SHA256 e375bf3feacb2f04bf5e1d40b141c1cfc5f69fa5437ea2704e323fd7523b22e5と4golden行が一致。7手例（各2clusters/4replicates/9tables/180gates）も保存した。

OUT artifacts/independent-inference-math-2026-09-24。draws/rules/fixture/hand-answers/test-results/summary、最終文書revisionはsavepoint-evidence.json。所要3.633秒、peak private29.26MiB、最小空きRAM17.71GiB/commit余裕21.68GiB、終了時C/D空き131.04/298.63GiB。初回の十進手答えassertの1 ULP差はテスト側だけ修正し、閾値の1 ULP境界試験を維持。

実観測/実seed集計/実性能CIは読取り・生成・計算していない。fixture_*の選択例を実採択にせず、selected_candidate=null、formal/promotion/S6=false、performance=not_evaluated。既存旧保存点・source・本流・dirty guard不変、banto-24 PAUSED。

次は保存済み監査結果のseed単位raw counts集計と認証入口。登録順、全12layouts×2層×3候補、profile/母数/重複欠落を確認し算術へ接続する。現dev8/smoke2を正式40holdoutへ代用しない。正式schema/実CI/全gate/slice/delay、runtime/単一writer受入は残る。

## 157. 認証済み保存報告からのseed raw counts集計（2026-09-24）

[詳細](anomaly-multiseed-v0.3-independent-seed-aggregation-2026-09-24.md)。最終実装`d48ecb4ac2a1d6c7c72d3cd16966b84600e165c5`、OUT `artifacts/independent-seed-aggregation-2026-09-24`、成功はverified/。33試験通過、dev8/smoke2×各12 layouts/2層/3候補の全720評価を認証。seed90表・role18表の1404 countsと候補差12表144点が旧記述集計と一致。登録順、母数、profile状態、入力pin、verified attemptを確認し、区間119失敗attempt1を除外して保全した。

初回5c8c4f8では警報0件の適合率46評価の正しいinconclusive状態を入口が拒否。分母0のnull状態を修正し、手例を追加。undefined_input_pointsを保持し、recall/予定露出から当該区間を落とさない。実評価の失敗ではない。初回記録はOUT直下、成功結果はverified/に分離保存。

処理1.289秒、peak private 39.27MiB、最小空きRAM 15.63GiB/commit余裕 21.22GiB、終了時C/D空き 130.22/297.07GiB。新規観測/評価/score再計算/実CIは0。旧保存点・本流・実計算source・dirty guard保全、banto-24 PAUSED。

次は独立analysis出力のschema接続を手例で検証する。実dev/smokeに正式40holdoutのbootstrap/gateを代用しない。slice/delay/runtime・単一writer受入/正式holdout/完全S6は未完了。formal/promotion=false、selected_candidate=null、performance=not_evaluated。

## 158. 独立算術からanalysis結果表への手例接続（2026-09-24）

[詳細](anomaly-multiseed-v0.3-analysis-table-adapter-2026-09-24.md)。実装`9b18626703c40801a164f61eb01dab3acbb36eae`、OUT artifacts/independent-analysis-adapter-2026-09-24。新11＋算術21＋S1契約27=59試験通過、7手例の各9表/180判定を保存。raw counts/CI/gatesを丸めずschema部分形式へ変換し、必要なeffective exposureと全検出delayを明示入力、全体medianを元delay結合から算出。

手例は2架空clusters/4replicatesで、正式40×50,000やsource evidenceを偽装したfull documentは出力しない。fixture_*だけに仮選択を置き、実selected=null/performance=not_evaluated/formal/promotion/S6=false。実dev/smoke集計はreadiness確認だけ。full schema/source/runtime/slicesは未完了。

実行2.516秒、peak 27.36MiB、RAM空き最小15.09GiB/commit余裕21.12GiB、C/D空き128.43/298.74GiB。保存約1.3MB、旧保存点/実source/本流/dirty guard保全、banto-24 PAUSED。

次は保存済み検出遅延・sliceの独立集計。必要列の認証と有限メモリでの読取り、母数/重複/欠落、結合delayを確認し、既存score再計算は不要。正式holdout/CI/gateや保留principalを起動しない。

## 159. 保存済み720評価の検出遅延・診断slice独立集計（2026-09-25）

[詳細](anomaly-multiseed-v0.3-independent-slice-audit-2026-09-25.md)。実装`782dcb7957e29dce481f0dea5c136df85a9152f3`、OUT artifacts/independent-slice-audit-2026-09-25。関連32試験通過。全120区間/720評価JSONを監査済みpinで認証して読み、10,368,000 score行・14,400事例からincident6軸/score9軸を集計。seed90/role18表が旧countsと一致し、母数・重複欠落・順序を確認した。旧score/matching検算を再利用し、再計算しない。

因果検出だけの遅延1〜5秒の正確な度数を合算し、全体median/mean/min/maxを算出。未検出はnull。event-offsetは40計画event参照で10件のload_proxyを対象外として明示、負offset試験外も保持。target品質・有効qualityと交差する同target正例窓のoverlapという診断定義を明記。正式slice schema/full documentを完了扱いしない。

処理844.159秒、process peak private 145.32MiB、最小空きRAM 9.60GiB/commit余裕 16.49GiB。終了時C/D空き 127.05/298.62GiB。 21 checkpointと120区間reportを保存。最終文書revision/pinはsavepoint-evidence.json。旧保存点/実source/本流/dirty guard不変、banto-24 PAUSED。新観測・新評価・score計算・実CI0。

次は、別々に検算したcounts・遅延・sliceを単一の認証済み解析入力へ統合し、正式schemaで不足するsource/runtime証拠等を整理する。現dev8/smoke2は記述集計に限定し、正式40holdoutの代用にしない。 正式holdout/CI/gate、runtime/単一writer受入、完全S6/Phase 2/3は残る。formal/promotion/S6=false、selected=null、performance=not_evaluated。

## 160. 認証済みcounts・遅延・sliceの解析入力統合（2026-09-25）

[詳細](anomaly-multiseed-v0.3-analysis-inputs-2026-09-25.md)。実装`1db34dc3502552feb0869da2cec68508736f1b8d`、OUT artifacts/independent-analysis-inputs-2026-09-25。関連39試験通過。外部slice保存点SHAから三保存点・counts/slices・schemaを認証し、全720評価のseed90/role18表を結合。overall30組/role18組の加算を確認し、未定義適合率46記録、profile診断、offsetの対象外/試験外参照を保持した。読取6入力ファイル5,453,594bytes、元payload読取0。

処理3.176秒、process peak private 53.00MiB、前後観測の最小空きRAM 10.68GiB/commit余裕 15.14GiB、終了時C/D空き 126.79/298.91GiB。 最終文書revision/pinはsavepoint-evidence.json。新観測・新評価・score再計算・実CI0、旧保存点/source/本流/dirty guard不変、banto-24 PAUSED。

正式schema必須10項目のreadinessを保存。dev/smokeの記述入力は揃ったが、正式40holdout/50,000 bootstrap・CI/gate・source/runtime受入・正式slice行への対応・完全S6は未完了。formal/promotion/S6=false、selected=null、performance=not_evaluated。次は統合済み入力から、dev/smoke別の記述結果表と診断表を出力する。正式schemaとの列対応を確認し、event-offsetの対象外/試験外参照やavailability・閾値超過・警報開始数を落とさない。

## 161. 用途別記述結果表と全条件別診断の出力（2026-09-25）

[詳細](anomaly-multiseed-v0.3-descriptive-report-2026-09-25.md)。実装`e0753ba4e1518706002cb3a51f9b5a3c891a4e7c`、OUT artifacts/descriptive-report-2026-09-25。新9＋統合7＋adapter11=27試験通過。認証済み解析入力からdev/smoke各9表を出し、234主指標・5,670診断行を元入力/schema部分形式へ照合した。incident recall864行、scoreのavailability/threshold exceedance/signal onset各1,602行を別系列にし、対象外・試験外参照や遅延度数・適合率未定義46記録を保持。

report.md/HTML/JSONを保存。HTMLは18展開セクション/54表/2,610行を構造確認。3入力5,171,731bytesを認証し元payload読取0。処理1.625秒、process peak private 44.18MiB、前後観測の最小空きRAM 14.70GiB/commit余裕 21.44GiB、終了時C/D空き 126.09/293.77GiB。 最終文書revision/pinはsavepoint-evidence.json。新観測/評価/score再計算/実CI0、旧保存点/source/本流/dirty guard不変、banto-24 PAUSED。

正式full documentは出さず、実dev/smoke母数によるschema部分検証のみ。入力時点のreadinessは文脈として保持する。formal/promotion/S6=false、selected=null、performance=not_evaluated。次は既存のsource/runtime・単一writer受入記録と独立consumerの接続状況を調べ、freeze前に必要な実装・証拠の残件を確定する。既存合格試験を繰り返す必要があるかを先に判断し、保留principalや正式holdoutは起動しない。

## 162. 受入証拠・consumer接続の残件整理（2026-09-25）

[詳細と5まとまりの完了条件](anomaly-multiseed-v0.3-acceptance-gap-review-2026-09-25.md)。基準ddd0165a45f42e9921e849e150d2cba63714b3a6、OUT artifacts/acceptance-gap-review-2026-09-25、成功verified/とsupplement-source-map.json、最終文書revision/pinはsavepoint-evidence.json。11保存点＋3小型receipt203,543bytesを外部hashへ照合。158source等比較中157一致、差分は旧READMEの追記だけ。単一writer実装は旧27試験時点から不変。

10consumer入口から静的import候補17モジュールを記録。manifest.pyのみworking CRLF/Git LF差があり、正規化後同一だがraw不一致のまま保全。旧Linux CI036ecb4からselected11本に差があるため、そのpassは最新候補の全回帰受入ではない。完全dependency/runtime closureやconsumer freezeとは記録しない。

本流が別作業でclean 6f1285d28a37edf486ba5c49b8dac3708c7f3067へ進んだ（4commit/5path）。main docs/READMEのtemp native/Windows互換試験記録はGit bytesまで確認し、raw/CI独立再検証なし。自動統合やWindows3.12必須化、§116保留principalの再開なし。今後helper.boundariesの旧main HEAD固定をそのまま使わず、今回review.pyの観測境界を参照する。実計算c01d1c9、完走closed、旧保存点、dirty guardは不変。

OSはProfessional25H2/26200/UBR9457。旧engineering9445からの更新を記録、正式pin9168や過去runtimeは変更なし。主確認2.450秒、peak26.82MiB、最小空きRAM11.49GiB/commit余裕19.98GiB、C126.24/D293.31GiB。新観測・評価・score/bootstrap・試験実行・元payload読取0。初回main guard停止とraw差guard停止をOUT直下に残し、成功確認をverified/へ分離した。

freeze前は(1)単一writer/OS方針の正式運用契約、(2)consumer正式入出力、(3)source/runtime受入・版固定、(4)保存公開接続、(5)容量時間予算の5まとまり。正式holdoutと最終独立監査はその後。次は1/2の接点として、consumerの入力・検査・出力と必要な接続試験を具体案にする。既存合格試験/720評価を反射的に再実行せず、実holdout・gateは閉じたまま。banto-24 PAUSED、formal/promotion/S6=false、Phase2/3全体未完了。

## 163. consumer入出力と保存の具体契約案（2026-09-25）

[契約案](../anomaly-v03-consumer-io-proposal.md)、[確認記録](anomaly-multiseed-v0.3-consumer-io-contract-2026-09-25.md)。起点0b75c1ea89a15e04dbde0963ae2b634648a10201、OUT artifacts/consumer-io-contract-2026-09-25、最終revision/pinはsavepoint-evidence.json。入力7項目・8工程・保存payloadと失敗状態を具体化、10consumer/22関数/schema必須10欄とT01〜T12の接続確認群を対応づけた。既存算術/保存の試験を再利用し、新入口の境界へ確認を絞る。

主analysisのsliceはincident recall＋score availability、sidecarは全4系列とする案。主1,233/sidecar2,835行は予定在庫、実行結果ではない。補助sliceは記述値でCI/gate未計算。formal mapping/新運用契約未採択、旧科学schema/registry/正式gate不変。23ファイルpinとAST/schema参照の整合確認を実施、試験実行/観測読取/評価/bootstrapは0。

資源peak22.72MiB、最小空きRAM11.67GiB/commit余裕20.34GiB、C124.98/D293.92GiB。前保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変。manifest.py改行差は保全、banto-24 PAUSED。次はT01〜T04前段のI/Oなし入力契約validatorをfixture/engineering専用で実装。正式mode拒否を維持し、観測reader/推論/writerは接続しない。正式採択・freeze・S4/S6・Phase2/3全体の完了とはしない。

## 164. consumer入力宣言のI/Oなし検査（2026-09-25）

[API](../anomaly-v03-consumer-input.md)、[結果](anomaly-multiseed-v0.3-consumer-input-validator-2026-09-25.md)。実装3fb988292e433311cfd86f00c773b8f17384a750、OUT artifacts/consumer-input-validator-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。fixture1区間6評価/engineering120区間720評価のplanned_inputとvalidate_inputを実装。formal modeを対象展開前で拒否し、canonical metadataの外部digest、固定identity/order/coverage、6種input pinと失敗履歴を検査。

既知入力pinを候補間/attempt間で固定。過去failed記録を残し最新attemptのみcoverageへ加算、成功後/連番欠落/integrity後のretryを拒否。profile inconclusiveをsuccessやsoftware failureへ変換しない。全chunkが完了してもproducer失敗ならdeclared_complete=false、公開済みmarkerは保持。検査成功でもデータ・source/runtime認証やexecution/analysis/formal/promotion/S6許可は全false。

22新規試験pass、failure/error/skip0、0.268秒。架空metadataと登録720枠だけで、file/process/bootstrapを呼ばない検査も実施。実payload/観測読取・評価・再計算0。peak29.58MiB、最小空きRAM12.93GiB/commit余裕20.23GiB、C124.32/D294.53GiB。前保存点/23参照ファイル・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変、banto-24 PAUSED。

次は完了記録から入力宣言への変換adapterをdecoded metadataだけで実装し、identity/最終attempt/失敗履歴/6種pinを外部anchorへ結合。観測reader・推論・writer・正式modeは接続しない。T01〜T04前段のみで、raw/path/marker認証や正式運用採択、S4/S6、Phase2/3全体は未完了。

## 165. checkpoint記録からconsumerへの変換（2026-09-25）

[API](../anomaly-v03-consumer-checkpoints.md)、[結果](anomaly-multiseed-v0.3-consumer-checkpoint-adapter-2026-09-25.md)。実装1a88d33d3dc4953e239a536f2bd5ea183904f02f、OUT artifacts/consumer-checkpoint-adapter-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。decoded plan/journal/全attempt manifestと外部4pin/countを既存reducer/manifest契約/consumer slot検査へ接続。最終attemptと過去失敗記録を保持し、既知6種hashを候補/再試行間で固定する。

区間別markerと全体producer markerは別なので、既存入力v1を緩和せず別checkpoint envelopeを返す。失敗manifest欠落はunreported/evaluations=null。profile_statusもslot宣言からの対応づけで、profile bytesの確認ではない。37試験（15新規＋22関連既存）pass、failure/error/skip0、35.876秒。

旧保存点のraw pinへ管理記録484件10,013,204bytesを1回照合。362journal/121manifest/120区間/720評価の実対応を確認（5.890秒）。区間119 attempt1はstage complete宣言6評価があるがmarkerなし/resource_limit失敗、attempt2だけ集計。原記録を補正せず保全。観測/evaluation本文/score読取・再計算・追加評価0。

peak73.05MiB、最小空きRAM12.57GiB/commit余裕20.16GiB、C/D124.22/298.67GiB。旧保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変、banto-24 PAUSED。次は固定hash readerと結合して区間公開印・manifest・終了記録の参照を認証。管理記録hash照合を公開/実終了/payload認証へ格上げしない。正式採択/freeze/推論/writer/S4/S6/Phase2/3は未完了。

## 166. 公開・終了記録のconsumer reader（2026-09-25）

[API](../anomaly-v03-consumer-publication.md)、[結果](anomaly-multiseed-v0.3-consumer-publication-reader-2026-09-25.md)。実装1b3021f8debbd4edb78b8d75efcf73cd6de88a7c、OUT artifacts/consumer-publication-reader-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。外部anchorのadapter/closedを使い、固定8管理file/区間（上限1,040KiB）で公開印・manifest・worker終了記録を照合する。hardlinkの同一identity、path/role/hash/attempt/runtime/outcomeの対応を確認。

14新規試験pass、failure/error/skip0、62.046秒。実記録4境界区間→残116区間を確認し、4区間の再読取なしで全120区間/720評価の報告を併合。960読取14,663,483bytes（closedは区間ごと）、unique841file/13,518,584bytes。所要0.867＋18.140秒。観測/evaluation本文/score/監査本文の読取・再計算・追加評価0。

metadata/manifest bytes/過去worker終了記録/controller closureは認証したが、全payload/監査本文は未認証。controller closedは処理完了記録でOSプロセス終了証明ではない。controller_process_exit_verifiedとtrust/analysis/execution/formal/promotion/S6はfalse。区間119 attempt1の失敗は元adapterに保全、attempt2のみ選択。

peak44.61MiB、最小RAM10.71GiB/commit余裕17.57GiB、C/D122.85/270.18GiB。旧保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変、banto-24 PAUSED。次は既存の独立監査済み集計入力との参照対応を固定し、重い再計算を避けてconsumer接続を進める。旧検証履歴の再利用範囲を明示、正式採択/freeze/推論/writer/S4/S6/Phase2/3は未完了。

## 167. 集計入力と公開metadataの導出結合（2026-09-25）

[API](../anomaly-v03-consumer-analysis-binding.md)、[結果](anomaly-multiseed-v0.3-consumer-analysis-binding-2026-09-25.md)。実装c4f04121764c882e1cb885f9fea173e4bc2d6cc3、OUT artifacts/consumer-analysis-binding-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。外部publication/analysis保存点と明示5rootから固定10artifactを各1回認証。hash連鎖をcheckpoint adapter・counts・完走evidenceへつなぎ、任意の記録内pathを開かない。

14新規試験pass（failure/error/skip0、11.189秒）。実記録10artifact/9,785,474bytes、0.542秒で全120区間/720評価を結合。公開管理記録960参照、input hash4,320件、evaluation hash720件が一致。10seed cluster/90seed表/18role表の元集計値・nullを維持。区間119 attempt2、過去失敗1件、判定不能46指標を保全。観測/score payload読取・score/集計再計算・新評価・bootstrap0。

集計入力bytesと公開metadataへの参照は認証したが、旧算術/診断の独立検証は保存点から再利用した。historical_aggregate_authentication_reused/historical_diagnostic_join_reused=true。全payload/source-runtime受入/trust/analysis/execution/formal/promotion/S6/controllerプロセス終了はfalse。

peak47.41MiB、最小RAM12.38GiB/commit余裕19.72GiB、C/D122.79/268.83GiB。旧保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変、banto-24 PAUSED。次は結合receiptからengineering consumerの入力選択・記述結果までを接続。既存APIと検証履歴を使い、重い再計算や正式gate/holdoutを起動しない。正式採択/freeze/S4/S6/Phase2/3は未完了。

## 168. engineering consumerの入力選択・記述結果保存（2026-09-25）

[API/CLI](../anomaly-v03-engineering-consumer.md)、[結果](anomaly-multiseed-v0.3-engineering-consumer-entry-2026-09-25.md)。実装6567a857455847baf225f552abf5ff9df6644c08、OUT artifacts/engineering-consumer-entry-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。結合receiptと記述結果の2保存点を外部pinで固定し、明示analysis-inputs.jsonを含む7fileを各1回認証。同じclosed/input anchor/hashを照合し、LocalPublicationへ4payloadを保存、writer終了後にreaderで確認した。

16新規試験pass（failure/error/skip0、0.560秒）。実保存7,896,608bytes、約2.055秒で入口から出力・読取を確認。全120区間720評価、dev8/smoke2、18表234主指標5,670診断行、chunk119 attempt2、過去失敗1件、判定不能46指標を保持。JSONのcanonical化は値を変えず、MD raw一致、HTMLは末尾LFだけ補った。観測/score読取・集計/比率/score再計算・追加評価/bootstrap0。

初回tuple比較の単体試験失敗を修正し、その後の実接続で判明したHTML末尾LF欠落に最小補正を追加。test-attempt-1/2と未完了publishedを保全し、最終成功はpublished-success。marker97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e、receipt11507bytes/SHAe2ac5bb2b36d5121062dd8bdc790556cd767cd22a7168ec0579d5aab6570cf3a。

peak37.25MiB、最小RAM12.53GiB/commit余裕19.81GiB、C/D122.78/268.83GiB。OS実値os-state.json。旧保存点・実計算c01d1c9・本流clean6f1285d・closed・dirty guard不変、banto-24 PAUSED。旧公開/数値/schema検証は保存点から再利用し、source-runtime受入/trust/formal/promotion/S6等へ格上げしない。次は契約案T01〜T12への対応と残件・容量時間予算の整理。正式採択/freeze/holdout/S4/S6/Phase2/3全体は未完了。

## 169. consumer契約対応と容量・時間シナリオ（2026-09-25）

[対応表](anomaly-multiseed-v0.3-consumer-coverage-budget-2026-09-25.md)。対象6af1c024be52c063e82f9a43143f2fc5e228258b、OUT artifacts/consumer-coverage-budget-review-2026-09-25。source変更なし、最終文書revision/pinはsavepoint-evidence.json。T01〜T12はengineering接続5群、旧検証再利用3群、部品まで1群、受入/外側状態/別reader接続残り3群。20保存file/2,818,781bytes、33 source/契約pin、30method参照を照合。直近5工程の新規81試験は歴史的合格記録で、今回新試験0。

元実績120区間720評価・16,081,676,236bytes・活動160,357.174秒から、正式480区間2880評価へ59.91GiB/178.17時間（7.42日）を単純外挿。別工程のscore/ledger約80.41分・生成約7.57分も参考値。正式CI/gate/選択・最終独立auditは未接続で予算未確定。240時間/96GiB＋空き32GiB（開始128GiB、同volume2コピー224GiB）は未採択・未適用の案。既存上限は変更なし。

過去区間119 attempt1はproducer900秒停止、同時期commit余裕52.73MiBの標本。原因帰属/リークは未確定で、privateとsystem commitを別に扱う必要を記録。今回C121.97/D256.05GiB、peak50.29MiB、最小RAM10.38GiB/commit余裕16.88GiB。主確認0.538秒。OS実値os-state.json、全旧境界不変、banto-24 PAUSED。

次はT11/T12：通常権限、writer終了後の別process reader、応答消失/読取失敗の外側receiptを接続。小さな架空入力と拒否例に絞り、旧保存試験や評価を繰り返さない。principal/UAC/ACL/同時書換え作業を再開せず、確定payload/markerは保全。正式化の5まとまり、source/runtime freeze、正式gate/holdout、S4/S6、Phase2/3は未完了。

## 170. 別process readerと外側receipt（2026-09-25）

[API](../anomaly-v03-consumer-reader.md)、[結果](anomaly-multiseed-v0.3-consumer-separate-reader-2026-09-25.md)。実装35842261a90b1efe475056dc9ef962c56773f1f1、OUT artifacts/consumer-separate-reader-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。writerを閉じた後の読取専用子processを既存supervisorへ接続し、外部marker/2保存点pinを新規requestに固定。旧source/結果からの対応を確認し、成功/不一致/応答消失を外側のresultへ保存。元結果/markerは不変。

13新規試験pass、failure/error/skip0、3.291秒。実確認は親35884/子27688、exit0/終了確認、監視error0。7file/7,896,608bytesから4payload/2,755,533bytesを確認し、元4payload＋2marker名の6pin不変。reader0.826秒、外側1.055秒。親peak33.34MiB/子35.91MiB、最小RAM12.30GiB/commit余裕20.24GiB、C/D130.25/329.72GiB。監視側OS26200.9457/Python3.14.0前後一致、全runtime/dependency受入ではない。

T11/T12 engineering部分を接続。再封印不整合は元保存点とのbytes比較で拒否し、独立数値audit実行はfalse。正式full document/source-runtime受入は未完了。次は40-cluster入力・推論/full document adapterを非登録の架空入力で準備し、正式mode/holdout/新評価/実データbootstrapは起動しない。旧境界・dirty guard・banto-24 PAUSEDを維持し、保留principal/UAC/ACL/同時書換え作業を再開しない。


## 171. 架空40clusterから結果文書草稿への接続（2026-09-25）

[API](../anomaly-v03-document-fixture.md)、[結果](anomaly-multiseed-v0.3-consumer-document-fixture-2026-09-25.md)。実装e2abbdce00719db482253c140a200d0776288284、OUT artifacts/consumer-document-fixture-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。既存推論・表adapter・固定schemaを使い、40cluster/1〜64drawの純粋関数を追加。9表180gate、10文書項目の対応、入力canonical hashと実drawを保持する。

12新規試験pass、failure/error/skip0、1.085秒。旧suite再実行なし。初回1失敗はcontrol precision nullに関する試験側想定の修正、既存科学条件は不変。test-attempt-1保全。保存例40cluster/4draw/160indexは0.089秒、入力279174bytes・出力220078bytes。正式validatorの草稿拒否も確認。

今回の測定process peak private 31.09MiB、最小空きRAM 10.01GiB / commit余裕 19.26GiB、例の保存後C/D 129.89/327.19GiB。 OS26200.9457/Python3.14.0、旧境界とdirty guard不変、banto-24 PAUSED。新評価/登録データ読取/正式bootstrap0。架空CI計算は実施、formal/promotion/S6/trust=false、実selected=null。

草稿のstatus/provenance/analysis_consumer/bootstrap/slicesはnull、正式full documentは未完了。次は架空診断からincident recall/availability slice行を作り、草稿へ接続する。正式実行/freeze・追加上限変更・保留principal/UAC/ACL作業は開始しない。


## 172. 架空診断のsliceを文書へ接続（2026-09-25）

[API](../anomaly-v03-slice-fixture.md)、[結果](anomaly-multiseed-v0.3-consumer-slice-fixture-2026-09-25.md)。実装52a032bf8bb22a1eee301ba0cb6d4bbb77a35bed、OUT artifacts/consumer-slice-fixture-2026-09-25、最終文書revision/pinはsavepoint-evidence.json。40clusterの診断countsから本文1233行・補助4系列2835行・詳細9表を接続。個別clusterと主表への件数/delay/profile対応、incident結合・周辺表、target/modeを検査する。既存v1と実入口は不変。

13新規試験pass、failure/error/skip0、16.694秒。旧suite再実行なし。保存例は前工程の主CIを再利用し、接続1.831秒、入力4337681bytes・出力3162172bytes。正式validatorの拒否を確認。測定processの最大private 70.88MiB、最小空きRAM 9.98GiB / commit余裕 18.87GiB、例の保存後C/D 125.54/370.16GiB。 OS26200.9457/Python3.14.0。旧境界・dirty guard不変、banto-24 PAUSED。

草稿6項目を配置、status/provenance/analysis_consumer/bootstrapはnull。新評価/登録データ/実データbootstrap0。正式mapping採択・source/runtime受入・独立S6は未完了。次は最新consumerの依存一覧/固定方法と正式実行前の判断資料を整理する。正式freeze・holdout・上限変更・保留principal/UAC/ACL作業は始めない。


## 173. 最新consumerのsource/runtime候補と固定方法（2026-09-25）

[計画](../anomaly-v03-consumer-source-runtime-plan.md)、[結果](anomaly-multiseed-v0.3-consumer-source-runtime-review-2026-09-25.md)。対象e9826bd0245cf26cf540e1ff470528c001f3cd5f、OUT artifacts/consumer-source-runtime-review-2026-09-25。source変更なし、最終文書revision/pinはsavepoint-evidence.json。5役割union41source/566551bytes、設定等18file・CLI2fileを照合。39source raw一致、generator.py/manifest.pyは改行差のみ。33stdlib候補、dynamic/native/subprocess15箇所、13method参照を記録。closure/freezeではない。

直近4保存点の54試験記録とsource pinを照合し、unit test0。起動probe2件では-I -Bにsystem siteが残り、-I -S -Bで除外。project import0、OS26200.9457/CPython3.14.0一致。Python exe/DLLとGit2.51.2.windows.1のpinを観測、全DLL/stdlib/外部tool閉包は未確認。主確認7.670秒、最大private 52.37MiB、最小空きRAM 10.26GiB / commit余裕 18.97GiB、主確認後C/D 124.43/370.49GiB。

6作業と将来の採択2まとまりを保存。次はreaderへ-S追加、通常権限の小さい接続試験。続いてsource/runtime証拠validatorを具体化する。正式consumer/証拠結合/予算が揃う前に採択待ちとしない。旧240h/96GiB案は未適用。実freeze・正式評価0、旧境界/dirty guard/banto-24 PAUSEDを維持、principal/UAC/ACL/同時書換えは保留。


## 174. engineering readerのsite初期化除外（2026-09-25）

[結果](anomaly-multiseed-v0.3-consumer-reader-no-site-2026-09-25.md)、[API](../anomaly-v03-consumer-reader.md)。実装863af36c74aad1bc63ff42bd5b2b469c748882df、OUT artifacts/consumer-reader-no-site-2026-09-25。最終文書revision/pinはsavepoint-evidence.json。-I -S -Bで起動し、reader＋testsの2fileだけを変更。旧pinは保全。

14接続試験pass、failure/error/skip0、3.963秒。実子の起動flag/site除外と架空公開結果の読取を確認。-Sだけを外した対照1件はno_site=0で期待どおり失敗し、sourceは変更していない。timeout/終了未確認は既存模擬試験、7子processの実監視は終了確定。試験processの最大private 32.27MiB、監視した子の最大private 21.44MiB。試験前後の最小空きRAM 11.15GiB / commit余裕 19.45GiB、試験後C/D空き 124.34/365.97GiB。

OS26200.9457/Python3.14.0。旧境界・dirty guard不変、banto-24 PAUSED。新評価/登録データ/正式bootstrap/freeze0。次は役割別source/runtime証拠validator。完全closure、正式consumer・最終audit/資源予算・S4/S6は未完了、principal/UAC/ACL/同時書換えは保留。


## 175. consumerの実行証拠と供給bytesの結合（2026-09-25）

[API](../anomaly-v03-consumer-evidence.md)、[結果](anomaly-multiseed-v0.3-consumer-execution-evidence-2026-09-25.md)。実装c79fc9e5db7d486a22c2ed4b5f5e75ca0027f7a0、OUT artifacts/consumer-execution-evidence-2026-09-25。新規module/test2本。analysis/audit/readerの外部期待値に前後source/runtime、process、全入出力bytesを結ぶ。16架空試験pass、failure/error/skip0、0.081秒。自己申告pass・役割/PID生成token違い・bytes差・未終了・前後OS差を拒否。

試験processの最大private 27.20MiB、試験前後の最小空きRAM 11.20GiB / commit余裕 19.57GiB、試験後C/D空き 124.34/365.97GiB。 前工程47code/18data pin・旧境界/dirty guard不変、banto-24 PAUSED。実process採取・評価・登録データ・bootstrap0。成功はsupplied-bytes-only、正式受入/全closure/実行真正性/S6ではない。

次：通常権限readerの実際の起動観測と外側で保持した期待値を、このvalidatorへ接続する。最初は既存の小さな架空公開結果で確認し、親の観測値を子の値として流用しない。 正式consumer・最終auditと予算、source/runtime受入は残る。正式freeze/holdoutや保留principal/UAC/ACLは開始しない。


## 176. 実reader観測と外部期待値の結合（2026-09-25）

[API](../anomaly-v03-reader-evidence.md)、[結果](anomaly-multiseed-v0.3-reader-observed-evidence-2026-09-25.md)。実装0ee336e72ca52849e6725415a3d7f8e4ff75aeeb、OUT artifacts/reader-observed-evidence-2026-09-25、成功attempt-3/。新APIはselected source10/Python2file、元handle・子selfのPID/生成FILETIME、前後環境、入力15fileを結合。新規13試験pass＋同工程の不変な既存回帰27種類を再利用。初回Git hardlinkによる失敗とattempt-2中間成功を保全。

保存例child 38824 exit0/reaped、監視0.809秒、OS26200.9457/CPython3.14.0。今回processの最大private 50.43MiB、保存例の子は36.34MiB。観測時の最小空きRAM 10.21GiB / commit余裕 17.88GiB、保存例後C/D空き 124.38/365.97GiB。 旧境界/dirty guard/banto-24 PAUSED不変。新評価・登録データ・bootstrap0。parentの期待値はメモリ保持し、保存記録から再採用しない。未終了ownerは保存失敗時も保持。

次：readerの依存sourceとstdlib/extension/loaded DLLの記録範囲を広げる。既知のCRLF差を現在の作業コピーで修正せず、必要なら指定revisionの一時的な候補checkoutでraw一致を確認する。正式freezeとしては扱わない。 完全closure/正式consumer/独立audit/資源予算は残る。正式gate・holdout・principal/UAC/ACLは開始しない。

## 177. reader依存source/runtimeの観測拡張（2026-09-25）

[API](../anomaly-v03-reader-evidence.md)、[結果](anomaly-multiseed-v0.3-reader-dependency-observation-2026-09-25.md)。実装0b03b91a59c7359e4eb05e3585242b88aa8c8cab、OUT artifacts/reader-dependency-observation-2026-09-25、成功attempt-2/。source28/stdlib79/cache候補77/extension8/その他native40、計232file/47,574,229bytes。177modules/loaded48images。前後差分0。親がdisk/Gitを照合し、外部nativeは親にもloadした同一pathに限定。完全closure/独立runtime事前期待値ではない。

新規13pass＋同工程の不変な既存29種類を再利用、unique42。初期ctime差とESET DLLによる失敗を記録。sample PID20520 exit0/reaped、監視1.566秒、private36.30MiB。資料生成後RAM11.08GiB/commit余裕19.47GiB、C124.35/D365.94GiB。候補rd01はclean0b03b91a59c7359e4eb05e3585242b88aa8c8cab、743file/8,430,967bytes、raw/Git一致。元70b0のCRLF差は変更しない。旧境界/dirty guard/PAUSED維持、新評価/実データ/実bootstrap0。

次：reader用の依存一覧を実行結果とは別に保持する期待profileへ落とし込み、import準備の境界と照合手順を定義する。今回の観測一覧をそのまま正式な期待値やfreezeとして採択しない。 既定APIのsource10/Python2file bindingと補助観測を区別。正式consumer/最終audit/全体予算、analysis/audit roleは残る。正式gate/holdout/principal/UAC/ACLを開始しない。

## 178. readerの事前保持依存候補への接続（2026-09-25）

[API](../anomaly-v03-reader-profile.md)、[結果](anomaly-multiseed-v0.3-reader-dependency-profile-2026-09-25.md)。実装0b2da336d90bcc60e97798d83d17d9f6f7421a34、OUT artifacts/reader-dependency-profile-2026-09-25、最終final/。prepare_profileは別の未profile化referenceの保持result pinから候補を新規保存。後続readerは保持candidateへ232files/177modules/48images、runtime/role/revision/root/境界を前後比較。candidateは16番目の入力。原本・copy差し替え、追加/欠落も拒否。

新規16pass、failure/error/skip0、53.083秒。初回41passのうち不変26種類を再利用、unique42。sample reference40904→reader29764、両者exit0/reaped、reader1.846秒。profile110646bytes/SHAa682eb680def9a61227696de7f76c6d6259d99705403cb150e41933ebb66a0ab。最終試験harnessのpeak private 52.46MiB、保存例readerのpeak 36.85MiB。資料作成前は空きRAM 10.35GiB / commit余裕 18.89GiB、C/D空き 126.00/326.57GiB。

rp01はclean0b2da336d90bcc60e97798d83d17d9f6f7421a34、746file/8,461,710bytes、Git/raw一致。rd01保全、元CRLF差/dirty guard/旧境界/closed/PAUSED維持。架空入力原本cleanup済み。次：解析側（engineering consumer）の実行観測と、別に保持した役割別期待値の接続を、小さな架空入力で具体化する。reader候補をanalysis/auditへ使い回さない。 候補の正式採択、準備processの観測、正式consumer/最終audit/全体予算も残る。正式gate/holdout/principal/UAC/ACLは開始しない。

## 179. analysis役割の保存結果準備を実process証拠へ接続（2026-09-26）

[API](../anomaly-v03-analysis-evidence.md)、[結果](anomaly-multiseed-v0.3-analysis-observed-evidence-2026-09-26.md)。実装2db441e44a65857f288f800a104ba436339358b9、OUT artifacts/analysis-observed-evidence-2026-09-25（開始日維持）、成功observed-example/。新module/test2本のみ。operation=prepare-saved-descriptive-resultに限定、7保存file/6622bytes、request/invocation込9入力/11272bytes→4payload/5237bytes。selected source12/Python2fileを親保持期待へ結ぶ。補助source29/全233file/178modules/48images、前後差分0。

全47pass（新15＋既存consumer16＋pure evidence16）、failure/error/skip0、36.157秒。sample child17940 exit0/reaped、監視1.546秒。試験harnessのpeak private 50.52MiB、保存例childのpeak 36.24MiB。資料作成前の空きRAM 10.59GiB、commit余裕 19.29GiB、C/D空き 125.95/326.57GiB。 ao01はclean2db441e44a65857f288f800a104ba436339358b9、750file/8,498,798bytes Git/raw一致。旧56code/18data・rp01/元CRLF差/dirty guard/closed/PAUSED維持。原本fixtureはcleanup済み、payloadと証拠は保持。

次：analysis専用の依存候補profileを別に準備し、後続の小さな保存結果準備が、起動前から保持した全依存一覧に一致するかを検査する。reader profileは使い回さない。 今回は保存済み記述結果の認証・準備のみで、数値再計算/完了publication/正式文書はなし。analysis_consumer=null、CLOSED維持。正式gate/holdout/freeze/principal/UAC/ACLは開始しない。

## 180. analysis専用の事前保持依存候補（2026-09-26）

[API](../anomaly-v03-analysis-evidence.md)、[結果](anomaly-multiseed-v0.3-analysis-dependency-profile-2026-09-26.md)。実装140e91de93e2cc43c45fab9efb9a7cbc6ece43c7、OUT artifacts/analysis-dependency-profile-2026-09-26。analysis専用のprepare_profileを追加し、別の成功した未profile化referenceと外部result pinから新規候補を保存する。format/role/operation/採取境界を固定し、reader候補の流用を拒否する。後続analysisは親が起動前から保持した候補のraw bytes/pinと依存集合へ前後一致を要求する。

全43試験pass（新規20＋既存analysis15＋reader候補の純粋検査8）、failure/error/skip0、145.715秒。誤pin、file hash改変、module欠落、子の再封印、保存copy差し替え、reference payload改変、候補の自動更新を拒否。source13/Python2file、候補を含む10入力を証拠へ結ぶ。依存source30/全234file/179modules/48images、47,606,116bytesが前後一致した。

保存例reference PID24184→後続PID8184は別process、双方exit0/reaped。後続監視2.123秒。候補111843bytes/SHA6502078885a3f42c7a356f0057a23f45ad24c384719380980cc4c4b0302b78ab。4payload/5237bytesはreferenceと後続で一致。原本の架空入力はcleanup済み、両実行のpayload/期待値/観測/監視と候補を保持する。試験harnessのpeak private 52.97MiB、保存例childのpeak 37.61MiB。資料作成前の空きRAM 9.77GiB、commit余裕 17.74GiB、C/D空き 125.89/346.17GiB。最終値はsave-checks.json。

ap01候補はclean 140e91de93e2cc43c45fab9efb9a7cbc6ece43c7、754tracked files/8,535,094bytesのGit/raw一致を検査。旧ao01/rp01/rd01、実計算checkout/本流/closed、元70b0の既知CRLF差と既存dirty文書を保全。banto-24 PAUSED。数値再計算・新評価・登録データ読取・実bootstrap・正式gate/holdout/freeze・principal/UAC/ACL・push/mergeなし。

candidate-not-acceptedであり、正式source/runtime固定やmemory codeの証明ではない。analysisの対象は保存済み記述結果の認証・準備だけ。numerical_analysis_performed/published/formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。次は、照合済みの4payloadを既存のsingle-writer公開処理へ接続し、writer終了後の別readerまでを小さな架空入力で通す。公開時に解析証拠と保持pinを結合し、数値再計算や正式採択へ範囲を広げない。 正式consumer/文書provenance/独立数値audit/完全資源予算は残る。

## 181. 解析証拠から通常公開・別readerへ（2026-09-26）

[API](../anomaly-v03-analysis-publication.md)、[結果](anomaly-multiseed-v0.3-analysis-publication-chain-2026-09-26.md)。実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48、OUT artifacts/analysis-publication-chain-2026-09-26。新module/test2本のみ追加し、既存analysis/profile/reader/collector/consumer/LocalPublicationを変更しない。外部result pinで選択したprofile付きanalysisの成功記録・4payloadを再認証し、保存原本との意味・bytes一致を確認して既存single-writer公開へ渡す。writerを閉じた後だけ、別のobserved readerを起動する。

公開物は従来どおり4payload。別directoryのpublication-binding.jsonが解析result/evidence/profile/binding pin、payload pin、公開root/marker、revisionと接続module pinを結ぶ。そのpinとreader result/evidence pinを最終chain resultへ保存し、呼出し側がresult_pinを保持する。公開marker単体は解析証拠の結合を証明しない。

全43試験pass（新14＋既存consumer16＋observed reader13）、failure/error/skip0、75.509秒。誤anchor・payload/evidence改変・reader role・未profile化・入力/出力重複・部分書き込み・writer応答喪失・reader失敗・結合記録改変・未終了ownerの保持を検査。正常時は二度目の公開を拒否し、元入力/公開物を保持する。

保存例reference PID11136→profile付きanalysis PID10040→通常writer PID39840→reader PID16652。全ての子はexit0/reaped。analysisはsource13/Python2file/10入力と依存234fileの事前候補一致、readerはsource10/Python2file/15入力と依存232fileの終了後照合。readerへanalysis候補は流用しない。4payload/5237bytes、marker SHA3837efdce90f6c7070ad0da8b1befa4c306ced1d6afcdebe2d976793e6fa997b。reader監視2.409秒。公開物/両analysis証拠/reader証拠/chain記録を保存し、架空原本だけtemp cleanup済み。

試験harness peak private 53.32MiB、保存例analysis child 37.66MiB、reader child 36.26MiB。資料作成前の空きRAM 10.13GiB、commit余裕 18.56GiB、C/D空き 133.21/345.91GiB。最終値はsave-checks.json。

pc01候補はclean f8f20bcf4ac7ade2f20e96f37bc1567328d88a48、757tracked files/8,567,147bytesのGit/raw一致。旧60code/18data pinとap01/旧候補、実計算checkout/本流/closed、既知CRLF差/既存dirty文書は不変、banto-24 PAUSED。新評価/数値再計算/登録データ読取/実bootstrap/正式gate/holdout/freeze/principal/UAC/ACL/push/mergeなし。

公開成功は架空engineering記述結果の通常公開で、正式文書や独立数値auditではない。formal/promotion/S6/trust/execution_authenticated/full closure=false、document_draft.analysis_consumer=nullを維持。接続moduleのGit/raw一致は確認したが、writer全processの実行証拠や全依存固定を完了したとは扱わない。次は、既存dev/smokeの保存済み記述レポートへこの一連の処理を適用し、外部anchor・解析証拠・公開marker・別reader結果を保存する。720評価は再実行せず、数値の正式受入やholdoutへ範囲を広げない。 正式consumer/文書provenance/独立数値audit/完全資源予算は残る。

## 182. 保存済みdev/smokeレポートへ公開接続を適用（2026-09-26）

[結果](anomaly-multiseed-v0.3-saved-report-publication-2026-09-26.md)。OUT artifacts/saved-report-publication-2026-09-26。既存dev/smokeの保存済み記述レポートに、profile付きanalysis→通常公開→別observed readerを適用して成功。実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48のpc01と前工程の依存候補を再利用し、source変更・新checkout・新reference起動・試験suite再実行は0。前回43試験の合格記録はcode pin不変を確認して再利用した。

認証した原本7file/7,896,608bytesから4payload/2,755,533bytesを出力。旧published-successの4payloadと2marker、計6fileのbytes/pinが新公開と一致し、原本7fileと旧公開6fileも実行前後で不変。過去の120区間/720評価の記述結果を保存したもので、新評価/数値再計算は0。

analysis PID14244、writer PID22020、reader PID21668。両子ともexit0/reaped、観測error0。全体26.528秒、子の監視はanalysis 2.072秒、reader 2.077秒。analysisの依存234fileは保持候補と前後一致、readerの依存232fileは終了後disk/Git照合。全処理harnessのpeak private 69.38MiB、analysis子 54.05MiB、reader子 52.51MiB。保存準備時は空きRAM 10.81GiB、commit余裕 19.30GiB、C/D空き 133.19/345.92GiB。最終値はsave-checks.json。

前工程manifest29435bytes/SHAe25092c42073f9129615bdb8188789a0eb07933d70dc9faa2f97469b7fb71dd3。62code/18data・旧境界/dirty guard/closed/PAUSED不変。新公開marker 97c8bc637328cb173e6c1a678765c7785512fb2ad7b66ed8af15939e819c874e、chain result 1709bytes/SHAea8b5c8b1185d06de8ae93a2e620191e742214be123fc630b7cc73edc8fc0f0c。候補・旧公開を削除せず、今回の解析/公開/reader記録を保持。formal/promotion/S6/trust/full closure=false、正式analysis_consumer=null。次は受入残件表を現在の実装・保存結果に合わせて更新し、正式consumer/本文provenance、独立数値audit、writer実行証拠、完全資源予算の未充足を具体化する。既存720評価は再実行しない。

## 183. 正式受入の残件・実行前後の区別（2026-09-26）

[更新表](anomaly-multiseed-v0.3-acceptance-gap-update-2026-09-26.md)。OUT artifacts/acceptance-gap-update-2026-09-26、開始文書56bb9a3698e80c082b698b2a45be4adf94064e31、実装f8f20bcf4ac7ade2f20e96f37bc1567328d88a48は不変。前保存点26548bytes/SHA53a0c1be44cb21114ada147e32d35346948d9664737bde9b9c41054dc362853a、62code/18data、11receipt20,083bytesと祖先保存点を照合。13sourceの静的確認とpc01/Git/作業版一致、保存済みslice草稿9表/1233行/2835行/null4欄を確認した。

5作業群とT01〜T12を更新し、通常保存・別readerは完了扱い。開始前に準備する契約/実装/役割期待値/回帰/予算と、開始後に得る実producer・50,000反復・正式本文・最終数値監査を分離した。新評価・数値再計算・suite起動・source変更・新checkoutなし。

次はI/Oなしのfixture専用5payload wrapper/証拠結合adapter。文書/slice/証拠validatorを再利用し、保持期待pin・役割・段階状態・coverageとの対応を小さい架空例で検査する。本文nullと不足は維持、正式mode拒否、保存結果準備を正式数値解析へ流用しない。既存保存/reader試験の反復や新公開process起動を含めない。完了後に数値解析/audit入口と資源停止へ進む。

仮予算240h/96GiB等は未適用。現在のsystem commit診断は強制停止ではなく、process supervisorのoutput制限はstdout/stderr分。全成果物・最終auditを含む予算と停止処理は正式準備の残り。開始時空きRAM10.85GiB/commit余裕19.36GiB/C133.12GiB/D367.39GiB、最終値はsave-checks.json。リークや他作業の原因は断定しない。

旧候補・実計算c01d1c9・本流6f1285d・closed・dirty文書/CRLF差保全、banto-24 PAUSED。formal/promotion/S6/trust/execution_authenticated/full closure=false。正式採択確認は具体的な契約差分・候補revision・受入記録・全体予算が揃ってから。principal/保護root/UAC/ACL/push/mergeは対象外。

## 184. 架空5payloadと供給実行記録を結合（2026-09-30）

[結果](anomaly-multiseed-v0.3-wrapper-fixture-2026-09-30.md)、[API](../anomaly-v03-wrapper-fixture.md)。開始536c66721878c04fb8c781ffcb86c4e868407033、OUT artifacts/wrapper-fixture-2026-09-30、tests-2/。新module/testの2本、旧62code/18data不変。mode/role/operation/revision/入力/出力pinを外部期待値へ結び、全2880の架空宣言枠と文書/sliceを5payloadへ対応付けた。

新16試験pass、failure/error/skip0、58.729秒。保存例5file/1,973,806bytes。未完了coverageの完成文書を拒否、None文書は失敗/未開始枠を保持。inconclusiveは処理済みの科学的判定不能として残す。本文null4欄、正式ready=false、writer/reader/audit not_run。架空PID/source/runtime bytesであり、実worker起動や正式解析の証明ではない。

試験/例保存harnessのpeak private 104.19MiB。保存例後の空きRAM 13.74GiB、commit余裕 14.42GiB、C/D空き 115.31/365.67GiB。OS実値26200/9457を記録。旧候補・実計算c01d1c9・本流6f1285d・closed・既存dirty文書/CRLF差を保全、banto-24 PAUSED。前保存点18702bytes/SHA3d5338c6e51d901b513b748dc95438455e8e9c5e13190e7f4876b76edaf1c28f。既存評価再実行0、正式許可/S6/trust/full closureはfalse。最終revision/pinはsavepoint-evidence.json。

次は、小さい架空入力を数値計算する所有workerと、起動前に呼出し側が保持する期待値を接続する。保存済み結果準備のoperationとは区別し、実holdout/正式50,000反復は起動しない。その後、独立数値auditの入口と全工程の資源停止条件を揃える。正式gate/holdout/freeze・principal/保護root/UAC/ACL・push/mergeは対象外。

## 185. 架空入力の数値workerと所有実行記録を接続（2026-10-01）

[結果](anomaly-multiseed-v0.3-fixture-worker-2026-10-01.md)、[API](../anomaly-v03-fixture-worker.md)。開始045bea45964585b003ac0fdf41b1dcde264230e8、実装4d3c08b4eb5e235e681ed0f0cafdde3c4f9ddde7。新module/testの2本、旧64code/18data不変。clean候補fw01/banto-aiを作成し旧候補を保全。OUT artifacts/fixture-numerical-worker-2026-10-01、tests-1/。

新15試験pass、failure/error/skip0、54.015秒。所有子が40個の架空cluster・4drawを計算し、前工程の既知文書pinと一致。親保持4入力・source/runtime・元Popen handleのPID/生成時刻・固定argvを照合し、5payload/1,976,761bytesを保存。selected source21/Python2/input4、補助依存project37/全245files/188modules/native48を終了後disk/Git照合。保存例14.678秒、子監視4.056秒、exit0/reaped/error0。

子上限60秒/private256MiB/stdout+stderr合計1MiB、fixture最大8draw、入力/文書/5payload上限10/4/8MiB。子peak64.95MiB、harness peak126.41MiB。保存例後RAM空き8.32GiB、commit余裕12.92GiB、C/D空き114.10/387.12GiB。OS26200/9457、旧formal pin不変。最終値・文書revision・hashはsavepoint-evidence.jsonとsave-checks.json。

既知文書も同一計算実装の過去出力なので、独立数値auditではない。次は同じ限定入力とanalysis出力の別実装検算を接続し、その後全工程directory/system commit停止条件を揃える。子観測は実行認証/full closureや受入済み依存profileではない。正式null4欄/ready=false、formal/promotion/S6/trust/full closure=false、fixture_inference_performed=true。writer/reader/audit/公開markerは今回未起動。

前保存点24493bytes/SHA8c96fb2649059b3a7500f20c2327435c95c193a7faa7199151329007a5f07046を照合。既存720評価再実行0、新評価0、登録データ読込み0。旧実計算c01d1c9・本流6f1285d・closed・dirty文書/CRLF差・候補/保存点を保全、banto-24 PAUSED。正式gate/holdout/freeze・principal/保護root/UAC/ACL・push/mergeは対象外。

## 186. 架空主集計の別実装auditと所有process証拠（2026-10-01）

[結果](anomaly-multiseed-v0.3-fixture-numerical-audit-2026-10-01.md)、[API](../anomaly-v03-fixture-numerical-audit.md)。開始362cb7544879c2e044423c5a84b13f6c185ca2b3、実装8bd4b67eac5ecaaa72fb139bc12a0bff484448b8、clean候補fa01/banto-ai。新算術/worker/test4本、旧66code/18data不変。OUT artifacts/fixture-numerical-audit-2026-10-01、tests-1/observed-audit/。

標準ライブラリのみの別算術でdraw番号を順に展開し、9主表の117絶対推定・72対応差・180gate、effective exposure/検出済みdelay/候補判断を検算。元analysisの4ファイルを前savepoint pinで保持し、元analysis/720評価は再実行なし。新22試験pass、27.521秒、failure/error/skip0。CI改変を保持receiptごと再封印しても実子が数値不一致としてexit2で拒否した。

実保存例7.506秒、子監視1.532秒、PID42012、exit0/reaped/error0。要約1185bytes/SHA6b78fea2e2863b99513cbf2e967a2ef70de99f0f5146d7762bbaf380c0696d1c。selected source13/Python2/5入力、補助依存project30/全234files/179modules/native48を終了後照合。role=audit、元handleと子PID/生成時刻、親保持期待値へ結合。

子上限60秒/private256MiB/stdout+stderr1MiB、最大8draw、入力6MiB。子peak46.54MiB、harness peak76.08MiB。保存例後RAM空き8.18GiB、commit余裕12.90GiB、C/D空き111.43/387.12GiB、OS26200/9457。最終資源・文書revision/pinはsavepoint-evidence.json/save-checks.json。

slice/sidecar導出・coverage/producer・登録データは対象外と明示。正式S6/full closure/受入済み依存profileや文書全体監査としない。formal/promotion/S6/execution_authenticated/full closure=false、fixture_numerical_audit_performed=true。元文書/5payloadのnull4欄・audit未実行表記を遡って変更しない。次は限定fixture工程のdirectory総量/system commitを含む資源停止条件を接続し、正式化時は未検算範囲を残件として扱う。

前保存点27575bytes/SHA5c0ff3a16f50589daf487a7f58a94a6acc85ae70625c32a97d5631d1c681f17d。旧実計算c01d1c9・本流6f1285d・closed・dirty文書/CRLF差・fw01を含む旧候補/保存点は保全、banto-24 PAUSED。新評価0、正式gate/holdout/freeze・principal/保護root/UAC/ACL・push/mergeは対象外。

## 187. 限定fixture工程の共有資源停止（2026-10-01）

[結果](anomaly-multiseed-v0.3-fixture-resource-budget-2026-10-01.md)、[API](../anomaly-v03-fixture-resource-budget.md)。開始a47b4ba1af372c8159413f0d8f2a8ce5cc5fbd3b、初回f4c1918、修正後cf4d9c42c11c202984aacdd71ac5efb0368f22d0、成功候補fb02。新module/test2本＋既存5本の変更、旧65code/18data不変、旧pinを保存。OUT artifacts/fixture-resource-budget-2026-10-01、成功tests-2/shared-example/。

新budget16＋supervisor13＋analysis15＋audit9の53pass、83.808秒、failure/error/skip0。初回52試験の19failure/2errorはWindows DirEntryのst_nlink=0による過剰拒否で、path.lstatへ修正し、monitor異常も失敗にする試験を追加。初回記録/fb01を保全した。実子の小容量超過・模擬commit低下・終了直後超過・未終了owner/保存失敗を検査。

親/共有120秒、親private512MiB、directory32MiB/256entries/深さ8、commit/RAM余裕2GiB、disk5GiBを監視。既存子60秒/256MiB/stdout+stderr1MiBと起動条件は併用。共有monitorで入力準備・analysis・auditを累積計測し、保存例23.623秒、両子exit0/reaped/error0、共有最大11.26MiB。小さい40cluster/4drawだけを各1回実行し、既知文書pin・主表検算が一致。元入力/既存720評価は変更・再実行なし。

子analysis/audit peak66.09/46.81MiB、harness peak121.75MiB。保存例後RAM空き8.25GiB、commit余裕12.93GiB、C/D空き107.20/387.12GiB、OS26200/9457。最終値と文書revision/pinはsavepoint-evidence.json/save-checks.json。予算はsamplingと親checkpointによる停止でhard quotaではなく、最終診断に64KiB予約する。

次は受入残件表を現在のfixture計算・primary audit・資源停止の証拠へ更新する。正式予算・契約/登録consumer/未検算slice・役割/source-runtime・公開受入は残る。正式null4欄/ready=false、formal/promotion/S6/trust/execution_authenticated/full closure=false。前savepoint26669bytes/SHAa57343756c873d9c6e51ba2faa63d68bf8150f8bbde7200ebae69baacc20f531。旧実計算c01d1c9・本流6f1285d・closed・dirty文書/CRLF差・旧候補/保存点保全、banto-24 PAUSED。正式gate/holdout/freeze・principal/保護root/UAC/ACL・push/mergeは対象外。

## 188. 2026-10-01 正式受入残件の更新と次のslice audit

[最新残件表](anomaly-multiseed-v0.3-acceptance-gap-update-2026-10-01.md)を保存。起点27e4d746979e9792b61b0017482890d0643565b1、実装cf4d9c42c11c202984aacdd71ac5efb0368f22d0/fb02は不変。OUT artifacts/acceptance-gap-update-2026-10-01、文書revisionとpinはsavepoint-evidence.json。保存点7＋receipt13＝20file/223,090bytes、72code/18dataを照合し、新評価/再計算/新試験0。

5payload・数値worker・主9表audit・限定fixture資源停止を完了側へ反映した。正式化は運用契約、登録consumer、役割/source-runtime、公開/全監査、全体予算の5まとまり。正式開始前の実装/契約と実行後の成功証拠を分け、循環要求しない。旧4payload通常公開/別readerを未実装へ戻さない。

次は架空40clusterのslice/sidecar別実装検算と既存owned auditへの接続。本文1,233行、補助4系列2,835行、詳細9表を独立導出し、合計維持の誤割当・key/分母/null/省略の不整合を検出する。保存済み入力・文書を使い、元analysis再計算0。必要なslice入力pinとaudit scopeを追加し、旧primary-only receiptを保全。限定予算を維持して関連試験と別audit例1回を実施する仕様を具体化した。今回まだこの検算は実装していない。

今回の開始時RAM空き7.62GiB/commit余裕12.29GiB/C/D126.13/387.12GiB、確認process peak20.37MiB。OS25H2/26200/UBR9457。終了資源はsave-checks.json。旧実計算c01d1c9/main6f1285d/closed/dirty文書を保全、banto-24 PAUSED。正式gate/holdout/50,000反復なし、principal/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。

## 189. 2026-10-01 架空slice/補助表の独立検算と所有audit接続

[結果](anomaly-multiseed-v0.3-fixture-slice-audit-2026-10-01.md)、[利用方法](../anomaly-v03-fixture-slice-audit.md)。実装b6d578e7c577470ecb2fbef228413d6b2abf85bf/fs02、初回ced27e3895b00e6fadcbc21157b74d38112364de/fs01を保全。OUT artifacts/fixture-slice-audit-2026-10-01、最終文書revisionと74code/18data pinはsavepoint-evidence.json。

計算側関数を使わず、fixed coordinate sums/literal delay multisetで本文1,233行・補助4系列2,835行・詳細9表を検算。新operation audit-invented-primary-and-slices-v1はslice pinを元analysisへ結び、6入力/14MiB、新出力primary-and-slices-audit.json。旧primary-only形式と5入力/6MiBは維持。

pure14＋owned14＋budget16の44項目。tests-1は43pass/1error・74.090秒、同じcountのcellから差を探した試験データの組立てを1件修正。production code不変、他test/setup不変をpin/ASTで確認し43成功を再利用、修正1件はtests-2でpass・1.964秒。旧ログ/候補/harnessを保全。

保存済みcf4d9c4解析を再実行せず、別audit1回で主9表/180gateとslice全対象一致。全体10.469秒/子2.868秒、PID46224/exit0/reaped/error0。selected15/Python2/入力6、依存project32/全236/module181/native48、追加0。出力2,384bytes/SHAbe0a327a15db02a5881e51b682fefcdcfe05cae995a7443dc941647c51a863c4、元文書既知pin/原本5file不変。

共有budget成功、dir6.74MiB/25entries、親peak100.68MiB/子66.58MiB、commit余裕最小12.24GiB。例後RAM7.91GiB/commit12.74GiB/C121.32GiB/D388.26GiB、OS25H2/26200/9457。正式pin9168や旧実計算c01d1c9/main6f1285d/closed/dirty文書不変。banto-24 PAUSED。新評価0/旧720再実行0/正式50,000反復0。

次は既存5payloadの通常公開・別readerへaudit scopeとwriter実行記録を結ぶ。自己参照とpartial/unconfirmed/応答喪失を扱い、旧4payload経路/元analysisを保全。今回の成果は架空countからの導出に限り、登録観測/coverage/正式推論/契約/全体予算/closureの受入ではない。正式null4/ready=false、principal/UAC/ACL/同時書換え保留、Windows3.12必須化なし、push/mergeなし。
