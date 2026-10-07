# v0.3 worker source callback／stop fence CIの保存照合（2026-10-07）

## spawn IO 1d9d70aのCI37637048268：両試験成功／run失敗を保存

外部fullHEAD `1d9d70a20aba3a96646f5a0e1e2ff1a2391cb20c`、attempt1/push/workflow SHA-256 `1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8` を固定。runはcompleted/failure、存在するjobは3.12=112845899910／3.14=112845899395の2件で両方success。各minor3381/fail0/error0/skip237/source不変、unittest_success=true。check suite101957648963にも同じsuccess check2件だけ／annotation0、artifactも両journalの2件だけ。

compare job/check／comparison-regression artifactが存在せず、run全体の失敗原因は未特定。比較jobの欠落をlocal回帰、共有fixture一致、runner候補一致、成功CIへ読み替えない。重複CI再実行0。

専用 `artifacts/ci-diagnostic-37637048268/` にrun/attempt jobs/check-runs/artifacts一覧／外部HEAD workflow／2journal／2full job logの9原rawを保存。failure-complete-index.jsonは2027B／`2b932cf568e580e89767e280ce996d30c28b76789758fd2c0259d2cf61661811`。download helper46724/creation134358601691182985/token32441068b411777fe59b3df454afceb82901211d177252080ee37ea136bdc6e8はexit0/CIM残存なし、元identity/tokenをlive/executionへ保存。native0／追加agent0／formal_permission=false。

未保存CIは37640186606（fullc78dbfe34827ae7a9bb7cb979da422cf0ceef1d1／3392予定）、37643113206（full0f9cb52e1b547ed70e0a352417b1846639afa322／3405予定）、37643762113（full0aaa12db38fe0caf03cc2d4bd4e036b10304fcc4／3406予定）、進行中。各終端をその外部HEAD/workflow/run/attempt/jobsへ固定して保存し、成功時だけlocal回帰／runner v2を照合する。doc-only新CI追跡なし。以下は先行履歴。

## read adapter43da351のCI37634146788を保存

外部fullHEAD `43da351954ccc80af5ddc2d91b53027b80786bc3`、attempt1/push/workflow SHA-256 `1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8`、jobs3.12=112835797417/3.14=112835797900/compare=112851378097へ固定。各minor3368/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37634146788/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote一致、共有29fixture/必須28、runner v2 consistent_candidateを保存。

3.12/compareは20260927.320.1、3.14は20261004.327.1、公式release/README metadata/blobと各log/journal外部pin・新版prerelease=trueを照合。digest未取得/候補未採択。選択CLI7は6raw一致/skip1file既知CRLF6差を両pinで保全。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| complete-summary.json | 2564 | `87eb7617d195f074221b3d1aa42d3d7ac79f3d0049004db565883c55a5e922ff` |
| 37634146788-candidate-pins.json | 3462 | `93d301f46529986707be397b01c19b70ed75f88f3cd3c406e7902e750023b444` |
| 37634146788-result.json | 3959 | `8a2494faab3919315890b4f3aa982e23e10f48108c211db975d5540952f2bb69` |
| ci-complete-index.json | 2783 | `4dcb29afb81401bbd9fd0ba99115a697b2ffac081b3c27d75d729a55693f92ed` |
| local-cli-source-pins.json | 2138 | `ef0722c17169c8c86b1e1a385524d877d6d92c57fbe8534e06d583427e6be29c` |

download13396/creation134358584877871179/token90d0c3d6c1160eb4f21109633a6515ad18a698a73e89f2c8a2359898af4e03a0、verification46732/creation134358585622648933/tokenc061fa254a8d19dd9e0118285b8c3241671a586703a8d6a34bfabf8e262bbe27はexit0/CIM残存なし。元identity/tokenは各live/executionへ保存しPID単独で扱わない。全helper終了・critical ownerなし、新native0・焦点反復0・追加agent0。この保存をc78dbfeの実pipe/native/容量合格/最終受入へ読み替えず、旧失敗rawも保全。未保存は37637048268（1d9d70a/3381予定）と37640186606（c78dbfe/3392予定）、進行中。以下は先行履歴。

## 追加IO owner初版66d31ee／補強ffbdc2fのCI保存

| run / 外部fullHEAD / attempt1 | jobs3.12 / 3.14 / compare | 各minor実試験 | index bytes / SHA-256 |
|---|---|---:|---|
| 37628405639 / `66d31eee72d25eda0546739053f43cf47f58d976` | 112816041057 / 112816041367 / 112836643919 | 3354 | 2783 / `f1b2f0e8ff218227721021663e98ef91de282d341a6ffeecae9cc847796f4fca` |
| 37629470712 / `ffbdc2f8c65dc9f155375330c9c194eb0b62b962` | 112819652646 / 112819652333 / 112833745727 | 3355 | 2783 / `cc0319c1c7409402dc52596ffb6a77229cf289c2b11e8ccd0947df4928aba8b4` |

