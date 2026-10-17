# Reader限定launcherの原owner・返値契約のsource監査

2026-10-08 JST。開始HEAD/originは98254bbcb1b24d5fe8c876e6485a810b346738dd、working tree clean、元先行4helper同identity不在/critical ownerなし。production code a1ab304608d0d0ff486c73d84b3ba6d1612be222は変更しない。今回は隣接するlauncher/Job/attribute lifetime/reader入口を一つのsource監査単位にまとめた。production/test/native/完成focus/旧suite/追加agent/runtime-profile再観測0、doc-only追補を一回skip ciへ集約する。

## 確認した経路

対象5production sourceの13個のAST関数spanとsource pinを保存した。監査rawはartifacts/preformal-reader-native-launch-audit-20261008-prep/。58source/science pinは先行HANDLE_LIST保存時から不変。scienceはhash metadataだけで登録holdout観測は読まない。

| 境界 | sourceで確認した現在の動作 | 接続前に必要な境界 |
| --- | --- | --- |
| `_spawn_cli_inner` | 原PROCESS_INFORMATIONをIO前に保持する。返値はJob/process HANDLE/thread HANDLE/PIDの4値 | 原API/引数/outputとBOOL返値を元return位置で保持し、同じ原Job/process/thread ownerへ結ぶ |
| CreateProcess/Job assignment | CreateProcessWとAssignProcessToJobObjectのBOOLは`_need`へ直接渡され、独立した原return保持slotはない | BOOL/PROCESS_INFORMATION/member outputを判定前に保持し、unknown時も原owner/既知prefixを保全 |
| generic HANDLE_LIST | stdio3を`enumerate((stdin, stdout, stderr))`で複製する。finallyにattribute Deleteと親側stdio closeがある | 専用2とstdio3を別枠で発行し、共有後のclose/attribute lifetimeを未共有abortへ読み替えない |
| reader supervisor | callerが所有するPopenを作成し、stdin=DEVNULL、stdout/stderrはfile-directed。startupinfo指定なし | native raw ownerとPopen所有権・getter/kill/wait経路の明示bridge。合成Popen風objectを原owner証拠にしない |
| generate/reader entry | actual `generate_and_read`はParent.bindへ元processを渡すが、新resource/inheritance/HANDLE_LISTの発行呼出しがない。READER_BOOTSTRAPはargvだけ | 原限定launcherの実発行とchild-local endpoint再構成・同request/root/creation/clockへの認証 |

主要spanはjob_tree_ownerの`_spawn_cli_inner`(1384)、reader_git_workerのParent.bind(442)/launch.bind(878)、process_supervisorのsupervise(97)、owned_generated_attemptのgenerate_and_read(519)、owned_saved_attemptのreader_worker_main(441)。完全な位置とspan pinはsource-audit.jsonに固定する。Popen側が厳密なPopen型検査を行うという主張ではない。元caller objectと実native ownerの由来が異なるため、属性の形だけで置換できないというsourceからの判断である。

