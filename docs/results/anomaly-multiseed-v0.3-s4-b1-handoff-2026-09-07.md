# anomaly multi-seed v0.3 S4-B1 引継書

状態: **handoff / blocked engineering candidate / no integration / no formal permission**

2026-09-10最新: §43を最初に参照。最終結果を先に出す表示処理を追加し、失敗operationの観測方法を比較した。追加childなし、原因未特定。
UBR固定の承認済み緩和と実測buildは§31に記録する。
候補c6fc191はpure/fake231件と独立レビューを通過。現在の10.0.26200.9445で17 sourceの実read-only preflightもverified。
限定診断の実childは起動・終了確認済み。本流統合・native受入・formal permissionは引き続き未達。

最新の自己点検: cleanup/置換traceの候補実装と追加修正は§11〜17を参照。
起動障害の既存ログ・公式仕様の照合は§18、独立レビューと是正結果は§19〜20を参照。
独立レビューのP2 2件は修正確認済み。child E2Eと本流統合は引き続き未完了。
以下の初期結論・commit一覧・試験数は引継書作成時点の記録である。

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
