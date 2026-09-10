# anomaly multi-seed v0.3 S4-B1 引継書

状態: **handoff / blocked engineering candidate / no integration / no formal permission**

2026-09-10最新: §71を最初に参照。bcrypt KsecDD open helperのR12D=C0000022を確認、所有終了・証跡readback pass。親の読み取り専用確認ではRC allow1200a9に要求100003のwrite mask0x2が不足し拒否と整合。token/ACL/coreは未変更、child E2E未達。互換性のための権限構成見直しを許容するか、判断資料を保存して返答待ち。
UBR固定の承認済み緩和と実測buildは§31に記録する。
候補c4fe99eはpure/fake243件と独立レビューを通過。現在の10.0.26200.9445で18 sourceの実read-only preflightもverified。
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