PythonのWindows Popenでは、handle_list指定時にclose_fdsと各HANDLEの継承性が関係する。この仕様は現在のreaderが専用HANDLEを渡した証拠ではない。並行creatorとの共有も、今後のexclusive発行境界に含める。[Python subprocess](https://docs.python.org/3/library/subprocess.html#windows-popen-helpers)。

CreateProcessWの成功は子初期化完了を保証しない。PROCESS_INFORMATIONの原process/thread HANDLE、STARTUPINFOEXとEXTENDED_STARTUPINFO_PRESENTの関係を新経路の返値契約へ固定する。[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)。Job assignmentの失敗・終了や割当前メモリの扱いもあるため、Job/memberの実returnを成功metadataで補わない。[AssignProcessToJobObject](https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-assignprocesstojobobject)。これらは公開仕様の参照で、実loaded runtime/profileや実Win ABIの観測ではない。

## 保存と原監査失敗

初回監査helperはstdioのASTが直接tupleであると誤って選択し、StopIteration/exit1で停止した。原source-audit.py/live/execution/source-audit-failure.jsonを保持。元18864/creation134359129386422118/token471c4fd84e2fa6bc839309b28bc634700151878e723c8a93a76c754498c65800はfailedで、同original process残存なし。原process stdout/stderr byte fileは捕捉していない。tool出力のtraceと失敗JSONを原processログ全体へ読み替えない。

別source-audit-v2.pyで選択条件をenumerate内tuple3へ訂正し、未完成のsource監査を一回完了した。元40284/creation134359132338946389/token0b48a39bf238639bde21d0212dc006267126d99a8a02a3017322727c258d1886はpassed/同original残存なし。native/試験bodyは初回・継続とも0。原metadata失敗をproduction/CI/native回収失敗へ読み替えず、原failed helperをsuccessへ書き換えない。

- source-audit.json: 20137B / 16ed9389e7885c9bf8ca7da050c207d62fd08f3654409069995c9ef853555617
- launch-contract-prep.json: 1480B / bfd51f1660456fff682d57ad08d0e5efb6dcd756d8fba7f22d205224f4646563
- 名前30source合計796233B、全体最大job_tree_owner 98055B / 9f3a36f3ca04f534a9feae092cbe35efe02d44d92e05ace741718558c5bf5901。archive module 94908Bはarchive自身の量で、全source最大ではない。

generated moduleは58準備pinに含めるが名前30の外。名前30/各phase32要求/予定64Git Jobを完全runtime閉包へ読み替えない。planはengineering準備要件でnative contract/request/policy/profileを発行したものではなく、fresh request/policy/runtime profileはNone。旧external v1-v4/request/entry/context/ack/proofへfieldを追加せず旧pinを読み替えない。

## 次の機能unitと制約

次は原raw Job/process/thread ownerを明示する限定launcher契約の準備を、CreateProcess return/Job assignment/member output/attribute lifetime/stdio3と専用2/原Python ownerの保持順までまとめる。既存Popenを偽装するadapterを採用しない。実child endpointの発行と原child close/rename/raw witness認証は別途同request/root/inventory/revision/clock/creationへ結ぶ。unknown/欠落/callback改変時は原error/output/HANDLE/pending/bufferを保持し、再launch/reap/recloseへ落とさない。

fresh latest-clean source/runtime/profile/private policy/request/unusedroot、exclusive、実control-packet-raw coupled容量、atomic全writer予約、親identity将来failure raw/diagnostic、原partialとnew archive growthの独立予約、entry/context実保存bytes、packet/gzip/frame/receipt/partial coupled peak/global memoryは未完成。snapshot/sidecar/context pin/attribute幅をatomic/native許可にしない。ReaderGitParent.create_nativeのroot/channel/clock/Job前拒否を維持し、準備前に全7役whole.runを限定readerとして実起動しない。同期native API/caller間の全経路wall・停止、実loaded runtime/source/業務異常子孫も未実証または未完了。

CI37732744553/git実fulla1ab304608d0d0ff486c73d84b3ba6d1612be222は開始時compact読取りで両minor113165365533/113165364493 in_progress/compareなし/run未終端、3812は算術予定/journal未確認。今回terminal download/journal/local回帰/runner候補照合0。終端時だけ未保存原rawを新専用rootへ一度保存する。doc-only新CI追跡なし、全完成CI/focusと旧failure/raw/pinは保全する。

formal gate=s4_acceptance_not_frozen/permission=false/credit0/holdout未読。正式5残件/採択/最終受入は未完了。archive512KiB/frame128KiB/decoded1536KiB/stdout1MiB/manifest32KiB/lease64、outer1MiB32entry depth2 reserve128KiB/global321MiB672entry、元wall-memory-output/cleanup30秒/poll0.25秒を維持。closed/disk一致/EOF/marker不在/worker exit/kill-wait/途中capacityを回収True/lease/ack/authへ読み替えない。実データは保存済み合成dev8/smoke2のengineering記述だけ。Sol容量エラー未確認、ACTIVE維持。
