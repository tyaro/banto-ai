# v0.3 worker source callback／stop fence CIの保存照合（2026-10-07）

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