両runともpush/workflow SHA-256 `1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8` を固定し全3job success、各minor fail0/error0/skip237/source不変。各専用 `artifacts/ci-diagnostic-<run>/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote一致、共有29fixture/必須28、runner v2 consistent_candidateを保存。3.12は両run20260927.320.1、3.14は両run20261004.327.1、compareは初版旧版/補強新版。公式release/README metadata/blobとlog/journal外部pin・新版prerelease=trueを照合、digest未取得/候補未採択。選択CLI7は6raw一致、skip1fileの既知CRLF6差は両pinを保全。

| 保存物（run順: 初版 / 補強） | bytes | SHA-256 |
|---|---:|---|
| complete-summary.json / 初版 | 2587 | `76f91787e4a7914446fdc2270f050cb2baa71372dc9839e703a7bccf49bf8f47` |
| candidate-pins.json / 初版 | 3462 | `79041d5f8703f5a6d51d12f6802d1c6528abefce5da4139835873386e71c5b30` |
| result.json / 初版 | 3959 | `01edd8d1acf0de11e6137e782afd6bb111e26dbe44164058c82f044ddd5b4688` |
| complete-summary.json / 補強 | 2579 | `a1f2e3b7d3e4b7c29daffca5c63500030e8e892c115b81e2e495288c7d648f33` |
| candidate-pins.json / 補強 | 3462 | `c2108bd2fea74d61fd70ab0d9c07826e79d4e7205d089f674788d682f4491e22` |
| result.json / 補強 | 3959 | `0f18a686d20b17db74b17f4d165810158d56af83e46e37abd0030ffa9476d3a7` |

初版download30752/creation134358558596121060/token5e9310b3d8a6be0c7a2bfaabed5bc0ce2a81899599a11569cb3115fb803954fd、verification37004/134358559010729195/token22f9e3c788480f624a67dd8092195cea53acc182e45f6e5972b01f6ad63ec75aはexit0/CIM残存なし。補強download26668/134358557397171910/token55533178a479f5180b592776a2544da096d5fa913720b0e503de1f01445d8e96、verification49716/134358557776668676/token1c448ee079cf03380fb6a6dd0a349a1c3e25c63ffef1df9921c847c7a80171e5もexit0/CIM残存なし。元identity/tokenは各live/executionへ保存しPID単独で扱わない。

焦点/native反復0、追加agent0、全helper終了・critical ownerなし。この保存を新read adapter43da351の実native/容量合格/最終受入へ読み替えず、旧失敗rawも保全。未保存CIは37634146788（full43da351954ccc80af5ddc2d91b53027b80786bc3/各minor3368予定）のみ。正式gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。以下は先行履歴。

## bounded Git spool 3ee5dc2のCI37625071676を保存

外部fullHEAD `3ee5dc2b1f3d35cb9bfc6d1cfccec94035f9a0a4`、attempt1/push、workflow SHA-256 `1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8`、jobs3.12=112804654034/3.14=112804653733/compare=112824039641へ固定。各minor3343/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37625071676/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote一致、共有29fixture/必須28、runner v2 consistent_candidateを保存。

全job20261004.327.1、公式release/README metadata/blobと各log/journal外部pinを照合。保存releaseのprerelease=true、digest未取得/候補未採択。選択CLI7は6raw一致、skip一覧1fileの既知CRLF6差は両raw pinを保全。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| complete-summary.json | 2566 | `78379863b954a77505e0c0d2b88bdfad03485bc8e07b884830d3b26eca9aba6d` |
| 37625071676-candidate-pins.json | 2565 | `4b9f69b23f5ceab927ed6ddf8d8c8bc1f9f9778f0947740a01894836a5fb1f94` |
| 37625071676-result.json | 3062 | `0752493b30b71cf08b54675107f89d46ddcce1333ae78ae579b6533afcfe2640` |
| ci-complete-index.json | 2783 | `17d71945d3766479478f3f45e7feccbdbe868dd42d626b686a34555105c036be` |
| local-cli-source-pins.json | 2138 | `86bfc3695074a4aefd55477e95fa4e8b35c48c8bed914a5aa9977d7019318eaf` |

download11976/creation134358546333730461/tokenb4ac015ced94016b7caf2542f0681f99b6bc28bc0331413c8c3b38ef1388d00d、verification34576/creation134358546607945951/token9dc5c75a3f58c8eb1f681233583c39b26cc5a376b2d0b6270fa8bc5b0f4f7333はexit0/CIM残存なし。元creation/tokenは各live/executionへ保存。新native0・焦点反復0・追加agent0、全helper終了・critical ownerなし。後続ffbdc2fの実pipe/native/容量合格や正式受入へ読み替えない。

未保存は37628405639（66d31ee/3354予定）と37629470712（ffbdc2f/3355予定）、両run進行中。doc-only新CI追跡なし。正式gate=s4_acceptance_not_frozen、formal_permission=false、正式credit0、登録holdout観測未読。以下は先行保存点の履歴。

## reader上位forwarding a12c3e9のCI37617865579を保存

外部fullHEAD `a12c3e91883d9e79fadbdd8f4b23b06f02add2ff`、attempt1、jobs112780500670/112780500318/112797954705。各minor3331/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37617865579/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote一致、共有29fixture/必須28、runner v2 consistent_candidateを保存。index2783B/0595d9dbb7d76a15433a2adaf39f554e9136bc1c59dbc4ffa8f5321d72f63066。

全job20260927.320.1。公式release/README metadata/blob外部pinと各log/journalを照合、digest未取得/候補未採択。選択CLI7は6raw一致、skip一覧1fileの既知CRLF6差を両raw pinで保存。sidecar2138B/5c2e120bf7d2509a39c9c8629d8c5bf4c74ed8a90fc804418568cb35ffbc2346。

download41096/creation134358516631126561/token6172b50b048d18b85870a4eb7327e0c21f8c907b8b56ac88dd50cae45998d853、verification42804/134358516864242556/token9c43db3376850215ae337364d11e50e79e1792f55a5c29c9f87982f5c75a4960はexit0/CIM残存なし。新native0・焦点反復0。後続3ee5dc2/native/正式受入へ読み替えない。未保存は37625071676（3ee5dc2/3343予定、進行中）。以下は先行履歴。

## reader実親接続217f0eaのCI37614547790を保存

外部fullHEAD `217f0ea66470d24bd9ecd3043a5ec428557b6fc3`、attempt1、jobs112769615386/112769614949/112785852696。各minor3321/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37614547790/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote一致、共有29fixture/必須28、runner v2 consistent_candidateを保存。index2783B/0bbdfd8b423dfa31593487d560fea024bd10987cbda3b9a18f4302de18c61fb4。

全job20260927.320.1。公式release/README metadata/blob外部pinと各log/journalを照合、digest未取得/候補未採択。選択CLI7は6raw一致、skip一覧1fileの既知CRLF6差を両raw pinで保存。sidecar2138B/b3ced2d99cb299bf4f8a3c0f64c7d4e723eafcc94ccf1fc9464da2e09ca4e890。

download46600/creation134358505666955522/token90ccf6ff6ca781369c4877d00fccbd14a4b8d62de06a6d1f2477715e31ee469c、verification44352/134358505891259855/token2f9606fb9e17c9d41b6d45b8f5fc8b0e6b2d635aaa5e7ef8e61a8d103a853df3はexit0/CIM残存なし。新native0・焦点反復0。後続a12c3e9/native/正式受入へ読み替えない。未保存は37617865579（a12c3e9/3331予定、run成功確認）のみ。以下は先行保存点の履歴。

## reader親proof 0f249f6のCI37612261124を保存

外部fullHEAD `0f249f63be055f0937c67a7963f541daa9e6df83`、attempt1、jobs112762079973/112762080346/112771980235。各minor3311/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37612261124/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote回帰一致、共有29fixture/必須28、runner v2 consistent_candidateを保存。index2783B/c5b3a0c4ad209a62d37846f96497ae918470d8d20deeebd038b48ea487880e40。

3.12/compareが20260927.320.1、3.14が20261004.327.1。公式release/README metadata/blobの外部pinと各log/journalを照合、新版prerelease=trueも一致。digest未取得/候補未採択。選択CLI7は6raw一致、skip一覧1fileの既知CRLF6差を両raw pinで保存。sidecar2138B/59a1555d4e1561a183cce6a7c2b7f6ba45dc1ccf5b8ef7f5037ef00e938986bc。

download47668/creation134358497174631451/token6480a23ec2643b9c1e1b8b45852ebb539a00fd354d1d79137f17609445cc8944、verification4980/134358497432554142/tokenf30b77073053ede5c31ba6e1f4cab3d64b7d5662eade2d2f616d045901483818はexit0/CIM残存なし。新native0・焦点反復0。後続code/native/正式受入へ読み替えない。未保存は37614547790（217f0ea/3321予定、run成功確認）、37617865579（a12c3e9/3331予定、進行中）。以下は先行保存点の履歴。

## initial-reader child入口202b1c3のCI37609649219を保存

外部fullHEAD `202b1c3081f34592e4a79188cda7f15cc9f4ec5f`、attempt1、jobs112753514958/112753514792/112769427609。各minor3299/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37609649219/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote回帰一致、共有29fixture/必須28、runner v2 consistent_candidateまで保存。index2783B/a31b7e6ae00e6785e9c48cfdc0d9307ebef24a42c39222e69445387c89a3f664。

全job20260927.320.1。公式release/README metadata/blobの外部pin、各log/journalを照合。digest未取得/候補未採択。選択CLI7は6raw一致、skip一覧1fileの既知CRLF6差を両raw pin保存。sidecar2289B/c4e80a07c1756443c03998939560af4b4ba214253b9762da292d82afd7279bb0。

download48116/creation134358480679183654/tokenb24c971e867dc91d7861371bbfdf9c0bf0f20a7fbcf00671a475ef2f53db4226、verification46332/134358480928545740/tokenb38ab75b809b307b2bddd6f25c3ceaa9e87dc12367d7f7574452f6c8a2fed57fはexit0/CIM残存なし。新native0・焦点反復0。後続0f249f6/217f0ea/a12c3e9のnativeや正式受入へ読み替えない。

未保存は37612261124（0f249f6/3311予定、run成功確認）、37614547790（217f0ea/3321予定、進行中）、37617865579（a12c3e9/3331予定、進行中）。先行37605468456等は保存済みで反復しない。以下は先行保存点の履歴。

## terminal guard-order e1b8924のCI37605468456を保存

外部fullHEAD `e1b892409fa22e45c9757f34bfe0f6655d1bc08d`、attempt1、jobs112739742275/112739742543/112755508389。各minor3287/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37605468456/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote回帰一致、共有29fixture/必須28、runner v2 consistent_candidateまで保存。index2783B/a33057c8b6553fc410cf4817f6d2edf892784cb373b399aa9235d08d976a1c55。

3.12/compareが20260927.320.1、3.14が20261004.327.1。公式release/README metadata/blobの外部pin、各log/journalを照合し新版prerelease=trueも一致。digest未取得/候補未採択。選択CLI7は6raw一致、skip一覧1fileのCRLF6差は両raw pinを保存。sidecar2289B/a06065c3cfbdf26a49d955de3e48c62310472c3024521901d86b98c04204f1c4。

download30868/creation134358462883487355/token77f168971288fc7ad6bcc5659969922eefd5ea539352ed60ad8b8c8c458e1a32、verification41608/134358463195262654/token6d73eba44e92afc8d41c3b51972530ac30413eb6ef0db12d82b59e4364cd7075はexit0/CIM残存なし。新native0・焦点反復0。後続202b1c3/0f249f6/217f0eaのnativeや最終受入へ読み替えない。

未保存は37609649219（202b1c3/3299予定、run成功確認）、37612261124（0f249f6/3311予定、進行中）、37614547790（217f0ea/3321予定、進行中）。先行37604591211等は保存済みで反復しない。以下は先行保存点の履歴。

## terminal初版13ac6a1のCI37604591211を保存

外部fullHEAD `13ac6a18a7681a0d85185d7e4fdad92940ae1bc0`、attempt1、jobs112736876226/112736876291/112752961027。各minor3286/fail0/error0/skip237/source不変、全3job success。専用 `artifacts/ci-diagnostic-37604591211/` にrun/attempt jobs・2journal・comparison/regression・3log＋localの10raw/14pin、local/remote回帰一致、共有29fixture/必須28、runner v2 consistent_candidateまで保存した。index2783B/20187902a675541ab96534bcf848e240fce16db8a2515179a5f89f165ee31b14。

3.12/3.14が20260927.320.1、compareが20261004.327.1。公式release/README metadata/blobの外部pin、各job log/journalを照合し新版prerelease=trueも一致。digest未取得/候補未採択。選択CLI7は6raw一致、skip一覧1fileは既知CRLF6差で両raw pinを保存。sidecar2289B/049baa238e6dcc103aef4e3e8899ff4d849b85c06fda0c01a872aa0c42ebec18。

download44556/creation134358450664634211/tokena2fabbb1dbef450b15fa6efa0ea3f33f8cf00ae6920a9ea4b7f628e8509e53a2、verification18964/134358450884987789/token147faaf80f09d7517c73935dc4be88b1c810a8796c8dbefd59f83fcb105158beはexit0/CIM残存なし。新native0、focus反復0。後続e1b8924/202b1c3/0f249f6のnativeや最終受入へ読み替えない。

未保存は37605468456（e1b8924/3287予定、run成功確認）、37609649219（202b1c3/3299予定、進行中）、37612261124（0f249f6/3311予定、進行中）。先行37602415125等は保存済み、反復しない。以下は先行保存点の履歴。

正式許可false・正式credit0・登録holdout観測未読。CIは各外部HEADに限定した証拠で、後続revisionのnativeや最終S4受入を代用しない。

| CI / 外部HEAD | 3.12 job / 3.14 job / compare job | 各minor件数 | index bytes / SHA-256 |
|---|---|---:|---|
| 37576149693 / `e4cb23aeff8501ab91cfdcf34d804612f856352f` | 112645385920 / 112645386128 / 112656640376 | 3144 | 2783 / `cfdb36fe2b651278ad8b00d35c6a79095f5fb146a762f030b9abaa2c072c0e71` |
| 37578543252 / `01ab74fe479ddfeb46ca781ebbd3db1ccb93c84c` | 112652777551 / 112652777298 / 112663769019 | 3157 | 2783 / `72ce93345566e5c74439debb921165d5e8cfd2778d088a81efb1576c1ea43ed6` |

両runはattempt1・push・全3job success。各minor fail0/error0/skip237/source不変。run/attempt jobs、2journal、comparison/regression、3job logとlocal regressionの10 rawを専用 `artifacts/ci-diagnostic-<run>/` へ保存し、local/remote全回帰一致、共有29fixture/必須28試験を確認。workflow Git blob SHA-256 `1376641c6a394b2f4781bb0ceaa8acfa735f35dfa1799d8503300ba9268815e8` と各外部fullHEAD/run/attempt/job idを固定、各indexは14 raw/control pinを保持する。

runner v2は両方consistent_candidate。37576149693は全job20260927.320.1、37578543252は3.12/compare20261004.327.1・3.14が20260927.320.1。保存済み公式release/README metadata/Git blobとminor journal/logを照合し、20261004版の外部prerelease=trueも一致。VM digest未取得・候補未採択。

追加の選択local CLI/source7 file照合では、`tools/ci_windows_native_skip_ids.py` のworking raw24604 BとGit raw24598 BにCRLF6箇所の差があった。初回all-raw-equalを要求したsidecar照合の失敗は37576149693 rootに保全した。Python sourceのCRLF→LFだけでGit bytesへ一致することを限定確認し、raw一致へ読み替えず両raw pinとrelationを `verifier-source-pins.json` へ明記した。他の選択6 fileはworking/Git raw一致。新しい数値試験/local回帰の再実行は0、この追加source照合は実ロード閉包ではない。

| source sidecar | bytes | SHA-256 |
|---|---:|---|
| 37576149693/verifier-source-pins.json | 2311 | `ae5aa7dd85a6de53388bf2f70b9864b996de6a0d2a10d5ee8366c8e7347b6a02` |
| 37578543252/verifier-source-pins.json | 2311 | `f9a53511457754c5de5b763d5bc2d6f076becb0144b83ddd16226df0b97cbfe7` |

保存後checkerは各14 raw pinと選択CLIのworking pin、channel更新のscience/source11 pin、clean HEAD/origin、doc-only差分を照合する。未保存CIは37581339092（HEADaaca57c、各minor3178予定）と37583002436（HEADe5ff975、各minor3191予定）。doc-only新CI追跡は増やさない。正式受入5残件と実データengineering範囲は変更しない。


## channel code aaca57cのCI追補

CI37581339092 / 外部HEAD `aaca57c9749fa4970919e2596f6a884b6851d2b5` / attempt1は全3job success。3.12 job112661473486、3.14 job112661473791、compare112674385868。各minor3178件・fail0/error0/skip237/source不変、共有29/必須28。専用 `artifacts/ci-diagnostic-37581339092/` に10 raw、local/remote全回帰一致、runner v2 consistent_candidate、14 pin indexを保存した。index2783 B / `d817666b4ca96baabbb4f6b3ee333c28c90e2a85c3f8773b774a75e2ace7f399`。

3.12/compareは20260927.320.1、3.14は20261004.327.1。保存公式release/README metadata/Git blob・log/journalと照合し、後者prerelease=trueも一致。digest未取得・候補未採択。選択CLI7 sourceは外部HEAD固定、skip一覧1fileだけCRLF→LF差を両raw pinで明記し他6 raw一致。source sidecar2311 B / `37e396bc9213a44b8ca2e864e786ff3324a41b636f0fc2c3de3d0c4e75dfc1d9`。数値/native replay0、後続codeの合格へ読み替えない。


## atomic channel code e5ff975のCI追補

CI37583002436 / 外部HEAD `e5ff97567a62764048576ce10606ce72bb6ab684` / attempt1は全3job success。3.12 job112666729426、3.14 job112666729643、compare112680362863。各minor3191件・fail0/error0/skip237/source不変、共有29/必須28。専用 `artifacts/ci-diagnostic-37583002436/` に10 raw、local/remote全回帰一致、runner v2 consistent_candidate、14 pin indexを保存した。index2783 B / `604389f2c14c42650dfe46cfec933b8515bb4c5274192954411f8e032deecff4`。

全job20260927.320.1。保存公式release/README metadata/Git blob・log/journalを照合、digest未取得・候補未採択。選択CLI7 sourceは外部HEAD固定、skip一覧1fileだけCRLF→LF差を両raw pinで明記し他6 raw一致。source sidecar2311 B / `41e3dce76e4785f929ad1218d5970a5a0372da9772543267e79a9504c0d56667`。後続revisionのnative/最終受入へ読み替えない。


## post-close code3016448のCI追補

CI37585092575 / 外部HEAD `301644854a9e4db7d6915ffda6c9bf8278be54dd` / attempt1は全3job success。3.12 job112673293155、3.14 job112673293337、compare112687473898。各minor3207件・fail0/error0/skip237/source不変、共有29/必須28。専用 `artifacts/ci-diagnostic-37585092575/` に10raw、local/remote回帰一致、runner v2 consistent_candidateを保存した。全job20260927.320.1、公式release/README metadata/Git blobとjournal/log照合済み。VM digest未取得/候補未採択。index2783 B / `0f3263fc3fb405c9f498b59bd88dd10a8efbabc0c0b368f5815665abc4730499`、選択CLI7 sidecar2311 B / `b17584605a44435ddb97ac6432c5244de3e3e33727bf596f04a219d978a8150d`。skip一覧のCRLF6差は両raw pinで明記、他6raw一致。

未保存はCI37587463962（HEAD8faa921/3220、run成功）、37590543104（HEADf0b3d72/3229、進行中）、37592838738（HEAD7da5aa9/3247予定、進行中）。doc-only新CI追跡を増やさない。

## 初版proof code18324bfの失敗保全

CI37592461789（HEAD18324bf）/ attempt1は3.12 job112696985861と3.14 job112696985445がRun unittestでRuntimeError、compare112697079830はskipped。run/jobs/failed log/2journalを `artifacts/ci-diagnostic-37592461789/` に保存した。両journalはtest_started0、成功run_finishedなし。local module discoveryは旧TestCase importで34（新18＋旧16）になり、7da5aa9のmodule参照修正でunique新18を確認した。失敗CIをsuccessへ読み替えず、修正後37592838738を別に追跡する。failure-index842 B / `cb704b22975f573b7b8ef873216ebc2025f7dc5d092b44be8f923e96b3e43adc`、journal-diagnostic2518 B / `a525c616f926ea18cce6a41dc26fb5ff0ba9acddfa0512b5e9d81649977e1604`。正式許可false/credit0/holdout未読、新native0。


## 子keeper code8faa921のCI追補

CI37587463962 / 外部HEAD `8faa921fc5c9e33ebe1a84799b3747c22326f28c` / attempt1は全3job success。3.12 job112680825712、3.14 job112680825951、compare112695061031。各minor3220件・fail0/error0/skip237/source不変、共有29/必須28。専用 `artifacts/ci-diagnostic-37587463962/` に10rawを保存、外部fullHEAD/workflow/run/attempt/jobsを固定したlocal/remote全回帰一致とrunner v2 consistent_candidateを確認。全job20260927.320.1、保存済み公式release/README metadata/Git blobと各minor journal/logを照合した。VM digest未取得/候補未採択。index2783 B / `886f576ab4fd97397a9ac25bd5ea763144eb0b4ca0fec8cd96da4020ac24b63b`、選択CLI7 sidecar2311 B / `9528bb81aa34d0f7cca0a7f96c5b126dbf0e43442aa557fa75d28994349a845b`。skip一覧CRLF6差を両raw pinで明記、他6raw一致。

全helper終了・critical ownerなし・新native0。verification helperのPID38812は先行proof焦点helperと再利用されたため、双方のcreation identity/tokenを各execution.jsonに保全して区別した。PIDだけでは同一process扱いにしない。初版proof CI37592461789の失敗rawは保持。未保存は37590543104（HEADf0b3d72/3229）と37592838738（HEAD7da5aa9/3247予定）、doc-only新CI追跡を増やさない。

実worker接続に向けた選択3 sourceは7da5aa9のworking/Git raw一致。既存parent archiveはverified source_blob専用でpost-close witness、head/status、failed/recovery rawを扱わないため、親の完了部品をworker actorへ流用しない。次は専用opt-in worker archive/raw resolverと元close/recovery eventを小さく固定し、0-job/部分ackの範囲を定めてから実entryへ渡す。source3のpinと静的所見は同CI rootのnext-boundary-notes.json1162 B / `15d03bb0fb9ecc7a4ba6932352da21e00b89620240ac26de192a80d2bff47f5f`。これはruntime閉包/nativeの証明ではなく、正式5残件は変更しない。


## spawn cleanup codef0b3d72のLinux失敗保全とfixture修正

CI37590543104 / 外部HEAD f0b3d72deea42ab984ad70a20a20cd7dcace7225 / attempt1は両minor3229件、各fail1/error1/skip237/source不変。3.12 job112690704814、3.14 job112690705168、compare112707082230はskipped。run/jobs/failed log/2full job log/2journalの7rawを専用rootに保全、failure-complete-index2863 B / `1d5a879c0cf8c98048f819cc7d8f143722bb8f066059389b210977c1baac2021`。comparison/regressionとcompare logはない。成功CIやrunner候補一致へ読み替えない。

fake Win API試験のctypes.get_last_error未stubがLinuxでAttributeErrorとなり、元OSError保持を確認する2件が失敗した。code9473523でtest setUpの1行だけを修正、Linux相当の属性欠落にした2件がpass、他の試験反復0・新native0。[修正証拠](anomaly-multiseed-v0.3-spawn-cleanup-portable-ci-fix-2026-10-07.md)。修正後CI37596406096（HEAD9473523/3247予定）と先行37592838738（HEAD7da5aa9/3247予定）は進行中で、両者を別外部HEADとして保存する。旧失敗と正式flag false/credit0/holdout未読を保持する。


## proof code7da5aa9の既知fixture失敗保全

CI37592838738 / 外部HEAD `7da5aa92b007965b3a51fd94afb73d6add67d3c3` / attempt1は両minor3247・各fail1/error1/skip237/source不変、compare skipped。3.12 job112698211125、3.14 job112698211531、compare112713514280。失敗はCI37590543104と同じspawn fixtureの元OSError保持2件で、Linux ctypes.get_last_errorのstub9473523を含まないHEADであることを確認。原run/jobs/failed-step log/2full job log/2journalの7rawを専用rootへ保存、failure-complete-index2922 B / `acdd87eb92885328635389ef5d8f075bf3d58f3272d8c563dfea739eb9dd524d`。全job journal image20260927.320.1、comparison/regression/compare logはなし、成功CI/runner候補照合に読み替えない。

修正fixture CI37596406096（HEAD9473523/3247予定）と新worker archive CI37598762191（HEADba6f82e/3263予定）は進行中。新archiveの[16焦点・原raw再読取り証拠](anomaly-multiseed-v0.3-worker-git-archive-resolver-2026-10-07.md)を保存、旧試験反復0・新native0。最終source/runtime閉包・契約/runner候補採択・正式受入を意味しない。

## 追補: portable fixture修正9473523のCI（37596406096）

外部fullHEAD `9473523f3d2dd04259b6b8492ea3b9a237600e69`、attempt1/push/workflow上記pinに固定。job3.12=112710022797、3.14=112710022692、compare=112725681886。全3job success、両minor各3247・fail0/error0/skip237/source不変。原run/attempt jobs/2journal/comparison-regression/3logとlocal regressionの10rawを専用 `artifacts/ci-diagnostic-37596406096/` に保存。local/remote回帰全一致、共有29fixture/必須28、runner v2 consistent_candidate。

3.12は20261004.327.1、3.14/compareは20260927.320.1。保存済み公式release/README metadata/blobとjob/minorを照合、新版prerelease=trueも外部pin一致。digest未取得・候補未採択。旧f0b3d72/7da5aa9のfail1/error1は別の原7rawとして保全したまま。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| complete-summary.json | 2569 | `111a021ba253ec8c07512cd99dbf7c16429de66f7b3f3a6cbcb5407b0b30ad03` |
| 37596406096-candidate-pins.json | 3462 | `3e31f8f15af930bee4ee8cda19cfd890520b9c6e0640d4a7e67261715397d484` |
| 37596406096-result.json | 3959 | `f65b97fc269314567c04844ca03db608ac90bf0e9aedd89f1372cfb12ae72fa3` |
| ci-complete-index.json | 2783 | `657a6e17610ea73bd2ca7bb4f60ea460e2695d9ebba28da2359e0a88091d9185` |
| local-cli-source-pins.json | 2390 | `8c1d63ba0607defc6de0288a4f236804a3071a0edf17b64847342636d781a0a0` |
| post-save-checkpoint.json | 1157 | `b452dc11e130b262f1533e2ce9e3d276b8d5385ec10a06974ad55237b93ffd94` |

選択CLI7は外部HEADへ固定し、6raw一致・skip一覧1fileは既知CRLF6箇所のみ（両raw pin保存）。実ロード閉包ではない。14 raw/control pinを保存後照合し、download PID26284/creation134358397765799801/token2a4e23e66338dafca994b5018ebf0e7fa190d61c12fd83d3c6805ba0058da16d、verification PID1996/creation134358398170303211/token67d7d453e71a6c27660607848354c0357cbb92aacf038dba72b73ed8e302f2f4はexit0/CIM残存なし。全helper終了・critical ownerなし・新native0。

未保存対象は37598762191（HEADba6f82e/各minor3263予定）と37602415125（HEADf0ecd89/3276予定）。doc-only新CI追跡を増やさない。このCIをf0ecd89 actorのnativeや最終受入へ読み替えない。

## 追補: worker archive ba6f82eのCI（37598762191）

外部fullHEAD `ba6f82e01eeedb4007a402589cd459f458b4308b`、attempt1/push/workflow上記pinへ固定。job3.12=112717687460、3.14=112717687857、compare=112733955134。全3job success・両minor3263/fail0/error0/skip237/source不変。原run/attempt jobs・2journal・comparison/regression・3job log＋localの10raw、14pinを `artifacts/ci-diagnostic-37598762191/` に保存。local/remote回帰全一致・共有29fixture/必須28・runner v2 consistent_candidate。

全job20260927.320.1、保存済み公式release/README metadata/Git blobと各log/minor journalを照合。digest未取得・候補未採択。選択CLI7は外部ba6f82eへ固定、6raw一致・skip一覧1fileはCRLF6差のみで両raw pin保存。runtime閉包ではない。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| complete-summary.json | 2576 | `28478f307acb3767bcb0789cf387e589cf961a367d2f015979a08a1ec67b2f65` |
| 37598762191-candidate-pins.json | 2567 | `d5278c9a5fabcfccd630adf4e797457877867a3e31df0f8a4c8442e500d208bf` |
| 37598762191-result.json | 3064 | `41687f6aa8b5065d8ce950be099a037faf336643e07ef73daa0e599eab790789` |
| ci-complete-index.json | 2783 | `331fc11cebd8d46ceb37c44708fddac50449ba1a00daecdfe9c5773c2a35acff` |
| local-cli-source-pins.json | 2390 | `fbf345abbe3f7368ede2e105d3cc03b38e7800b4970a0973c674f5c50ab0979d` |
| post-save-checkpoint.json | 1157 | `3ad98ac2b61062b600eb953b22eda5bb008f034d377d83c6714bf02e98263ef1` |

14 raw/control pinを保存後照合。download PID5772/creation134358409216731185/token443a50f9aaa390b374027bf9d4943c0640e272814db9ce7d7f6a8effbc13cd73、verification PID41304/creation134358410288654168/token8cdfaa1a87a9983e1216da4c4d67e832ecdc98abea2c516970c6634a15755b1bはexit0/CIM残存なし。全helper終了・critical ownerなし・新native0。

未保存CIは37602415125（f0ecd89/3276予定）、37604591211（13ac6a1/3286予定）、37605468456（e1b8924/3287予定）。このCIを終了guard e1b8924や最終受入のnativeへ読み替えず、doc-only新CI追跡を増やさない。

## 追補: worker actor f0ecd89のCI（37602415125）

外部fullHEAD `f0ecd8942432811120a2c82145cecf89822650ff`、attempt1/push/workflow上記pinへ固定。3.12 job112729729655、3.14 job112729729570、compare112742467485。全3job success・両minor3276/fail0/error0/skip237/source不変、10raw/14pin・local/remote回帰一致・共有29fixture/必須28・runner v2 consistent_candidate・保存後照合まで完了。rawはartifacts/ci-diagnostic-37602415125/。

3.12/3.14は20261004.327.1、compareは20260927.320.1。保存済み公式release/README metadata/blobと各journal/logを照合、新版prerelease=trueも外部pin一致。digest未取得・候補未採択。選択CLI7は6raw一致・skip一覧1fileは既知CRLF6差で両raw pinを保全、完全なruntime閉包ではない。

| 保存物 | bytes | SHA-256 |
|---|---:|---|
| complete-summary.json | 2565 | `88bb4789ec108660b0a2c75f1f81b6e150b2eb605bafd9953f3205b6a2a2ff20` |
| 37602415125-candidate-pins.json | 3462 | `0766669952fea19159aba9036dfa37f6f2d7340c11e19fb286f39356e13b05e5` |
| 37602415125-result.json | 3959 | `2066ee845a6758629df5b9ea74047c379ca2bbc7a1014636b40dde849e19abba` |
| ci-complete-index.json | 2783 | `72aebacb37240c440482d0f8412b96f39a4e111c7992d47381e5429b8c502b1a` |
| local-cli-source-pins.json | 2390 | `a49709f70b99348a7f57fc391e5e2d113c3f579c9783999e5a5b23f09d033754` |
| post-save-checkpoint.json | 1159 | `886e9712cd1d1c59dbb4e28b333bf1179ea4a3bcab9d27ded9e33d2b5a13852d` |

14 raw/control pinを保存後照合。download42160/creation134358437039117172/token74398ed30af2879bd3262e805bc9846a0a874e8da3a4c9ef4503acddddae1d7e、verification41428/creation134358438390052319/tokenec7dc239d161fde0056dcad14250d801c1d9849fc8e3d4ae0dd1b62e117c7632はexit0/CIM残存なし。全helper終了・critical ownerなし・新native0。

未保存は37604591211（13ac6a1/3286予定）、37605468456（e1b8924/3287予定）、37609649219（202b1c3/3299予定）。このCIを新child入口202b1c3や最終受入のnativeへ読み替えず、doc-only新CI追跡を増やさない。
