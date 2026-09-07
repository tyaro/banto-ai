# anomaly multi-seed v0.3 S4-B1 引継書

状態: **handoff / blocked engineering candidate / no integration / no formal permission**

最新の自己点検: cleanup/置換traceの候補実装と追加修正は§11〜17を参照。
起動障害の既存ログ・公式仕様の照合は§18を参照。独立レビューとchild E2Eは未完了。
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
